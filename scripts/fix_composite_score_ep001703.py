#!/usr/bin/env python3
"""
EP-001,703のcomposite_score修正スクリプト

石ノ森章太郎の66歳のエピソード（EP-001,703）のcomposite_scoreが
81.43になっているが、正しくは8.14であるべき。

問題: composite_scoreが10倍になっている
修正: 7軸スコアの平均を再計算して正しい値に修正
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

CSV_PATH = Path(__file__).parent.parent / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = Path(__file__).parent.parent / f"MASTER_EPISODES_CURRENT_backup_before_ep001703_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# 修正対象のエピソードID
TARGET_EPISODE_ID = "EP-001,703"


def calculate_composite_score(row: pd.Series) -> float:
    """7軸スコアからcomposite_scoreを計算（他のエピソードと同じロジック）"""
    seven_axes = []

    for axis in ['記憶性スコア', '共感性スコア', '意外性スコア', '生成品質スコア',
                 '教育的価値', 'ストーリー品質', '事実密度']:
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
    print("📊 EP-001,703のcomposite_score修正")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # Step 2: 修正対象の確認
    print("Step 2: 修正対象の確認中...")
    target_mask = df['episode_id'] == TARGET_EPISODE_ID
    target_df = df[target_mask].copy()

    if len(target_df) == 0:
        print(f"  ❌ エラー: {TARGET_EPISODE_ID} が見つかりません")
        return

    target_row = target_df.iloc[0]
    print(f"  対象エピソード: {target_row['episode_id']}")
    print(f"  人物名: {target_row['person_name']}")
    print(f"  年齢: {target_row['age']}歳")
    print(f"  現在のcomposite_score: {target_row['composite_score']}")
    print()

    # Step 3: 7軸スコアを確認
    print("Step 3: 7軸スコアの確認...")
    seven_axes_cols = ['記憶性スコア', '共感性スコア', '意外性スコア', '生成品質スコア',
                       '教育的価値', 'ストーリー品質', '事実密度']

    seven_axes_values = []
    for axis in seven_axes_cols:
        val = target_row[axis]
        seven_axes_values.append(val)
        print(f"  {axis}: {val}")

    print()

    # 7軸平均を計算
    if all(pd.notna(v) for v in seven_axes_values):
        manual_avg = sum(seven_axes_values) / 7
        print(f"  7軸平均（手動計算）: {manual_avg:.6f}")
    print()

    # Step 4: composite_scoreを再計算
    print("Step 4: composite_scoreを再計算中...")
    correct_composite_score = calculate_composite_score(target_row)

    if correct_composite_score is None:
        print(f"  ❌ エラー: 7軸スコアが不完全のため計算できません")
        return

    print(f"  計算結果: {correct_composite_score:.6f}")
    print(f"  現在の値: {target_row['composite_score']}")
    print(f"  差分: {target_row['composite_score'] - correct_composite_score:.6f} (約{target_row['composite_score'] / correct_composite_score:.1f}倍)")
    print()

    # Step 5: バックアップ作成
    print("Step 5: バックアップ作成中...")
    df.to_csv(BACKUP_PATH, index=False, encoding='utf-8-sig')
    print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
    print()

    # Step 6: 修正を適用
    print("Step 6: 修正を適用中...")
    target_idx = target_df.index[0]
    df.at[target_idx, 'composite_score'] = correct_composite_score
    print(f"  ✅ composite_scoreを {target_row['composite_score']:.2f} → {correct_composite_score:.6f} に修正")
    print()

    # Step 7: CSVファイル保存
    print("Step 7: CSVファイル保存中...")
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    # Step 8: 検証
    print("Step 8: 修正結果の検証...")
    df_verify = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    verify_row = df_verify[df_verify['episode_id'] == TARGET_EPISODE_ID].iloc[0]

    print(f"  検証結果:")
    print(f"    エピソードID: {verify_row['episode_id']}")
    print(f"    composite_score: {verify_row['composite_score']:.6f}")
    print(f"    期待値: {correct_composite_score:.6f}")
    print(f"    一致: {'✅' if abs(verify_row['composite_score'] - correct_composite_score) < 0.0001 else '❌'}")
    print()

    # Step 9: 石ノ森章太郎の全エピソードを検証
    print("Step 9: 石ノ森章太郎の全エピソードを検証...")
    ishinomori_all = df_verify[df_verify['person_name'] == '石ノ森章太郎'][['episode_id', 'age', 'composite_score']].sort_values('age')
    print(ishinomori_all.to_string())
    print()

    # サマリー
    print("=" * 80)
    print("✅ EP-001,703のcomposite_score修正が完了しました！")
    print("=" * 80)
    print()
    print(f"📊 サマリー:")
    print(f"  - 修正前: {target_row['composite_score']:.2f}")
    print(f"  - 修正後: {correct_composite_score:.6f}")
    print(f"  - バックアップ: {BACKUP_PATH}")
    print()


if __name__ == "__main__":
    main()
