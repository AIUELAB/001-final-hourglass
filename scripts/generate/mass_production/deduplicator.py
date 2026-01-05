#!/usr/bin/env python3
"""
高速重複チェックモジュール

TF-IDF + コサイン類似度による効率的な重複検出
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Note: QualityGateConfig is optional, used for type hints only
# from .config import QualityGateConfig


@dataclass
class DuplicateCheckResult:
    """重複チェック結果"""

    episode_text: str
    is_duplicate: bool
    max_similarity: float
    most_similar_episode_id: Optional[str]
    most_similar_text: Optional[str]
    person_name: str
    age: int


class FastDeduplicator:
    """高速重複チェッカー"""

    def __init__(
        self,
        existing_texts: List[str],
        existing_ids: Optional[List[str]] = None,
        threshold: float = 0.7,
        max_features: int = 5000,
    ):
        """
        Args:
            existing_texts: 既存エピソードテキストリスト
            existing_ids: 既存エピソードIDリスト
            threshold: 重複判定閾値
            max_features: TF-IDF最大特徴量
        """
        self.threshold = threshold
        self.existing_texts = existing_texts
        self.existing_ids = existing_ids or [f"idx_{i}" for i in range(len(existing_texts))]

        # 空のテキストを除外
        self.valid_indices = [i for i, t in enumerate(existing_texts) if t and len(t.strip()) > 0]
        self.valid_texts = [existing_texts[i] for i in self.valid_indices]
        self.valid_ids = [self.existing_ids[i] for i in self.valid_indices]

        # TF-IDFベクトライザー（少数ドキュメントでも動作するよう設定）
        # max_df は絶対値で指定（パーセンテージだと少数ドキュメントで問題発生）
        effective_max_df = 1.0 if len(self.valid_texts) < 10 else 0.95
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),  # ユニグラム + バイグラム
            min_df=1,
            max_df=effective_max_df,
            token_pattern=r"(?u)\b\w+\b",  # 日本語対応
        )

        # 既存テキストのベクトル化
        if self.valid_texts:
            self.existing_matrix = self.vectorizer.fit_transform(self.valid_texts)
        else:
            self.existing_matrix = None

    def is_duplicate(self, text: str) -> Tuple[bool, float, Optional[str]]:
        """
        単一テキストの重複チェック

        Args:
            text: チェック対象テキスト

        Returns:
            (is_duplicate, max_similarity, most_similar_id)
        """
        if not text or not text.strip():
            return False, 0.0, None

        if self.existing_matrix is None or self.existing_matrix.shape[0] == 0:
            return False, 0.0, None

        # ベクトル化
        try:
            new_vector = self.vectorizer.transform([text])
        except Exception:
            return False, 0.0, None

        # コサイン類似度計算
        similarities = cosine_similarity(new_vector, self.existing_matrix)[0]

        max_idx = int(np.argmax(similarities))
        max_sim = float(similarities[max_idx])

        most_similar_id = self.valid_ids[max_idx] if max_sim > 0 else None

        return max_sim >= self.threshold, max_sim, most_similar_id

    def check_batch(
        self,
        episodes: List[Dict],
        text_key: str = "episode_text",
    ) -> List[Dict]:
        """
        バッチで重複チェック

        Args:
            episodes: エピソードリスト
            text_key: テキストフィールド名

        Returns:
            重複フラグ付きエピソードリスト
        """
        if not episodes:
            return []

        if self.existing_matrix is None or self.existing_matrix.shape[0] == 0:
            # 既存データなし → 全て非重複
            for ep in episodes:
                ep["is_duplicate"] = False
                ep["max_similarity"] = 0.0
                ep["most_similar_episode_id"] = None
            return episodes

        # バッチベクトル化
        new_texts = [ep.get(text_key, "") or "" for ep in episodes]
        valid_new = [(i, t) for i, t in enumerate(new_texts) if t.strip()]

        if not valid_new:
            for ep in episodes:
                ep["is_duplicate"] = False
                ep["max_similarity"] = 0.0
                ep["most_similar_episode_id"] = None
            return episodes

        valid_indices, valid_texts_batch = zip(*valid_new)

        try:
            new_matrix = self.vectorizer.transform(valid_texts_batch)
        except Exception:
            for ep in episodes:
                ep["is_duplicate"] = False
                ep["max_similarity"] = 0.0
                ep["most_similar_episode_id"] = None
            return episodes

        # バッチ類似度計算（スパース行列で高速）
        similarities = cosine_similarity(new_matrix, self.existing_matrix)

        # 結果をマッピング
        sim_results = {}
        for batch_idx, orig_idx in enumerate(valid_indices):
            max_idx = int(np.argmax(similarities[batch_idx]))
            max_sim = float(similarities[batch_idx][max_idx])
            sim_results[orig_idx] = (max_sim, self.valid_ids[max_idx])

        # 全エピソードに結果を付与
        for i, ep in enumerate(episodes):
            if i in sim_results:
                max_sim, similar_id = sim_results[i]
                ep["is_duplicate"] = max_sim >= self.threshold
                ep["max_similarity"] = max_sim
                ep["most_similar_episode_id"] = similar_id
            else:
                ep["is_duplicate"] = False
                ep["max_similarity"] = 0.0
                ep["most_similar_episode_id"] = None

        return episodes

    def filter_non_duplicates(
        self,
        episodes: List[Dict],
        text_key: str = "episode_text",
    ) -> List[Dict]:
        """
        非重複エピソードのみを返す

        Args:
            episodes: エピソードリスト
            text_key: テキストフィールド名

        Returns:
            非重複エピソードリスト
        """
        checked = self.check_batch(episodes, text_key)
        return [ep for ep in checked if not ep.get("is_duplicate", False)]


class PersonAgeDeduplicator:
    """人物×年齢単位の重複チェッカー"""

    def __init__(
        self,
        master_csv_path: Path,
        threshold: float = 0.7,
    ):
        """
        Args:
            master_csv_path: マスターCSVパス
            threshold: 重複判定閾値
        """
        self.threshold = threshold
        self.df = pd.read_csv(master_csv_path, dtype=str, low_memory=False)
        self._build_person_age_index()

    def _build_person_age_index(self) -> None:
        """人物×年齢インデックスを構築"""
        self.person_age_texts: Dict[Tuple[str, int], List[Tuple[str, str]]] = {}

        for _, row in self.df.iterrows():
            person = row.get("person_name", "")
            age_str = row.get("age", "")
            text = row.get("episode_text", "")
            ep_id = row.get("episode_id", "")

            if not person or not text:
                continue

            try:
                age = int(float(age_str)) if age_str else 0
            except (ValueError, TypeError):
                age = 0

            key = (person, age)
            if key not in self.person_age_texts:
                self.person_age_texts[key] = []
            self.person_age_texts[key].append((ep_id, text))

    def check_same_person_age(
        self,
        person_name: str,
        age: int,
        new_text: str,
    ) -> Tuple[bool, float, Optional[str]]:
        """
        同一人物×同一年齢での重複チェック

        Args:
            person_name: 人物名
            age: 年齢
            new_text: 新規テキスト

        Returns:
            (is_duplicate, max_similarity, most_similar_id)
        """
        key = (person_name, age)
        existing = self.person_age_texts.get(key, [])

        if not existing:
            return False, 0.0, None

        existing_texts = [t for _, t in existing]
        existing_ids = [i for i, _ in existing]

        dedup = FastDeduplicator(
            existing_texts=existing_texts,
            existing_ids=existing_ids,
            threshold=self.threshold,
        )

        return dedup.is_duplicate(new_text)

    def check_batch_same_person_age(
        self,
        episodes: List[Dict],
    ) -> List[Dict]:
        """
        バッチで同一人物×年齢重複チェック

        Args:
            episodes: エピソードリスト

        Returns:
            重複フラグ付きエピソードリスト
        """
        for ep in episodes:
            person = ep.get("person_name", "")
            age = ep.get("age", 0)
            text = ep.get("episode_text", "")

            if not person or not text:
                ep["is_same_age_duplicate"] = False
                ep["same_age_max_similarity"] = 0.0
                ep["same_age_similar_id"] = None
                continue

            is_dup, max_sim, similar_id = self.check_same_person_age(person, age, text)
            ep["is_same_age_duplicate"] = is_dup
            ep["same_age_max_similarity"] = max_sim
            ep["same_age_similar_id"] = similar_id

        return episodes


class ContentSimilarityChecker:
    """内容類似性チェッカー（イベント重複検出）"""

    # 重要キーワード抽出パターン
    YEAR_PATTERN = re.compile(r"\d{4}年")
    NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?(?:歳|万|億|円|人|本|件|回|%|kg|m|km)?")

    def __init__(self, threshold: float = 0.8):
        """
        Args:
            threshold: イベント類似度閾値
        """
        self.threshold = threshold

    def extract_key_facts(self, text: str) -> Set[str]:
        """
        テキストから重要事実を抽出

        Args:
            text: エピソードテキスト

        Returns:
            重要事実セット
        """
        facts = set()

        # 年号抽出
        years = self.YEAR_PATTERN.findall(text)
        facts.update(years)

        # 数値抽出
        numbers = self.NUMBER_PATTERN.findall(text)
        facts.update(numbers)

        return facts

    def calculate_fact_overlap(self, text1: str, text2: str) -> float:
        """
        事実の重複率を計算

        Args:
            text1: テキスト1
            text2: テキスト2

        Returns:
            重複率（0-1）
        """
        facts1 = self.extract_key_facts(text1)
        facts2 = self.extract_key_facts(text2)

        if not facts1 or not facts2:
            return 0.0

        intersection = facts1 & facts2
        union = facts1 | facts2

        return len(intersection) / len(union) if union else 0.0

    def is_event_duplicate(self, text1: str, text2: str) -> Tuple[bool, float]:
        """
        イベント重複判定

        Args:
            text1: テキスト1
            text2: テキスト2

        Returns:
            (is_duplicate, overlap_ratio)
        """
        overlap = self.calculate_fact_overlap(text1, text2)
        return overlap >= self.threshold, overlap


def main():
    """デモ実行"""
    from .config import MASTER_CSV_PATH

    print("=== 重複チェッカーデモ ===")

    # サンプルテキスト
    existing = [
        "1905年、アインシュタインは26歳で特殊相対性理論を発表した。",
        "1969年7月20日、アームストロングは38歳で月面に降り立った。",
        "1997年、スティーブ・ジョブズは42歳でAppleに復帰した。",
    ]

    dedup = FastDeduplicator(existing, threshold=0.7)

    # テストケース
    test_cases = [
        "1905年にアインシュタインは相対性理論を世に問うた。",  # 類似
        "2020年、大谷翔平は26歳でMLBでMVPを獲得した。",  # 非類似
        "アームストロングは1969年に月に着陸した最初の人間となった。",  # 類似
    ]

    print("\n重複チェック結果:")
    for text in test_cases:
        is_dup, sim, _ = dedup.is_duplicate(text)
        status = "重複" if is_dup else "非重複"
        print(f"  [{status}] 類似度={sim:.3f}: {text[:40]}...")


if __name__ == "__main__":
    main()
