"""
Completeness Gate - 必須フィールド完全性チェック + 派生フィールド自動補完

EPUP再発防止: エピソード追加前に全必須フィールドの充填を検証。

RCA-20260106: 年代・5軸スコア欠損問題の再発防止
- 年代: ageから自動計算
- 総合品質: (記憶性 + 生成品質) / 2
- 感情インパクト: (共感性 + 意外性) / 2
- composite_score_5axis: 5軸平均
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


def age_to_nendai(age_str: str) -> str:
    """年齢から年代ラベルを生成（EPUP再発防止）"""
    try:
        age = float(age_str)
        if age >= 60:
            return "60歳以上"
        elif age >= 50:
            return "50代"
        elif age >= 40:
            return "40代"
        elif age >= 30:
            return "30代"
        elif age >= 20:
            return "20代"
        elif age >= 10:
            return "10代"
        elif age >= 1:
            return "幼少期"
        else:
            return ""
    except (ValueError, TypeError):
        return ""


def auto_fill_derived_fields(episode: dict) -> dict:
    """
    派生フィールドを自動補完（EPUP再発防止）

    補完対象:
    - 年代: ageから計算
    - 総合品質: (記憶性 + 生成品質) / 2
    - 感情インパクト: (共感性 + 意外性) / 2
    - composite_score_5axis: 5軸平均
    """
    filled = episode.copy()

    # 年代の補完
    if not filled.get("年代", "").strip() and filled.get("age", "").strip():
        filled["年代"] = age_to_nendai(str(filled["age"]))

    # 7軸スコアを取得
    mem = float(filled.get("記憶性スコア", 0) or 0)
    gen = float(filled.get("生成品質スコア", 0) or 0)
    emp = float(filled.get("共感性スコア", 0) or 0)
    sur = float(filled.get("意外性スコア", 0) or 0)
    edu = float(filled.get("教育的価値", 0) or 0)
    story = float(filled.get("ストーリー品質", 0) or 0)
    fact = float(filled.get("事実密度", 0) or 0)

    # 5軸スコアの補完
    if not str(filled.get("総合品質", "")).strip() and mem and gen:
        filled["総合品質"] = f"{(mem + gen) / 2:.2f}"

    if not str(filled.get("感情インパクト", "")).strip() and emp and sur:
        filled["感情インパクト"] = f"{(emp + sur) / 2:.2f}"

    # composite_score_5axisの補完
    if not str(filled.get("composite_score_5axis", "")).strip():
        overall = float(filled.get("総合品質", 0) or 0)
        emotional = float(filled.get("感情インパクト", 0) or 0)
        if overall and emotional and edu and story and fact:
            filled["composite_score_5axis"] = f"{(overall + emotional + edu + story + fact) / 5:.2f}"

    return filled


@dataclass
class CompletenessCheckResult:
    """完全性チェック結果"""

    passed: bool
    missing_fields: list[str]
    invalid_fields: list[str]
    message: str


def check_completeness(episode: dict, auto_fill: bool = True) -> CompletenessCheckResult:
    """
    エピソードの完全性をチェック

    Args:
        episode: エピソードデータ（dict）
        auto_fill: Trueの場合、派生フィールドを自動補完してから検証（デフォルト: True）

    Returns:
        CompletenessCheckResult
    """
    # 自動補完（デフォルトで有効）
    if auto_fill:
        episode = auto_fill_derived_fields(episode)

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


def quick_completeness_check(episode: dict, auto_fill: bool = True) -> bool:
    """簡易完全性チェック（True/Falseのみ）"""
    return check_completeness(episode, auto_fill=auto_fill).passed
