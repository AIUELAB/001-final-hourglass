#!/usr/bin/env python3
"""
有名人度ランキング計算スクリプト

fame_score_v2（表示用スコア）とは別に、fame_rank（一意な順位）を計算する。
タイブレーカーを適用して同率をほぼ0に抑制する。

Usage:
    # ドライラン（変更なし、結果確認のみ）
    python scripts/calculate_fame_rank.py --dry-run

    # 実行（CSV更新）
    python scripts/calculate_fame_rank.py --execute

    # 品質チェックのみ
    python scripts/calculate_fame_rank.py --check
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

# プロジェクトルート
project_root = Path(__file__).parent.parent


def calculate_fame_rank(df: pd.DataFrame) -> pd.DataFrame:
    """
    fame_rank を計算して追加

    タイブレーカー優先順位:
    1. fame_score_v2 (DESC) - 基本スコア
    2. wikipedia_pv (DESC) - 同点時はPV高い方が上位
    3. person_id (ASC) - 完全一致時はID順で一意化
    """
    # 人物単位でユニーク化
    person_df = (
        df.groupby("person_id")
        .agg(
            {
                "person_name": "first",
                "fame_score_v2": "first",
                "wikipedia_pv": "first",
            }
        )
        .reset_index()
    )

    # 欠損値を0で埋める（ソート用）
    person_df["fame_score_v2"] = person_df["fame_score_v2"].fillna(0)
    person_df["wikipedia_pv"] = person_df["wikipedia_pv"].fillna(0)

    # ソート（タイブレーカー適用）
    person_df = person_df.sort_values(
        by=["fame_score_v2", "wikipedia_pv", "person_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    # ランク付与（1始まり）
    person_df["fame_rank"] = range(1, len(person_df) + 1)

    # 元DFにマージ
    rank_map = person_df.set_index("person_id")["fame_rank"]
    df["fame_rank"] = df["person_id"].map(rank_map)

    return df


def check_fame_ranking_quality(df: pd.DataFrame) -> Dict:
    """ランキング品質チェック"""
    # 人物単位でユニーク化
    person_ranks = df.groupby("person_id")["fame_rank"].first().dropna()
    person_scores = df.groupby("person_id")["fame_score_v2"].first().dropna()

    # 同率サイズ分布
    rank_counts = person_ranks.value_counts()
    score_counts = person_scores.value_counts()

    # Top 10のランク確認
    top_10 = (
        df.groupby("person_id")
        .agg(
            {
                "person_name": "first",
                "fame_score_v2": "first",
                "wikipedia_pv": "first",
                "fame_rank": "first",
            }
        )
        .sort_values("fame_rank")
        .head(10)
    )

    return {
        "total_persons": len(person_ranks),
        "unique_ranks": person_ranks.nunique(),
        "unique_scores": person_scores.nunique(),
        "rank_unique_ratio": person_ranks.nunique() / len(person_ranks) * 100,
        "score_unique_ratio": person_scores.nunique() / len(person_scores) * 100,
        "first_place_rank_count": (person_ranks == 1).sum(),
        "first_place_score_count": (person_scores == person_scores.max()).sum(),
        "max_rank_tie_size": rank_counts.max() if len(rank_counts) > 0 else 0,
        "max_score_tie_size": score_counts.max() if len(score_counts) > 0 else 0,
        "is_rank_valid": person_ranks.nunique() == len(person_ranks),
        "top_10": top_10.to_dict("records"),
    }


def print_quality_report(quality: Dict):
    """品質レポートを表示"""
    print("=" * 70)
    print("有名人度ランキング 品質レポート")
    print("=" * 70)

    print(f"\n総人物数: {quality['total_persons']:,}")

    print("\n--- fame_rank（順位）---")
    print(f"ユニーク順位数: {quality['unique_ranks']:,}")
    print(f"ユニーク率: {quality['rank_unique_ratio']:.2f}%")
    print(f"1位人数: {quality['first_place_rank_count']}")
    print(f"同率最大サイズ: {quality['max_rank_tie_size']}")
    print(f"ランキング有効: {'✅ YES' if quality['is_rank_valid'] else '❌ NO'}")

    print("\n--- fame_score_v2（スコア）---")
    print(f"ユニークスコア数: {quality['unique_scores']:,}")
    print(f"ユニーク率: {quality['score_unique_ratio']:.2f}%")
    print(f"最高スコア同率人数: {quality['first_place_score_count']}")
    print(f"同率最大サイズ: {quality['max_score_tie_size']}")

    print("\n--- Top 10 ランキング ---")
    for item in quality["top_10"]:
        pv = int(item["wikipedia_pv"]) if pd.notna(item["wikipedia_pv"]) else 0
        print(
            f"  {item['fame_rank']:>4}位: {item['person_name'][:15]:<15} "
            f"score={item['fame_score_v2']:.2f} PV={pv:,}"
        )

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="有名人度ランキング計算")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（CSV更新しない）")
    parser.add_argument("--execute", action="store_true", help="実行（CSV更新する）")
    parser.add_argument("--check", action="store_true", help="品質チェックのみ")
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=project_root / "preserved/data/MASTER_EPISODES_CURRENT.csv",
        help="CSVファイルパス",
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute and not args.check:
        print("⚠️ --dry-run, --execute, または --check を指定してください")
        return

    # CSV読み込み
    print(f"📂 CSV読み込み: {args.csv_path}")
    df = pd.read_csv(args.csv_path, encoding="utf-8-sig", low_memory=False)
    print(f"📊 総レコード数: {len(df):,}")

    if args.check:
        # 既存のfame_rankがあれば品質チェック
        if "fame_rank" not in df.columns:
            print("⚠️ fame_rank列がありません。--execute で計算してください。")
            return
        quality = check_fame_ranking_quality(df)
        print_quality_report(quality)
        return

    # fame_rank計算
    print("\n🔄 fame_rank 計算中...")
    df = calculate_fame_rank(df)

    # 品質チェック
    quality = check_fame_ranking_quality(df)
    print_quality_report(quality)

    if args.dry_run:
        print("\n🔍 ドライラン完了（CSV更新なし）")
        return

    if args.execute:
        # バックアップ作成
        backup_path = args.csv_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        shutil.copy(args.csv_path, backup_path)
        print(f"\n💾 バックアップ作成: {backup_path.name}")

        # CSV保存
        df.to_csv(args.csv_path, encoding="utf-8-sig", index=False)
        print(f"✅ CSV更新完了: {args.csv_path}")

        # 検証
        if quality["is_rank_valid"]:
            print("\n✅ 品質ゲート: PASSED")
            print(f"   - 1位人数: {quality['first_place_rank_count']} (期待値: 1)")
            print(f"   - 同率最大: {quality['max_rank_tie_size']} (期待値: 1)")
            print(f"   - ユニーク率: {quality['rank_unique_ratio']:.2f}% (期待値: 100%)")
        else:
            print("\n⚠️ 品質ゲート: FAILED - 同率が残っています")


if __name__ == "__main__":
    main()
