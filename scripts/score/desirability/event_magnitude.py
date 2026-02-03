"""
event_magnitude計算モジュール
エピソードの「何が起きたか」の重要度を計算

episode_fame_v6のhistorical_impact計算を参考にTier構造を採用。
キーワードマッチングによってイベントの歴史的・社会的重要度を評価する。
"""

from typing import Tuple

from .config import (
    TIER_S_KEYWORDS,
    TIER_A_KEYWORDS,
    TIER_B_KEYWORDS,
    TIER_C_KEYWORDS,
    TIER_MAGNITUDE,
)


def calculate_event_magnitude(episode_text: str) -> Tuple[float, str, list]:
    """
    エピソードテキストからevent_magnitudeを計算

    キーワードマッチングによってイベントの重要度を評価する。
    Tier S（歴史的）> Tier A（国際的）> Tier B（国内）> Tier C（一般）の
    階層構造で判定し、最も高いTierのmagnitude値を返す。

    Args:
        episode_text: エピソードのテキスト

    Returns:
        Tuple[magnitude, highest_tier, matched_keywords]
        - magnitude: 計算されたmagnitude値 (0-50)
        - highest_tier: マッチした最高Tier ("S", "A", "B", "C", "DEFAULT")
        - matched_keywords: マッチしたキーワードリスト

    Examples:
        >>> mag, tier, kws = calculate_event_magnitude("ノーベル物理学賞を受賞")
        >>> mag
        50
        >>> tier
        'S'
        >>> "ノーベル物理学賞" in kws
        True
    """
    if not episode_text:
        return TIER_MAGNITUDE["DEFAULT"], "DEFAULT", []

    matched: list[str] = []
    highest_tier = "DEFAULT"

    # Tier S チェック（最優先）
    for kw in TIER_S_KEYWORDS:
        if kw in episode_text:
            matched.append(kw)
            highest_tier = "S"

    # Tier A チェック
    for kw in TIER_A_KEYWORDS:
        if kw in episode_text:
            matched.append(kw)
            if highest_tier == "DEFAULT":
                highest_tier = "A"

    # Tier B チェック
    for kw in TIER_B_KEYWORDS:
        if kw in episode_text:
            matched.append(kw)
            if highest_tier in ["DEFAULT"]:
                highest_tier = "B"

    # Tier C チェック
    for kw in TIER_C_KEYWORDS:
        if kw in episode_text:
            matched.append(kw)
            if highest_tier == "DEFAULT":
                highest_tier = "C"

    magnitude = TIER_MAGNITUDE[highest_tier]

    # 複数キーワードマッチボーナス（最大+10）
    # 複数の重要キーワードが含まれる場合、より重要なイベントと判定
    if len(matched) >= 3:
        magnitude = min(50, magnitude + 5)
    elif len(matched) >= 2:
        magnitude = min(50, magnitude + 2)

    return magnitude, highest_tier, matched


def normalize_magnitude(magnitude: float, max_value: float = 50.0) -> float:
    """
    magnitudeを0-1に正規化

    Args:
        magnitude: 正規化前のmagnitude値
        max_value: magnitude最大値（デフォルト: 50.0）

    Returns:
        0-1に正規化されたmagnitude値

    Examples:
        >>> normalize_magnitude(50)
        1.0
        >>> normalize_magnitude(25)
        0.5
        >>> normalize_magnitude(0)
        0.0
    """
    if max_value <= 0:
        return 0.0
    return min(1.0, max(0.0, magnitude / max_value))


def get_magnitude_tier_description(tier: str) -> str:
    """
    Tier名に対応する説明を返す

    Args:
        tier: Tier名 ("S", "A", "B", "C", "DEFAULT")

    Returns:
        Tierの説明文字列
    """
    descriptions = {
        "S": "歴史的・世界的に最も重要な出来事",
        "A": "国際的に重要な出来事・受賞",
        "B": "国内・地域で重要な出来事",
        "C": "一般的な成果・出来事",
        "DEFAULT": "特定のキーワードマッチなし",
    }
    return descriptions.get(tier, "不明なTier")
