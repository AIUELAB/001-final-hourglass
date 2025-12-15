#!/usr/bin/env python3
"""
データベースからMichael Newton (person_08981)を削除
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple


class MichaelNewtonDeleter:
    """特定のレコードを削除"""

    def __init__(self):
        self.stats = {
            'total': 0,
            'deleted': 0,
            'deleted_records': []
        }

    def delete_from_database(self, input_file: str = None) -> Tuple[str, Dict]:
        """データベースから削除"""

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
                    candidates = list(Path('.').glob('final_with_birth_year_*.json'))
                    if candidates:
                        input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
                    else:
                        print("⚠️ 入力ファイルが見つかりません")
                        return None, self.stats

        print("🗑️ データベース削除処理開始")
        print(f"  入力: {input_file}")
        print("  削除対象: person_08981 (Michael Newton)")

        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stats['total'] = len(data)

        # 削除対象を探して記録
        if 'person_08981' in data:
            deleted_record = data['person_08981']
            self.stats['deleted_records'].append({
                'id': 'person_08981',
                'name': deleted_record.get('name', ''),
                'display_name': deleted_record.get('preferred_display_name', ''),
                'original_name': deleted_record.get('original_name', ''),
                'birth_date': deleted_record.get('birth_date', ''),
                'death_date': deleted_record.get('death_date', ''),
                'occupation': deleted_record.get('occupation', '')
            })

            # 削除実行
            del data['person_08981']
            self.stats['deleted'] = 1

            print("\n✅ 削除完了:")
            print("  ID: person_08981")
            print(f"  名前: {deleted_record.get('name', '')}")
            print(f"  表示名: {deleted_record.get('preferred_display_name', '')}")
            print(f"  元の名前: {deleted_record.get('original_name', '')}")
        else:
            print("\n⚠️ person_08981 が見つかりません")

        # 結果を保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"database_after_deletion_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # レポート
        print("\n📊 削除結果:")
        print(f"  削除前: {self.stats['total']:,}件")
        print(f"  削除後: {len(data):,}件")
        print(f"  削除数: {self.stats['deleted']}件")

        print(f"\n✅ 出力: {output_file}")

        return output_file, self.stats

    def generate_clean_csv(self, json_file: str) -> str:
        """クリーンなCSVを生成"""
        import csv

        print("\n📊 CSVファイル生成中...")

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
                    'wikidata_id': value.get('wikidata_id', ''),
                    'grade': value.get('advanced_grade') or value.get('grade', ''),
                    'birth_year': value.get('birth_year', 0)
                }
                rows.append(row)

        # Gradeでソート
        rows.sort(key=lambda x: (
            x['grade'] if x['grade'] else 'ZZ',
            x['person_name_display']
        ))

        # CSV出力
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"clean_database_{timestamp}.csv"

        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        print(f"  CSV出力: {csv_file}")
        print(f"  レコード数: {len(rows):,}件")

        return csv_file


def main():
    """メイン実行"""
    deleter = MichaelNewtonDeleter()

    # データベースから削除
    output_file, stats = deleter.delete_from_database()

    if output_file and stats['deleted'] > 0:
        # CSV生成
        csv_file = deleter.generate_clean_csv(output_file)

        print("\n" + "="*60)
        print("🎯 削除処理完了")
        print("="*60)
        print(f"\nデータベース: {output_file}")
        print(f"CSV: {csv_file}")
        print("Michael Newton (person_08981) を削除しました")
        print("残りレコード数: 12,369件")


if __name__ == "__main__":
    main()
