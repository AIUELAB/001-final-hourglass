#!/usr/bin/env python3
"""
YouTuberグループ問題の調査と分析ツール
QuizKnockやその他のYouTuberグループメンバーをCSVから検索し、
グループ名の表示状況を確認します。
"""

import pandas as pd
import re
from typing import Dict, List, Tuple
from pathlib import Path
import json

def load_csv_data(file_path: str) -> pd.DataFrame:
    """CSVファイルを読み込み"""
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        print(f"✅ CSVファイル読み込み成功: {len(df)} 行")
        return df
    except Exception as e:
        print(f"❌ CSVファイル読み込みエラー: {e}")
        return pd.DataFrame()

def search_quizknock_members(df: pd.DataFrame) -> Dict:
    """QuizKnockメンバーの検索"""
    quizknock_members = [
        "伊沢拓司", "河村拓哉", "須貝駿貴", "こうちゃん", 
        "山本祥彰", "鶴崎修功", "福良拳", "志葉玲", "林輝幸"
    ]
    
    results = {}
    search_columns = ['person_name', 'person_name_ja', 'display_name']
    
    for member in quizknock_members:
        found_records = []
        for col in search_columns:
            if col in df.columns:
                # 完全一致と部分一致の両方で検索
                exact_match = df[df[col] == member]
                partial_match = df[df[col].str.contains(member, na=False)]
                
                for _, row in exact_match.iterrows():
                    found_records.append({
                        'match_type': 'exact',
                        'column': col,
                        'value': row[col],
                        'display_name': row.get('display_name', ''),
                        'person_name': row.get('person_name', ''),
                        'person_name_ja': row.get('person_name_ja', ''),
                        'occupation': row.get('occupation', ''),
                        'group_name': row.get('group_name', ''),
                        'index': row.name
                    })
                
                for _, row in partial_match.iterrows():
                    if row.name not in [r['index'] for r in found_records]:
                        found_records.append({
                            'match_type': 'partial',
                            'column': col,
                            'value': row[col],
                            'display_name': row.get('display_name', ''),
                            'person_name': row.get('person_name', ''),
                            'person_name_ja': row.get('person_name_ja', ''),
                            'occupation': row.get('occupation', ''),
                            'group_name': row.get('group_name', ''),
                            'index': row.name
                        })
        
        results[member] = found_records
    
    return results

def search_fishers_members(df: pd.DataFrame) -> Dict:
    """フィッシャーズメンバーの検索"""
    fishers_members = [
        "シルクロード", "マサイ", "ンダホ", "ザカオ", "ダーマ", 
        "モトキ", "ぺけたん"
    ]
    
    results = {}
    search_columns = ['person_name', 'person_name_ja', 'display_name']
    
    for member in fishers_members:
        found_records = []
        for col in search_columns:
            if col in df.columns:
                # 完全一致と部分一致
                exact_match = df[df[col] == member]
                partial_match = df[df[col].str.contains(member, na=False)]
                
                for _, row in exact_match.iterrows():
                    found_records.append({
                        'match_type': 'exact',
                        'column': col,
                        'value': row[col],
                        'display_name': row.get('display_name', ''),
                        'person_name': row.get('person_name', ''),
                        'person_name_ja': row.get('person_name_ja', ''),
                        'occupation': row.get('occupation', ''),
                        'group_name': row.get('group_name', ''),
                        'index': row.name
                    })
                
                for _, row in partial_match.iterrows():
                    if row.name not in [r['index'] for r in found_records]:
                        found_records.append({
                            'match_type': 'partial',
                            'column': col,
                            'value': row[col],
                            'display_name': row.get('display_name', ''),
                            'person_name': row.get('person_name', ''),
                            'person_name_ja': row.get('person_name_ja', ''),
                            'occupation': row.get('occupation', ''),
                            'group_name': row.get('group_name', ''),
                            'index': row.name
                        })
        
        results[member] = found_records
    
    return results

def search_tokai_members(df: pd.DataFrame) -> Dict:
    """東海オンエアメンバーの検索"""
    tokai_members = [
        "てつや", "しばゆー", "としみつ", "りょう", "ゆめまる", "虫眼鏡"
    ]
    
    results = {}
    search_columns = ['person_name', 'person_name_ja', 'display_name']
    
    for member in tokai_members:
        found_records = []
        for col in search_columns:
            if col in df.columns:
                exact_match = df[df[col] == member]
                partial_match = df[df[col].str.contains(member, na=False)]
                
                for _, row in exact_match.iterrows():
                    found_records.append({
                        'match_type': 'exact',
                        'column': col,
                        'value': row[col],
                        'display_name': row.get('display_name', ''),
                        'person_name': row.get('person_name', ''),
                        'person_name_ja': row.get('person_name_ja', ''),
                        'occupation': row.get('occupation', ''),
                        'group_name': row.get('group_name', ''),
                        'index': row.name
                    })
                
                for _, row in partial_match.iterrows():
                    if row.name not in [r['index'] for r in found_records]:
                        found_records.append({
                            'match_type': 'partial',
                            'column': col,
                            'value': row[col],
                            'display_name': row.get('display_name', ''),
                            'person_name': row.get('person_name', ''),
                            'person_name_ja': row.get('person_name_ja', ''),
                            'occupation': row.get('occupation', ''),
                            'group_name': row.get('group_name', ''),
                            'index': row.name
                        })
        
        results[member] = found_records
    
    return results

def search_other_youtuber_groups(df: pd.DataFrame) -> Dict:
    """その他のYouTuberグループメンバーの検索"""
    other_groups = {
        "スカイピース": ["☆イニ☆", "テオくん", "イニ", "テオ"],
        "コムドット": ["ゆうた", "やまと", "ゆうま", "ひゅうが", "あむぎり"],
        "水溜りボンド": ["カンタ", "トミー"]
    }
    
    results = {}
    search_columns = ['person_name', 'person_name_ja', 'display_name']
    
    for group_name, members in other_groups.items():
        group_results = {}
        for member in members:
            found_records = []
            for col in search_columns:
                if col in df.columns:
                    exact_match = df[df[col] == member]
                    partial_match = df[df[col].str.contains(member, na=False)]
                    
                    for _, row in exact_match.iterrows():
                        found_records.append({
                            'match_type': 'exact',
                            'column': col,
                            'value': row[col],
                            'display_name': row.get('display_name', ''),
                            'person_name': row.get('person_name', ''),
                            'person_name_ja': row.get('person_name_ja', ''),
                            'occupation': row.get('occupation', ''),
                            'group_name': row.get('group_name', ''),
                            'index': row.name
                        })
                    
                    for _, row in partial_match.iterrows():
                        if row.name not in [r['index'] for r in found_records]:
                            found_records.append({
                                'match_type': 'partial',
                                'column': col,
                                'value': row[col],
                                'display_name': row.get('display_name', ''),
                                'person_name': row.get('person_name', ''),
                                'person_name_ja': row.get('person_name_ja', ''),
                                'occupation': row.get('occupation', ''),
                                'group_name': row.get('group_name', ''),
                                'index': row.name
                            })
            
            group_results[member] = found_records
        results[group_name] = group_results
    
    return results

def analyze_group_name_display(all_results: Dict) -> Dict:
    """グループ名の表示状況を分析"""
    analysis = {
        'with_brackets': [],
        'without_brackets': [],
        'no_group_name': [],
        'bracket_patterns': []
    }
    
    bracket_pattern = re.compile(r'[（(].*?[）)]')
    
    for group, members in all_results.items():
        if isinstance(members, dict):
            # other_groups形式
            for member, records in members.items():
                for record in records:
                    group_name = record.get('group_name', '')
                    display_name = record.get('display_name', '')
                    
                    if group_name:
                        if bracket_pattern.search(group_name):
                            analysis['with_brackets'].append({
                                'group': group,
                                'member': member,
                                'group_name': group_name,
                                'display_name': display_name
                            })
                        else:
                            analysis['without_brackets'].append({
                                'group': group,
                                'member': member,
                                'group_name': group_name,
                                'display_name': display_name
                            })
                    else:
                        analysis['no_group_name'].append({
                            'group': group,
                            'member': member,
                            'display_name': display_name
                        })
                    
                    # 括弧パターンの抽出
                    brackets_in_display = bracket_pattern.findall(display_name)
                    if brackets_in_display:
                        analysis['bracket_patterns'].extend(brackets_in_display)
        else:
            # QuizKnock, フィッシャーズ形式
            for record in members:
                group_name = record.get('group_name', '')
                display_name = record.get('display_name', '')
                
                if group_name:
                    if bracket_pattern.search(group_name):
                        analysis['with_brackets'].append({
                            'group': group,
                            'member': 'N/A',
                            'group_name': group_name,
                            'display_name': display_name
                        })
                    else:
                        analysis['without_brackets'].append({
                            'group': group,
                            'member': 'N/A',
                            'group_name': group_name,
                            'display_name': display_name
                        })
                else:
                    analysis['no_group_name'].append({
                        'group': group,
                        'member': 'N/A',
                        'display_name': display_name
                    })
                
                brackets_in_display = bracket_pattern.findall(display_name)
                if brackets_in_display:
                    analysis['bracket_patterns'].extend(brackets_in_display)
    
    return analysis

def print_results(results: Dict, title: str):
    """検索結果の表示"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")
    
    found_count = 0
    for member, records in results.items():
        if isinstance(records, dict):
            # other_groups形式の処理
            for sub_member, sub_records in records.items():
                if sub_records:
                    found_count += len(sub_records)
                    print(f"\n✅ {member} - {sub_member}: {len(sub_records)} 件")
                    for record in sub_records:
                        print(f"   📋 {record['match_type']} match in {record['column']}: {record['value']}")
                        print(f"      Display: {record['display_name']}")
                        print(f"      Group: {record['group_name']}")
                        print(f"      Occupation: {record['occupation']}")
        else:
            # 通常の形式
            if records:
                found_count += len(records)
                print(f"\n✅ {member}: {len(records)} 件")
                for record in records:
                    print(f"   📋 {record['match_type']} match in {record['column']}: {record['value']}")
                    print(f"      Display: {record['display_name']}")
                    print(f"      Group: {record['group_name']}")
                    print(f"      Occupation: {record['occupation']}")
    
    if found_count == 0:
        print("❌ 該当するメンバーは見つかりませんでした")
    else:
        print(f"\n📊 合計 {found_count} 件の一致を発見")

def main():
    """メイン実行関数"""
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_HAJIME_FIXED_20250828_194909.csv"
    
    print("🚀 YouTuberグループ問題の調査を開始します")
    print(f"📂 対象ファイル: {csv_file}")
    
    # CSVデータの読み込み
    df = load_csv_data(csv_file)
    if df.empty:
        return
    
    print(f"📊 データ概要:")
    print(f"   - 行数: {len(df)}")
    print(f"   - 列数: {len(df.columns)}")
    print(f"   - 列名: {list(df.columns)}")
    
    # 各グループの検索を並行実行
    print("\n🔍 グループメンバーの検索を開始...")
    
    # 1. QuizKnockメンバーの検索
    quizknock_results = search_quizknock_members(df)
    print_results(quizknock_results, "QuizKnockメンバー検索結果")
    
    # 2. フィッシャーズメンバーの検索
    fishers_results = search_fishers_members(df)
    print_results(fishers_results, "フィッシャーズメンバー検索結果")
    
    # 3. 東海オンエアメンバーの検索
    tokai_results = search_tokai_members(df)
    print_results(tokai_results, "東海オンエアメンバー検索結果")
    
    # 4. その他のYouTuberグループの検索
    other_results = search_other_youtuber_groups(df)
    print_results(other_results, "その他のYouTuberグループ検索結果")
    
    # 5. グループ名表示状況の分析
    all_results = {
        "QuizKnock": quizknock_results,
        "フィッシャーズ": fishers_results,
        "東海オンエア": tokai_results,
        **other_results
    }
    
    group_analysis = analyze_group_name_display(all_results)
    
    print(f"\n{'='*60}")
    print("📈 グループ名表示状況の分析")
    print(f"{'='*60}")
    
    print(f"\n✅ 括弧付きグループ名: {len(group_analysis['with_brackets'])} 件")
    for item in group_analysis['with_brackets'][:10]:  # 最初の10件を表示
        print(f"   - {item['group']} - {item['member']}: {item['group_name']}")
    
    print(f"\n⚠️  括弧なしグループ名: {len(group_analysis['without_brackets'])} 件")
    for item in group_analysis['without_brackets'][:10]:
        print(f"   - {item['group']} - {item['member']}: {item['group_name']}")
    
    print(f"\n❌ グループ名なし: {len(group_analysis['no_group_name'])} 件")
    for item in group_analysis['no_group_name'][:10]:
        print(f"   - {item['group']} - {item['member']}: {item['display_name']}")
    
    # 結果をJSONで保存
    output_file = "youtuber_group_analysis_results.json"
    analysis_results = {
        'quizknock': quizknock_results,
        'fishers': fishers_results,
        'tokai': tokai_results,
        'other_groups': other_results,
        'group_name_analysis': group_analysis
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 分析結果を {output_file} に保存しました")
    print("\n🎉 YouTuberグループ問題の調査が完了しました!")

if __name__ == "__main__":
    main()