#!/usr/bin/env python3
"""
石ノ森章太郎のエピソードのスコア修正スクリプト

EP-001,713/714/715/716の fame_score と composite_score を設定
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

CSV_PATH = Path(__file__).parent.parent / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = Path(__file__).parent.parent / f"MASTER_EPISODES_CURRENT_backup_before_ishinomori_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# 修正対象のエピソードID
TARGET_EPISODES = ["EP-001,713", "EP-001,714", "EP-001,715", "EP-001,716"]

# デフォルトのfame_score（石ノ森章太郎は国民的漫画家）
DEFAULT_FAME_SCORE = 70.0


def calculate_composite_score(row: pd.Series) -> float:
    """7軸スコアからcomposite_scoreを計算"""
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
    print("📊 石ノ森章太郎のエピソードスコア修正")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # Step 2: バックアップ作成
    print("Step 2: バックアップ作成中...")
    df.to_csv(BACKUP_PATH, index=False, encoding='utf-8-sig')
    print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
    print()

    # Step 3: 修正対象の確認
    print("Step 3: 修正対象の確認中...")
    target_mask = df['episode_id'].isin(TARGET_EPISODES)
    target_df = df[target_mask].copy()

    print(f"  修正対象: {len(target_df)}件")
    for _, row in target_df.iterrows():
        print(f"    - {row['episode_id']}: {row['person_name']} ({row['age']}歳)")
    print()

    # Step 4: スコア計算と設定
    print("Step 4: スコア計算と設定中...")

    updated_count = 0

    for idx, row in target_df.iterrows():
        episode_id = row['episode_id']

        # composite_scoreを計算
        composite_score = calculate_composite_score(row)

        if composite_score is not None:
            # fame_scoreとcomposite_scoreを設定
            df.at[idx, 'fame_score'] = DEFAULT_FAME_SCORE
            df.at[idx, 'composite_score'] = composite_score

            # タイムスタンプも設定
            df.at[idx, 'fame_score_updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            print(f"  ✅ {episode_id}:")
            print(f"      fame_score: {DEFAULT_FAME_SCORE}")
            print(f"      composite_score: {composite_score:.2f}")

            updated_count += 1
        else:
            print(f"  ⚠️  {episode_id}: 7軸スコアが不完全のためスキップ")

    print()
    print(f"  更新件数: {updated_count}件")
    print()

    # Step 5: CSVファイル保存
    print("Step 5: CSVファイル保存中...")
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    # Step 6: 検証
    print("Step 6: 修正結果の検証...")
    df_verify = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    verify_df = df_verify[df_verify['episode_id'].isin(TARGET_EPISODES)]

    print(f"  検証対象: {len(verify_df)}件")
    all_ok = True

    for _, row in verify_df.iterrows():
        episode_id = row['episode_id']
        fame_score = row['fame_score']
        composite_score = row['composite_score']

        has_fame = pd.notna(fame_score)
        has_composite = pd.notna(composite_score)

        status = "✅" if (has_fame and has_composite) else "❌"
        print(f"  {status} {episode_id}: fame={fame_score:.1f if has_fame else 'N/A'}, composite={composite_score:.2f if has_composite else 'N/A'}")

        if not (has_fame and has_composite):
            all_ok = False

    print()

    # サマリー
    print("=" * 80)
    if all_ok:
        print("✅ 石ノ森章太郎のエピソードスコア修正が完了しました！")
    else:
        print("⚠️  一部のエピソードで修正が完了しませんでした")
    print("=" * 80)
    print()
    print(f"📊 サマリー:")
    print(f"  - 修正件数: {updated_count}件")
    print(f"  - バックアップ: {BACKUP_PATH}")
    print()


if __name__ == "__main__":
    main()
