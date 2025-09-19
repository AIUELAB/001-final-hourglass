#!/usr/bin/env python3
"""
品質問題修正システム - 日本語名設定
実在アーティストの芸名を適切に処理
"""

import csv
import json
from datetime import datetime
import io


class JapaneseNameQualityFixer:
    """日本語名の品質問題を修正"""
    
    def __init__(self):
        self.fixed_count = 0
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 芸名・グループ名の日本語表記辞書
        self.name_corrections = {
            'Ado': 'Ado',  # そのまま
            'After the Rain': 'After the Rain',  # そのまま
            'Ayase': 'Ayase',  # そのまま
            'CLAMP': 'CLAMP',  # そのまま
            'DAIGO': 'DAIGO',  # そのまま
            'DJ LOVE': 'DJ LOVE',  # そのまま
            'Eve': 'Eve',  # そのまま
            'Fukase': 'Fukase',  # そのまま
            'GACKT': 'GACKT',  # そのまま
            'HEATH': 'HEATH',  # そのまま
            'HIKAKIN': 'HIKAKIN',  # そのまま
            'HISASHI': 'HISASHI',  # そのまま
            'IKKO': 'IKKO',  # そのまま
            'INORAN': 'INORAN',  # そのまま
            'JIRO': 'JIRO',  # そのまま
            'J': 'J',  # そのまま
            'Nakajin': 'Nakajin',  # そのまま
            'PATA': 'PATA',  # そのまま
            'RM': 'RM',  # BTS
            'RYUICHI': 'RYUICHI',  # そのまま
            'SUGIZO': 'SUGIZO',  # そのまま
            'Saori': 'Saori',  # そのまま
            'TAKURO': 'TAKURO',  # そのまま
            'TERU': 'TERU',  # そのまま
            'Toshl': 'Toshl',  # そのまま
            'Vaundy': 'Vaundy',  # そのまま
            'V': 'V',  # BTS
            'YOASOBI': 'YOASOBI',  # そのまま
            'YOSHIKI': 'YOSHIKI',  # そのまま
            'YuNi': 'YuNi',  # そのまま
            'hyde': 'hyde',  # そのまま
            'ken': 'ken',  # そのまま
            'tetsuya': 'tetsuya',  # そのまま
            'yukihiro': 'yukihiro',  # そのまま
        }
        
        # グループはそもそも削除対象
        self.groups_to_remove = [
            'After the Rain',
            'CLAMP',
            'YOASOBI'
        ]
    
    def fix_database(self, input_file: str):
        """データベースの品質問題を修正"""
        
        print(f"\n🔧 品質問題修正開始: {input_file}")
        
        persons = []
        removed = []
        
        # CSVファイル読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            
            reader = csv.DictReader(io.StringIO(content))
            
            for row in reader:
                person_name = row.get('person_name', '')
                
                # グループチェック
                if person_name in self.groups_to_remove:
                    removed.append(row)
                    print(f"  ❌ グループ削除: {person_name}")
                    continue
                
                # 日本語名修正
                if person_name == row.get('person_name_ja', ''):
                    if person_name in self.name_corrections:
                        # 芸名の場合はperson_name_displayを適切に設定
                        row['person_name_ja'] = self.name_corrections[person_name]
                        row['person_name_display'] = self.name_corrections[person_name]
                        self.fixed_count += 1
                        print(f"  ✅ 修正: {person_name} → {row['person_name_display']}")
                
                persons.append(row)
        
        print(f"\n📊 修正結果:")
        print(f"  修正: {self.fixed_count}件")
        print(f"  削除: {len(removed)}件")
        print(f"  残存: {len(persons)}件")
        
        return persons, removed
    
    def save_fixed_database(self, persons: list):
        """修正済みデータベースを保存"""
        
        output_csv = f"ultra_think_QUALITY_FIXED_{self.timestamp}.csv"
        output_json = f"ultra_think_QUALITY_FIXED_{self.timestamp}.json"
        
        # CSV保存
        if persons:
            headers = list(persons[0].keys())
            
            with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(persons)
            
            print(f"\n✅ CSV保存: {output_csv}")
            
            # JSON保存
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(persons, f, ensure_ascii=False, indent=2)
            
            print(f"✅ JSON保存: {output_json}")
        
        return output_csv


def main():
    """メイン処理"""
    
    print("=" * 60)
    print("🔧 品質問題修正システム")
    print("芸名・グループ名の適切な処理")
    print("=" * 60)
    
    # 対象ファイル
    input_file = 'ULTRA_THINK_FINAL_20250827_083951.csv'
    
    # 修正システム初期化
    fixer = JapaneseNameQualityFixer()
    
    # Step 1: 品質問題修正
    persons, removed = fixer.fix_database(input_file)
    
    # Step 2: 修正済みデータベース保存
    output_file = fixer.save_fixed_database(persons)
    
    print("\n" + "=" * 60)
    print("✨ 品質問題修正完了")
    print(f"  次のステップ: {output_file}でプレースホルダー削除を再実行")
    print("=" * 60)


if __name__ == "__main__":
    main()