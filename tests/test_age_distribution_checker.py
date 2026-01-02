#!/usr/bin/env python3
"""
年齢分布チェッカーのテスト

【テスト観点表】

■ 等価分割
1. 正常パターン: 自然な年齢分布（17, 28, 43, 62など）
2. 5の倍数偏重: 80%以上が5の倍数
3. 等間隔パターン: 全て等間隔（20, 25, 30など）
4. 全て5の倍数: 最高リスクパターン
5. エピソード少数: 2件未満はスキップ

■ 境界値
1. 5の倍数率: 79% (OK) vs 80% (WARNING)
2. 等間隔件数: 2件 (OK) vs 3件 (WARNING)
3. 新規追加: 追加前OK→追加後WARNING
"""

import pytest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.validators.age_distribution_checker import (
    AgeDistributionChecker,
    CheckResult,
)


class TestAgeDistributionChecker:
    """年齢分布チェッカーのテスト"""

    def setup_method(self):
        """テストごとにチェッカーを初期化"""
        self.checker = AgeDistributionChecker(strict=False)
        self.strict_checker = AgeDistributionChecker(strict=True)

    # ============================================================
    # 正常パターン
    # ============================================================

    def test_natural_distribution_ok(self):
        """自然な年齢分布は OK"""
        ages = [17.0, 28.0, 43.0, 62.0]
        result = self.checker.check_person_distribution("P001", ages)
        assert result.result == CheckResult.OK
        assert not result.is_suspicious

    def test_single_episode_ok(self):
        """エピソード1件はスキップ"""
        ages = [25.0]
        result = self.checker.check_person_distribution("P001", ages)
        assert result.result == CheckResult.OK
        assert not result.is_suspicious

    def test_two_episodes_ok(self):
        """エピソード2件でも等間隔判定はしない"""
        ages = [20.0, 25.0]  # 5歳刻みだが2件なので等間隔警告なし
        result = self.checker.check_person_distribution("P001", ages)
        # 5の倍数は100%だが2件では警告レベルは低い
        # ただし80%以上の5の倍数偏重は検出される
        assert result.result == CheckResult.WARNING  # 5の倍数100%

    # ============================================================
    # 5の倍数偏重
    # ============================================================

    def test_five_multiple_under_threshold_ok(self):
        """5の倍数が79%以下は OK"""
        # 5件中3件(60%)が5の倍数
        ages = [20.0, 25.0, 30.0, 28.0, 33.0]
        result = self.checker.check_person_distribution("P001", ages)
        # 60% < 80%なのでOK
        assert result.result == CheckResult.OK

    def test_five_multiple_at_threshold_warning(self):
        """5の倍数が80%で WARNING"""
        # 5件中4件(80%)が5の倍数
        ages = [20.0, 25.0, 30.0, 35.0, 28.0]
        result = self.checker.check_person_distribution("P001", ages)
        assert result.result == CheckResult.WARNING
        assert result.is_suspicious
        assert "5の倍数偏重" in result.message

    def test_five_multiple_above_threshold_warning(self):
        """5の倍数が80%超で WARNING"""
        ages = [20.0, 25.0, 30.0, 35.0, 40.0]  # 100%
        result = self.checker.check_person_distribution("P001", ages)
        assert result.result == CheckResult.WARNING
        assert result.is_suspicious

    # ============================================================
    # 等間隔パターン
    # ============================================================

    def test_uniform_interval_three_episodes_warning(self):
        """3件の等間隔で WARNING"""
        ages = [20.0, 25.0, 30.0]  # 5歳刻み
        result = self.checker.check_person_distribution("P001", ages)
        assert result.result == CheckResult.WARNING
        assert result.is_suspicious
        assert "等間隔パターン" in result.message or "5の倍数" in result.message

    def test_uniform_interval_four_episodes_warning(self):
        """4件の等間隔で WARNING"""
        ages = [30.0, 35.0, 40.0, 45.0]  # 5歳刻み
        result = self.checker.check_person_distribution("P001", ages)
        assert result.result == CheckResult.WARNING
        assert result.is_suspicious

    def test_non_five_uniform_interval_warning(self):
        """5以外の等間隔でも WARNING"""
        ages = [20.0, 27.0, 34.0]  # 7歳刻み
        result = self.checker.check_person_distribution("P001", ages)
        assert result.result == CheckResult.WARNING
        assert "等間隔パターン" in result.message

    # ============================================================
    # 全て5の倍数（最高リスク）
    # ============================================================

    def test_all_five_multiples_warning(self):
        """全て5の倍数は最高リスク WARNING"""
        ages = [20.0, 25.0, 30.0]
        result = self.checker.check_person_distribution("P001", ages)
        assert result.result == CheckResult.WARNING
        assert result.is_suspicious
        assert "全て5の倍数" in result.message

    # ============================================================
    # 新規追加チェック
    # ============================================================

    def test_new_episode_makes_suspicious(self):
        """追加で疑わしくなるケース"""
        existing = [20.0, 25.0]  # 現状2件
        new_age = 30.0  # 追加すると3件の等間隔
        result = self.checker.check_new_episode("P001", new_age, existing)
        assert result.is_suspicious
        assert "等間隔パターン" in result.message or "5の倍数" in result.message

    def test_new_episode_keeps_ok(self):
        """追加してもOKのケース"""
        existing = [22.0, 37.0]
        new_age = 51.0  # 自然な追加
        result = self.checker.check_new_episode("P001", new_age, existing)
        assert result.result == CheckResult.OK

    # ============================================================
    # 厳格モード
    # ============================================================

    def test_strict_mode_blocks(self):
        """厳格モードでは BLOCK"""
        ages = [20.0, 25.0, 30.0]
        result = self.strict_checker.check_person_distribution("P001", ages)
        assert result.result == CheckResult.BLOCK
        assert result.is_suspicious

    # ============================================================
    # データベーススキャン
    # ============================================================

    def test_scan_database(self):
        """DBスキャンのテスト"""
        episodes_by_person = {
            "P001": [17.0, 28.0, 43.0],  # OK
            "P002": [20.0, 25.0, 30.0],  # 疑わしい
            "P003": [22.0, 38.0],  # OK
        }
        suspicious = self.checker.scan_database(episodes_by_person)
        assert len(suspicious) == 1
        assert any("P002" in s.message for s in suspicious)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
