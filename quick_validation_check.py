#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
要検証候補の簡単チェック - 6件の重複候補を確認
"""

import pandas as pd
from difflib import SequenceMatcher

def check_validation_candidates():
    """要検証の6件を簡単チェック"""
    df = pd.read_csv("ultra_think_GROUP_FIXED_20250831_185100.csv")
    
    validation_candidates = [
        'P000130', 'P000867', 'P002680', 
        'P003511', 'P015985', 'P015986'
    ]
    
    print("🔍 要検証候補の詳細確認")
    print("="*60)
    
    for person_id in validation_candidates:
        target_record = df[df['person_id'] == person_id]
        
        if not target_record.empty:
            record = target_record.iloc[0]
            target_name = str(record['person_name'])
            
            print(f"\n📋 {person_id}: {target_name}")
            print(f"  表示名: {record['person_name_display']}")
            print(f"  日本語名: {record['person_name_ja']}")
            print(f"  国籍: {record['nationality']}")
            print(f"  職業: {record['occupation']}")
            print(f"  認知度: {record['name_recognition']}")
            print(f"  カテゴリ: {record['category']}")
            
            # 類似レコードを検索
            print("  🔍 類似レコード検索:")
            similar_found = False
            
            for idx, row in df.iterrows():
                if row['person_id'] != person_id:
                    other_name = str(row['person_name'])
                    similarity = SequenceMatcher(None, target_name, other_name).ratio()
                    
                    if similarity > 0.85:  # 85%以上の類似度
                        print(f"    {row['person_id']}: {other_name} (類似度: {similarity:.3f})")
                        similar_found = True
            
            if not similar_found:
                print("    類似レコードなし - 保持推奨")
    
    return validation_candidates

if __name__ == "__main__":
    check_validation_candidates()