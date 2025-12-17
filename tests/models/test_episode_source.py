"""
EpisodeSourceモデルのテスト
"""

import pytest
from datetime import datetime
from pathlib import Path

from src.models.episode_source import EpisodeSource


def test_episode_source_creation():
    """EpisodeSourceの基本的な生成テスト"""
    source = EpisodeSource(
        person_name="イチロー",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        source_type="wikipedia",
        raw_text="2004年シーズン262安打記録",
        context="年齢31歳時の業績",
    )

    assert source.person_name == "イチロー"
    assert source.person_id == "P001ABC12"
    assert source.person_type == "REAL"
    assert source.evidence_quality == "C"  # デフォルト
    assert source.verification_status == "unverified"  # デフォルト
    assert source.source_id.startswith("SRC-")
    assert len(source.source_id) == 20  # SRC- + 16桁


def test_source_id_generation():
    """source_id生成の冪等性テスト"""
    source_id1 = EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")
    source_id2 = EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")

    assert source_id1 == source_id2  # 同じ入力は同じIDを生成


def test_validation_invalid_url():
    """不正なURL形式のバリデーションテスト"""
    with pytest.raises(ValueError, match="Invalid URL format"):
        EpisodeSource(
            person_name="テスト",
            person_id="P001ABC12",
            person_type="REAL",
            source_url="not-a-url",  # 不正なURL
            source_type="manual",
            raw_text="テストテキスト",
        )


def test_validation_invalid_person_type():
    """不正なperson_typeのバリデーションテスト"""
    with pytest.raises(ValueError, match="Invalid person_type"):
        EpisodeSource(
            person_name="テスト",
            person_id="P001ABC12",
            person_type="INVALID",  # 不正なperson_type
            source_url="https://example.com",
            source_type="manual",
            raw_text="テストテキスト",
        )


def test_validation_invalid_evidence_quality():
    """不正なevidence_qualityのバリデーションテスト"""
    with pytest.raises(ValueError, match="Invalid evidence_quality"):
        EpisodeSource(
            person_name="テスト",
            person_id="P001ABC12",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テストテキスト",
            evidence_quality="D",  # 不正な品質
        )


def test_to_dict():
    """to_dict変換テスト"""
    source = EpisodeSource(
        person_name="イチロー",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        source_type="wikipedia",
        raw_text="2004年シーズン262安打記録",
        context="年齢31歳時の業績",
    )

    data = source.to_dict()

    assert data["person_name"] == "イチロー"
    assert data["person_id"] == "P001ABC12"
    assert data["person_type"] == "REAL"
    assert data["source_id"].startswith("SRC-")
    assert "collected_at" in data


def test_from_dict():
    """from_dict生成テスト"""
    data = {
        "source_id": "SRC-abc123def456",
        "person_name": "イチロー",
        "person_id": "P001ABC12",
        "person_type": "REAL",
        "source_url": "https://ja.wikipedia.org/wiki/イチロー",
        "source_type": "wikipedia",
        "raw_text": "2004年シーズン262安打記録",
        "context": "年齢31歳時の業績",
        "evidence_quality": "B",
        "verification_status": "verified",
        "collected_at": "2025-12-17T14:00:00",
        "verified_at": "2025-12-17T14:30:00",
    }

    source = EpisodeSource.from_dict(data)

    assert source.person_name == "イチロー"
    assert source.evidence_quality == "B"
    assert source.verification_status == "verified"
    assert isinstance(source.collected_at, datetime)
    assert isinstance(source.verified_at, datetime)


def test_raw_text_length_warning(caplog):
    """raw_text長さ警告テスト"""
    long_text = "x" * 300  # 250文字超

    source = EpisodeSource(
        person_name="テスト",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://example.com",
        source_type="manual",
        raw_text=long_text,
    )

    # 警告ログが出力されることを確認
    assert "exceeds 250 characters" in caplog.text
