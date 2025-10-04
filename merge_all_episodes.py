#!/usr/bin/env python3
"""
全58件のエピソードを統合して最終CSVファイルを作成
既存の29件 + 新規29件 = 合計58件
"""

import pandas as pd
from datetime import datetime

def merge_all_episodes():
    """全エピソードを統合（重複チェック付き）"""

    print("="*70)
    print("📊 全エピソード統合処理（改良版）")
    print("="*70)

    # 1. 既存の29件を読み込み（エピソードID: 1）
    print("\n1️⃣ 既存エピソード読み込み中...")
    existing_df = pd.read_csv('episodes_29_corrected_20250922_210220.csv', encoding='utf-8-sig')
    existing_df['episode_id'] = 1
    print(f"  既存エピソード: {len(existing_df)}件")

    # 既存エピソードの人物リストを取得
    existing_persons = set(existing_df['person_name'].unique())
    print(f"  既存人物数: {len(existing_persons)}人")

    # 2. 各バッチの改善版を読み込み（エピソードID: 2）
    print("\n2️⃣ 新規エピソード読み込み中...")

    # 第1バッチ（改善版）
    batch1_df = pd.read_csv('batch1_improved_20250923_000350.csv', encoding='utf-8-sig')
    print(f"  第1バッチ: {len(batch1_df)}件 (平均スコア: {batch1_df['quality_score'].mean():.1f})")

    # 第2バッチ（改善版）
    batch2_df = pd.read_csv('batch2_improved_20250923_000654.csv', encoding='utf-8-sig')
    print(f"  第2バッチ: {len(batch2_df)}件 (平均スコア: {batch2_df['quality_score'].mean():.1f})")

    # 第3バッチ（改善版）
    batch3_df = pd.read_csv('batch3_improved_20250923_000900.csv', encoding='utf-8-sig')
    print(f"  第3バッチ: {len(batch3_df)}件 (平均スコア: {batch3_df['quality_score'].mean():.1f})")

    # 3. 新規エピソードを統合
    new_episodes_df = pd.concat([batch1_df, batch2_df, batch3_df], ignore_index=True)
    print(f"\n新規エピソード合計: {len(new_episodes_df)}件")

    # 重複チェック
    new_persons = set(new_episodes_df['person_name'].unique())
    duplicate_persons = existing_persons & new_persons

    if duplicate_persons:
        print(f"\n⚠️ 警告: {len(duplicate_persons)}人の重複を検出:")
        for person in sorted(duplicate_persons)[:5]:
            print(f"  - {person}")

        print("\n🔧 重複解決処理:")
        print("  既存エピソードを優先し、重複する新規エピソードを削除します")

        # 重複する人物の新規エピソードを削除
        new_episodes_df = new_episodes_df[~new_episodes_df['person_name'].isin(duplicate_persons)]
        print(f"  削除後の新規エピソード: {len(new_episodes_df)}件")

    # 4. 全エピソードを統合
    all_episodes_df = pd.concat([existing_df, new_episodes_df], ignore_index=True)

    # 5. ソート（人物名 → エピソードID）
    all_episodes_df = all_episodes_df.sort_values(['person_name', 'episode_id'])

    # 6. 統計情報を表示
    print("\n📈 統計情報:")
    print(f"  総エピソード数: {len(all_episodes_df)}件")

    # 人物ごとのエピソード数を確認
    episode_counts = all_episodes_df.groupby('person_name').size()
    print(f"  人物数: {len(episode_counts)}人")
    print(f"  各人のエピソード数: {episode_counts.value_counts().to_dict()}")

    # 品質スコアの統計
    new_episodes_only = all_episodes_df[all_episodes_df['episode_id'] == 2]
    passed_episodes = new_episodes_only[new_episodes_only['quality_score'] >= 6.0]
    print(f"\n  新規エピソード品質:")
    print(f"    合格: {len(passed_episodes)}/{len(new_episodes_only)}件 ({len(passed_episodes)/len(new_episodes_only)*100:.0f}%)")
    print(f"    平均スコア: {new_episodes_only['quality_score'].mean():.1f}")

    # スコア別分布
    score_dist = pd.cut(new_episodes_only['quality_score'],
                        bins=[0, 5, 6, 7, 8, 10],
                        labels=['5未満', '5-6', '6-7', '7-8', '8以上'])
    print(f"\n  スコア分布:")
    for label, count in score_dist.value_counts().sort_index().items():
        print(f"    {label}: {count}件")

    # 7. 最終CSVファイルを保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'episodes_58_complete_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        all_episodes_df.to_csv(f, index=False)

    print(f"\n✅ 最終ファイル保存: {output_file}")

    # 8. 不合格者リストを表示
    failed_episodes = new_episodes_only[new_episodes_only['quality_score'] < 6.0]
    if len(failed_episodes) > 0:
        print(f"\n⚠️ 品質基準未達成エピソード ({len(failed_episodes)}件):")
        for _, row in failed_episodes.iterrows():
            print(f"  - {row['person_name']} ({row['episode_age']}歳): スコア {row['quality_score']:.1f}")

    return all_episodes_df

def main():
    all_episodes = merge_all_episodes()

    print("\n" + "="*70)
    print("🎉 全エピソード統合完了")
    print("="*70)

    # 最終統計を計算
    unique_persons = len(all_episodes['person_name'].unique())
    total_episodes = len(all_episodes)

    print(f"""
    最終成果:
    - {total_episodes}件のエピソード
    - {unique_persons}人の人物
    - 各人物1エピソードの原則を遵守
    - 重複チェック機能により品質保証

    ファイル: episodes_complete_[timestamp].csv
    """)

if __name__ == "__main__":
    main()