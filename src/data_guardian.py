#!/usr/bin/env python3
"""
Data Guardian - データ保管の完全性を保証するシステム

主な機能:
- 変更前のチェックポイント作成
- 変更の妥当性検証
- 品質低下時の自動ロールバック
- Tombstoneによる削除追跡

使用方法:
    >>> from src.data_guardian import DataGuardian
    >>> guardian = DataGuardian()
    >>> checkpoint_id = guardian.pre_modification_checkpoint()
    >>> # ... データ変更処理 ...
    >>> guardian.verify_modification(checkpoint_id)
"""

import csv
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.backup_manager import BackupManager
from src.csv_path_resolver import get_master_csv_path, get_project_root


class TombstoneManager:
    """削除されたエピソードを追跡するシステム"""

    def __init__(self, tombstone_dir: Optional[Path] = None):
        if tombstone_dir is None:
            self.tombstone_dir = get_project_root() / "preserved" / "tombstones"
        else:
            self.tombstone_dir = tombstone_dir
        self.tombstone_dir.mkdir(parents=True, exist_ok=True)
        self.tombstone_file = self.tombstone_dir / "deleted_episodes.json"
        self._load_tombstones()

    def _load_tombstones(self) -> None:
        """Tombstoneデータを読み込み"""
        if self.tombstone_file.exists():
            with open(self.tombstone_file, "r", encoding="utf-8") as f:
                self.tombstones = json.load(f)
        else:
            self.tombstones = {"deleted_episodes": [], "total_deleted": 0}

    def _save_tombstones(self) -> None:
        """Tombstoneデータを保存"""
        with open(self.tombstone_file, "w", encoding="utf-8") as f:
            json.dump(self.tombstones, f, ensure_ascii=False, indent=2)

    def record_deletion(
        self,
        episode_id: str,
        person_name: str,
        reason: str,
        episode_data: dict,
    ) -> None:
        """削除を記録"""
        tombstone = {
            "episode_id": episode_id,
            "person_name": person_name,
            "deletion_timestamp": datetime.now().isoformat(),
            "reason": reason,
            "original_data": episode_data,
            "restorable": True,
        }
        self.tombstones["deleted_episodes"].append(tombstone)
        self.tombstones["total_deleted"] += 1
        self._save_tombstones()
        print(f"  Tombstone: {episode_id} ({person_name}) - {reason}")

    def get_deleted_episodes(self, limit: Optional[int] = None) -> list:
        """削除されたエピソードを取得"""
        episodes = self.tombstones["deleted_episodes"]
        if limit:
            return episodes[-limit:]
        return episodes

    def restore_episode(self, episode_id: str) -> Optional[dict]:
        """削除されたエピソードを復元用に取得"""
        for tombstone in self.tombstones["deleted_episodes"]:
            if tombstone["episode_id"] == episode_id and tombstone["restorable"]:
                return tombstone["original_data"]
        return None


class DataGuardian:
    """データ保管の完全性を保証するシステム"""

    def __init__(self, master_csv: Optional[Path] = None):
        if master_csv is None:
            self.master_csv = get_master_csv_path()
        else:
            self.master_csv = master_csv

        self.backup_manager = BackupManager()
        self.tombstone_manager = TombstoneManager()
        self.checkpoint_dir = get_project_root() / "preserved" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # チェックポイント履歴
        self.checkpoint_history_file = self.checkpoint_dir / "checkpoint_history.json"
        self._load_checkpoint_history()

    def _load_checkpoint_history(self) -> None:
        """チェックポイント履歴を読み込み"""
        if self.checkpoint_history_file.exists():
            with open(self.checkpoint_history_file, "r", encoding="utf-8") as f:
                self.checkpoints = json.load(f)
        else:
            self.checkpoints = []

    def _save_checkpoint_history(self) -> None:
        """チェックポイント履歴を保存"""
        with open(self.checkpoint_history_file, "w", encoding="utf-8") as f:
            json.dump(self.checkpoints, f, ensure_ascii=False, indent=2)

    def _compute_file_hash(self, file_path: Path) -> str:
        """ファイルのSHA256ハッシュを計算"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _count_episodes(self, csv_path: Path) -> int:
        """エピソード数をカウント"""
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            return sum(1 for _ in f) - 1  # ヘッダー行を除く

    def pre_modification_checkpoint(self, description: str = "") -> str:
        """
        変更前のチェックポイント作成

        Returns:
            チェックポイントID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"CP_{timestamp}"

        # バックアップ作成
        backup_path = self.backup_manager.create_backup(self.master_csv)

        # 統計情報取得
        episode_count = self._count_episodes(self.master_csv)
        file_hash = self._compute_file_hash(self.master_csv)

        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "backup_path": str(backup_path),
            "episode_count": episode_count,
            "file_hash": file_hash,
            "status": "created",
        }

        self.checkpoints.append(checkpoint)
        self._save_checkpoint_history()

        print(f"Checkpoint created: {checkpoint_id}")
        print(f"  Episodes: {episode_count:,}")
        print(f"  Backup: {backup_path}")

        return checkpoint_id

    def verify_modification(self, checkpoint_id: str) -> dict:
        """
        変更の妥当性検証

        Returns:
            検証結果の辞書
        """
        # チェックポイントを検索
        checkpoint = None
        for cp in self.checkpoints:
            if cp["checkpoint_id"] == checkpoint_id:
                checkpoint = cp
                break

        if checkpoint is None:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

        # 現在の状態を取得
        current_count = self._count_episodes(self.master_csv)
        current_hash = self._compute_file_hash(self.master_csv)

        # 差分計算
        count_diff = current_count - checkpoint["episode_count"]
        hash_changed = current_hash != checkpoint["file_hash"]

        # 品質評価
        if checkpoint["episode_count"] > 0:
            retention_rate = current_count / checkpoint["episode_count"]
        else:
            retention_rate = 1.0

        result = {
            "checkpoint_id": checkpoint_id,
            "verification_timestamp": datetime.now().isoformat(),
            "before": {
                "episode_count": checkpoint["episode_count"],
                "file_hash": checkpoint["file_hash"][:16] + "...",
            },
            "after": {
                "episode_count": current_count,
                "file_hash": current_hash[:16] + "...",
            },
            "diff": {
                "episode_count_diff": count_diff,
                "hash_changed": hash_changed,
                "retention_rate": retention_rate,
            },
            "status": "ok" if retention_rate >= 0.95 else "warning",
        }

        # チェックポイントのステータス更新
        checkpoint["status"] = "verified"
        checkpoint["verification_result"] = result
        self._save_checkpoint_history()

        print(f"\nVerification: {checkpoint_id}")
        print(f"  Episode diff: {count_diff:+d} ({checkpoint['episode_count']:,} -> {current_count:,})")
        print(f"  Retention rate: {retention_rate:.2%}")
        print(f"  Status: {result['status']}")

        return result

    def rollback_if_needed(
        self,
        checkpoint_id: str,
        threshold: float = 0.95,
    ) -> bool:
        """
        品質低下時の自動ロールバック

        Args:
            checkpoint_id: チェックポイントID
            threshold: ロールバックのしきい値（デフォルト95%）

        Returns:
            ロールバックが実行された場合True
        """
        # 検証実行
        result = self.verify_modification(checkpoint_id)

        if result["diff"]["retention_rate"] < threshold:
            # チェックポイントを検索
            checkpoint = None
            for cp in self.checkpoints:
                if cp["checkpoint_id"] == checkpoint_id:
                    checkpoint = cp
                    break

            if checkpoint:
                backup_path = Path(checkpoint["backup_path"])
                if backup_path.exists():
                    print(f"\nRolling back to {checkpoint_id}...")
                    self.backup_manager.restore_backup(backup_path, self.master_csv)
                    checkpoint["status"] = "rolled_back"
                    self._save_checkpoint_history()
                    print("  Rollback completed")
                    return True

        return False

    def safe_delete_episodes(
        self,
        episode_ids: list[str],
        reason: str,
    ) -> dict:
        """
        安全なエピソード削除（Tombstone付き）

        Args:
            episode_ids: 削除するエピソードIDのリスト
            reason: 削除理由

        Returns:
            削除結果の辞書
        """
        # チェックポイント作成
        checkpoint_id = self.pre_modification_checkpoint(f"Delete {len(episode_ids)} episodes: {reason}")

        # CSVを読み込み
        rows = []
        deleted = []
        with open(self.master_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            for row in reader:
                if row["episode_id"] in episode_ids:
                    # Tombstone記録
                    self.tombstone_manager.record_deletion(
                        episode_id=row["episode_id"],
                        person_name=row.get("person_name", ""),
                        reason=reason,
                        episode_data=row,
                    )
                    deleted.append(row["episode_id"])
                else:
                    rows.append(row)

        # 保存
        with open(self.master_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        # 検証
        result = self.verify_modification(checkpoint_id)

        return {
            "deleted_count": len(deleted),
            "deleted_ids": deleted,
            "checkpoint_id": checkpoint_id,
            "verification": result,
        }

    def get_checkpoint_history(self, limit: Optional[int] = 10) -> list:
        """チェックポイント履歴を取得"""
        if limit:
            return self.checkpoints[-limit:]
        return self.checkpoints

    def get_tombstone_summary(self) -> dict:
        """Tombstoneサマリーを取得"""
        tombstones = self.tombstone_manager.tombstones
        return {
            "total_deleted": tombstones["total_deleted"],
            "restorable_count": sum(1 for t in tombstones["deleted_episodes"] if t.get("restorable", False)),
            "recent_deletions": tombstones["deleted_episodes"][-5:],
        }


def run_guardian_check() -> dict:
    """
    Data Guardianチェックを実行（CI/CD用）

    Returns:
        チェック結果
    """
    guardian = DataGuardian()

    # 現在の状態を確認
    current_count = guardian._count_episodes(guardian.master_csv)
    current_hash = guardian._compute_file_hash(guardian.master_csv)

    # 最新のチェックポイントと比較
    checkpoints = guardian.get_checkpoint_history(limit=1)

    result = {
        "timestamp": datetime.now().isoformat(),
        "current_episode_count": current_count,
        "current_file_hash": current_hash[:16] + "...",
        "status": "ok",
        "tombstone_summary": guardian.get_tombstone_summary(),
    }

    if checkpoints:
        last_cp = checkpoints[-1]
        if last_cp["episode_count"] > 0:
            retention = current_count / last_cp["episode_count"]
            result["retention_from_last_checkpoint"] = retention
            if retention < 0.95:
                result["status"] = "warning"
                result["message"] = f"Episode count dropped by {(1-retention)*100:.1f}%"

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("Data Guardian - Status Check")
    print("=" * 60)

    result = run_guardian_check()

    print(f"\nTimestamp: {result['timestamp']}")
    print(f"Episodes: {result['current_episode_count']:,}")
    print(f"File hash: {result['current_file_hash']}")
    print(f"Status: {result['status']}")

    tombstone = result["tombstone_summary"]
    print("\nTombstones:")
    print(f"  Total deleted: {tombstone['total_deleted']}")
    print(f"  Restorable: {tombstone['restorable_count']}")

    if tombstone["recent_deletions"]:
        print("\nRecent deletions:")
        for t in tombstone["recent_deletions"]:
            print(f"  - {t['episode_id']}: {t['person_name']} ({t['reason']})")
