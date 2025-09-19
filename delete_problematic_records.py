#!/usr/bin/env python3
"""
データベースから問題のある表示名を持つレコードを削除
Mozart/Bach関連で不適切な表示名のレコードを削除
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class ProblematicRecordsDeleter:
    """問題のあるレコードを削除"""
    
    def __init__(self):
        # 削除対象のレコードID
        self.records_to_delete = [
            'person_11883',  # Franz Xaver Wolfgang Mozart → モーツァルト
            'person_11930',  # Maria Anna Mozart → モーツァルト
            'person_11937',  # Leopold Mozart → モーツァルト
            'person_05887',  # ヨハン・エルンスト・バッハ
            'person_05654',  # ヨハン・クリストフ・バッハ
            'person_05619',  # ヨハン・クリストフ・フリードリヒ・バッハ
        ]
        
        self.stats = {
            'total': 0,
            'deleted': 0,
            'deleted_records': []
        }
    
    def delete_from_database(self, input_file: str = None) -> Tuple[str, Dict]:
        """データベースから削除"""
        
        # 入力ファイルを探す
        if not input_file:
            # 最新の削除済みファイルを探す
            candidates = list(Path('.').glob('database_after_deletion_*.json'))
            if candidates:
                input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
            else:
                # なければ修正済みファイルを探す
                candidates = list(Path('.').glob('perfect_display_fixed_*.json'))
                if candidates:
                    input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
                else:
                    print("⚠️ 入力ファイルが見つかりません")
                    return None, self.stats
        
        print("🗑️ 問題レコード削除処理開始")
        print(f"  入力: {input_file}")
        print(f"  削除対象: {len(self.records_to_delete)}件")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['total'] = len(data)
        
        # 削除対象を処理
        print("\n削除実行:")
        for record_id in self.records_to_delete:
            if record_id in data:
                record = data[record_id]
                
                # 削除記録を保存
                self.stats['deleted_records'].append({
                    'id': record_id,
                    'person_name': record.get('original_name') or record.get('display_name', ''),
                    'person_name_ja': record.get('name', ''),
                    'person_name_display': record.get('preferred_display_name', ''),
                    'birth_date': record.get('birth_date', ''),
                    'occupation': record.get('occupation', ''),
                    'reason': '不適切な表示名（フルネーム→姓のみ）'
                })
                
                # 削除実行
                del data[record_id]
                self.stats['deleted'] += 1
                
                print(f"  ✅ {record_id}: {record.get('original_name', '')} → {record.get('preferred_display_name', '')} [削除]")
            else:
                print(f"  ⚠️ {record_id}: 見つかりません")
        
        # 結果を保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"database_cleaned_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # レポート
        print("\n📊 削除結果:")
        print(f"  削除前: {self.stats['total']:,}件")
        print(f"  削除後: {len(data):,}件")
        print(f"  削除数: {self.stats['deleted']}件")
        
        # 削除レコードの詳細
        if self.stats['deleted_records']:
            print("\n📝 削除されたレコード:")
            for rec in self.stats['deleted_records']:
                print(f"  {rec['id']}: {rec['person_name']} → {rec['person_name_display']}")
        
        print(f"\n✅ 出力: {output_file}")
        
        return output_file, self.stats
    
    def generate_final_csv(self, json_file: str) -> str:
        """最終的なクリーンCSVを生成"""
        import csv
        
        print("\n📊 最終CSVファイル生成中...")
        
        # JSONデータ読み込み
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # CSV用データ準備
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
                    'grade': value.get('advanced_grade') or value.get('grade', ''),
                    'data_source': value.get('data_source', 'wikidata'),
                    'created_at': value.get('created_at', datetime.now().strftime("%Y-%m-%d")),
                    'birth_year': value.get('birth_year', 0),
                    'advanced_grade': value.get('advanced_grade', ''),
                    'name_display_type': value.get('name_display_type', ''),
                    'is_criminal': 1 if value.get('is_criminal') else 0
                }
                rows.append(row)
        
        # Gradeでソート
        rows.sort(key=lambda x: (
            x['grade'] if x['grade'] else 'ZZ',
            -x['impact_score'],
            x['person_name_display']
        ))
        
        # カラム定義
        columns = [
            'id', 'person_name', 'person_name_ja', 'person_name_display',
            'birth_date', 'death_date', 'nationality', 'occupation',
            'main_category', 'subcategory', 'wikidata_id', 'description',
            'impact_score', 'japanese_relevance', 'grade',
            'data_source', 'created_at', 'birth_year',
            'advanced_grade', 'name_display_type', 'is_criminal'
        ]
        
        # CSV出力
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"final_database_{timestamp}.csv"
        
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"  CSV出力: {csv_file}")
        print(f"  レコード数: {len(rows):,}件")
        
        # サンプル表示
        print("\n📝 データサンプル（Mozart/Bach関連）:")
        for row in rows[:100]:
            if 'Mozart' in row['person_name'] or 'モーツァルト' in row['person_name_display']:
                print(f"  {row['id']}: {row['person_name']:30} → {row['person_name_display']}")
            elif 'Bach' in row['person_name'] or 'バッハ' in row['person_name_display']:
                print(f"  {row['id']}: {row['person_name']:30} → {row['person_name_display']}")
        
        return csv_file
    
    def create_deletion_report(self) -> str:
        """削除レポートを作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"DELETION_REPORT_{timestamp}.md"
        
        report = f"""# データベース削除レポート

## 削除実施日時
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 削除理由
フルネームから姓のみの表示名になってしまった不適切なレコード

## 削除結果
- **削除前**: {self.stats['total']:,}件
- **削除後**: {self.stats['total'] - self.stats['deleted']:,}件
- **削除数**: {self.stats['deleted']}件

## 削除されたレコード

| ID | 元の名前 | 不適切な表示名 | 理由 |
|----|---------|--------------|------|
"""
        
        for rec in self.stats['deleted_records']:
            report += f"| {rec['id']} | {rec['person_name']} | {rec['person_name_display']} | {rec['reason']} |\n"
        
        report += """

## 削除基準
1. フルネームから姓のみの表示になっている
2. 同じ姓の別人が混同される可能性がある
3. 表示名として不適切

---
*削除処理完了*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 削除レポート: {report_file}")
        
        return report_file


def main():
    """メイン実行"""
    deleter = ProblematicRecordsDeleter()
    
    # データベースから削除
    output_file, stats = deleter.delete_from_database()
    
    if output_file and stats['deleted'] > 0:
        # CSV生成
        csv_file = deleter.generate_final_csv(output_file)
        
        # レポート作成
        report_file = deleter.create_deletion_report()
        
        print("\n" + "="*60)
        print("🎯 削除処理完了")
        print("="*60)
        print(f"\nデータベース: {output_file}")
        print(f"CSV: {csv_file}")
        print(f"レポート: {report_file}")
        print(f"\n最終レコード数: {stats['total'] - stats['deleted']:,}件")
        print(f"（12,369件 → {stats['total'] - stats['deleted']:,}件）")


if __name__ == "__main__":
    main()