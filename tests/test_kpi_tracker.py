"""
KPI Tracker Tests - KPIトラッカーのテスト
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.kpi_tracker import (
    KPIAlert,
    KPISnapshot,
    KPITargets,
    KPITracker,
    check_kpi_alerts,
    generate_weekly_report,
)


class TestKPITargets:
    """KPITargets のテスト"""

    def test_default_values(self):
        """デフォルト値の確認"""
        targets = KPITargets()
        assert targets.llm_calls_per_episode == 1.3
        assert targets.tokens_per_episode == 1500
        assert targets.acceptance_rate == 0.90
        assert targets.avg_super_total == 400000
        assert targets.retry_rate == 0.20
        assert targets.fallback_rate == 0.10

    def test_custom_values(self):
        """カスタム値の設定"""
        targets = KPITargets(acceptance_rate=0.95, avg_super_total=500000)
        assert targets.acceptance_rate == 0.95
        assert targets.avg_super_total == 500000


class TestKPISnapshot:
    """KPISnapshot のテスト"""

    def test_to_dict(self):
        """辞書変換"""
        snapshot = KPISnapshot(
            timestamp="2026-01-07T12:00:00",
            period_start="2026-01-01T00:00:00",
            period_end="2026-01-07T12:00:00",
            total_episodes=10000,
            new_episodes=500,
            acceptance_rate=0.85,
            avg_super_total=450000,
        )
        d = snapshot.to_dict()
        assert d["total_episodes"] == 10000
        assert d["new_episodes"] == 500
        assert d["acceptance_rate"] == 0.85
        assert d["avg_super_total"] == 450000


class TestKPIAlert:
    """KPIAlert のテスト"""

    def test_alert_creation(self):
        """アラート作成"""
        alert = KPIAlert(
            metric="acceptance_rate",
            current_value=0.70,
            target_value=0.90,
            severity="critical",
            message="採用率が目標を下回っています",
        )
        assert alert.metric == "acceptance_rate"
        assert alert.current_value == 0.70
        assert alert.severity == "critical"


class TestKPITracker:
    """KPITracker のテスト"""

    @pytest.fixture
    def tracker(self):
        """テスト用トラッカー"""
        return KPITracker()

    def test_init(self, tracker):
        """初期化"""
        assert tracker.targets is not None
        assert tracker.targets.acceptance_rate == 0.90

    def test_take_snapshot(self, tracker):
        """スナップショット取得"""
        snapshot = tracker.take_snapshot(period_days=7)
        assert snapshot.timestamp is not None
        assert snapshot.total_episodes >= 0
        assert snapshot.achieved_ages >= 0

    def test_check_alerts_good(self, tracker):
        """アラートなし（良好な状態）"""
        snapshot = KPISnapshot(
            timestamp="2026-01-07T12:00:00",
            period_start="2026-01-01T00:00:00",
            period_end="2026-01-07T12:00:00",
            acceptance_rate=0.95,  # 目標超え
            avg_super_total=450000,  # 目標超え
            llm_calls=100,
            retry_count=10,  # 10%
        )
        alerts = tracker.check_alerts(snapshot)
        assert len(alerts) == 0

    def test_check_alerts_warning(self, tracker):
        """警告アラート"""
        snapshot = KPISnapshot(
            timestamp="2026-01-07T12:00:00",
            period_start="2026-01-01T00:00:00",
            period_end="2026-01-07T12:00:00",
            acceptance_rate=0.85,  # 目標未達（90%）
            avg_super_total=450000,
            llm_calls=100,
            retry_count=10,
        )
        alerts = tracker.check_alerts(snapshot)
        assert len(alerts) == 1
        assert alerts[0].metric == "acceptance_rate"
        assert alerts[0].severity == "warning"

    def test_check_alerts_critical(self, tracker):
        """重大アラート"""
        snapshot = KPISnapshot(
            timestamp="2026-01-07T12:00:00",
            period_start="2026-01-01T00:00:00",
            period_end="2026-01-07T12:00:00",
            acceptance_rate=0.50,  # 目標の80%未満
            avg_super_total=450000,
            llm_calls=100,
            retry_count=10,
        )
        alerts = tracker.check_alerts(snapshot)
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        assert len(critical_alerts) >= 1

    def test_generate_report(self, tracker):
        """レポート生成"""
        snapshot = KPISnapshot(
            timestamp="2026-01-07T12:00:00",
            period_start="2026-01-01T00:00:00",
            period_end="2026-01-07T12:00:00",
            total_episodes=10000,
            new_episodes=500,
            acceptance_rate=0.90,
            avg_super_total=450000,
            achieved_ages=7,
            total_upper_episodes=10000,
            category_distribution={"科学": 1000, "芸術": 800},
            age_distribution={"20s": 3000, "30s": 2500},
        )
        report = tracker.generate_report(snapshot)
        assert "# SAGE 週次KPIレポート" in report
        assert "10,000" in report
        assert "90.0%" in report


class TestConvenienceFunctions:
    """便利関数のテスト"""

    def test_check_kpi_alerts(self):
        """check_kpi_alerts関数"""
        alerts = check_kpi_alerts()
        assert isinstance(alerts, list)
        for a in alerts:
            assert "metric" in a
            assert "severity" in a
            assert "message" in a


class TestKPITrackerIntegration:
    """統合テスト"""

    def test_full_workflow(self):
        """フルワークフロー"""
        tracker = KPITracker()

        # スナップショット取得
        snapshot = tracker.take_snapshot(period_days=7)
        assert snapshot.total_episodes > 0

        # アラートチェック
        alerts = tracker.check_alerts(snapshot)
        assert isinstance(alerts, list)

        # レポート生成
        report = tracker.generate_report(snapshot)
        assert len(report) > 100

    def test_snapshot_contains_inventory_info(self):
        """スナップショットに在庫情報が含まれる"""
        tracker = KPITracker()
        snapshot = tracker.take_snapshot()
        assert snapshot.achieved_ages >= 0
        assert snapshot.total_upper_episodes >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
