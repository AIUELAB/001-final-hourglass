"""
InventoryManager Tests - 年齢別在庫管理のテスト

SAGE vNext Phase 1: InventoryManagerの単体テスト
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.inventory_manager import (
    AgeStatus,
    GenerationMode,
    InventoryConfig,
    InventoryManager,
    ReplacementTarget,
)


class TestInventoryConfig:
    """InventoryConfig のテスト"""

    def test_default_values(self):
        """デフォルト値の確認"""
        config = InventoryConfig()
        assert config.target_per_age == 365
        assert config.min_factual_density == 7.0
        assert config.min_generation_quality == 8.0
        assert config.replacement_threshold == 0.05
        assert config.min_age == 0
        assert config.max_age == 120

    def test_custom_values(self):
        """カスタム値の設定"""
        config = InventoryConfig(target_per_age=100, replacement_threshold=0.10)
        assert config.target_per_age == 100
        assert config.replacement_threshold == 0.10


class TestAgeStatus:
    """AgeStatus のテスト"""

    def test_to_dict(self):
        """辞書変換"""
        status = AgeStatus(
            age=30,
            total_count=500,
            upper_count=400,
            target=365,
            achieved=True,
            mode=GenerationMode.STOP,
            min_upper_score=450000.0,
            deficit=-35,
        )
        d = status.to_dict()
        assert d["age"] == 30
        assert d["achieved"] is True
        assert d["mode"] == "stop"
        assert d["deficit"] == -35


class TestInventoryManager:
    """InventoryManager のテスト"""

    @pytest.fixture
    def manager(self):
        """テスト用マネージャー"""
        return InventoryManager()

    def test_init(self, manager):
        """初期化"""
        assert manager.config.target_per_age == 365
        assert manager._inventory == {}

    def test_refresh(self, manager):
        """在庫更新"""
        manager.refresh()
        assert len(manager._inventory) > 0
        assert manager._last_update is not None

    def test_get_status(self, manager):
        """ステータス取得"""
        status = manager.get_status(30)
        assert status is not None
        assert status.age == 30
        assert isinstance(status.mode, GenerationMode)

    def test_get_status_invalid_age(self, manager):
        """無効な年齢"""
        status = manager.get_status(200)  # 範囲外
        assert status is None

    def test_should_generate_unachieved(self, manager):
        """未達成年齢は生成可"""
        manager.refresh()
        # 未達成年齢を探す
        for age, status in manager._inventory.items():
            if not status.achieved:
                assert manager.should_generate(age) is True
                break

    def test_should_generate_achieved(self, manager):
        """達成年齢は生成停止"""
        manager.refresh()
        # 達成年齢を探す
        for age, status in manager._inventory.items():
            if status.achieved:
                assert manager.should_generate(age) is False
                break

    def test_should_replace_unachieved(self, manager):
        """未達成年齢は置換しない"""
        manager.refresh()
        for age, status in manager._inventory.items():
            if not status.achieved:
                assert manager.should_replace(age, 999999) is False
                break

    def test_should_replace_high_score(self, manager):
        """高スコアなら置換"""
        manager.refresh()
        for age, status in manager._inventory.items():
            if status.achieved and status.min_upper_score > 0:
                # 5%以上高いスコア
                high_score = status.min_upper_score * 1.10
                assert manager.should_replace(age, high_score) is True
                break

    def test_should_replace_low_score(self, manager):
        """低スコアなら置換しない"""
        manager.refresh()
        for age, status in manager._inventory.items():
            if status.achieved and status.min_upper_score > 0:
                # 同じスコア
                same_score = status.min_upper_score
                assert manager.should_replace(age, same_score) is False
                break

    def test_get_summary(self, manager):
        """サマリー取得"""
        summary = manager.get_summary()
        assert "total_ages" in summary
        assert "achieved_ages" in summary
        assert "achievement_rate" in summary
        assert "total_upper_episodes" in summary

    def test_get_priority_ages(self, manager):
        """優先年齢リスト"""
        priority = manager.get_priority_ages(limit=5)
        assert isinstance(priority, list)
        assert len(priority) <= 5
        # 全て未達成年齢
        for age in priority:
            status = manager.get_status(age)
            assert status is not None
            assert status.achieved is False


class TestGenerationMode:
    """GenerationMode のテスト"""

    def test_enum_values(self):
        """Enum値の確認"""
        assert GenerationMode.GENERATE.value == "generate"
        assert GenerationMode.STOP.value == "stop"
        assert GenerationMode.REPLACE.value == "replace"


class TestUpperLevelCriteria:
    """上位レベル判定基準のテスト"""

    def test_upper_level_definition(self):
        """上位レベル定義: factual_density>=7 AND 生成品質>=8"""
        manager = InventoryManager()
        config = manager.config
        assert config.min_factual_density == 7.0
        assert config.min_generation_quality == 8.0


class TestPhase4ReplacementMode:
    """Phase 4: 置換モードのテスト"""

    @pytest.fixture
    def manager(self):
        """テスト用マネージャー"""
        return InventoryManager()

    def test_is_replacement_mode_achieved(self, manager):
        """達成年齢は置換モード"""
        manager.refresh()
        for age, status in manager._inventory.items():
            if status.achieved:
                assert manager.is_replacement_mode(age) is True
                assert status.mode == GenerationMode.REPLACE
                break

    def test_is_replacement_mode_unachieved(self, manager):
        """未達成年齢は置換モードではない"""
        manager.refresh()
        for age, status in manager._inventory.items():
            if not status.achieved:
                assert manager.is_replacement_mode(age) is False
                assert status.mode == GenerationMode.GENERATE
                break

    def test_replacement_threshold_calculated(self, manager):
        """置換閾値が計算されている"""
        manager.refresh()
        for age, status in manager._inventory.items():
            if status.achieved and status.min_upper_score > 0:
                # 閾値は最低スコアの1.05倍
                expected = status.min_upper_score * 1.05
                assert abs(status.replacement_threshold - expected) < 0.01
                break

    def test_get_replacement_target_returns_dataclass(self, manager):
        """get_replacement_target は ReplacementTarget を返す"""
        manager.refresh()
        for age, status in manager._inventory.items():
            if status.achieved:
                target = manager.get_replacement_target(age)
                if target is not None:
                    assert isinstance(target, ReplacementTarget)
                    assert target.episode_id
                    assert target.person_id
                    assert target.age == age
                    assert target.score >= 0
                break

    def test_get_replacement_target_unachieved_returns_none(self, manager):
        """未達成年齢は置換対象なし"""
        manager.refresh()
        for age, status in manager._inventory.items():
            if not status.achieved:
                target = manager.get_replacement_target(age)
                assert target is None
                break


class TestReplacementTarget:
    """ReplacementTarget のテスト"""

    def test_dataclass_creation(self):
        """データクラス作成"""
        target = ReplacementTarget(
            episode_id="EP-000000001",
            person_id="P123456",
            person_name="テスト太郎",
            age=30,
            score=500000.0,
        )
        assert target.episode_id == "EP-000000001"
        assert target.person_id == "P123456"
        assert target.person_name == "テスト太郎"
        assert target.age == 30
        assert target.score == 500000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
