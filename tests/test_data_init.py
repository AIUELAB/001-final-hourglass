"""
tests/test_data_init.py - data/__init__.py ユニットテスト
"""

import pytest


class TestDataPackageImport:
    """dataパッケージのインポートテスト"""

    def test_import_master_updater(self):
        """MasterUpdaterがインポートできることを確認"""
        from src.data import MasterUpdater

        assert MasterUpdater is not None

    def test_all_exports(self):
        """__all__のエクスポートを確認"""
        from src import data

        assert hasattr(data, "__all__")
        assert "MasterUpdater" in data.__all__

    def test_master_updater_is_class(self):
        """MasterUpdaterがクラスであることを確認"""
        from src.data import MasterUpdater

        assert isinstance(MasterUpdater, type)
