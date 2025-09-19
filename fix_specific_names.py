#!/usr/bin/env python3
"""
特定の人物のperson_name_displayを修正
"""

import csv
import json
import shutil
from datetime import datetime


def main():
    """メイン処理"""
    print("=" * 60)
    print("特定人物の表示名修正")
    print("=" * 60)
    
    input_file = 'final_12410_firebase_20250822_201828.json'
    
    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_specific_names_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")
    
    # JSON読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 修正対象と新しい表示名
    name_fixes = {
        '黒澤明': '黒澤明',  # 黒澤 → 黒澤明
        '小津安二郎': '小津安二郎',  # 小津 → 小津安二郎
        '西行': '西行法師',  # 西行 → 西行法師
        '円仁': '慈覚大師円仁'  # 円仁 → 慈覚大師円仁
    }
    
    fix_count = 0
    fix_log = []
    
    for key, person in data.items():
        person_name_ja = person.get('person_name_ja', '')
        current_display = person.get('person_name_display', '')
        
        # 修正対象かチェック
        for target_name, new_display in name_fixes.items():
            if target_name in person_name_ja or person_name_ja == target_name:
                if current_display != new_display:
                    fix_log.append({
                        'id': key,
                        'person_name_ja': person_name_ja,
                        'old_display': current_display,
                        'new_display': new_display,
                        'category': person.get('subcategory', ''),
                        'birth': person.get('birth_date', ''),
                        'death': person.get('death_date', '')
                    })
                    person['person_name_display'] = new_display
                    fix_count += 1
                    print(f"  ✏️ {key}: {current_display} → {new_display} ({person_name_ja})")
    
    # 結果を保存
    output_file = f'specific_names_fixed_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ログ保存
    log_file = f'specific_names_fix_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'fix_count': fix_count,
            'timestamp': timestamp,
            'fixes': fix_log
        }, f, ensure_ascii=False, indent=2)
    
    # 元のファイルを更新
    shutil.copy2(output_file, input_file)
    
    print("\n📊 処理結果:")
    print(f"  修正件数: {fix_count}件")
    
    # CSV出力
    print("\n📊 CSV出力中...")
    csv_filename = f'final_with_grade_{timestamp}.csv'
    
    headers = [
        'id', 'person_name', 'person_name_ja', 'person_name_display', 'grade',
        'birth_date', 'death_date', 'nationality', 'occupation',
        'main_category', 'subcategory', 'description'
    ]
    
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for key, person in data.items():
            row = {
                'id': person.get('id', key),
                'person_name': person.get('person_name', ''),
                'person_name_ja': person.get('person_name_ja', ''),
                'person_name_display': person.get('person_name_display', ''),
                'grade': person.get('grade', ''),
                'birth_date': person.get('birth_date', ''),
                'death_date': person.get('death_date', ''),
                'nationality': person.get('nationality', ''),
                'occupation': person.get('occupation', ''),
                'main_category': person.get('main_category', ''),
                'subcategory': person.get('subcategory', ''),
                'description': person.get('description', '')
            }
            writer.writerow(row)
    
    print(f"✅ CSV出力完了: {csv_filename}")
    print(f"📊 総エントリ数: {len(data)}件")
    
    return fix_count

if __name__ == "__main__":
    main()