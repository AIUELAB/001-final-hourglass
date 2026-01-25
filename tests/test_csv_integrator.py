"""
CSVIntegrator テストモジュール

csv_integrator.py の単体テストを提供します。
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

pytestmark = pytest.mark.integration

from src.csv_integrator import CSVIntegrator


@pytest.fixture
def sample_master_csv(tmp_path: Path) -> Path:
    """テスト用のMASTER CSVを作成"""
    master_path = tmp_path / "MASTER_EPISODES_CURRENT.csv"
    master_df = pd.DataFrame(
        [
            {
                "episode_id": "E12345678",
                "person_id": "P1234567",
                "person_name": "山田太郎",
                "age": "30",
                "category": "テスト",
                "episode_text": "テストエピソード",
                "person_type": "REAL",
                "char_count": 100,
                "composite_score": 75.0,
            },
            {
                "episode_id": "E87654321",
                "person_id": "P7654321",
                "person_name": "鈴木花子",
                "age": "25",
                "category": "テスト",
                "episode_text": "別のテストエピソード",
                "person_type": "REAL",
                "char_count": 120,
                "composite_score": 80.0,
            },
        ]
    )
    master_df.to_csv(master_path, index=False, encoding="utf-8-sig")
    return master_path


@pytest.fixture
def integrator(sample_master_csv: Path) -> CSVIntegrator:
    """テスト用のCSVIntegratorインスタンス"""
    with patch("src.csv_integrator.BackupManager") as mock_backup:
        mock_backup.return_value.create_backup.return_value = Path("/tmp/backup.csv")
        return CSVIntegrator(master_csv_path=sample_master_csv)


class TestCSVIntegratorInit:
    """初期化テスト"""

    def test_init_with_custom_path(self, sample_master_csv: Path) -> None:
        """カスタムパスで初期化できる"""
        with patch("src.csv_integrator.BackupManager"):
            integrator = CSVIntegrator(master_csv_path=sample_master_csv)
            assert integrator.master_path == sample_master_csv

    def test_init_with_default_path(self) -> None:
        """デフォルトパスで初期化できる"""
        with patch("src.csv_integrator.BackupManager"):
            with patch("src.csv_integrator.get_master_csv_path") as mock_path:
                mock_path.return_value = Path("/default/path.csv")
                integrator = CSVIntegrator()
                assert integrator.master_path == Path("/default/path.csv")


class TestIntegrateEpisodes:
    """integrate_episodes メソッドのテスト"""

    def test_dry_run_returns_would_add_count(self, integrator: CSVIntegrator) -> None:
        """Dry-runモードは追加予定件数を返す"""
        episodes = [
            {"person_name": "新規太郎", "age": 35, "episode_text": "新規エピソード"},
        ]
        result = integrator.integrate_episodes(episodes, dry_run=True)

        assert result["added"] == 0
        assert result["would_add"] == 1
        assert result["backup_path"] is None

    def test_dry_run_skips_duplicates(self, integrator: CSVIntegrator) -> None:
        """Dry-runモードは重複をスキップする"""
        episodes = [
            {"person_name": "山田太郎", "age": 30, "episode_text": "重複エピソード"},
        ]
        result = integrator.integrate_episodes(episodes, dry_run=True)

        assert result["added"] == 0
        assert result["would_add"] == 0
        assert result["skipped"] == 1

    def test_integration_adds_new_episodes(self, sample_master_csv: Path, integrator: CSVIntegrator) -> None:
        """新規エピソードが追加される"""
        episodes = [
            {
                "person_name": "新規太郎",
                "age": 35,
                "episode_text": "新規エピソード",
                "category": "テスト",
                "person_type": "REAL",
                "char_count": 100,
                "composite_score": 70.0,
            },
        ]
        result = integrator.integrate_episodes(episodes, dry_run=False)

        assert result["added"] == 1
        assert result["skipped"] == 0

        # CSVを読み直して確認
        master_df = pd.read_csv(sample_master_csv, encoding="utf-8-sig")
        assert len(master_df) == 3  # 元の2件 + 新規1件
        assert "新規太郎" in master_df["person_name"].values

    def test_integration_skips_duplicates(self, integrator: CSVIntegrator) -> None:
        """重複エピソードはスキップされる"""
        episodes = [
            {"person_name": "山田太郎", "age": 30, "episode_text": "重複"},
        ]
        result = integrator.integrate_episodes(episodes, dry_run=False)

        assert result["added"] == 0
        assert result["skipped"] == 1

    def test_integration_handles_empty_list(self, integrator: CSVIntegrator) -> None:
        """空のリストでもエラーにならない"""
        result = integrator.integrate_episodes([], dry_run=False)

        assert result["added"] == 0
        assert result["skipped"] == 0

    def test_integration_handles_mixed_episodes(self, integrator: CSVIntegrator) -> None:
        """新規と重複が混在するリストを処理できる"""
        episodes = [
            {"person_name": "山田太郎", "age": 30, "episode_text": "重複"},
            {
                "person_name": "新規次郎",
                "age": 40,
                "episode_text": "新規",
                "category": "テスト",
                "person_type": "REAL",
                "char_count": 100,
                "composite_score": 75.0,
            },
        ]
        result = integrator.integrate_episodes(episodes, dry_run=True)

        assert result["would_add"] == 1
        assert result["skipped"] == 1


class TestAddIds:
    """_add_ids メソッドのテスト"""

    def test_generates_episode_id(self, integrator: CSVIntegrator) -> None:
        """episode_idが生成される"""
        df = pd.DataFrame([{"person_name": "テスト太郎", "age": 25, "episode_text": "テスト"}])
        result = integrator._add_ids(df)

        assert "episode_id" in result.columns
        assert result["episode_id"].iloc[0].startswith("E")
        assert len(result["episode_id"].iloc[0]) == 9  # E + 8文字

    def test_generates_person_id(self, integrator: CSVIntegrator) -> None:
        """person_idが生成される"""
        df = pd.DataFrame([{"person_name": "テスト太郎", "age": 25, "episode_text": "テスト"}])
        result = integrator._add_ids(df)

        assert "person_id" in result.columns
        assert result["person_id"].iloc[0].startswith("P")
        assert len(result["person_id"].iloc[0]) == 8  # P + 7文字

    def test_same_person_gets_same_person_id(self, integrator: CSVIntegrator) -> None:
        """同じ人物名は同じperson_idを取得する"""
        df = pd.DataFrame(
            [
                {"person_name": "テスト太郎", "age": 25, "episode_text": "テスト1"},
                {"person_name": "テスト太郎", "age": 30, "episode_text": "テスト2"},
            ]
        )
        result = integrator._add_ids(df)

        assert result["person_id"].iloc[0] == result["person_id"].iloc[1]

    def test_different_episodes_get_different_episode_ids(self, integrator: CSVIntegrator) -> None:
        """異なるエピソードは異なるepisode_idを取得する"""
        df = pd.DataFrame(
            [
                {"person_name": "テスト太郎", "age": 25, "episode_text": "テスト1"},
                {"person_name": "テスト太郎", "age": 30, "episode_text": "テスト2"},
            ]
        )
        result = integrator._add_ids(df)

        assert result["episode_id"].iloc[0] != result["episode_id"].iloc[1]

    def test_preserves_existing_ids(self, integrator: CSVIntegrator) -> None:
        """既存のIDは保持される"""
        df = pd.DataFrame(
            [
                {
                    "person_name": "テスト太郎",
                    "age": 25,
                    "episode_text": "テスト",
                    "episode_id": "EEXISTING",
                    "person_id": "PEXIST",
                }
            ]
        )
        result = integrator._add_ids(df)

        assert result["episode_id"].iloc[0] == "EEXISTING"
        assert result["person_id"].iloc[0] == "PEXIST"

    def test_fills_empty_ids(self, integrator: CSVIntegrator) -> None:
        """空のIDは新規生成される"""
        df = pd.DataFrame(
            [
                {
                    "person_name": "テスト太郎",
                    "age": 25,
                    "episode_text": "テスト",
                    "episode_id": "",
                    "person_id": "",
                }
            ]
        )
        result = integrator._add_ids(df)

        assert result["episode_id"].iloc[0] != ""
        assert result["person_id"].iloc[0] != ""


class TestAlignColumns:
    """_align_columns メソッドのテスト"""

    def test_drops_extra_columns(self, integrator: CSVIntegrator) -> None:
        """マスターにないカラムは削除される"""
        new_df = pd.DataFrame([{"person_name": "テスト", "age": 25, "extra_column": "削除対象"}])
        master_columns = pd.Index(["person_name", "age"])

        result = integrator._align_columns(new_df, master_columns)

        assert "extra_column" not in result.columns
        assert list(result.columns) == ["person_name", "age"]

    def test_adds_missing_columns(self, integrator: CSVIntegrator) -> None:
        """不足しているカラムは空文字で追加される"""
        new_df = pd.DataFrame([{"person_name": "テスト"}])
        master_columns = pd.Index(["person_name", "age", "category"])

        result = integrator._align_columns(new_df, master_columns)

        assert "age" in result.columns
        assert "category" in result.columns
        assert result["age"].iloc[0] == ""
        assert result["category"].iloc[0] == ""

    def test_preserves_column_order(self, integrator: CSVIntegrator) -> None:
        """カラム順序がマスターと同じになる"""
        new_df = pd.DataFrame([{"age": 25, "person_name": "テスト"}])
        master_columns = pd.Index(["person_name", "age", "category"])

        result = integrator._align_columns(new_df, master_columns)

        assert list(result.columns) == ["person_name", "age", "category"]


class TestVerifyIdempotency:
    """verify_idempotency メソッドのテスト"""

    def test_reports_idempotent_for_duplicates(self, integrator: CSVIntegrator) -> None:
        """重複エピソードは冪等と判定される"""
        episodes = [
            {"person_name": "山田太郎", "age": 30, "episode_text": "テスト"},
        ]
        result = integrator.verify_idempotency(episodes)

        # 既存データなので両方ともスキップされる
        assert result["is_idempotent"] is True

    def test_returns_run_details(self, integrator: CSVIntegrator) -> None:
        """実行詳細が返される"""
        episodes = [
            {"person_name": "新規太郎", "age": 99, "episode_text": "テスト"},
        ]
        result = integrator.verify_idempotency(episodes)

        assert "first_run" in result
        assert "second_run" in result
        assert "is_idempotent" in result
