#!/usr/bin/env python3
"""
EPUP: 誤分類された架空キャラクターエピソード削除スクリプト

架空キャラクターなのに person_type = "REAL" に誤分類されているエピソードを
CSVから削除する。

処理フロー:
1. MASTER_EPISODES_CURRENT.csv のバックアップ作成（日付付き）
2. detect_person_type_mismatch.py と同じロジックで問題エピソードを検出
3. 問題エピソードをCSVから削除
4. 削除前後の件数を報告

使用方法:
    # ドライラン（確認のみ、デフォルト）
    python scripts/fix/remove_misclassified_fictional_episodes.py

    # 実行（実際に削除）
    python scripts/fix/remove_misclassified_fictional_episodes.py --execute

    # 詳細出力
    python scripts/fix/remove_misclassified_fictional_episodes.py --verbose

Author: EPUP Fix Team
Date: 2026-01-22
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# detect_person_type_mismatch.py からロジックをインポート
from scripts.validation.detect_person_type_mismatch import (
    PersonTypeMismatchDetector,
    ALL_FICTIONAL_CHARACTERS,
    BLACKLIST_NAMES,
)

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/data/backups"
LOG_DIR = PROJECT_ROOT / "src/reports/logs"


def create_backup(csv_path: Path) -> Path:
    """
    CSVファイルのバックアップを作成

    Args:
        csv_path: バックアップ元のCSVパス

    Returns:
        バックアップファイルのパス
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"MASTER_EPISODES_CURRENT_backup_{timestamp}.csv"
    backup_path = BACKUP_DIR / backup_filename

    shutil.copy2(csv_path, backup_path)

    return backup_path


def write_deletion_log(deleted_ids: list[str], log_dir: Path) -> Path:
    """
    削除したエピソードIDをログファイルに記録

    Args:
        deleted_ids: 削除したエピソードIDのリスト
        log_dir: ログ出力ディレクトリ

    Returns:
        ログファイルのパス
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"deleted_misclassified_fictional_{timestamp}.log"
    log_path = log_dir / log_filename

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("# 誤分類された架空キャラクターエピソード削除ログ\n")
        f.write(f"# 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 削除件数: {len(deleted_ids)}\n")
        f.write("#\n")
        f.write("# 削除したエピソードID一覧:\n")
        for eid in deleted_ids:
            f.write(f"{eid}\n")

    return log_path


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP: 誤分類された架空キャラクターエピソード削除")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に削除を実行（デフォルトはドライラン）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細出力",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="表示する最大件数（デフォルト: 50）",
    )

    args = parser.parse_args()
    is_dry_run = not args.execute

    # ヘッダー
    print("=" * 70)
    print("EPUP: 誤分類された架空キャラクターエピソード削除")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"モード: {'ドライラン（確認のみ）' if is_dry_run else '実行モード'}")
    print("=" * 70)

    # マスターCSV存在確認
    if not MASTER_CSV.exists():
        print(f"\nError: Master CSV not found: {MASTER_CSV}")
        return 2

    # 検出器初期化
    detector = PersonTypeMismatchDetector(MASTER_CSV)

    print(f"\nマスターCSV: {MASTER_CSV}")
    print(f"総エピソード数: {len(detector.master_df):,}")
    print(f"登録架空キャラクター数: {len(ALL_FICTIONAL_CHARACTERS)}")
    print(f"ブラックリスト（除外名）: {len(BLACKLIST_NAMES)}")

    # スキャン実行
    print("\n問題エピソードをスキャン中...")
    records = detector.scan_all()

    if not records:
        print("\n[OK] 誤分類されたエピソードは検出されませんでした")
        return 0

    # サマリー
    summary = detector.get_summary(records)

    print(f"\n{'=' * 70}")
    print("検出結果サマリー")
    print(f"{'=' * 70}")
    print(f"削除対象エピソード: {summary['total_mismatches']}件")
    print(f"ユニークキャラクター数: {summary['unique_characters']}人")
    print(f"ユニーク作品数: {summary['unique_works']}作品")

    if summary["by_work"]:
        print("\n作品別削除対象数:")
        for work, count in list(summary["by_work"].items())[:10]:
            print(f"  {work}: {count}件")

    if summary["by_character"]:
        print("\nキャラクター別削除対象数（上位10）:")
        for char, count in list(summary["by_character"].items())[:10]:
            print(f"  {char}: {count}件")

    # 詳細出力
    if args.verbose:
        limit = args.limit
        print(f"\n{'=' * 70}")
        print(f"削除対象詳細（上位{min(limit, len(records))}件）")
        print(f"{'=' * 70}")

        for i, record in enumerate(records[:limit], 1):
            print(f"\n{i}. {record.episode_id}")
            print(f"   人物名: {record.person_name}")
            print(f"   現在の分類: {record.current_person_type}")
            print(f"   マッチした作品: {record.matched_work}")
            print(f"   理由: {record.detection_reason}")

    # 削除対象エピソードID一覧
    episode_ids_to_delete = [r.episode_id for r in records]
    print(f"\n{'=' * 70}")
    print("削除対象エピソードID一覧")
    print(f"{'=' * 70}")
    print(f"総数: {len(episode_ids_to_delete)}件")
    for eid in episode_ids_to_delete[:20]:
        print(f"  {eid}")
    if len(episode_ids_to_delete) > 20:
        print(f"  ... 他 {len(episode_ids_to_delete) - 20}件")

    # ドライランの場合はここで終了
    if is_dry_run:
        print(f"\n{'=' * 70}")
        print("[DRY RUN] 確認のみ - 実際の削除は行われていません")
        print("削除を実行するには --execute オプションを付けて再実行してください:")
        print("  python scripts/fix/remove_misclassified_fictional_episodes.py --execute")
        print(f"{'=' * 70}")
        return 0

    # 実行モード: バックアップ作成
    print(f"\n{'=' * 70}")
    print("削除実行")
    print(f"{'=' * 70}")

    print("\n1. バックアップを作成中...")
    backup_path = create_backup(MASTER_CSV)
    print(f"   バックアップ: {backup_path}")

    # CSVから削除
    print("\n2. CSVから該当エピソードを削除中...")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    original_count = len(df)

    # 削除対象のエピソードIDをセットに変換（高速化）
    ids_to_delete_set = set(episode_ids_to_delete)

    # エピソードID列を文字列に変換して比較
    df["episode_id"] = df["episode_id"].astype(str)

    # 削除対象以外を残す
    df_filtered = df[~df["episode_id"].isin(ids_to_delete_set)]
    deleted_count = original_count - len(df_filtered)

    print(f"   削除前: {original_count:,}件")
    print(f"   削除後: {len(df_filtered):,}件")
    print(f"   削除数: {deleted_count:,}件")

    # CSVを上書き保存
    print("\n3. CSVを保存中...")
    df_filtered.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
    print(f"   保存完了: {MASTER_CSV}")

    # 削除ログ出力
    print("\n4. 削除ログを出力中...")
    log_path = write_deletion_log(episode_ids_to_delete, LOG_DIR)
    print(f"   ログ: {log_path}")

    # 完了
    print(f"\n{'=' * 70}")
    print("[SUCCESS] 削除完了")
    print(f"{'=' * 70}")
    print(f"削除件数: {deleted_count:,}件")
    print(f"バックアップ: {backup_path}")
    print(f"削除ログ: {log_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
