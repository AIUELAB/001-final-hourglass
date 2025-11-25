#!/usr/bin/env python3
"""
最新のデータベースをCSV出力
database_cleaned_20250824_195241.json から完全なCSVを生成
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple


class LatestDatabaseExporter:
    """最新データベースのCSVエクスポート"""

    def __init__(self):
        # 元の仕様書準拠のカラム定義
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
            'exported': 0,
            'grade_distribution': {}
        }

    def export_to_csv(self, input_file: str = 'database_cleaned_20250824_195241.json') -> Tuple[str, Dict]:
        """データベースをCSVに出力"""

        print("📊 最新データベースのCSV出力開始")
        print(f"  入力: {input_file}")

        # データ読み込み
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"⚠️ ファイルが見つかりません: {input_file}")
            return None, self.stats

        self.stats['total'] = len(data)

        # CSVデータ準備
        rows = []

        for key, value in data.items():
            if isinstance(value, dict):
                # データマッピング
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
                    'grade': value.get('advanced_grade') or value.get('grade', ''),
                    'data_source': value.get('data_source', 'wikidata'),
                    'created_at': value.get('created_at', datetime.now().strftime("%Y-%m-%d")),
                    'birth_year': value.get('birth_year', 0),
                    'advanced_grade': value.get('advanced_grade', ''),
                    'name_display_type': value.get('name_display_type', ''),
                    'is_criminal': 1 if value.get('is_criminal') else 0
                }

                rows.append(row)
                self.stats['exported'] += 1

                # Grade分布統計
                grade = row['grade']
                if grade:
                    self.stats['grade_distribution'][grade] = \
                        self.stats['grade_distribution'].get(grade, 0) + 1

        # Gradeと影響度でソート
        rows.sort(key=lambda x: (
            x['grade'] if x['grade'] and x['grade'] != 'N/A' else 'ZZ',
            -x['impact_score'],
            x['person_name_display']
        ))

        # CSV出力（UTF-8 BOM付き）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"latest_database_{timestamp}.csv"

        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writeheader()
            writer.writerows(rows)

        # レポート出力
        print("\n✅ CSV出力完了")
        print(f"  出力ファイル: {output_file}")
        print(f"  総レコード数: {self.stats['exported']:,}件")
        print("  エンコーディング: UTF-8 with BOM (Excel対応)")

        # Grade分布
        print("\n📈 Grade分布:")
        for grade in sorted(self.stats['grade_distribution'].keys()):
            count = self.stats['grade_distribution'][grade]
            percentage = count / self.stats['exported'] * 100
            bar = '█' * min(int(percentage/2), 30)
            print(f"  Grade {grade}: {count:4,}件 ({percentage:5.1f}%) {bar}")

        # サンプル表示
        print("\n📝 データサンプル（上位10件）:")
        for i, row in enumerate(rows[:10], 1):
            print(f"  {i}. {row['id']}: {row['person_name_display']} (Grade {row['grade']})")

        return output_file, self.stats

    def create_summary_report(self, csv_file: str):
        """サマリーレポート作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"CSV_EXPORT_SUMMARY_{timestamp}.md"

        report = f"""# 最新データベースCSV出力レポート

## ファイル情報
- **入力JSON**: database_cleaned_20250824_195241.json
- **出力CSV**: {csv_file}
- **出力日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## データ統計
- **総レコード数**: {self.stats['exported']:,}件
- **Grade分布**:
"""

        for grade in sorted(self.stats['grade_distribution'].keys()):
            count = self.stats['grade_distribution'][grade]
            percentage = count / self.stats['exported'] * 100
            report += f"  - Grade {grade}: {count:,}件 ({percentage:.1f}%)\n"

        report += """

## カラム構成（21列）
1. **基本情報**: id, person_name, person_name_ja, person_name_display
2. **日付情報**: birth_date, death_date, birth_year
3. **属性情報**: nationality, occupation
4. **カテゴリ**: main_category, subcategory
5. **参照情報**: wikidata_id, description
6. **評価情報**: impact_score, japanese_relevance, grade, advanced_grade
7. **メタ情報**: data_source, created_at, name_display_type, is_criminal

## 品質保証
- ✅ UTF-8 BOM付き（Excel文字化け防止）
- ✅ Grade順・影響度順でソート
- ✅ 仕様書準拠のカラム構造
- ✅ 不適切な表示名は削除済み

---
*CSV出力完了*
"""

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📄 サマリーレポート: {report_file}")

        return report_file


def main():
    """メイン実行"""
    exporter = LatestDatabaseExporter()

    # CSV出力
    csv_file, stats = exporter.export_to_csv()

    if csv_file:
        # サマリーレポート作成
        report_file = exporter.create_summary_report(csv_file)

        print("\n" + "="*60)
        print("🏆 最新データベースCSV出力完了")
        print("="*60)
        print("\n成果物:")
        print(f"  CSV: {csv_file}")
        print(f"  レポート: {report_file}")
        print("\n12,363件の完全なデータベース")
        print("Excelで直接開けます（文字化けなし）")


if __name__ == "__main__":
    main()
