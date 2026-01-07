"""
Advanced Similarity Detection - Phase 6

セマンティック類似度、時間軸重複検出、カテゴリ間重複検出。
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..config import RejectionReason


# ==============================================================================
# データクラス
# ==============================================================================


@dataclass
class SemanticSimilarityResult:
    """セマンティック類似度結果"""

    is_similar: bool
    similarity_score: float  # 0.0-1.0
    similar_episode_id: Optional[str] = None
    similar_text_preview: Optional[str] = None
    method: str = "tfidf"  # "tfidf" or "embedding"

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_similar": self.is_similar,
            "similarity_score": self.similarity_score,
            "similar_episode_id": self.similar_episode_id,
            "method": self.method,
        }


@dataclass
class TemporalDuplicateResult:
    """時間軸重複検出結果"""

    is_duplicate: bool
    overlap_ages: list[int] = field(default_factory=list)
    overlap_themes: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_duplicate": self.is_duplicate,
            "overlap_ages": self.overlap_ages,
            "overlap_themes": self.overlap_themes,
            "reason": self.reason,
        }


@dataclass
class AdvancedDuplicateResult:
    """高度重複検出統合結果"""

    is_duplicate: bool
    semantic_result: Optional[SemanticSimilarityResult] = None
    temporal_result: Optional[TemporalDuplicateResult] = None
    cross_category_duplicate: bool = False
    overall_score: float = 0.0
    rejection_reason: Optional[RejectionReason] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_duplicate": self.is_duplicate,
            "semantic": self.semantic_result.to_dict() if self.semantic_result else None,
            "temporal": self.temporal_result.to_dict() if self.temporal_result else None,
            "cross_category_duplicate": self.cross_category_duplicate,
            "overall_score": self.overall_score,
        }


# ==============================================================================
# SemanticSimilarity
# ==============================================================================


class SemanticSimilarity:
    """
    セマンティック類似度計算

    sentence-transformers が利用可能な場合は埋め込みベクトルを使用。
    そうでない場合はTF-IDFにフォールバック。
    """

    # セマンティック類似度閾値
    MAX_SEMANTIC_SIMILARITY = 0.85

    def __init__(self, use_embeddings: bool = True):
        self._embedder = None
        self._use_embeddings = use_embeddings
        self._tfidf = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 4),
            max_features=5000,
        )
        self._init_embedder()

    def _init_embedder(self) -> None:
        """埋め込みモデルの初期化（オプショナル）"""
        if not self._use_embeddings:
            return

        try:
            from sentence_transformers import SentenceTransformer

            # 日本語対応の軽量モデル
            self._embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        except ImportError:
            # sentence-transformers がインストールされていない場合
            self._embedder = None

    def calculate_similarity(self, text1: str, text2: str) -> tuple[float, str]:
        """
        セマンティック類似度を計算

        Args:
            text1: テキスト1
            text2: テキスト2

        Returns:
            (similarity, method): 類似度スコアと使用手法
        """
        if self._embedder:
            return self._embedding_similarity(text1, text2), "embedding"
        else:
            return self._tfidf_similarity(text1, text2), "tfidf"

    def _embedding_similarity(self, text1: str, text2: str) -> float:
        """埋め込みベクトルによる類似度"""
        embeddings = self._embedder.encode([text1, text2])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        return float(similarity)

    def _tfidf_similarity(self, text1: str, text2: str) -> float:
        """TF-IDFによる類似度"""
        try:
            tfidf_matrix = self._tfidf.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except ValueError:
            return 0.0

    def check(
        self,
        new_text: str,
        existing_texts: list[tuple[str, str]],  # [(episode_id, text), ...]
        threshold: float = None,
    ) -> SemanticSimilarityResult:
        """
        既存テキストとのセマンティック類似度をチェック

        Args:
            new_text: 新規テキスト
            existing_texts: 既存テキストリスト [(episode_id, text), ...]
            threshold: 閾値

        Returns:
            SemanticSimilarityResult
        """
        threshold = threshold or self.MAX_SEMANTIC_SIMILARITY

        max_similarity = 0.0
        most_similar_id = None
        most_similar_text = None
        method = "tfidf"

        for ep_id, existing_text in existing_texts:
            similarity, method = self.calculate_similarity(new_text, existing_text)

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_id = ep_id
                most_similar_text = existing_text[:100]

        is_similar = max_similarity >= threshold

        return SemanticSimilarityResult(
            is_similar=is_similar,
            similarity_score=max_similarity,
            similar_episode_id=most_similar_id,
            similar_text_preview=most_similar_text,
            method=method,
        )


# ==============================================================================
# TemporalDuplicateDetector
# ==============================================================================


class TemporalDuplicateDetector:
    """
    時間軸重複検出

    年齢±1での類似エピソード、連続年齢での同テーマを検出。
    """

    # 主要テーマパターン
    THEME_PATTERNS = {
        "debut": [r"デビュー", r"初めて", r"始まり", r"開始"],
        "success": [r"成功", r"達成", r"受賞", r"優勝", r"1位"],
        "failure": [r"失敗", r"挫折", r"敗北", r"落選"],
        "transition": [r"転機", r"転職", r"引退", r"卒業"],
        "creation": [r"発表", r"発売", r"公開", r"リリース"],
        "marriage": [r"結婚", r"離婚", r"婚約"],
        "education": [r"入学", r"卒業", r"学位"],
    }

    def __init__(self, age_tolerance: int = 1):
        self.age_tolerance = age_tolerance

    def extract_themes(self, text: str) -> list[str]:
        """テキストからテーマを抽出"""
        themes = []
        for theme_name, patterns in self.THEME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    themes.append(theme_name)
                    break
        return themes

    def check(
        self,
        new_text: str,
        new_age: int,
        existing_episodes: list[dict],  # [{"age": int, "text": str, "episode_id": str}, ...]
    ) -> TemporalDuplicateResult:
        """
        時間軸重複をチェック

        Args:
            new_text: 新規テキスト
            new_age: 新規エピソードの年齢
            existing_episodes: 既存エピソードリスト

        Returns:
            TemporalDuplicateResult
        """
        new_themes = self.extract_themes(new_text)
        if not new_themes:
            return TemporalDuplicateResult(is_duplicate=False)

        overlap_ages = []
        overlap_themes = []

        for ep in existing_episodes:
            ep_age = ep.get("age", 0)
            ep_text = ep.get("text", "")

            # 年齢が±tolerance内かチェック
            if abs(ep_age - new_age) <= self.age_tolerance:
                ep_themes = self.extract_themes(ep_text)

                # テーマ重複チェック
                common_themes = set(new_themes) & set(ep_themes)
                if common_themes:
                    overlap_ages.append(ep_age)
                    overlap_themes.extend(common_themes)

        # 重複判定
        is_duplicate = len(overlap_ages) > 0

        return TemporalDuplicateResult(
            is_duplicate=is_duplicate,
            overlap_ages=list(set(overlap_ages)),
            overlap_themes=list(set(overlap_themes)),
            reason=f"Similar themes at ages {overlap_ages}: {overlap_themes}" if is_duplicate else "",
        )


# ==============================================================================
# CrossCategoryDuplicateDetector
# ==============================================================================


class CrossCategoryDuplicateDetector:
    """
    カテゴリ間重複検出

    異なるカテゴリで同じ事象が記述されていないかチェック。
    """

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self._semantic = SemanticSimilarity(use_embeddings=False)  # 軽量版

    def extract_key_events(self, text: str) -> list[str]:
        """キーイベントを抽出"""
        events = []

        # 年号+動詞パターン
        year_events = re.findall(r"(\d{4}年[^。]{5,30})", text)
        events.extend(year_events)

        # 「」内の事象
        quoted = re.findall(r"「([^」]{3,20})」", text)
        events.extend(quoted)

        return events

    def check(
        self,
        new_text: str,
        new_category: str,
        existing_episodes: list[dict],  # [{"category": str, "text": str, "episode_id": str}, ...]
    ) -> bool:
        """
        カテゴリ間重複をチェック

        Args:
            new_text: 新規テキスト
            new_category: 新規カテゴリ
            existing_episodes: 既存エピソードリスト

        Returns:
            bool: 重複が検出されたか
        """
        new_events = self.extract_key_events(new_text)
        if not new_events:
            return False

        for ep in existing_episodes:
            ep_category = ep.get("category", "")
            ep_text = ep.get("text", "")

            # 異なるカテゴリのみチェック
            if ep_category == new_category:
                continue

            ep_events = self.extract_key_events(ep_text)

            # イベント重複チェック
            for new_event in new_events:
                for ep_event in ep_events:
                    sim, _ = self._semantic.calculate_similarity(new_event, ep_event)
                    if sim >= self.similarity_threshold:
                        return True

        return False


# ==============================================================================
# AdvancedDuplicateChecker（統合）
# ==============================================================================


class AdvancedDuplicateChecker:
    """
    高度重複検出（統合）

    セマンティック + 時間軸 + カテゴリ間を統合。
    """

    def __init__(
        self,
        semantic_threshold: float = 0.85,
        age_tolerance: int = 1,
        use_embeddings: bool = True,
    ):
        self.semantic = SemanticSimilarity(use_embeddings=use_embeddings)
        self.temporal = TemporalDuplicateDetector(age_tolerance=age_tolerance)
        self.cross_category = CrossCategoryDuplicateDetector()
        self.semantic_threshold = semantic_threshold

    def check(
        self,
        new_text: str,
        new_age: int,
        new_category: str,
        existing_episodes: list[dict],
    ) -> AdvancedDuplicateResult:
        """
        統合重複チェック

        Args:
            new_text: 新規テキスト
            new_age: 年齢
            new_category: カテゴリ
            existing_episodes: 既存エピソードリスト
                [{"episode_id": str, "text": str, "age": int, "category": str}, ...]

        Returns:
            AdvancedDuplicateResult
        """
        # 1. セマンティック類似度チェック
        existing_texts = [(ep.get("episode_id", ""), ep.get("text", "")) for ep in existing_episodes]
        semantic_result = self.semantic.check(
            new_text,
            existing_texts,
            threshold=self.semantic_threshold,
        )

        # 2. 時間軸重複チェック
        temporal_result = self.temporal.check(new_text, new_age, existing_episodes)

        # 3. カテゴリ間重複チェック
        cross_category = self.cross_category.check(new_text, new_category, existing_episodes)

        # 4. 総合判定
        is_duplicate = semantic_result.is_similar or (temporal_result.is_duplicate and cross_category)

        # 5. 総合スコア
        overall_score = semantic_result.similarity_score
        if temporal_result.is_duplicate:
            overall_score = max(overall_score, 0.7)
        if cross_category:
            overall_score = max(overall_score, 0.6)

        rejection_reason = None
        if is_duplicate:
            if semantic_result.is_similar:
                rejection_reason = RejectionReason.HIGH_SIMILARITY
            else:
                rejection_reason = RejectionReason.SAME_AGE_DUPLICATE

        return AdvancedDuplicateResult(
            is_duplicate=is_duplicate,
            semantic_result=semantic_result,
            temporal_result=temporal_result,
            cross_category_duplicate=cross_category,
            overall_score=overall_score,
            rejection_reason=rejection_reason,
        )


# ==============================================================================
# 便利関数
# ==============================================================================


def check_advanced_duplicate(
    new_text: str,
    new_age: int,
    new_category: str,
    existing_episodes: list[dict],
) -> AdvancedDuplicateResult:
    """
    高度重複チェック（便利関数）

    Args:
        new_text: 新規テキスト
        new_age: 年齢
        new_category: カテゴリ
        existing_episodes: 既存エピソードリスト

    Returns:
        AdvancedDuplicateResult
    """
    checker = AdvancedDuplicateChecker(use_embeddings=False)  # 軽量版
    return checker.check(new_text, new_age, new_category, existing_episodes)


if __name__ == "__main__":
    print("=== Advanced Similarity Test ===")

    # 1. セマンティック類似度テスト
    print("\n1. セマンティック類似度テスト")
    semantic = SemanticSimilarity(use_embeddings=False)

    text1 = "1905年にアインシュタインは特殊相対性理論を発表した"
    text2 = "アインシュタインが1905年に発表した相対性理論"
    text3 = "野球選手がホームランを打った"

    sim1, method = semantic.calculate_similarity(text1, text2)
    sim2, _ = semantic.calculate_similarity(text1, text3)

    print(f"  類似テキスト: {sim1:.3f} ({method})")
    print(f"  異なるテキスト: {sim2:.3f}")

    # 2. 時間軸重複テスト
    print("\n2. 時間軸重複テスト")
    temporal = TemporalDuplicateDetector()

    existing = [
        {"age": 25, "text": "25歳でデビューを果たした", "episode_id": "EP001"},
        {"age": 30, "text": "30歳で優勝した", "episode_id": "EP002"},
    ]

    result = temporal.check("26歳で新人賞を受賞しデビュー", 26, existing)
    print(f"  重複: {result.is_duplicate}")
    print(f"  重複年齢: {result.overlap_ages}")
    print(f"  重複テーマ: {result.overlap_themes}")

    # 3. 統合テスト
    print("\n3. 統合テスト")
    checker = AdvancedDuplicateChecker(use_embeddings=False)

    existing_full = [
        {"episode_id": "EP001", "text": "25歳でデビュー", "age": 25, "category": "芸能"},
        {"episode_id": "EP002", "text": "30歳で映画出演", "age": 30, "category": "芸能"},
    ]

    result = checker.check(
        new_text="26歳でドラマデビュー",
        new_age=26,
        new_category="芸能",
        existing_episodes=existing_full,
    )

    print(f"  統合判定: duplicate={result.is_duplicate}")
    print(f"  セマンティック: {result.semantic_result.similarity_score:.3f}")
    print(f"  時間軸: {result.temporal_result.is_duplicate}")
    print(f"  カテゴリ間: {result.cross_category_duplicate}")

    print("\n=== テスト完了 ===")
