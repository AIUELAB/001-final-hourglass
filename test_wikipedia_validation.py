#!/usr/bin/env python3
"""
Wikipedia検証システムのテスト（少量のサンプルデータで）
"""

import pandas as pd
from ultra_think_wikipedia_validator import WikipediaValidator
import time

def test_sample_validation():
    """サンプルデータでWikipedia検証をテスト"""
    print("=== Wikipedia検証テスト ===\n")
    
    # サンプルデータを作成（実在の人物とプレースホルダーの混合）
    sample_data = pd.DataFrame([
        # 実在の人物（Wikipediaに掲載）
        {
            'person_id': 'P001',
            'person_name': 'Ado',
            'person_name_display': 'Ado',
            'person_name_ja': 'Ado',
            'occupation': '歌手'
        },
        {
            'person_id': 'P002',
            'person_name': 'GACKT',
            'person_name_display': 'GACKT',
            'person_name_ja': 'GACKT',
            'occupation': '歌手'
        },
        {
            'person_id': 'P003',
            'person_name': 'Albert Einstein',
            'person_name_display': 'アルバート・アインシュタイン',
            'person_name_ja': 'アルバート・アインシュタイン',
            'occupation': '物理学者'
        },
        # プレースホルダー候補（架空または存在しない）
        {
            'person_id': 'P004',
            'person_name': 'TestPerson_001',
            'person_name_display': 'テストパーソン001',
            'person_name_ja': 'テストパーソン001',
            'occupation': '研究者'
        },
        {
            'person_id': 'P005',
            'person_name': 'PlaceholderUser_123',
            'person_name_display': 'プレースホルダーユーザー123',
            'person_name_ja': 'プレースホルダーユーザー123',
            'occupation': 'エンジニア'
        }
    ])
    
    print(f"テストデータ: {len(sample_data)}人\n")
    
    # Wikipedia検証実行
    start_time = time.time()
    validator = WikipediaValidator(use_parallel=False, max_workers=1)
    
    # ドライランで実行
    df_clean, removed_persons = validator.verify_all_persons(sample_data, dry_run=True)
    
    # 結果表示
    print(f"\n=== 検証結果 ===")
    print(f"処理時間: {time.time() - start_time:.1f}秒")
    print(f"Wikipedia掲載: {validator.stats['found_on_wikipedia']}人")
    print(f"非掲載（削除対象）: {validator.stats['not_found']}人")
    
    if removed_persons:
        print(f"\n削除対象:")
        for person in removed_persons:
            print(f"  - {person['person_name']} ({person['occupation']})")
    
    # レポート生成
    report = validator.generate_report()
    print(f"\n{report}")
    
    return validator


def test_batch_validation():
    """大量データの部分的なテスト"""
    print("\n=== 大量データ部分テスト ===\n")
    
    # 実際のCSVから最初の100件を読み込み
    try:
        full_df = pd.read_csv('ultra_think_COMPLETE_FIXED_20250828_003356.csv')
        sample_df = full_df.head(100)
        print(f"テスト対象: 最初の{len(sample_df)}人")
        
        # Wikipedia検証実行（並列処理でテスト）
        start_time = time.time()
        validator = WikipediaValidator(use_parallel=True, max_workers=3)
        
        # ドライランで実行
        df_clean, removed_persons = validator.verify_all_persons(sample_df, dry_run=True)
        
        # 結果表示
        print(f"\n=== バッチテスト結果 ===")
        print(f"処理時間: {time.time() - start_time:.1f}秒")
        print(f"Wikipedia掲載: {validator.stats['found_on_wikipedia']}人")
        print(f"非掲載（削除対象）: {validator.stats['not_found']}人")
        print(f"削除率: {len(removed_persons)/len(sample_df)*100:.1f}%")
        
        # エラーログ表示
        if validator.error_log:
            print(f"\nエラーログ（最初の5件）:")
            for error in validator.error_log[:5]:
                print(f"  - {error}")
        
        return validator
        
    except Exception as e:
        print(f"エラー: {e}")
        return None


if __name__ == "__main__":
    # 1. サンプルデータでテスト
    test_sample_validation()
    
    # 2. 実際のデータの一部でテスト
    test_batch_validation()