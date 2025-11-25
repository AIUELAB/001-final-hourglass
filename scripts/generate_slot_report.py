#!/usr/bin/env python3
"""
スロット割り当てレポート生成スクリプト
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / f"slot_assignment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# スロット定義
SLOTS = [1, 10, 20, 30, 40, 50, 60]


def get_expected_age_range(slot: int) -> str:
    """スロットの期待年齢範囲を返す"""
    ranges = {
        1: "0-5歳",
        10: "6-15歳",
        20: "16-25歳",
        30: "26-35歳",
        40: "36-45歳",
        50: "46-55歳",
        60: "56歳以上"
    }
    return ranges.get(slot, "不明")


def generate_report():
    """レポート生成"""
    print("=" * 80)
    print("📋 スロット割り当てレポート生成")
    print("=" * 80)
    print()

    # CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # 検証データ収集
    print("Step 2: 検証データ収集中...")
    validation = {
        "total_episodes": int(len(df)),
        "slots_assigned": int(df['slot'].notna().sum()),
        "slots_missing": int(df['slot'].isna().sum()),
        "slot_distribution": {int(k): int(v) for k, v in df['slot'].value_counts().to_dict().items() if pd.notna(k)},
        "age_slot_consistency": []
    }

    # 年齢とスロットの一貫性チェック
    for slot in SLOTS:
        slot_episodes = df[df['slot'] == slot]
        if len(slot_episodes) > 0:
            avg_age = slot_episodes['age'].mean()
            min_age = slot_episodes['age'].min()
            max_age = slot_episodes['age'].max()
            validation["age_slot_consistency"].append({
                "slot": int(slot),
                "count": int(len(slot_episodes)),
                "avg_age": round(float(avg_age), 2),
                "min_age": float(min_age),
                "max_age": float(max_age),
                "expected_range": get_expected_age_range(slot)
            })

    print(f"  ✅ 検証完了")
    print()

    # レポート作成
    print("Step 3: レポート作成中...")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "csv_path": str(CSV_PATH),
        "validation": validation,
        "slot_definition": {
            "slots": SLOTS,
            "assignment_method": "age_based",
            "version": "1.0"
        }
    }

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"  ✅ レポート保存: {REPORT_PATH}")
    print()

    # サマリー表示
    print("=" * 80)
    print("📊 スロット割り当てサマリー")
    print("=" * 80)
    print()
    print(f"総エピソード数: {validation['total_episodes']:,}件")
    print(f"スロット割り当て済み: {validation['slots_assigned']:,}件 ({validation['slots_assigned'] / validation['total_episodes'] * 100:.1f}%)")
    print(f"スロット未割り当て: {validation['slots_missing']:,}件")
    print()

    print("スロット別分布:")
    for slot in SLOTS:
        count = validation['slot_distribution'].get(slot, 0)
        pct = count / validation['total_episodes'] * 100 if validation['total_episodes'] > 0 else 0
        bar = '█' * int(pct / 2)
        print(f"  slot {slot:2d}: {count:4d}件 ({pct:5.1f}%) {bar}")
    print()

    print("年齢-スロット一貫性チェック:")
    for consistency in validation['age_slot_consistency']:
        print(f"  slot {consistency['slot']:2d} ({consistency['expected_range']:12s}): "
              f"平均{consistency['avg_age']:.1f}歳 "
              f"[{consistency['min_age']:.0f}-{consistency['max_age']:.0f}歳] "
              f"{consistency['count']:4d}件")
    print()

    print("=" * 80)
    print("✅ レポート生成が完了しました！")
    print("=" * 80)


if __name__ == "__main__":
    generate_report()
