"""
Completeness Gate - 必須フィールド完全性チェック + 派生フィールド自動補完

EPUP再発防止: エピソード追加前に全必須フィールドの充填を検証。

RCA-20260106: 年代・5軸スコア欠損問題の再発防止
- 年代: ageから自動計算
- 総合品質: (記憶性 + 生成品質) / 2
- 感情インパクト: (共感性 + 意外性) / 2
- composite_score_5axis: 5軸平均

RCA-20260110: SAGE Turbo欠損補完ミッション追加
- episode_type: テキストから自動推定
- fame_tier: fame_score_v3から算出
- episode_fame_v6: 簡易計算
- verification_status: 初期値設定
- generation_timestamp: 表示形式設定
"""

from dataclasses import dataclass
from datetime import datetime

# 必須フィールド（7軸スコア）
REQUIRED_SCORE_FIELDS = [
    "memorability_score",
    "empathy_score",
    "surprise_score",
    "generation_quality_score",
    "educational_value",
    "story_quality",
    "factual_density",
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
    mem = float(filled.get("memorability_score", 0) or 0)
    gen = float(filled.get("generation_quality_score", 0) or 0)
    emp = float(filled.get("empathy_score", 0) or 0)
    sur = float(filled.get("surprise_score", 0) or 0)
    edu = float(filled.get("educational_value", 0) or 0)
    story = float(filled.get("story_quality", 0) or 0)
    fact = float(filled.get("factual_density", 0) or 0)

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


# =============================================================================
# RCA-20260110: SAGE Turbo欠損補完ミッション追加関数
# =============================================================================

# fame_tier計算閾値（fame_score_v3ベース）
FAME_TIER_THRESHOLDS = {
    5: 800,  # Tier 5: 800+
    4: 600,  # Tier 4: 600-799
    3: 400,  # Tier 3: 400-599
    2: 200,  # Tier 2: 200-399
    1: 0,  # Tier 1: 0-199
}


def fill_episode_type(episode: dict) -> dict:
    """
    episode_typeをテキストから推定して補完

    Args:
        episode: エピソードデータ

    Returns:
        補完後のエピソードデータ
    """
    from .episode_type_inferrer import infer_episode_type

    filled = episode.copy()
    ep_type = filled.get("episode_type", "")

    if not ep_type or str(ep_type).strip() == "":
        episode_text = str(filled.get("episode_text", ""))
        result = infer_episode_type(episode_text)
        if result.episode_type:
            filled["episode_type"] = result.episode_type

    return filled


def fill_fame_tier(episode: dict) -> dict:
    """
    fame_tierをfame_score_v3から算出

    Args:
        episode: エピソードデータ

    Returns:
        補完後のエピソードデータ
    """
    filled = episode.copy()
    fame_tier = filled.get("fame_tier")

    # 既に設定済みならスキップ
    if fame_tier and fame_tier not in (0, "", "0"):
        return filled

    # fame_score_v3から計算
    fame_score = filled.get("fame_score_v3")
    if not fame_score:
        return filled

    try:
        score = float(fame_score)
        tier = 1
        for t, threshold in FAME_TIER_THRESHOLDS.items():
            if score >= threshold:
                tier = t
                break
        filled["fame_tier"] = tier
    except (ValueError, TypeError):
        pass

    return filled


def fill_episode_fame_v6(episode: dict) -> dict:
    """
    episode_fame_v6を簡易計算で補完

    Note: 完全なv6計算は別途スクリプトで行う。
    ここでは7軸スコアの加重平均を基に推定値を設定。

    Args:
        episode: エピソードデータ

    Returns:
        補完後のエピソードデータ
    """
    filled = episode.copy()
    v6 = filled.get("episode_fame_v6")

    # 既に設定済みならスキップ
    if v6 and v6 not in (0, "", "0", 0.0):
        return filled

    # 7軸スコアから計算
    score_cols = [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]

    scores = []
    for col in score_cols:
        val = filled.get(col)
        if val and val not in (0, "", "0"):
            try:
                scores.append(float(val))
            except (ValueError, TypeError):
                pass

    if not scores:
        return filled

    # 簡易v6計算: (7軸平均 * 10)
    avg_score = sum(scores) / len(scores)
    v6_estimate = avg_score * 10

    # fame_score_v3ボーナス
    fame_score = filled.get("fame_score_v3")
    if fame_score:
        try:
            fame_bonus = min(float(fame_score) / 50, 20)
            v6_estimate += fame_bonus
        except (ValueError, TypeError):
            pass

    filled["episode_fame_v6"] = round(v6_estimate, 2)

    # episode_fame_scoreも同期
    filled["episode_fame_score"] = round(v6_estimate, 2)

    # episode_fame_tier_v6も設定
    tier_v6 = 1
    if v6_estimate >= 80:
        tier_v6 = 5
    elif v6_estimate >= 60:
        tier_v6 = 4
    elif v6_estimate >= 40:
        tier_v6 = 3
    elif v6_estimate >= 20:
        tier_v6 = 2
    filled["episode_fame_tier_v6"] = tier_v6

    return filled


def fill_verification_status(episode: dict) -> dict:
    """
    verification_statusを初期値設定

    Args:
        episode: エピソードデータ

    Returns:
        補完後のエピソードデータ
    """
    filled = episode.copy()
    status = filled.get("verification_status", "")

    if not status or str(status).strip() == "":
        filled["verification_status"] = "unverified"

    return filled


def fill_generation_timestamp(episode: dict) -> dict:
    """
    generation_timestampを表示形式（YYYY.MM.DD）で設定

    Args:
        episode: エピソードデータ

    Returns:
        補完後のエピソードデータ
    """
    filled = episode.copy()
    ts = filled.get("generation_timestamp", "")

    if not ts or str(ts).strip() == "":
        # generated_atから変換
        generated_at = filled.get("generated_at", "")
        if generated_at:
            try:
                dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
                filled["generation_timestamp"] = dt.strftime("%Y.%m.%d")
            except (ValueError, TypeError):
                filled["generation_timestamp"] = datetime.now().strftime("%Y.%m.%d")
        else:
            filled["generation_timestamp"] = datetime.now().strftime("%Y.%m.%d")

    return filled


def auto_fill_all_derived_fields(episode: dict) -> dict:
    """
    全派生フィールドを自動補完（拡張版）

    補完対象:
    - 既存: 年代、総合品質、感情インパクト、composite_score_5axis
    - 追加: episode_type, fame_tier, episode_fame_v6, verification_status, generation_timestamp

    Args:
        episode: エピソードデータ

    Returns:
        補完後のエピソードデータ
    """
    filled = episode.copy()

    # 既存の派生フィールド補完
    filled = auto_fill_derived_fields(filled)

    # 新規追加の補完
    filled = fill_episode_type(filled)
    filled = fill_fame_tier(filled)
    filled = fill_episode_fame_v6(filled)
    filled = fill_verification_status(filled)
    filled = fill_generation_timestamp(filled)

    return filled


def check_completeness_extended(episode: dict, auto_fill: bool = True) -> CompletenessCheckResult:
    """
    拡張版完全性チェック（全派生フィールドを自動補完してからチェック）

    Args:
        episode: エピソードデータ
        auto_fill: Trueの場合、全派生フィールドを自動補完してから検証

    Returns:
        CompletenessCheckResult
    """
    if auto_fill:
        episode = auto_fill_all_derived_fields(episode)

    return check_completeness(episode, auto_fill=False)
