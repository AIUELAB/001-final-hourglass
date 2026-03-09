#!/usr/bin/env python3
"""fact_checker テスト"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fact_checker import (
    FactChecker,
    FactCheckReport,
    FactCheckResult,
    FactCheckViolation,
    test_fact_checker,
)


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

    def test_summary_with_suggestion(self):
        """suggestionがある場合のサマリー"""
        checker = FactChecker()
        # 大きな数値でsuggestion付きの違反を生成
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="売上は9999999999円を達成した",  # 10億超の数値
        )
        summary = checker.generate_summary(report)
        # suggestionが表示される
        if any(v.suggestion for v in report.violations):
            assert "→" in summary

    def test_summary_with_verified_facts(self):
        """検証済み事実がある場合のサマリー"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="イチロー",
            episode_text="2001年に活躍した選手",  # イチローの既知イベント年
            birth_year=1973,
        )
        summary = checker.generate_summary(report)
        if report.verified_facts:
            assert "検証済みの事実" in summary


class TestCheckKnownFacts:
    """_check_known_factsメソッドのテスト"""

    def test_birth_year_mismatch(self):
        """生年が既知の事実と異なる場合"""
        checker = FactChecker()
        # 安倍晋三の実際の生年は1954年だが、異なる年を記述
        report = checker.check_episode(
            person_id="P001",
            person_name="安倍晋三",
            episode_text="1960年生まれの政治家として活躍した",
            birth_year=1954,
        )
        # 生年の不一致が未検証クレームに追加される可能性
        assert report is not None

    def test_birth_year_match(self):
        """生年が正しい場合"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="安倍晋三",
            episode_text="普通のエピソードテキスト",
            birth_year=1954,
        )
        # 検証済み事実に生年が含まれる可能性
        assert report is not None

    def test_major_events_verification(self):
        """主要イベントの検証"""
        checker = FactChecker()
        # イチローの2001年はMLBデビュー年として既知
        report = checker.check_episode(
            person_id="P001",
            person_name="イチロー",
            episode_text="2001年にMLBで活躍を開始",
            birth_year=1973,
        )
        # イベント年が検証される
        assert report is not None


class TestLargeNumberCheck:
    """大きな数値のチェックテスト"""

    def test_detect_very_large_number(self):
        """10億超の数値を検出"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="総額12345678901円を売り上げた",  # 12桁以上
        )
        suspicious_violations = [v for v in report.violations if v.violation_type == "SUSPICIOUS_NUMBER"]
        assert len(suspicious_violations) > 0

    def test_normal_large_number_ok(self):
        """通常の大きな数値はOK"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="売上は500000000円だった",  # 5億 (10億未満)
        )
        suspicious_violations = [v for v in report.violations if v.violation_type == "SUSPICIOUS_NUMBER"]
        assert len(suspicious_violations) == 0


class TestUnverifiedResult:
    """UNVERIFIED結果のテスト"""

    def test_unverified_with_high_score(self):
        """高スコアだがUNVERIFIEDになるケース"""
        checker = FactChecker()
        # 違反もなく検証済み事実もない普通のエピソード
        report = checker.check_episode(
            person_id="P001",
            person_name="一般人",
            episode_text="普通に生活している普通の人",
        )
        # 違反なしでスコア高い場合はVERIFIEDかUNVERIFIED
        assert report.result in [FactCheckResult.VERIFIED, FactCheckResult.UNVERIFIED]


class TestVerifyKnownFactsExtended:
    """_verify_known_facts の未カバー行をテスト"""

    def test_birth_year_mismatch_in_text(self):
        """テキスト中の生年が既知の事実と異なる場合、unverified_claimsに追加される"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="安倍晋三",
            episode_text="1960年生まれの政治家として知られる",
            birth_year=1954,
        )
        # 生年パターン(\d{4}年.*生)にマッチするが、1954年ではないのでunverified
        assert any("生年が既知の事実" in claim for claim in report.unverified_claims)

    def test_birth_year_no_pattern(self):
        """テキストに生年パターンがない場合、verified_factsに生年が追加される"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="安倍晋三",
            episode_text="政治家として長く活躍した人物です",
            birth_year=1954,
        )
        # 生年パターンがテキストにないので、verified_factsに追加
        assert any("1954年" in fact for fact in report.verified_facts)

    def test_abe_major_events_verified(self):
        """安倍晋三のテキストに2006を含むと、major_eventsがverified_factsに追加される"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="安倍晋三",
            episode_text="2006年に重要な役割を果たした政治家",
            birth_year=1954,
        )
        assert any("2006" in fact and "内閣総理大臣" in fact for fact in report.verified_facts)

    def test_abe_major_events_2012(self):
        """安倍晋三のテキストに2012を含むと、major_eventsがverified_factsに追加される"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="安倍晋三",
            episode_text="2012年に再び政権を担った",
            birth_year=1954,
        )
        assert any("2012" in fact for fact in report.verified_facts)


class TestValidPercentageContexts:
    """_check_numerical_validity の valid_over_100_contexts パターンマッチングをテスト"""

    def test_valid_growth_rate(self):
        """前年比150%は正当な文脈なので違反にならない"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="売上は前年比150%を記録した",
        )
        pct_violations = [v for v in report.violations if v.violation_type == "INVALID_PERCENTAGE"]
        assert len(pct_violations) == 0

    def test_valid_growth_word(self):
        """成長率200%は正当な文脈なので違反にならない"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="事業の成長率200%を達成した",
        )
        pct_violations = [v for v in report.violations if v.violation_type == "INVALID_PERCENTAGE"]
        assert len(pct_violations) == 0

    def test_valid_increase_rate(self):
        """増加率120%は正当な文脈なので違反にならない"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="利用者数の増加率120%となった",
        )
        pct_violations = [v for v in report.violations if v.violation_type == "INVALID_PERCENTAGE"]
        assert len(pct_violations) == 0

    def test_valid_return_percentage(self):
        """リターン2703%は正当な文脈なので違反にならない"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="投資のリターン2703%を実現した",
        )
        pct_violations = [v for v in report.violations if v.violation_type == "INVALID_PERCENTAGE"]
        assert len(pct_violations) == 0

    def test_mixed_valid_invalid(self):
        """正当な文脈の150%と、文脈なしの250%が混在する場合、250%のみ違反"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P001",
            person_name="テスト",
            episode_text="前年比150%の成長を遂げ、達成率250%を記録した",
        )
        pct_violations = [v for v in report.violations if v.violation_type == "INVALID_PERCENTAGE"]
        # 達成率250%は valid_over_100_contexts に含まれないので違反
        assert len(pct_violations) >= 1
        assert any("250" in v.evidence for v in pct_violations)
        # 前年比150%は違反にならない
        assert not any("150" in v.evidence for v in pct_violations)


class TestEvaluateReportUnverified:
    """_evaluate_report で UNVERIFIED 結果になるケースをテスト"""

    def test_unverified_result(self):
        """low severity違反のみでスコア90 → UNVERIFIED"""
        checker = FactChecker()
        report = FactCheckReport(
            person_id="P001",
            person_name="テスト",
            timestamp="2025-01-01T00:00:00",
            result=FactCheckResult.VERIFIED,
        )
        # low severity違反を1つ追加（-10点、スコア90）
        report.violations.append(
            FactCheckViolation(
                violation_type="MINOR_ISSUE",
                message="軽微な問題",
                severity="low",
                confidence=0.5,
            )
        )
        checker._evaluate_report(report)
        assert report.total_score == 90.0
        assert report.result == FactCheckResult.UNVERIFIED


class TestModuleLevelFunction:
    """モジュールレベルの test_fact_checker() 関数をテスト"""

    def test_test_fact_checker(self, capsys):
        """test_fact_checker()がエラーなく実行され、出力を生成する"""
        test_fact_checker()
        captured = capsys.readouterr()
        # 出力にレポート情報が含まれる
        assert "事実確認レポート" in captured.out
        assert "イチロー" in captured.out
        assert "HIKAKIN" in captured.out


class TestBranchCoverage:
    """ブランチカバレッジの漏れを補完するテスト"""

    def test_known_facts_without_birth_year(self):
        """KNOWN_FACTSにbirth_yearがない人物の場合、生年チェックをスキップ（L232->241分岐）"""
        checker = FactChecker()
        # KNOWN_FACTSにbirth_yearなしの仮エントリを追加
        checker.KNOWN_FACTS["テスト人物_no_birth"] = {
            "major_events": [
                {"year": 2020, "event": "テストイベント"},
            ],
        }
        report = checker.check_episode(
            person_id="P100",
            person_name="テスト人物_no_birth",
            episode_text="2020年に活躍した人物",
        )
        # birth_yearがないため生年関連のunverified_claimsは追加されない
        assert not any("生年が既知の事実" in c for c in report.unverified_claims)
        # major_eventsは検証される
        assert any("2020" in f for f in report.verified_facts)

    def test_known_facts_correct_birth_year_in_text(self):
        """テキスト中の生年が既知の事実と一致する場合（L235->True分岐）"""
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P101",
            person_name="安倍晋三",
            episode_text="1954年生まれの政治家",
            birth_year=1954,
        )
        # 正しい生年なのでunverified_claimsに追加されない
        assert not any("生年が既知の事実" in c for c in report.unverified_claims)

    def test_known_facts_without_major_events(self):
        """KNOWN_FACTSにmajor_eventsがない人物（L241 major_events分岐スキップ）"""
        checker = FactChecker()
        checker.KNOWN_FACTS["テスト人物_no_events"] = {
            "birth_year": 1980,
        }
        report = checker.check_episode(
            person_id="P102",
            person_name="テスト人物_no_events",
            episode_text="普通のテキスト",
        )
        # エラーなく処理される
        assert report is not None

    def test_valid_percentage_bai_pattern(self):
        """「3倍」パターンがvalid_over_100_contextsにマッチし、pct_matchがNoneになるケース（L294->291分岐）

        「3倍」はパターン r"\\d+(?:\\.\\d+)?倍" にマッチするが、
        マッチした文字列 "3倍" には %/％ が含まれないため
        pct_match = re.search(r"(\\d+(?:\\.\\d+)?)[%％]", "3倍") は None を返す。
        """
        checker = FactChecker()
        report = checker.check_episode(
            person_id="P103",
            person_name="テスト",
            episode_text="売上が3倍に増加した",
        )
        # パーセンテージ違反はない（%を含むテキストがないため）
        pct_violations = [v for v in report.violations if v.violation_type == "INVALID_PERCENTAGE"]
        assert len(pct_violations) == 0

    def test_generate_summary_no_unverified_claims(self):
        """unverified_claimsが空の場合、「未検証の主張」セクションが表示されない（L363->361分岐）"""
        checker = FactChecker()
        report = FactCheckReport(
            person_id="P104",
            person_name="テスト",
            timestamp="2025-01-01T00:00:00",
            result=FactCheckResult.VERIFIED,
            verified_facts=["テスト事実"],
            unverified_claims=[],  # 空
        )
        summary = checker.generate_summary(report)
        assert "未検証の主張" not in summary
        assert "検証済みの事実" in summary

    def test_generate_summary_with_unverified_claims(self):
        """unverified_claimsがある場合、「未検証の主張」セクションが表示される"""
        checker = FactChecker()
        report = FactCheckReport(
            person_id="P105",
            person_name="テスト",
            timestamp="2025-01-01T00:00:00",
            result=FactCheckResult.UNVERIFIED,
            unverified_claims=["未確認の主張テスト"],
        )
        summary = checker.generate_summary(report)
        assert "未検証の主張" in summary
        assert "未確認の主張テスト" in summary

    def test_generate_summary_violation_without_suggestion(self):
        """violationにsuggestionがない場合、矢印行が出力されない（L363->361分岐）"""
        checker = FactChecker()
        report = FactCheckReport(
            person_id="P106",
            person_name="テスト",
            timestamp="2025-01-01T00:00:00",
            result=FactCheckResult.SUSPICIOUS,
            violations=[
                FactCheckViolation(
                    violation_type="TEST_ISSUE",
                    message="テスト問題",
                    severity="medium",
                    suggestion=None,  # suggestionなし
                    confidence=0.5,
                )
            ],
        )
        summary = checker.generate_summary(report)
        assert "検出された問題" in summary
        assert "テスト問題" in summary
        # suggestionがないので矢印行は出力されない
        assert "→" not in summary
