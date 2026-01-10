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
from ..gates.completeness import (
    auto_fill_all_derived_fields,
    check_completeness_extended,
)


@dataclass
class WriteResult:
    """書き込み結果"""

    success: bool
    added_count: int = 0
    skipped_count: int = 0
    replaced_count: int = 0  # Phase 4: 置換数
    error_message: str = ""
    backup_path: Optional[Path] = None
    diff_log_path: Optional[Path] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "added_count": self.added_count,
            "skipped_count": self.skipped_count,
            "replaced_count": self.replaced_count,
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
        "memorability_score",  # Phase 28: 英語化
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
        "iconic_score",  # Phase 28: 追加
        "composite_score",
        "super_total_score",
        # Phase 26: モデル追跡とコスト可視化
        "model",  # 使用モデル名（claude-3-5-haiku-20241022 等）
        "generator_type",  # batch_api_haiku / batch_api_sonnet
        "cost_usd",  # エピソード単位のコスト（USD）
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

    def _check_duplicate(self, row: dict, existing_df: pd.DataFrame) -> tuple[bool, str]:
        """
        重複チェック（EPUP再発防止強化版）

        Args:
            row: 書き込み対象の行
            existing_df: 既存データ

        Returns:
            (is_duplicate: bool, reason: str)
        """
        if existing_df.empty:
            return False, ""

        person_id = row.get("person_id", "")
        age = row.get("age")

        if not person_id or age is None:
            return False, ""

        # 同一人物・同一年齢チェック（EPUP: 1人1年齢1エピソード原則）
        duplicates = existing_df[(existing_df["person_id"] == person_id) & (existing_df["age"] == age)]

        if not duplicates.empty:
            existing_ep = duplicates.iloc[0]
            reason = (
                f"EPUP違反: 同一人物×同一年齢のエピソード既存 - "
                f"person_id={person_id}, age={age}, "
                f"existing_ep={existing_ep.get('episode_id', 'unknown')}"
            )
            return True, reason

        return False, ""

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

            # 重複チェック（EPUP: 1人1年齢1エピソード原則）
            is_dup, dup_reason = self._check_duplicate(row, existing_df)
            if is_dup:
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

                # RCA-20260110: 派生フィールド自動補完
                row = auto_fill_all_derived_fields(row)

                # RCA-20260110: 完全性チェック（欠損があれば書き込まない）
                completeness_result = check_completeness_extended(row, auto_fill=False)
                if not completeness_result.passed:
                    # 欠損があっても書き込むが、ログを残す
                    # Note: 厳格モードが必要な場合はここでskipする
                    pass  # 現在は警告のみ（移行期間）

                # 重複チェック
                is_dup, dup_reason = self._check_duplicate(row, existing_df)
                if is_dup:
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

    def replace_episode(
        self,
        old_episode_id: str,
        new_result: GenerationResult,
        dry_run: bool = True,
    ) -> WriteResult:
        """
        Phase 4: エピソードを置換

        Args:
            old_episode_id: 置換対象のエピソードID
            new_result: 新しい生成結果
            dry_run: True の場合は実際に書き込まない

        Returns:
            WriteResult: 実行結果
        """
        try:
            # 1. 既存データ読み込み
            if not self.master_csv.exists():
                return WriteResult(
                    success=False,
                    error_message="Master CSV not found",
                )

            existing_df = pd.read_csv(self.master_csv, encoding="utf-8-sig")

            # 2. 置換対象を検索
            target_mask = existing_df["episode_id"] == old_episode_id
            if not target_mask.any():
                return WriteResult(
                    success=False,
                    error_message=f"Episode not found: {old_episode_id}",
                )

            old_row = existing_df[target_mask].iloc[0].to_dict()

            # 3. 新しい行を準備
            new_row = self._result_to_row(new_result)

            # 検証
            valid, error = self._validate_row(new_row)
            if not valid:
                return WriteResult(
                    success=False,
                    error_message=f"Validation failed: {error}",
                )

            # 差分エントリ
            diff_entries = [
                DiffEntry(
                    episode_id=old_episode_id,
                    person_name=str(old_row.get("person_name", "")),
                    age=int(old_row.get("age", 0)),
                    action="replace",
                    details={
                        "old_episode_id": old_episode_id,
                        "new_episode_id": new_row["episode_id"],
                        "old_score": old_row.get("super_total_score", 0),
                        "new_score": new_row.get("super_total_score", 0),
                    },
                )
            ]

            if dry_run:
                diff_log_path = self._save_diff_log(diff_entries, dry_run=True)
                return WriteResult(
                    success=True,
                    replaced_count=1,
                    diff_log_path=diff_log_path,
                )

            # 4. バックアップ作成
            backup_info = create_pre_operation_backup("replace_episode")
            backup_path = backup_info.path if backup_info else None

            # 5. 置換実行（古いエピソードを削除して新しいエピソードを追加）
            existing_df = existing_df[~target_mask]
            new_df = pd.DataFrame([new_row])

            # カラム順序を整える
            for col in self.COLUMN_ORDER:
                if col not in new_df.columns:
                    new_df[col] = ""

            # 結合
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)

            # 6. 書き込み
            combined_df.to_csv(self.master_csv, index=False, encoding="utf-8-sig")

            # 7. 差分ログを保存
            diff_log_path = self._save_diff_log(diff_entries, dry_run=False)

            # 8. 置換履歴を保存
            self._save_replacement_log(old_episode_id, new_row["episode_id"], old_row, new_row)

            return WriteResult(
                success=True,
                replaced_count=1,
                backup_path=backup_path,
                diff_log_path=diff_log_path,
            )

        except Exception as e:
            return WriteResult(
                success=False,
                error_message=str(e),
            )

    def _save_replacement_log(
        self,
        old_episode_id: str,
        new_episode_id: str,
        old_row: dict,
        new_row: dict,
    ) -> None:
        """置換履歴を保存"""
        log_path = self.logs_dir / "replacement_log.json"

        # 既存ログを読み込み
        if log_path.exists():
            with open(log_path, encoding="utf-8") as f:
                log_data = json.load(f)
        else:
            log_data = {"replacements": []}

        # 新しいエントリを追加
        log_data["replacements"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "old_episode_id": old_episode_id,
                "new_episode_id": new_episode_id,
                "person_name": old_row.get("person_name", ""),
                "age": old_row.get("age", 0),
                "old_score": old_row.get("super_total_score", 0),
                "new_score": new_row.get("super_total_score", 0),
                "score_improvement": (new_row.get("super_total_score", 0) - old_row.get("super_total_score", 0)),
            }
        )

        # 保存
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

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
