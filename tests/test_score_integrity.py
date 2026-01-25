#!/usr/bin/env python3
"""
スコア整合性マネージャーのテスト

テスト項目:
  - 欠損検出が正しく動作すること
  - 欠損埋めが正しく動作すること
  - 範囲外値が検出されること
  - 欠損理由がレポートに出力されること
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.integration

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.score.score_integrity_manager import ScoreIntegrityManager, SCORE_COLUMNS


@pytest.fixture
def sample_df():
    """テスト用のサンプルDataFrame"""
    return pd.DataFrame(
        {
            "episode_id": ["EP-001", "EP-002", "EP-003", "EP-004", "EP-005"],
            "person_id": ["P001", "P002", "P003", "P004", "P005"],
            "episode_text": [
                "1990年、彼は世界記録を達成した。",
                "短い文。",
                "2005年に初の「作品名」を発表。感動的な発見だった。",
                "",
                "1985年と1995年、2度の転機。しかし困難を克服して達成した。",
            ],
            "memorability_score": [7.0, 0, 8.0, 6.0, 7.5],
            "empathy_score": [6.5, 0, 7.0, 6.0, 8.0],
            "surprise_score": [7.0, 0, 6.5, 5.5, 7.5],
            "generation_quality_score": [7.5, 0, 7.5, 6.5, 8.0],
            "educational_value": [7.0, 0, 8.0, 6.0, 7.0],
            "story_quality": [6.5, 0, 7.5, 5.5, 8.0],
            "factual_density": [8.0, 0, 7.0, 6.0, 8.5],
            "composite_score": [49.5, 0, 51.5, 0, 54.5],
            "composite_score_5axis": [0, 0, 0, 0, 0],
            "episode_fame_v6": [50.0, 30.0, 60.0, 40.0, 70.0],
            "episode_fame_tier_v6": [3, 2, 3, 2, 4],
            "episode_fame_score": [50.0, 0, 60.0, 0, 70.0],
            "fame_score_v3": [500.0, 300.0, 600.0, 400.0, 700.0],
            "fame_score_japan": [0, 0, 0, 0, 0],
            "fame_tier": [3, 0, 4, 0, 4],
            "celebrity_score_v2": [500.0, 300.0, 600.0, 400.0, 700.0],
            "celebrity_rank_v2": [100, 200, 50, 150, 30],
            "super_total_score": [500000, 0, 600000, 0, 700000],
            "quality_score": [7.0, 0, 7.5, 0, 8.0],
        }
    )


class TestScoreIntegrityManager:
    """ScoreIntegrityManagerのテストクラス"""

    def test_detect_missing_identifies_zeros(self, sample_df, tmp_path, monkeypatch):
        """0値を欠損として検出できること"""
        csv_path = tmp_path / "test.csv"
        sample_df.to_csv(csv_path, index=False)

        monkeypatch.setattr("scripts.score.score_integrity_manager.CSV_PATH", csv_path)

        manager = ScoreIntegrityManager(dry_run=True)
        manager.load_csv()
        results = manager.detect_missing()

        # memorability_scoreは1件欠損（0値）
        assert results["memorability_score"]["missing"] == 1
        assert results["memorability_score"]["filled"] == 4

    def test_detect_missing_identifies_nan(self, sample_df, tmp_path, monkeypatch):
        """NaN値を欠損として検出できること"""
        sample_df.loc[0, "memorability_score"] = np.nan
        csv_path = tmp_path / "test.csv"
        sample_df.to_csv(csv_path, index=False)

        monkeypatch.setattr("scripts.score.score_integrity_manager.CSV_PATH", csv_path)

        manager = ScoreIntegrityManager(dry_run=True)
        manager.load_csv()
        results = manager.detect_missing()

        # memorability_scoreは2件欠損（NaN + 0値）
        assert results["memorability_score"]["missing"] == 2

    def test_fill_composite_score(self, sample_df, tmp_path, monkeypatch):
        """composite_scoreが7軸から正しく計算されること"""
        csv_path = tmp_path / "test.csv"
        sample_df.to_csv(csv_path, index=False)

        monkeypatch.setattr("scripts.score.score_integrity_manager.CSV_PATH", csv_path)

        manager = ScoreIntegrityManager(dry_run=False)
        manager.load_csv()
        manager.fill_missing_scores()

        # EP-004のcomposite_scoreが計算されていること
        idx = manager.df[manager.df["episode_id"] == "EP-004"].index[0]
        expected = 6.0 + 6.0 + 5.5 + 6.5 + 6.0 + 5.5 + 6.0  # 41.5
        assert manager.df.at[idx, "composite_score"] == expected

    def test_fill_fame_tier_from_fame_score(self, sample_df, tmp_path, monkeypatch):
        """fame_tierがfame_score_v3から正しく計算されること"""
        csv_path = tmp_path / "test.csv"
        sample_df.to_csv(csv_path, index=False)

        monkeypatch.setattr("scripts.score.score_integrity_manager.CSV_PATH", csv_path)

        manager = ScoreIntegrityManager(dry_run=False)
        manager.load_csv()
        manager.fill_missing_scores()

        # fame_score_v3=300 → tier=2 (200-400範囲)
        idx = manager.df[manager.df["episode_id"] == "EP-002"].index[0]
        tier = manager.df.at[idx, "fame_tier"]
        assert tier >= 1 and tier <= 5, f"fame_tier should be 1-5, got {tier}"

        # fame_score_v3=400 → tier=2 (200-400範囲)
        idx = manager.df[manager.df["episode_id"] == "EP-004"].index[0]
        tier = manager.df.at[idx, "fame_tier"]
        assert tier >= 1 and tier <= 5, f"fame_tier should be 1-5, got {tier}"

    def test_sync_episode_fame_score(self, sample_df, tmp_path, monkeypatch):
        """episode_fame_scoreがepisode_fame_v6から同期されること"""
        csv_path = tmp_path / "test.csv"
        sample_df.to_csv(csv_path, index=False)

        monkeypatch.setattr("scripts.score.score_integrity_manager.CSV_PATH", csv_path)

        manager = ScoreIntegrityManager(dry_run=False)
        manager.load_csv()
        manager.fill_missing_scores()

        # EP-002: episode_fame_v6=30 → episode_fame_score=30
        idx = manager.df[manager.df["episode_id"] == "EP-002"].index[0]
        assert manager.df.at[idx, "episode_fame_score"] == 30.0

    def test_heuristic_score_calculation(self, tmp_path, monkeypatch):
        """ヒューリスティックスコア計算が正しく動作すること"""
        df = pd.DataFrame(
            {
                "episode_id": ["EP-001"],
                "person_id": ["P001"],
                "episode_text": ["1990年、感動的な発見。しかし困難を克服した。"],
                "memorability_score": [0],
                "empathy_score": [0],
                "surprise_score": [0],
                "generation_quality_score": [0],
                "educational_value": [0],
                "story_quality": [0],
                "factual_density": [0],
                "composite_score": [0],
                "composite_score_5axis": [0],
                "episode_fame_v6": [50],
                "episode_fame_tier_v6": [3],
                "episode_fame_score": [0],
                "fame_score_v3": [500],
                "fame_score_japan": [0],
                "fame_tier": [0],
                "celebrity_score_v2": [500],
                "celebrity_rank_v2": [100],
                "super_total_score": [0],
                "quality_score": [0],
            }
        )

        csv_path = tmp_path / "test.csv"
        df.to_csv(csv_path, index=False)

        monkeypatch.setattr("scripts.score.score_integrity_manager.CSV_PATH", csv_path)

        manager = ScoreIntegrityManager(dry_run=False)
        manager.load_csv()
        manager.fill_missing_scores()

        # 7軸スコアがすべて5.0〜9.5の範囲内であること
        for col in [
            "memorability_score",
            "empathy_score",
            "surprise_score",
            "generation_quality_score",
            "educational_value",
            "story_quality",
            "factual_density",
        ]:
            score = manager.df.at[0, col]
            assert 5.0 <= score <= 9.5, f"{col} = {score} is out of range"

    def test_validation_detects_out_of_range(self, tmp_path, monkeypatch):
        """範囲外値が検出されること"""
        df = pd.DataFrame(
            {
                "episode_id": ["EP-001"],
                "person_id": ["P001"],
                "episode_text": ["テスト"],
                "memorability_score": [20.0],  # 範囲外 (0-10, max*1.5=15まで許容)
                "empathy_score": [7.0],
                "surprise_score": [7.0],
                "generation_quality_score": [7.0],
                "educational_value": [7.0],
                "story_quality": [7.0],
                "factual_density": [7.0],
                "composite_score": [49.0],
                "composite_score_5axis": [35.0],
                "episode_fame_v6": [50],
                "episode_fame_tier_v6": [3],
                "episode_fame_score": [50],
                "fame_score_v3": [500],
                "fame_score_japan": [0],
                "fame_tier": [3],
                "celebrity_score_v2": [500],
                "celebrity_rank_v2": [100],
                "super_total_score": [500000],
                "quality_score": [7.0],
            }
        )

        csv_path = tmp_path / "test.csv"
        df.to_csv(csv_path, index=False)

        monkeypatch.setattr("scripts.score.score_integrity_manager.CSV_PATH", csv_path)

        manager = ScoreIntegrityManager(dry_run=True)
        manager.load_csv()
        validation = manager.validate_scores()

        # memorability_scoreが範囲外として検出されること (20 > 10*1.5=15)
        assert "memorability_score" in validation["range_violations"]
        assert validation["range_violations"]["memorability_score"] == 1

    def test_dry_run_does_not_modify_csv(self, sample_df, tmp_path, monkeypatch):
        """dry-runモードではCSVが変更されないこと"""
        csv_path = tmp_path / "test.csv"
        sample_df.to_csv(csv_path, index=False)
        original_content = csv_path.read_text()

        monkeypatch.setattr("scripts.score.score_integrity_manager.CSV_PATH", csv_path)

        manager = ScoreIntegrityManager(dry_run=True)
        manager.run_full_pipeline()

        # CSVが変更されていないこと
        assert csv_path.read_text() == original_content

    def test_report_generation(self, sample_df, tmp_path, monkeypatch):
        """レポートが正しく生成されること"""
        csv_path = tmp_path / "test.csv"
        sample_df.to_csv(csv_path, index=False)

        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        monkeypatch.setattr("scripts.score.score_integrity_manager.CSV_PATH", csv_path)
        monkeypatch.setattr("scripts.score.score_integrity_manager.LOG_DIR", log_dir)

        manager = ScoreIntegrityManager(dry_run=True)
        manager.load_csv()
        manager.detect_missing()
        report_path = manager.save_report()

        assert report_path.exists()
        assert report_path.suffix == ".json"


class TestScoreColumnDefinitions:
    """スコア列定義のテスト"""

    def test_all_required_columns_defined(self):
        """必須列がすべて定義されていること"""
        required_cols = [
            "memorability_score",
            "empathy_score",
            "surprise_score",
            "generation_quality_score",
            "educational_value",
            "story_quality",
            "factual_density",
            "composite_score",
            "episode_fame_v6",
            "episode_fame_tier_v6",
            "fame_score_v3",
            "celebrity_score_v2",
            "celebrity_rank_v2",
            "super_total_score",
        ]

        for col in required_cols:
            assert col in SCORE_COLUMNS, f"{col} is not defined"
            assert SCORE_COLUMNS[col]["required"] is True or SCORE_COLUMNS[col]["scale"] is not None

    def test_scale_definitions_are_valid(self):
        """スケール定義が有効であること"""
        for col, config in SCORE_COLUMNS.items():
            scale = config["scale"]
            assert len(scale) == 2, f"{col} scale must have 2 elements"
            assert scale[0] < scale[1], f"{col} scale min must be less than max"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
