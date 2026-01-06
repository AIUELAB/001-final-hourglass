#!/usr/bin/env python3
"""
大量生産用候補選定モジュール

多様性を担保しながら生成候補を選定
"""

import random
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.birth_year_database import get_birth_year, get_max_valid_age, CURRENT_YEAR

from .config import MassProductionConfig, SelectionConfig


@dataclass
class SelectionCandidate:
    """選定候補"""

    person_id: str
    person_name: str
    age: int
    category: str
    birth_year: Optional[int]
    death_year: Optional[int]
    existing_episode_id: Optional[str]  # 置換対象EPがある場合
    selection_reason: str  # 選定理由
    priority_score: float  # 優先度スコア


def get_valid_age_range(person_name: str) -> tuple[int, int]:
    """
    人物の有効な年齢範囲を取得

    Args:
        person_name: 人物名

    Returns:
        (min_age, max_age) タプル。生年不明の場合は (0, 130)
    """
    birth_year = get_birth_year(person_name)
    if birth_year is None:
        # 生年不明の場合、安全な範囲を設定（警告付き）
        return (0, 70)  # 高齢は避ける

    max_age = CURRENT_YEAR - birth_year
    return (0, max_age)


def is_valid_age(person_name: str, age: int) -> bool:
    """
    年齢が有効かどうかをチェック

    Args:
        person_name: 人物名
        age: チェック対象の年齢

    Returns:
        有効ならTrue
    """
    min_age, max_age = get_valid_age_range(person_name)
    return min_age <= age <= max_age


class MassProductionSelector:
    """大量生産用候補選定器"""

    def __init__(
        self,
        master_csv_path: Path,
        config: Optional[SelectionConfig] = None,
    ):
        """
        Args:
            master_csv_path: マスターCSVパス
            config: 選定設定
        """
        self.config = config or SelectionConfig()
        self.df = pd.read_csv(master_csv_path, dtype=str, low_memory=False)
        self._prepare_data()

    def _prepare_data(self) -> None:
        """データ前処理"""
        # 数値変換（存在するカラムのみ）
        numeric_cols = ["age", "事実密度", "生成品質スコア"]
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        # 人物ごとの集約情報
        self.person_stats = self._compute_person_stats()

    def _compute_person_stats(self) -> pd.DataFrame:
        """人物ごとの統計情報を計算"""
        # 基本集約
        agg_dict = {
            "person_id": "first",
            "episode_id": "count",
            "category": "first",
            "age": list,
        }

        # オプションカラム（存在する場合のみ）
        if "事実密度" in self.df.columns:
            agg_dict["事実密度"] = "mean"
        if "生成品質スコア" in self.df.columns:
            agg_dict["生成品質スコア"] = "mean"

        stats = self.df.groupby("person_name").agg(agg_dict).reset_index()

        # カラム名を正規化
        column_mapping = {
            "person_name": "person_name",
            "person_id": "person_id",
            "episode_id": "episode_count",
            "category": "category",
            "age": "covered_ages",
        }
        if "事実密度" in stats.columns:
            column_mapping["事実密度"] = "avg_factual_density"
        if "生成品質スコア" in stats.columns:
            column_mapping["生成品質スコア"] = "avg_generation_quality"

        stats = stats.rename(columns=column_mapping)

        # birth_year/death_yearは現在のCSVにないのでNoneとして追加
        if "birth_year" not in stats.columns:
            stats["birth_year"] = None
        if "death_year" not in stats.columns:
            stats["death_year"] = None
        if "avg_factual_density" not in stats.columns:
            stats["avg_factual_density"] = 5.0
        if "avg_generation_quality" not in stats.columns:
            stats["avg_generation_quality"] = 5.0

        return stats

    def select_candidates(
        self,
        target_count: int = 500,
        today: Optional[date] = None,
        exclude_persons: Optional[Set[str]] = None,
    ) -> List[SelectionCandidate]:
        """
        生成候補を選定

        Args:
            target_count: 目標候補数
            today: 基準日（カテゴリローテ用）
            exclude_persons: 除外人物セット

        Returns:
            選定候補リスト
        """
        today = today or date.today()
        exclude_persons = exclude_persons or set()

        candidates: List[SelectionCandidate] = []

        # 戦略1: 未カバー人物×年齢（優先度: 高）
        uncovered_count = int(target_count * self.config.uncovered_ratio)
        uncovered = self._get_uncovered_candidates(
            count=uncovered_count,
            exclude_persons=exclude_persons,
        )
        candidates.extend(uncovered)

        # 戦略2: 低品質EP置換対象（優先度: 中）
        low_quality_count = int(target_count * self.config.low_quality_ratio)
        low_quality = self._get_low_quality_candidates(
            count=low_quality_count,
            exclude_persons=exclude_persons,
        )
        candidates.extend(low_quality)

        # 戦略3: 多様性向上（優先度: 低）
        diversity_count = target_count - len(candidates)
        diversity = self._get_diversity_candidates(
            count=diversity_count,
            today=today,
            exclude_persons=exclude_persons,
            already_selected={c.person_name for c in candidates},
        )
        candidates.extend(diversity)

        # シャッフルして返却
        random.shuffle(candidates)
        return candidates[:target_count]

    def _get_uncovered_candidates(
        self,
        count: int,
        exclude_persons: Set[str],
    ) -> List[SelectionCandidate]:
        """未カバー人物×年齢を取得（年齢境界チェック付き）"""
        candidates = []
        skipped_age_boundary = 0

        for _, person in self.person_stats.iterrows():
            person_name = person["person_name"]
            if person_name in exclude_persons:
                continue

            # covered_agesをintのsetに変換（NaN除外）
            raw_ages = person.get("covered_ages", [])
            if raw_ages is None:
                raw_ages = []
            covered_ages = set()
            for a in raw_ages:
                try:
                    if not pd.isna(a):
                        covered_ages.add(int(float(a)))
                except (ValueError, TypeError):
                    pass

            # 生年データを取得して有効な年齢範囲を決定
            birth_year = get_birth_year(person_name)
            min_valid_age, max_valid_age = get_valid_age_range(person_name)

            # 重要な年齢帯（20-70歳）を優先、ただし有効範囲内のみ
            important_ages = [a for a in range(20, 71) if min_valid_age <= a <= max_valid_age]

            for age in important_ages:
                if age not in covered_ages:
                    # 年齢境界チェック
                    if not is_valid_age(person_name, age):
                        skipped_age_boundary += 1
                        continue

                    candidates.append(
                        SelectionCandidate(
                            person_id=person["person_id"],
                            person_name=person_name,
                            age=age,
                            category=person["category"] or "その他",
                            birth_year=birth_year,  # 生年データベースから取得
                            death_year=None,  # TODO: 没年データも統合
                            existing_episode_id=None,
                            selection_reason="uncovered_age",
                            priority_score=1.0 - (abs(age - 35) / 50),  # 35歳に近いほど高優先
                        )
                    )

            if len(candidates) >= count * 2:  # 十分な候補を確保
                break

        if skipped_age_boundary > 0:
            print(f"  ⚠️ 年齢境界違反でスキップ: {skipped_age_boundary}件")

        # 優先度でソートして返却
        candidates.sort(key=lambda c: c.priority_score, reverse=True)
        return candidates[:count]

    def _get_low_quality_candidates(
        self,
        count: int,
        exclude_persons: Set[str],
    ) -> List[SelectionCandidate]:
        """低品質EP置換対象を取得（年齢境界チェック付き）"""
        # 品質カラムが存在するかチェック
        has_factual = "事実密度" in self.df.columns
        has_quality = "生成品質スコア" in self.df.columns

        if not has_factual and not has_quality:
            return []  # 品質データなし

        # 低品質EP（事実密度<7 or 生成品質<8）を抽出
        conditions = []
        if has_factual:
            conditions.append(self.df["事実密度"] < 7.0)
        if has_quality:
            conditions.append(self.df["生成品質スコア"] < 8.0)

        if len(conditions) == 2:
            low_quality_df = self.df[conditions[0] | conditions[1]].copy()
        else:
            low_quality_df = self.df[conditions[0]].copy()

        # 除外人物をフィルタ
        low_quality_df = low_quality_df[~low_quality_df["person_name"].isin(exclude_persons)]

        if len(low_quality_df) == 0:
            return []

        # 優先度計算（品質が低いほど高優先）
        factual = low_quality_df["事実密度"].fillna(5) if has_factual else 5
        quality = low_quality_df["生成品質スコア"].fillna(5) if has_quality else 5
        low_quality_df["priority"] = 14.0 - (factual + quality)

        # ソートして上位を取得
        low_quality_df = low_quality_df.nlargest(min(count * 2, len(low_quality_df)), "priority")

        candidates = []
        skipped_age_boundary = 0
        for _, row in low_quality_df.iterrows():
            person_name = row["person_name"]
            age = int(row["age"]) if not pd.isna(row["age"]) else 30
            birth_year = get_birth_year(person_name)

            # 年齢境界チェック
            if not is_valid_age(person_name, age):
                skipped_age_boundary += 1
                continue

            candidates.append(
                SelectionCandidate(
                    person_id=row.get("person_id", ""),
                    person_name=person_name,
                    age=age,
                    category=row.get("category", "その他") or "その他",
                    birth_year=birth_year,  # 生年データベースから取得
                    death_year=None,
                    existing_episode_id=row.get("episode_id"),
                    selection_reason="low_quality_replacement",
                    priority_score=row["priority"] / 14.0,
                )
            )

        if skipped_age_boundary > 0:
            print(f"  ⚠️ 低品質候補で年齢境界違反スキップ: {skipped_age_boundary}件")

        return candidates[:count]

    def _get_diversity_candidates(
        self,
        count: int,
        today: date,
        exclude_persons: Set[str],
        already_selected: Set[str],
    ) -> List[SelectionCandidate]:
        """多様性向上候補を取得（年齢境界チェック付き）"""
        # 今日のターゲットカテゴリ
        weekday = today.weekday()
        target_categories = self.config.weekday_categories.get(weekday, [])

        # カテゴリでフィルタ
        if target_categories:
            category_df = self.df[self.df["category"].isin(target_categories)].copy()
        else:
            category_df = self.df.copy()

        # 除外人物をフィルタ
        category_df = category_df[~category_df["person_name"].isin(exclude_persons | already_selected)]

        if len(category_df) == 0:
            return []

        # エピソード数が少ない人物を優先
        person_ep_counts = category_df.groupby("person_name").size()
        low_ep_persons = person_ep_counts[person_ep_counts <= 2].index.tolist()

        # 低EPカウント人物を優先
        priority_df = category_df[category_df["person_name"].isin(low_ep_persons)]

        if len(priority_df) < count:
            # 足りなければ全体から追加
            priority_df = pd.concat([priority_df, category_df]).drop_duplicates()

        if len(priority_df) == 0:
            return []

        # ランダムサンプリング
        sampled = priority_df.sample(min(count * 2, len(priority_df)))

        candidates = []
        seen_persons = set()
        skipped_age_boundary = 0

        for _, row in sampled.iterrows():
            person = row["person_name"]
            if person in seen_persons:
                continue
            seen_persons.add(person)

            # 生年データを取得して有効範囲を決定
            birth_year = get_birth_year(person)
            min_valid_age, max_valid_age = get_valid_age_range(person)

            # 新しい年齢を選択（既存年齢を避け、有効範囲内のみ）
            existing_ages_raw = self.df[self.df["person_name"] == person]["age"].dropna()
            existing_ages = set()
            for a in existing_ages_raw:
                try:
                    existing_ages.add(int(float(a)))
                except (ValueError, TypeError):
                    pass

            # 20-70歳の範囲で未カバー年齢を選択（有効範囲内のみ）
            possible_ages = [a for a in range(20, 71) if a not in existing_ages and min_valid_age <= a <= max_valid_age]

            if not possible_ages:
                skipped_age_boundary += 1
                continue

            new_age = random.choice(possible_ages)

            candidates.append(
                SelectionCandidate(
                    person_id=row.get("person_id", ""),
                    person_name=person,
                    age=new_age,
                    category=row.get("category", "その他") or "その他",
                    birth_year=birth_year,  # 生年データベースから取得
                    death_year=None,
                    existing_episode_id=None,
                    selection_reason="diversity",
                    priority_score=0.5,
                )
            )

            if len(candidates) >= count:
                break

        if skipped_age_boundary > 0:
            print(f"  ⚠️ 多様性候補で年齢境界違反スキップ: {skipped_age_boundary}件")

        return candidates


def main():
    """デモ実行"""
    from .config import MASTER_CSV_PATH

    print("=== 大量生産候補選定デモ ===")

    selector = MassProductionSelector(MASTER_CSV_PATH)
    candidates = selector.select_candidates(target_count=50)

    print(f"\n選定候補数: {len(candidates)}件")
    print("\n選定理由別:")
    reasons = {}
    for c in candidates:
        reasons[c.selection_reason] = reasons.get(c.selection_reason, 0) + 1
    for reason, count in reasons.items():
        print(f"  {reason}: {count}件")

    print("\n上位10件:")
    for i, c in enumerate(candidates[:10], 1):
        print(f"  {i}. {c.person_name}（{c.age}歳）- {c.selection_reason}")


if __name__ == "__main__":
    main()
