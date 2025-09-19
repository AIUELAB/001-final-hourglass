#!/usr/bin/env python3
"""
日本人なのに外国語表記になっているレコードを特定
"""
import pandas as pd
import json
from datetime import datetime

def identify_foreign_display_issues():
    # 最新のCSVファイルを読み込み
    df = pd.read_csv('ultra_think_COMEDY_GROUPS_FIXED_20250828_190550.csv')
    
    # 日本人のレコードをフィルタ
    japanese_records = df[df['nationality'] == '日本'].copy()
    
    print(f"📊 日本人レコード数: {len(japanese_records)}")
    
    # 問題のあるレコードを特定
    # 条件: person_name_displayが英語（アルファベット）で、person_name_jaが存在する
    problems = []
    
    for idx, row in japanese_records.iterrows():
        person_id = row['person_id']
        person_name = row['person_name']
        person_name_display = str(row['person_name_display'])
        person_name_ja = row['person_name_ja']
        occupation = row['occupation']
        category = row['category']
        
        # person_name_jaが存在し、person_name_displayに日本語が含まれていない
        if pd.notna(person_name_ja) and person_name_ja:
            # person_name_displayが英語表記か判定
            # 日本語文字（ひらがな、カタカナ、漢字）が含まれていない場合
            import re
            has_japanese = bool(re.search(r'[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', person_name_display))
            
            if not has_japanese:
                problems.append({
                    'person_id': person_id,
                    'person_name': person_name,
                    'current_display': person_name_display,
                    'person_name_ja': person_name_ja,
                    'expected_display': person_name_ja,  # 期待される表示
                    'occupation': occupation,
                    'category': category,
                    'issue': '日本人なのに英語表記'
                })
    
    # 指定されたperson_idの詳細を確認
    target_ids = ['P000064', 'P000065', 'P000066', 'P000067', 'P000068', 'P000069', 'P000070', 'P000073', 'P000074']
    
    print("\n🎯 指定されたperson_idの詳細:")
    print("-" * 80)
    
    for pid in target_ids:
        record = df[df['person_id'] == pid]
        if not record.empty:
            row = record.iloc[0]
            print(f"{pid}:")
            print(f"  person_name: {row['person_name']}")
            print(f"  person_name_display: {row['person_name_display']}")
            print(f"  person_name_ja: {row['person_name_ja']}")
            print(f"  occupation: {row['occupation']}")
            print(f"  nationality: {row['nationality']}")
            print()
    
    # 統計を表示
    print(f"\n📊 問題のあるレコード統計:")
    print(f"  総数: {len(problems)}件")
    
    # occupation別の集計
    occupation_counts = {}
    for problem in problems:
        occ = problem['occupation']
        if occ not in occupation_counts:
            occupation_counts[occ] = 0
        occupation_counts[occ] += 1
    
    print("\n📈 職業別の内訳:")
    for occ, count in sorted(occupation_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {occ}: {count}件")
    
    # 結果をJSONで保存
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_japanese_records': len(japanese_records),
        'problem_count': len(problems),
        'problem_rate': f"{len(problems) / len(japanese_records) * 100:.2f}%",
        'occupation_breakdown': occupation_counts,
        'problems': problems
    }
    
    with open('foreign_display_issues.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # CSVでも保存（修正前後の比較用）
    if problems:
        problems_df = pd.DataFrame(problems)
        problems_df.to_csv('foreign_display_issues.csv', index=False, encoding='utf-8')
        print(f"\n📁 問題リスト保存: foreign_display_issues.csv ({len(problems)}件)")
    
    return problems, report

if __name__ == "__main__":
    problems, report = identify_foreign_display_issues()
    
    # 修正が必要なレコードの例を表示
    if problems:
        print("\n🔧 修正が必要な例（最初の10件）:")
        for i, problem in enumerate(problems[:10], 1):
            print(f"{i}. {problem['person_id']}: {problem['current_display']} → {problem['expected_display']}")