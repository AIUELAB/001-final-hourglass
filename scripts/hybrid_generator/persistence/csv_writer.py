"""
Safe CSV Writer

安全なCSV追記とトランザクション管理。
"""

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ..adapters.base import GenerationResult
from ..config import LOGS_DIR, MASTER_CSV
from .backup import BackupManager, create_pre_operation_backup


@dataclass
class WriteResult:
    """書き込み結果"""

    success: bool
    added_count: int = 0
    skipped_count: int = 0
    error_message: str = ""
    backup_path: Optional[Path] = None
    diff_log_path: Optional[Path] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "added_count": self.added_count,
            "skipped_count": self.skipped_count,
            "error_message": self.error_message,
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "diff_log_path": str(self.diff_log_path) if self.diff_log_path else None,
        }


@dataclass
class DiffEntry:
    """差分エントリ"""

    episode_id: str
    person_name: str
    age: int
    action: str  # 'add', 'update', 'delete'
    details: dict = field(default_factory=dict)


class SafeCSVWriter:
    """
    安全なCSV書き込み

    - dry-runモード
    - バックアップ作成
    - 差分ログ
    - トランザクション的操作
    """

    # CSVカラム順序
    COLUMN_ORDER = [
        "episode_id",
        "person_id",
        "person_name",
        "age",
        "category",
        "episode_text",
        "episode_type",
        "char_count",
        "person_type",
        "slot",
        "tier",
        "generation_timestamp",
        "記憶性スコア",
        "共感性スコア",
        "意外性スコア",
        "生成品質スコア",
        "教育的価値",
        "ストーリー品質",
        "事実密度",
        "composite_score",
        "super_total_score",
    ]

    def __init__(
        self,
        master_csv: Path = MASTER_CSV,
        logs_dir: Path = LOGS_DIR,
    ):
        self.master_csv = master_csv
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._backup_manager = BackupManager()

    def _generate_episode_id(self) -> str:
        """エピソードIDを生成"""
        timestamp = datetime.now().strftime("%y%m%d%H%M%S%f")[:15]
        return f"EP-{timestamp}"

    def _result_to_row(self, result: GenerationResult) -> dict:
        """GenerationResultをCSV行に変換"""
        row = result.to_csv_row()

        # エピソードIDを追加
        if "episode_id" not in row or not row["episode_id"]:
            row["episode_id"] = self._generate_episode_id()

        return row

    def _validate_row(self, row: dict) -> tuple[bool, str]:
        """行を検証"""
        required = ["person_id", "person_name", "age", "episode_text"]

        for field_name in required:
            if field_name not in row or not row[field_name]:
                return False, f"Missing required field: {field_name}"

        # 文字数チェック
        text = row.get("episode_text", "")
        if len(text) < 100:
            return False, f"Episode text too short: {len(text)}"

        return True, ""

    def _check_duplicate(self, row: dict, existing_df: pd.DataFrame) -> bool:
        """重複チェック"""
        if existing_df.empty:
            return False

        # 同一人物・同一年齢
        duplicates = existing_df[(existing_df["person_id"] == row["person_id"]) & (existing_df["age"] == row["age"])]

        return not duplicates.empty

    def dry_run(self, results: list[GenerationResult]) -> WriteResult:
        """
        dry-run実行（実際には書き込まない）

        Args:
            results: 生成結果リスト

        Returns:
            WriteResult: 実行結果
        """
        # 既存データ読み込み
        if self.master_csv.exists():
            existing_df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
        else:
            existing_df = pd.DataFrame()

        added_count = 0
        skipped_count = 0
        diff_entries = []

        for result in results:
            if not result.success:
                skipped_count += 1
                continue

            row = self._result_to_row(result)

            # 検証
            valid, error = self._validate_row(row)
            if not valid:
                skipped_count += 1
                continue

            # 重複チェック
            if self._check_duplicate(row, existing_df):
                skipped_count += 1
                continue

            added_count += 1
            diff_entries.append(
                DiffEntry(
                    episode_id=row["episode_id"],
                    person_name=row["person_name"],
                    age=row["age"],
                    action="add",
                    details={"category": row.get("category", "")},
                )
            )

        # 差分ログを保存
        diff_log_path = self._save_diff_log(diff_entries, dry_run=True)

        return WriteResult(
            success=True,
            added_count=added_count,
            skipped_count=skipped_count,
            diff_log_path=diff_log_path,
        )

    def write(self, results: list[GenerationResult]) -> WriteResult:
        """
        実際に書き込み

        Args:
            results: 生成結果リスト

        Returns:
            WriteResult: 実行結果
        """
        try:
            # 1. バックアップ作成
            backup_info = create_pre_operation_backup("hybrid_gen")
            backup_path = backup_info.path if backup_info else None

            # 2. 既存データ読み込み
            if self.master_csv.exists():
                existing_df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
            else:
                existing_df = pd.DataFrame()

            new_rows = []
            skipped_count = 0
            diff_entries = []

            for result in results:
                if not result.success:
                    skipped_count += 1
                    continue

                row = self._result_to_row(result)

                # 検証
                valid, error = self._validate_row(row)
                if not valid:
                    skipped_count += 1
                    continue

                # 重複チェック
                if self._check_duplicate(row, existing_df):
                    skipped_count += 1
                    continue

                new_rows.append(row)
                diff_entries.append(
                    DiffEntry(
                        episode_id=row["episode_id"],
                        person_name=row["person_name"],
                        age=row["age"],
                        action="add",
                        details={"category": row.get("category", "")},
                    )
                )

            if not new_rows:
                return WriteResult(
                    success=True,
                    added_count=0,
                    skipped_count=skipped_count,
                    backup_path=backup_path,
                )

            # 3. 新しい行を追加
            new_df = pd.DataFrame(new_rows)

            # カラム順序を整える
            for col in self.COLUMN_ORDER:
                if col not in new_df.columns:
                    new_df[col] = ""

            # 既存データと結合
            if not existing_df.empty:
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                combined_df = new_df

            # 4. 書き込み
            combined_df.to_csv(self.master_csv, index=False, encoding="utf-8-sig")

            # 5. 差分ログを保存
            diff_log_path = self._save_diff_log(diff_entries, dry_run=False)

            return WriteResult(
                success=True,
                added_count=len(new_rows),
                skipped_count=skipped_count,
                backup_path=backup_path,
                diff_log_path=diff_log_path,
            )

        except Exception as e:
            return WriteResult(
                success=False,
                error_message=str(e),
            )

    def _save_diff_log(self, entries: list[DiffEntry], dry_run: bool = False) -> Optional[Path]:
        """差分ログを保存"""
        if not entries:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "dryrun" if dry_run else "applied"
        log_path = self.logs_dir / f"diff_{prefix}_{timestamp}.json"

        log_data = {
            "timestamp": timestamp,
            "dry_run": dry_run,
            "entries": [
                {
                    "episode_id": e.episode_id,
                    "person_name": e.person_name,
                    "age": e.age,
                    "action": e.action,
                    "details": e.details,
                }
                for e in entries
            ],
        }

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        return log_path


def safe_append_episodes(results: list[GenerationResult], dry_run: bool = True) -> WriteResult:
    """
    エピソードを安全に追記

    Args:
        results: 生成結果リスト
        dry_run: True の場合は実際に書き込まない

    Returns:
        WriteResult: 実行結果
    """
    writer = SafeCSVWriter()

    if dry_run:
        return writer.dry_run(results)
    else:
        return writer.write(results)
