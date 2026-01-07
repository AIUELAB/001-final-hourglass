"""
Semantic Gaming Detector - Phase 6

セマンティック単調性検出、ペルソナハック検出、感情語彙偏り検出。
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


# ==============================================================================
# データクラス
# ==============================================================================


@dataclass
class SemanticGamingResult:
    """セマンティックゲーミング検出結果"""

    is_gaming: bool
    score: float  # 0.0-1.0 (高いほどゲーミング疑い)
    synonym_repetitions: list[str] = field(default_factory=list)
    structural_patterns: list[str] = field(default_factory=list)
    emotional_bias: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_gaming": self.is_gaming,
            "score": self.score,
            "synonym_repetitions": self.synonym_repetitions,
            "structural_patterns": self.structural_patterns,
            "emotional_bias": self.emotional_bias,
            "recommendations": self.recommendations,
        }


# ==============================================================================
# SynonymRepetitionDetector
# ==============================================================================


class SynonymRepetitionDetector:
    """
    同義語繰り返し検出

    同じ意味の言葉の繰り返しを検出。
    """

    # 同義語グループ
    SYNONYM_GROUPS = {
        "success": ["成功", "成し遂げ", "達成", "実現", "果た"],
        "challenge": ["挑戦", "チャレンジ", "試み", "トライ"],
        "important": ["重要", "大切", "大事", "肝心"],
        "great": ["偉大", "素晴らしい", "すばらしい", "すごい", "立派"],
        "famous": ["有名", "著名", "知られ", "名高い"],
        "change": ["変化", "変わ", "転換", "移行"],
        "new": ["新しい", "新たな", "斬新", "革新"],
        "first": ["初めて", "最初", "初の", "はじめて"],
        "strong": ["強い", "力強い", "強力", "パワフル"],
        "legend": ["伝説", "レジェンド", "神話的", "伝説的"],
    }

    # 許容繰り返し回数
    MAX_REPETITIONS = 2

    def detect(self, text: str) -> tuple[float, list[str]]:
        """
        同義語繰り返しを検出

        Args:
            text: テキスト

        Returns:
            (score, repetitions): スコアと検出された繰り返し
        """
        repetitions = []
        total_score = 0.0

        for group_name, synonyms in self.SYNONYM_GROUPS.items():
            count = 0
            found_words = []

            for synonym in synonyms:
                matches = re.findall(synonym, text)
                if matches:
                    count += len(matches)
                    found_words.extend(matches)

            if count > self.MAX_REPETITIONS:
                repetitions.append(f"{group_name}({count}回): {', '.join(set(found_words))}")
                total_score += (count - self.MAX_REPETITIONS) * 0.1

        return min(total_score, 1.0), repetitions


# ==============================================================================
# StructuralPatternDetector
# ==============================================================================


class StructuralPatternDetector:
    """
    文構造パターン検出

    同じ文構造の繰り返しを検出。
    """

    # テンプレート文パターン
    TEMPLATE_PATTERNS = [
        (r"あなたと同じ\d+歳のとき、[^。]+は[^。]+。", "template_opener"),
        (r"[^。]+という[^。]+だった。", "template_narrative"),
        (r"[^。]+という経験は[^。]+。", "template_reflection"),
        (r"この経験は[^。]+となった。", "template_conclusion"),
        (r"こうして[^。]+のである。", "template_ending"),
    ]

    # 繰り返し文末パターン
    REPETITIVE_ENDINGS = [
        (r"のである。", 2),
        (r"だった。", 3),
        (r"となった。", 2),
        (r"している。", 3),
    ]

    def detect(self, text: str) -> tuple[float, list[str]]:
        """
        構造パターンを検出

        Args:
            text: テキスト

        Returns:
            (score, patterns): スコアと検出されたパターン
        """
        patterns_found = []
        score = 0.0

        # テンプレートパターン検出
        for pattern, pattern_name in self.TEMPLATE_PATTERNS:
            matches = re.findall(pattern, text)
            if len(matches) >= 2:
                patterns_found.append(f"{pattern_name}({len(matches)}回)")
                score += 0.15

        # 繰り返し文末検出
        for ending, max_count in self.REPETITIVE_ENDINGS:
            count = len(re.findall(ending, text))
            if count > max_count:
                patterns_found.append(f"文末'{ending}'({count}回)")
                score += (count - max_count) * 0.05

        return min(score, 1.0), patterns_found

    def detect_persona_hack(
        self,
        texts: list[str],
        threshold: float = 0.6,
    ) -> tuple[bool, list[str]]:
        """
        ペルソナハック検出（同一人物の複数エピソードが同じ構造）

        Args:
            texts: 同一人物のエピソードリスト
            threshold: 類似度閾値

        Returns:
            (is_hack, patterns): ハック検出結果とパターン
        """
        if len(texts) < 2:
            return False, []

        # 文構造を抽出
        structures = []
        for text in texts:
            sentences = text.split("。")
            structure = []
            for sent in sentences:
                if len(sent) > 5:
                    # 品詞パターンの簡易表現
                    pattern = ""
                    if re.search(r"^\d+歳", sent):
                        pattern += "AGE_"
                    if re.search(r"という", sent):
                        pattern += "QUOTE_"
                    if re.search(r"である|だった", sent):
                        pattern += "PAST_"
                    if re.search(r"となった|になった", sent):
                        pattern += "RESULT_"
                    structure.append(pattern or "OTHER")
            structures.append(tuple(structure))

        # 構造の重複チェック
        structure_counts = Counter(structures)
        duplicates = [s for s, c in structure_counts.items() if c > 1]

        if duplicates:
            return True, [f"同一構造パターン: {len(duplicates)}種"]

        return False, []


# ==============================================================================
# EmotionalBiasDetector
# ==============================================================================


class EmotionalBiasDetector:
    """
    感情語彙偏り検出

    感動・涙・絶賛などの感情語の多用を検出。
    """

    # 感情語カテゴリ
    EMOTIONAL_WORDS = {
        "admiration": ["感動", "感銘", "胸を打", "心を動かし"],
        "tears": ["涙", "泣", "号泣", "感涙"],
        "praise": ["絶賛", "称賛", "賞賛", "賛美"],
        "miracle": ["奇跡", "ミラクル", "神業"],
        "legend": ["伝説", "レジェンド", "神話"],
        "revolution": ["革命", "革新", "画期的"],
        "shock": ["衝撃", "ショック", "驚愕"],
    }

    # 許容使用回数
    MAX_EMOTIONAL_WORDS = 2
    MAX_CATEGORY_COUNT = 3

    def detect(self, text: str) -> tuple[float, list[str]]:
        """
        感情語彙偏りを検出

        Args:
            text: テキスト

        Returns:
            (score, biases): スコアと検出された偏り
        """
        biases = []
        score = 0.0

        total_emotional = 0
        category_counts = {}

        for category, words in self.EMOTIONAL_WORDS.items():
            count = 0
            found = []

            for word in words:
                matches = re.findall(word, text)
                if matches:
                    count += len(matches)
                    found.extend(matches)

            if count > 0:
                category_counts[category] = count
                total_emotional += count

                if count > self.MAX_EMOTIONAL_WORDS:
                    biases.append(f"{category}({count}回): {', '.join(set(found))}")
                    score += (count - self.MAX_EMOTIONAL_WORDS) * 0.1

        # カテゴリ数チェック
        if len(category_counts) > self.MAX_CATEGORY_COUNT:
            biases.append(f"感情カテゴリ過多({len(category_counts)}種)")
            score += 0.2

        return min(score, 1.0), biases


# ==============================================================================
# SemanticGamingDetector（統合）
# ==============================================================================


class SemanticGamingDetector:
    """
    セマンティックゲーミング検出（統合）

    同義語繰り返し + 構造パターン + 感情偏りを統合。
    """

    # ゲーミング判定閾値
    GAMING_THRESHOLD = 0.4

    def __init__(self):
        self.synonym_detector = SynonymRepetitionDetector()
        self.structural_detector = StructuralPatternDetector()
        self.emotional_detector = EmotionalBiasDetector()

    def detect(self, text: str) -> SemanticGamingResult:
        """
        セマンティックゲーミングを検出

        Args:
            text: エピソードテキスト

        Returns:
            SemanticGamingResult
        """
        # 各検出器を実行
        synonym_score, synonym_reps = self.synonym_detector.detect(text)
        structural_score, structural_patterns = self.structural_detector.detect(text)
        emotional_score, emotional_biases = self.emotional_detector.detect(text)

        # 総合スコア（加重平均）
        total_score = synonym_score * 0.3 + structural_score * 0.4 + emotional_score * 0.3

        # ゲーミング判定
        is_gaming = total_score >= self.GAMING_THRESHOLD

        # 推奨事項
        recommendations = []
        if synonym_reps:
            recommendations.append("同義語の繰り返しを減らし、多様な表現を使用")
        if structural_patterns:
            recommendations.append("文構造にバリエーションを持たせる")
        if emotional_biases:
            recommendations.append("感情語の使用を控え、具体的事実で表現")

        return SemanticGamingResult(
            is_gaming=is_gaming,
            score=total_score,
            synonym_repetitions=synonym_reps,
            structural_patterns=structural_patterns,
            emotional_bias=emotional_biases,
            recommendations=recommendations,
        )

    def detect_multi_episode(
        self,
        episodes: list[str],
    ) -> tuple[bool, list[str]]:
        """
        複数エピソードでのペルソナハック検出

        Args:
            episodes: 同一人物のエピソードリスト

        Returns:
            (is_hack, issues): ハック検出結果と問題リスト
        """
        return self.structural_detector.detect_persona_hack(episodes)


# ==============================================================================
# 便利関数
# ==============================================================================


def check_semantic_gaming(text: str) -> SemanticGamingResult:
    """
    セマンティックゲーミングチェック（便利関数）

    Args:
        text: エピソードテキスト

    Returns:
        SemanticGamingResult
    """
    detector = SemanticGamingDetector()
    return detector.detect(text)


if __name__ == "__main__":
    print("=== Semantic Gaming Detector Test ===")

    # 1. 同義語繰り返しテスト
    print("\n1. 同義語繰り返しテスト")
    synonym_detector = SynonymRepetitionDetector()

    text1 = "成功を収め、大成功となった。この成功は素晴らしい成功だった。"
    score, reps = synonym_detector.detect(text1)
    print(f"  スコア: {score:.2f}")
    print(f"  繰り返し: {reps}")

    # 2. 構造パターンテスト
    print("\n2. 構造パターンテスト")
    structural_detector = StructuralPatternDetector()

    text2 = "あなたと同じ25歳のとき、彼は決断した。あなたと同じ30歳のとき、彼は成功した。"
    score, patterns = structural_detector.detect(text2)
    print(f"  スコア: {score:.2f}")
    print(f"  パターン: {patterns}")

    # 3. 感情偏りテスト
    print("\n3. 感情偏りテスト")
    emotional_detector = EmotionalBiasDetector()

    text3 = "感動的な瞬間で涙が溢れた。この奇跡は伝説となり、革命を起こした。"
    score, biases = emotional_detector.detect(text3)
    print(f"  スコア: {score:.2f}")
    print(f"  偏り: {biases}")

    # 4. 統合テスト
    print("\n4. 統合テスト")
    detector = SemanticGamingDetector()

    test_text = """
    あなたと同じ25歳のとき、彼は偉大な挑戦に成功した。
    この成功は伝説的で、感動的な奇跡だった。
    こうして彼は成功を収め、偉大な存在となったのである。
    """

    result = detector.detect(test_text)
    print(f"  ゲーミング: {result.is_gaming}")
    print(f"  スコア: {result.score:.2f}")
    print(f"  同義語: {result.synonym_repetitions}")
    print(f"  構造: {result.structural_patterns}")
    print(f"  感情: {result.emotional_bias}")
    print(f"  推奨: {result.recommendations}")

    print("\n=== テスト完了 ===")
