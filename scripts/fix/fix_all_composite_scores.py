#!/usr/bin/env python3
"""
全エピソードのcomposite_score修正スクリプト

composite_scoreは本来0-10スケール（7軸スコアの平均）であるべきだが、
多くのエピソードで10倍されている。全エピソードを正しい値に修正する。

修正方法: 7軸スコアの平均を再計算して設定
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).parent.parent / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = (
    Path(__file__).parent.parent
    / f"MASTER_EPISODES_CURRENT_backup_before_fix_all_composite_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)


def calculate_composite_score(row: pd.Series) -> float:
    """7軸スコアからcomposite_scoreを計算（共通ロジック）"""
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
        return sum(seven_axes) / 7
    else:
        return None


def main():
    print("=" * 80)
    print("📊 全エピソードのcomposite_score修正")
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

    # Step 3: 修正対象の確認
    print("Step 3: 修正対象の確認中...")
    needs_fix_count = 0
    already_correct_count = 0
    missing_7axes_count = 0

    for idx, row in df.iterrows():
        expected = calculate_composite_score(row)
        actual = row.get("composite_score")

        if expected is None:
            missing_7axes_count += 1
            continue

        if pd.isna(actual):
            needs_fix_count += 1
            continue

        diff = abs(actual - expected)
        if diff >= 0.0001:
            needs_fix_count += 1
        else:
            already_correct_count += 1

    print(f"  修正必要: {needs_fix_count:,}件")
    print(f"  既に正しい: {already_correct_count:,}件")
    print(f"  7軸スコア不完全: {missing_7axes_count:,}件")
    print()

    # Step 4: 全エピソードのcomposite_scoreを再計算
    print("Step 4: composite_scoreを再計算中...")
    fixed_count = 0
    skipped_count = 0

    for idx, row in df.iterrows():
        expected = calculate_composite_score(row)

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

    # Step 5: CSVファイル保存
    print("Step 5: CSVファイル保存中...")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    # Step 6: 検証
    print("Step 6: 修正結果の検証...")
    df_verify = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    verification_samples = [
        ("石ノ森章太郎", 66.0),
        ("AKB48", 22.0),
        ("森三郎", 25.0),
        ("棚橋弘至", 29.0),
        ("梶田隆章", 56.0),
    ]

    print("  サンプル検証:")
    all_ok = True

    for person_name, age in verification_samples:
        sample = df_verify[(df_verify["person_name"] == person_name) & (df_verify["age"] == age)]

        if len(sample) == 0:
            continue

        row = sample.iloc[0]
        expected = calculate_composite_score(row)
        actual = row["composite_score"]

        if expected is None:
            continue

        diff = abs(actual - expected)
        status = "✅" if diff < 0.0001 else "❌"

        print(f"    {status} {person_name} ({age}歳): {actual:.6f} (期待={expected:.6f})")

        if diff >= 0.0001:
            all_ok = False

    print()

    # 全体の一貫性チェック
    print("  全体の一貫性チェック:")
    consistent_count = 0
    inconsistent_count = 0

    for idx, row in df_verify.iterrows():
        expected = calculate_composite_score(row)
        actual = row.get("composite_score")

        if expected is None:
            continue

        if pd.isna(actual):
            continue

        diff = abs(actual - expected)
        if diff < 0.0001:
            consistent_count += 1
        else:
            inconsistent_count += 1

    print(f"    一致: {consistent_count:,}件")
    print(f"    不一致: {inconsistent_count:,}件")
    print()

    # サマリー
    print("=" * 80)
    if inconsistent_count == 0:
        print("✅ 全エピソードのcomposite_scoreが正しく修正されました！")
    else:
        print(f"⚠️  一部のエピソードで不整合があります: {inconsistent_count}件")
    print("=" * 80)
    print()
    print("📊 サマリー:")
    print(f"  - 修正件数: {fixed_count:,}件")
    print(f"  - スキップ件数: {skipped_count:,}件")
    print(f"  - 一致確認: {consistent_count:,}件")
    print(f"  - 不一致: {inconsistent_count:,}件")
    print(f"  - バックアップ: {BACKUP_PATH}")
    print()


if __name__ == "__main__":
    main()
