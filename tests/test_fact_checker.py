#!/usr/bin/env python3
"""fact_checker テスト"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fact_checker import FactChecker, FactCheckReport, FactCheckResult, FactCheckViolation


class TestFactCheckResult:
    """FactCheckResultのテスト"""

    def test_verified(self):
        assert FactCheckResult.VERIFIED.value == "verified"

    def test_unverified(self):
        assert FactCheckResult.UNVERIFIED.value == "unverified"

    def test_incorrect(self):
        assert FactCheckResult.INCORRECT.value == "incorrect"

    def test_suspicious(self):
        assert FactCheckResult.SUSPICIOUS.value == "suspicious"

    def test_partial(self):
        assert FactCheckResult.PARTIAL.value == "partial"

    def test_count(self):
        assert len(FactCheckResult) == 5


class TestFactCheckViolation:
    """FactCheckViolationのテスト"""

    def test_init_minimal(self):
        """最小構成"""
        violation = FactCheckViolation(violation_type="date_error", message="日付が誤っています", severity="high")
        assert violation.violation_type == "date_error"
        assert violation.severity == "high"
        assert violation.evidence is None
        assert violation.confidence == 0.0

    def test_init_full(self):
        """フル構成"""
        violation = FactCheckViolation(
            violation_type="fact_error",
            message="事実と異なります",
            severity="critical",
            evidence="Wikipedia参照",
            suggestion="修正が必要",
            confidence=0.95,
        )
        assert violation.evidence == "Wikipedia参照"
        assert violation.confidence == 0.95


class TestFactCheckReport:
    """FactCheckReportのテスト"""

    def test_init_minimal(self):
        """最小構成"""
        report = FactCheckReport(
            person_id="person_001",
            person_name="テスト太郎",
            timestamp="2025-01-01T00:00:00",
            result=FactCheckResult.VERIFIED,
        )
        assert report.person_id == "person_001"
        assert report.person_name == "テスト太郎"
        assert report.result == FactCheckResult.VERIFIED
        assert report.violations == []
        assert report.total_score == 100.0

    def test_with_violations(self):
        """違反付き"""
        violation = FactCheckViolation(violation_type="error", message="エラー", severity="medium")
        report = FactCheckReport(
            person_id="p1",
            person_name="テスト",
            timestamp="2025-01-01",
            result=FactCheckResult.INCORRECT,
            violations=[violation],
            total_score=50.0,
        )
        assert len(report.violations) == 1
        assert report.total_score == 50.0


class TestFactChecker:
    """FactCheckerのテスト"""

    def test_init(self):
        """初期化テスト"""
        checker = FactChecker()
        assert checker.KNOWN_FACTS is not None
        assert "安倍晋三" in checker.KNOWN_FACTS
        assert "イチロー" in checker.KNOWN_FACTS

    def test_known_facts_structure(self):
        """既知の事実データ構造"""
        checker = FactChecker()
        abe_data = checker.KNOWN_FACTS["安倍晋三"]
        assert "birth_year" in abe_data
        assert abe_data["birth_year"] == 1954

        ichiro_data = checker.KNOWN_FACTS["イチロー"]
        assert ichiro_data["real_name"] == "鈴木一朗"
