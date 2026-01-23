#!/usr/bin/env python3
"""
EPUP: メタ要素違反エピソード削除スクリプト

RCA-20260123で検出されたメタ要素違反エピソードをCSVから削除する。
違反レポート（src/reports/meta_violations_report_20260123.txt）から
episode_idリストを読み込み、該当エピソードを一括削除。

処理フロー:
1. 違反IDリストファイル（/tmp/meta_violation_ids.txt）を読み込み
2. MASTER_EPISODES_CURRENT.csv のバックアップ作成
3. 該当エピソードをCSVから削除
4. 削除前後の件数を報告

使用方法:
    # ドライラン（確認のみ、デフォルト）
    python scripts/fix/remove_meta_violation_episodes.py --dry-run

    # 実行（実際に削除）
    python scripts/fix/remove_meta_violation_episodes.py --execute

    # 詳細出力
    python scripts/fix/remove_meta_violation_episodes.py --execute --verbose

Author: EPUP Fix Team
Date: 2026-01-23
RCA: RCA-20260123 メタ要素違反検出
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

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/data/backups"
LOG_DIR = PROJECT_ROOT / "src/reports/logs"
DEFAULT_IDS_FILE = Path("/tmp/meta_violation_ids.txt")


def load_violation_ids(ids_file: Path) -> list[str]:
    """
    違反IDリストファイルを読み込む

    Args:
        ids_file: 違反IDリストファイルのパス

    Returns:
        エピソードIDのリスト
    """
    if not ids_file.exists():
        raise FileNotFoundError(f"IDリストファイルが見つかりません: {ids_file}")

    with open(ids_file, "r", encoding="utf-8") as f:
        ids = [line.strip() for line in f if line.strip()]

    return ids


def create_backup(csv_path: Path) -> Path:
    """
    CSVファイルのバックアップを作成

    Args:
        csv_path: バックアップ元のCSVパス

    Returns:
        バックアップファイルのパス
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")
    backup_filename = f"MASTER_EPISODES_{timestamp}_pre_meta_fix.csv"
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
    log_filename = f"deleted_meta_violations_{timestamp}.log"
    log_path = log_dir / log_filename

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("# メタ要素違反エピソード削除ログ\n")
        f.write(f"# 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 削除件数: {len(deleted_ids)}\n")
        f.write("# RCA: RCA-20260123\n")
        f.write("#\n")
        f.write("# 削除したエピソードID一覧:\n")
        for eid in deleted_ids:
            f.write(f"{eid}\n")

    return log_path


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP: メタ要素違反エピソード削除")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（確認のみ）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に削除を実行",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細出力",
    )
    parser.add_argument(
        "--ids-file",
        type=Path,
        default=DEFAULT_IDS_FILE,
        help=f"違反IDリストファイル（デフォルト: {DEFAULT_IDS_FILE}）",
    )

    args = parser.parse_args()

    # --executeも--dry-runも指定されていない場合はdry-run
    if not args.execute and not args.dry_run:
        args.dry_run = True

    is_dry_run = args.dry_run or not args.execute

    # ヘッダー
    print("=" * 70)
    print("EPUP: メタ要素違反エピソード削除（RCA-20260123）")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"モード: {'ドライラン（確認のみ）' if is_dry_run else '実行モード'}")
    print("=" * 70)

    # IDリストファイル確認
    if not args.ids_file.exists():
        print(f"\n[ERROR] IDリストファイルが見つかりません: {args.ids_file}")
        print("\n以下のコマンドでIDリストを生成してください:")
        print("  grep 'episode_id: EP-' src/reports/meta_violations_report_20260123.txt | \\")
        print("    sed 's/episode_id: //' | sort -u > /tmp/meta_violation_ids.txt")
        return 2

    # マスターCSV存在確認
    if not MASTER_CSV.exists():
        print(f"\n[ERROR] マスターCSVが見つかりません: {MASTER_CSV}")
        return 2

    # 違反IDリスト読み込み
    print(f"\nIDリストファイル: {args.ids_file}")
    violation_ids = load_violation_ids(args.ids_file)
    print(f"削除対象ID数: {len(violation_ids)}件")

    # マスターCSV読み込み
    print(f"\nマスターCSV: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    print(f"現在のエピソード数: {len(df):,}件")

    # episode_idを文字列に変換
    df["episode_id"] = df["episode_id"].astype(str)

    # 削除対象をセットに変換
    ids_to_delete = set(violation_ids)

    # CSVに存在する削除対象を確認
    existing_ids = set(df["episode_id"].tolist())
    matched_ids = ids_to_delete & existing_ids
    missing_ids = ids_to_delete - existing_ids

    print(f"\nCSVで一致した削除対象: {len(matched_ids)}件")
    if missing_ids:
        print(f"CSVに存在しないID: {len(missing_ids)}件")
        if args.verbose and len(missing_ids) <= 20:
            for mid in sorted(missing_ids)[:20]:
                print(f"  - {mid}")

    # 削除対象詳細（verbose時）
    if args.verbose:
        print("\n" + "=" * 70)
        print("削除対象エピソード詳細（上位20件）")
        print("=" * 70)

        df_to_delete = df[df["episode_id"].isin(list(matched_ids))]
        for i, (_, row) in enumerate(df_to_delete.head(20).iterrows(), 1):
            print(f"\n{i}. {row['episode_id']}")
            print(f"   人物名: {row.get('person_name', 'N/A')}")
            print(f"   年齢: {row.get('age', 'N/A')}")
            if "episode_text" in row:
                text = str(row["episode_text"])[:80]
                print(f"   テキスト: {text}...")

        if len(matched_ids) > 20:
            print(f"\n   ... 他 {len(matched_ids) - 20}件")

    # ドライランの場合はここで終了
    if is_dry_run:
        print(f"\n{'=' * 70}")
        print("[DRY RUN] 確認のみ - 実際の削除は行われていません")
        print("=" * 70)
        print(f"\n[INFO] 削除対象: {len(matched_ids)}件")
        print("\n削除を実行するには --execute オプションを付けて再実行してください:")
        print("  python scripts/fix/remove_meta_violation_episodes.py --execute")
        print(f"{'=' * 70}")
        return 0

    # 実行モード: バックアップ作成
    print(f"\n{'=' * 70}")
    print("削除実行")
    print("=" * 70)

    print("\n1. バックアップを作成中...")
    backup_path = create_backup(MASTER_CSV)
    print(f"   [INFO] バックアップ作成: {backup_path}")

    # CSVから削除
    print("\n2. CSVから該当エピソードを削除中...")
    original_count = len(df)

    # 削除対象以外を残す
    df_filtered = df[~df["episode_id"].isin(list(ids_to_delete))]
    deleted_count = original_count - len(df_filtered)

    print(f"   削除前: {original_count:,}件")
    print(f"   削除後: {len(df_filtered):,}件")
    print(f"   [INFO] 削除完了: {deleted_count}件")

    # CSVを上書き保存
    print("\n3. CSVを保存中...")
    df_filtered.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
    print(f"   保存完了: {MASTER_CSV}")

    # 削除ログ出力
    print("\n4. 削除ログを出力中...")
    log_path = write_deletion_log(list(matched_ids), LOG_DIR)
    print(f"   ログ: {log_path}")

    # 完了
    print(f"\n{'=' * 70}")
    print("[SUCCESS] 削除完了")
    print("=" * 70)
    print(f"[INFO] 削除対象: {len(violation_ids)}件")
    print(f"[INFO] バックアップ作成: {backup_path}")
    print(f"[INFO] 削除完了: {deleted_count}件")
    print(f"[INFO] 残存エピソード: {len(df_filtered):,}件")

    return 0


if __name__ == "__main__":
    sys.exit(main())
