"""
CuratedEpisodeモデルのテスト
"""

import pytest
from datetime import datetime

from src.models.curated_episode import CuratedEpisode


def test_curated_episode_creation():
    """CuratedEpisodeの基本的な生成テスト"""
    episode = CuratedEpisode(
        person_id="P001ABC12",
        person_name="イチロー",
        age=31,
        episode_text="あなたと同じ31歳のとき、イチローは2004年シーズンに262安打を記録した。",
        source_id="SRC-abc123def456",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        evidence_quality="B",
    )

    assert episode.person_name == "イチロー"
    assert episode.age == 31
    assert episode.evidence_quality == "B"
    assert episode.validation_status == "pending"  # デフォルト
    assert episode.person_type == "REAL"  # デフォルト


def test_validation_age_range():
    """年齢範囲バリデーションテスト"""
    with pytest.raises(ValueError, match="Invalid age"):
        CuratedEpisode(
            person_id="P001ABC12",
            person_name="テスト",
            age=200,  # 不正な年齢
            episode_text="あなたと同じ200歳のとき...",
            source_id="SRC-abc123def456",
            source_url="https://example.com",
            evidence_quality="C",
        )


def test_validation_episode_text_format(caplog):
    """episode_textフォーマット警告テスト"""
    episode = CuratedEpisode(
        person_id="P001ABC12",
        person_name="テスト",
        age=30,
        episode_text="間違ったフォーマット",  # 「あなたと同じ」で始まらない
        source_id="SRC-abc123def456",
        source_url="https://example.com",
        evidence_quality="C",
    )

    # 警告ログが出力されることを確認
    assert "does not start with" in caplog.text


def test_mark_passed():
    """mark_passed機能テスト"""
    episode = CuratedEpisode(
        person_id="P001ABC12",
        person_name="イチロー",
        age=31,
        episode_text="あなたと同じ31歳のとき、イチローは...",
        source_id="SRC-abc123def456",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        evidence_quality="B",
    )

    episode.mark_passed()

    assert episode.validation_status == "passed"
    assert episode.validation_issues is None


def test_mark_failed():
    """mark_failed機能テスト"""
    episode = CuratedEpisode(
        person_id="P001ABC12",
        person_name="イチロー",
        age=31,
        episode_text="あなたと同じ31歳のとき、イチローは...",
        source_id="SRC-abc123def456",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        evidence_quality="B",
    )

    episode.mark_failed('[{"type": "format_violation"}]')

    assert episode.validation_status == "failed"
    assert episode.validation_issues is not None


def test_mark_review():
    """mark_review機能テスト"""
    episode = CuratedEpisode(
        person_id="P001ABC12",
        person_name="イチロー",
        age=31,
        episode_text="あなたと同じ31歳のとき、イチローは...",
        source_id="SRC-abc123def456",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        evidence_quality="C",
    )

    episode.mark_review("evidence_quality_C")

    assert episode.validation_status == "review"
    assert episode.validation_issues == "evidence_quality_C"


def test_to_master_format():
    """MASTER_EPISODES_CURRENT.csv互換形式変換テスト"""
    episode = CuratedEpisode(
        episode_id="EP-000000001",
        person_id="P001ABC12",
        person_name="イチロー",
        age=31,
        episode_text="あなたと同じ31歳のとき、イチローは...",
        source_id="SRC-abc123def456",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        evidence_quality="B",
        person_type="REAL",
        category="スポーツ",
        episode_type="転機",
    )

    master_data = episode.to_master_format()

    assert master_data["episode_id"] == "EP-000000001"
    assert master_data["person_id"] == "P001ABC12"
    assert master_data["person_name"] == "イチロー"
    assert master_data["age"] == 31
    assert master_data["source"] == "COLLECTION_PIPELINE"
    assert master_data["fact_check_result"] == "確認済み"  # B品質
    assert master_data["evidence_quality"] == "B"
    assert master_data["verification_status"] == "verified"
    assert "char_count" in master_data
    assert "quality_score" in master_data


def test_filter_by_status():
    """ステータスフィルタリングテスト"""
    episodes = [
        CuratedEpisode(
            person_id="P001ABC12",
            person_name="人物A",
            age=30,
            episode_text="あなたと同じ30歳のとき...",
            source_id="SRC-abc123",
            source_url="https://example.com/a",
            evidence_quality="A",
            validation_status="passed",
        ),
        CuratedEpisode(
            person_id="P002ABC12",
            person_name="人物B",
            age=40,
            episode_text="あなたと同じ40歳のとき...",
            source_id="SRC-def456",
            source_url="https://example.com/b",
            evidence_quality="B",
            validation_status="review",
        ),
    ]

    # passedのみ抽出
    passed = CuratedEpisode.filter_by_status(episodes, "passed")
    assert len(passed) == 1
    assert passed[0].person_name == "人物A"


def test_filter_by_quality():
    """品質フィルタリングテスト"""
    episodes = [
        CuratedEpisode(
            person_id="P001ABC12",
            person_name="人物A",
            age=30,
            episode_text="あなたと同じ30歳のとき...",
            source_id="SRC-abc123",
            source_url="https://example.com/a",
            evidence_quality="A",
        ),
        CuratedEpisode(
            person_id="P002ABC12",
            person_name="人物B",
            age=40,
            episode_text="あなたと同じ40歳のとき...",
            source_id="SRC-def456",
            source_url="https://example.com/b",
            evidence_quality="C",
        ),
    ]

    # B以上でフィルタ
    filtered = CuratedEpisode.filter_by_quality(episodes, min_quality="B")
    assert len(filtered) == 1
    assert filtered[0].evidence_quality == "A"
