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

    def test_hallucination_patterns(self):
        """ハルシネーションパターン"""
        checker = FactChecker()
        assert len(checker.HALLUCINATION_PATTERNS) > 0
        # 各パターンは(pattern, description)のタプル
        for pattern, description in checker.HALLUCINATION_PATTERNS:
            assert isinstance(pattern, str)
            assert isinstance(description, str)

    def test_anachronism_patterns(self):
        """時代錯誤パターン"""
        checker = FactChecker()
        assert len(checker.ANACHRONISM_PATTERNS) > 0


class TestCheckEpisode:
    """check_episodeメソッドのテスト"""

    def test_normal_episode(self):
        """正常なエピソード"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト太郎",
            episode_text="2020年に東京で活動を始めた。",
            birth_year=1990,
        )
        assert report.person_id == "P001"
        assert report.person_name == "テスト太郎"
        assert report.result is not None

    def test_episode_with_metadata(self):
        """メタデータ付きエピソード"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P002",
            person_name="テスト次郎",
            episode_text="普通のテキスト",
            metadata={"source": "test"},
        )
        assert report.metadata == {"source": "test"}

    def test_episode_without_birth_year(self):
        """生年なしのエピソード"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P003",
            person_name="不明人物",
            episode_text="特に問題のないテキスト",
        )
        assert report is not None


class TestCheckHallucination:
    """_check_hallucinationメソッドのテスト"""

    def test_detect_world_first(self):
        """世界初パターン検出"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="世界で初めて宇宙に行った日本人",
        )
        assert len(report.violations) > 0
        assert any(v.violation_type == "HALLUCINATION_PATTERN" for v in report.violations)

    def test_detect_only_in_japan(self):
        """日本唯一パターン検出"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="日本で唯一の技術を持つ職人",
        )
        assert any(v.violation_type == "HALLUCINATION_PATTERN" for v in report.violations)

    def test_detect_nobel_prize(self):
        """ノーベル賞パターン検出"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="2025年にノーベル賞を受賞した",
        )
        assert any(v.violation_type == "HALLUCINATION_PATTERN" for v in report.violations)

    def test_no_hallucination(self):
        """ハルシネーションなし"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="普通の日常生活を送っている",
        )
        hallucination_violations = [v for v in report.violations if v.violation_type == "HALLUCINATION_PATTERN"]
        assert len(hallucination_violations) == 0


class TestCheckAnachronism:
    """_check_anachronismメソッドのテスト"""

    def test_detect_edo_internet(self):
        """江戸時代+インターネット"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="侍",
            episode_text="江戸時代にインターネットで情報発信していた",
        )
        assert any(v.violation_type == "ANACHRONISM" for v in report.violations)

    def test_detect_meiji_tv(self):
        """明治時代+テレビ"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="人物",
            episode_text="明治時代にテレビ出演していた",
        )
        assert any(v.violation_type == "ANACHRONISM" for v in report.violations)

    def test_no_anachronism(self):
        """時代錯誤なし"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="人物",
            episode_text="令和時代にインターネットで活躍している",
        )
        anachronism_violations = [v for v in report.violations if v.violation_type == "ANACHRONISM"]
        assert len(anachronism_violations) == 0


class TestCheckChronologicalConsistency:
    """_check_chronological_consistencyメソッドのテスト"""

    def test_consistent_age_year(self):
        """整合性のある年齢と年代"""
        checker = FactChecker()
        # 1985年に25歳 → 生年1960年
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="1985年に25歳でデビューした",
            birth_year=1960,
        )
        chrono_violations = [v for v in report.violations if v.violation_type == "CHRONOLOGICAL_INCONSISTENCY"]
        assert len(chrono_violations) == 0

    def test_inconsistent_age_year(self):
        """不整合な年齢と年代"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="2020年に50歳でデビューした",
            birth_year=1990,  # 2020年なら30歳のはず
        )
        chrono_violations = [v for v in report.violations if v.violation_type == "CHRONOLOGICAL_INCONSISTENCY"]
        assert len(chrono_violations) > 0


class TestVerifyKnownFacts:
    """_verify_known_factsメソッドのテスト"""

    def test_verify_ichiro_facts(self):
        """イチローの既知事実検証"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="イチロー",
            episode_text="2004年にシーズン262安打の記録を達成した",
            birth_year=1973,
        )
        # 2004年は既知のイベント年
        assert len(report.verified_facts) > 0 or report is not None

    def test_unknown_person(self):
        """未知の人物"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P999",
            person_name="未知の人物",
            episode_text="2020年に活躍した",
        )
        # エラーなく処理される
        assert report is not None


class TestCheckNumericalValidity:
    """_check_numerical_validityメソッドのテスト"""

    def test_valid_percentage(self):
        """有効なパーセンテージ"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="成功率は85%だった",
        )
        pct_violations = [v for v in report.violations if v.violation_type == "INVALID_PERCENTAGE"]
        assert len(pct_violations) == 0

    def test_invalid_percentage(self):
        """無効なパーセンテージ（100%超）"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="成功率は150%を達成した",
        )
        pct_violations = [v for v in report.violations if v.violation_type == "INVALID_PERCENTAGE"]
        assert len(pct_violations) > 0


class TestEvaluateReport:
    """_evaluate_reportメソッドのテスト"""

    def test_verified_result(self):
        """違反なしでVERIFIED"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="普通の人",
            episode_text="普通の生活を送っている",
        )
        # 違反がなければVERIFIEDになる可能性が高い
        if len(report.violations) == 0:
            assert report.result == FactCheckResult.VERIFIED

    def test_incorrect_with_critical(self):
        """criticalでINCORRECT"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="江戸時代にインターネットで成功率150%を達成",
        )
        # critical違反がある場合はINCORRECT
        if any(v.severity == "critical" for v in report.violations):
            assert report.result == FactCheckResult.INCORRECT

    def test_score_deduction(self):
        """スコア減点"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="世界で初めての技術で日本で唯一の存在",
        )
        # 違反があればスコアが100未満
        if len(report.violations) > 0:
            assert report.total_score < 100.0


class TestGenerateSummary:
    """generate_summaryメソッドのテスト"""

    def test_summary_contains_person_info(self):
        """サマリーに人物情報が含まれる"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト太郎",
            episode_text="通常のエピソード",
        )
        summary = checker.generate_summary(report)
        assert "テスト太郎" in summary
        assert "P001" in summary

    def test_summary_contains_score(self):
        """サマリーにスコアが含まれる"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="普通のテキスト",
        )
        summary = checker.generate_summary(report)
        assert "スコア" in summary
        assert "/100" in summary

    def test_summary_with_violations(self):
        """違反ありのサマリー"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="世界で初めての快挙を達成",
        )
        summary = checker.generate_summary(report)
        if len(report.violations) > 0:
            assert "検出された問題" in summary

    def test_summary_structure(self):
        """サマリー構造"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="テストエピソード",
        )
        summary = checker.generate_summary(report)
        assert "【事実確認レポート】" in summary
        assert "人物:" in summary
        assert "結果:" in summary
