#!/usr/bin/env python3
"""
自動統合システム
週次バッチとマスターファイルの自動マージ
"""

import csv
import os
import shutil
from datetime import datetime
from typing import Dict, List, Set, Tuple
from collections import Counter

class AutoMergeSystem:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = "backups"
        self.weekly_dir = "weekly"
        self.master_dir = "master"

        # ディレクトリ作成
        for dir_name in [self.backup_dir, self.weekly_dir, self.master_dir]:
            os.makedirs(dir_name, exist_ok=True)

    def find_latest_batch(self) -> str:
        """最新の週次バッチファイルを検索"""
        batch_files = [f for f in os.listdir('.') if f.startswith('weekly_batch_')]
        if not batch_files:
            return None

        # 最新のファイルを取得
        latest = sorted(batch_files)[-1]
        print(f"📁 最新バッチファイル検出: {latest}")
        return latest

    def find_master_file(self) -> str:
        """マスターファイルを検索"""
        # 優先順位でマスターファイルを検索
        candidates = [
            "master/episodes_master_current.csv",
            "episodes_merged_20250923_093733.csv",
            "episodes_master_current.csv"
        ]

        for file in candidates:
            if os.path.exists(file):
                print(f"📁 マスターファイル検出: {file}")
                return file

        # 最新のmergedファイルを検索
        merged_files = [f for f in os.listdir('.') if f.startswith('episodes_merged_')]
        if merged_files:
            latest = sorted(merged_files)[-1]
            print(f"📁 マスターファイル検出: {latest}")
            return latest

        return None

    def backup_master(self, master_file: str) -> str:
        """マスターファイルのバックアップ作成"""
        if not os.path.exists(master_file):
            return None

        backup_name = f"{self.backup_dir}/backup_{self.timestamp}.csv"
        shutil.copy2(master_file, backup_name)
        print(f"💾 バックアップ作成: {backup_name}")
        return backup_name

    def load_csv(self, filepath: str) -> Tuple[List[str], List[Dict]]:
        """CSVファイルを読み込む"""
        data = []
        headers = []

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            for row in reader:
                data.append(row)

        return headers, data

    def check_duplicates(self, master_data: List[Dict], batch_data: List[Dict]) -> Tuple[Set[str], List[Dict]]:
        """重複チェックと除外"""
        master_names = {row['person_name'] for row in master_data}
        batch_names = {row['person_name'] for row in batch_data}
        duplicates = master_names & batch_names

        # 重複を除外した新規データ
        unique_batch = [row for row in batch_data if row['person_name'] not in duplicates]

        return duplicates, unique_batch

    def merge_data(self, master_file: str, batch_file: str) -> str:
        """データを統合"""
        print("\n" + "="*60)
        print("🔄 自動統合処理開始")
        print("="*60)

        # マスターファイルのバックアップ
        self.backup_master(master_file)

        # データ読み込み
        headers, master_data = self.load_csv(master_file)
        _, batch_data = self.load_csv(batch_file)

        print(f"\n📊 統合前の状態:")
        print(f"   - マスター: {len(master_data)}件")
        print(f"   - バッチ: {len(batch_data)}件")

        # 重複チェック
        duplicates, unique_batch = self.check_duplicates(master_data, batch_data)

        if duplicates:
            print(f"\n⚠️ 重複検出: {', '.join(sorted(duplicates))}")
            print(f"   → 重複分を除外して統合")
        else:
            print(f"\n✅ 重複なし")

        # データ統合
        merged_data = master_data + unique_batch
        new_count = len(unique_batch)

        print(f"\n📈 統合後の状態:")
        print(f"   - 新規追加: {new_count}件")
        print(f"   - 総件数: {len(merged_data)}件")

        # 新しいマスターファイルを生成
        output_file = f"episodes_master_{self.timestamp}.csv"
        self.save_merged_data(headers, merged_data, output_file)

        # masterディレクトリに現在のマスターとしてコピー
        current_master = f"{self.master_dir}/episodes_master_current.csv"
        shutil.copy2(output_file, current_master)
        print(f"✅ 現在のマスター更新: {current_master}")

        # 週次バッチをアーカイブ
        archived_batch = f"{self.weekly_dir}/{os.path.basename(batch_file)}"
        shutil.move(batch_file, archived_batch)
        print(f"📦 バッチをアーカイブ: {archived_batch}")

        return output_file

    def save_merged_data(self, headers: List[str], data: List[Dict], output_file: str) -> None:
        """統合データを保存"""
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        print(f"✅ 新マスターファイル生成: {output_file}")

    def show_statistics(self, merged_file: str) -> None:
        """統合後の統計情報表示"""
        _, data = self.load_csv(merged_file)

        print("\n" + "="*60)
        print("📊 統合後の統計情報")
        print("="*60)

        # カテゴリー分析
        categories = Counter(row['category'] for row in data)
        total = len(data)

        print(f"\n📂 カテゴリー分布 (全{total}件):")
        for category, count in categories.most_common():
            percentage = count / total * 100
            print(f"   - {category}: {count}件 ({percentage:.1f}%)")

        # 文字数統計
        char_counts = [int(row['character_count']) for row in data if row.get('character_count')]
        if char_counts:
            avg_chars = sum(char_counts) / len(char_counts)
            print(f"\n📏 平均文字数: {avg_chars:.1f}文字")

        # 有効率
        valid_count = sum(1 for row in data if row.get('is_valid') == 'True')
        valid_rate = valid_count / total * 100
        print(f"\n✅ 有効率: {valid_count}/{total}件 ({valid_rate:.1f}%)")

        # 目標達成状況
        print(f"\n🎯 目標達成状況:")
        if total < 100:
            print(f"   Phase 1 (100件): {total}/100件 ({total}%)")
        elif total < 500:
            print(f"   Phase 2 (500件): {total}/500件 ({total/5:.1f}%)")
        else:
            print(f"   Phase 3 (1000件+): {total}件")

    def run_merge(self, batch_file: str = None, master_file: str = None) -> bool:
        """統合処理を実行"""
        # バッチファイルの特定
        if not batch_file:
            batch_file = self.find_latest_batch()
            if not batch_file:
                print("❌ バッチファイルが見つかりません")
                return False

        # マスターファイルの特定
        if not master_file:
            master_file = self.find_master_file()
            if not master_file:
                print("❌ マスターファイルが見つかりません")
                print("💡 ヒント: 初回の場合は既存のCSVファイルをマスターとして指定してください")
                return False

        # 統合実行
        try:
            merged_file = self.merge_data(master_file, batch_file)
            self.show_statistics(merged_file)

            print("\n✨ 自動統合完了！")
            return True

        except Exception as e:
            print(f"❌ 統合中にエラーが発生: {e}")
            return False

    def create_weekly_report(self) -> None:
        """週次レポートを生成"""
        master_file = f"{self.master_dir}/episodes_master_current.csv"
        if not os.path.exists(master_file):
            return

        _, data = self.load_csv(master_file)
        total = len(data)

        report_file = f"weekly_report_{self.timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 週次エピソード追加レポート\n\n")
            f.write(f"**生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}\n\n")
            f.write(f"## 📊 全体統計\n\n")
            f.write(f"- **総エピソード数**: {total}件\n")
            f.write(f"- **今週の追加数**: 10件\n")
            f.write(f"- **次週の目標**: {total + 10}件\n\n")

            # カテゴリー分析
            categories = Counter(row['category'] for row in data)
            f.write("## 📂 カテゴリー分布\n\n")
            f.write("| カテゴリー | 件数 | 割合 |\n")
            f.write("|-----------|------|------|\n")
            for category, count in categories.most_common():
                percentage = count / total * 100
                f.write(f"| {category} | {count} | {percentage:.1f}% |\n")

            f.write("\n## 🎯 次週の優先事項\n\n")
            # 10%未満のカテゴリーを特定
            underrepresented = [cat for cat, count in categories.items()
                               if count / total < 0.10]
            if underrepresented:
                f.write("以下のカテゴリーを優先的に追加:\n")
                for cat in underrepresented:
                    f.write(f"- {cat}\n")
            else:
                f.write("- カテゴリーバランスは良好\n")
                f.write("- 新規カテゴリーの開拓を検討\n")

        print(f"\n📄 週次レポート生成: {report_file}")

def main():
    """メイン処理"""
    import sys

    merger = AutoMergeSystem()

    # コマンドライン引数でファイル指定可能
    batch_file = sys.argv[1] if len(sys.argv) > 1 else None
    master_file = sys.argv[2] if len(sys.argv) > 2 else None

    # 統合実行
    if merger.run_merge(batch_file, master_file):
        # 週次レポート生成
        merger.create_weekly_report()

if __name__ == "__main__":
    main()