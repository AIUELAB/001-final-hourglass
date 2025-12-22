#!/usr/bin/env python3
"""curated_episode.py のユニットテスト"""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from src.models.curated_episode import CuratedEpisode


def make_valid_episode(**kwargs) -> CuratedEpisode:
    """テスト用の有効なCuratedEpisodeを作成"""
    defaults = {
        "person_id": "P123",
        "person_name": "山田太郎",
        "age": 30,
        "episode_text": "あなたと同じ30歳の時、山田太郎は重要な成果を達成しました。",
        "source_id": "S001",
        "source_url": "https://example.com/source",
        "evidence_quality": "A",
    }
    defaults.update(kwargs)
    return CuratedEpisode(**defaults)


class TestCuratedEpisodeInit:
    """CuratedEpisode初期化のテスト"""

    def test_creates_valid_episode(self):
        """有効なデータで作成"""
        episode = make_valid_episode()
        assert episode.person_id == "P123"
        assert episode.person_name == "山田太郎"
        assert episode.age == 30
        assert episode.validation_status == "pending"

    def test_default_values(self):
        """デフォルト値が設定される"""
        episode = make_valid_episode()
        assert episode.episode_id == ""
        assert episode.validation_status == "pending"
        assert episode.person_type == "REAL"
        assert episode.category is None
        assert episode.episode_type is None


class TestValidate:
    """validate() メソッドのテスト"""

    def test_missing_person_id(self):
        """person_idがない場合エラー"""
        with pytest.raises(ValueError, match="person_id is required"):
            CuratedEpisode(
                person_id="",
                person_name="山田太郎",
                age=30,
                episode_text="あなたと同じ30歳",
                source_id="S001",
                source_url="https://example.com",
                evidence_quality="A",
            )

    def test_missing_person_name(self):
        """person_nameがない場合エラー"""
        with pytest.raises(ValueError, match="person_name is required"):
            CuratedEpisode(
                person_id="P123",
                person_name="",
                age=30,
                episode_text="あなたと同じ30歳",
                source_id="S001",
                source_url="https://example.com",
                evidence_quality="A",
            )

    def test_missing_episode_text(self):
        """episode_textがない場合エラー"""
        with pytest.raises(ValueError, match="episode_text is required"):
            CuratedEpisode(
                person_id="P123",
                person_name="山田太郎",
                age=30,
                episode_text="",
                source_id="S001",
                source_url="https://example.com",
                evidence_quality="A",
            )

    def test_missing_source_id(self):
        """source_idがない場合エラー"""
        with pytest.raises(ValueError, match="source_id is required"):
            CuratedEpisode(
                person_id="P123",
                person_name="山田太郎",
                age=30,
                episode_text="あなたと同じ30歳",
                source_id="",
                source_url="https://example.com",
                evidence_quality="A",
            )

    def test_missing_source_url(self):
        """source_urlがない場合エラー"""
        with pytest.raises(ValueError, match="source_url is required"):
            CuratedEpisode(
                person_id="P123",
                person_name="山田太郎",
                age=30,
                episode_text="あなたと同じ30歳",
                source_id="S001",
                source_url="",
                evidence_quality="A",
            )

    def test_invalid_age_negative(self):
        """年齢が負の場合エラー"""
        with pytest.raises(ValueError, match="Invalid age"):
            CuratedEpisode(
                person_id="P123",
                person_name="山田太郎",
                age=-1,
                episode_text="あなたと同じ30歳",
                source_id="S001",
                source_url="https://example.com",
                evidence_quality="A",
            )

    def test_invalid_age_over_150(self):
        """年齢が150超の場合エラー"""
        with pytest.raises(ValueError, match="Invalid age"):
            CuratedEpisode(
                person_id="P123",
                person_name="山田太郎",
                age=151,
                episode_text="あなたと同じ30歳",
                source_id="S001",
                source_url="https://example.com",
                evidence_quality="A",
            )

    def test_age_boundary_0(self):
        """年齢0は有効"""
        episode = make_valid_episode(age=0)
        assert episode.age == 0

    def test_age_boundary_150(self):
        """年齢150は有効"""
        episode = make_valid_episode(age=150)
        assert episode.age == 150

    def test_invalid_evidence_quality(self):
        """evidence_qualityが不正の場合エラー"""
        with pytest.raises(ValueError, match="Invalid evidence_quality"):
            CuratedEpisode(
                person_id="P123",
                person_name="山田太郎",
                age=30,
                episode_text="あなたと同じ30歳",
                source_id="S001",
                source_url="https://example.com",
                evidence_quality="D",
            )

    def test_invalid_validation_status(self):
        """validation_statusが不正の場合エラー"""
        with pytest.raises(ValueError, match="Invalid validation_status"):
            CuratedEpisode(
                person_id="P123",
                person_name="山田太郎",
                age=30,
                episode_text="あなたと同じ30歳",
                source_id="S001",
                source_url="https://example.com",
                evidence_quality="A",
                validation_status="unknown",
            )

    def test_invalid_person_type(self):
        """person_typeが不正の場合エラー"""
        with pytest.raises(ValueError, match="Invalid person_type"):
            CuratedEpisode(
                person_id="P123",
                person_name="山田太郎",
                age=30,
                episode_text="あなたと同じ30歳",
                source_id="S001",
                source_url="https://example.com",
                evidence_quality="A",
                person_type="UNKNOWN",
            )

    def test_episode_text_format_warning(self):
        """episode_textが「あなたと同じ」で始まらない場合警告"""
        import logging

        with patch.object(logging, "warning") as mock_warning:
            CuratedEpisode(
                person_id="P123",
                person_name="山田太郎",
                age=30,
                episode_text="別の形式のテキスト",
                source_id="S001",
                source_url="https://example.com",
                evidence_quality="A",
            )
            mock_warning.assert_called_once()


class TestMarkMethods:
    """mark_passed/mark_failed/mark_review メソッドのテスト"""

    def test_mark_passed(self):
        """mark_passedでステータスがpassedになる"""
        episode = make_valid_episode()
        episode.mark_passed()
        assert episode.validation_status == "passed"
        assert episode.validation_issues is None

    def test_mark_failed(self):
        """mark_failedでステータスがfailedになる"""
        episode = make_valid_episode()
        episode.mark_failed("重大なエラー")
        assert episode.validation_status == "failed"
        assert episode.validation_issues == "重大なエラー"

    def test_mark_review(self):
        """mark_reviewでステータスがreviewになる"""
        episode = make_valid_episode()
        episode.mark_review("要確認")
        assert episode.validation_status == "review"
        assert episode.validation_issues == "要確認"


class TestToDict:
    """to_dict() メソッドのテスト"""

    def test_returns_dict(self):
        """辞書を返す"""
        episode = make_valid_episode()
        result = episode.to_dict()
        assert isinstance(result, dict)

    def test_contains_all_fields(self):
        """全フィールドを含む"""
        episode = make_valid_episode()
        result = episode.to_dict()
        expected_keys = [
            "episode_id",
            "person_id",
            "person_name",
            "age",
            "episode_text",
            "source_id",
            "source_url",
            "evidence_quality",
            "validation_status",
            "validation_issues",
            "generated_at",
            "person_type",
            "category",
            "episode_type",
        ]
        for key in expected_keys:
            assert key in result

    def test_handles_none_values(self):
        """Noneの値を空文字に変換"""
        episode = make_valid_episode(category=None)
        result = episode.to_dict()
        assert result["category"] == ""


class TestFromDict:
    """from_dict() クラスメソッドのテスト"""

    def test_creates_from_dict(self):
        """辞書からインスタンス作成"""
        data = {
            "person_id": "P123",
            "person_name": "山田太郎",
            "age": 30,
            "episode_text": "あなたと同じ30歳",
            "source_id": "S001",
            "source_url": "https://example.com",
            "evidence_quality": "A",
        }
        episode = CuratedEpisode.from_dict(data)
        assert episode.person_id == "P123"

    def test_datetime_string_conversion(self):
        """datetime文字列を変換"""
        data = {
            "person_id": "P123",
            "person_name": "山田太郎",
            "age": 30,
            "episode_text": "あなたと同じ30歳",
            "source_id": "S001",
            "source_url": "https://example.com",
            "evidence_quality": "A",
            "generated_at": "2024-01-15T10:30:00",
        }
        episode = CuratedEpisode.from_dict(data)
        assert isinstance(episode.generated_at, datetime)
        assert episode.generated_at.year == 2024

    def test_datetime_none_uses_now(self):
        """generated_atがNoneの場合は現在時刻"""
        data = {
            "person_id": "P123",
            "person_name": "山田太郎",
            "age": 30,
            "episode_text": "あなたと同じ30歳",
            "source_id": "S001",
            "source_url": "https://example.com",
            "evidence_quality": "A",
            "generated_at": None,
        }
        episode = CuratedEpisode.from_dict(data)
        assert isinstance(episode.generated_at, datetime)

    def test_optional_fields(self):
        """オプションフィールドのデフォルト値"""
        data = {
            "person_id": "P123",
            "person_name": "山田太郎",
            "age": 30,
            "episode_text": "あなたと同じ30歳",
            "source_id": "S001",
            "source_url": "https://example.com",
            "evidence_quality": "A",
        }
        episode = CuratedEpisode.from_dict(data)
        assert episode.episode_id == ""
        assert episode.validation_status == "pending"
        assert episode.person_type == "REAL"


class TestToMasterFormat:
    """to_master_format() メソッドのテスト"""

    def test_returns_master_format(self):
        """マスター形式の辞書を返す"""
        episode = make_valid_episode(evidence_quality="A")
        result = episode.to_master_format()
        assert isinstance(result, dict)
        assert "fact_check_result" in result
        assert result["source"] == "COLLECTION_PIPELINE"

    def test_fact_check_result_for_quality_a(self):
        """品質Aは確認済み"""
        episode = make_valid_episode(evidence_quality="A")
        result = episode.to_master_format()
        assert result["fact_check_result"] == "確認済み"

    def test_fact_check_result_for_quality_c(self):
        """品質Cは未確認"""
        episode = make_valid_episode(evidence_quality="C")
        result = episode.to_master_format()
        assert result["fact_check_result"] == "未確認"


class TestSaveToCSV:
    """save_to_csv() 静的メソッドのテスト"""

    def test_saves_episodes(self, tmp_path):
        """エピソードをCSVに保存"""
        episodes = [make_valid_episode()]
        csv_path = tmp_path / "test.csv"
        CuratedEpisode.save_to_csv(episodes, csv_path)
        assert csv_path.exists()

    def test_empty_list_does_nothing(self, tmp_path):
        """空リストの場合は何もしない"""
        csv_path = tmp_path / "test.csv"
        CuratedEpisode.save_to_csv([], csv_path)
        assert not csv_path.exists()

    def test_append_mode(self, tmp_path):
        """追記モード"""
        csv_path = tmp_path / "test.csv"
        # 最初に1件保存
        episodes1 = [make_valid_episode(person_id="P001")]
        CuratedEpisode.save_to_csv(episodes1, csv_path)

        # 追記
        episodes2 = [make_valid_episode(person_id="P002")]
        CuratedEpisode.save_to_csv(episodes2, csv_path, append=True)

        # 確認
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        assert len(df) == 2

    def test_creates_parent_directory(self, tmp_path):
        """親ディレクトリを作成"""
        csv_path = tmp_path / "subdir" / "test.csv"
        episodes = [make_valid_episode()]
        CuratedEpisode.save_to_csv(episodes, csv_path)
        assert csv_path.exists()


class TestLoadFromCSV:
    """load_from_csv() 静的メソッドのテスト"""

    def test_loads_episodes(self, tmp_path):
        """CSVからエピソードを読み込み"""
        csv_path = tmp_path / "test.csv"
        # 保存
        episodes = [make_valid_episode()]
        CuratedEpisode.save_to_csv(episodes, csv_path)
        # 読み込み
        loaded = CuratedEpisode.load_from_csv(csv_path)
        assert len(loaded) == 1
        assert loaded[0].person_id == "P123"

    def test_returns_empty_for_nonexistent_file(self, tmp_path):
        """存在しないファイルは空リスト"""
        csv_path = tmp_path / "nonexistent.csv"
        loaded = CuratedEpisode.load_from_csv(csv_path)
        assert loaded == []

    def test_handles_invalid_rows(self, tmp_path):
        """不正な行をスキップ"""
        csv_path = tmp_path / "test.csv"
        # 不正なデータを含むCSVを手動作成
        df = pd.DataFrame(
            [
                {
                    "person_id": "P001",
                    "person_name": "山田",
                    "age": 30,
                    "episode_text": "あなたと同じ",
                    "source_id": "S1",
                    "source_url": "http://example.com",
                    "evidence_quality": "A",
                },
                {
                    "person_id": "",
                    "person_name": "",
                    "age": "invalid",
                    "episode_text": "",
                    "source_id": "",
                    "source_url": "",
                    "evidence_quality": "X",
                },
            ]
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        import logging

        with patch.object(logging, "error") as mock_error:
            loaded = CuratedEpisode.load_from_csv(csv_path)
            # 有効な行のみ読み込み
            assert len(loaded) == 1
            mock_error.assert_called()


class TestFilterMethods:
    """filter_by_status/filter_by_quality 静的メソッドのテスト"""

    def test_filter_by_status(self):
        """ステータスでフィルタリング"""
        episodes = [
            make_valid_episode(person_id="P001"),
            make_valid_episode(person_id="P002"),
            make_valid_episode(person_id="P003"),
        ]
        episodes[0].validation_status = "passed"
        episodes[1].validation_status = "failed"
        episodes[2].validation_status = "passed"

        result = CuratedEpisode.filter_by_status(episodes, "passed")
        assert len(result) == 2

    def test_filter_by_quality_a(self):
        """品質Aでフィルタリング"""
        episodes = [
            make_valid_episode(evidence_quality="A"),
            make_valid_episode(evidence_quality="B"),
            make_valid_episode(evidence_quality="C"),
        ]
        result = CuratedEpisode.filter_by_quality(episodes, "A")
        assert len(result) == 1

    def test_filter_by_quality_b(self):
        """品質B以上でフィルタリング"""
        episodes = [
            make_valid_episode(evidence_quality="A"),
            make_valid_episode(evidence_quality="B"),
            make_valid_episode(evidence_quality="C"),
        ]
        result = CuratedEpisode.filter_by_quality(episodes, "B")
        assert len(result) == 2

    def test_filter_by_quality_c(self):
        """品質C以上でフィルタリング（全て）"""
        episodes = [
            make_valid_episode(evidence_quality="A"),
            make_valid_episode(evidence_quality="B"),
            make_valid_episode(evidence_quality="C"),
        ]
        result = CuratedEpisode.filter_by_quality(episodes, "C")
        assert len(result) == 3
