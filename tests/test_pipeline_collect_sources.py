#!/usr/bin/env python3
"""
Test: pipeline_collect_sources.py

Stage 1情報源収集パイプラインのユニットテスト。
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.integration

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.episode_source import EpisodeSource


class TestEpisodeSource:
    """EpisodeSourceモデルのテスト"""

    def test_generate_source_id(self):
        """source_id生成の冪等性テスト"""
        source_id1 = EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")
        source_id2 = EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")

        assert source_id1 == source_id2
        assert source_id1.startswith("SRC-")
        assert len(source_id1) == 20  # SRC- + 16文字

    def test_generate_source_id_different_inputs(self):
        """異なる入力で異なるsource_idが生成されることを確認"""
        source_id1 = EpisodeSource.generate_source_id("イチロー", "https://example.com/1")
        source_id2 = EpisodeSource.generate_source_id("イチロー", "https://example.com/2")
        source_id3 = EpisodeSource.generate_source_id("山中伸弥", "https://example.com/1")

        assert source_id1 != source_id2
        assert source_id1 != source_id3
        assert source_id2 != source_id3

    def test_create_episode_source(self):
        """EpisodeSource生成テスト"""
        source = EpisodeSource(
            person_name="イチロー",
            person_id="P001",
            person_type="REAL",
            source_url="https://ja.wikipedia.org/wiki/イチロー",
            source_type="wikipedia",
            raw_text="2004年シーズン262安打記録",
            context="年齢31歳時の業績",
            evidence_quality="B",
        )

        assert source.person_name == "イチロー"
        assert source.person_id == "P001"
        assert source.person_type == "REAL"
        assert source.evidence_quality == "B"
        assert source.verification_status == "unverified"
        assert source.source_id.startswith("SRC-")

    def test_invalid_person_type(self):
        """不正なperson_typeでエラーが発生することを確認"""
        with pytest.raises(ValueError, match="Invalid person_type"):
            EpisodeSource(
                person_name="テスト",
                person_id="P001",
                person_type="INVALID",
                source_url="https://example.com",
                source_type="manual",
                raw_text="テスト",
            )

    def test_invalid_evidence_quality(self):
        """不正なevidence_qualityでエラーが発生することを確認"""
        with pytest.raises(ValueError, match="Invalid evidence_quality"):
            EpisodeSource(
                person_name="テスト",
                person_id="P001",
                person_type="REAL",
                source_url="https://example.com",
                source_type="manual",
                raw_text="テスト",
                evidence_quality="D",
            )

    def test_invalid_url_format(self):
        """不正なURL形式でエラーが発生することを確認"""
        with pytest.raises(ValueError, match="Invalid URL format"):
            EpisodeSource(
                person_name="テスト",
                person_id="P001",
                person_type="REAL",
                source_url="example.com",  # http:// がない
                source_type="manual",
                raw_text="テスト",
            )

    def test_missing_required_field(self):
        """必須フィールド欠落でエラーが発生することを確認"""
        with pytest.raises(ValueError, match="person_name is required"):
            EpisodeSource(
                person_name="",
                person_id="P001",
                person_type="REAL",
                source_url="https://example.com",
                source_type="manual",
                raw_text="テスト",
            )

    def test_to_dict(self):
        """to_dict()メソッドのテスト"""
        source = EpisodeSource(
            person_name="イチロー",
            person_id="P001",
            person_type="REAL",
            source_url="https://ja.wikipedia.org/wiki/イチロー",
            source_type="wikipedia",
            raw_text="2004年シーズン262安打記録",
        )

        data = source.to_dict()

        assert isinstance(data, dict)
        assert data["person_name"] == "イチロー"
        assert data["person_id"] == "P001"
        assert data["source_id"].startswith("SRC-")
        assert "collected_at" in data

    def test_from_dict(self):
        """from_dict()メソッドのテスト"""
        data = {
            "source_id": "SRC-test123",
            "person_name": "イチロー",
            "person_id": "P001",
            "person_type": "REAL",
            "source_url": "https://ja.wikipedia.org/wiki/イチロー",
            "source_type": "wikipedia",
            "raw_text": "2004年シーズン262安打記録",
            "context": "年齢31歳時の業績",
            "evidence_quality": "B",
            "verification_status": "verified",
            "collected_at": "2025-12-17T14:00:00",
            "verified_at": "",
        }

        source = EpisodeSource.from_dict(data)

        assert source.person_name == "イチロー"
        assert source.person_id == "P001"
        assert source.evidence_quality == "B"

    def test_save_and_load_csv(self):
        """CSV保存・読み込みのテスト"""
        sources = [
            EpisodeSource(
                person_name="イチロー",
                person_id="P001",
                person_type="REAL",
                source_url="https://ja.wikipedia.org/wiki/イチロー",
                source_type="wikipedia",
                raw_text="2004年シーズン262安打記録",
            ),
            EpisodeSource(
                person_name="山中伸弥",
                person_id="P002",
                person_type="REAL",
                source_url="https://ja.wikipedia.org/wiki/山中伸弥",
                source_type="wikipedia",
                raw_text="2012年ノーベル賞受賞",
            ),
        ]

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)

        try:
            EpisodeSource.save_to_csv(sources, temp_path)

            # 読み込み
            loaded_sources = EpisodeSource.load_from_csv(temp_path)

            assert len(loaded_sources) == 2
            assert loaded_sources[0].person_name == "イチロー"
            assert loaded_sources[1].person_name == "山中伸弥"

        finally:
            temp_path.unlink()

    def test_is_duplicate(self):
        """重複チェックのテスト"""
        source = EpisodeSource(
            person_name="イチロー",
            person_id="P001",
            person_type="REAL",
            source_url="https://ja.wikipedia.org/wiki/イチロー",
            source_type="wikipedia",
            raw_text="2004年シーズン262安打記録",
        )

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = Path(f.name)

        try:
            EpisodeSource.save_to_csv([source], temp_path)

            # 重複チェック
            assert EpisodeSource.is_duplicate(source.source_id, temp_path) is True
            assert EpisodeSource.is_duplicate("SRC-nonexistent", temp_path) is False

        finally:
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
