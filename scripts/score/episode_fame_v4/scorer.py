"""
Episode Fame Score v4 計算ロジック

LLM 7軸評価スコアを統合したエピソード有名度スコア計算
"""

from dataclasses import dataclass, field
from typing import Optional

from .config import (
    WEIGHTS,
    LLM_WEIGHTS,
    TYPE_BONUS,
    FACT_DENSITY_DEPENDENT_TYPES,
    HISTORICAL_KEYWORDS,
    KEYWORD_BONUS_VALUES,
    KEYWORD_BONUS_MAX,
    PERSONAL_KEYWORDS,
    LOW_IMPORTANCE_KEYWORDS,
    PERSONAL_PENALTY_MAX,
    LOW_IMPORTANCE_PENALTY_MAX,
    TIER_THRESHOLDS,
    PERSON_FAME_MAX,
)


@dataclass
class EpisodeFameSignals:
    """v4スコア計算用のシグナル"""

    # LLM 7軸スコア（0-10スケール）
    llm_memorability: float = 0.0
    llm_empathy: float = 0.0
    llm_surprise: float = 0.0
    llm_generation_quality: float = 0.0
    llm_educational_value: float = 0.0
    llm_storytelling_quality: float = 0.0
    llm_factual_density: float = 0.0

    # エピソード情報
    episode_text: str = ""
    episode_type: str = ""

    # 人物知名度（celebrity_score_v2: 0-1000）
    person_fame_score: float = 0.0

    # オプション
    category: str = ""


@dataclass
class EpisodeFameResult:
    """v4スコア計算結果"""

    score: float  # 0-100
    tier: int  # 1-5
    components: dict = field(default_factory=dict)  # 詳細内訳
    reason: str = ""  # 人間可読な説明


def calculate_tier(score: float) -> int:
    """スコアからティアを計算"""
    for tier, threshold in sorted(TIER_THRESHOLDS.items(), reverse=True):
        if score >= threshold:
            return tier
    return 1


def calculate_llm_component(signals: EpisodeFameSignals) -> float:
    """
    LLM 7軸スコアから統合スコアを計算

    入力: 0-10スケールの各軸スコア
    出力: 0-100スケールの統合スコア
    """
    llm_scores = {
        "memorability": signals.llm_memorability,
        "empathy": signals.llm_empathy,
        "surprise": signals.llm_surprise,
        "generation_quality": signals.llm_generation_quality,
        "educational_value": signals.llm_educational_value,
        "storytelling_quality": signals.llm_storytelling_quality,
        "factual_density": signals.llm_factual_density,
    }

    # 重み付き合計
    weighted_sum = sum(score * LLM_WEIGHTS.get(key, 0) for key, score in llm_scores.items())

    # 0-10を0-100に正規化
    return weighted_sum * 10.0


def calculate_keyword_component(episode_text: str) -> tuple[float, list[str]]:
    """
    歴史的キーワードからボーナスを計算

    Returns:
        tuple: (スコア 0-100, マッチしたキーワードリスト)
    """
    matched_keywords = []
    bonus = 0.0

    for kw in HISTORICAL_KEYWORDS:
        if kw in episode_text:
            matched_keywords.append(kw)
            # キーワード固有の値があればそれを使用、なければ5点
            bonus += KEYWORD_BONUS_VALUES.get(kw, 5)

    # 上限適用
    bonus = min(bonus, KEYWORD_BONUS_MAX)

    # ペナルティ計算
    personal_count = sum(1 for kw in PERSONAL_KEYWORDS if kw in episode_text)
    personal_penalty = min(personal_count * 5, PERSONAL_PENALTY_MAX)

    low_count = sum(1 for kw in LOW_IMPORTANCE_KEYWORDS if kw in episode_text)
    low_penalty = min(low_count * 3, LOW_IMPORTANCE_PENALTY_MAX)

    # 基準50点にボーナス/ペナルティ適用
    base_score = 50.0
    score = base_score + bonus - personal_penalty - low_penalty

    # 0-100にクランプ
    score = max(0.0, min(100.0, score))

    return score, matched_keywords


def calculate_type_component(episode_type: str, factual_density: float = 0.0) -> float:
    """
    エピソードタイプからボーナスを計算

    Returns:
        スコア 0-100
    """
    base_score = 50.0

    episode_type_upper = episode_type.strip().upper()
    type_bonus = TYPE_BONUS.get(episode_type_upper, 0)

    # 事実密度依存タイプの場合、事実密度で補正
    if episode_type_upper in FACT_DENSITY_DEPENDENT_TYPES:
        if factual_density >= 5.0:
            multiplier = 1.0
        else:
            # 事実密度が低い場合は効果減衰（最低0.77）
            multiplier = max(0.77, factual_density / 5.0)
        type_bonus = type_bonus * multiplier

    return base_score + type_bonus


def calculate_person_component(person_fame_score: float) -> float:
    """
    人物知名度からスコアを計算

    入力: celebrity_score_v2 (0-1000)
    出力: 0-100
    """
    # 0-1000を0-100に正規化
    normalized = (person_fame_score / PERSON_FAME_MAX) * 100.0
    return min(100.0, max(0.0, normalized))


def calculate_episode_fame_v4(
    signals: EpisodeFameSignals,
    episode_id: str = "",
) -> EpisodeFameResult:
    """
    Episode Fame Score v4を計算

    計算式:
        score = LLM(45%) + キーワード(25%) + タイプ(15%) + 人物知名度(15%)

    Args:
        signals: 計算に必要なシグナル
        episode_id: エピソードID（ログ用）

    Returns:
        EpisodeFameResult: スコア、ティア、内訳、理由
    """
    # 1. LLMコンポーネント（45%）
    llm_score = calculate_llm_component(signals)

    # 2. キーワードコンポーネント（25%）
    keyword_score, matched_keywords = calculate_keyword_component(signals.episode_text)

    # 3. タイプコンポーネント（15%）
    type_score = calculate_type_component(signals.episode_type, signals.llm_factual_density)

    # 4. 人物知名度コンポーネント（15%）
    person_score = calculate_person_component(signals.person_fame_score)

    # 重み付き合計
    raw_score = (
        llm_score * WEIGHTS["llm"]
        + keyword_score * WEIGHTS["keyword"]
        + type_score * WEIGHTS["type"]
        + person_score * WEIGHTS["person_fame"]
    )

    # 0-100にクランプ
    final_score = max(0.0, min(100.0, raw_score))

    # ティア計算
    tier = calculate_tier(final_score)

    # 内訳
    components = {
        "llm": round(llm_score, 2),
        "llm_weighted": round(llm_score * WEIGHTS["llm"], 2),
        "keyword": round(keyword_score, 2),
        "keyword_weighted": round(keyword_score * WEIGHTS["keyword"], 2),
        "type": round(type_score, 2),
        "type_weighted": round(type_score * WEIGHTS["type"], 2),
        "person": round(person_score, 2),
        "person_weighted": round(person_score * WEIGHTS["person_fame"], 2),
        "matched_keywords": matched_keywords[:5],  # 上位5件のみ
    }

    # 理由文生成
    reason_parts = []
    if llm_score > 60:
        reason_parts.append(f"LLM高評価({llm_score:.0f})")
    if matched_keywords:
        reason_parts.append(f"キーワード:{','.join(matched_keywords[:3])}")
    if signals.episode_type:
        reason_parts.append(f"タイプ:{signals.episode_type}")
    if person_score > 50:
        reason_parts.append(f"有名人({person_score:.0f})")

    reason = "; ".join(reason_parts) if reason_parts else "標準評価"

    return EpisodeFameResult(
        score=round(final_score, 2),
        tier=tier,
        components=components,
        reason=reason,
    )
