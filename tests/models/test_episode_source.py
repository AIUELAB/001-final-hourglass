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


def test_is_duplicate_file_not_exists(tmp_path):
    """is_duplicate: ファイルが存在しない場合のテスト"""
    csv_path = tmp_path / "nonexistent.csv"
    result = EpisodeSource.is_duplicate("SRC-abc123", csv_path)
    assert result is False


def test_is_duplicate_found(tmp_path):
    """is_duplicate: 重複が見つかる場合のテスト"""
    import pandas as pd

    csv_path = tmp_path / "sources.csv"
    df = pd.DataFrame({"source_id": ["SRC-abc123", "SRC-def456"]})
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    assert EpisodeSource.is_duplicate("SRC-abc123", csv_path) is True
    assert EpisodeSource.is_duplicate("SRC-xyz789", csv_path) is False


def test_save_to_csv_empty_list(tmp_path):
    """save_to_csv: 空リストの場合のテスト"""
    csv_path = tmp_path / "empty.csv"
    EpisodeSource.save_to_csv([], csv_path)

    # ファイルが作成されないことを確認
    assert not csv_path.exists()


def test_save_to_csv_append_mode(tmp_path):
    """save_to_csv: 追記モードのテスト"""
    csv_path = tmp_path / "append.csv"

    # 初回保存
    source1 = EpisodeSource(
        person_name="テスト1",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://example1.com",
        source_type="manual",
        raw_text="テキスト1",
    )
    EpisodeSource.save_to_csv([source1], csv_path)

    # 追記
    source2 = EpisodeSource(
        person_name="テスト2",
        person_id="P002DEF34",
        person_type="FICTIONAL",
        source_url="https://example2.com",
        source_type="wikipedia",
        raw_text="テキスト2",
    )
    EpisodeSource.save_to_csv([source2], csv_path, append=True)

    # 2件あることを確認
    import pandas as pd

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    assert len(df) == 2


def test_save_to_csv_append_dedup(tmp_path):
    """save_to_csv: 追記時の重複排除テスト"""
    csv_path = tmp_path / "dedup.csv"

    source = EpisodeSource(
        person_name="テスト",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://example.com",
        source_type="manual",
        raw_text="テキスト",
    )

    # 同じソースを2回保存
    EpisodeSource.save_to_csv([source], csv_path)
    EpisodeSource.save_to_csv([source], csv_path, append=True)

    # 1件のみであることを確認（重複排除）
    import pandas as pd

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    assert len(df) == 1


def test_load_from_csv_not_exists(tmp_path):
    """load_from_csv: ファイルが存在しない場合のテスト"""
    csv_path = tmp_path / "nonexistent.csv"
    result = EpisodeSource.load_from_csv(csv_path)
    assert result == []


def test_load_from_csv_with_invalid_row(tmp_path, caplog):
    """load_from_csv: 不正な行がある場合のテスト"""
    import pandas as pd

    csv_path = tmp_path / "invalid.csv"
    # 不正なperson_typeを含む行
    df = pd.DataFrame(
        [
            {
                "source_id": "SRC-abc123",
                "person_name": "テスト",
                "person_id": "P001",
                "person_type": "INVALID",  # 不正
                "source_url": "https://example.com",
                "source_type": "manual",
                "raw_text": "テキスト",
                "context": "",
                "evidence_quality": "C",
                "verification_status": "unverified",
                "collected_at": "2025-12-17T14:00:00",
                "verified_at": "",
            }
        ]
    )
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    result = EpisodeSource.load_from_csv(csv_path)

    # 不正な行はスキップされる
    assert len(result) == 0
    assert "Failed to load row" in caplog.text


def test_from_dict_collected_at_none():
    """from_dict: collected_atがNoneの場合のテスト"""
    data = {
        "person_name": "テスト",
        "person_id": "P001ABC12",
        "person_type": "REAL",
        "source_url": "https://example.com",
        "source_type": "manual",
        "raw_text": "テキスト",
        "collected_at": None,  # None
    }

    source = EpisodeSource.from_dict(data)
    assert isinstance(source.collected_at, datetime)


def test_from_dict_without_source_id():
    """from_dict: source_idがない/空の場合のテスト"""
    # source_idが空文字の場合
    data = {
        "source_id": "",
        "person_name": "テスト",
        "person_id": "P001ABC12",
        "person_type": "REAL",
        "source_url": "https://example.com",
        "source_type": "manual",
        "raw_text": "テキスト",
    }

    source = EpisodeSource.from_dict(data)
    # 自動生成されたsource_idを持つ
    assert source.source_id.startswith("SRC-")


def test_validation_missing_person_name():
    """バリデーション: person_nameが空の場合"""
    with pytest.raises(ValueError, match="person_name is required"):
        EpisodeSource(
            person_name="",
            person_id="P001ABC12",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テキスト",
        )


def test_validation_missing_raw_text():
    """バリデーション: raw_textが空の場合"""
    with pytest.raises(ValueError, match="raw_text is required"):
        EpisodeSource(
            person_name="テスト",
            person_id="P001ABC12",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="",
        )


def test_validation_invalid_source_type():
    """バリデーション: 不正なsource_typeの場合"""
    with pytest.raises(ValueError, match="Invalid source_type"):
        EpisodeSource(
            person_name="テスト",
            person_id="P001ABC12",
            person_type="REAL",
            source_url="https://example.com",
            source_type="invalid_type",
            raw_text="テキスト",
        )


def test_validation_invalid_verification_status():
    """バリデーション: 不正なverification_statusの場合"""
    with pytest.raises(ValueError, match="Invalid verification_status"):
        EpisodeSource(
            person_name="テスト",
            person_id="P001ABC12",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テキスト",
            verification_status="pending",  # 不正
        )


def test_to_dict_with_verified_at():
    """to_dict: verified_atがある場合のテスト"""
    from datetime import datetime

    source = EpisodeSource(
        person_name="テスト",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://example.com",
        source_type="manual",
        raw_text="テキスト",
    )
    source.verified_at = datetime(2025, 12, 17, 14, 30, 0)

    data = source.to_dict()
    assert data["verified_at"] == "2025-12-17T14:30:00"
