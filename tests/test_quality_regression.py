#!/usr/bin/env python3
"""
品質回帰テスト

CI/CDで実行される品質回帰テスト。
常体混入・「私は」パターン・冒頭フォーマットの回帰を検出。
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.quality_regression_check import (
    QualityRegressionChecker,
    MASTER_CSV,
    DEFAULT_PLAIN_THRESHOLD,
    DEFAULT_WATASHI_THRESHOLD,
)


class TestQualityRegression:
    """品質回帰テスト

    データ品質の回帰を検出するテスト。
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """テストセットアップ"""
        self.checker = QualityRegressionChecker()
        if MASTER_CSV.exists():
            self.checker.load_episodes()
        else:
            pytest.skip("マスターCSVが存在しません")

    def test_plain_form_below_threshold(self):
        """常体混入率が閾値以下であること"""
        result = self.checker.check_plain_form()

        assert result["violation_rate"] <= DEFAULT_PLAIN_THRESHOLD, (
            f"常体混入率が閾値を超えています: "
            f"{result['violation_rate']}% > {DEFAULT_PLAIN_THRESHOLD}%\n"
            f"違反数: {result['violation_count']}/{result['total_episodes']}"
        )

    def test_watashi_pattern_below_threshold(self):
        """「私は」パターンが閾値以下であること（Phase 13で修正済み: 11168件 → 0件）"""
        result = self.checker.check_watashi_pattern()

        assert result["violation_count"] <= DEFAULT_WATASHI_THRESHOLD, (
            f"「私は」パターン回帰検出: "
            f"{result['violation_count']}件 > {DEFAULT_WATASHI_THRESHOLD}件\n"
            f"サンプル: {result['samples'][:5]}"
        )

    def test_opening_format_compliance(self):
        """冒頭フォーマットが遵守されていること（警告のみ、厳格なゲートではない）"""
        result = self.checker.check_opening_format()
        # 冒頭フォーマットチェックは情報取得のみ（assertなし）
        assert result is not None

    def test_all_checks_pass(self):
        """全チェックがパスすること"""
        results = self.checker.run_all_checks()

        # 必須チェック（plain_form, watashi_pattern）
        assert results["results"]["plain_form"]["passed"], f"常体チェック失敗: {results['results']['plain_form']}"
        assert results["results"]["watashi_pattern"][
            "passed"
        ], f"「私は」チェック失敗: {results['results']['watashi_pattern']}"


class TestQualityRegressionPatterns:
    """パターン検出の単体テスト"""

    @pytest.fixture
    def checker(self):
        """チェッカーインスタンス"""
        return QualityRegressionChecker()

    def test_plain_form_violation_detection(self, checker):
        """常体が違反として検出されること

        注: エピソードは丁寧語で書くべき。常体（だった）が違反対象。
        """
        checker.episodes = [
            {"episode_id": "EP-TEST001", "episode_text": "彼は成功していました。"},  # 丁寧語 → OK
            {"episode_id": "EP-TEST002", "episode_text": "彼は成功だった。"},  # 常体「だった」→ 違反
        ]

        result = checker.check_plain_form()
        assert result["violation_count"] == 1

    def test_watashi_detection(self, checker):
        """「私は」パターンが検出されること"""
        checker.episodes = [
            {"episode_id": "EP-TEST001", "episode_text": "私は成功しました。"},  # 違反
            {"episode_id": "EP-TEST002", "episode_text": "彼は成功しました。"},  # OK
        ]

        result = checker.check_watashi_pattern()
        assert result["violation_count"] == 1

    def test_quote_exclusion(self, checker):
        """引用内は除外されること"""
        # 引用内に常体・「私は」パターンがあるが、引用外は丁寧語
        checker.episodes = [
            {"episode_id": "EP-TEST001", "episode_text": "「私は成功した」と語りました。"},
            {"episode_id": "EP-TEST002", "episode_text": "『私は最高だ』と叫びました。"},
        ]

        # 引用内の「した」「だ」「私は」は除外されるべき
        plain_result = checker.check_plain_form()
        watashi_result = checker.check_watashi_pattern()

        assert plain_result["violation_count"] == 0, "引用内の常体は除外されるべき"
        assert watashi_result["violation_count"] == 0, "引用内の「私は」は除外されるべき"

    def test_opening_format_detection(self, checker):
        """冒頭フォーマット違反が検出されること"""
        checker.episodes = [
            {"episode_id": "EP-TEST001", "episode_text": "あなたと同じ25歳のとき、田中は成功しました。"},
            {"episode_id": "EP-TEST002", "episode_text": "田中は25歳で成功しました。"},  # 違反
        ]

        result = checker.check_opening_format()
        assert result["violation_count"] == 1

    def test_multiple_patterns(self, checker):
        """複数パターンが正しく検出されること

        注: エピソードは丁寧語で書くべき。常体（である/だった）が違反対象。
        """
        checker.episodes = [
            {"episode_id": "EP-TEST001", "episode_text": "彼はそこにいた。常体である。"},  # 常体「である」→ 違反
            {"episode_id": "EP-TEST002", "episode_text": "彼女は偉大だった。"},  # 常体「だった」→ 違反
            {"episode_id": "EP-TEST003", "episode_text": "彼は成功しました。"},  # 丁寧語 → OK
        ]

        result = checker.check_plain_form()
        assert result["violation_count"] == 2

    def test_empty_episodes(self, checker):
        """空のエピソードリストでもエラーにならないこと"""
        checker.episodes = []

        plain_result = checker.check_plain_form()
        watashi_result = checker.check_watashi_pattern()
        opening_result = checker.check_opening_format()

        assert plain_result["violation_count"] == 0
        assert watashi_result["violation_count"] == 0
        assert opening_result["violation_count"] == 0
        assert plain_result["passed"] is True


class TestQualityRegressionThresholds:
    """閾値テスト"""

    def test_plain_threshold_configurable(self):
        """常体閾値が設定可能であること"""
        checker = QualityRegressionChecker(plain_threshold=5.0)
        assert checker.plain_threshold == 5.0

    def test_watashi_threshold_configurable(self):
        """「私は」閾値が設定可能であること"""
        checker = QualityRegressionChecker(watashi_threshold=5)
        assert checker.watashi_threshold == 5

    def test_threshold_pass_boundary(self):
        """閾値境界でパス判定されること

        注: 常体（だった）が違反、丁寧語（でした）はOK
        """
        checker = QualityRegressionChecker(plain_threshold=10.0)
        # 10件が常体（違反）、90件が丁寧語（OK）→ 違反率10%
        checker.episodes = [
            {"episode_id": f"EP-{i:06d}", "episode_text": "彼は成功だった。" if i < 10 else "彼は成功でした。"}
            for i in range(100)
        ]

        result = checker.check_plain_form()
        # 10/100 = 10% = 閾値と同じなのでパス
        assert result["passed"] is True

    def test_threshold_fail_boundary(self):
        """閾値を超えたら失敗すること

        注: 常体（だった）が違反、丁寧語（でした）はOK
        """
        checker = QualityRegressionChecker(plain_threshold=9.0)
        # 10件が常体（違反）、90件が丁寧語（OK）→ 違反率10%
        checker.episodes = [
            {"episode_id": f"EP-{i:06d}", "episode_text": "彼は成功だった。" if i < 10 else "彼は成功でした。"}
            for i in range(100)
        ]

        result = checker.check_plain_form()
        # 10/100 = 10% > 9% なので失敗
        assert result["passed"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
