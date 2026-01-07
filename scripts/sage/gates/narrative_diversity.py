"""
Narrative Diversity - Phase 6

ストーリータイプ多様性、時代別テーマバランス。
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ==============================================================================
# ストーリータイプ定義
# ==============================================================================


class StoryType(Enum):
    """ストーリータイプ分類"""

    TURNING_POINT = "turning_point"  # 転機
    REDISCOVERY = "rediscovery"  # 再発見
    CONFLICT = "conflict"  # 対立
    COOPERATION = "cooperation"  # 協力
    SUCCESS = "success"  # 成功
    FAILURE = "failure"  # 失敗
    GROWTH = "growth"  # 成長
    CHALLENGE = "challenge"  # 挑戦
    UNKNOWN = "unknown"  # 不明


class EraTheme(Enum):
    """時代別テーマ"""

    ANCIENT = "ancient"  # 古代（統治、神話）
    MEDIEVAL = "medieval"  # 中世（戦争、宗教）
    MODERN = "modern"  # 近代（革命、産業）
    CONTEMPORARY = "contemporary"  # 現代（イノベーション、グローバル）


# ==============================================================================
# データクラス
# ==============================================================================


@dataclass
class StoryClassificationResult:
    """ストーリー分類結果"""

    story_type: StoryType
    confidence: float  # 0.0-1.0
    matched_keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_type": self.story_type.value,
            "confidence": self.confidence,
            "matched_keywords": self.matched_keywords,
        }


@dataclass
class NarrativeBalanceResult:
    """物語バランス結果"""

    is_balanced: bool
    story_type_distribution: dict[str, int] = field(default_factory=dict)
    era_theme_distribution: dict[str, int] = field(default_factory=dict)
    gini_coefficient: float = 0.0
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_balanced": self.is_balanced,
            "story_type_distribution": self.story_type_distribution,
            "era_theme_distribution": self.era_theme_distribution,
            "gini_coefficient": self.gini_coefficient,
            "recommendations": self.recommendations,
        }


# ==============================================================================
# StoryTypeClassifier
# ==============================================================================


class StoryTypeClassifier:
    """
    ストーリータイプ分類器

    エピソードテキストからストーリータイプを判定。
    """

    # ストーリータイプ別キーワード
    STORY_TYPE_KEYWORDS = {
        StoryType.TURNING_POINT: [
            r"転機",
            r"人生を変えた",
            r"決断",
            r"方向転換",
            r"新たな道",
            r"岐路",
        ],
        StoryType.REDISCOVERY: [
            r"再発見",
            r"原点回帰",
            r"再出発",
            r"復活",
            r"再び",
            r"戻った",
        ],
        StoryType.CONFLICT: [
            r"対立",
            r"反発",
            r"批判",
            r"争い",
            r"衝突",
            r"論争",
            r"対決",
        ],
        StoryType.COOPERATION: [
            r"協力",
            r"共同",
            r"コラボ",
            r"提携",
            r"パートナー",
            r"チーム",
        ],
        StoryType.SUCCESS: [
            r"成功",
            r"達成",
            r"受賞",
            r"優勝",
            r"1位",
            r"トップ",
            r"栄冠",
            r"金メダル",
        ],
        StoryType.FAILURE: [
            r"失敗",
            r"挫折",
            r"敗北",
            r"落選",
            r"不合格",
            r"倒産",
            r"解散",
        ],
        StoryType.GROWTH: [
            r"成長",
            r"学び",
            r"克服",
            r"乗り越え",
            r"進化",
            r"向上",
        ],
        StoryType.CHALLENGE: [
            r"挑戦",
            r"チャレンジ",
            r"初めて",
            r"新規",
            r"開拓",
            r"冒険",
        ],
    }

    def classify(self, text: str) -> StoryClassificationResult:
        """
        テキストからストーリータイプを分類

        Args:
            text: エピソードテキスト

        Returns:
            StoryClassificationResult
        """
        scores: dict[StoryType, tuple[int, list[str]]] = {}

        for story_type, keywords in self.STORY_TYPE_KEYWORDS.items():
            matched = []
            for keyword in keywords:
                if re.search(keyword, text):
                    matched.append(keyword)

            if matched:
                scores[story_type] = (len(matched), matched)

        if not scores:
            return StoryClassificationResult(
                story_type=StoryType.UNKNOWN,
                confidence=0.0,
                matched_keywords=[],
            )

        # 最高スコアのタイプを選択
        best_type = max(scores.keys(), key=lambda t: scores[t][0])
        count, matched = scores[best_type]

        # 信頼度計算（マッチ数 / 最大キーワード数）
        max_keywords = len(self.STORY_TYPE_KEYWORDS[best_type])
        confidence = min(count / max_keywords, 1.0)

        return StoryClassificationResult(
            story_type=best_type,
            confidence=confidence,
            matched_keywords=matched,
        )

    def classify_batch(self, texts: list[str]) -> list[StoryClassificationResult]:
        """バッチ分類"""
        return [self.classify(text) for text in texts]


# ==============================================================================
# EraThemeClassifier
# ==============================================================================


class EraThemeClassifier:
    """
    時代別テーマ分類器
    """

    # 時代別キーワード
    ERA_KEYWORDS = {
        EraTheme.ANCIENT: [
            r"古代",
            r"紀元前",
            r"帝国",
            r"王朝",
            r"神話",
            r"神殿",
        ],
        EraTheme.MEDIEVAL: [
            r"中世",
            r"封建",
            r"騎士",
            r"城",
            r"宗教",
            r"十字軍",
        ],
        EraTheme.MODERN: [
            r"近代",
            r"革命",
            r"産業",
            r"植民地",
            r"明治|大正|昭和",
        ],
        EraTheme.CONTEMPORARY: [
            r"現代",
            r"21世紀",
            r"デジタル",
            r"インターネット",
            r"グローバル",
            r"AI",
        ],
    }

    # 年号による時代推定
    YEAR_RANGES = {
        EraTheme.ANCIENT: (None, 500),
        EraTheme.MEDIEVAL: (500, 1500),
        EraTheme.MODERN: (1500, 1950),
        EraTheme.CONTEMPORARY: (1950, None),
    }

    def classify(self, text: str, birth_year: Optional[int] = None) -> EraTheme:
        """
        テキストから時代テーマを分類

        Args:
            text: エピソードテキスト
            birth_year: 人物の生年（オプション）

        Returns:
            EraTheme
        """
        # 生年からの推定
        if birth_year:
            for era, (start, end) in self.YEAR_RANGES.items():
                if start and birth_year < start:
                    continue
                if end and birth_year >= end:
                    continue
                return era

        # キーワードによる推定
        for era, keywords in self.ERA_KEYWORDS.items():
            for keyword in keywords:
                if re.search(keyword, text):
                    return era

        return EraTheme.CONTEMPORARY  # デフォルト


# ==============================================================================
# NarrativeBalancer
# ==============================================================================


class NarrativeBalancer:
    """
    物語バランス管理

    ストーリータイプとテーマの均衡を監視。
    """

    # 目標分布
    TARGET_STORY_DISTRIBUTION = {
        StoryType.SUCCESS: 0.20,
        StoryType.CHALLENGE: 0.15,
        StoryType.TURNING_POINT: 0.15,
        StoryType.GROWTH: 0.15,
        StoryType.FAILURE: 0.10,
        StoryType.CONFLICT: 0.10,
        StoryType.COOPERATION: 0.08,
        StoryType.REDISCOVERY: 0.07,
    }

    # 許容Gini係数
    MAX_GINI = 0.35

    def __init__(self):
        self.story_classifier = StoryTypeClassifier()
        self.era_classifier = EraThemeClassifier()

    def calculate_gini(self, counts: list[int]) -> float:
        """Gini係数計算"""
        if not counts or sum(counts) == 0:
            return 0.0

        n = len(counts)
        sorted_counts = sorted(counts)
        total = sum(counts)

        numerator = sum((i + 1) * c for i, c in enumerate(sorted_counts))
        denominator = n * total

        gini = (2 * numerator - n - 1) / (n - 1) if n > 1 else 0
        return max(0, 1 - gini / n)

    def analyze_distribution(
        self,
        episodes: list[dict],
    ) -> NarrativeBalanceResult:
        """
        分布分析

        Args:
            episodes: エピソードリスト [{"text": str, "birth_year": int}, ...]

        Returns:
            NarrativeBalanceResult
        """
        # ストーリータイプ集計
        story_counts: Counter = Counter()
        era_counts: Counter = Counter()

        for ep in episodes:
            text = ep.get("text", "")
            birth_year = ep.get("birth_year")

            # ストーリータイプ分類
            story_result = self.story_classifier.classify(text)
            story_counts[story_result.story_type.value] += 1

            # 時代テーマ分類
            era = self.era_classifier.classify(text, birth_year)
            era_counts[era.value] += 1

        # Gini係数計算
        story_values = list(story_counts.values())
        gini = self.calculate_gini(story_values) if story_values else 0.0

        # バランス判定
        is_balanced = gini <= self.MAX_GINI

        # 推奨事項
        recommendations = []
        total = sum(story_counts.values())
        if total > 0:
            for story_type, target_ratio in self.TARGET_STORY_DISTRIBUTION.items():
                current_ratio = story_counts.get(story_type.value, 0) / total
                if current_ratio < target_ratio * 0.5:
                    recommendations.append(f"「{story_type.value}」タイプのエピソードを増やす")

        return NarrativeBalanceResult(
            is_balanced=is_balanced,
            story_type_distribution=dict(story_counts),
            era_theme_distribution=dict(era_counts),
            gini_coefficient=gini,
            recommendations=recommendations,
        )

    def suggest_story_type(
        self,
        current_distribution: dict[str, int],
    ) -> StoryType:
        """
        次に生成すべきストーリータイプを提案

        Args:
            current_distribution: 現在の分布

        Returns:
            StoryType: 推奨タイプ
        """
        total = sum(current_distribution.values()) or 1

        # 不足しているタイプを特定
        gaps = []
        for story_type, target_ratio in self.TARGET_STORY_DISTRIBUTION.items():
            current_count = current_distribution.get(story_type.value, 0)
            current_ratio = current_count / total
            gap = target_ratio - current_ratio
            if gap > 0:
                gaps.append((story_type, gap))

        if gaps:
            # 最も不足しているタイプを返す
            return max(gaps, key=lambda x: x[1])[0]

        return StoryType.SUCCESS  # デフォルト


# ==============================================================================
# 便利関数
# ==============================================================================


def classify_story(text: str) -> StoryClassificationResult:
    """ストーリータイプ分類（便利関数）"""
    classifier = StoryTypeClassifier()
    return classifier.classify(text)


def analyze_narrative_balance(episodes: list[dict]) -> NarrativeBalanceResult:
    """物語バランス分析（便利関数）"""
    balancer = NarrativeBalancer()
    return balancer.analyze_distribution(episodes)


if __name__ == "__main__":
    print("=== Narrative Diversity Test ===")

    # 1. ストーリータイプ分類テスト
    print("\n1. ストーリータイプ分類テスト")
    classifier = StoryTypeClassifier()

    test_texts = [
        "人生の転機となる決断を下した",
        "挑戦を続け、ついに成功を収めた",
        "失敗から多くを学んだ",
        "チームとの協力で大きな成果を上げた",
        "批判を受けながらも信念を貫いた",
    ]

    for text in test_texts:
        result = classifier.classify(text)
        print(f"  '{text[:20]}...' -> {result.story_type.value} ({result.confidence:.2f})")

    # 2. 時代テーマ分類テスト
    print("\n2. 時代テーマ分類テスト")
    era_classifier = EraThemeClassifier()

    test_cases = [
        ("古代ローマ帝国の時代", None),
        ("現代のデジタル社会", None),
        ("産業革命の時代", 1800),
    ]

    for text, year in test_cases:
        era = era_classifier.classify(text, year)
        print(f"  '{text}' -> {era.value}")

    # 3. 物語バランス分析テスト
    print("\n3. 物語バランス分析テスト")
    balancer = NarrativeBalancer()

    episodes = [
        {"text": "成功を収めた", "birth_year": 1980},
        {"text": "挑戦を続けた", "birth_year": 1985},
        {"text": "成功した", "birth_year": 1990},
        {"text": "転機を迎えた", "birth_year": 1975},
        {"text": "失敗から学んだ", "birth_year": 1982},
    ]

    result = balancer.analyze_distribution(episodes)
    print(f"  バランス: {result.is_balanced}")
    print(f"  Gini係数: {result.gini_coefficient:.3f}")
    print(f"  ストーリー分布: {result.story_type_distribution}")
    print(f"  推奨: {result.recommendations[:2]}")

    print("\n=== テスト完了 ===")
