#!/usr/bin/env python3
"""
スロット割り当てスクリプト

全エピソードに年齢ベースでスロット値（1, 10, 20, 30, 40, 50, 60）を割り当てる
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT_backup_before_slot_assignment.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / f"slot_assignment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# スロット定義
SLOTS = [1, 10, 20, 30, 40, 50, 60]


def assign_slot_by_age(age: float) -> int:
    """
    実年齢から最も近いスロット値を返す

    Args:
        age: 実年齢

    Returns:
        スロット値（1, 10, 20, 30, 40, 50, 60のいずれか）
    """
    if pd.isna(age):
        return None

    # 最も近いスロットを探す
    return min(SLOTS, key=lambda slot: abs(age - slot))


def validate_slot_assignment(df: pd.DataFrame) -> dict:
    """
    スロット割り当ての検証

    Args:
        df: エピソードDataFrame

    Returns:
        検証結果の辞書
    """
    validation = {
        "total_episodes": int(len(df)),
        "slots_assigned": int(df["slot"].notna().sum()),
        "slots_missing": int(df["slot"].isna().sum()),
        "slot_distribution": {int(k): int(v) for k, v in df["slot"].value_counts().to_dict().items() if pd.notna(k)},
        "age_slot_consistency": [],
    }

    # 年齢とスロットの一貫性チェック
    for slot in SLOTS:
        slot_episodes = df[df["slot"] == slot]
        if len(slot_episodes) > 0:
            avg_age = slot_episodes["age"].mean()
            min_age = slot_episodes["age"].min()
            max_age = slot_episodes["age"].max()
            validation["age_slot_consistency"].append(
                {
                    "slot": int(slot),
                    "count": int(len(slot_episodes)),
                    "avg_age": round(float(avg_age), 2),
                    "min_age": float(min_age),
                    "max_age": float(max_age),
                    "expected_range": get_expected_age_range(slot),
                }
            )

    return validation


def get_expected_age_range(slot: int) -> str:
    """スロットの期待年齢範囲を返す"""
    ranges = {1: "0-5歳", 10: "6-15歳", 20: "16-25歳", 30: "26-35歳", 40: "36-45歳", 50: "46-55歳", 60: "56歳以上"}
    return ranges.get(slot, "不明")


def assign_slots():
    """スロット割り当てのメイン処理"""

    print("=" * 80)
    print("📋 スロット割り当てスクリプト")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # Step 2: バックアップ作成
    print("Step 2: バックアップ作成中...")
    df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
    print()

    # Step 3: 現在の状態確認
    print("Step 3: 現在の状態確認")
    if "slot" not in df.columns:
        print("  ℹ️  'slot'カラムが存在しないため、新規作成します")
        df["slot"] = None
    else:
        slots_assigned = df["slot"].notna().sum()
        print(f"  既存のスロット割り当て: {slots_assigned}件 ({slots_assigned / len(df) * 100:.1f}%)")

    age_missing = df["age"].isna().sum()
    print(f"  年齢欠損: {age_missing}件 ({age_missing / len(df) * 100:.1f}%)")
    print()

    # Step 4: スロット割り当て
    print("Step 4: スロット割り当て中...")

    # 年齢が存在するエピソードにスロットを割り当て
    df["slot"] = df["age"].apply(assign_slot_by_age)

    slots_assigned = df["slot"].notna().sum()
    print(f"  ✅ スロット割り当て完了: {slots_assigned:,}件")
    print()

    # Step 5: 検証
    print("Step 5: スロット割り当ての検証")
    validation = validate_slot_assignment(df)

    print(f"  総エピソード数: {validation['total_episodes']:,}件")
    print(
        f"  スロット割り当て済み: {validation['slots_assigned']:,}件 ({validation['slots_assigned'] / validation['total_episodes'] * 100:.1f}%)"
    )
    print(f"  スロット未割り当て: {validation['slots_missing']:,}件")
    print()

    print("  スロット別分布:")
    for slot in SLOTS:
        count = validation["slot_distribution"].get(float(slot), 0)
        pct = count / validation["total_episodes"] * 100 if validation["total_episodes"] > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"    slot {slot:2d}: {count:4d}件 ({pct:5.1f}%) {bar}")
    print()

    print("  年齢-スロット一貫性チェック:")
    for consistency in validation["age_slot_consistency"]:
        print(
            f"    slot {consistency['slot']:2d} ({consistency['expected_range']:12s}): "
            f"平均{consistency['avg_age']:.1f}歳 "
            f"[{consistency['min_age']:.0f}-{consistency['max_age']:.0f}歳] "
            f"{consistency['count']:4d}件"
        )
    print()

    # Step 6: CSVファイル保存
    print("Step 6: CSVファイル保存中...")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    # Step 7: レポート保存
    print("Step 7: レポート保存中...")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "csv_path": str(CSV_PATH),
        "backup_path": str(BACKUP_PATH),
        "validation": validation,
        "slot_definition": {"slots": SLOTS, "assignment_method": "age_based", "version": "1.0"},
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"  ✅ レポート保存: {REPORT_PATH}")
    print()

    # サマリー
    print("=" * 80)
    print("✅ スロット割り当てが完了しました！")
    print("=" * 80)
    print()
    print("📊 サマリー:")
    print(f"  - 総エピソード数: {validation['total_episodes']:,}件")
    print(f"  - スロット割り当て済み: {validation['slots_assigned']:,}件")
    print(f"  - スロット未割り当て: {validation['slots_missing']:,}件")
    print(f"  - バックアップ: {BACKUP_PATH}")
    print(f"  - レポート: {REPORT_PATH}")
    print()


def show_sample_assignments(n: int = 10):
    """サンプルのスロット割り当てを表示"""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    print("=" * 80)
    print(f"📋 サンプルスロット割り当て（{n}件）")
    print("=" * 80)
    print()

    sample = df[df["slot"].notna()].sample(min(n, len(df)))

    for _, row in sample.iterrows():
        print(f"  {row['episode_id']}")
        print(f"    人物: {row['person_name']}")
        print(f"    年齢: {row['age']:.0f}歳 → スロット: {int(row['slot'])}")
        print(f"    カテゴリ: {row['category']}")
        print()


if __name__ == "__main__":
    assign_slots()
    print()
    show_sample_assignments(10)
