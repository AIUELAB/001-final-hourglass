#!/usr/bin/env python3
"""models/verified_source.py ユニットテスト"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from src.models.verified_source import VerifiedSource


class TestVerifiedSourceInit:
    """VerifiedSource初期化テスト"""

    def test_basic_init(self):
        """基本的な初期化"""
        source = VerifiedSource(
            person_name="テスト太郎",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com/test",
            source_type="manual",
            raw_text="テストテキスト",
        )
        assert source.person_name == "テスト太郎"
        assert source.person_id == "P001"
        assert source.source_id.startswith("SRC-")

    def test_verifier_notes_default(self):
        """verifier_notesデフォルトはNone"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
        )
        assert source.verifier_notes is None

    def test_verifier_notes_custom(self):
        """カスタムverifier_notes"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
            verifier_notes="検証メモ",
        )
        assert source.verifier_notes == "検証メモ"


class TestAutoJudgeQuality:
    """auto_judge_quality品質判定テスト"""

    def test_quality_a_go_jp(self):
        """政府公式（.go.jp）はA判定"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://www.kantei.go.jp/test",
            source_type="manual",
            raw_text="テスト",
            evidence_quality="C",
            verification_status="unverified",
        )
        result = source.auto_judge_quality()
        assert result == "A"

    def test_quality_a_ac_jp(self):
        """学術機関（.ac.jp）はA判定"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://www.u-tokyo.ac.jp/test",
            source_type="manual",
            raw_text="テスト",
        )
        result = source.auto_judge_quality()
        assert result == "A"

    def test_quality_a_edu(self):
        """教育機関（.edu）はA判定"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://www.harvard.edu/test",
            source_type="manual",
            raw_text="テスト",
        )
        result = source.auto_judge_quality()
        assert result == "A"

    def test_quality_a_ndl(self):
        """国会図書館はA判定"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://ndl.go.jp/test",
            source_type="manual",
            raw_text="テスト",
        )
        result = source.auto_judge_quality()
        assert result == "A"

    def test_quality_b_wikipedia(self):
        """WikipediaはB判定"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://ja.wikipedia.org/wiki/Test",
            source_type="wikipedia",
            raw_text="テスト",
        )
        result = source.auto_judge_quality()
        assert result == "B"

    def test_quality_b_britannica(self):
        """BritannicaはB判定"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://www.britannica.com/topic/Test",
            source_type="manual",
            raw_text="テスト",
        )
        result = source.auto_judge_quality()
        assert result == "B"

    def test_quality_c_default(self):
        """その他はC判定"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com/test",
            source_type="manual",
            raw_text="テスト",
        )
        result = source.auto_judge_quality()
        assert result == "C"

    def test_quality_c_blog(self):
        """ブログはC判定"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://blog.example.com/article",
            source_type="manual",
            raw_text="テスト",
        )
        result = source.auto_judge_quality()
        assert result == "C"


class TestMarkVerified:
    """mark_verifiedメソッドテスト"""

    def test_mark_verified_basic(self):
        """基本的な検証マーク"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
        )
        source.mark_verified()
        assert source.verification_status == "verified"
        assert source.verified_at is not None

    def test_mark_verified_with_notes(self):
        """ノート付き検証マーク"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
        )
        source.mark_verified("品質A確認済み")
        assert source.verification_status == "verified"
        assert source.verifier_notes == "品質A確認済み"

    def test_mark_verified_timestamp(self):
        """検証タイムスタンプ設定"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
        )
        before = datetime.now()
        source.mark_verified()
        after = datetime.now()
        assert before <= source.verified_at <= after


class TestMarkRejected:
    """mark_rejectedメソッドテスト"""

    def test_mark_rejected_basic(self):
        """基本的な却下マーク"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
        )
        source.mark_rejected("センシティブキーワード検出")
        assert source.verification_status == "rejected"
        assert source.verifier_notes == "センシティブキーワード検出"

    def test_mark_rejected_timestamp(self):
        """却下タイムスタンプ設定"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
        )
        before = datetime.now()
        source.mark_rejected("却下理由")
        after = datetime.now()
        assert before <= source.verified_at <= after


class TestToDict:
    """to_dictメソッドテスト"""

    def test_to_dict_basic(self):
        """基本的な辞書変換"""
        source = VerifiedSource(
            person_name="テスト太郎",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テストテキスト",
        )
        data = source.to_dict()
        assert data["person_name"] == "テスト太郎"
        assert data["person_id"] == "P001"
        assert "verifier_notes" in data

    def test_to_dict_with_verifier_notes(self):
        """verifier_notes付き辞書変換"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
            verifier_notes="検証メモ",
        )
        data = source.to_dict()
        assert data["verifier_notes"] == "検証メモ"

    def test_to_dict_none_verifier_notes(self):
        """verifier_notesがNoneの場合は空文字列"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
        )
        data = source.to_dict()
        assert data["verifier_notes"] == ""


class TestFromDict:
    """from_dictメソッドテスト"""

    def test_from_dict_basic(self):
        """基本的な辞書からの生成"""
        data = {
            "person_name": "テスト太郎",
            "person_id": "P001",
            "person_type": "REAL",
            "source_url": "https://example.com",
            "source_type": "manual",
            "raw_text": "テストテキスト",
        }
        source = VerifiedSource.from_dict(data)
        assert source.person_name == "テスト太郎"
        assert source.person_id == "P001"

    def test_from_dict_with_datetime_string(self):
        """日時文字列からの生成"""
        data = {
            "person_name": "テスト",
            "person_id": "P001",
            "person_type": "REAL",
            "source_url": "https://example.com",
            "source_type": "manual",
            "raw_text": "テスト",
            "collected_at": "2024-01-15T10:30:00",
            "verified_at": "2024-01-16T12:00:00",
        }
        source = VerifiedSource.from_dict(data)
        assert isinstance(source.collected_at, datetime)
        assert isinstance(source.verified_at, datetime)

    def test_from_dict_with_empty_verified_at(self):
        """空のverified_at"""
        data = {
            "person_name": "テスト",
            "person_id": "P001",
            "person_type": "REAL",
            "source_url": "https://example.com",
            "source_type": "manual",
            "raw_text": "テスト",
            "verified_at": "",
        }
        source = VerifiedSource.from_dict(data)
        assert source.verified_at is None

    def test_from_dict_with_source_id(self):
        """source_id指定"""
        data = {
            "person_name": "テスト",
            "person_id": "P001",
            "person_type": "REAL",
            "source_url": "https://example.com",
            "source_type": "manual",
            "raw_text": "テスト",
            "source_id": "SRC-custom12345678",
        }
        source = VerifiedSource.from_dict(data)
        assert source.source_id == "SRC-custom12345678"

    def test_from_dict_with_verifier_notes(self):
        """verifier_notes付き"""
        data = {
            "person_name": "テスト",
            "person_id": "P001",
            "person_type": "REAL",
            "source_url": "https://example.com",
            "source_type": "manual",
            "raw_text": "テスト",
            "verifier_notes": "カスタムノート",
        }
        source = VerifiedSource.from_dict(data)
        assert source.verifier_notes == "カスタムノート"


class TestFilterByQuality:
    """filter_by_qualityメソッドテスト"""

    def create_source(self, quality: str) -> VerifiedSource:
        """テスト用ソース作成"""
        return VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
            evidence_quality=quality,
            verification_status="verified",
        )

    def test_filter_quality_a_only(self):
        """Aのみフィルタ"""
        sources = [
            self.create_source("A"),
            self.create_source("B"),
            self.create_source("C"),
        ]
        filtered = VerifiedSource.filter_by_quality(sources, min_quality="A")
        assert len(filtered) == 1
        assert all(s.evidence_quality == "A" for s in filtered)

    def test_filter_quality_b_and_above(self):
        """B以上フィルタ"""
        sources = [
            self.create_source("A"),
            self.create_source("B"),
            self.create_source("C"),
        ]
        filtered = VerifiedSource.filter_by_quality(sources, min_quality="B")
        assert len(filtered) == 2

    def test_filter_quality_c_all(self):
        """C以上（全件）フィルタ"""
        sources = [
            self.create_source("A"),
            self.create_source("B"),
            self.create_source("C"),
        ]
        filtered = VerifiedSource.filter_by_quality(sources, min_quality="C")
        assert len(filtered) == 3

    def test_filter_empty_list(self):
        """空リストフィルタ"""
        filtered = VerifiedSource.filter_by_quality([], min_quality="A")
        assert filtered == []


class TestFilterVerified:
    """filter_verifiedメソッドテスト"""

    def create_source(self, status: str) -> VerifiedSource:
        """テスト用ソース作成"""
        return VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
            verification_status=status,
        )

    def test_filter_verified_only(self):
        """検証済みのみフィルタ"""
        sources = [
            self.create_source("verified"),
            self.create_source("unverified"),
            self.create_source("rejected"),
        ]
        filtered = VerifiedSource.filter_verified(sources)
        assert len(filtered) == 1
        assert filtered[0].verification_status == "verified"

    def test_filter_no_verified(self):
        """検証済みなし"""
        sources = [
            self.create_source("unverified"),
            self.create_source("rejected"),
        ]
        filtered = VerifiedSource.filter_verified(sources)
        assert len(filtered) == 0

    def test_filter_all_verified(self):
        """全て検証済み"""
        sources = [
            self.create_source("verified"),
            self.create_source("verified"),
        ]
        filtered = VerifiedSource.filter_verified(sources)
        assert len(filtered) == 2


class TestSaveAndLoadCSV:
    """CSV保存・読み込みテスト"""

    def create_source(self, name: str) -> VerifiedSource:
        """テスト用ソース作成"""
        return VerifiedSource(
            person_name=name,
            person_id=f"P{name}",
            person_type="REAL",
            source_url=f"https://example.com/{name}",
            source_type="manual",
            raw_text=f"テキスト{name}",
        )

    def test_save_to_csv_basic(self):
        """基本的なCSV保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test.csv"
            sources = [self.create_source("1"), self.create_source("2")]
            VerifiedSource.save_to_csv(sources, csv_path)
            assert csv_path.exists()

    def test_save_to_csv_empty_list(self):
        """空リストの保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test.csv"
            VerifiedSource.save_to_csv([], csv_path)
            # 空リストの場合は何も保存しない
            assert not csv_path.exists()

    def test_save_to_csv_creates_parent_dir(self):
        """親ディレクトリ自動作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "subdir" / "test.csv"
            sources = [self.create_source("1")]
            VerifiedSource.save_to_csv(sources, csv_path)
            assert csv_path.exists()

    def test_load_from_csv_basic(self):
        """基本的なCSV読み込み"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test.csv"
            sources = [self.create_source("1"), self.create_source("2")]
            VerifiedSource.save_to_csv(sources, csv_path)

            loaded = VerifiedSource.load_from_csv(csv_path)
            assert len(loaded) == 2

    def test_load_from_csv_nonexistent(self):
        """存在しないファイルの読み込み"""
        csv_path = Path("/nonexistent/path/test.csv")
        loaded = VerifiedSource.load_from_csv(csv_path)
        assert loaded == []

    def test_save_to_csv_append_mode(self):
        """追記モード"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test.csv"

            # 最初の保存
            sources1 = [self.create_source("1")]
            VerifiedSource.save_to_csv(sources1, csv_path)

            # 追記
            sources2 = [self.create_source("2")]
            VerifiedSource.save_to_csv(sources2, csv_path, append=True)

            loaded = VerifiedSource.load_from_csv(csv_path)
            assert len(loaded) == 2

    def test_save_to_csv_append_deduplicate(self):
        """追記時の重複排除"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test.csv"

            # 同じソースを2回保存
            source = self.create_source("1")
            VerifiedSource.save_to_csv([source], csv_path)
            VerifiedSource.save_to_csv([source], csv_path, append=True)

            loaded = VerifiedSource.load_from_csv(csv_path)
            # 重複排除されて1件のみ
            assert len(loaded) == 1


class TestRoundTrip:
    """往復変換テスト（to_dict -> from_dict）"""

    def test_roundtrip_basic(self):
        """基本的な往復変換"""
        original = VerifiedSource(
            person_name="テスト太郎",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com/test",
            source_type="manual",
            raw_text="テストテキスト",
            evidence_quality="B",
            verification_status="verified",
            verifier_notes="検証済みメモ",
        )

        data = original.to_dict()
        restored = VerifiedSource.from_dict(data)

        assert restored.person_name == original.person_name
        assert restored.person_id == original.person_id
        assert restored.source_url == original.source_url
        assert restored.evidence_quality == original.evidence_quality
        assert restored.verifier_notes == original.verifier_notes

    def test_roundtrip_csv(self):
        """CSV経由の往復"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test.csv"

            original = VerifiedSource(
                person_name="テスト花子",
                person_id="P002",
                person_type="FICTIONAL",
                source_url="https://example.com/hanako",
                source_type="wikidata",
                raw_text="花子のテキスト",
                verifier_notes="テストノート",
            )

            VerifiedSource.save_to_csv([original], csv_path)
            loaded = VerifiedSource.load_from_csv(csv_path)

            assert len(loaded) == 1
            restored = loaded[0]
            assert restored.person_name == original.person_name
            assert restored.source_id == original.source_id


class TestEdgeCases:
    """エッジケーステスト"""

    def test_auto_quality_with_trailing_slash(self):
        """末尾スラッシュ付きURL"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://www.mext.go.jp/",
            source_type="manual",
            raw_text="テスト",
        )
        assert source.auto_judge_quality() == "A"

    def test_quality_with_subdomain(self):
        """サブドメイン付きURL"""
        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://www.lib.u-tokyo.ac.jp/collection",
            source_type="manual",
            raw_text="テスト",
        )
        assert source.auto_judge_quality() == "A"

    def test_from_dict_none_collected_at(self):
        """collected_atがNoneの場合"""
        data = {
            "person_name": "テスト",
            "person_id": "P001",
            "person_type": "REAL",
            "source_url": "https://example.com",
            "source_type": "manual",
            "raw_text": "テスト",
            "collected_at": None,
        }
        source = VerifiedSource.from_dict(data)
        assert isinstance(source.collected_at, datetime)

    def test_inheritance_from_episode_source(self):
        """EpisodeSourceからの継承確認"""
        from src.models.episode_source import EpisodeSource

        source = VerifiedSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
        )
        assert isinstance(source, EpisodeSource)


class TestEpisodeSourceValidation:
    """EpisodeSource バリデーションテスト"""

    def test_missing_person_id(self):
        """person_id未設定でエラー"""
        from src.models.episode_source import EpisodeSource

        with pytest.raises(ValueError, match="person_id is required"):
            EpisodeSource(
                person_name="テスト",
                person_id="",
                person_type="REAL",
                source_url="https://example.com",
                source_type="manual",
                raw_text="テスト",
            )

    def test_missing_source_url(self):
        """source_url未設定でエラー"""
        from src.models.episode_source import EpisodeSource

        with pytest.raises(ValueError, match="source_url is required"):
            EpisodeSource(
                person_name="テスト",
                person_id="P001",
                person_type="REAL",
                source_url="",
                source_type="manual",
                raw_text="テスト",
            )

    def test_missing_raw_text(self):
        """raw_text未設定でエラー"""
        from src.models.episode_source import EpisodeSource

        with pytest.raises(ValueError, match="raw_text is required"):
            EpisodeSource(
                person_name="テスト",
                person_id="P001",
                person_type="REAL",
                source_url="https://example.com",
                source_type="manual",
                raw_text="",
            )

    def test_invalid_verification_status(self):
        """無効なverification_statusでエラー"""
        from src.models.episode_source import EpisodeSource

        with pytest.raises(ValueError, match="Invalid verification_status"):
            EpisodeSource(
                person_name="テスト",
                person_id="P001",
                person_type="REAL",
                source_url="https://example.com",
                source_type="manual",
                raw_text="テスト",
                verification_status="invalid_status",
            )

    def test_invalid_source_type(self):
        """無効なsource_typeでエラー"""
        from src.models.episode_source import EpisodeSource

        with pytest.raises(ValueError, match="Invalid source_type"):
            EpisodeSource(
                person_name="テスト",
                person_id="P001",
                person_type="REAL",
                source_url="https://example.com",
                source_type="invalid_type",
                raw_text="テスト",
            )

    def test_auto_generate_source_id(self):
        """source_id未指定時に自動生成"""
        from src.models.episode_source import EpisodeSource

        source = EpisodeSource(
            person_name="テスト",
            person_id="P001",
            person_type="REAL",
            source_url="https://example.com",
            source_type="manual",
            raw_text="テスト",
        )
        assert source.source_id.startswith("SRC-")
        assert len(source.source_id) == 20  # "SRC-" + 16文字

    def test_raw_text_long_warning(self, caplog):
        """raw_textが250文字超で警告"""
        from src.models.episode_source import EpisodeSource
        import logging

        long_text = "あ" * 300  # 250文字超
        with caplog.at_level(logging.WARNING):
            source = EpisodeSource(
                person_name="テスト",
                person_id="P001",
                person_type="REAL",
                source_url="https://example.com",
                source_type="manual",
                raw_text=long_text,
            )
        assert "exceeds 250 characters" in caplog.text
