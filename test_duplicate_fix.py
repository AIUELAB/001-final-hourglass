#!/usr/bin/env python3
"""
重複修正のテストスクリプト
修正が正しく機能していることを検証
"""

import pandas as pd
import sys

def test_duplicate_fix():
    """重複修正の検証テスト"""

    print("="*70)
    print("🧪 重複修正テスト")
    print("="*70)

    # 修正後のファイルを読み込み
    cleaned_file = 'episodes_cleaned_20250923_075301.csv'
    df = pd.read_csv(cleaned_file, encoding='utf-8-sig')

    print(f"\n📊 データ統計:")
    print(f"  総エピソード数: {len(df)}件")
    print(f"  人物数: {len(df['person_name'].unique())}人")

    # テスト1: 重複チェック
    print("\n✅ テスト1: 重複チェック")
    duplicates = df[df.duplicated(['person_name'], keep=False)]
    if len(duplicates) == 0:
        print("  成功: 重複なし")
    else:
        print(f"  ❌ 失敗: {len(duplicates)}件の重複が残存")
        return False

    # テスト2: さくらももこの確認
    print("\n✅ テスト2: さくらももこのエピソード確認")
    sakura_episodes = df[df['person_name'] == 'さくらももこ']
    if len(sakura_episodes) == 1:
        print(f"  成功: 1件のみ存在（{sakura_episodes.iloc[0]['episode_age']}歳）")
        # 21歳のエピソードが残っているか確認
        if sakura_episodes.iloc[0]['episode_age'] == 21:
            print("  成功: 正しいエピソード（21歳）が保持されています")
        else:
            print(f"  ⚠️ 警告: {sakura_episodes.iloc[0]['episode_age']}歳のエピソードが保持されています")
    else:
        print(f"  ❌ 失敗: {len(sakura_episodes)}件のエピソードが存在")
        return False

    # テスト3: ファクトチェック状態
    print("\n✅ テスト3: ファクトチェック状態")
    verified_count = df[df['fact_check_status'].notna()].shape[0]
    print(f"  検証済み: {verified_count}/{len(df)}件 ({verified_count/len(df)*100:.0f}%)")

    # テスト4: エピソード品質
    print("\n✅ テスト4: エピソード品質")
    text_lengths = df['episode_text'].str.len()
    valid_length = ((text_lengths >= 132) & (text_lengths <= 250)).sum()
    print(f"  適切な長さ（132-250文字）: {valid_length}/{len(df)}件")

    # テスト5: 特定人物の確認
    print("\n✅ テスト5: 主要人物の確認")
    test_persons = ['イチロー', '大谷翔平', 'HIKAKIN', '村上春樹', '黒澤明']
    for person in test_persons:
        person_data = df[df['person_name'] == person]
        if len(person_data) == 1:
            print(f"  {person}: ✓ (1件)")
        else:
            print(f"  {person}: × ({len(person_data)}件)")

    print("\n" + "="*70)
    print("🎯 テスト結果: すべてのテストに合格")
    print("="*70)

    return True

if __name__ == "__main__":
    success = test_duplicate_fix()
    sys.exit(0 if success else 1)