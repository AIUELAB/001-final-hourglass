"""
Candidate Prioritizer

候補の優先度スコアリングと最適な生成対象の選定。
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

from ..config import DIVERSITY_TARGETS, MASTER_CSV
from ..inventory_manager import InventoryManager


@dataclass
class CandidatePriorityScore:
    """候補の優先度スコア"""

    person_id: str
    person_name: str
    category: str
    age: int
    score: float
    ep_count: int
    ep_count_score: float
    category_score: float
    age_coverage_score: float
    inventory_priority_score: float = 0.0  # Phase 15: 年齢在庫優先度
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "person_id": self.person_id,
            "person_name": self.person_name,
            "category": self.category,
            "age": self.age,
            "score": self.score,
            "ep_count": self.ep_count,
            "components": {
                "ep_count_score": self.ep_count_score,
                "category_score": self.category_score,
                "age_coverage_score": self.age_coverage_score,
                "inventory_priority_score": self.inventory_priority_score,
            },
            "details": self.details,
        }


class CandidatePrioritizer:
    """
    候補の優先度スコアリング

    EP数、カテゴリバランス、年齢カバレッジを考慮して
    最適な生成対象を選定する。
    """

    # スコアウェイト (Phase 15: 年齢在庫優先度追加)
    EP_COUNT_WEIGHT = 0.4  # EP数少ない人物を優先
    CATEGORY_WEIGHT = 0.25  # 不足カテゴリを優先
    AGE_COVERAGE_WEIGHT = 0.15  # 未カバー年齢を優先
    INVENTORY_AGE_PRIORITY_WEIGHT = 0.2  # 年齢在庫不足を優先

    # Phase 16: 低成功率パターンのペナルティ（15歳スポーツ選手など）
    LOW_SUCCESS_PENALTY = 0.3  # 優先度を30%下げる
    LOW_SUCCESS_PATTERNS = [
        {"category_prefix": "スポーツ", "age_range": (10, 18)},  # 若年スポーツ選手
    ]

    def __init__(
        self,
        master_csv: Path = MASTER_CSV,
        targets: Optional[dict] = None,
    ):
        self.master_csv = master_csv
        self.targets = targets or DIVERSITY_TARGETS.copy()
        self._master_df: Optional[pd.DataFrame] = None
        self._ep_counts: Optional[dict[str, int]] = None
        self._category_counts: Optional[dict[str, int]] = None
        self._person_ages: Optional[dict[str, set[int]]] = None
        # Phase 15: 年齢在庫管理
        self._inventory_manager: Optional[InventoryManager] = None

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

    def _get_ep_counts(self) -> dict[str, int]:
        """人物ごとのEP数を取得"""
        if self._ep_counts is None:
            if self.master_df.empty:
                self._ep_counts = {}
            else:
                self._ep_counts = dict(self.master_df["person_id"].value_counts())
        return self._ep_counts

    def _get_category_counts(self) -> dict[str, int]:
        """カテゴリごとのEP数を取得"""
        if self._category_counts is None:
            if self.master_df.empty:
                self._category_counts = {}
            else:
                self._category_counts = dict(self.master_df["category"].value_counts())
        return self._category_counts

    def _get_person_ages(self) -> dict[str, set[int]]:
        """人物ごとの既存年齢を取得"""
        if self._person_ages is None:
            self._person_ages = {}
            if not self.master_df.empty:
                for _, row in self.master_df.iterrows():
                    person_id = row["person_id"]
                    age = row.get("age")
                    if pd.notna(age):
                        if person_id not in self._person_ages:
                            self._person_ages[person_id] = set()
                        self._person_ages[person_id].add(int(age))
        return self._person_ages

    def _calculate_ep_count_score(self, person_id: str) -> tuple[float, int]:
        """
        EP数スコアを計算（少ないほど高い）

        Returns:
            (score, ep_count)
        """
        ep_counts = self._get_ep_counts()
        ep_count = ep_counts.get(person_id, 0)

        # EP数が少ないほど高スコア (0件→100, 10件→10, 100件→1)
        score = 100 / (ep_count + 1)

        return score, ep_count

    def _calculate_category_score(self, category: str) -> float:
        """
        カテゴリスコアを計算（不足カテゴリほど高い）
        """
        category_counts = self._get_category_counts()
        total = sum(category_counts.values()) if category_counts else 1

        # 現在の割合
        current_ratio = category_counts.get(category, 0) / total

        # 目標割合
        target_ratios = self.targets.get("category_distribution", {})
        target_ratio = target_ratios.get(category, 1 / len(target_ratios) if target_ratios else 0.1)

        # 不足度を計算 (目標より少ないほど高スコア)
        deficit = max(0, target_ratio - current_ratio)
        score = deficit * 500  # 0-50の範囲に正規化

        return min(50, score)

    def _calculate_age_coverage_score(self, person_id: str, age: int) -> float:
        """
        年齢カバレッジスコアを計算（未カバー年齢ほど高い）
        """
        person_ages = self._get_person_ages()
        existing_ages = person_ages.get(person_id, set())

        if not existing_ages:
            # 初めての人物は中程度のスコア
            return 30

        if age in existing_ages:
            # 既存年齢は低スコア
            return 0

        # 近い年齢があるかチェック
        min_distance = min(abs(age - a) for a in existing_ages)

        if min_distance <= 2:
            # 2歳以内に既存あり → 低スコア
            return 10
        elif min_distance <= 5:
            # 5歳以内 → 中スコア
            return 30
        else:
            # 離れた年齢 → 高スコア
            return 50

    def _get_inventory_manager(self) -> InventoryManager:
        """InventoryManagerを遅延初期化で取得"""
        if self._inventory_manager is None:
            self._inventory_manager = InventoryManager()
            self._inventory_manager.refresh()
        return self._inventory_manager

    def _calculate_inventory_age_priority_score(self, age: int) -> float:
        """
        年齢在庫優先度スコアを計算（Phase 15 + Phase 3最適化 + 安全性修正）

        不足数が多い年齢を優先。極端年齢（0-10, 80-84）で低カバレッジの場合は
        年齢ペナルティを軽減してブーストする。

        注意: 85歳以上は境界検証が困難なため、ブーストしない。

        Returns:
            0-100の正規化スコア
        """
        inventory = self._get_inventory_manager()
        status = inventory.get_status(age)

        if status is None:
            return 0.0

        # GENERATEモードでないなら低スコア
        from ..inventory_manager import GenerationMode

        if status.mode != GenerationMode.GENERATE:
            return 10.0  # REPLACEモードは低優先度

        # 不足数
        deficit = status.deficit
        if deficit <= 0:
            return 0.0

        # カバレッジ率を計算 (target=400を想定)
        target = self.targets.get(age, 400)
        current = target - deficit
        coverage_rate = current / target if target > 0 else 1.0

        # Phase 3最適化（安全性修正版）: 極端年齢ブースト
        # 85歳以上はブーストなし（境界検証が困難）
        is_safe_extreme_age = (age <= 10) or (80 <= age <= 84)
        is_risky_extreme_age = age >= 85
        is_very_low_coverage = coverage_rate < 0.15  # 15%未満

        if is_risky_extreme_age:
            # 85歳以上: ブーストなし、通常ペナルティ
            age_penalty = 1.0 + abs(age - 40) / 20
            extreme_boost = 1.0
        elif is_safe_extreme_age and is_very_low_coverage:
            # 安全な極端年齢(0-10, 80-84)で低カバレッジ: ブースト
            age_penalty = 1.0 + abs(age - 40) / 60  # 1/3に軽減
            extreme_boost = 1.5
        elif is_safe_extreme_age:
            # 安全な極端年齢: 中程度のブースト
            age_penalty = 1.0 + abs(age - 40) / 40  # 1/2に軽減
            extreme_boost = 1.2
        else:
            # 通常年齢: 従来のペナルティ
            age_penalty = 1.0 + abs(age - 40) / 20
            extreme_boost = 1.0

        # 基本スコア: deficit / age_penalty * boost
        raw_score = (deficit / age_penalty) * extreme_boost

        # 正規化 (0-100): 最大不足数365を想定
        normalized = min(100, raw_score / 3)

        return normalized

    def score(
        self,
        person_id: str,
        person_name: str,
        category: str,
        age: int,
    ) -> CandidatePriorityScore:
        """
        候補の優先度スコアを計算

        Args:
            person_id: 人物ID
            person_name: 人物名
            category: カテゴリ
            age: 年齢

        Returns:
            CandidatePriorityScore: 優先度スコア
        """
        # 各コンポーネントスコア
        ep_count_score, ep_count = self._calculate_ep_count_score(person_id)
        category_score = self._calculate_category_score(category)
        age_coverage_score = self._calculate_age_coverage_score(person_id, age)
        inventory_priority_score = self._calculate_inventory_age_priority_score(age)

        # 重み付き合計 (Phase 15: 年齢在庫優先度追加)
        total_score = (
            ep_count_score * self.EP_COUNT_WEIGHT
            + category_score * self.CATEGORY_WEIGHT
            + age_coverage_score * self.AGE_COVERAGE_WEIGHT
            + inventory_priority_score * self.INVENTORY_AGE_PRIORITY_WEIGHT
        )

        # Phase 16: 低成功率パターンのペナルティ適用
        for pattern in self.LOW_SUCCESS_PATTERNS:
            cat_prefix = pattern.get("category_prefix", "")
            age_min, age_max = pattern.get("age_range", (0, 0))
            if category.startswith(cat_prefix) and age_min <= age <= age_max:
                total_score *= 1.0 - self.LOW_SUCCESS_PENALTY
                break

        return CandidatePriorityScore(
            person_id=person_id,
            person_name=person_name,
            category=category,
            age=age,
            score=total_score,
            ep_count=ep_count,
            ep_count_score=ep_count_score,
            category_score=category_score,
            age_coverage_score=age_coverage_score,
            inventory_priority_score=inventory_priority_score,
            details={
                "weights": {
                    "ep_count": self.EP_COUNT_WEIGHT,
                    "category": self.CATEGORY_WEIGHT,
                    "age_coverage": self.AGE_COVERAGE_WEIGHT,
                    "inventory_priority": self.INVENTORY_AGE_PRIORITY_WEIGHT,
                }
            },
        )

    def prioritize_candidates(
        self,
        candidates: list[dict],
        top_n: int = 10,
        min_score: float = 0.0,  # Phase 12: 最低スコア閾値
        exclude_existing_ages: bool = True,  # Phase 16: 既存年齢を除外
    ) -> list[CandidatePriorityScore]:
        """
        候補リストを優先度順にソート

        Args:
            candidates: 候補リスト [{"person_id", "person_name", "category", "age"}, ...]
            top_n: 上位N件を返す
            min_score: 最低スコア閾値（これ未満は除外）
            exclude_existing_ages: 既存年齢を除外するか（デフォルトTrue）

        Returns:
            list[CandidatePriorityScore]: スコア順の候補
        """
        scored = []

        for c in candidates:
            score = self.score(
                person_id=c["person_id"],
                person_name=c["person_name"],
                category=c.get("category", ""),
                age=c.get("age", 30),
            )
            # Phase 16: 既存年齢は除外（same_age_duplicate防止）
            if exclude_existing_ages and score.age_coverage_score == 0:
                continue

            # Phase 12: 閾値以上のみ追加
            if score.score >= min_score:
                scored.append(score)

        # スコア降順でソート
        scored.sort(key=lambda x: x.score, reverse=True)

        return scored[:top_n]

    def get_priority_stats(self) -> dict:
        """
        優先度関連の統計を取得
        """
        ep_counts = self._get_ep_counts()
        category_counts = self._get_category_counts()

        if not ep_counts:
            return {
                "total_persons": 0,
                "avg_ep_per_person": 0,
                "category_distribution": {},
            }

        return {
            "total_persons": len(ep_counts),
            "total_episodes": sum(ep_counts.values()),
            "avg_ep_per_person": sum(ep_counts.values()) / len(ep_counts),
            "max_ep_person": max(ep_counts.items(), key=lambda x: x[1]) if ep_counts else None,
            "min_ep_persons": [k for k, v in ep_counts.items() if v <= 2][:10],
            "category_distribution": category_counts,
        }
