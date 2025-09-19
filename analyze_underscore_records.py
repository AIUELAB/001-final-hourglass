#!/usr/bin/env python3
"""
アンダースコア（_）を含むレコードの詳細分析
"""
import pandas as pd
import json
from collections import Counter, defaultdict
import re

def analyze_underscore_records():
    """アンダースコアを含むレコードを詳細分析"""
    
    # CSVファイルを読み込み
    file_path = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_YOUTUBER_GROUPS_FIXED_20250828_201154.csv"
    
    try:
        df = pd.read_csv(file_path)
        print(f"総レコード数: {len(df)}")
        print(f"カラム数: {len(df.columns)}")
        print(f"カラム名: {df.columns.tolist()}")
        
        # アンダースコアを含むレコードを抽出
        underscore_records = []
        
        # person_name, person_name_display, person_name_jaでアンダースコアを検索
        for col in ['person_name', 'person_name_display', 'person_name_ja']:
            if col in df.columns:
                mask = df[col].str.contains('_', na=False)
                found_records = df[mask]
                print(f"\n{col}でアンダースコアを含むレコード: {len(found_records)}件")
                
                if len(found_records) > 0:
                    underscore_records.extend(found_records.to_dict('records'))
        
        # 重複を削除
        unique_records = []
        seen_ids = set()
        for record in underscore_records:
            if record['person_id'] not in seen_ids:
                unique_records.append(record)
                seen_ids.add(record['person_id'])
        
        print(f"\nユニークなアンダースコア含有レコード: {len(unique_records)}件")
        
        # パターン分析
        patterns = {
            'group_pattern': [],  # (グループ名) パターン
            'underscore_in_name': [],  # 名前自体にアンダースコア
            'ja_underscore': [],  # 日本語名にアンダースコア
        }
        
        occupation_counter = Counter()
        category_counter = Counter()
        
        print("\n=== 詳細分析（最初の20件） ===")
        for i, record in enumerate(unique_records[:20]):
            person_name = record.get('person_name', '')
            person_name_display = record.get('person_name_display', '')
            person_name_ja = record.get('person_name_ja', '')
            occupation = record.get('occupation', '')
            category = record.get('category', '')
            
            print(f"\n{i+1}. ID: {record['person_id']}")
            print(f"   person_name: {person_name}")
            print(f"   person_name_display: {person_name_display}")
            print(f"   person_name_ja: {person_name_ja}")
            print(f"   occupation: {occupation}")
            print(f"   category: {category}")
            
            # パターン分類
            if '(' in person_name_display and ')' in person_name_display:
                patterns['group_pattern'].append(record)
            elif '_' in person_name:
                patterns['underscore_in_name'].append(record)
            elif '_' in person_name_ja:
                patterns['ja_underscore'].append(record)
            
            occupation_counter[occupation] += 1
            category_counter[category] += 1
        
        print(f"\n=== パターン分類 ===")
        print(f"(グループ名)パターン: {len(patterns['group_pattern'])}件")
        print(f"名前自体にアンダースコア: {len(patterns['underscore_in_name'])}件")
        print(f"日本語名にアンダースコア: {len(patterns['ja_underscore'])}件")
        
        print(f"\n=== 職業別分布 ===")
        for occupation, count in occupation_counter.most_common(10):
            print(f"{occupation}: {count}件")
        
        print(f"\n=== カテゴリー別分布 ===")
        for category, count in category_counter.most_common(10):
            print(f"{category}: {count}件")
        
        # グループ名パターンの詳細分析
        print(f"\n=== (グループ名)パターンの詳細 ===")
        group_names = []
        for record in patterns['group_pattern']:
            display_name = record.get('person_name_display', '')
            if '(' in display_name and ')' in display_name:
                group_part = display_name[display_name.find('(')+1:display_name.find(')')]
                group_names.append(group_part)
        
        group_counter = Counter(group_names)
        print("グループ名の出現回数:")
        for group, count in group_counter.most_common():
            print(f"  {group}: {count}件")
        
        # 修正が必要なパターンを特定
        print(f"\n=== 修正が必要なパターン ===")
        problematic_records = []
        
        for record in unique_records:
            person_name = record.get('person_name', '')
            person_name_display = record.get('person_name_display', '')
            person_name_ja = record.get('person_name_ja', '')
            
            # 問題のパターンを特定
            issues = []
            
            # パターン1: person_nameにアンダースコアが含まれている
            if '_' in person_name:
                issues.append('person_name_underscore')
            
            # パターン2: person_name_displayが正しくない形式
            if person_name_display != person_name and '(' not in person_name_display:
                issues.append('display_name_mismatch')
            
            # パターン3: person_name_jaに不正なアンダースコア
            if '_' in person_name_ja:
                issues.append('ja_name_underscore')
            
            if issues:
                problematic_records.append({
                    'record': record,
                    'issues': issues
                })
        
        print(f"問題のあるレコード: {len(problematic_records)}件")
        for i, prob_record in enumerate(problematic_records[:10]):
            record = prob_record['record']
            issues = prob_record['issues']
            print(f"\n{i+1}. ID: {record['person_id']} - 問題: {', '.join(issues)}")
            print(f"   person_name: {record.get('person_name', '')}")
            print(f"   person_name_display: {record.get('person_name_display', '')}")
            print(f"   person_name_ja: {record.get('person_name_ja', '')}")
        
        # 結果をJSONで保存
        analysis_result = {
            'total_records': len(df),
            'underscore_records_count': len(unique_records),
            'patterns': {
                'group_pattern_count': len(patterns['group_pattern']),
                'underscore_in_name_count': len(patterns['underscore_in_name']),
                'ja_underscore_count': len(patterns['ja_underscore'])
            },
            'occupation_distribution': dict(occupation_counter),
            'category_distribution': dict(category_counter),
            'group_names': dict(group_counter),
            'problematic_records_count': len(problematic_records)
        }
        
        with open('/Users/admin/Documents/AIUELAB/001-final-hourglass/underscore_analysis_result.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析結果を underscore_analysis_result.json に保存しました。")
        
        return analysis_result
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None

if __name__ == "__main__":
    analyze_underscore_records()