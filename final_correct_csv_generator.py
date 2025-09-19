#!/usr/bin/env python3
"""
最終的な正しいCSV生成
修正済みのdisplay_nameデータを使用
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class FinalCSVGenerator:
    """最終CSV生成"""
    
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
            'display_name_correct': 0,
            'display_name_issues': 0
        }
    
    def validate_display_name(self, name: str) -> bool:
        """display_nameが正しいか検証"""
        import re
        
        # 問題のあるパターン
        problematic_patterns = [
            r'^[a-z].*[\u30A0-\u30FF]',  # 小文字で始まってカタカナ含む
            r'[a-zA-Z]+[\u30A0-\u30FF]+[a-z]+',  # カタカナが単語の途中
            r'[a-z]+ [アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン]'  # 小文字 + カタカナ
        ]
        
        for pattern in problematic_patterns:
            if re.search(pattern, name):
                return False
        
        return True
    
    def map_data_to_structure(self, key: str, person: Dict) -> Dict:
        """データを正しい構造にマッピング"""
        
        # display_name の選択（修正済みデータを優先）
        display_name = person.get('preferred_display_name') or person.get('display_name', '')
        
        # display_nameの検証
        if not self.validate_display_name(display_name):
            self.stats['display_name_issues'] += 1
            # 問題がある場合は日本語名を使用
            display_name = person.get('name', display_name)
        else:
            self.stats['display_name_correct'] += 1
        
        # 元のカラムへのマッピング
        row = {
            'id': key,
            'person_name': person.get('original_name') or person.get('display_name', ''),
            'person_name_ja': person.get('name') or person.get('preferred_display_name', ''),
            'person_name_display': display_name,
            'birth_date': person.get('birth_date', ''),
            'death_date': person.get('death_date', ''),
            'nationality': person.get('nationality', ''),
            'occupation': person.get('occupation', ''),
            'main_category': person.get('main_category', ''),
            'subcategory': person.get('subcategory', ''),
            'wikidata_id': person.get('wikidata_id', ''),
            'description': person.get('description', ''),
            'impact_score': person.get('fame_score', 0),
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
    
    def generate_final_csv(self, input_file: str) -> Tuple[str, Dict]:
        """最終CSV生成"""
        
        print("📊 最終CSV生成開始")
        print(f"  入力: {input_file}")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['total'] = len(data)
        
        # CSVデータ準備
        rows = []
        
        # display_name問題のサンプル
        issue_samples = []
        
        for key, value in data.items():
            if isinstance(value, dict):
                row = self.map_data_to_structure(key, value)
                rows.append(row)
                self.stats['exported'] += 1
                
                # 問題のあるdisplay_nameをサンプル収集
                if not self.validate_display_name(row['person_name_display']):
                    if len(issue_samples) < 10:
                        issue_samples.append({
                            'id': key,
                            'display': row['person_name_display'],
                            'ja': row['person_name_ja']
                        })
        
        # ソート（grade → impact_score → person_name_display）
        rows.sort(key=lambda x: (
            x['grade'] if x['grade'] != 'N/A' else 'ZZ',
            -x['impact_score'],
            x['person_name_display']
        ))
        
        # CSVファイル作成（UTF-8 BOM付き）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"final_correct_{timestamp}.csv"
        
        # 全カラムリスト
        all_columns = self.original_columns + self.additional_columns
        
        # BOM付きUTF-8で書き込み
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_columns)
            writer.writeheader()
            writer.writerows(rows)
        
        # レポート出力
        print("\n✅ 最終CSV生成完了")
        print(f"  出力ファイル: {output_file}")
        print(f"  エクスポート: {self.stats['exported']:,}/{self.stats['total']:,}件")
        print(f"  display_name正常: {self.stats['display_name_correct']:,}件")
        print(f"  display_name問題: {self.stats['display_name_issues']:,}件")
        
        if issue_samples:
            print("\n⚠️ display_name に残存する問題:")
            for sample in issue_samples:
                print(f"  {sample['id']}: {sample['display']:30} (代替: {sample['ja']})")
        
        print("\n📋 カラム構造:")
        print("  元のカラム (1-17): 仕様書準拠")
        print("  追加カラム (18-21): birth_year, advanced_grade, name_display_type, is_criminal")
        
        # 検証レポート
        self.create_validation_report(output_file, rows[:100])
        
        return output_file, self.stats
    
    def create_validation_report(self, csv_file: str, sample_rows: List[Dict]):
        """検証レポート作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"VALIDATION_REPORT_{timestamp}.md"
        
        report = f"""# CSV検証レポート

## ファイル情報
- **CSVファイル**: `{csv_file}`
- **生成日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **総レコード数**: {self.stats['total']:,}件

## display_name 品質
- **正常**: {self.stats['display_name_correct']:,}件 ({self.stats['display_name_correct']/self.stats['total']*100:.1f}%)
- **問題あり**: {self.stats['display_name_issues']:,}件 ({self.stats['display_name_issues']/self.stats['total']*100:.1f}%)

## サンプルデータ（上位10件）

| ID | person_name_display | grade | impact_score |
|----|-------------------|-------|--------------|
"""
        
        for row in sample_rows[:10]:
            report += f"| {row['id']} | {row['person_name_display']} | {row['grade']} | {row['impact_score']} |\n"
        
        report += """
## カラム構造確認

✅ 元の仕様書カラム（1-17）:
- id, person_name, person_name_ja, person_name_display
- birth_date, death_date, nationality, occupation
- main_category, subcategory, wikidata_id, description
- impact_score, japanese_relevance, grade
- data_source, created_at

✅ 追加カラム（18-21）:
- birth_year: 生誕年
- advanced_grade: A-Z詳細グレード
- name_display_type: 芸名/歴史的人物
- is_criminal: 犯罪者フラグ

---
*検証完了*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 検証レポート: {report_file}")


def main():
    """メイン実行"""
    # コマンドライン引数から入力ファイルを取得
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # デフォルト: 最新の修正済みファイル
        candidates = list(Path('.').glob('perfect_display_fixed_*.json'))
        if candidates:
            input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
        else:
            print("⚠️ 入力ファイルが見つかりません")
            print("使用方法: python final_correct_csv_generator.py [input_file.json]")
            return
    
    generator = FinalCSVGenerator()
    csv_file, stats = generator.generate_final_csv(input_file)
    
    print("\n" + "="*60)
    print("🏆 最終CSV生成完了")
    print("="*60)
    print(f"\n最終成果物: {csv_file}")
    print("仕様書のカラム構造を完全に維持しています。")


if __name__ == "__main__":
    main()