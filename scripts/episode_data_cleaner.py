#!/usr/bin/env python3
"""
エピソードデータクリーニングスクリプト

非標準フォーマットのエピソードを検出し、以下の処理を行う：
1. 年齢データ検証（故人・寿命超過、存命者・未来年齢）
2. フォーマット検証（標準プレフィックスチェック）
3. 削除処理（バックアップ作成→削除実行→検証）
4. 再生成キュー作成（架空キャラで修正可能なものをリストアップ）
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 定数
CURRENT_YEAR = 2025
CSV_PATH = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = project_root / "preserved" / "data" / "backups"

# 標準フォーマットパターン
STANDARD_PREFIX_PATTERN = r"^あなたと同じ\d+歳のとき、.+は"


class EpisodeDataCleaner:
    """エピソードデータクリーニングクラス"""

    def __init__(self, csv_path: Path = CSV_PATH):
        self.csv_path = csv_path
        self.df: Optional[pd.DataFrame] = None
        self.issues: dict = {
            "deceased_age_exceeded": [],  # 故人・寿命超過
            "living_future_age": [],  # 存命者・未来年齢
            "format_invalid": [],  # フォーマット不正
            "unknown_person": [],  # 不明人物
            "group_not_individual": [],  # グループ（個人ではない）
            "fictional_format_invalid": [],  # 架空キャラ・フォーマット不正（再生成可能）
        }

    def load_data(self) -> None:
        """CSVデータを読み込む"""
        print(f"📂 データ読み込み: {self.csv_path}")
        self.df = pd.read_csv(self.csv_path, encoding="utf-8-sig")
        print(f"   総レコード数: {len(self.df)}件")

    def detect_issues(self) -> dict:
        """問題のあるエピソードを検出"""
        if self.df is None:
            self.load_data()

        print("\n🔍 問題検出中...")

        for idx, row in self.df.iterrows():
            episode_text = str(row.get("episode_text", ""))
            person_type = str(row.get("person_type", "")).upper()
            person_name = str(row.get("person_name", ""))
            age = row.get("age")

            # フォーマットチェック
            has_standard_prefix = bool(re.match(STANDARD_PREFIX_PATTERN, episode_text))

            if not has_standard_prefix:
                issue_data = {
                    "index": idx,
                    "episode_id": row.get("episode_id", ""),
                    "person_id": row.get("person_id", ""),
                    "person_name": person_name,
                    "age": age,
                    "person_type": person_type,
                    "episode_text_preview": episode_text[:100] + "..." if len(episode_text) > 100 else episode_text,
                }

                # カテゴリ分類
                if person_type == "FICTIONAL":
                    # 架空キャラは再生成可能
                    self.issues["fictional_format_invalid"].append(issue_data)
                elif self._is_deceased_age_exceeded(row, episode_text):
                    self.issues["deceased_age_exceeded"].append(issue_data)
                elif self._is_living_future_age(row, age):
                    self.issues["living_future_age"].append(issue_data)
                elif self._is_group(row, person_name):
                    self.issues["group_not_individual"].append(issue_data)
                elif self._is_unknown_person(row, episode_text):
                    self.issues["unknown_person"].append(issue_data)
                else:
                    # その他のフォーマット不正
                    self.issues["format_invalid"].append(issue_data)

        return self.issues

    def _is_deceased_age_exceeded(self, row: pd.Series, episode_text: str) -> bool:
        """故人の寿命超過チェック"""
        # エラーメッセージパターン
        error_patterns = [
            r"死亡年齢.*超え",
            r"すでに.*亡くなって",
            r"存命中のみ",
            r"寿命.*超過",
        ]
        for pattern in error_patterns:
            if re.search(pattern, episode_text):
                return True
        return False

    def _is_living_future_age(self, row: pd.Series, age) -> bool:
        """存命者の未来年齢チェック"""
        try:
            age_int = int(age)
            # 一般的に100歳以上で未確認の場合は未来年齢の可能性
            if age_int > 100:
                return True
        except (ValueError, TypeError):
            pass
        return False

    def _is_group(self, row: pd.Series, person_name: str) -> bool:
        """グループ（個人ではない）チェック"""
        group_keywords = ["チーム", "グループ", "バンド", "ユニット", "コンビ"]
        for keyword in group_keywords:
            if keyword in person_name:
                return True
        return False

    def _is_unknown_person(self, row: pd.Series, episode_text: str) -> bool:
        """不明人物チェック"""
        unknown_patterns = [
            r"情報.*見つかりません",
            r"不明な人物",
            r"検索結果なし",
        ]
        for pattern in unknown_patterns:
            if re.search(pattern, episode_text):
                return True
        return False

    def print_report(self) -> None:
        """検出結果レポートを表示"""
        print("\n" + "=" * 60)
        print("📊 検出結果レポート")
        print("=" * 60)

        total_issues = 0
        delete_count = 0
        regenerate_count = 0

        # 削除対象
        for category in ["deceased_age_exceeded", "living_future_age", "unknown_person", "group_not_individual"]:
            count = len(self.issues[category])
            total_issues += count
            delete_count += count
            if count > 0:
                print(f"\n❌ {self._get_category_name(category)}: {count}件 (削除対象)")
                for item in self.issues[category][:5]:  # 最初の5件のみ表示
                    print(f"   - {item['person_name']} ({item['age']}歳): {item['episode_text_preview'][:50]}...")
                if count > 5:
                    print(f"   ... 他 {count - 5}件")

        # 再生成対象（架空キャラ）
        count = len(self.issues["fictional_format_invalid"])
        total_issues += count
        regenerate_count += count
        if count > 0:
            print(f"\n🔄 {self._get_category_name('fictional_format_invalid')}: {count}件 (再生成対象)")
            for item in self.issues["fictional_format_invalid"][:5]:
                print(f"   - {item['person_name']} ({item['age']}歳)")
            if count > 5:
                print(f"   ... 他 {count - 5}件")

        # その他のフォーマット不正
        count = len(self.issues["format_invalid"])
        total_issues += count
        delete_count += count
        if count > 0:
            print(f"\n⚠️ {self._get_category_name('format_invalid')}: {count}件 (削除対象)")
            for item in self.issues["format_invalid"][:5]:
                print(f"   - {item['person_name']} ({item['age']}歳): {item['episode_text_preview'][:50]}...")
            if count > 5:
                print(f"   ... 他 {count - 5}件")

        print("\n" + "-" * 60)
        print(f"📈 サマリー")
        print(f"   総問題件数: {total_issues}件")
        print(f"   削除対象: {delete_count}件")
        print(f"   再生成対象: {regenerate_count}件")

    def _get_category_name(self, category: str) -> str:
        """カテゴリ名を取得"""
        names = {
            "deceased_age_exceeded": "故人・寿命超過",
            "living_future_age": "存命者・未来年齢",
            "format_invalid": "フォーマット不正",
            "unknown_person": "不明人物",
            "group_not_individual": "グループ（個人ではない）",
            "fictional_format_invalid": "架空キャラ・フォーマット不正",
        }
        return names.get(category, category)

    def create_backup(self) -> Path:
        """バックアップを作成"""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"MASTER_EPISODES_backup_{timestamp}.csv"

        print(f"\n📦 バックアップ作成: {backup_path}")
        self.df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        return backup_path

    def execute_deletion(self, dry_run: bool = True) -> dict:
        """削除を実行"""
        if self.df is None:
            self.load_data()

        # 削除対象のインデックスを収集
        delete_indices = []
        for category in ["deceased_age_exceeded", "living_future_age", "unknown_person", "group_not_individual", "format_invalid"]:
            for item in self.issues[category]:
                delete_indices.append(item["index"])

        if not delete_indices:
            print("\n✅ 削除対象はありません")
            return {"deleted": 0, "remaining": len(self.df)}

        if dry_run:
            print(f"\n🔍 ドライラン: {len(delete_indices)}件が削除対象")
            return {"deleted": len(delete_indices), "remaining": len(self.df) - len(delete_indices), "dry_run": True}

        # バックアップ作成
        self.create_backup()

        # 削除実行
        print(f"\n🗑️ 削除実行: {len(delete_indices)}件")
        self.df = self.df.drop(delete_indices)
        self.df.reset_index(drop=True, inplace=True)

        # 保存
        self.df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
        print(f"💾 保存完了: {len(self.df)}件")

        return {"deleted": len(delete_indices), "remaining": len(self.df)}

    def export_regeneration_queue(self) -> Path:
        """再生成キューをエクスポート"""
        queue_data = self.issues["fictional_format_invalid"]
        if not queue_data:
            print("\n✅ 再生成対象はありません")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        queue_path = project_root / "reports" / f"regeneration_queue_{timestamp}.csv"
        queue_path.parent.mkdir(parents=True, exist_ok=True)

        queue_df = pd.DataFrame(queue_data)
        queue_df.to_csv(queue_path, index=False, encoding="utf-8-sig")
        print(f"\n📄 再生成キュー出力: {queue_path}")
        print(f"   件数: {len(queue_data)}件")

        return queue_path


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="エピソードデータクリーニング")
    parser.add_argument("--detect", action="store_true", help="問題検出のみ")
    parser.add_argument("--delete", action="store_true", help="削除実行（ドライランなし）")
    parser.add_argument("--export-queue", action="store_true", help="再生成キューをエクスポート")
    args = parser.parse_args()

    cleaner = EpisodeDataCleaner()
    cleaner.load_data()
    cleaner.detect_issues()
    cleaner.print_report()

    if args.export_queue:
        cleaner.export_regeneration_queue()

    if args.delete:
        cleaner.execute_deletion(dry_run=False)
    elif not args.detect:
        # デフォルトはドライラン
        cleaner.execute_deletion(dry_run=True)


if __name__ == "__main__":
    main()
