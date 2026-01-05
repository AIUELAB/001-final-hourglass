#!/usr/bin/env python3
"""
大量生産用候補選定モジュール

多様性を担保しながら生成候補を選定
"""

import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

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
        # 数値変換
        for col in ["age", "birth_year", "death_year", "事実密度", "生成品質スコア"]:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        # 人物ごとの集約情報
        self.person_stats = self._compute_person_stats()

    def _compute_person_stats(self) -> pd.DataFrame:
        """人物ごとの統計情報を計算"""
        stats = (
            self.df.groupby("person_name")
            .agg(
                {
                    "person_id": "first",
                    "episode_id": "count",
                    "category": "first",
                    "birth_year": "first",
                    "death_year": "first",
                    "age": list,
                    "事実密度": "mean",
                    "生成品質スコア": "mean",
                }
            )
            .reset_index()
        )
        stats.columns = [
            "person_name",
            "person_id",
            "episode_count",
            "category",
            "birth_year",
            "death_year",
            "covered_ages",
            "avg_factual_density",
            "avg_generation_quality",
        ]
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
        """未カバー人物×年齢を取得"""
        candidates = []

        for _, person in self.person_stats.iterrows():
            if person["person_name"] in exclude_persons:
                continue

            birth = person.get("birth_year")
            death = person.get("death_year")
            covered_ages = set(person.get("covered_ages", []))

            if pd.isna(birth):
                continue

            birth = int(birth)
            death = int(death) if not pd.isna(death) else birth + 100

            # 重要な年齢帯（20-70歳）を優先
            important_ages = list(range(20, min(71, death - birth + 1)))

            for age in important_ages:
                if age not in covered_ages:
                    candidates.append(
                        SelectionCandidate(
                            person_id=person["person_id"],
                            person_name=person["person_name"],
                            age=age,
                            category=person["category"] or "その他",
                            birth_year=birth,
                            death_year=death if death != birth + 100 else None,
                            existing_episode_id=None,
                            selection_reason="uncovered_age",
                            priority_score=1.0 - (abs(age - 35) / 50),  # 35歳に近いほど高優先
                        )
                    )

            if len(candidates) >= count * 2:  # 十分な候補を確保
                break

        # 優先度でソートして返却
        candidates.sort(key=lambda c: c.priority_score, reverse=True)
        return candidates[:count]

    def _get_low_quality_candidates(
        self,
        count: int,
        exclude_persons: Set[str],
    ) -> List[SelectionCandidate]:
        """低品質EP置換対象を取得"""
        # 低品質EP（事実密度<7 or 生成品質<8）を抽出
        low_quality_df = self.df[(self.df["事実密度"] < 7.0) | (self.df["生成品質スコア"] < 8.0)].copy()

        # 除外人物をフィルタ
        low_quality_df = low_quality_df[~low_quality_df["person_name"].isin(exclude_persons)]

        # 優先度計算（品質が低いほど高優先）
        low_quality_df["priority"] = 14.0 - (
            low_quality_df["事実密度"].fillna(5) + low_quality_df["生成品質スコア"].fillna(5)
        )

        # ソートして上位を取得
        low_quality_df = low_quality_df.nlargest(count * 2, "priority")

        candidates = []
        for _, row in low_quality_df.iterrows():
            candidates.append(
                SelectionCandidate(
                    person_id=row.get("person_id", ""),
                    person_name=row["person_name"],
                    age=int(row["age"]) if not pd.isna(row["age"]) else 30,
                    category=row.get("category", "その他") or "その他",
                    birth_year=int(row["birth_year"]) if not pd.isna(row.get("birth_year")) else None,
                    death_year=int(row["death_year"]) if not pd.isna(row.get("death_year")) else None,
                    existing_episode_id=row.get("episode_id"),
                    selection_reason="low_quality_replacement",
                    priority_score=row["priority"] / 14.0,
                )
            )

        return candidates[:count]

    def _get_diversity_candidates(
        self,
        count: int,
        today: date,
        exclude_persons: Set[str],
        already_selected: Set[str],
    ) -> List[SelectionCandidate]:
        """多様性向上候補を取得"""
        # 今日のターゲットカテゴリ
        weekday = today.weekday()
        target_categories = self.config.weekday_categories.get(weekday, [])

        # カテゴリでフィルタ
        if target_categories:
            category_df = self.df[self.df["category"].isin(target_categories)]
        else:
            category_df = self.df

        # 除外人物をフィルタ
        category_df = category_df[~category_df["person_name"].isin(exclude_persons | already_selected)]

        # エピソード数が少ない人物を優先
        person_ep_counts = category_df.groupby("person_name").size()
        low_ep_persons = person_ep_counts[person_ep_counts <= 2].index.tolist()

        # 低EPカウント人物を優先
        priority_df = category_df[category_df["person_name"].isin(low_ep_persons)]

        if len(priority_df) < count:
            # 足りなければ全体から追加
            priority_df = pd.concat([priority_df, category_df]).drop_duplicates()

        # ランダムサンプリング
        sampled = priority_df.sample(min(count * 2, len(priority_df)))

        candidates = []
        seen_persons = set()

        for _, row in sampled.iterrows():
            person = row["person_name"]
            if person in seen_persons:
                continue
            seen_persons.add(person)

            # 新しい年齢を選択
            existing_ages = set(self.df[self.df["person_name"] == person]["age"].dropna().astype(int))
            birth = row.get("birth_year")
            death = row.get("death_year")

            if pd.isna(birth):
                new_age = 35  # デフォルト
            else:
                birth = int(birth)
                death = int(death) if not pd.isna(death) else birth + 80
                possible_ages = [a for a in range(20, min(71, death - birth)) if a not in existing_ages]
                new_age = random.choice(possible_ages) if possible_ages else 35

            candidates.append(
                SelectionCandidate(
                    person_id=row.get("person_id", ""),
                    person_name=person,
                    age=new_age,
                    category=row.get("category", "その他") or "その他",
                    birth_year=int(birth) if not pd.isna(row.get("birth_year")) else None,
                    death_year=int(death) if not pd.isna(row.get("death_year")) else None,
                    existing_episode_id=None,
                    selection_reason="diversity",
                    priority_score=0.5,
                )
            )

            if len(candidates) >= count:
                break

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
