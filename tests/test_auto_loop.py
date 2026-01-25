#!/usr/bin/env python3
"""
SAGE Turbo Auto Loop テスト

テスト対象:
- scripts/sage/auto_loop.py

テスト観点:
1. 設定の検証
2. 在庫ステータス取得
3. 不足年齢計算
4. 安全性チェック
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.auto_loop import AutoLoopRunner, LoopConfig, LoopStatus


class TestLoopConfig:
    """LoopConfig設定テスト"""

    def test_default_values(self):
        """デフォルト値の確認"""
        config = LoopConfig()
        assert config.target_per_age == 375
        assert config.batch_size == 10000
        assert config.max_error_rate == 0.10
        assert config.dry_run_only is False
        assert config.poll_interval == 60
        assert config.max_wait_time == 7200

    def test_custom_values(self):
        """カスタム値の設定"""
        config = LoopConfig(
            target_per_age=400,
            batch_size=5000,
            max_error_rate=0.05,
            dry_run_only=True,
        )
        assert config.target_per_age == 400
        assert config.batch_size == 5000
        assert config.max_error_rate == 0.05
        assert config.dry_run_only is True


class TestAutoLoopRunner:
    """AutoLoopRunnerテスト"""

    @pytest.fixture
    def runner(self):
        """テスト用ランナー"""
        config = LoopConfig(dry_run_only=True)
        return AutoLoopRunner(config)

    def test_init(self, runner):
        """初期化の確認"""
        assert runner.config.target_per_age == 375
        assert runner.config.dry_run_only is True
        assert runner.status.achieved_ages == 0

    def test_check_safety_all_accepted(self, runner):
        """安全チェック: 全件成功"""
        result = runner.check_safety(accepted=100, rejected=0)
        assert result is True

    def test_check_safety_low_error_rate(self, runner):
        """安全チェック: エラー率が閾値以下"""
        # 5%エラー率
        result = runner.check_safety(accepted=95, rejected=5)
        assert result is True

    def test_check_safety_high_error_rate(self, runner):
        """安全チェック: エラー率が閾値超過"""
        # 15%エラー率
        result = runner.check_safety(accepted=85, rejected=15)
        assert result is False

    def test_check_safety_zero_total(self, runner):
        """安全チェック: 処理件数0"""
        result = runner.check_safety(accepted=0, rejected=0)
        assert result is True  # 続行可能

    def test_get_deficit_ages(self, runner):
        """不足年齢取得テスト"""
        # モックステータス
        mock_status_30 = MagicMock()
        mock_status_30.deficit = 50
        mock_status_50 = MagicMock()
        mock_status_50.deficit = 100
        mock_status_70 = MagicMock()
        mock_status_70.deficit = 0  # 達成済み

        def mock_get_status(age):
            if age == 30:
                return mock_status_30
            elif age == 50:
                return mock_status_50
            elif age == 70:
                return mock_status_70
            else:
                mock_other = MagicMock()
                mock_other.deficit = 0
                return mock_other

        # inventoryオブジェクトのメソッドをモック
        runner.inventory.get_status = mock_get_status
        runner.inventory.refresh = MagicMock()

        deficits = runner.get_deficit_ages()

        # 不足のある年齢のみ返される（不足数降順）
        ages = [age for age, _ in deficits]
        assert 30 in ages
        assert 50 in ages
        assert 70 not in ages

    def test_loop_status_dataclass(self):
        """LoopStatusデータクラスの確認"""
        status = LoopStatus()
        assert status.achieved_ages == 0
        assert status.total_ages == 100
        assert status.total_deficit == 0
        assert status.batch_accepted == 0
        assert status.batch_rejected == 0
        assert status.total_processed == 0


class TestSafetyThresholds:
    """安全性閾値のパラメトリックテスト"""

    @pytest.fixture
    def runner(self):
        config = LoopConfig(max_error_rate=0.10)
        return AutoLoopRunner(config)

    @pytest.mark.parametrize(
        "accepted,rejected,expected",
        [
            (100, 0, True),  # 0%エラー
            (95, 5, True),  # 5%エラー
            (90, 10, True),  # 10%エラー（閾値ちょうど）
            (89, 11, False),  # 11%エラー（閾値超過）
            (50, 50, False),  # 50%エラー
            (0, 100, False),  # 100%エラー
        ],
    )
    def test_error_rate_threshold(self, runner, accepted, rejected, expected):
        """エラー率閾値の境界テスト"""
        result = runner.check_safety(accepted, rejected)
        assert result == expected


class TestIntegration:
    """統合テスト"""

    @pytest.fixture
    def master_csv(self):
        return PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    def test_inventory_manager_integration(self, master_csv):
        """InventoryManagerとの統合確認"""
        if not master_csv.exists():
            pytest.skip("マスターCSVが存在しません")

        config = LoopConfig(target_per_age=375)
        runner = AutoLoopRunner(config)

        # 在庫情報を取得できることを確認
        runner.inventory.refresh()
        summary = runner.inventory.get_summary()

        assert "achieved_ages" in summary
        assert "total_ages" in summary
        assert summary["total_ages"] == 100  # 1-100歳

    def test_deficit_calculation(self, master_csv):
        """不足計算の統合テスト"""
        if not master_csv.exists():
            pytest.skip("マスターCSVが存在しません")

        config = LoopConfig(target_per_age=375)
        runner = AutoLoopRunner(config)

        deficits = runner.get_deficit_ages()

        # 不足年齢があることを確認（未達成の場合）
        # または空リスト（全達成の場合）
        assert isinstance(deficits, list)
        for item in deficits:
            age, deficit = item
            assert 1 <= age <= 100
            assert deficit > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
