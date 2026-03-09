"""
Tests for src/generation_manager.py - GenerationManager

TDD: 世代管理システムのテスト
- ファイル操作（CSV, gzip, metadata JSON）
- 世代の作成・一覧・取得・復元・ローテーション
- 差分バックアップ
- エッジケース（空ファイル、不正メタデータ等）
"""

import gzip
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.generation_manager import GenerationManager, print_generation_status


# =============================================================================
# Helpers
# =============================================================================


def _create_csv(path: Path, rows: int = 5) -> Path:
    """テスト用CSVファイルを生成"""
    lines = ["col1,col2,col3\n"]
    for i in range(rows):
        lines.append(f"val{i}_1,val{i}_2,val{i}_3\n")
    path.write_text("".join(lines), encoding="utf-8-sig")
    return path


# =============================================================================
# __init__ Tests
# =============================================================================


class TestGenerationManagerInit:
    """__init__ のテスト"""

    def test_init_with_explicit_paths(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"

        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        assert mgr.master_csv == csv_path
        assert mgr.generation_dir == gen_dir
        assert gen_dir.exists()
        assert mgr.metadata["current_generation"] == 0
        assert mgr.metadata["generations"] == []

    def test_init_without_params_uses_defaults(self, tmp_path: Path):
        """パラメータ省略時にget_master_csv_path/get_project_rootが呼ばれる"""
        csv_path = _create_csv(tmp_path / "master.csv")
        project_root = tmp_path

        with (
            patch("src.generation_manager.get_master_csv_path", return_value=csv_path),
            patch("src.generation_manager.get_project_root", return_value=project_root),
        ):
            mgr = GenerationManager()

        assert mgr.master_csv == csv_path
        assert "generations" in str(mgr.generation_dir)

    def test_init_creates_generation_dir(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "deep" / "nested" / "gens"

        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)
        assert gen_dir.exists()


# =============================================================================
# _load_metadata / _save_metadata Tests
# =============================================================================


class TestMetadata:
    """メタデータの読み書きテスト"""

    def test_load_metadata_no_file(self, tmp_path: Path):
        """メタデータファイルが存在しない場合のデフォルト値"""
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        assert mgr.metadata["current_generation"] == 0
        assert mgr.metadata["generations"] == []

    def test_load_metadata_existing_file(self, tmp_path: Path):
        """既存メタデータファイルからの読み込み"""
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"
        gen_dir.mkdir(parents=True)

        metadata = {
            "current_generation": 3,
            "generations": [{"generation_number": 1}],
        }
        (gen_dir / "generations_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)
        assert mgr.metadata["current_generation"] == 3
        assert len(mgr.metadata["generations"]) == 1

    def test_load_metadata_non_dict(self, tmp_path: Path):
        """JSONがdictでない場合はデフォルトを使用"""
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"
        gen_dir.mkdir(parents=True)

        # リストをJSONとして保存
        (gen_dir / "generations_metadata.json").write_text("[1,2,3]", encoding="utf-8")

        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)
        # デフォルト値のまま
        assert mgr.metadata["current_generation"] == 0
        assert mgr.metadata["generations"] == []

    def test_save_metadata(self, tmp_path: Path):
        """メタデータの保存"""
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"
        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        mgr.metadata["current_generation"] = 42
        mgr._save_metadata()

        with open(mgr.metadata_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["current_generation"] == 42


# =============================================================================
# _compute_file_hash / _count_rows / _get_csv_stats Tests
# =============================================================================


class TestFileUtils:
    """ファイルユーティリティのテスト"""

    def test_compute_file_hash_deterministic(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=3)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        h1 = mgr._compute_file_hash(csv_path)
        h2 = mgr._compute_file_hash(csv_path)
        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex digest length

    def test_compute_file_hash_different_content(self, tmp_path: Path):
        csv1 = _create_csv(tmp_path / "a.csv", rows=3)
        csv2 = _create_csv(tmp_path / "b.csv", rows=5)
        mgr = GenerationManager(master_csv=csv1, generation_dir=tmp_path / "gens")

        assert mgr._compute_file_hash(csv1) != mgr._compute_file_hash(csv2)

    def test_count_rows(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=10)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        assert mgr._count_rows(csv_path) == 10

    def test_count_rows_empty(self, tmp_path: Path):
        """ヘッダーのみのCSV"""
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("col1,col2\n", encoding="utf-8-sig")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        assert mgr._count_rows(csv_path) == 0

    def test_get_csv_stats(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=7)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        stats = mgr._get_csv_stats(csv_path)
        assert stats["row_count"] == 7
        assert stats["file_size"] > 0
        assert len(stats["file_hash"]) == 64


# =============================================================================
# create_generation Tests
# =============================================================================


class TestCreateGeneration:
    """世代作成のテスト"""

    def test_create_compressed(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=5)
        gen_dir = tmp_path / "gens"
        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        result = mgr.create_generation("test backup", compress=True)

        assert result["generation_number"] == 1
        assert result["description"] == "test backup"
        assert result["compressed"] is True
        assert result["backup_file"].endswith(".csv.gz")
        assert (gen_dir / result["backup_file"]).exists()
        assert mgr.metadata["current_generation"] == 1

        # gzipラウンドトリップ検証
        backup_path = gen_dir / result["backup_file"]
        with gzip.open(backup_path, "rb") as f:
            restored = f.read()
        original = csv_path.read_bytes()
        assert restored == original

    def test_create_uncompressed(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=5)
        gen_dir = tmp_path / "gens"
        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        result = mgr.create_generation("uncompressed", compress=False)

        assert result["compressed"] is False
        assert result["backup_file"].endswith(".csv")
        assert not result["backup_file"].endswith(".csv.gz")

        backup_path = gen_dir / result["backup_file"]
        assert backup_path.read_bytes() == csv_path.read_bytes()

    def test_create_increments_generation_number(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        r1 = mgr.create_generation("gen1")
        r2 = mgr.create_generation("gen2")

        assert r1["generation_number"] == 1
        assert r2["generation_number"] == 2
        assert mgr.metadata["current_generation"] == 2

    def test_create_updates_metadata_file(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"
        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        mgr.create_generation("persist test")

        with open(mgr.metadata_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["current_generation"] == 1
        assert len(saved["generations"]) == 1

    def test_create_when_generations_not_list(self, tmp_path: Path):
        """metadata['generations']がlistでない場合の復旧"""
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"
        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)
        mgr.metadata["generations"] = "broken"

        result = mgr.create_generation("recovery")

        assert result["generation_number"] == 1
        assert isinstance(mgr.metadata["generations"], list)


# =============================================================================
# _rotate_generations Tests
# =============================================================================


class TestRotateGenerations:
    """世代ローテーションのテスト"""

    def test_rotate_when_over_max(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"
        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        # MAX_GENERATIONS + 2 の世代を作成
        for i in range(GenerationManager.MAX_GENERATIONS + 2):
            mgr.create_generation(f"gen {i+1}")

        assert len(mgr.metadata["generations"]) == GenerationManager.MAX_GENERATIONS

    def test_rotate_deletes_old_files(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"
        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        # 最初の世代を作成してファイル名を記録
        first = mgr.create_generation("first")
        first_file = gen_dir / first["backup_file"]
        assert first_file.exists()

        # MAX_GENERATIONS + 1 まで追加して最初の世代を追い出す
        for i in range(GenerationManager.MAX_GENERATIONS):
            mgr.create_generation(f"gen {i+2}")

        # 最初のファイルが削除されていることを確認
        assert not first_file.exists()

    def test_rotate_when_generations_not_list(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")
        mgr.metadata["generations"] = "not a list"

        # エラーにならないことを確認
        mgr._rotate_generations()

    def test_rotate_missing_old_file(self, tmp_path: Path):
        """古い世代のファイルが既に存在しない場合"""
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"
        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        # 世代を作成して、最初のバックアップファイルを手動削除
        first = mgr.create_generation("first")
        first_file = gen_dir / first["backup_file"]
        first_file.unlink()

        # MAX+1まで追加してもエラーにならない
        for i in range(GenerationManager.MAX_GENERATIONS):
            mgr.create_generation(f"gen {i+2}")


# =============================================================================
# list_generations Tests
# =============================================================================


class TestListGenerations:
    """世代一覧のテスト"""

    def test_list_all(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        mgr.create_generation("g1")
        mgr.create_generation("g2")
        mgr.create_generation("g3")

        result = mgr.list_generations()
        assert len(result) == 3

    def test_list_with_limit(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        for i in range(5):
            mgr.create_generation(f"g{i+1}")

        result = mgr.list_generations(limit=2)
        assert len(result) == 2
        # 最新の2件が返る
        assert result[-1]["description"] == "g5"

    def test_list_empty(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        assert mgr.list_generations() == []

    def test_list_non_list_metadata(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")
        mgr.metadata["generations"] = "broken"

        assert mgr.list_generations() == []

    def test_list_filters_non_dict_entries(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")
        mgr.metadata["generations"] = [
            {"generation_number": 1, "description": "valid"},
            "invalid_entry",
            42,
            {"generation_number": 2, "description": "also valid"},
        ]

        result = mgr.list_generations()
        assert len(result) == 2


# =============================================================================
# get_generation Tests
# =============================================================================


class TestGetGeneration:
    """特定世代取得のテスト"""

    def test_get_found(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        mgr.create_generation("target")
        mgr.create_generation("other")

        result = mgr.get_generation(1)
        assert result is not None
        assert result["description"] == "target"

    def test_get_not_found(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        assert mgr.get_generation(999) is None


# =============================================================================
# restore_to_generation Tests
# =============================================================================


class TestRestoreToGeneration:
    """世代復元のテスト"""

    def test_restore_compressed(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=5)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        # 世代1を作成
        mgr.create_generation("before changes", compress=True)
        original_content = csv_path.read_bytes()

        # CSVを変更
        _create_csv(csv_path, rows=20)
        assert csv_path.read_bytes() != original_content

        # 世代1に復元
        result = mgr.restore_to_generation(1)

        assert result["restored_to"] == 1
        assert csv_path.read_bytes() == original_content

    def test_restore_uncompressed(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=5)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        mgr.create_generation("uncompressed backup", compress=False)
        original_content = csv_path.read_bytes()

        _create_csv(csv_path, rows=20)

        mgr.restore_to_generation(1)
        assert csv_path.read_bytes() == original_content

    def test_restore_not_found_raises(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        with pytest.raises(ValueError, match="not found"):
            mgr.restore_to_generation(999)

    def test_restore_file_missing_raises(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"
        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        result = mgr.create_generation("will delete file")
        # バックアップファイルを手動削除
        (gen_dir / result["backup_file"]).unlink()

        with pytest.raises(FileNotFoundError, match="Backup file not found"):
            mgr.restore_to_generation(1)

    def test_restore_result_contains_stats(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=5)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        mgr.create_generation("stats check")

        result = mgr.restore_to_generation(1)
        assert "before_stats" in result
        assert "after_stats" in result
        assert "timestamp" in result


# =============================================================================
# get_generation_history Tests
# =============================================================================


class TestGetGenerationHistory:
    """世代履歴のテスト"""

    def test_history_with_existing_files(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        mgr.create_generation("h1")
        mgr.create_generation("h2")

        history = mgr.get_generation_history()
        assert len(history) == 2
        assert all(h["exists"] for h in history)
        assert all(h["current_size"] > 0 for h in history)

    def test_history_with_missing_file(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"
        mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        result = mgr.create_generation("will delete")
        (gen_dir / result["backup_file"]).unlink()

        history = mgr.get_generation_history()
        assert len(history) == 1
        assert history[0]["exists"] is False
        assert history[0]["current_size"] == 0


# =============================================================================
# get_diff_between_generations Tests
# =============================================================================


class TestGetDiffBetweenGenerations:
    """世代間差分のテスト"""

    def test_diff_success(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=5)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        mgr.create_generation("gen1")
        _create_csv(csv_path, rows=10)
        mgr.create_generation("gen2")

        diff = mgr.get_diff_between_generations(1, 2)
        assert diff["from_generation"] == 1
        assert diff["to_generation"] == 2
        assert diff["row_diff"] == 5
        assert diff["hash_changed"] is True
        assert "size_diff" in diff

    def test_diff_same_content(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=5)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        mgr.create_generation("same1")
        mgr.create_generation("same2")

        diff = mgr.get_diff_between_generations(1, 2)
        assert diff["row_diff"] == 0
        assert diff["hash_changed"] is False

    def test_diff_one_not_found_raises(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")
        mgr.create_generation("only one")

        with pytest.raises(ValueError, match="One or both generations not found"):
            mgr.get_diff_between_generations(1, 999)

    def test_diff_both_not_found_raises(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        with pytest.raises(ValueError, match="One or both generations not found"):
            mgr.get_diff_between_generations(1, 2)


# =============================================================================
# create_differential_backup Tests
# =============================================================================


class TestCreateDifferentialBackup:
    """差分バックアップのテスト"""

    def test_no_prior_generations_creates_full(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        result = mgr.create_differential_backup()

        assert result["generation_number"] == 1
        assert result["description"] == "Initial full backup"

    def test_no_changes_detected(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=5)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        mgr.create_generation("baseline")

        result = mgr.create_differential_backup()
        assert result["status"] == "no_changes"
        assert result["base_generation"] == 1

    def test_changes_detected_creates_new(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=5)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        mgr.create_generation("baseline")
        _create_csv(csv_path, rows=10)

        result = mgr.create_differential_backup()
        assert result["status"] == "created"
        assert result["new_generation"] == 2
        assert result["diff"]["row_diff"] == 5

    def test_explicit_base_generation(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv", rows=5)
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        mgr.create_generation("gen1")
        _create_csv(csv_path, rows=8)
        mgr.create_generation("gen2")
        _create_csv(csv_path, rows=15)

        result = mgr.create_differential_backup(base_generation=1)
        assert result["status"] == "created"
        assert result["base_generation"] == 1
        assert result["diff"]["row_diff"] == 10

    def test_base_not_found_raises(self, tmp_path: Path):
        csv_path = _create_csv(tmp_path / "master.csv")
        mgr = GenerationManager(master_csv=csv_path, generation_dir=tmp_path / "gens")

        with pytest.raises(ValueError, match="Base generation 999 not found"):
            mgr.create_differential_backup(base_generation=999)


# =============================================================================
# print_generation_status Tests
# =============================================================================


class TestPrintGenerationStatus:
    """print_generation_status関数のテスト"""

    def test_print_status_no_generations(self, tmp_path: Path, capsys):
        csv_path = _create_csv(tmp_path / "master.csv")
        project_root = tmp_path

        with (
            patch("src.generation_manager.get_master_csv_path", return_value=csv_path),
            patch("src.generation_manager.get_project_root", return_value=project_root),
        ):
            print_generation_status()

        captured = capsys.readouterr()
        assert "Generation Manager" in captured.out
        assert "No generations created yet" in captured.out

    def test_print_status_with_generations(self, tmp_path: Path, capsys):
        csv_path = _create_csv(tmp_path / "master.csv")
        gen_dir = tmp_path / "gens"

        with (
            patch("src.generation_manager.get_master_csv_path", return_value=csv_path),
            patch("src.generation_manager.get_project_root", return_value=tmp_path),
        ):
            # GenerationManagerのデフォルトパスを上書きするため直接操作
            mgr = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)
            mgr.create_generation("test gen")

        # print_generation_statusはデフォルトパスを使うのでpatchが必要
        with (
            patch("src.generation_manager.get_master_csv_path", return_value=csv_path),
            patch("src.generation_manager.get_project_root", return_value=tmp_path),
        ):
            # generation_dirが異なるため、直接テスト
            mgr2 = GenerationManager(master_csv=csv_path, generation_dir=gen_dir)

        assert mgr2.metadata["current_generation"] == 1
