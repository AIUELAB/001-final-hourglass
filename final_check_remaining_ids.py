#!/usr/bin/env python3
"""
Ultra Think 最終チェック - 残存する指定IDの確認
Final Check of Remaining Target IDs
"""

import csv
from collections import defaultdict

def final_check():
    """最終的に残存する指定IDをチェック"""
    
    # 指定されたperson_idリストを読み込み
    with open('check_person_ids.txt', 'r') as f:
        target_ids = set(line.strip() for line in f if line.strip())
    
    # 最新のクリーンデータベースを読み込み
    input_file = "ultra_think_REAL_PERSONS_ONLY_20250827_142039.csv"
    
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
    
    # 残存する指定IDの人物を抽出
    remaining_targets = []
    for row in all_rows:
        if row['person_id'] in target_ids:
            remaining_targets.append(row)
    
    print(f"📋 最終残存する指定ID: {len(remaining_targets)}件")
    print(f"   データベース総数: {len(all_rows)}名")
    print("\n" + "=" * 80)
    
    # カテゴリ別集計
    categories = defaultdict(list)
    for person in remaining_targets:
        categories[person.get('category', 'Unknown')].append(person)
    
    print("\n【カテゴリ別内訳】")
    for cat, persons in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {cat}: {len(persons)}件")
    
    # 知名度分布
    recognition_dist = defaultdict(int)
    for person in remaining_targets:
        rec = int(person.get('name_recognition', 0))
        bucket = (rec // 10) * 10
        recognition_dist[bucket] += 1
    
    print("\n【知名度分布】")
    for bucket in sorted(recognition_dist.keys()):
        print(f"  {bucket:3d}-{bucket+9:3d}: {'■' * (recognition_dist[bucket] // 10)} {recognition_dist[bucket]}件")
    
    # サンプル表示（各カテゴリから）
    print("\n" + "=" * 80)
    print("【残存人物サンプル（各カテゴリ上位）】")
    print("=" * 80)
    
    for cat, persons in sorted(categories.items()):
        print(f"\n◆ {cat} （{len(persons)}件）")
        # 知名度順にソート
        sorted_persons = sorted(persons, key=lambda x: int(x.get('name_recognition', 0)), reverse=True)
        for i, p in enumerate(sorted_persons[:5], 1):
            print(f"  {i}. {p['person_id']}: {p['person_name']}")
            print(f"     日本語: {p.get('person_name_ja', '')}")
            print(f"     表示: {p.get('person_name_display', '')}")
            print(f"     職業: {p.get('occupation', '')} | 知名度: {p.get('name_recognition', '')}")
    
    # 疑わしいパターンのチェック
    print("\n" + "=" * 80)
    print("【品質チェック】")
    print("=" * 80)
    
    issues = {
        'low_recognition': [],
        'missing_display': [],
        'numeric_names': []
    }
    
    for person in remaining_targets:
        # 低知名度（40未満）
        if int(person.get('name_recognition', 0)) < 40:
            issues['low_recognition'].append(person)
        
        # 表示名が不適切
        if not person.get('person_name_display', '').strip():
            issues['missing_display'].append(person)
        
        # 数字を含む名前
        import re
        if (re.search(r'\d', person.get('person_name', '')) or 
            re.search(r'\d', person.get('person_name_ja', ''))):
            issues['numeric_names'].append(person)
    
    print(f"\n⚠️  低知名度（40未満）: {len(issues['low_recognition'])}件")
    if issues['low_recognition']:
        for p in issues['low_recognition'][:5]:
            print(f"    - {p['person_name']} (知名度: {p.get('name_recognition', '')})")
    
    print(f"\n⚠️  表示名なし: {len(issues['missing_display'])}件")
    
    print(f"\n⚠️  数字を含む名前: {len(issues['numeric_names'])}件")
    if issues['numeric_names']:
        for p in issues['numeric_names'][:5]:
            print(f"    - {p['person_name']} / {p.get('person_name_ja', '')}")
    
    # 最終判定
    print("\n" + "=" * 80)
    print("【最終判定】")
    print("=" * 80)
    
    high_quality_count = len([p for p in remaining_targets 
                             if int(p.get('name_recognition', 0)) >= 40 
                             and p.get('person_name_display', '').strip()
                             and not re.search(r'\d', p.get('person_name', ''))
                             and not re.search(r'\d', p.get('person_name_ja', ''))])
    
    print(f"\n✅ 高品質な実在有名人: {high_quality_count}件")
    print(f"❓ 品質に疑問あり: {len(remaining_targets) - high_quality_count}件")
    
    return remaining_targets

if __name__ == "__main__":
    print("🎌 Ultra Think 最終品質チェック")
    print("=" * 80)
    
    remaining = final_check()
    
    print("\n" + "=" * 80)
    print(f"📊 最終レポート: 指定IDリストから{len(remaining)}件が残存")
    print("=" * 80)