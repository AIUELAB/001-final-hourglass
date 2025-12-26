"""
InspirationScore（感銘度）スコアラー

エピソード本文から「困難→努力/決断→結果」パターンを検出し、
感銘度を0-100でスコアリング
"""

import re
from typing import Optional

from .config import (
    INSPIRATION_AXES,
    INSPIRATION_KEYWORDS,
    KEYWORD_BASE_SCORE,
    KEYWORD_MAX_SCORE,
)


def calculate_axis_score(text: str, axis: str) -> float:
    """
    1軸のスコアを計算（0-10）

    Args:
        text: エピソード本文
        axis: 軸名（difficulty, effort, decision, achievement, social_impact）

    Returns:
        0-10のスコア
    """
    keywords = INSPIRATION_KEYWORDS.get(axis, [])
    if not keywords:
        return 0.0

    matched_count = 0
    matched_keywords = []

    for keyword in keywords:
        if keyword in text:
            matched_count += 1
            matched_keywords.append(keyword)

    if matched_count == 0:
        return 0.0

    # キーワードマッチ数に応じてスコア計算
    # 1つ: 3点、2つ: 5点、3つ以上: 6-8点
    if matched_count == 1:
        score = KEYWORD_BASE_SCORE
    elif matched_count == 2:
        score = 5.0
    elif matched_count == 3:
        score = 6.0
    else:
        score = min(KEYWORD_MAX_SCORE, 6.0 + (matched_count - 3) * 0.5)

    return score


def calculate_narrative_bonus(text: str) -> float:
    """
    ナラティブボーナス（困難→努力/決断→結果の流れがあるか）

    v2.1: 複合パターン対応・上限拡大

    Args:
        text: エピソード本文

    Returns:
        0-15のボーナス
    """
    bonus = 0.0

    # 困難系キーワードと達成系キーワードの両方がある場合
    has_difficulty = any(kw in text for kw in INSPIRATION_KEYWORDS["difficulty"])
    has_achievement = any(kw in text for kw in INSPIRATION_KEYWORDS["achievement"])
    has_effort = any(kw in text for kw in INSPIRATION_KEYWORDS["effort"])
    has_decision = any(kw in text for kw in INSPIRATION_KEYWORDS["decision"])
    has_social = any(kw in text for kw in INSPIRATION_KEYWORDS["social_impact"])

    # 困難→達成パターン（基本）
    if has_difficulty and has_achievement:
        bonus += 3.0

    # 困難→努力→達成パターン（v2.1: 2.0→3.0）
    if has_difficulty and has_effort and has_achievement:
        bonus += 3.0

    # 困難→決断→達成パターン（v2.1追加）
    if has_difficulty and has_decision and has_achievement:
        bonus += 2.0

    # 決断→達成パターン
    if has_decision and has_achievement:
        bonus += 1.0

    # 社会的影響→達成パターン（v2.1追加）
    if has_social and has_achievement:
        bonus += 2.0

    # 社会的影響と困難/努力/決断の組み合わせ
    if has_social and (has_difficulty or has_effort or has_decision):
        bonus += 2.0

    # 完全ナラティブボーナス（v2.1追加: 5軸すべてマッチ）
    if all([has_difficulty, has_decision, has_effort, has_achievement, has_social]):
        bonus += 3.0

    return min(bonus, 15.0)  # v2.1: 上限10→15


def calculate_inspiration_score(
    text: str,
    person_name: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    """
    InspirationScore（感銘度）を計算

    Args:
        text: エピソード本文
        person_name: 人物名（オプション）
        category: カテゴリ（オプション）

    Returns:
        {
            "total": 0-100のトータルスコア,
            "axes": {各軸のスコア},
            "narrative_bonus": ナラティブボーナス,
            "details": {詳細情報}
        }
    """
    if not text:
        return {
            "total": 0.0,
            "axes": {axis: 0.0 for axis in INSPIRATION_AXES},
            "narrative_bonus": 0.0,
            "details": {"matched_keywords": {}},
        }

    # 各軸のスコア計算
    axes_scores = {}
    matched_keywords = {}

    for axis in INSPIRATION_AXES:
        score = calculate_axis_score(text, axis)
        axes_scores[axis] = score

        # マッチしたキーワードを記録
        keywords = INSPIRATION_KEYWORDS.get(axis, [])
        matched = [kw for kw in keywords if kw in text]
        if matched:
            matched_keywords[axis] = matched

    # ナラティブボーナス
    narrative_bonus = calculate_narrative_bonus(text)

    # 重み付け合計（0-50スケール → 0-100に正規化）
    weighted_sum = sum(axes_scores[axis] * weight for axis, weight in INSPIRATION_AXES.items())

    # 基本スコア（0-10 * weights合計=1.0 → 0-10）を0-100にスケール
    base_score = weighted_sum * 10

    # ナラティブボーナスを加算（最大10点）
    total_score = base_score + narrative_bonus

    # 0-100に収める
    total_score = max(0.0, min(100.0, total_score))

    return {
        "total": round(total_score, 2),
        "axes": {axis: round(score, 2) for axis, score in axes_scores.items()},
        "narrative_bonus": round(narrative_bonus, 2),
        "details": {
            "matched_keywords": matched_keywords,
            "base_score": round(base_score, 2),
        },
    }


def get_inspiration_tier(score: float) -> int:
    """
    InspirationScoreからティアを判定

    Args:
        score: 0-100のスコア

    Returns:
        1-5のティア
    """
    if score >= 80:
        return 5
    elif score >= 60:
        return 4
    elif score >= 40:
        return 3
    elif score >= 20:
        return 2
    else:
        return 1
