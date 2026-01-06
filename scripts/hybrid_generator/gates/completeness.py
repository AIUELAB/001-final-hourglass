"""
Completeness Gate - 必須フィールド完全性チェック

EPUP再発防止: エピソード追加前に全必須フィールドの充填を検証。
"""

from dataclasses import dataclass

# 必須フィールド（7軸スコア）
REQUIRED_SCORE_FIELDS = [
    "記憶性スコア",
    "共感性スコア",
    "意外性スコア",
    "生成品質スコア",
    "教育的価値",
    "ストーリー品質",
    "事実密度",
]

# 必須基本フィールド
REQUIRED_BASIC_FIELDS = [
    "episode_id",
    "person_id",
    "person_name",
    "age",
    "category",
    "episode_type",
    "episode_text",
]

# 有効なエピソードタイプ
VALID_EPISODE_TYPES = {"転機", "達成", "死去", "挑戦", "キャリア", "革新", "創業", "失敗", "復帰"}


@dataclass
class CompletenessCheckResult:
    """完全性チェック結果"""

    passed: bool
    missing_fields: list[str]
    invalid_fields: list[str]
    message: str


def check_completeness(episode: dict) -> CompletenessCheckResult:
    """
    エピソードの完全性をチェック

    Args:
        episode: エピソードデータ（dict）

    Returns:
        CompletenessCheckResult
    """
    missing = []
    invalid = []

    # 基本フィールドチェック
    for field in REQUIRED_BASIC_FIELDS:
        val = episode.get(field)
        if val is None or str(val).strip() == "":
            missing.append(field)

    # 7軸スコアチェック
    for field in REQUIRED_SCORE_FIELDS:
        val = episode.get(field)
        if val is None or str(val).strip() == "":
            missing.append(field)
        else:
            try:
                score = float(val)
                if score < 1 or score > 10:
                    invalid.append(f"{field}={score} (1-10の範囲外)")
            except (ValueError, TypeError):
                invalid.append(f"{field}={val} (数値変換エラー)")

    # エピソードタイプチェック
    ep_type = episode.get("episode_type", "")
    if ep_type and ep_type not in VALID_EPISODE_TYPES:
        invalid.append(f"episode_type={ep_type} (無効)")

    # 年齢チェック
    age = episode.get("age")
    person_type = episode.get("person_type", "")
    if age is not None:
        try:
            age_val = float(age)
            # FICTIONALでない場合は150歳まで
            if person_type != "FICTIONAL" and age_val > 150:
                invalid.append(f"age={age_val} (150歳超過・非FICTIONAL)")
        except (ValueError, TypeError):
            invalid.append(f"age={age} (数値変換エラー)")

    # テキスト最小長チェック
    text = episode.get("episode_text", "")
    if len(text) < 50:
        invalid.append(f"episode_text={len(text)}文字 (最小50文字)")

    passed = len(missing) == 0 and len(invalid) == 0

    if passed:
        message = "✅ 完全性チェック合格"
    else:
        parts = []
        if missing:
            parts.append(f"欠損: {', '.join(missing)}")
        if invalid:
            parts.append(f"無効: {', '.join(invalid)}")
        message = f"❌ 完全性チェック不合格: {'; '.join(parts)}"

    return CompletenessCheckResult(
        passed=passed,
        missing_fields=missing,
        invalid_fields=invalid,
        message=message,
    )


def quick_completeness_check(episode: dict) -> bool:
    """簡易完全性チェック（True/Falseのみ）"""
    return check_completeness(episode).passed
