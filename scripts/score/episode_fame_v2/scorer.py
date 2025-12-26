"""
Episode Fame Score v2 統合スコアラー

感銘重視のエピソードランキングを生成
"""

from typing import Optional

from .config import (
    HISTORICAL_BONUS_MAX,
    HISTORICAL_IMPACT_KEYWORDS,
    MAX_SAME_PERSON_IN_TOP_N,
    PERSON_FAME_MAX,
    TIER_THRESHOLDS,
    WEIGHTS,
)
from .inspiration_scorer import calculate_inspiration_score
from .quality_gate import calculate_quality_score


def calculate_historical_impact(text: str) -> dict:
    """
    歴史的インパクトスコアを計算

    Args:
        text: エピソード本文

    Returns:
        {
            "total": 0-100のスコア,
            "matched": {カテゴリ: マッチしたキーワード}
        }
    """
    if not text:
        return {"total": 0.0, "matched": {}}

    total_bonus = 0.0
    matched = {}

    for category, data in HISTORICAL_IMPACT_KEYWORDS.items():
        keywords = data["keywords"]
        bonus = data["bonus"]

        matched_kws = [kw for kw in keywords if kw in text]
        if matched_kws:
            total_bonus += bonus
            matched[category] = matched_kws

    # 上限適用
    total_bonus = min(total_bonus, HISTORICAL_BONUS_MAX)

    # 0-30を0-100にスケール
    scaled_score = (total_bonus / HISTORICAL_BONUS_MAX) * 100

    return {
        "total": round(scaled_score, 2),
        "matched": matched,
        "raw_bonus": round(total_bonus, 2),
    }


def calculate_person_fame_score(celebrity_score: float) -> float:
    """
    人物知名度スコアを正規化（0-100）

    Args:
        celebrity_score: celebrity_score_v2値（0-1000）

    Returns:
        0-100のスコア
    """
    if celebrity_score is None or celebrity_score <= 0:
        return 0.0

    # 0-1000を0-100に正規化
    normalized = (celebrity_score / PERSON_FAME_MAX) * 100
    return min(100.0, normalized)


def calculate_episode_fame_v2(
    text: str,
    llm_scores: dict,
    celebrity_score: float,
    episode_age: Optional[int] = None,
    birth_year: Optional[int] = None,
    death_year: Optional[int] = None,
    person_name: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    """
    Episode Fame Score v2を計算

    Args:
        text: エピソード本文
        llm_scores: LLM 7軸スコア
        celebrity_score: 人物知名度（celebrity_score_v2）
        episode_age: エピソードの年齢
        birth_year: 誕生年
        death_year: 死亡年
        person_name: 人物名
        category: カテゴリ

    Returns:
        {
            "total": 0-100の最終スコア,
            "tier": 1-5のティア,
            "components": {各コンポーネントのスコア},
            "exclude": 除外フラグ,
            "details": 詳細情報
        }
    """
    # 1. InspirationScore（感銘度）
    inspiration = calculate_inspiration_score(text, person_name, category)
    inspiration_score = inspiration["total"]

    # 2. QualityScore（品質）
    quality = calculate_quality_score(
        llm_scores=llm_scores,
        text=text,
        episode_age=episode_age,
        birth_year=birth_year,
        death_year=death_year,
    )
    quality_score = quality["total"]

    # 3. HistoricalImpact（歴史的インパクト）
    historical = calculate_historical_impact(text)
    historical_score = historical["total"]

    # 4. PersonFame（人物知名度）
    person_fame_score = calculate_person_fame_score(celebrity_score)

    # 除外チェック
    exclude = quality["exclude"]

    if exclude:
        total_score = 0.0
    else:
        # 重み付け合計
        total_score = (
            inspiration_score * WEIGHTS["inspiration"]
            + quality_score * WEIGHTS["quality"]
            + historical_score * WEIGHTS["historical"]
            + person_fame_score * WEIGHTS["person_fame"]
        )

    # ティア判定
    tier = get_tier(total_score)

    return {
        "total": round(total_score, 2),
        "tier": tier,
        "exclude": exclude,
        "components": {
            "inspiration": round(inspiration_score, 2),
            "quality": round(quality_score, 2),
            "historical": round(historical_score, 2),
            "person_fame": round(person_fame_score, 2),
        },
        "weights": WEIGHTS,
        "details": {
            "inspiration": inspiration,
            "quality": quality,
            "historical": historical,
        },
    }


def get_tier(score: float) -> int:
    """
    スコアからティアを判定

    Args:
        score: 0-100のスコア

    Returns:
        1-5のティア
    """
    for tier, threshold in sorted(TIER_THRESHOLDS.items(), reverse=True):
        if score >= threshold:
            return tier
    return 1


def apply_bias_control(episodes: list, top_n: int = 100) -> list:
    """
    偏り制御（同一人物独占防止）を適用

    Args:
        episodes: スコア付きエピソードのリスト（score降順ソート済み）
        top_n: 対象とするトップN

    Returns:
        偏り制御後のエピソードリスト
    """
    if not episodes:
        return []

    # person_idごとのカウント
    person_counts = {}
    result = []

    for ep in episodes:
        person_id = ep.get("person_id", "")
        current_rank = len(result) + 1

        if current_rank > top_n:
            # top_n以降は全て追加
            result.append(ep)
            continue

        # 現在のランクに対する制限を確認
        max_allowed = MAX_SAME_PERSON_IN_TOP_N.get(top_n, 3)
        for limit_n, limit_count in sorted(MAX_SAME_PERSON_IN_TOP_N.items()):
            if current_rank <= limit_n:
                max_allowed = min(max_allowed, limit_count)

        # 同一人物のカウント確認
        current_count = person_counts.get(person_id, 0)

        if current_count < max_allowed:
            result.append(ep)
            person_counts[person_id] = current_count + 1
        else:
            # 除外（bias_excludedフラグを設定）
            ep["bias_excluded"] = True
            ep["bias_reason"] = f"Same person limit ({max_allowed}) reached at rank {current_rank}"
            result.append(ep)

    return result


def rank_episodes(episodes: list, apply_bias: bool = True) -> list:
    """
    エピソードをランキング

    Args:
        episodes: episode_fame_v2計算済みのエピソードリスト
        apply_bias: 偏り制御を適用するか

    Returns:
        ランキングされたエピソードリスト
    """
    # 除外フラグがないものだけでソート
    active = [ep for ep in episodes if not ep.get("exclude", False)]
    excluded = [ep for ep in episodes if ep.get("exclude", False)]

    # スコア降順ソート
    active.sort(key=lambda x: x.get("episode_fame_v2", 0), reverse=True)

    if apply_bias:
        active = apply_bias_control(active)

    # ランク付け
    rank = 1
    for ep in active:
        if not ep.get("bias_excluded", False):
            ep["rank_v2"] = rank
            rank += 1
        else:
            ep["rank_v2"] = None

    return active + excluded
