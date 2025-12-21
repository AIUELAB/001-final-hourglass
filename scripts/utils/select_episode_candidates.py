#!/usr/bin/env python3
"""
エピソード追加候補選定スクリプト

Phase 1: 全年齢100本達成のための人物・年齢マッチング
- 不足している年齢を特定
- fame_score上位人物から候補を抽出
- 年齢×人物のマッチングを実行
"""

import pandas as pd
import argparse
from datetime import datetime


class EpisodeCandidateSelector:
    """エピソード追加候補の選定"""

    def __init__(self, master_csv: str = "preserved/data/MASTER_EPISODES_CURRENT.csv"):
        self.df = pd.read_csv(master_csv)
        self.person_stats = self._calculate_person_stats()

    def _calculate_person_stats(self) -> pd.DataFrame:
        """人物ごとの統計を計算"""
        stats = (
            self.df.groupby("person_name")
            .agg(
                {
                    "fame_score": "first",
                    "episode_id": "count",
                    "age": list,
                    "category": "first",
                    "person_type": "first",
                }
            )
            .rename(columns={"episode_id": "ep_count", "age": "covered_ages"})
        )

        # 有効な行のみ抽出
        stats = stats[stats["fame_score"].notna()]
        return stats.sort_values("fame_score", ascending=False)

    def get_age_gaps(self, target: int = 100) -> pd.DataFrame:
        """各年齢の不足数を計算"""
        age_stats = []
        for age in range(0, 81):
            count = len(self.df[self.df["age"] == age])
            gap = max(0, target - count)
            age_stats.append({"age": age, "current": count, "target": target, "gap": gap})

        return pd.DataFrame(age_stats).sort_values("gap", ascending=False)

    def select_candidates_for_age(self, target_age: int, needed: int, min_fame: float = 3.0) -> list[dict]:
        """
        特定年齢のエピソード候補を選定

        Args:
            target_age: 対象年齢
            needed: 必要なエピソード数
            min_fame: 最低fame_score

        Returns:
            候補リスト
        """
        candidates = []

        # 既にこの年齢でエピソードがある人物を除外
        existing_persons = set(self.df[self.df["age"] == target_age]["person_name"].unique())

        # fame_score順に人物を検討
        for person_name, row in self.person_stats.iterrows():
            if len(candidates) >= needed:
                break

            # 既存の人物はスキップ
            if person_name in existing_persons:
                continue

            # fame_score閾値チェック
            if row["fame_score"] < min_fame:
                continue

            # FICTIONAL人物は一部年齢帯のみ
            if row["person_type"] == "FICTIONAL" and target_age > 50:
                continue

            candidates.append(
                {
                    "person_name": person_name,
                    "age": target_age,
                    "category": row["category"],
                    "fame_score": row["fame_score"],
                    "existing_eps": row["ep_count"],
                }
            )

        return candidates

    def generate_phase1_template(self, target_per_age: int = 100, output_path: str = None) -> pd.DataFrame:
        """
        Phase 1用のテンプレートを生成

        Args:
            target_per_age: 各年齢の目標本数
            output_path: 出力ファイルパス

        Returns:
            テンプレートDataFrame
        """
        all_candidates = []
        age_gaps = self.get_age_gaps(target_per_age)

        print("=" * 60)
        print(f"Phase 1 テンプレート生成 (目標: 各年齢{target_per_age}本)")
        print("=" * 60)

        for _, row in age_gaps.iterrows():
            age = int(row["age"])
            gap = int(row["gap"])

            if gap <= 0:
                continue

            # 年齢帯に応じたfame_score閾値
            if age <= 9 or age >= 70:
                min_fame = 5.0  # 難しい年齢帯は有名人に限定
            elif age <= 19:
                min_fame = 4.0
            else:
                min_fame = 3.0

            candidates = self.select_candidates_for_age(age, gap, min_fame)
            all_candidates.extend(candidates)

            print(f"  {age}歳: {len(candidates)}/{gap}件の候補を選定 (min_fame={min_fame})")

        result_df = pd.DataFrame(all_candidates)

        if output_path:
            result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(f"\n✅ テンプレートを保存: {output_path}")
            print(f"   総候補数: {len(result_df):,}件")

        return result_df


def main():
    parser = argparse.ArgumentParser(description="エピソード追加候補を選定")
    parser.add_argument(
        "--target",
        type=int,
        default=100,
        help="各年齢の目標エピソード数 (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="出力CSVファイルパス",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="分析のみ実行（テンプレート生成なし）",
    )

    args = parser.parse_args()

    selector = EpisodeCandidateSelector()

    if args.analyze_only:
        # 分析のみ
        print("=" * 60)
        print("現状分析")
        print("=" * 60)

        age_gaps = selector.get_age_gaps(args.target)
        total_gap = age_gaps["gap"].sum()

        print(f"\n目標: 各年齢{args.target}本")
        print(f"現在の総不足: {total_gap:,}件")
        print(f"不足年齢数: {len(age_gaps[age_gaps['gap'] > 0])}個")

        print("\n【年齢帯別サマリー】")
        for start, end in [(0, 9), (10, 19), (20, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 80)]:
            band = age_gaps[(age_gaps["age"] >= start) & (age_gaps["age"] <= end)]
            print(f"  {start}-{end}歳: 不足{band['gap'].sum():,}件")

    else:
        # テンプレート生成
        output = args.output or f"templates/phase1_candidates_{datetime.now().strftime('%Y%m%d')}.csv"
        selector.generate_phase1_template(args.target, output)


if __name__ == "__main__":
    main()
