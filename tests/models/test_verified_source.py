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
