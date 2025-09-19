#!/usr/bin/env python3
"""
お笑い芸人のグループ表記問題を分析するスクリプト
"""

import csv
import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Set

def load_csv_comedians(file_path: str) -> List[Dict]:
    """CSVからお笑い芸人のレコードを読み込み"""
    comedians = []
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['occupation'] == 'お笑い芸人':
                comedians.append(row)
    return comedians

def load_groups_database(file_path: str) -> Dict:
    """groups_database.jsonを読み込み"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def extract_group_from_display_name(display_name: str) -> str:
    """display_nameから括弧内のグループ名を抽出"""
    match = re.search(r'\(([^)]+)\)', display_name)
    return match.group(1) if match else ""

def analyze_comedian_groups(csv_file: str, json_file: str):
    """お笑い芸人のグループ表記問題を分析"""
    
    # データ読み込み
    comedians = load_csv_comedians(csv_file)
    groups_db = load_groups_database(json_file)
    
    # グループデータベースの準備
    all_groups = {}
    member_to_groups = defaultdict(list)
    
    # comedy_groupsから処理
    if 'comedy_groups' in groups_db:
        for group_name, group_info in groups_db['comedy_groups'].items():
            all_groups[group_name] = group_info
            for member in group_info['members']:
                member_to_groups[member].append(group_name)
                # 名前のバリエーションも追加
                member_to_groups[member.replace(' ', '')].append(group_name)
    
    # YouTuberグループからもお笑い要素があるかチェック
    if 'youtuber_groups' in groups_db:
        for group_name, group_info in groups_db['youtuber_groups'].items():
            if 'エンターテインメント' in group_info.get('category', ''):
                all_groups[group_name] = group_info
                for member in group_info['members']:
                    member_to_groups[member].append(group_name)
                    member_to_groups[member.replace(' ', '')].append(group_name)
    
    # 分析結果
    problems = []
    statistics = {
        'total_comedians': len(comedians),
        'with_group_display': 0,
        'missing_group_display': 0,
        'name_mismatch': 0,
        'correct_display': 0
    }
    
    print(f"お笑い芸人の総数: {statistics['total_comedians']}")
    print(f"グループデータベース内のグループ数: {len(all_groups)}")
    print(f"グループデータベース内のメンバー数: {len(member_to_groups)}")
    print()
    
    for comedian in comedians:
        person_id = comedian['person_id']
        person_name = comedian['person_name']
        person_name_ja = comedian['person_name_ja']
        person_name_display = comedian['person_name_display']
        
        # display_nameから現在のグループを抽出
        current_group = extract_group_from_display_name(person_name_display)
        
        # 名前のバリエーション準備
        name_variations = [
            person_name,
            person_name_ja,
            person_name.replace(' ', ''),
            person_name_ja.replace(' ', ''),
        ]
        
        # groups_database.jsonでこの人物がメンバーとして登録されているか確認
        found_groups = []
        matched_name = ""
        
        for name_var in name_variations:
            if name_var in member_to_groups:
                found_groups.extend(member_to_groups[name_var])
                matched_name = name_var
                break
        
        # 問題ケースの特定
        problem_type = []
        expected_display = person_name_display  # デフォルトは現在の値
        
        if found_groups:
            # グループメンバーとして登録されている場合
            primary_group = found_groups[0]  # 最初に見つかったグループを使用
            expected_display = f"{person_name_ja} ({primary_group})"
            
            if not current_group:
                # a) groups_database.jsonにメンバーとして登録されているが、グループ名が表示されていない
                problem_type.append("グループ名が欠落")
                statistics['missing_group_display'] += 1
            elif current_group != primary_group:
                # グループ名が違う
                problem_type.append("グループ名が不一致")
                statistics['name_mismatch'] += 1
            else:
                # 正しく表示されている
                statistics['correct_display'] += 1
                
            # b) person_nameとgroups_database.jsonの名前が一致しないケース
            if matched_name != person_name:
                problem_type.append("person_name不一致")
                
            # c) person_name_jaとgroups_database.jsonの名前が一致するケース
            if matched_name == person_name_ja:
                problem_type.append("person_name_ja一致")
                
        else:
            # グループメンバーとして登録されていない
            if current_group:
                # グループ名が表示されているが、データベースにない
                problem_type.append("データベース未登録のグループ表示")
                statistics['name_mismatch'] += 1
            else:
                # ソロ活動者として正しい
                statistics['correct_display'] += 1
        
        # グループが表示されているかどうか
        if current_group:
            statistics['with_group_display'] += 1
        
        # 問題があるレコードをリストに追加
        if problem_type:
            problems.append({
                'person_id': person_id,
                'person_name': person_name,
                'person_name_ja': person_name_ja,
                'person_name_display': person_name_display,
                'expected_display': expected_display,
                'found_groups': found_groups,
                'matched_name': matched_name,
                'problem_types': problem_type
            })
    
    # 結果出力
    print("=== 統計情報 ===")
    print(f"お笑い芸人の総数: {statistics['total_comedians']}")
    print(f"正しくグループ名が表示されている数: {statistics['correct_display']}")
    print(f"グループ名が欠落している数: {statistics['missing_group_display']}")
    print(f"名前の不一致による問題の数: {statistics['name_mismatch']}")
    print(f"グループ名付きで表示されている総数: {statistics['with_group_display']}")
    print()
    
    print("=== 問題のあるレコード ===")
    for i, problem in enumerate(problems, 1):
        print(f"{i}. {problem['person_id']}")
        print(f"   person_name: {problem['person_name']}")
        print(f"   person_name_ja: {problem['person_name_ja']}")
        print(f"   現在のdisplay_name: {problem['person_name_display']}")
        print(f"   期待されるdisplay_name: {problem['expected_display']}")
        print(f"   発見されたグループ: {problem['found_groups']}")
        print(f"   マッチした名前: {problem['matched_name']}")
        print(f"   問題の種類: {', '.join(problem['problem_types'])}")
        print()
    
    # 問題の種類別集計
    problem_counts = defaultdict(int)
    for problem in problems:
        for problem_type in problem['problem_types']:
            problem_counts[problem_type] += 1
    
    print("=== 問題種類別集計 ===")
    for problem_type, count in problem_counts.items():
        print(f"{problem_type}: {count}件")
    
    print(f"\n総問題件数: {len(problems)}件")
    
    # JSONで詳細結果を保存
    result = {
        'statistics': statistics,
        'problems': problems,
        'problem_counts': dict(problem_counts),
        'analysis_date': '2025-08-28'
    }
    
    output_file = 'comedian_group_analysis_20250828.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n詳細結果を {output_file} に保存しました。")

if __name__ == "__main__":
    csv_file = "ultra_think_FAST_VALIDATED_20250828_181901.csv"
    json_file = "groups_database.json"
    analyze_comedian_groups(csv_file, json_file)