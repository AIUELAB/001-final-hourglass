#!/usr/bin/env python3
"""
Ultra Think 残存プレースホルダー完全削除スクリプト
Remove Remaining Placeholders from Calibrated Database
"""

import csv
import re
from datetime import datetime

def remove_placeholders():
    """残存プレースホルダーを削除"""
    
    # 入力ファイル
    input_file = "ultra_think_calibrated_20250827_132748.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ultra_think_FINAL_CLEAN_{timestamp}.csv"
    removed_file = f"removed_placeholders_{timestamp}.csv"
    
    print("🎌 Ultra Think 残存プレースホルダー削除処理")
    print("=" * 60)
    print(f"入力: {input_file}")
    
    # データ読み込み
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
        headers = reader.fieldnames
    
    print(f"総レコード数: {len(all_rows)}名")
    
    # プレースホルダーパターン
    placeholder_patterns = [
        r'^(Actor|Influencer|Comedian|Person|Celebrity|Artist|Creator|User|Member|Player|Singer|Writer|Athlete) \d+$',
        r'^YouTuber \d+$',
        r'Contemporary.*Artist',
        r'Contemporary・アーティスト'
    ]
    
    # フィルタリング
    clean_rows = []
    removed_rows = []
    
    for row in all_rows:
        person_name = row.get('person_name', '')
        person_name_ja = row.get('person_name_ja', '')
        person_name_display = row.get('person_name_display', '')
        
        # いずれかの名前フィールドがプレースホルダーパターンに一致するかチェック
        is_placeholder = False
        for pattern in placeholder_patterns:
            if (re.match(pattern, person_name) or 
                re.match(pattern, person_name_ja) or
                re.match(pattern, person_name_display)):
                is_placeholder = True
                break
        
        if is_placeholder:
            removed_rows.append(row)
        else:
            clean_rows.append(row)
    
    # 結果表示
    print(f"\n【削除されるプレースホルダー】")
    print(f"  総数: {len(removed_rows)}件")
    
    # タイプ別集計
    placeholder_types = {}
    for row in removed_rows:
        person_name = row.get('person_name', '')
        if ' ' in person_name:
            type_name = person_name.split(' ')[0]
            placeholder_types[type_name] = placeholder_types.get(type_name, 0) + 1
    
    print("\n【タイプ別内訳】")
    for type_name, count in sorted(placeholder_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {type_name}: {count}件")
    
    # サンプル表示
    print("\n【削除例（最初の10件）】")
    for row in removed_rows[:10]:
        print(f"  - {row.get('person_name')} / {row.get('person_name_ja')} (ID: {row.get('person_id')})")
    
    # クリーンデータ保存
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(clean_rows)
    
    # 削除データ保存
    with open(removed_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(removed_rows)
    
    print(f"\n✅ 処理完了")
    print(f"  クリーンデータ: {output_file}")
    print(f"  最終レコード数: {len(clean_rows)}名")
    print(f"  削除レコード: {removed_file} ({len(removed_rows)}件)")
    
    # 統計
    print(f"\n【最終統計】")
    print(f"  元のレコード数: {len(all_rows)}名")
    print(f"  削除数: {len(removed_rows)}名")
    print(f"  最終数: {len(clean_rows)}名")
    print(f"  削減率: {len(removed_rows) / len(all_rows) * 100:.1f}%")
    
    return output_file, len(clean_rows), len(removed_rows)

if __name__ == "__main__":
    output_file, clean_count, removed_count = remove_placeholders()
    
    print("\n" + "=" * 60)
    print("🎉 Ultra Think データベースのクリーニング完了！")
    print(f"   プレースホルダーフリーの人数: {clean_count}名")