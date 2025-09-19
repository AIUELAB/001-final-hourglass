#!/usr/bin/env python3
"""
Newtonのperson_name_display違反を修正
英語表記の"Newton"をカタカナの"ニュートン"に統一
"""
import csv
import json
from datetime import datetime

def fix_newton_display_names():
    """Newtonの表示名を修正"""
    input_file = "migrated_episodes_final_20250826_013954.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"migrated_episodes_fixed_{timestamp}.csv"
    
    fixed_count = 0
    total_rows = 0
    
    # CSVファイルを読み込み、修正して新しいファイルに書き込み
    with open(input_file, 'r', encoding='utf-8-sig') as infile, \
         open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:
        
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            total_rows += 1
            
            # Newton関連のエントリーを検出
            if row.get('person_name') and 'Newton' in row['person_name']:
                # person_name_displayがNewton（英語）の場合修正
                if row.get('person_name_display') == 'Newton':
                    row['person_name_display'] = 'ニュートン'
                    fixed_count += 1
                
                # 不完全な表記も修正
                elif row.get('person_name_display') in ['ニュー', 'ケンブリッジ']:
                    row['person_name_display'] = 'ニュートン'
                    fixed_count += 1
            
            writer.writerow(row)
    
    # レポート作成
    report = f"""
# Newton表示名修正レポート
作成日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

## 修正結果
- 入力ファイル: {input_file}
- 出力ファイル: {output_file}
- 総エピソード数: {total_rows:,}
- 修正件数: {fixed_count}

## 修正内容
- "Newton"（英語） → "ニュートン"（カタカナ）
- "ニュー"（不完全） → "ニュートン"（カタカナ）
- "ケンブリッジ"（誤記） → "ニュートン"（カタカナ）

## ルール根拠
PERSON_NAME_DISPLAY_UNIFIED_RULES.mdに基づく：
- 西洋の歴史的偉人は姓のみで特定可能な場合は姓だけでOK
- ニュートンは物理学者として唯一無二
- 日本語表記（カタカナ）を使用
"""
    
    report_file = f"NEWTON_FIX_REPORT_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 修正完了")
    print(f"  - 修正件数: {fixed_count}件")
    print(f"  - 出力ファイル: {output_file}")
    print(f"  - レポート: {report_file}")
    
    return output_file, fixed_count

if __name__ == "__main__":
    fix_newton_display_names()