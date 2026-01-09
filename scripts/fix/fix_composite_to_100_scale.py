#!/usr/bin/env python3
"""
composite_scoreを0-100スケールに修正

composite_scoreは7軸スコアの平均 × 10 で、0-100スケールであるべき
誤って0-10スケールに修正してしまったので、元に戻す
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).parent.parent / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = (
    Path(__file__).parent.parent
    / f"MASTER_EPISODES_CURRENT_backup_before_100scale_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)


def calculate_composite_score_100(row: pd.Series) -> float:
    """7軸スコアからcomposite_scoreを計算（0-100スケール）"""
    seven_axes = []

    for axis in [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]:
        val = row.get(axis)
        if pd.notna(val):
            try:
                seven_axes.append(float(val))
            except (ValueError, TypeError):
                pass

    if len(seven_axes) == 7:
        # 7軸の平均 × 10 で0-100スケール
        return (sum(seven_axes) / 7) * 10
    else:
        return None


def main():
    print("=" * 80)
    print("📊 composite_scoreを0-100スケールに修正")
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
    print("Step 3: 現在のcomposite_score範囲確認...")
    current_min = df["composite_score"].min()
    current_max = df["composite_score"].max()
    current_avg = df["composite_score"].mean()
    print(f"  現在の範囲: {current_min:.2f} - {current_max:.2f}")
    print(f"  現在の平均: {current_avg:.2f}")
    print()

    # Step 4: 全エピソードのcomposite_scoreを再計算（0-100スケール）
    print("Step 4: composite_scoreを0-100スケールで再計算中...")
    fixed_count = 0
    skipped_count = 0

    for idx, row in df.iterrows():
        expected = calculate_composite_score_100(row)

        if expected is None:
            skipped_count += 1
            continue

        # composite_scoreを設定
        df.at[idx, "composite_score"] = expected
        fixed_count += 1

        # 進捗表示（100件ごと）
        if fixed_count % 100 == 0:
            print(f"  処理中: {fixed_count:,} / {len(df):,} 件 ({fixed_count / len(df) * 100:.1f}%)")

    print(f"  ✅ 修正完了: {fixed_count:,}件")
    print(f"  ⚠️  スキップ: {skipped_count:,}件（7軸スコア不完全）")
    print()

    # Step 5: 修正後の範囲確認
    print("Step 5: 修正後のcomposite_score範囲確認...")
    new_min = df["composite_score"].min()
    new_max = df["composite_score"].max()
    new_avg = df["composite_score"].mean()
    print(f"  修正後の範囲: {new_min:.2f} - {new_max:.2f}")
    print(f"  修正後の平均: {new_avg:.2f}")
    print()

    # Step 6: CSVファイル保存
    print("Step 6: CSVファイル保存中...")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    # Step 7: サンプル検証
    print("Step 7: サンプル検証...")
    verification_samples = [
        ("石ノ森章太郎", 66.0),
        ("AKB48", 22.0),
        ("森三郎", 25.0),
        ("棚橋弘至", 29.0),
        ("梶田隆章", 56.0),
    ]

    print("  サンプル:")
    for person_name, age in verification_samples:
        sample = df[(df["person_name"] == person_name) & (df["age"] == age)]

        if len(sample) == 0:
            continue

        row = sample.iloc[0]
        composite = row["composite_score"]

        print(f"    {person_name} ({age}歳): composite_score = {composite:.2f}")

    print()

    # サマリー
    print("=" * 80)
    print("✅ 全エピソードのcomposite_scoreを0-100スケールに修正しました！")
    print("=" * 80)
    print()
    print("📊 サマリー:")
    print(f"  - 修正件数: {fixed_count:,}件")
    print(f"  - スキップ件数: {skipped_count:,}件")
    print(f"  - 修正前平均: {current_avg:.2f}")
    print(f"  - 修正後平均: {new_avg:.2f}")
    print(f"  - 修正後範囲: {new_min:.2f} - {new_max:.2f}")
    print(f"  - バックアップ: {BACKUP_PATH}")
    print()


if __name__ == "__main__":
    main()
