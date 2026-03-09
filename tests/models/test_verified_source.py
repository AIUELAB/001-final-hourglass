"""
VerifiedSourceモデルのテスト
"""

import pytest
from datetime import datetime

from src.models.verified_source import VerifiedSource


def test_verified_source_creation():
    """VerifiedSourceの基本的な生成テスト"""
    source = VerifiedSource(
        person_name="イチロー",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        source_type="wikipedia",
        raw_text="2004年シーズン262安打記録",
        context="年齢31歳時の業績",
        evidence_quality="B",
        verification_status="verified",
    )

    assert source.person_name == "イチロー"
    assert source.evidence_quality == "B"
    assert source.verification_status == "verified"
    assert source.verifier_notes is None


def test_auto_judge_quality_a():
    """A品質自動判定テスト（政府公式サイト）"""
    source = VerifiedSource(
        person_name="テスト",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://www.mext.go.jp/test",  # .go.jp
        source_type="manual",
        raw_text="テストテキスト",
    )

    # 自動判定でA品質になることを確認
    assert source.evidence_quality == "A"


def test_auto_judge_quality_b():
    """B品質自動判定テスト（Wikipedia）"""
    source = VerifiedSource(
        person_name="テスト",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://ja.wikipedia.org/wiki/test",
        source_type="wikipedia",
        raw_text="テストテキスト",
    )

    # 自動判定でB品質になることを確認
    assert source.evidence_quality == "B"


def test_auto_judge_quality_c():
    """C品質自動判定テスト（その他ドメイン）"""
    source = VerifiedSource(
        person_name="テスト",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://example.com/test",
        source_type="manual",
        raw_text="テストテキスト",
    )

    # 自動判定でC品質になることを確認
    assert source.evidence_quality == "C"


def test_mark_verified():
    """mark_verified機能テスト"""
    source = VerifiedSource(
        person_name="イチロー",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        source_type="wikipedia",
        raw_text="2004年シーズン262安打記録",
    )

    source.mark_verified("品質A確認済み")

    assert source.verification_status == "verified"
    assert source.verified_at is not None
    assert source.verifier_notes == "品質A確認済み"


def test_mark_rejected():
    """mark_rejected機能テスト"""
    source = VerifiedSource(
        person_name="テスト",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://example.com/test",
        source_type="manual",
        raw_text="テストテキスト",
    )

    source.mark_rejected("センシティブキーワード検出")

    assert source.verification_status == "rejected"
    assert source.verified_at is not None
    assert source.verifier_notes == "センシティブキーワード検出"


def test_filter_by_quality():
    """品質フィルタリングテスト"""
    sources = [
        VerifiedSource(
            person_name="人物A",
            person_id="P001ABC12",
            person_type="REAL",
            source_url="https://www.mext.go.jp/a",
            source_type="manual",
            raw_text="テストA",
            evidence_quality="A",
        ),
        VerifiedSource(
            person_name="人物B",
            person_id="P002ABC12",
            person_type="REAL",
            source_url="https://ja.wikipedia.org/wiki/b",
            source_type="wikipedia",
            raw_text="テストB",
            evidence_quality="B",
        ),
        VerifiedSource(
            person_name="人物C",
            person_id="P003ABC12",
            person_type="REAL",
            source_url="https://example.com/c",
            source_type="manual",
            raw_text="テストC",
            evidence_quality="C",
        ),
    ]

    # B以上でフィルタ
    filtered = VerifiedSource.filter_by_quality(sources, min_quality="B")
    assert len(filtered) == 2
    assert all(s.evidence_quality in ["A", "B"] for s in filtered)


def test_filter_verified():
    """検証済みフィルタリングテスト"""
    sources = [
        VerifiedSource(
            person_name="人物A",
            person_id="P001ABC12",
            person_type="REAL",
            source_url="https://example.com/a",
            source_type="manual",
            raw_text="テストA",
            verification_status="verified",
        ),
        VerifiedSource(
            person_name="人物B",
            person_id="P002ABC12",
            person_type="REAL",
            source_url="https://example.com/b",
            source_type="manual",
            raw_text="テストB",
            verification_status="unverified",
        ),
    ]

    # 検証済みのみ抽出
    verified = VerifiedSource.filter_verified(sources)
    assert len(verified) == 1
    assert verified[0].person_name == "人物A"


# ============================================================================
# 追加テスト: 未カバー行の網羅
# ============================================================================


def _make_verified_source(**kwargs):
    """テスト用ヘルパー: 有効なVerifiedSourceを作成"""
    defaults = {
        "person_name": "テスト太郎",
        "person_id": "P001ABC12",
        "person_type": "REAL",
        "source_url": "https://example.com/test",
        "source_type": "manual",
        "raw_text": "テストテキスト",
    }
    defaults.update(kwargs)
    return VerifiedSource(**defaults)


class TestVerifiedSourceToDict:
    """to_dict() メソッドのテスト（VerifiedSource固有のフィールド）"""

    def test_includes_verifier_notes(self):
        """verifier_notesが辞書に含まれる"""
        source = _make_verified_source(verifier_notes="検証メモ")
        data = source.to_dict()
        assert data["verifier_notes"] == "検証メモ"

    def test_verifier_notes_none_becomes_empty_string(self):
        """verifier_notesがNoneの場合は空文字になる"""
        source = _make_verified_source()
        data = source.to_dict()
        assert data["verifier_notes"] == ""

    def test_includes_parent_fields(self):
        """親クラス(EpisodeSource)のフィールドも含む"""
        source = _make_verified_source()
        data = source.to_dict()
        assert "source_id" in data
        assert "person_name" in data
        assert "person_id" in data
        assert "source_url" in data
        assert "collected_at" in data


class TestVerifiedSourceFromDict:
    """from_dict() クラスメソッドのテスト"""

    def test_creates_from_dict(self):
        """辞書からVerifiedSourceインスタンスを作成"""
        data = {
            "person_name": "テスト太郎",
            "person_id": "P001ABC12",
            "person_type": "REAL",
            "source_url": "https://example.com/test",
            "source_type": "manual",
            "raw_text": "テストテキスト",
            "evidence_quality": "B",
            "verification_status": "verified",
            "verifier_notes": "検証完了",
        }
        source = VerifiedSource.from_dict(data)
        assert source.person_name == "テスト太郎"
        assert source.evidence_quality == "B"
        assert source.verifier_notes == "検証完了"

    def test_from_dict_with_collected_at_string(self):
        """collected_atが文字列の場合にdatetimeに変換"""
        data = {
            "person_name": "テスト太郎",
            "person_id": "P001ABC12",
            "person_type": "REAL",
            "source_url": "https://example.com/test",
            "source_type": "manual",
            "raw_text": "テストテキスト",
            "collected_at": "2025-06-15T10:00:00",
        }
        source = VerifiedSource.from_dict(data)
        assert isinstance(source.collected_at, datetime)
        assert source.collected_at.year == 2025

    def test_from_dict_with_collected_at_none(self):
        """collected_atがNoneの場合は現在時刻を使用"""
        data = {
            "person_name": "テスト太郎",
            "person_id": "P001ABC12",
            "person_type": "REAL",
            "source_url": "https://example.com/test",
            "source_type": "manual",
            "raw_text": "テストテキスト",
            "collected_at": None,
        }
        source = VerifiedSource.from_dict(data)
        assert isinstance(source.collected_at, datetime)

    def test_from_dict_with_verified_at_string(self):
        """verified_atが文字列の場合にdatetimeに変換"""
        data = {
            "person_name": "テスト太郎",
            "person_id": "P001ABC12",
            "person_type": "REAL",
            "source_url": "https://example.com/test",
            "source_type": "manual",
            "raw_text": "テストテキスト",
            "verified_at": "2025-06-15T14:30:00",
        }
        source = VerifiedSource.from_dict(data)
        assert isinstance(source.verified_at, datetime)
        assert source.verified_at.hour == 14

    def test_from_dict_with_verified_at_empty_string(self):
        """verified_atが空文字の場合はNone"""
        data = {
            "person_name": "テスト太郎",
            "person_id": "P001ABC12",
            "person_type": "REAL",
            "source_url": "https://example.com/test",
            "source_type": "manual",
            "raw_text": "テストテキスト",
            "verified_at": "",
        }
        source = VerifiedSource.from_dict(data)
        assert source.verified_at is None

    def test_from_dict_with_source_id(self):
        """source_idが指定されている場合は上書き"""
        data = {
            "source_id": "SRC-custom12345678",
            "person_name": "テスト太郎",
            "person_id": "P001ABC12",
            "person_type": "REAL",
            "source_url": "https://example.com/test",
            "source_type": "manual",
            "raw_text": "テストテキスト",
        }
        source = VerifiedSource.from_dict(data)
        assert source.source_id == "SRC-custom12345678"

    def test_from_dict_without_source_id(self):
        """source_idがない場合は自動生成"""
        data = {
            "person_name": "テスト太郎",
            "person_id": "P001ABC12",
            "person_type": "REAL",
            "source_url": "https://example.com/test",
            "source_type": "manual",
            "raw_text": "テストテキスト",
        }
        source = VerifiedSource.from_dict(data)
        assert source.source_id.startswith("SRC-")

    def test_from_dict_default_values(self):
        """オプションフィールドのデフォルト値"""
        data = {
            "person_name": "テスト太郎",
            "person_id": "P001ABC12",
            "person_type": "REAL",
            "source_url": "https://example.com/test",
            "source_type": "manual",
            "raw_text": "テストテキスト",
        }
        source = VerifiedSource.from_dict(data)
        assert source.evidence_quality == "C"
        assert source.verification_status == "unverified"
        assert source.verifier_notes is None


class TestVerifiedSourceSaveToCSV:
    """save_to_csv() 静的メソッドのテスト"""

    def test_saves_sources(self, tmp_path):
        """ソースをCSVに保存"""
        sources = [_make_verified_source()]
        csv_path = tmp_path / "verified.csv"
        VerifiedSource.save_to_csv(sources, csv_path)
        assert csv_path.exists()

    def test_empty_list_does_nothing(self, tmp_path):
        """空リストの場合はファイルを作成しない"""
        csv_path = tmp_path / "empty.csv"
        VerifiedSource.save_to_csv([], csv_path)
        assert not csv_path.exists()

    def test_append_mode(self, tmp_path):
        """追記モードで保存"""
        import pandas as pd

        csv_path = tmp_path / "append.csv"

        # 1件目保存
        source1 = _make_verified_source(
            person_name="人物1",
            source_url="https://example.com/1",
        )
        VerifiedSource.save_to_csv([source1], csv_path)

        # 2件目追記
        source2 = _make_verified_source(
            person_name="人物2",
            source_url="https://example.com/2",
        )
        VerifiedSource.save_to_csv([source2], csv_path, append=True)

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        assert len(df) == 2

    def test_append_deduplication(self, tmp_path):
        """追記時にsource_idで重複排除"""
        import pandas as pd

        csv_path = tmp_path / "dedup.csv"
        source = _make_verified_source()

        # 同一ソースを2回保存
        VerifiedSource.save_to_csv([source], csv_path)
        VerifiedSource.save_to_csv([source], csv_path, append=True)

        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        assert len(df) == 1

    def test_creates_parent_directory(self, tmp_path):
        """親ディレクトリを自動作成"""
        csv_path = tmp_path / "subdir" / "verified.csv"
        sources = [_make_verified_source()]
        VerifiedSource.save_to_csv(sources, csv_path)
        assert csv_path.exists()


class TestVerifiedSourceLoadFromCSV:
    """load_from_csv() 静的メソッドのテスト"""

    def test_loads_sources(self, tmp_path):
        """CSVからソースを読み込み"""
        csv_path = tmp_path / "verified.csv"

        # 保存
        source = _make_verified_source(evidence_quality="A")
        VerifiedSource.save_to_csv([source], csv_path)

        # 読み込み
        loaded = VerifiedSource.load_from_csv(csv_path)
        assert len(loaded) == 1
        assert loaded[0].person_name == "テスト太郎"

    def test_returns_empty_for_nonexistent_file(self, tmp_path):
        """存在しないファイルの場合は空リスト"""
        csv_path = tmp_path / "nonexistent.csv"
        loaded = VerifiedSource.load_from_csv(csv_path)
        assert loaded == []

    def test_handles_invalid_rows(self, tmp_path):
        """不正な行をスキップして読み込み"""
        import pandas as pd

        csv_path = tmp_path / "invalid.csv"
        df = pd.DataFrame(
            [
                {
                    "source_id": "SRC-valid123456789",
                    "person_name": "有効な人物",
                    "person_id": "P001",
                    "person_type": "REAL",
                    "source_url": "https://example.com/valid",
                    "source_type": "manual",
                    "raw_text": "有効なテキスト",
                    "context": "",
                    "evidence_quality": "C",
                    "verification_status": "unverified",
                    "collected_at": "2025-06-15T10:00:00",
                    "verified_at": "",
                    "verifier_notes": "",
                },
                {
                    "source_id": "SRC-invalid123456",
                    "person_name": "",
                    "person_id": "",
                    "person_type": "INVALID",
                    "source_url": "not-a-url",
                    "source_type": "unknown",
                    "raw_text": "",
                    "context": "",
                    "evidence_quality": "X",
                    "verification_status": "bad",
                    "collected_at": "",
                    "verified_at": "",
                    "verifier_notes": "",
                },
            ]
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        loaded = VerifiedSource.load_from_csv(csv_path)
        # 有効な行のみ読み込まれる
        assert len(loaded) == 1


class TestVerifiedSourceMarkVerifiedNoNotes:
    """mark_verified() のノートなし呼び出しテスト"""

    def test_mark_verified_without_notes(self):
        """ノートなしでmark_verifiedを呼ぶ"""
        source = _make_verified_source()
        source.mark_verified()

        assert source.verification_status == "verified"
        assert source.verified_at is not None
        assert source.verifier_notes is None


class TestAutoJudgeQualityAdditional:
    """auto_judge_quality() の追加ドメインテスト"""

    def test_academic_domain_ac_jp(self):
        """学術機関(.ac.jp)はA品質"""
        source = _make_verified_source(
            source_url="https://www.u-tokyo.ac.jp/research",
        )
        assert source.evidence_quality == "A"

    def test_edu_domain(self):
        """教育機関(.edu)はA品質"""
        source = _make_verified_source(
            source_url="https://www.mit.edu/research",
        )
        assert source.evidence_quality == "A"

    def test_ndl_domain(self):
        """国会図書館(ndl.go.jp)はA品質"""
        source = _make_verified_source(
            source_url="https://ndl.go.jp/collection/test",
        )
        assert source.evidence_quality == "A"

    def test_britannica_domain(self):
        """ブリタニカ(britannica.com)はB品質"""
        source = _make_verified_source(
            source_url="https://www.britannica.com/topic/test",
        )
        assert source.evidence_quality == "B"

    def test_no_auto_judge_when_quality_already_set(self):
        """evidence_qualityがC以外で設定済みの場合、自動判定しない"""
        source = _make_verified_source(
            source_url="https://www.mext.go.jp/test",
            evidence_quality="B",
            verification_status="verified",
        )
        # Bで設定されているので、自動判定されない（条件: C and unverified）
        assert source.evidence_quality == "B"

    def test_no_auto_judge_when_already_verified(self):
        """verification_statusがverifiedの場合、自動判定しない"""
        source = _make_verified_source(
            source_url="https://www.mext.go.jp/test",
            evidence_quality="C",
            verification_status="verified",
        )
        # verified状態なので自動判定されない
        assert source.evidence_quality == "C"
