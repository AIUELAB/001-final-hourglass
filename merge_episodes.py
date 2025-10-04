#!/usr/bin/env python3
"""
エピソードCSVファイル統合スクリプト
既存の29件と新規生成の30件を統合し、重複チェックを行う
"""

import csv
import os
from datetime import datetime
from typing import Dict, List, Set, Tuple

class EpisodeMerger:
    def __init__(self):
        self.existing_file = "episodes_29_corrected_20250922_210220.csv"
        self.new_file = "episodes_30persons_20250923_093219.csv"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = f"episodes_merged_{self.timestamp}.csv"

    def load_csv(self, filepath: str) -> Tuple[List[str], List[Dict]]:
        """CSVファイルを読み込む"""
        data = []
        headers = []

        if not os.path.exists(filepath):
            print(f"❌ ファイルが見つかりません: {filepath}")
            return headers, data

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            for row in reader:
                data.append(row)

        print(f"✅ {filepath} から {len(data)}件のエピソードを読み込みました")
        return headers, data

    def check_duplicates(self, data1: List[Dict], data2: List[Dict]) -> Set[str]:
        """重複する人物名をチェック"""
        names1 = {row['person_name'] for row in data1}
        names2 = {row['person_name'] for row in data2}
        duplicates = names1 & names2

        if duplicates:
            print(f"⚠️ 重複する人物名を検出: {', '.join(sorted(duplicates))}")
        else:
            print("✅ 重複する人物名はありません")

        return duplicates

    def merge_episodes(self) -> None:
        """エピソードを統合"""
        print("\n" + "="*60)
        print("📊 エピソード統合処理")
        print("="*60)

        # 既存エピソードを読み込み
        headers1, existing_data = self.load_csv(self.existing_file)

        # 新規エピソードを読み込み
        headers2, new_data = self.load_csv(self.new_file)

        if not existing_data or not new_data:
            print("❌ データの読み込みに失敗しました")
            return

        # 重複チェック
        duplicates = self.check_duplicates(existing_data, new_data)

        # 重複を除外した新規データ
        filtered_new_data = [row for row in new_data
                            if row['person_name'] not in duplicates]

        print(f"\n📝 統合対象:")
        print(f"   - 既存エピソード: {len(existing_data)}件")
        print(f"   - 新規エピソード: {len(new_data)}件")
        if duplicates:
            print(f"   - 重複除外: {len(duplicates)}件")
        print(f"   - 統合後の総数: {len(existing_data) + len(filtered_new_data)}件")

        # データを統合
        merged_data = existing_data + filtered_new_data

        # カテゴリ別に集計
        categories = {}
        for row in merged_data:
            category = row.get('category', '不明')
            categories[category] = categories.get(category, 0) + 1

        # 統合ファイルを出力
        self.save_merged_csv(headers1, merged_data)

        # 統計情報を表示
        self.show_statistics(merged_data, categories)

    def save_merged_csv(self, headers: List[str], data: List[Dict]) -> None:
        """統合したデータをCSVファイルに保存"""
        with open(self.output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        print(f"\n✅ 統合ファイルを生成しました: {self.output_file}")

    def show_statistics(self, data: List[Dict], categories: Dict[str, int]) -> None:
        """統計情報を表示"""
        print("\n" + "="*60)
        print("📈 統合後の統計情報")
        print("="*60)

        # 文字数統計
        char_counts = [int(row.get('character_count', 0)) for row in data
                      if row.get('character_count')]
        if char_counts:
            avg_chars = sum(char_counts) / len(char_counts)
            min_chars = min(char_counts)
            max_chars = max(char_counts)

            print(f"\n📏 文字数統計:")
            print(f"   - 平均: {avg_chars:.1f}文字")
            print(f"   - 最小: {min_chars}文字")
            print(f"   - 最大: {max_chars}文字")

        # カテゴリ別統計
        print(f"\n📂 カテゴリ別内訳:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {category}: {count}件")

        # 有効性統計
        valid_count = sum(1 for row in data if row.get('is_valid') == 'True')
        valid_rate = (valid_count / len(data) * 100) if data else 0
        print(f"\n✅ 有効エピソード: {valid_count}/{len(data)}件 ({valid_rate:.1f}%)")

        # 人物名一覧（最初の10名）
        print(f"\n👥 統合された人物（一部）:")
        for i, row in enumerate(data[:10]):
            print(f"   {i+1:2d}. {row['person_name']}")
        if len(data) > 10:
            print(f"   ... 他{len(data)-10}名")

def main():
    """メイン処理"""
    merger = EpisodeMerger()
    merger.merge_episodes()
    print("\n✨ 統合処理が完了しました！")

if __name__ == "__main__":
    main()