"""
tests/test_monitoring_init.py - monitoring/__init__.py ユニットテスト
"""

import pytest


class TestMonitoringPackageImport:
    """monitoringパッケージのインポートテスト"""

    def test_import_kpi_calculator(self):
        """EPUPKPICalculatorがインポートできることを確認"""
        from src.monitoring import EPUPKPICalculator

        assert EPUPKPICalculator is not None

    def test_all_exports(self):
        """__all__のエクスポートを確認"""
        from src import monitoring

        assert hasattr(monitoring, "__all__")
        assert "EPUPKPICalculator" in monitoring.__all__

    def test_kpi_calculator_is_class(self):
        """EPUPKPICalculatorがクラスであることを確認"""
        from src.monitoring import EPUPKPICalculator

        assert isinstance(EPUPKPICalculator, type)
