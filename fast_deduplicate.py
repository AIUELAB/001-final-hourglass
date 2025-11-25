#!/usr/bin/env python3
"""
高速重複除去スクリプト - 最適化版
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict
import re

class FastDeduplicator:
    """高速重複除去エンジン"""

    def __init__(self):
        self.stats = {
            'total_records': 0,
            'duplicates_found': 0,
            'records_merged': 0,
            'final_count': 0
        }

    def normalize_name(self, name: str) -> str:
        """名前の正規化（高速版）"""
        if not name:
            return ""

        # 基本的な正規化のみ
        name = name.replace('　', ' ')
        name = re.sub(r'[（(][^)）]*[)）]', '', name)
        return ' '.join(name.split()).strip()

    def deduplicate(self, input_file: str) -> Tuple[str, str]:
        """高速重複除去"""
        print("⚡ 高速重複除去開始")
        print(f"  入力: {input_file}")

        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stats['total_records'] = len(data)
        print(f"  レコード数: {self.stats['total_records']:,}件")

        # 名前でグループ化（単純な完全一致のみ）
        print("\n🔍 重複検出中...")
        name_to_keys = defaultdict(list)

        for key, value in data.items():
            if isinstance(value, dict):
                name = value.get('name', '')
                if name:
                    normalized = self.normalize_name(name)
                    name_to_keys[normalized].append(key)

        # 重複除去
        print("🔄 マージ中...")
        cleaned_data = {}
        processed = set()

        for name, keys in name_to_keys.items():
            if len(keys) > 1:
                # 重複あり - 最初のレコードを保持し、他から補完
                self.stats['duplicates_found'] += len(keys) - 1

                # 最初のレコードをベースに
                base_record = data[keys[0]].copy()

                # 他のレコードから欠損データを補完
                for key in keys[1:]:
                    other = data[key]
                    for field, value in other.items():
                        if not base_record.get(field) and value:
                            base_record[field] = value

                cleaned_data[keys[0]] = base_record
                processed.update(keys)
                self.stats['records_merged'] += len(keys) - 1
            else:
                # 重複なし
                cleaned_data[keys[0]] = data[keys[0]]
                processed.add(keys[0])

        self.stats['final_count'] = len(cleaned_data)

        # 結果を保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_json = f"deduplicated_{timestamp}.json"
        output_csv = f"deduplicated_{timestamp}.csv"

        print("\n💾 保存中...")

        # JSON保存
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

        # CSV保存
        self.save_to_csv(cleaned_data, output_csv)

        # 簡易レポート
        self.print_summary()

        print(f"\n✅ 完了!")
        print(f"  JSON: {output_json}")
        print(f"  CSV: {output_csv}")

        return output_json, output_csv

    def save_to_csv(self, data: Dict, filename: str):
        """CSV保存"""
        if not data:
            return

        # フィールド収集
        sample = next(iter(data.values()))
        fieldnames = ['id', 'name', 'original_name', 'person_name_ja',
                     'person_name_display', 'occupation', 'main_category',
                     'subcategory', 'birth_date', 'death_date', 'nationality']

        # 存在するフィールドのみ使用
        fieldnames = [f for f in fieldnames if f in sample or f == 'id']

        # 追加フィールド
        for value in data.values():
            if isinstance(value, dict):
                for key in value.keys():
                    if key not in fieldnames:
                        fieldnames.append(key)
                break

        # CSV書き込み
        with open(filename, 'w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for key, value in data.items():
                if isinstance(value, dict):
                    row = value.copy()
                    if 'id' not in row:
                        row['id'] = key
                    writer.writerow(row)

    def print_summary(self):
        """結果サマリー表示"""
        reduction_rate = (self.stats['duplicates_found'] / self.stats['total_records'] * 100) if self.stats['total_records'] > 0 else 0

        print("\n" + "=" * 60)
        print("📊 重複除去結果")
        print("=" * 60)
        print(f"元レコード数: {self.stats['total_records']:,}件")
        print(f"重複検出: {self.stats['duplicates_found']:,}件 ({reduction_rate:.1f}%)")
        print(f"最終レコード数: {self.stats['final_count']:,}件")
        print(f"削減: {self.stats['records_merged']:,}件")


def main():
    """メイン実行"""
    deduplicator = FastDeduplicator()

    # 最新のデータファイルを使用
    input_file = 'category_fixed_20250825_101132.json'

    json_file, csv_file = deduplicator.deduplicate(input_file)

    return json_file, csv_file


if __name__ == "__main__":
    main()
