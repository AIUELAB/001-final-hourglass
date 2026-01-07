#!/usr/bin/env python3
"""
年齢別優先度分析スクリプト

GENERATEモード年齢の優先度を分析し、効率的な生成戦略を提案します。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from scripts.sage.config import MASTER_CSV
from scripts.sage.inventory_manager import InventoryManager, GenerationMode


def analyze_age_candidates():
    """年齢別の候補数を分析"""
    # マスターCSV読み込み
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")

    # REAL人物のみ
    real_df = df[df["person_type"] == "REAL"]

    # 人物ごとの既存年齢を取得
    person_ages = real_df.groupby("person_id")["age"].apply(set).to_dict()

    # 年齢別の候補数（その年齢のエピソードがない人物数）
    age_candidates = {}
    for age in range(0, 121):
        # この年齢のエピソードがない人物を数える
        count = sum(1 for ages in person_ages.values() if age not in ages)
        age_candidates[age] = count

    return age_candidates


def main():
    """メイン処理"""
    print("=" * 70)
    print("年齢別優先度分析")
    print("=" * 70)
    print()

    # インベントリ取得
    manager = InventoryManager()
    manager.refresh()

    # 候補数分析
    age_candidates = analyze_age_candidates()

    # GENERATEモード年齢のみ分析
    priority_ages = []
    for age in range(0, 121):
        status = manager.get_status(age)
        if status and status.mode == GenerationMode.GENERATE:
            candidates = age_candidates.get(age, 0)
            priority_ages.append(
                {
                    "age": age,
                    "current": status.upper_count,
                    "target": status.target,
                    "deficit": status.deficit,
                    "candidates": candidates,
                    # 優先度スコア: 不足数 × 候補数 / (年齢の極端さペナルティ)
                    "priority_score": status.deficit * candidates / (1 + abs(age - 40) / 20),
                }
            )

    # 優先度スコアでソート
    priority_ages.sort(key=lambda x: x["priority_score"], reverse=True)

    # 推奨年齢TOP20
    print("🎯 推奨生成年齢TOP20（優先度スコア順）:")
    print("-" * 70)
    print(f"{'年齢':>5} {'現在':>6} {'目標':>6} {'不足':>6} {'候補数':>8} {'優先度':>10}")
    print("-" * 70)

    for a in priority_ages[:20]:
        print(
            f"{a['age']:5d}歳 {a['current']:6d} {a['target']:6d} {a['deficit']:6d} {a['candidates']:8d} {a['priority_score']:10.0f}"
        )

    print()

    # 年齢帯別の推奨
    print("📊 年齢帯別推奨:")
    print("-" * 70)

    bands = [
        ("15-24歳（若年期）", 15, 25),
        ("25-34歳（青年期）", 25, 35),
        ("35-44歳（壮年期）", 35, 45),
        ("45-54歳（中年期）", 45, 55),
        ("55-64歳（熟年期）", 55, 65),
        ("65-79歳（高齢期）", 65, 80),
    ]

    for name, start, end in bands:
        band_ages = [a for a in priority_ages if start <= a["age"] < end]
        if band_ages:
            total_candidates = sum(a["candidates"] for a in band_ages)
            total_deficit = sum(a["deficit"] for a in band_ages)
            best = max(band_ages, key=lambda x: x["priority_score"])
            print(f"{name}:")
            print(f"  不足計: {total_deficit:,}件, 候補計: {total_candidates:,}人")
            print(f"  最優先: {best['age']}歳（候補{best['candidates']:,}人、不足{best['deficit']}件）")
            print()

    # 生成戦略提案
    print("=" * 70)
    print("💡 生成戦略提案:")
    print("=" * 70)
    print()
    print("1. 短期目標（次の100件）:")
    top_20_ages = [a["age"] for a in priority_ages[:20]]
    print(f"   優先年齢: {top_20_ages}")
    print()
    print("2. 中期目標（次の1,000件）:")
    print("   - 15-64歳に集中（候補が多く、エピソード生成が容易）")
    print("   - 80歳以上は一旦スキップ（候補が少なく、非現実的）")
    print()
    print("3. 長期目標:")
    achievable_deficit = sum(a["deficit"] for a in priority_ages if 15 <= a["age"] < 80)
    print(f"   - 15-79歳の不足: {achievable_deficit:,}件")
    print("   - 週100件ペースで約{:.0f}週間".format(achievable_deficit / 100))


if __name__ == "__main__":
    main()
