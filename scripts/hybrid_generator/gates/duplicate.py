"""
Duplicate Detection Gate

重複検出とテキスト類似度計算。
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ..config import MASTER_CSV, QUALITY_THRESHOLDS, RejectionReason


@dataclass
class DuplicateCheckResult:
    """重複チェック結果"""

    is_duplicate: bool
    similarity_score: float  # 0.0-1.0
    most_similar_episode_id: Optional[str] = None
    most_similar_text: Optional[str] = None
    reason: str = ""
    rejection_reason: RejectionReason = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_duplicate": self.is_duplicate,
            "similarity_score": self.similarity_score,
            "most_similar_episode_id": self.most_similar_episode_id,
            "reason": self.reason,
        }


class TextSimilarityCalculator:
    """
    テキスト類似度計算器

    複数の類似度計算方式をサポート。
    """

    @staticmethod
    def sequence_matcher_ratio(text1: str, text2: str) -> float:
        """SequenceMatcherによる類似度"""
        return SequenceMatcher(None, text1, text2).ratio()

    @staticmethod
    def jaccard_similarity(text1: str, text2: str) -> float:
        """Jaccard類似度（単語ベース）"""
        # 単語に分割
        words1 = set(re.findall(r"\w+", text1))
        words2 = set(re.findall(r"\w+", text2))

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    @staticmethod
    def key_phrase_overlap(text1: str, text2: str) -> float:
        """キーフレーズ重複率"""
        # 年号抽出
        years1 = set(re.findall(r"(1[89]\d{2}|20[0-2]\d)年", text1))
        years2 = set(re.findall(r"(1[89]\d{2}|20[0-2]\d)年", text2))

        # 固有名詞抽出（「」内）
        quoted1 = set(re.findall(r"「([^」]+)」", text1))
        quoted2 = set(re.findall(r"「([^」]+)」", text2))

        # カタカナ語抽出
        katakana1 = set(re.findall(r"[\u30A0-\u30FF]{3,}", text1))
        katakana2 = set(re.findall(r"[\u30A0-\u30FF]{3,}", text2))

        # 全キーフレーズ
        keys1 = years1 | quoted1 | katakana1
        keys2 = years2 | quoted2 | katakana2

        if not keys1 or not keys2:
            return 0.0

        intersection = keys1 & keys2
        smaller = min(len(keys1), len(keys2))

        return len(intersection) / smaller

    @classmethod
    def combined_similarity(cls, text1: str, text2: str) -> float:
        """複合類似度（3方式の加重平均）"""
        seq_sim = cls.sequence_matcher_ratio(text1, text2)
        jac_sim = cls.jaccard_similarity(text1, text2)
        key_sim = cls.key_phrase_overlap(text1, text2)

        # 加重平均（キーフレーズ重視）
        return seq_sim * 0.3 + jac_sim * 0.3 + key_sim * 0.4


class DuplicateDetector:
    """
    重複検出器

    同一人物・同一年齢のエピソード重複を検出。
    """

    def __init__(
        self,
        master_csv: Path = MASTER_CSV,
        similarity_threshold: float = None,
        thresholds: dict = None,
    ):
        self.master_csv = master_csv
        self.thresholds = thresholds or QUALITY_THRESHOLDS.copy()
        self.similarity_threshold = similarity_threshold or self.thresholds.get("max_text_similarity", 0.6)
        self._master_df: Optional[pd.DataFrame] = None
        self._similarity_calc = TextSimilarityCalculator()

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

    def reload_master(self) -> None:
        """マスターデータを再読み込み"""
        self._master_df = None

    def check_exact_duplicate(self, person_id: str, age: int) -> DuplicateCheckResult:
        """
        完全一致重複チェック（同一人物・同一年齢）

        Args:
            person_id: 人物ID
            age: 年齢

        Returns:
            DuplicateCheckResult: チェック結果
        """
        if self.master_df.empty:
            return DuplicateCheckResult(
                is_duplicate=False,
                similarity_score=0.0,
                reason="No existing episodes",
            )

        # 同一人物・同一年齢のエピソードを検索
        existing = self.master_df[(self.master_df["person_id"] == person_id) & (self.master_df["age"] == age)]

        if not existing.empty:
            first = existing.iloc[0]
            return DuplicateCheckResult(
                is_duplicate=True,
                similarity_score=1.0,
                most_similar_episode_id=first.get("episode_id", "unknown"),
                most_similar_text=str(first.get("episode_text", ""))[:100],
                reason=f"Exact duplicate: {person_id} at age {age}",
                rejection_reason=RejectionReason.SAME_AGE_DUPLICATE,
            )

        return DuplicateCheckResult(
            is_duplicate=False,
            similarity_score=0.0,
            reason="No exact duplicate found",
        )

    def check_text_similarity(self, text: str, person_id: str, age: int = None) -> DuplicateCheckResult:
        """
        テキスト類似度チェック

        Args:
            text: 新規エピソードテキスト
            person_id: 人物ID
            age: 年齢（オプション）

        Returns:
            DuplicateCheckResult: チェック結果
        """
        if self.master_df.empty:
            return DuplicateCheckResult(
                is_duplicate=False,
                similarity_score=0.0,
                reason="No existing episodes",
            )

        # 同一人物のエピソードを検索
        existing = self.master_df[self.master_df["person_id"] == person_id]

        if age is not None:
            # 同一年齢に絞る
            same_age = existing[existing["age"] == age]
            if not same_age.empty:
                existing = same_age

        if existing.empty:
            return DuplicateCheckResult(
                is_duplicate=False,
                similarity_score=0.0,
                reason="No existing episodes for this person",
            )

        # 類似度計算
        max_similarity = 0.0
        most_similar_id = None
        most_similar_text = None

        for _, row in existing.iterrows():
            existing_text = str(row.get("episode_text", ""))
            if not existing_text:
                continue

            similarity = self._similarity_calc.combined_similarity(text, existing_text)

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_id = row.get("episode_id", "unknown")
                most_similar_text = existing_text[:100]

        is_duplicate = max_similarity >= self.similarity_threshold

        return DuplicateCheckResult(
            is_duplicate=is_duplicate,
            similarity_score=max_similarity,
            most_similar_episode_id=most_similar_id,
            most_similar_text=most_similar_text,
            reason=f"Similarity: {max_similarity:.2f} (threshold: {self.similarity_threshold})",
            rejection_reason=RejectionReason.HIGH_SIMILARITY if is_duplicate else None,
        )

    def check_all(self, text: str, person_id: str, age: int) -> DuplicateCheckResult:
        """
        全重複チェックを実行

        Args:
            text: 新規エピソードテキスト
            person_id: 人物ID
            age: 年齢

        Returns:
            DuplicateCheckResult: チェック結果
        """
        # 1. 完全一致チェック
        exact_result = self.check_exact_duplicate(person_id, age)
        if exact_result.is_duplicate:
            return exact_result

        # 2. テキスト類似度チェック
        similarity_result = self.check_text_similarity(text, person_id, age)
        return similarity_result


def quick_duplicate_check(text: str, person_id: str, age: int) -> bool:
    """
    簡易重複チェック

    Args:
        text: エピソードテキスト
        person_id: 人物ID
        age: 年齢

    Returns:
        bool: 重複がないか（True = 重複なし）
    """
    detector = DuplicateDetector()
    result = detector.check_all(text, person_id, age)
    return not result.is_duplicate
