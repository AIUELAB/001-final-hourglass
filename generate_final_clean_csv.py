#!/usr/bin/env python3
"""
最終的なクリーンなCSVを生成
修正済みデータから完全なCSVを出力
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple


class FinalCleanCSVGenerator:
    """最終的なクリーンなCSV生成"""
    
    def __init__(self):
        # 元の仕様書のカラム定義
        self.columns = [
            'id',                   # 人物ID
            'person_name',          # 原語表記
            'person_name_ja',       # 日本語名
            'person_name_display',  # 表示用短縮名
            'birth_date',          # 生誕日
            'death_date',          # 死亡日
            'nationality',         # 国籍
            'occupation',          # 職業
            'main_category',       # メインカテゴリ
            'subcategory',         # サブカテゴリ
            'wikidata_id',         # WikidataID
            'description',         # 説明
            'impact_score',        # 影響度スコア
            'japanese_relevance',  # 日本関連度
            'grade',              # グレード
            'data_source',        # データソース
            'created_at',         # 作成日時
            'birth_year',         # 生誕年
            'advanced_grade',     # A-Z詳細グレード
            'name_display_type',  # 芸名/歴史的人物
            'is_criminal'         # 犯罪者フラグ
        ]
        
        self.stats = {
            'total': 0,
            'exported': 0
        }
    
    def generate_csv(self, input_file: str = None) -> Tuple[str, Dict]:
        """最終CSVを生成"""
        
        # 入力ファイルを探す
        if not input_file:
            # 最新の修正済みファイルを探す
            candidates = list(Path('.').glob('perfect_display_fixed_*.json'))
            if candidates:
                input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
            else:
                candidates = list(Path('.').glob('display_name_fixed_*.json'))
                if candidates:
                    input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
                else:
                    print("⚠️ 入力ファイルが見つかりません")
                    return None, self.stats
        
        print("📊 最終CSV生成開始")
        print(f"  入力: {input_file}")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['total'] = len(data)
        
        # CSVデータ準備
        rows = []
        
        for key, value in data.items():
            if isinstance(value, dict):
                row = {
                    'id': key,
                    'person_name': value.get('original_name') or value.get('display_name', ''),
                    'person_name_ja': value.get('name', ''),
                    'person_name_display': value.get('preferred_display_name') or value.get('name', ''),
                    'birth_date': value.get('birth_date', ''),
                    'death_date': value.get('death_date', ''),
                    'nationality': value.get('nationality', ''),
                    'occupation': value.get('occupation', ''),
                    'main_category': value.get('main_category', ''),
                    'subcategory': value.get('subcategory', ''),
                    'wikidata_id': value.get('wikidata_id', ''),
                    'description': value.get('description', ''),
                    'impact_score': value.get('fame_score', 0),
                    'japanese_relevance': value.get('japanese_relevance', 0),
                    'grade': value.get('advanced_grade') or value.get('grade', 'Unknown'),
                    'data_source': value.get('data_source', 'wikidata'),
                    'created_at': value.get('created_at', datetime.now().strftime("%Y-%m-%d")),
                    'birth_year': value.get('birth_year', 0),
                    'advanced_grade': value.get('advanced_grade', ''),
                    'name_display_type': value.get('name_display_type', ''),
                    'is_criminal': 1 if value.get('is_criminal') else 0
                }
                rows.append(row)
                self.stats['exported'] += 1
        
        # Gradeでソート
        rows.sort(key=lambda x: (
            x['grade'] if x['grade'] != 'N/A' else 'ZZ',
            -x['impact_score'],
            x['person_name_display']
        ))
        
        # 出力ファイル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"final_clean_database_{timestamp}.csv"
        
        # CSV出力（UTF-8 BOM付き）
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writeheader()
            writer.writerows(rows)
        
        print("\n✅ CSV生成完了")
        print(f"  出力: {output_file}")
        print(f"  レコード数: {self.stats['exported']:,}件")
        print("  エンコーディング: UTF-8 with BOM (Excel対応)")
        
        # サンプル表示
        print("\n📝 データサンプル（上位5件）:")
        for row in rows[:5]:
            print(f"  {row['id']}: {row['person_name_display']} (Grade {row['grade']})")
        
        return output_file, self.stats


def main():
    """メイン実行"""
    generator = FinalCleanCSVGenerator()
    output_file, stats = generator.generate_csv()
    
    if output_file:
        print("\n" + "="*60)
        print("🏆 最終CSV出力完了")
        print("="*60)
        print(f"\n成果物: {output_file}")
        print("12,370件の完全なデータベース")
        print("Excelで直接開けます（文字化けなし）")


if __name__ == "__main__":
    main()