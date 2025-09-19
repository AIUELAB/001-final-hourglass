#!/usr/bin/env python3
"""
Ultra Think プレースホルダー削除 - Player/選手パターン
Remove Player Pattern Placeholders
"""

import csv
import re
from datetime import datetime

def remove_player_placeholders():
    """Player XXX形式のプレースホルダーを削除"""
    
    # 指定されたperson_idリストを読み込み
    with open('check_person_ids.txt', 'r') as f:
        target_ids = set(line.strip() for line in f if line.strip())
    
    print(f"📋 検証対象ID数: {len(target_ids)}")
    
    # クリーンデータベースを読み込み
    input_file = "ultra_think_FINAL_CLEAN_20250827_135023.csv"
    
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
        headers = reader.fieldnames
    
    print(f"総レコード数: {len(all_rows)}名")
    
    # プレースホルダーパターン（より包括的に）
    placeholder_patterns = [
        # Player系パターン
        r'.*(Player|選手)\s*\d+',  # "Olympic Player 636", "Olympic選手636"など
        r'^(Olympic|World|Champion|National|Star|Rising|Elite|Pro|Junior|Senior|Master|Super|Top|Best|Great|Famous|Legend|Hero|Ace)\s+(Player|選手)\s*\d+',
        
        # Comedian/Actor/Influencer系（既存）
        r'^(Actor|Influencer|Comedian)\s+\d+$',
        
        # 一般的なプレースホルダー
        r'^(Person|User|Member|Artist|Creator|Celebrity)\s+\d+$',
        r'^YouTuber\s+\d+$',
        r'^Test\s*\d*',
        r'^Sample\s*\d*',
        r'^Unknown\s*\d*',
        r'^Placeholder',
        r'^TBD',
        r'^N/A'
    ]
    
    # フィルタリング
    clean_rows = []
    removed_rows = []
    removed_from_target = []
    
    for row in all_rows:
        person_id = row.get('person_id', '')
        person_name = row.get('person_name', '')
        person_name_ja = row.get('person_name_ja', '')
        person_name_display = row.get('person_name_display', '')
        
        # プレースホルダーチェック
        is_placeholder = False
        matched_pattern = None
        
        for pattern in placeholder_patterns:
            if (re.match(pattern, person_name, re.IGNORECASE) or 
                re.match(pattern, person_name_ja, re.IGNORECASE) or
                re.match(pattern, person_name_display, re.IGNORECASE)):
                is_placeholder = True
                matched_pattern = pattern
                break
        
        if is_placeholder:
            removed_rows.append(row)
            if person_id in target_ids:
                removed_from_target.append({
                    'id': person_id,
                    'name': person_name,
                    'name_ja': person_name_ja,
                    'display': person_name_display,
                    'pattern': matched_pattern
                })
        else:
            clean_rows.append(row)
    
    # 結果表示
    print(f"\n【削除されるプレースホルダー】")
    print(f"  総数: {len(removed_rows)}件")
    print(f"  指定IDリストから: {len(removed_from_target)}件")
    
    # プレースホルダータイプ別集計
    player_count = 0
    other_count = 0
    
    for row in removed_rows:
        name = row.get('person_name', '')
        if 'Player' in name or '選手' in name:
            player_count += 1
        else:
            other_count += 1
    
    print(f"\n【内訳】")
    print(f"  Player/選手系: {player_count}件")
    print(f"  その他: {other_count}件")
    
    # 削除例を表示
    print("\n【削除例（最初の20件）】")
    for i, item in enumerate(removed_from_target[:20], 1):
        print(f"  {i}. {item['id']}: {item['name']} / {item['name_ja']}")
    
    # クリーンデータ保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ultra_think_NO_PLACEHOLDERS_{timestamp}.csv"
    removed_file = f"removed_player_placeholders_{timestamp}.csv"
    
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
    
    # 最終統計
    print(f"\n【最終統計】")
    print(f"  元のレコード数: {len(all_rows)}名")
    print(f"  削除数: {len(removed_rows)}名")
    print(f"  最終数: {len(clean_rows)}名")
    print(f"  削減率: {len(removed_rows) / len(all_rows) * 100:.1f}%")
    
    # 指定IDリストの残存確認
    remaining_target_ids = 0
    for row in clean_rows:
        if row['person_id'] in target_ids:
            remaining_target_ids += 1
    
    print(f"\n【指定IDリストの状況】")
    print(f"  元の指定数: {len(target_ids)}")
    print(f"  削除された数: {len(removed_from_target)}")
    print(f"  残存数: {remaining_target_ids}")
    
    return output_file, len(clean_rows), len(removed_rows)

if __name__ == "__main__":
    print("🎌 Ultra Think Player系プレースホルダー削除処理")
    print("=" * 60)
    
    output_file, clean_count, removed_count = remove_player_placeholders()
    
    print("\n" + "=" * 60)
    print("🎉 プレースホルダー削除完了！")
    print(f"   最終的なクリーンな人数: {clean_count}名")