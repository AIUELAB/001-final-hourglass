#!/usr/bin/env python3
"""
Quarantine Manager - エピソード隔離システム

隔離されたエピソードを管理し、復帰・完全削除を追跡する。

使用方法:
    >>> from scripts.validation.quarantine_manager import QuarantineManager
    >>> qm = QuarantineManager()
    >>> record = qm.quarantine(
    ...     episode_id="EP-123",
    ...     person_name="テスト人物",
    ...     reason="品質違反",
    ...     violation_type="META_REFERENCE",
    ...     super_total_score=500.0,
    ...     episode_data={"episode_id": "EP-123", ...}
    ... )
    >>> qm.release("EP-123", "Manual review passed")
    >>> qm.get_quarantined(status=QuarantineStatus.QUARANTINED)
"""

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.csv_path_resolver import get_project_root


class QuarantineStatus(Enum):
    """隔離ステータス"""

    QUARANTINED = "quarantined"  # 隔離中
    RELEASED = "released"  # 復帰済み
    PURGED = "purged"  # 完全削除済み


@dataclass
class QuarantineRecord:
    """隔離レコード"""

    episode_id: str
    person_name: str
    quarantine_timestamp: str
    reason: str
    violation_type: str
    super_total_score: float
    original_data: dict
    status: QuarantineStatus
    release_timestamp: Optional[str] = None
    release_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuarantineRecord":
        """辞書からインスタンスを生成"""
        # status を Enum に変換
        status_value = data.get("status", "quarantined")
        if isinstance(status_value, str):
            status = QuarantineStatus(status_value)
        else:
            status = status_value

        return cls(
            episode_id=data["episode_id"],
            person_name=data["person_name"],
            quarantine_timestamp=data["quarantine_timestamp"],
            reason=data["reason"],
            violation_type=data["violation_type"],
            super_total_score=float(data.get("super_total_score", 0.0)),
            original_data=data.get("original_data", {}),
            status=status,
            release_timestamp=data.get("release_timestamp"),
            release_reason=data.get("release_reason"),
        )


class QuarantineManager:
    """
    隔離されたエピソードを管理するシステム

    TombstoneManagerと同様のパターンで、隔離・復帰・完全削除を追跡する。
    """

    def __init__(self, quarantine_dir: Optional[Path] = None):
        """
        初期化

        Args:
            quarantine_dir: 隔離データの保存ディレクトリ（デフォルト: preserved/quarantine/）
        """
        if quarantine_dir is None:
            self.quarantine_dir = get_project_root() / "preserved" / "quarantine"
        else:
            self.quarantine_dir = quarantine_dir

        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_file = self.quarantine_dir / "quarantine_episodes.json"

        # 内部データ構造
        self._data: dict[str, Any] = {
            "quarantine_records": [],
            "statistics": {
                "total_quarantined": 0,
                "total_released": 0,
                "total_purged": 0,
            },
        }

        self._load_quarantine()

    def _load_quarantine(self) -> None:
        """隔離データを読み込み"""
        if self.quarantine_file.exists():
            try:
                with open(self.quarantine_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._data = loaded
                        return
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load quarantine data: {e}")

        # フォールバック
        self._data = {
            "quarantine_records": [],
            "statistics": {
                "total_quarantined": 0,
                "total_released": 0,
                "total_purged": 0,
            },
        }

    def _save_quarantine(self) -> None:
        """隔離データを保存"""
        with open(self.quarantine_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _update_statistics(self) -> None:
        """統計情報を再計算"""
        records = self._data.get("quarantine_records", [])

        stats = {
            "total_quarantined": 0,
            "total_released": 0,
            "total_purged": 0,
        }

        for record in records:
            status = record.get("status", "quarantined")
            if status == QuarantineStatus.QUARANTINED.value:
                stats["total_quarantined"] += 1
            elif status == QuarantineStatus.RELEASED.value:
                stats["total_released"] += 1
            elif status == QuarantineStatus.PURGED.value:
                stats["total_purged"] += 1

        self._data["statistics"] = stats

    def quarantine(
        self,
        episode_id: str,
        person_name: str,
        reason: str,
        violation_type: str,
        super_total_score: float,
        episode_data: dict,
    ) -> QuarantineRecord:
        """
        エピソードを隔離に追加

        Args:
            episode_id: エピソードID
            person_name: 人物名
            reason: 隔離理由
            violation_type: 違反タイプ（例: META_REFERENCE, AGE_BOUNDARY）
            super_total_score: 超総合スコア
            episode_data: 元のエピソードデータ

        Returns:
            作成されたQuarantineRecord
        """
        # 既存レコードをチェック
        existing = self.get_record(episode_id)
        if existing and existing.status == QuarantineStatus.QUARANTINED:
            print(f"  Warning: Episode {episode_id} is already quarantined")
            return existing

        record = QuarantineRecord(
            episode_id=episode_id,
            person_name=person_name,
            quarantine_timestamp=datetime.now().isoformat(),
            reason=reason,
            violation_type=violation_type,
            super_total_score=super_total_score,
            original_data=episode_data,
            status=QuarantineStatus.QUARANTINED,
        )

        self._data["quarantine_records"].append(record.to_dict())
        self._update_statistics()
        self._save_quarantine()

        print(f"  Quarantine: {episode_id} ({person_name}) - {reason}")

        return record

    def release(
        self,
        episode_id: str,
        release_reason: str = "Manual review passed",
    ) -> Optional[QuarantineRecord]:
        """
        隔離からの復帰

        Args:
            episode_id: エピソードID
            release_reason: 復帰理由

        Returns:
            更新されたQuarantineRecord（見つからない場合はNone）
        """
        for record_dict in self._data["quarantine_records"]:
            if record_dict["episode_id"] == episode_id:
                if record_dict["status"] != QuarantineStatus.QUARANTINED.value:
                    print(f"  Warning: Episode {episode_id} is not in quarantine status")
                    return QuarantineRecord.from_dict(record_dict)

                record_dict["status"] = QuarantineStatus.RELEASED.value
                record_dict["release_timestamp"] = datetime.now().isoformat()
                record_dict["release_reason"] = release_reason

                self._update_statistics()
                self._save_quarantine()

                print(f"  Released: {episode_id} - {release_reason}")

                return QuarantineRecord.from_dict(record_dict)

        print(f"  Warning: Episode {episode_id} not found in quarantine")
        return None

    def purge(self, episode_id: str) -> bool:
        """
        隔離から完全削除（ステータスをPURGEDに変更）

        Args:
            episode_id: エピソードID

        Returns:
            成功した場合True
        """
        for record_dict in self._data["quarantine_records"]:
            if record_dict["episode_id"] == episode_id:
                if record_dict["status"] == QuarantineStatus.PURGED.value:
                    print(f"  Warning: Episode {episode_id} is already purged")
                    return False

                record_dict["status"] = QuarantineStatus.PURGED.value
                record_dict["release_timestamp"] = datetime.now().isoformat()
                record_dict["release_reason"] = "Permanently deleted"

                self._update_statistics()
                self._save_quarantine()

                print(f"  Purged: {episode_id}")

                return True

        print(f"  Warning: Episode {episode_id} not found in quarantine")
        return False

    def get_quarantined(
        self,
        status: Optional[QuarantineStatus] = None,
        limit: Optional[int] = None,
    ) -> list[QuarantineRecord]:
        """
        隔離リストを取得

        Args:
            status: フィルタするステータス（Noneの場合は全て）
            limit: 取得件数上限

        Returns:
            QuarantineRecordのリスト
        """
        records = self._data.get("quarantine_records", [])

        # ステータスでフィルタ
        if status is not None:
            records = [r for r in records if r.get("status") == status.value]

        # 件数制限
        if limit is not None:
            records = records[-limit:]

        return [QuarantineRecord.from_dict(r) for r in records]

    def get_record(self, episode_id: str) -> Optional[QuarantineRecord]:
        """
        特定のエピソードのレコードを取得

        Args:
            episode_id: エピソードID

        Returns:
            QuarantineRecord（見つからない場合はNone）
        """
        for record_dict in self._data["quarantine_records"]:
            if record_dict["episode_id"] == episode_id:
                return QuarantineRecord.from_dict(record_dict)
        return None

    def generate_report(self) -> dict:
        """
        隔離レポートを生成

        Returns:
            レポート辞書
        """
        records = self._data.get("quarantine_records", [])
        stats = self._data.get("statistics", {})

        # 違反タイプ別集計
        violation_type_counts: dict[str, int] = {}
        for record in records:
            if record.get("status") == QuarantineStatus.QUARANTINED.value:
                vtype = record.get("violation_type", "UNKNOWN")
                violation_type_counts[vtype] = violation_type_counts.get(vtype, 0) + 1

        # 最近の隔離
        quarantined_records = [r for r in records if r.get("status") == QuarantineStatus.QUARANTINED.value]

        return {
            "generated_at": datetime.now().isoformat(),
            "statistics": stats,
            "violation_type_breakdown": violation_type_counts,
            "recent_quarantined": quarantined_records[-10:] if quarantined_records else [],
            "total_records": len(records),
        }

    def get_restorable_data(self, episode_id: str) -> Optional[dict]:
        """
        復元用のオリジナルデータを取得

        Args:
            episode_id: エピソードID

        Returns:
            オリジナルのエピソードデータ（見つからない場合はNone）
        """
        record = self.get_record(episode_id)
        if record and record.status in [
            QuarantineStatus.QUARANTINED,
            QuarantineStatus.RELEASED,
        ]:
            return record.original_data
        return None


def run_quarantine_report() -> None:
    """隔離レポートを表示（CLI用）"""
    qm = QuarantineManager()
    report = qm.generate_report()

    print("=" * 60)
    print("Quarantine Manager - Status Report")
    print("=" * 60)

    print(f"\nGenerated at: {report['generated_at']}")

    stats = report["statistics"]
    print("\nStatistics:")
    print(f"  Total quarantined: {stats.get('total_quarantined', 0)}")
    print(f"  Total released: {stats.get('total_released', 0)}")
    print(f"  Total purged: {stats.get('total_purged', 0)}")

    vtype_breakdown = report.get("violation_type_breakdown", {})
    if vtype_breakdown:
        print("\nViolation Types (quarantined):")
        for vtype, count in sorted(vtype_breakdown.items(), key=lambda x: -x[1]):
            print(f"  {vtype}: {count}")

    recent = report.get("recent_quarantined", [])
    if recent:
        print("\nRecent Quarantined (last 10):")
        for r in recent:
            print(f"  - {r['episode_id']}: {r['person_name']} ({r['violation_type']})")


if __name__ == "__main__":
    run_quarantine_report()
