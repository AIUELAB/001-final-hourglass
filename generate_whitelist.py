#!/usr/bin/env python3
"""
Wikipedia検証済み人物からホワイトリストを生成
"""

import pandas as pd
import json
from pathlib import Path

def generate_whitelist():
    """検証済みデータからホワイトリストを生成"""
    
    # 検証済みCSVを読み込み
    validated_file = "ultra_think_WIKIPEDIA_VALIDATED_20250828_075912.csv"
    if not Path(validated_file).exists():
        print(f"❌ ファイルが見つかりません: {validated_file}")
        return
    
    print(f"📁 検証済みファイルを読み込み中: {validated_file}")
    df = pd.read_csv(validated_file, encoding='utf-8')
    print(f"✅ {len(df)}人の検証済み人物を読み込みました")
    
    # ホワイトリスト辞書の作成
    whitelist = {}
    
    for idx, row in df.iterrows():
        person_id = str(row['person_id'])
        
        # 複数の名前パターンを登録
        names = []
        
        # person_name_ja を優先
        if pd.notna(row['person_name_ja']) and row['person_name_ja']:
            names.append(str(row['person_name_ja']))
        
        if pd.notna(row['person_name_display']) and row['person_name_display']:
            names.append(str(row['person_name_display']))
            
        if pd.notna(row['person_name']) and row['person_name']:
            names.append(str(row['person_name']))
        
        # ユニークな名前のみ
        unique_names = list(set(filter(None, names)))
        
        if unique_names:
            entry = {
                'id': person_id,
                'names': unique_names,
                'occupation': str(row['occupation']) if pd.notna(row['occupation']) else '',
                'category': str(row['category']) if pd.notna(row['category']) else '',
                'nationality': str(row['nationality']) if pd.notna(row['nationality']) else '',
                'name_recognition': float(row['name_recognition']) if pd.notna(row['name_recognition']) else 0,
                'verified': True  # Wikipedia検証済み
            }
            
            # 各名前をキーとして登録
            for name in unique_names:
                if name and name != 'nan':
                    whitelist[name] = entry
    
    # 統計情報
    print(f"\n📊 ホワイトリスト統計:")
    print(f"  総エントリー数: {len(whitelist)}")
    print(f"  ユニーク人物数: {len(df)}")
    
    # カテゴリ別統計
    categories = df['category'].value_counts()
    print(f"\nカテゴリ分布:")
    for cat, count in categories.head(10).items():
        print(f"  {cat}: {count}")
    
    # ファイル保存
    output_file = "famous_persons_whitelist.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(whitelist, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ ホワイトリストを保存: {output_file}")
    print(f"   サイズ: {Path(output_file).stat().st_size / 1024 / 1024:.2f} MB")
    
    return whitelist


if __name__ == "__main__":
    generate_whitelist()