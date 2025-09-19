#!/usr/bin/env python3
"""
Wikipedia検証システムの高度なテスト
実際にプレースホルダーを検出できるかテスト
"""

import pandas as pd
from ultra_think_wikipedia_validator import WikipediaValidator
import time

def test_with_fake_entries():
    """明らかに架空の人物でテスト"""
    print("=== Wikipedia検証テスト（架空人物含む） ===\n")
    
    # テストデータ（実在と架空の混合）
    test_data = pd.DataFrame([
        # 実在の人物
        {
            'person_id': 'P001',
            'person_name': '安倍晋三',
            'person_name_display': '安倍晋三',
            'person_name_ja': '安倍晋三',
            'occupation': '政治家'
        },
        {
            'person_id': 'P002',
            'person_name': '大谷翔平',
            'person_name_display': '大谷翔平',
            'person_name_ja': '大谷翔平',
            'occupation': '野球選手'
        },
        {
            'person_id': 'P003',
            'person_name': '新垣結衣',
            'person_name_display': '新垣結衣',
            'person_name_ja': '新垣結衣',
            'occupation': '女優'
        },
        # 明らかに架空の人物（プレースホルダー）
        {
            'person_id': 'P004',
            'person_name': 'テスト太郎123',
            'person_name_display': 'テスト太郎123',
            'person_name_ja': 'テスト太郎123',
            'occupation': '研究者'
        },
        {
            'person_id': 'P005',
            'person_name': 'サンプル花子456',
            'person_name_display': 'サンプル花子456',
            'person_name_ja': 'サンプル花子456',
            'occupation': 'エンジニア'
        },
        {
            'person_id': 'P006',
            'person_name': 'プレースホルダー次郎',
            'person_name_display': 'プレースホルダー次郎',
            'person_name_ja': 'プレースホルダー次郎',
            'occupation': '医師'
        },
        {
            'person_id': 'P007',
            'person_name': 'ダミーユーザー789',
            'person_name_display': 'ダミーユーザー789',
            'person_name_ja': 'ダミーユーザー789',
            'occupation': '教師'
        }
    ])
    
    print(f"テストデータ:")
    print(f"  実在人物: 3人")
    print(f"  架空人物: 4人")
    print(f"  合計: {len(test_data)}人\n")
    
    # Wikipedia検証実行
    start_time = time.time()
    validator = WikipediaValidator(use_parallel=False, max_workers=1)
    
    # ドライランで実行
    df_clean, removed_persons = validator.verify_all_persons(test_data, dry_run=True)
    
    # 結果表示
    elapsed = time.time() - start_time
    print(f"\n=== 検証結果 ===")
    print(f"処理時間: {elapsed:.1f}秒")
    print(f"Wikipedia掲載: {validator.stats['found_on_wikipedia']}人")
    print(f"非掲載（削除対象）: {validator.stats['not_found']}人")
    
    if removed_persons:
        print(f"\n✅ 削除対象として正しく検出:")
        for person in removed_persons:
            print(f"  - {person['person_name']} ({person['occupation']})")
    else:
        print("\n⚠️ 削除対象が検出されませんでした")
    
    # 期待値との比較
    expected_removed = 4  # 架空人物4人
    actual_removed = len(removed_persons)
    
    if actual_removed == expected_removed:
        print(f"\n✅ テスト成功: 期待通り{expected_removed}人が削除対象として検出されました")
    else:
        print(f"\n❌ テスト失敗: {expected_removed}人削除されるべきが、{actual_removed}人しか検出されませんでした")
    
    return validator


def test_specific_patterns():
    """特定のパターンをテスト"""
    print("\n=== 特定パターンのテスト ===\n")
    
    # 実際のデータから特定のパターンを探す
    try:
        df = pd.read_csv('ultra_think_COMPLETE_FIXED_20250828_003356.csv')
        
        # 様々なパターンを検索
        patterns = [
            ('数字を含む', r'\d+'),
            ('アンダースコアを含む', r'_'),
            ('testを含む', r'test', ),
            ('研究者（occupation）', None)
        ]
        
        for pattern_name, regex in patterns[:-1]:
            if regex:
                matches = df[df['person_name'].str.contains(regex, case=False, na=False)]
                print(f"{pattern_name}: {len(matches)}件")
                if len(matches) > 0:
                    print(f"  例: {matches['person_name'].head(3).tolist()}")
        
        # 職業が研究者の人物
        researchers = df[df['occupation'] == '研究者']
        print(f"\n職業が研究者: {len(researchers)}件")
        if len(researchers) > 0:
            # ランダムに3人選んで検証
            sample = researchers.sample(min(3, len(researchers)))
            print(f"  サンプル検証:")
            
            validator = WikipediaValidator(use_parallel=False, max_workers=1)
            for _, person in sample.iterrows():
                result = validator.verify_person(person.to_dict())
                status = "✅ 掲載" if result['found_on_wikipedia'] else "❌ 非掲載"
                print(f"    {person['person_name']}: {status}")
        
    except Exception as e:
        print(f"エラー: {e}")


def analyze_current_database():
    """現在のデータベースの分析"""
    print("\n=== データベース分析 ===\n")
    
    try:
        df = pd.read_csv('ultra_think_COMPLETE_FIXED_20250828_003356.csv')
        
        print(f"総人数: {len(df):,}人")
        
        # 職業分布
        print(f"\n職業TOP10:")
        occupation_counts = df['occupation'].value_counts().head(10)
        for occ, count in occupation_counts.items():
            print(f"  {occ}: {count}人")
        
        # 国籍分布
        if 'nationality' in df.columns:
            print(f"\n国籍TOP10:")
            nationality_counts = df['nationality'].value_counts().head(10)
            for nat, count in nationality_counts.items():
                print(f"  {nat}: {count}人")
        
        # 名前パターン分析
        print(f"\n名前パターン:")
        print(f"  日本語名あり: {df['person_name_ja'].notna().sum()}人")
        print(f"  表示名あり: {df['person_name_display'].notna().sum()}人")
        print(f"  基本名のみ: {(df['person_name_ja'].isna() & df['person_name_display'].isna()).sum()}人")
        
    except Exception as e:
        print(f"エラー: {e}")


if __name__ == "__main__":
    # 1. 架空人物を含むテスト
    print("=" * 60)
    test_with_fake_entries()
    
    # 2. 特定パターンのテスト
    print("\n" + "=" * 60)
    test_specific_patterns()
    
    # 3. データベース分析
    print("\n" + "=" * 60)
    analyze_current_database()