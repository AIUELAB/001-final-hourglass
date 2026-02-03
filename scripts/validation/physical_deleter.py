#!/usr/bin/env python3
"""
Physical Deleter - CSVからエピソードを物理削除するモジュール

マスターCSVからエピソードを物理削除する機能を提供します。
削除前には必ずバックアップを作成し、復元機能も提供します。

使用方法:
    >>> from scripts.validation.physical_deleter import PhysicalDeleter, DeletionResult
    >>> deleter = PhysicalDeleter()
    >>> result = deleter.delete_episodes(["EP-123", "EP-456"], dry_run=True)
    >>> print(f"削除対象: {result.deleted_count}件")
    >>> result = deleter.delete_episodes(["EP-123", "EP-456"], dry_run=False)
    >>> print(f"削除完了: {result.deleted_count}件, バックアップ: {result.backup_path}")

CLI使用例:
    python scripts/validation/physical_deleter.py --ids EP-123 EP-456  # ドライラン
    python scripts/validation/physical_deleter.py --ids EP-123 EP-456 --execute  # 実行
    python scripts/validation/physical_deleter.py --restore preserved/backups/purge/pre_purge_20260203_120000.csv
"""

import argparse
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートの設定
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class DeletionResult:
    """削除結果を表すデータクラス"""

    success: bool
    deleted_count: int
    backup_path: Path
    error_message: str = ""
    deleted_episodes: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.success:
            return f"DeletionResult(success=True, deleted_count={self.deleted_count}, backup_path={self.backup_path})"
        return f"DeletionResult(success=False, error_message={self.error_message})"


class PhysicalDeleter:
    """
    CSVからエピソードを物理削除するクラス

    削除前にはバックアップを必ず作成し、
    復元機能やドライラン機能を提供します。
    """

    BACKUP_DIR = PROJECT_ROOT / "preserved/backups/purge"

    def __init__(self, master_csv: Path = MASTER_CSV):
        """
        初期化

        Args:
            master_csv: マスターCSVのパス（デフォルト: MASTER_EPISODES_CURRENT.csv）
        """
        self.master_csv = master_csv
        self.backup_dir = self.BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info("PhysicalDeleter initialized")
        logger.info(f"  Master CSV: {self.master_csv}")
        logger.info(f"  Backup dir: {self.backup_dir}")

    def create_backup(self) -> Path:
        """
        削除前バックアップを作成

        Returns:
            バックアップファイルのパス

        Raises:
            FileNotFoundError: マスターCSVが存在しない場合
            IOError: バックアップの作成に失敗した場合
        """
        if not self.master_csv.exists():
            raise FileNotFoundError(f"Master CSV not found: {self.master_csv}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"pre_purge_{timestamp}.csv"
        backup_path = self.backup_dir / backup_filename

        # ファイルをコピー
        df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")

        logger.info(f"Backup created: {backup_path} ({len(df)} episodes)")
        return backup_path

    def delete_episodes(self, episode_ids: list[str], dry_run: bool = True) -> DeletionResult:
        """
        指定されたエピソードを物理削除

        Args:
            episode_ids: 削除するエピソードIDのリスト
            dry_run: Trueの場合は削除せず件数のみ返す

        Returns:
            DeletionResult: 削除結果
        """
        if not episode_ids:
            logger.warning("No episode IDs provided")
            return DeletionResult(
                success=True,
                deleted_count=0,
                backup_path=Path(""),
                error_message="No episode IDs provided",
                deleted_episodes=[],
            )

        try:
            # CSVを読み込み
            if not self.master_csv.exists():
                return DeletionResult(
                    success=False,
                    deleted_count=0,
                    backup_path=Path(""),
                    error_message=f"Master CSV not found: {self.master_csv}",
                )

            df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
            original_count = len(df)

            # 削除対象のエピソードを特定
            episode_ids_list = list(episode_ids)
            mask = df["episode_id"].isin(episode_ids_list)
            episodes_to_delete = df[mask]["episode_id"].tolist()
            deleted_count = len(episodes_to_delete)

            # 見つからないIDを警告
            found_ids = set(episodes_to_delete)
            not_found = set(episode_ids_list) - found_ids
            if not_found:
                logger.warning(f"Episode IDs not found in CSV: {not_found}")

            logger.info(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
            logger.info(f"Original count: {original_count}")
            logger.info(f"Episodes to delete: {deleted_count}")

            if dry_run:
                # ドライランの場合は削除せず結果を返す
                logger.info("Dry run completed - no changes made")
                return DeletionResult(
                    success=True,
                    deleted_count=deleted_count,
                    backup_path=Path(""),
                    deleted_episodes=episodes_to_delete,
                )

            # 実行モード: バックアップを作成
            backup_path = self.create_backup()

            # 削除を実行
            df_after = df[~mask]
            final_count = len(df_after)

            # 整合性チェック
            expected_count = original_count - deleted_count
            if final_count != expected_count:
                error_msg = f"Integrity check failed: expected {expected_count}, got {final_count}"
                logger.error(error_msg)
                return DeletionResult(
                    success=False,
                    deleted_count=0,
                    backup_path=backup_path,
                    error_message=error_msg,
                )

            # CSVに書き込み
            df_after.to_csv(self.master_csv, index=False, encoding="utf-8-sig")

            # 削除したエピソードIDをログに記録
            for ep_id in episodes_to_delete:
                logger.info(f"Deleted: {ep_id}")

            logger.info(f"Deletion completed: {original_count} -> {final_count} episodes")
            logger.info(f"Backup available at: {backup_path}")

            return DeletionResult(
                success=True,
                deleted_count=deleted_count,
                backup_path=backup_path,
                deleted_episodes=episodes_to_delete,
            )

        except Exception as e:
            logger.error(f"Deletion failed: {e}")
            return DeletionResult(
                success=False,
                deleted_count=0,
                backup_path=Path(""),
                error_message=str(e),
            )

    def restore_from_backup(self, backup_path: Path) -> bool:
        """
        バックアップからマスターCSVを復元

        Args:
            backup_path: 復元するバックアップファイルのパス

        Returns:
            成功した場合True
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            # バックアップを読み込んで検証
            df_backup = pd.read_csv(backup_path, encoding="utf-8-sig")
            backup_count = len(df_backup)

            # 現在のマスターCSVの件数を取得
            current_count = 0
            df_current: pd.DataFrame | None = None
            if self.master_csv.exists():
                df_current = pd.read_csv(self.master_csv, encoding="utf-8-sig")
                current_count = len(df_current)

            logger.info(f"Restoring from backup: {backup_path}")
            logger.info(f"  Backup count: {backup_count}")
            logger.info(f"  Current count: {current_count}")

            # 復元前に現在の状態をバックアップ
            if df_current is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pre_restore_backup = self.backup_dir / f"pre_restore_{timestamp}.csv"
                df_current.to_csv(pre_restore_backup, index=False, encoding="utf-8-sig")
                logger.info(f"Pre-restore backup created: {pre_restore_backup}")

            # 復元を実行
            df_backup.to_csv(self.master_csv, index=False, encoding="utf-8-sig")
            logger.info(f"Restore completed: {backup_count} episodes")

            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def verify_deletion(self, episode_ids: list[str]) -> tuple[int, int]:
        """
        削除結果を検証

        Args:
            episode_ids: 検証するエピソードIDのリスト

        Returns:
            (削除済み件数, 残存件数) のタプル
        """
        if not self.master_csv.exists():
            logger.error(f"Master CSV not found: {self.master_csv}")
            return (0, 0)

        df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
        episode_ids_set = set(episode_ids)

        # CSVに存在するIDを確認
        existing_ids = set(df["episode_id"].values) & episode_ids_set
        remaining_count = len(existing_ids)
        deleted_count = len(episode_ids_set) - remaining_count

        logger.info("Verification result:")
        logger.info(f"  Requested: {len(episode_ids_set)}")
        logger.info(f"  Deleted: {deleted_count}")
        logger.info(f"  Remaining: {remaining_count}")

        if remaining_count > 0:
            logger.warning(f"  Still existing: {existing_ids}")

        return (deleted_count, remaining_count)

    def list_backups(self) -> list[Path]:
        """
        利用可能なバックアップファイルを一覧表示

        Returns:
            バックアップファイルのパスリスト（新しい順）
        """
        backups = sorted(self.backup_dir.glob("*.csv"), reverse=True)
        return backups


def main():
    """CLI エントリーポイント"""
    parser = argparse.ArgumentParser(
        description="CSV からエピソードを物理削除（バックアップ必須）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # ドライラン（削除せず件数確認）
  python scripts/validation/physical_deleter.py --ids EP-123 EP-456

  # 実際に削除
  python scripts/validation/physical_deleter.py --ids EP-123 EP-456 --execute

  # バックアップから復元
  python scripts/validation/physical_deleter.py --restore preserved/backups/purge/pre_purge_20260203_120000.csv

  # バックアップ一覧
  python scripts/validation/physical_deleter.py --list-backups

  # 削除結果を検証
  python scripts/validation/physical_deleter.py --verify EP-123 EP-456
""",
    )

    parser.add_argument(
        "--ids",
        nargs="+",
        help="削除するエピソードID（複数指定可）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に削除を実行（指定しない場合はドライラン）",
    )
    parser.add_argument(
        "--restore",
        type=Path,
        metavar="BACKUP_PATH",
        help="指定したバックアップから復元",
    )
    parser.add_argument(
        "--list-backups",
        action="store_true",
        help="利用可能なバックアップを一覧表示",
    )
    parser.add_argument(
        "--verify",
        nargs="+",
        metavar="EPISODE_ID",
        help="指定したエピソードIDの削除状態を検証",
    )

    args = parser.parse_args()

    deleter = PhysicalDeleter()

    # バックアップ一覧
    if args.list_backups:
        print("=" * 60)
        print("Available Backups")
        print("=" * 60)
        backups = deleter.list_backups()
        if backups:
            for backup in backups:
                size_mb = backup.stat().st_size / (1024 * 1024)
                print(f"  {backup.name} ({size_mb:.2f} MB)")
        else:
            print("  No backups found")
        return 0

    # 復元
    if args.restore:
        print("=" * 60)
        print("Restore from Backup")
        print("=" * 60)
        success = deleter.restore_from_backup(args.restore)
        return 0 if success else 1

    # 削除検証
    if args.verify:
        print("=" * 60)
        print("Verify Deletion")
        print("=" * 60)
        deleted, remaining = deleter.verify_deletion(args.verify)
        print(f"\nResult: {deleted} deleted, {remaining} remaining")
        return 0 if remaining == 0 else 1

    # 削除実行
    if args.ids:
        print("=" * 60)
        print("Physical Deleter")
        print("=" * 60)
        print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
        print(f"Episode IDs: {len(args.ids)}")
        print()

        result = deleter.delete_episodes(args.ids, dry_run=not args.execute)

        print()
        print("=" * 60)
        print("Result")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Deleted count: {result.deleted_count}")
        if result.backup_path and result.backup_path.exists():
            print(f"Backup: {result.backup_path}")
        if result.error_message:
            print(f"Error: {result.error_message}")

        if not args.execute and result.deleted_count > 0:
            print()
            print("To execute deletion, add --execute flag")

        return 0 if result.success else 1

    # 引数がない場合はヘルプを表示
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
