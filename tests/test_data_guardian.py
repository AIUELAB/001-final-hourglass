#!/usr/bin/env python3
"""
DataGuardian / TombstoneManager / run_guardian_check の包括的テスト

カバレッジ目標: 90%+
テスト対象: src/data_guardian.py (177 stmts)
"""

import csv
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: テスト用CSVファイルを生成
# ---------------------------------------------------------------------------
def _make_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> Path:
    """テスト用CSVを作成して返す"""
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else ["episode_id", "person_name", "content"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _sample_rows(n: int = 5) -> list[dict]:
    return [
        {"episode_id": f"EP-{i:04d}", "person_name": f"Person{i}", "content": f"Content{i}"} for i in range(1, n + 1)
    ]


def _sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


# ============================================================================
# TombstoneManager Tests
# ============================================================================
@pytest.mark.unit
class TestTombstoneManager:
    """TombstoneManager の全メソッドをテスト"""

    def test_init_creates_directory(self, tmp_path):
        """__init__: tombstone_dir を渡すとディレクトリが作成される"""
        tdir = tmp_path / "tombstones"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)
        assert tdir.exists()
        assert mgr.tombstones == {"deleted_episodes": [], "total_deleted": 0}

    def test_init_default_dir(self, tmp_path):
        """__init__: tombstone_dir=None のときデフォルトパスを使用"""
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager()
        expected = tmp_path / "preserved" / "tombstones"
        assert mgr.tombstone_dir == expected
        assert expected.exists()

    def test_load_tombstones_existing_file(self, tmp_path):
        """_load_tombstones: 正常な既存JSONファイルを読み込む"""
        tdir = tmp_path / "ts"
        tdir.mkdir()
        data = {"deleted_episodes": [{"episode_id": "EP-0001"}], "total_deleted": 1}
        (tdir / "deleted_episodes.json").write_text(json.dumps(data), encoding="utf-8")

        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)
        assert mgr.tombstones == data

    def test_load_tombstones_no_file(self, tmp_path):
        """_load_tombstones: ファイルが存在しない場合はデフォルト値"""
        tdir = tmp_path / "ts_empty"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)
        assert mgr.tombstones == {"deleted_episodes": [], "total_deleted": 0}

    def test_load_tombstones_non_dict_fallback(self, tmp_path):
        """_load_tombstones: JSONがdictでない場合はフォールバック"""
        tdir = tmp_path / "ts_bad"
        tdir.mkdir()
        (tdir / "deleted_episodes.json").write_text("[1,2,3]", encoding="utf-8")

        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)
        assert mgr.tombstones == {"deleted_episodes": [], "total_deleted": 0}

    def test_save_tombstones(self, tmp_path):
        """_save_tombstones: JSONファイルに書き込まれる"""
        tdir = tmp_path / "ts_save"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)
        mgr.tombstones["total_deleted"] = 42
        mgr._save_tombstones()

        saved = json.loads((tdir / "deleted_episodes.json").read_text(encoding="utf-8"))
        assert saved["total_deleted"] == 42

    def test_record_deletion(self, tmp_path):
        """record_deletion: tombstone を追加し total_deleted を増加"""
        tdir = tmp_path / "ts_rec"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)

        mgr.record_deletion("EP-0001", "Taro", "test reason", {"episode_id": "EP-0001"})
        assert mgr.tombstones["total_deleted"] == 1
        assert len(mgr.tombstones["deleted_episodes"]) == 1
        ts = mgr.tombstones["deleted_episodes"][0]
        assert ts["episode_id"] == "EP-0001"
        assert ts["person_name"] == "Taro"
        assert ts["reason"] == "test reason"
        assert ts["restorable"] is True

    def test_get_deleted_episodes_no_limit(self, tmp_path):
        """get_deleted_episodes: limit=None で全件返却"""
        tdir = tmp_path / "ts_get"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)

        for i in range(3):
            mgr.record_deletion(f"EP-{i}", f"P{i}", "r", {})

        result = mgr.get_deleted_episodes()
        assert len(result) == 3

    def test_get_deleted_episodes_with_limit(self, tmp_path):
        """get_deleted_episodes: limit=2 で末尾2件返却"""
        tdir = tmp_path / "ts_lim"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)

        for i in range(5):
            mgr.record_deletion(f"EP-{i}", f"P{i}", "r", {})

        result = mgr.get_deleted_episodes(limit=2)
        assert len(result) == 2
        assert result[0]["episode_id"] == "EP-3"
        assert result[1]["episode_id"] == "EP-4"

    def test_get_deleted_episodes_non_list(self, tmp_path):
        """get_deleted_episodes: deleted_episodes が list でない場合は空リスト"""
        tdir = tmp_path / "ts_nonlist"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)

        mgr.tombstones["deleted_episodes"] = "not a list"
        result = mgr.get_deleted_episodes()
        assert result == []

    def test_restore_episode_found(self, tmp_path):
        """restore_episode: restorable=True のエピソードを復元"""
        tdir = tmp_path / "ts_restore"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)

        original = {"episode_id": "EP-0001", "content": "Hello"}
        mgr.record_deletion("EP-0001", "Taro", "test", original)

        restored = mgr.restore_episode("EP-0001")
        assert restored == original

    def test_restore_episode_not_restorable(self, tmp_path):
        """restore_episode: restorable=False の場合は None"""
        tdir = tmp_path / "ts_nores"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)

        mgr.record_deletion("EP-0001", "Taro", "test", {"a": 1})
        mgr.tombstones["deleted_episodes"][0]["restorable"] = False

        assert mgr.restore_episode("EP-0001") is None

    def test_restore_episode_not_found(self, tmp_path):
        """restore_episode: 存在しないIDは None"""
        tdir = tmp_path / "ts_nf"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)

        assert mgr.restore_episode("NONEXIST") is None

    def test_restore_episode_non_dict_original_data(self, tmp_path):
        """restore_episode: original_data が dict でない場合は None"""
        tdir = tmp_path / "ts_nond"
        with patch("src.data_guardian.get_project_root", return_value=tmp_path):
            from src.data_guardian import TombstoneManager

            mgr = TombstoneManager(tombstone_dir=tdir)

        # record_deletion は dict を受け取るが、内部データを直接操作してテスト
        mgr.tombstones["deleted_episodes"].append(
            {"episode_id": "EP-X", "restorable": True, "original_data": "not a dict"}
        )
        assert mgr.restore_episode("EP-X") is None


# ============================================================================
# DataGuardian Tests
# ============================================================================
@pytest.mark.unit
class TestDataGuardian:
    """DataGuardian の全メソッドをテスト"""

    def _make_guardian(self, tmp_path, rows=None):
        """テスト用 DataGuardian を構築するヘルパー"""
        if rows is None:
            rows = _sample_rows(5)

        csv_path = tmp_path / "master.csv"
        _make_csv(csv_path, rows)

        backup_dir = tmp_path / "backups"
        backup_dir.mkdir(exist_ok=True)
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)
        tombstone_dir = tmp_path / "tombstones"
        tombstone_dir.mkdir(exist_ok=True)

        mock_backup = MagicMock()
        # create_backup: CSVをバックアップディレクトリにコピーして返す
        backup_file = backup_dir / "backup.csv"

        def fake_create_backup(path):
            import shutil

            shutil.copy2(path, backup_file)
            return backup_file

        mock_backup.create_backup.side_effect = fake_create_backup
        mock_backup.restore_backup.side_effect = lambda src, dst: __import__("shutil").copy2(src, dst)

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager", return_value=mock_backup),
            patch("src.data_guardian.TombstoneManager") as MockTombstone,
        ):
            # TombstoneManager のモックをセットアップ
            from src.data_guardian import TombstoneManager as RealTM

            real_tm = RealTM(tombstone_dir=tombstone_dir)
            MockTombstone.return_value = real_tm

            from src.data_guardian import DataGuardian

            guardian = DataGuardian(master_csv=csv_path)

        # BackupManager を差し替え
        guardian.backup_manager = mock_backup
        guardian.checkpoint_dir = checkpoint_dir
        guardian.checkpoint_history_file = checkpoint_dir / "checkpoint_history.json"

        return guardian

    # --- __init__ ---
    def test_init_with_master_csv(self, tmp_path):
        """__init__: master_csv を明示指定"""
        csv_path = tmp_path / "test.csv"
        _make_csv(csv_path, _sample_rows(2))

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager"),
            patch("src.data_guardian.TombstoneManager"),
        ):
            from src.data_guardian import DataGuardian

            g = DataGuardian(master_csv=csv_path)
        assert g.master_csv == csv_path

    def test_init_default_master_csv(self, tmp_path):
        """__init__: master_csv=None でデフォルトパスを使用"""
        csv_path = tmp_path / "default.csv"
        _make_csv(csv_path, _sample_rows(1))

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager"),
            patch("src.data_guardian.TombstoneManager"),
        ):
            from src.data_guardian import DataGuardian

            g = DataGuardian()
        assert g.master_csv == csv_path

    # --- _load_checkpoint_history ---
    def test_load_checkpoint_history_existing(self, tmp_path):
        """_load_checkpoint_history: 既存JSONから読み込み"""
        csv_path = tmp_path / "m.csv"
        _make_csv(csv_path, _sample_rows(1))
        cp_dir = tmp_path / "preserved" / "checkpoints"
        cp_dir.mkdir(parents=True)
        cp_file = cp_dir / "checkpoint_history.json"
        cp_data = [{"checkpoint_id": "CP_001", "episode_count": 10}]
        cp_file.write_text(json.dumps(cp_data), encoding="utf-8")

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager"),
            patch("src.data_guardian.TombstoneManager"),
        ):
            from src.data_guardian import DataGuardian

            g = DataGuardian(master_csv=csv_path)
        assert len(g.checkpoints) == 1
        assert g.checkpoints[0]["checkpoint_id"] == "CP_001"

    def test_load_checkpoint_history_non_list(self, tmp_path):
        """_load_checkpoint_history: JSONが list でない場合はフォールバック"""
        csv_path = tmp_path / "m.csv"
        _make_csv(csv_path, _sample_rows(1))
        cp_dir = tmp_path / "preserved" / "checkpoints"
        cp_dir.mkdir(parents=True)
        (cp_dir / "checkpoint_history.json").write_text('{"not": "a list"}', encoding="utf-8")

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager"),
            patch("src.data_guardian.TombstoneManager"),
        ):
            from src.data_guardian import DataGuardian

            g = DataGuardian(master_csv=csv_path)
        assert g.checkpoints == []

    def test_load_checkpoint_history_filters_non_dicts(self, tmp_path):
        """_load_checkpoint_history: list 内の非dict要素をフィルタ"""
        csv_path = tmp_path / "m.csv"
        _make_csv(csv_path, _sample_rows(1))
        cp_dir = tmp_path / "preserved" / "checkpoints"
        cp_dir.mkdir(parents=True)
        cp_data = [{"checkpoint_id": "CP_001"}, "bad_entry", 42, {"checkpoint_id": "CP_002"}]
        (cp_dir / "checkpoint_history.json").write_text(json.dumps(cp_data), encoding="utf-8")

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager"),
            patch("src.data_guardian.TombstoneManager"),
        ):
            from src.data_guardian import DataGuardian

            g = DataGuardian(master_csv=csv_path)
        assert len(g.checkpoints) == 2

    def test_load_checkpoint_history_no_file(self, tmp_path):
        """_load_checkpoint_history: ファイル不在でフォールバック"""
        csv_path = tmp_path / "m.csv"
        _make_csv(csv_path, _sample_rows(1))

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager"),
            patch("src.data_guardian.TombstoneManager"),
        ):
            from src.data_guardian import DataGuardian

            g = DataGuardian(master_csv=csv_path)
        assert g.checkpoints == []

    # --- _save_checkpoint_history ---
    def test_save_checkpoint_history(self, tmp_path):
        """_save_checkpoint_history: JSONファイルに書き込み"""
        guardian = self._make_guardian(tmp_path)
        guardian.checkpoints = [{"checkpoint_id": "CP_TEST"}]
        guardian._save_checkpoint_history()

        saved = json.loads(guardian.checkpoint_history_file.read_text(encoding="utf-8"))
        assert saved == [{"checkpoint_id": "CP_TEST"}]

    # --- _compute_file_hash ---
    def test_compute_file_hash(self, tmp_path):
        """_compute_file_hash: SHA256 が正しく計算される"""
        guardian = self._make_guardian(tmp_path)
        expected = _sha256(guardian.master_csv)
        assert guardian._compute_file_hash(guardian.master_csv) == expected

    # --- _count_episodes ---
    def test_count_episodes(self, tmp_path):
        """_count_episodes: ヘッダーを除いた行数を返す"""
        guardian = self._make_guardian(tmp_path, rows=_sample_rows(7))
        assert guardian._count_episodes(guardian.master_csv) == 7

    def test_count_episodes_empty_csv(self, tmp_path):
        """_count_episodes: データ行0件のCSVでは0を返す（ヘッダーのみ）"""
        guardian = self._make_guardian(tmp_path, rows=[])
        # ヘッダー行1行 - 1 = 0
        assert guardian._count_episodes(guardian.master_csv) == 0

    # --- pre_modification_checkpoint ---
    def test_pre_modification_checkpoint(self, tmp_path):
        """pre_modification_checkpoint: バックアップ作成・統計記録・ID返却"""
        guardian = self._make_guardian(tmp_path)
        cp_id = guardian.pre_modification_checkpoint("test checkpoint")

        assert cp_id.startswith("CP_")
        assert len(guardian.checkpoints) == 1
        cp = guardian.checkpoints[0]
        assert cp["description"] == "test checkpoint"
        assert cp["episode_count"] == 5
        assert cp["status"] == "created"
        assert "backup_path" in cp
        guardian.backup_manager.create_backup.assert_called_once()

    # --- verify_modification ---
    def test_verify_modification_found_ok(self, tmp_path):
        """verify_modification: 保持率95%以上で status=ok"""
        guardian = self._make_guardian(tmp_path, rows=_sample_rows(10))
        cp_id = guardian.pre_modification_checkpoint()

        # 1行削除して9行に (retention=90% -> warning, 10行のまま -> ok)
        result = guardian.verify_modification(cp_id)
        assert result["status"] == "ok"
        assert result["diff"]["retention_rate"] == 1.0

    def test_verify_modification_warning(self, tmp_path):
        """verify_modification: 保持率95%未満で status=warning"""
        guardian = self._make_guardian(tmp_path, rows=_sample_rows(10))
        cp_id = guardian.pre_modification_checkpoint()

        # CSVを書き換えて行数を減らす
        _make_csv(guardian.master_csv, _sample_rows(5))

        result = guardian.verify_modification(cp_id)
        assert result["status"] == "warning"
        assert result["diff"]["retention_rate"] == 0.5

    def test_verify_modification_not_found(self, tmp_path):
        """verify_modification: 存在しないチェックポイントIDでValueError"""
        guardian = self._make_guardian(tmp_path)
        with pytest.raises(ValueError, match="Checkpoint not found"):
            guardian.verify_modification("CP_NONEXIST")

    def test_verify_modification_zero_episode_count(self, tmp_path):
        """verify_modification: 元のエピソード数が0の場合 retention_rate=1.0"""
        guardian = self._make_guardian(tmp_path, rows=[])
        cp_id = guardian.pre_modification_checkpoint()

        result = guardian.verify_modification(cp_id)
        assert result["diff"]["retention_rate"] == 1.0

    # --- rollback_if_needed ---
    def test_rollback_below_threshold(self, tmp_path):
        """rollback_if_needed: 保持率がしきい値未満でロールバック実行"""
        guardian = self._make_guardian(tmp_path, rows=_sample_rows(10))
        cp_id = guardian.pre_modification_checkpoint()

        # CSVを大幅に縮小
        _make_csv(guardian.master_csv, _sample_rows(2))

        rolled_back = guardian.rollback_if_needed(cp_id, threshold=0.95)
        assert rolled_back is True
        guardian.backup_manager.restore_backup.assert_called_once()

        # ステータスが rolled_back に更新されている
        cp = next(c for c in guardian.checkpoints if c["checkpoint_id"] == cp_id)
        assert cp["status"] == "rolled_back"

    def test_rollback_above_threshold(self, tmp_path):
        """rollback_if_needed: 保持率がしきい値以上ならロールバックしない"""
        guardian = self._make_guardian(tmp_path, rows=_sample_rows(10))
        cp_id = guardian.pre_modification_checkpoint()

        # CSVを変更しない
        rolled_back = guardian.rollback_if_needed(cp_id, threshold=0.95)
        assert rolled_back is False
        guardian.backup_manager.restore_backup.assert_not_called()

    def test_rollback_backup_missing(self, tmp_path):
        """rollback_if_needed: バックアップファイルが存在しない場合はFalse"""
        guardian = self._make_guardian(tmp_path, rows=_sample_rows(10))
        cp_id = guardian.pre_modification_checkpoint()

        # CSVを縮小
        _make_csv(guardian.master_csv, _sample_rows(1))

        # バックアップファイルを削除
        backup_path = Path(guardian.checkpoints[0]["backup_path"])
        if backup_path.exists():
            backup_path.unlink()

        rolled_back = guardian.rollback_if_needed(cp_id, threshold=0.95)
        assert rolled_back is False

    # --- safe_delete_episodes ---
    def test_safe_delete_episodes(self, tmp_path):
        """safe_delete_episodes: 指定IDのエピソードを削除しtombstone記録"""
        guardian = self._make_guardian(tmp_path, rows=_sample_rows(5))

        result = guardian.safe_delete_episodes(["EP-0002", "EP-0004"], "test deletion")

        assert result["deleted_count"] == 2
        assert "EP-0002" in result["deleted_ids"]
        assert "EP-0004" in result["deleted_ids"]
        assert "checkpoint_id" in result
        assert "verification" in result

        # CSVから削除されていることを確認
        with open(guardian.master_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            remaining_ids = [row["episode_id"] for row in reader]
        assert "EP-0002" not in remaining_ids
        assert "EP-0004" not in remaining_ids
        assert len(remaining_ids) == 3

    def test_safe_delete_episodes_empty_fieldnames(self, tmp_path):
        """safe_delete_episodes: ヘッダーがないCSVでValueError"""
        guardian = self._make_guardian(tmp_path)

        # 空ファイルを作成（ヘッダーなし）
        guardian.master_csv.write_text("", encoding="utf-8-sig")

        # pre_modification_checkpoint 内で _count_episodes が呼ばれるため
        # 空ファイルでは -1 行になるが、その後 safe_delete で fieldnames=None エラー
        # ここでは明示的に空CSVの場合をテスト
        with pytest.raises(Exception):
            guardian.safe_delete_episodes(["EP-0001"], "test")

    # --- get_checkpoint_history ---
    def test_get_checkpoint_history_with_limit(self, tmp_path):
        """get_checkpoint_history: limit で末尾N件を返す"""
        guardian = self._make_guardian(tmp_path)
        guardian.checkpoints = [{"id": i} for i in range(20)]

        result = guardian.get_checkpoint_history(limit=5)
        assert len(result) == 5
        assert result[0]["id"] == 15

    def test_get_checkpoint_history_no_limit(self, tmp_path):
        """get_checkpoint_history: limit=None で全件返す"""
        guardian = self._make_guardian(tmp_path)
        guardian.checkpoints = [{"id": i} for i in range(20)]

        result = guardian.get_checkpoint_history(limit=None)
        assert len(result) == 20

    def test_get_checkpoint_history_default_limit(self, tmp_path):
        """get_checkpoint_history: デフォルトlimit=10"""
        guardian = self._make_guardian(tmp_path)
        guardian.checkpoints = [{"id": i} for i in range(20)]

        result = guardian.get_checkpoint_history()
        assert len(result) == 10

    # --- get_tombstone_summary ---
    def test_get_tombstone_summary(self, tmp_path):
        """get_tombstone_summary: 正しい集計を返す"""
        guardian = self._make_guardian(tmp_path)

        # tombstone に直接データを設定
        guardian.tombstone_manager.tombstones = {
            "total_deleted": 3,
            "deleted_episodes": [
                {"episode_id": "EP-1", "restorable": True, "person_name": "A", "reason": "r"},
                {"episode_id": "EP-2", "restorable": False, "person_name": "B", "reason": "r"},
                {"episode_id": "EP-3", "restorable": True, "person_name": "C", "reason": "r"},
            ],
        }

        summary = guardian.get_tombstone_summary()
        assert summary["total_deleted"] == 3
        assert summary["restorable_count"] == 2
        assert len(summary["recent_deletions"]) == 3


# ============================================================================
# run_guardian_check Tests
# ============================================================================
@pytest.mark.unit
class TestRunGuardianCheck:
    """run_guardian_check 関数のテスト"""

    def test_no_checkpoints(self, tmp_path):
        """チェックポイントが存在しない場合: status=ok"""
        csv_path = tmp_path / "master.csv"
        _make_csv(csv_path, _sample_rows(10))

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager"),
            patch("src.data_guardian.TombstoneManager") as MockTM,
        ):
            MockTM.return_value.tombstones = {"total_deleted": 0, "deleted_episodes": []}

            from src.data_guardian import run_guardian_check

            result = run_guardian_check()

        assert result["status"] == "ok"
        assert result["current_episode_count"] == 10
        assert "retention_from_last_checkpoint" not in result

    def test_with_checkpoints_ok(self, tmp_path):
        """チェックポイントあり・保持率OK: status=ok"""
        csv_path = tmp_path / "master.csv"
        _make_csv(csv_path, _sample_rows(10))

        cp_dir = tmp_path / "preserved" / "checkpoints"
        cp_dir.mkdir(parents=True)
        cp_data = [{"checkpoint_id": "CP_001", "episode_count": 10}]
        (cp_dir / "checkpoint_history.json").write_text(json.dumps(cp_data), encoding="utf-8")

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager"),
            patch("src.data_guardian.TombstoneManager") as MockTM,
        ):
            MockTM.return_value.tombstones = {"total_deleted": 0, "deleted_episodes": []}

            from src.data_guardian import run_guardian_check

            result = run_guardian_check()

        assert result["status"] == "ok"
        assert result["retention_from_last_checkpoint"] == 1.0

    def test_with_checkpoints_warning(self, tmp_path):
        """チェックポイントあり・保持率低下: status=warning"""
        csv_path = tmp_path / "master.csv"
        _make_csv(csv_path, _sample_rows(5))

        cp_dir = tmp_path / "preserved" / "checkpoints"
        cp_dir.mkdir(parents=True)
        # 前回は100件あったことにする
        cp_data = [{"checkpoint_id": "CP_001", "episode_count": 100}]
        (cp_dir / "checkpoint_history.json").write_text(json.dumps(cp_data), encoding="utf-8")

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager"),
            patch("src.data_guardian.TombstoneManager") as MockTM,
        ):
            MockTM.return_value.tombstones = {"total_deleted": 0, "deleted_episodes": []}

            from src.data_guardian import run_guardian_check

            result = run_guardian_check()

        assert result["status"] == "warning"
        assert "message" in result
        assert result["retention_from_last_checkpoint"] == 0.05

    def test_with_zero_episode_checkpoint(self, tmp_path):
        """チェックポイントの episode_count=0 の場合: retention 計算をスキップ"""
        csv_path = tmp_path / "master.csv"
        _make_csv(csv_path, _sample_rows(5))

        cp_dir = tmp_path / "preserved" / "checkpoints"
        cp_dir.mkdir(parents=True)
        cp_data = [{"checkpoint_id": "CP_001", "episode_count": 0}]
        (cp_dir / "checkpoint_history.json").write_text(json.dumps(cp_data), encoding="utf-8")

        with (
            patch("src.data_guardian.get_master_csv_path", return_value=csv_path),
            patch("src.data_guardian.get_project_root", return_value=tmp_path),
            patch("src.data_guardian.BackupManager"),
            patch("src.data_guardian.TombstoneManager") as MockTM,
        ):
            MockTM.return_value.tombstones = {"total_deleted": 0, "deleted_episodes": []}

            from src.data_guardian import run_guardian_check

            result = run_guardian_check()

        # episode_count=0 なので retention 計算に入らない
        assert result["status"] == "ok"
        assert "retention_from_last_checkpoint" not in result
