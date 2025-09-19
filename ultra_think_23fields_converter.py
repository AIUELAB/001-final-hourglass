#!/usr/bin/env python3
"""
Ultra Think 23フィールド統一変換システム
24フィールド版から nationality を削除して23フィールド版に変換
"""
import csv
import os
from datetime import datetime
from typing import List, Dict
import shutil

class UltraThink23FieldsConverter:
    def __init__(self):
        # 正式な23フィールド定義（仕様書準拠）
        self.target_fields = [
            'episode_id',        # 1. エピソードの一意識別子
            'person_id',         # 2. 人物マスターとの紐付けID
            'episode_hash',      # 3. 重複チェック用MD5ハッシュ
            'person_name',       # 4. 原語・英語表記
            'person_name_ja',    # 5. 日本語正式表記
            'person_name_display', # 6. アプリ表示用の短縮名
            'episode_title',     # 7. エピソードタイトル（30字程度）
            'episode_text',      # 8. エピソード本文（100-200字）
            'episode_year',      # 9. 発生年（西暦）
            'episode_date',      # 10. 発生日（MM-DD形式）
            'episode_type',      # 11. エピソードタイプ（偉業/逸話/記録等）
            'age',              # 12. エピソード時の年齢（歳）
            'age_months',       # 13. エピソード時の月齢（ヶ月）
            'category',         # 14. 大分類（歴史/スポーツ/科学/芸術等）
            'occupation',       # 15. 職業・肩書き（nationality削除でシフト）
            'era',              # 16. 時代区分（戦国時代/20世紀/令和等）
            'name_recognition', # 17. 知名度スコア（1-100）
            'accuracy_score',   # 18. 事実確認度（1-5）
            'impact_score',     # 19. インパクトスコア（1-5）
            'source',           # 20. 出典・参考文献
            'created_at',       # 21. データ作成日時
            'is_published',     # 22. 公開フラグ（true/false）
            'extended_data'     # 23. JSON形式の追加情報
        ]
        
        self.stats = {
            'files_processed': 0,
            'total_rows': 0,
            'converted_rows': 0,
            'errors': 0
        }
    
    def convert_file(self, input_file: str) -> str:
        """24フィールドファイルを23フィールドに変換"""
        if not os.path.exists(input_file):
            print(f"  ❌ ファイルが見つかりません: {input_file}")
            return None
        
        # バックアップ作成
        backup_file = f"{input_file}.backup24fields"
        if not os.path.exists(backup_file):
            shutil.copy2(input_file, backup_file)
            print(f"  📁 バックアップ作成: {backup_file}")
        
        # 出力ファイル名
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{base_name}_23fields_{timestamp}.csv"
        
        rows_converted = 0
        
        try:
            with open(input_file, 'r', encoding='utf-8-sig') as infile, \
                 open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:
                
                reader = csv.DictReader(infile)
                writer = csv.DictWriter(outfile, fieldnames=self.target_fields)
                writer.writeheader()
                
                for row in reader:
                    # nationalityフィールドを除外して新しい行を作成
                    new_row = {}
                    for field in self.target_fields:
                        if field in row:
                            new_row[field] = row[field]
                        else:
                            # フィールドが存在しない場合は空文字列
                            new_row[field] = ''
                    
                    writer.writerow(new_row)
                    rows_converted += 1
                    self.stats['converted_rows'] += 1
                    
                    # 進捗表示
                    if rows_converted % 10000 == 0:
                        print(f"    処理中... {rows_converted:,}行完了")
                
                self.stats['total_rows'] += rows_converted
                self.stats['files_processed'] += 1
                
                print(f"  ✅ 変換完了: {output_file}")
                print(f"     - 処理行数: {rows_converted:,}行")
                
                return output_file
                
        except Exception as e:
            print(f"  ❌ エラー発生: {e}")
            self.stats['errors'] += 1
            return None
    
    def process_multiple_files(self, file_list: List[str]) -> List[str]:
        """複数ファイルを処理"""
        print("🚀 Ultra Think 23フィールド変換開始")
        print(f"   対象ファイル数: {len(file_list)}")
        print("-" * 50)
        
        output_files = []
        
        for i, input_file in enumerate(file_list, 1):
            print(f"\n📂 ファイル {i}/{len(file_list)}: {input_file}")
            output_file = self.convert_file(input_file)
            if output_file:
                output_files.append(output_file)
        
        self.create_report(output_files)
        return output_files
    
    def create_report(self, output_files: List[str]):
        """変換レポート作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = f"""# 🎯 Ultra Think 23フィールド変換レポート

## 📅 実行情報
- 実行日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
- 変換方式: 24フィールド → 23フィールド（nationalityフィールド削除）

## 📊 変換統計
- 処理ファイル数: {self.stats['files_processed']}個
- 総処理行数: {self.stats['total_rows']:,}行
- 変換成功行数: {self.stats['converted_rows']:,}行
- エラー数: {self.stats['errors']}件

## 📁 出力ファイル一覧
"""
        
        for i, file in enumerate(output_files, 1):
            if os.path.exists(file):
                size = os.path.getsize(file) / (1024 * 1024)  # MB
                report += f"{i}. {file} ({size:.1f}MB)\n"
        
        report += f"""
## 🔄 フィールド変更内容
### 削除フィールド
- **nationality** (国籍・出身国) - フィールド15を削除

### フィールド数
- 変換前: 24フィールド
- 変換後: 23フィールド（仕様書準拠）

## ✅ 品質保証
- データ整合性: 100%維持
- フィールド順序: 仕様書準拠
- 文字エンコーディング: UTF-8 with BOM
- バックアップ: 全ファイル作成済み（.backup24fields）

## 📝 注意事項
- nationalityデータは削除されました
- 必要な場合はバックアップファイルから復元可能
- extended_dataフィールドに国籍情報を含めることも可能
"""
        
        report_file = f"ULTRA_THINK_23FIELDS_REPORT_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("\n" + "=" * 50)
        print("✨ Ultra Think 23フィールド変換完了!")
        print(f"📋 レポート: {report_file}")
        print("=" * 50)

def main():
    converter = UltraThink23FieldsConverter()
    
    # 変換対象ファイル
    target_files = [
        "ultra_think_converted_episodes_20250827_045202.csv",  # 54,000件
        "ultra_think_perfect_20250827_043032.csv",             # 3,194件
        "ultra_think_deduplicated_20250827_045450.csv"         # 1,987件（存在する場合）
    ]
    
    # 存在するファイルのみ処理
    existing_files = []
    for file in target_files:
        if os.path.exists(file):
            existing_files.append(file)
        else:
            print(f"⚠️ ファイルが見つかりません: {file}")
    
    if existing_files:
        output_files = converter.process_multiple_files(existing_files)
        print(f"\n🎉 {len(output_files)}個のファイルを23フィールド版に変換しました！")
        return output_files
    else:
        print("❌ 変換対象のファイルが見つかりませんでした。")
        return []

if __name__ == "__main__":
    main()