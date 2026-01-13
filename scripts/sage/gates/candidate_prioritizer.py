"""
Candidate Prioritizer

候補の優先度スコアリングと最適な生成対象の選定。
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

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

    # スコアウェイト (Phase 15: 年齢在庫優先度追加, RCA-20260110: カテゴリ強化)
    EP_COUNT_WEIGHT = 0.35  # EP数少ない人物を優先 (0.4→0.35)
    CATEGORY_WEIGHT = 0.35  # 不足カテゴリを優先 (0.25→0.35: バランス改善)
    AGE_COVERAGE_WEIGHT = 0.10  # 未カバー年齢を優先 (0.15→0.10)
    INVENTORY_AGE_PRIORITY_WEIGHT = 0.20  # 年齢在庫不足を優先

    # Phase 16: 低成功率パターンのペナルティ（15歳スポーツ選手など）
    LOW_SUCCESS_PENALTY = 0.3  # 優先度を30%下げる
    LOW_SUCCESS_PATTERNS = [
        {"category_prefix": "スポーツ", "age_range": (10, 18)},  # 若年スポーツ選手
    ]

    # RCA-20260110-C: 過剰カテゴリの抑制（スポーツ9.3%→7%目標）
    EXCESS_CATEGORY_PENALTY = 0.4  # 優先度を40%下げる
    EXCESS_CATEGORIES = ["スポーツ"]  # 目標7%に対して9.3%で過剰

    # RCA-20260110: 不足カテゴリブースト（充足率改善）
    # 世紀のコンテンツ誕生エピソード強化対応
    DEFICIT_BOOST_THRESHOLD = 0.02  # 2%以上の不足でブースト
    DEFICIT_BOOST_MULTIPLIER = 1.5  # 不足カテゴリは1.5倍ブースト
    SEVERE_DEFICIT_CATEGORIES = [
        "芸術・文化",  # +610件必要（世紀の名作誕生強化）
        "文学",  # +492件必要
        "音楽",  # +390件必要（世紀の名曲誕生強化）
        "映画・演劇",  # 追加: 世紀の名映画誕生強化
        "科学・技術",  # 追加: 世紀の大発見誕生強化
        "医学・健康",  # +377件必要
        "歴史",  # +312件必要
        "哲学者",  # +269件必要
        "探検・冒険",  # +214件必要
        "動画・デジタルコンテンツ",  # 新規: 世紀の名動画誕生強化
    ]

    # RCA-20260110-B: 1EP人物の別年齢生成ブースト（候補枯渇対策）
    # 1EPのみの人物を別年齢で生成することで候補プールを拡大
    LOW_EP_BOOST_THRESHOLD = 2  # 2EP以下の人物にブースト
    LOW_EP_BOOST_MULTIPLIER = 2.0  # 1EP人物は2倍ブースト
    LOW_EP_DEFICIT_COMBO_MULTIPLIER = 3.0  # 1EP + 不足カテゴリは3倍ブースト

    # Q1対応: 平均寿命以下優先ロジック
    LIFESPAN_THRESHOLD = 80  # 平均寿命閾値
    # Q1対応: 80歳以下優先モード
    LIFESPAN_PRIORITY_PENALTY = 1.0  # 一時的に無効化（1-5歳候補枯渇のため81-100歳を許可）

    # RCA-20260110-D: 極端年齢の優先度ブースト（整合性修正版）
    # RCA-20260110: pre_generation_rules.pyのextreme_age_filterと整合
    # - 0-5歳: フィルターで除外されるためブースト対象外
    # - 90歳以上: 寿命検証がない場合除外されるためブースト削除
    # Phase 12: 10-14歳を4.0倍に強化（現状318件=1.7%、極端に低い）
    EXTREME_AGE_BOOST_CONFIG = {
        # 少年期（10-14歳）: 4倍ブースト（Phase 12強化: 318件=1.7%、極端に低い）
        "youth": {"age_range": (10, 14), "boost": 4.0},
        # 青年期（6-9歳）: 2倍ブースト（子役デビュー・神童系）
        "childhood": {"age_range": (6, 9), "boost": 2.0},
        # 高齢期（70-89歳）: 1.5倍ブースト（寿命内で生成可能）
        "elderly": {"age_range": (70, 89), "boost": 1.5},
    }

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
                    if pd.notna(age):  # type: ignore[arg-type]
                        if person_id not in self._person_ages:
                            self._person_ages[person_id] = set()  # type: ignore[index]
                        self._person_ages[person_id].add(int(age))  # type: ignore[index,arg-type]
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

        RCA-20260110: 深刻な不足カテゴリにブーストを適用
        """
        category_counts = self._get_category_counts()
        total = sum(category_counts.values()) if category_counts else 1

        # 現在の割合
        current_ratio = category_counts.get(category, 0) / total

        # 目標割合
        target_ratios = self.targets.get("category_distribution", {})
        target_ratio = target_ratios.get(category, 1 / len(target_ratios) if target_ratios else 0.1)  # type: ignore[union-attr]

        # 不足度を計算 (目標より少ないほど高スコア)
        deficit = max(0, target_ratio - current_ratio)
        score = deficit * 500  # 0-50の範囲に正規化

        # RCA-20260110: 深刻な不足カテゴリにブースト適用
        if category in self.SEVERE_DEFICIT_CATEGORIES:
            score *= self.DEFICIT_BOOST_MULTIPLIER

        return min(75, score)  # 上限を50→75に引き上げ

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

    def _get_lifespan_deficit(self) -> int:
        """
        80歳以下の年齢の総deficit数を取得

        Returns:
            int: 80歳以下の総deficit
        """
        if not self._inventory_manager:
            return 0

        total_deficit = 0
        for age in range(1, self.LIFESPAN_THRESHOLD + 1):  # 1-80歳
            status = self._inventory_manager.get_status(age)
            if status and status.deficit > 0:
                total_deficit += status.deficit
        return total_deficit

    def _calculate_extreme_age_boost(self, age: int) -> float:
        """
        RCA-20260110-D: 極端年齢のブースト倍率を計算

        年齢分布分析に基づき、不足が深刻な年齢帯にブーストを適用:
        - 90-100歳: 5倍（平均11件/歳、深刻）
        - 1-9歳: 3倍（平均76件/歳、中程度）
        - 70-89歳: 2倍（100件未満多数）
        - 10-14歳: 1.5倍（不足傾向）

        Returns:
            float: ブースト倍率（1.0-5.0）
        """
        for config in self.EXTREME_AGE_BOOST_CONFIG.values():
            age_min, age_max = config["age_range"]  # type: ignore[index]
            if age_min <= age <= age_max:
                return config["boost"]  # type: ignore[return-value]
        return 1.0  # ブーストなし

    def _calculate_inventory_age_priority_score(self, age: int) -> float:
        """
        年齢在庫優先度スコアを計算（Phase 15 + Phase 3最適化 + RCA-20260110-D）

        不足数が多い年齢を優先。極端年齢で低カバレッジの場合は
        年齢ペナルティを軽減してブーストする。

        RCA-20260110-D: 超高齢（90-100歳）を大幅ブースト
        - 90-100歳: 5x相当のブースト（ペナルティ1/5軽減 + 追加ブースト2x）
        - 85-89歳: 2x相当のブースト（ペナルティ1/2軽減 + 追加ブースト1.5x）
        - 0-10歳、80-84歳: 従来通りのブースト

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
        target = self.targets.get(age, 400)  # type: ignore[arg-type]
        current = target - deficit
        coverage_rate = current / target if target > 0 else 1.0

        # Phase 3最適化 + RCA-20260110-D: 極端年齢ブースト
        # 90-100歳は5xブースト（super_elderly）、85-89は中程度ブースト
        is_safe_extreme_age = (age <= 10) or (80 <= age <= 84)
        is_super_elderly = age >= 90  # RCA-20260110-D: 超高齢は特別扱い
        is_elderly_risky = 85 <= age <= 89  # 中程度のリスク
        is_very_low_coverage = coverage_rate < 0.15  # 15%未満

        if is_super_elderly:
            # RCA-20260110-D: 90歳以上は大幅ブースト（5x相当のペナルティ軽減）
            age_penalty = 1.0 + abs(age - 40) / 100  # 1/5に軽減
            extreme_boost = 2.0  # 追加ブースト
        elif is_elderly_risky:
            # 85-89歳: 中程度のブースト（2x相当のペナルティ軽減）
            age_penalty = 1.0 + abs(age - 40) / 40  # 1/2に軽減
            extreme_boost = 1.5
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

        # Q1対応: 平均寿命（80歳）以下を優先
        if age <= self.LIFESPAN_THRESHOLD:
            raw_score *= 1.3  # 30%ブースト（平均寿命以下優先）

        # Q1対応: 80歳以下優先モード
        # 80歳以下にdeficitが残っている間は、81歳以上のスコアを大幅に抑制
        if age > self.LIFESPAN_THRESHOLD:
            lifespan_deficit = self._get_lifespan_deficit()
            if lifespan_deficit > 0:
                # 80歳以下のdeficitが残っている → 81歳以上を抑制
                raw_score *= self.LIFESPAN_PRIORITY_PENALTY
                logger.debug(f"Q1優先モード: age {age} を抑制 (80歳以下deficit={lifespan_deficit})")

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
            if category.startswith(cat_prefix) and age_min <= age <= age_max:  # type: ignore[arg-type,operator]
                total_score *= 1.0 - self.LOW_SUCCESS_PENALTY
                break

        # RCA-20260110-B: 1EP人物の別年齢生成ブースト
        # 不足カテゴリで1-2EPの人物を優先して候補枯渇を解消
        if ep_count <= self.LOW_EP_BOOST_THRESHOLD:
            is_deficit_category = category in self.SEVERE_DEFICIT_CATEGORIES
            if ep_count == 1 and is_deficit_category:
                # 1EP + 不足カテゴリ: 最大ブースト
                total_score *= self.LOW_EP_DEFICIT_COMBO_MULTIPLIER
            elif ep_count <= 2 and is_deficit_category:
                # 2EP + 不足カテゴリ: 中程度ブースト
                total_score *= self.LOW_EP_BOOST_MULTIPLIER
            elif ep_count == 1:
                # 1EPのみ: 軽ブースト
                total_score *= 1.5

        # RCA-20260110-C: 過剰カテゴリの抑制
        if category in self.EXCESS_CATEGORIES:
            total_score *= 1.0 - self.EXCESS_CATEGORY_PENALTY

        # RCA-20260110-D: 極端年齢の優先度ブースト
        # 90-100歳（5x）、1-9歳（3x）、70-89歳（2x）、10-14歳（1.5x）
        extreme_age_boost = self._calculate_extreme_age_boost(age)
        if extreme_age_boost > 1.0:
            total_score *= extreme_age_boost

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
                },
                "extreme_age_boost": extreme_age_boost,
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
