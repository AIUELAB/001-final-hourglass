#!/usr/bin/env python3
"""
Ultra Think 指定person_idの検証と修正
Check and Fix Specific Person IDs
"""

import csv
import re
from datetime import datetime

def check_persons():
    """指定されたperson_idの人物を検証"""
    
    # 指定されたperson_idリストを読み込み
    with open('check_person_ids.txt', 'r') as f:
        target_ids = [line.strip() for line in f if line.strip()]
    
    print(f"📋 検証対象: {len(target_ids)}名")
    
    # クリーンデータベースを読み込み
    input_file = "ultra_think_FINAL_CLEAN_20250827_135023.csv"
    
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
        headers = reader.fieldnames
    
    # person_idでインデックス作成
    person_index = {row['person_id']: row for row in all_rows}
    
    # 問題のある人物を分析
    issues = {
        'not_found': [],
        'suspicious_names': [],
        'display_issues': [],
        'low_recognition': [],
        'ok': []
    }
    
    # サンプル表示用
    sample_data = []
    
    for pid in target_ids:
        if pid not in person_index:
            issues['not_found'].append(pid)
            continue
        
        person = person_index[pid]
        person_name = person.get('person_name', '')
        person_name_ja = person.get('person_name_ja', '')
        person_name_display = person.get('person_name_display', '')
        category = person.get('category', '')
        nationality = person.get('nationality', '')
        occupation = person.get('occupation', '')
        recognition = int(person.get('name_recognition', 0))
        
        # 問題チェック
        has_issue = False
        
        # 1. 疑わしい名前パターン
        suspicious_patterns = [
            r'^(Person|User|Member|Player|Artist|Creator) \d+$',
            r'^[A-Z]{2,4}\d{3,}$',  # XX123形式
            r'^\d+$',  # 数字のみ
            r'^Test',
            r'^Sample',
            r'^Unknown',
            r'^TBD',
            r'^N/A'
        ]
        
        for pattern in suspicious_patterns:
            if (re.match(pattern, person_name) or 
                re.match(pattern, person_name_ja) or
                re.match(pattern, person_name_display)):
                issues['suspicious_names'].append({
                    'id': pid,
                    'name': person_name,
                    'name_ja': person_name_ja,
                    'display': person_name_display
                })
                has_issue = True
                break
        
        # 2. person_name_display問題
        if not has_issue:
            # 空または不適切な表示名
            if not person_name_display or person_name_display == person_name:
                # 日本人の場合は日本語名が必要
                if nationality == '日本' and person_name_display != person_name_ja:
                    issues['display_issues'].append({
                        'id': pid,
                        'name': person_name,
                        'name_ja': person_name_ja,
                        'display': person_name_display,
                        'issue': 'Japanese person needs Japanese display name'
                    })
                    has_issue = True
        
        # 3. 低知名度チェック（30未満は疑わしい）
        if not has_issue and recognition < 30:
            issues['low_recognition'].append({
                'id': pid,
                'name': person_name_ja or person_name,
                'recognition': recognition,
                'category': category
            })
            has_issue = True
        
        if not has_issue:
            issues['ok'].append(pid)
        
        # サンプルデータ収集（最初の20件）
        if len(sample_data) < 20:
            sample_data.append({
                'id': pid,
                'name': person_name,
                'name_ja': person_name_ja,
                'display': person_name_display,
                'category': category,
                'nationality': nationality,
                'occupation': occupation,
                'recognition': recognition
            })
    
    # レポート出力
    print("\n" + "=" * 80)
    print("📊 検証結果サマリー")
    print("=" * 80)
    
    print(f"\n✅ 問題なし: {len(issues['ok'])}名")
    print(f"❌ 見つからない: {len(issues['not_found'])}名")
    print(f"⚠️  疑わしい名前: {len(issues['suspicious_names'])}名")
    print(f"⚠️  表示名問題: {len(issues['display_issues'])}名")
    print(f"⚠️  低知名度: {len(issues['low_recognition'])}名")
    
    # サンプル表示
    print("\n" + "=" * 80)
    print("📋 サンプルデータ（最初の20件）")
    print("=" * 80)
    
    for i, p in enumerate(sample_data, 1):
        print(f"\n[{i}] {p['id']}")
        print(f"  名前: {p['name']}")
        print(f"  日本語: {p['name_ja']}")
        print(f"  表示: {p['display']}")
        print(f"  カテゴリ: {p['category']}")
        print(f"  国籍: {p['nationality']}")
        print(f"  職業: {p['occupation']}")
        print(f"  知名度: {p['recognition']}")
    
    # 問題のある人物の詳細
    if issues['suspicious_names']:
        print("\n" + "=" * 80)
        print("⚠️  疑わしい名前の人物")
        print("=" * 80)
        for p in issues['suspicious_names'][:10]:
            print(f"  {p['id']}: {p['name']} / {p['name_ja']} / {p['display']}")
    
    if issues['display_issues']:
        print("\n" + "=" * 80)
        print("⚠️  表示名に問題がある人物")
        print("=" * 80)
        for p in issues['display_issues'][:10]:
            print(f"  {p['id']}: {p['name_ja']} → 表示: '{p['display']}' ({p['issue']})")
    
    if issues['low_recognition']:
        print("\n" + "=" * 80)
        print("⚠️  極端に低い知名度の人物")
        print("=" * 80)
        for p in issues['low_recognition'][:10]:
            print(f"  {p['id']}: {p['name']} (知名度: {p['recognition']}, カテゴリ: {p['category']})")
    
    return issues

def fix_issues(issues):
    """問題のある人物を修正または削除"""
    
    # データベースを読み込み
    input_file = "ultra_think_FINAL_CLEAN_20250827_135023.csv"
    
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
        headers = reader.fieldnames
    
    # 削除するIDのセット
    to_remove = set()
    
    # 疑わしい名前は削除
    for p in issues['suspicious_names']:
        to_remove.add(p['id'])
    
    # 見つからないIDも記録
    for pid in issues['not_found']:
        to_remove.add(pid)
    
    # 極端に低い知名度（25未満）も削除
    for p in issues['low_recognition']:
        if p['recognition'] < 25:
            to_remove.add(p['id'])
    
    # フィルタリング
    clean_rows = []
    removed_count = 0
    fixed_count = 0
    
    for row in all_rows:
        person_id = row['person_id']
        
        if person_id in to_remove:
            removed_count += 1
            continue
        
        # 表示名の修正
        if any(p['id'] == person_id for p in issues['display_issues']):
            if row['nationality'] == '日本' and row['person_name_ja']:
                row['person_name_display'] = row['person_name_ja']
                fixed_count += 1
        
        clean_rows.append(row)
    
    # 結果を保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ultra_think_VERIFIED_{timestamp}.csv"
    
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(clean_rows)
    
    print(f"\n" + "=" * 80)
    print("✅ 修正完了")
    print("=" * 80)
    print(f"  削除: {removed_count}名")
    print(f"  表示名修正: {fixed_count}名")
    print(f"  最終人数: {len(clean_rows)}名")
    print(f"  出力ファイル: {output_file}")
    
    return output_file

if __name__ == "__main__":
    print("🎌 Ultra Think person_id検証システム")
    print("=" * 80)
    
    # 検証実行
    issues = check_persons()
    
    # 修正が必要な場合
    total_issues = (len(issues['suspicious_names']) + 
                   len(issues['display_issues']) + 
                   len(issues['low_recognition']) +
                   len(issues['not_found']))
    
    if total_issues > 0:
        print(f"\n⚠️  {total_issues}件の問題が見つかりました")
        response = input("\n修正を実行しますか？ (y/n): ")
        
        if response.lower() == 'y':
            output_file = fix_issues(issues)
            print("\n✅ 検証と修正が完了しました")