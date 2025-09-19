#!/usr/bin/env python3
"""
正しいカラム構造を維持したCSVエクスポーター
元の仕様書のカラム名を厳守し、新規カラムは追加として末尾に配置
"""

import codecs
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class CorrectCSVExporter:
    """仕様書準拠のCSVエクスポーター"""
    
    def __init__(self):
        # 元の仕様書のカラム定義（順序も維持）
        self.original_columns = [
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
            'created_at'          # 作成日時
        ]
        
        # 新規追加カラム（末尾に追加）
        self.additional_columns = [
            'birth_year',          # 生誕年（英語表記）
            'advanced_grade',      # A-Z詳細グレード
            'name_display_type',   # 芸名/歴史的人物
            'is_criminal'          # 犯罪者フラグ
        ]
        
        self.stats = {
            'total': 0,
            'exported': 0,
            'mapping_success': 0,
            'mapping_failed': 0
        }
    
    def map_data_to_original_structure(self, key: str, person: Dict) -> Dict:
        """データを元の構造にマッピング"""
        
        # 元のカラムへのマッピング
        row = {
            'id': key,
            'person_name': person.get('original_name') or person.get('display_name', ''),
            'person_name_ja': person.get('name') or person.get('preferred_display_name', ''),
            'person_name_display': person.get('preferred_display_name') or person.get('display_name', ''),
            'birth_date': person.get('birth_date', ''),
            'death_date': person.get('death_date', ''),
            'nationality': person.get('nationality', ''),
            'occupation': person.get('occupation', ''),
            'main_category': person.get('main_category', ''),
            'subcategory': person.get('subcategory', ''),
            'wikidata_id': person.get('wikidata_id', ''),
            'description': person.get('description', ''),
            'impact_score': person.get('fame_score', 0),  # fame_score → impact_score
            'japanese_relevance': person.get('japanese_relevance', 0),
            'grade': person.get('advanced_grade') or person.get('grade', 'Unknown'),
            'data_source': person.get('data_source', 'wikidata'),
            'created_at': person.get('created_at', datetime.now().strftime("%Y-%m-%d"))
        }
        
        # 新規カラムの追加
        row['birth_year'] = person.get('birth_year', 0)
        row['advanced_grade'] = person.get('advanced_grade', '')
        row['name_display_type'] = person.get('name_display_type', '')
        row['is_criminal'] = 1 if person.get('is_criminal') else 0
        
        return row
    
    def export_with_correct_structure(self, input_file: str = None) -> Tuple[str, Dict]:
        """正しい構造でCSVエクスポート"""
        
        # 最新のデータファイルを探す
        if not input_file:
            candidates = list(Path('.').glob('final_with_birth_year_*.json'))
            if candidates:
                input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
            else:
                candidates = list(Path('.').glob('advanced_grade_*.json'))
                if candidates:
                    input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
                else:
                    print("⚠️ 入力ファイルが見つかりません")
                    return None, self.stats
        
        print("📊 正しいカラム構造でCSV生成開始")
        print(f"  入力: {input_file}")
        print(f"  元のカラム数: {len(self.original_columns)}")
        print(f"  追加カラム数: {len(self.additional_columns)}")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['total'] = len(data)
        
        # CSVデータ準備
        rows = []
        for key, value in data.items():
            if isinstance(value, dict):
                try:
                    row = self.map_data_to_original_structure(key, value)
                    rows.append(row)
                    self.stats['exported'] += 1
                    self.stats['mapping_success'] += 1
                except Exception as e:
                    print(f"  ⚠️ マッピングエラー ({key}): {e}")
                    self.stats['mapping_failed'] += 1
        
        # ソート（grade → impact_score → person_name_display）
        rows.sort(key=lambda x: (
            x['grade'] if x['grade'] != 'N/A' else 'ZZ',
            -x['impact_score'],
            x['person_name_display']
        ))
        
        # CSVファイル作成（UTF-8 BOM付き）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"correct_structure_{timestamp}.csv"
        
        # 全カラムリスト（元のカラム + 追加カラム）
        all_columns = self.original_columns + self.additional_columns
        
        # BOM付きUTF-8で書き込み
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_columns)
            
            # ヘッダー書き込み
            writer.writeheader()
            
            # データ書き込み
            writer.writerows(rows)
        
        # レポート出力
        print("\n✅ 正しい構造でCSV生成完了")
        print(f"  出力ファイル: {output_file}")
        print(f"  エクスポート: {self.stats['exported']:,}/{self.stats['total']:,}件")
        print(f"  マッピング成功: {self.stats['mapping_success']:,}件")
        print(f"  マッピング失敗: {self.stats['mapping_failed']:,}件")
        
        print("\n📋 カラム構造:")
        print(f"  元のカラム (1-17): {', '.join(self.original_columns)}")
        print(f"  追加カラム (18-21): {', '.join(self.additional_columns)}")
        
        print("\n⚠️ ルール遵守:")
        print("  ✅ 元のカラム名を維持")
        print("  ✅ 元のカラム順序を維持")
        print("  ✅ 新規カラムは末尾に追加")
        print("  ✅ 勝手な変更なし")
        
        # ルール記録ファイル作成
        self.save_rules()
        
        return output_file, self.stats
    
    def save_rules(self):
        """ルール違反防止の記録"""
        rules_file = "CSV_EXPORT_RULES.md"
        
        rules_content = """# CSV エクスポートルール

## 厳守事項

### 1. カラム名の変更禁止
- **元のカラム名は絶対に変更しない**
- impact_score を「有名度スコア」に変更 → ❌ 禁止
- grade を「Grade」に変更 → ❌ 禁止

### 2. カラム順序の維持
- 元の仕様書のカラム順序を維持する
- 1-17: 元のカラム（id〜created_at）
- 18以降: 新規追加カラム

### 3. 新規カラムの追加方法
- 必要な場合のみ、末尾に追加
- 英語表記で統一（birth_year等）
- 元のカラムと混在させない

## 元の仕様書カラム定義

| カラム名 | 説明 |
|---------|------|
| id | 人物ID |
| person_name | 原語表記 |
| person_name_ja | 日本語名 |
| person_name_display | 表示用短縮名 |
| birth_date | 生誕日 |
| death_date | 死亡日 |
| nationality | 国籍 |
| occupation | 職業 |
| main_category | メインカテゴリ |
| subcategory | サブカテゴリ |
| wikidata_id | WikidataID |
| description | 説明 |
| impact_score | 影響度スコア |
| japanese_relevance | 日本関連度 |
| grade | グレード |
| data_source | データソース |
| created_at | 作成日時 |

## データマッピング規則

- preferred_display_name → person_name_display
- fame_score → impact_score
- advanced_grade → grade（元のgradeを更新）
- original_name → person_name

## 違反防止チェックリスト

- [ ] カラム名を勝手に変更していないか？
- [ ] カラム順序を維持しているか？
- [ ] 新規カラムは末尾に追加したか？
- [ ] 元の仕様書を確認したか？

---

*このルールは厳守すること。違反は二度手間を生む。*
*記録日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        
        with open(rules_file, 'w', encoding='utf-8') as f:
            f.write(rules_content)
        
        print(f"\n📝 ルール記録: {rules_file}")


def main():
    """メイン実行"""
    exporter = CorrectCSVExporter()
    
    # 正しい構造でCSV生成
    csv_file, stats = exporter.export_with_correct_structure()
    
    if csv_file:
        print("\n" + "="*60)
        print("✅ 正しいカラム構造でCSV生成完了")
        print("="*60)
        print(f"\n最終CSV: {csv_file}")
        print("元の仕様書のカラム構造を完全に維持しました。")


if __name__ == "__main__":
    main()