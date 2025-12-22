"""
tests/test_episode_generation_bridge.py - episode_generation_bridge.py ユニットテスト
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestEpisodeGenerationBridgeInit:
    """EpisodeGenerationBridge初期化テスト"""

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_init(self, mock_generator):
        """初期化"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test-key")

        assert bridge.generator is not None
        assert bridge.episode_validator is None  # 遅延ロード
        mock_generator.assert_called_once_with(api_key="test-key", model="claude-sonnet-4-5")

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_init_custom_model(self, mock_generator):
        """カスタムモデルで初期化"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test-key", model="claude-opus-4")

        mock_generator.assert_called_once_with(api_key="test-key", model="claude-opus-4")


class TestCalculateValidAgeRange:
    """_calculate_valid_age_rangeメソッドテスト"""

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_with_birth_year(self, mock_generator):
        """birth_yearあり"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        person_data = {"person_name": "テスト", "birth_year": 1990, "death_year": None}
        ages = bridge._calculate_valid_age_range(person_data)

        assert 10 in ages
        assert min(ages) == 10

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_with_death_year(self, mock_generator):
        """death_yearあり"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        person_data = {"person_name": "テスト", "birth_year": 1950, "death_year": 2000}
        ages = bridge._calculate_valid_age_range(person_data)

        assert max(ages) == 50  # 2000 - 1950
        assert 10 in ages

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_without_birth_year(self, mock_generator):
        """birth_yearなし（デフォルト範囲）"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        person_data = {"person_name": "テスト"}
        ages = bridge._calculate_valid_age_range(person_data)

        assert ages == list(range(20, 61))

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_invalid_age_range(self, mock_generator):
        """無効な年齢範囲"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        # 9歳で亡くなった場合（min_age=10を満たさない）
        person_data = {"person_name": "テスト", "birth_year": 2000, "death_year": 2005}
        ages = bridge._calculate_valid_age_range(person_data)

        assert ages == []


class TestSelectAges:
    """_select_agesメソッドテスト"""

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_select_ages_fewer_available(self, mock_generator):
        """利用可能な年齢が少ない場合"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        ages = bridge._select_ages([25, 26, 27], 5)
        assert ages == [25, 26, 27]

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_select_ages_distributed(self, mock_generator):
        """均等に分散"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        ages = bridge._select_ages(list(range(20, 60)), 3)

        assert len(ages) == 3
        # 均等に分散されていることを確認
        assert ages[0] < ages[1] < ages[2]

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_select_ages_empty(self, mock_generator):
        """空のリスト"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        ages = bridge._select_ages([], 3)
        assert ages == []


class TestSelectAgesWithPriority:
    """_select_ages_with_priorityメソッドテスト"""

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_priority_20s_30s(self, mock_generator):
        """20-30代を優先"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        ages = bridge._select_ages_with_priority(list(range(10, 70)), 1)

        # 優先度高（20-39歳）から選択
        assert 20 <= ages[0] <= 39

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_priority_multiple(self, mock_generator):
        """複数選択時の優先度"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        ages = bridge._select_ages_with_priority(list(range(10, 70)), 3)

        assert len(ages) == 3

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_priority_only_teens(self, mock_generator):
        """10代のみの場合"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        ages = bridge._select_ages_with_priority(list(range(10, 20)), 2)

        assert all(10 <= a <= 19 for a in ages)


class TestGenerateForPerson:
    """generate_for_personメソッドテスト"""

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_generate_with_preferred_age(self, mock_generator):
        """preferred_age指定時"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        mock_gen_instance = MagicMock()
        mock_generator.return_value = mock_gen_instance
        mock_gen_instance.generate.return_value = {
            "person_name": "テスト",
            "age": 47,
            "episode_text": "テストエピソード",
            "person_id": "P1234567",
        }

        bridge = EpisodeGenerationBridge(api_key="test")

        # 品質ゲートのモック
        with patch.object(bridge, "_load_quality_gates"):
            bridge.episode_validator = MagicMock(return_value=[])
            bridge.fact_checker = MagicMock()
            bridge.fact_checker.check_episode.return_value = MagicMock(violations=[])
            bridge.template_blocker = MagicMock()
            bridge.template_blocker.check_episode.return_value = (False, [])

            person_data = {
                "person_name": "テスト人物",
                "category": "科学・技術",
                "person_type": "REAL",
                "preferred_age": 47,
            }

            episodes = bridge.generate_for_person(person_data, episodes_count=1)

            assert len(episodes) == 1

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_generate_no_valid_ages(self, mock_generator):
        """有効な年齢がない場合"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        bridge = EpisodeGenerationBridge(api_key="test")

        with patch.object(bridge, "_load_quality_gates"):
            bridge.episode_validator = MagicMock()
            bridge.fact_checker = MagicMock()
            bridge.template_blocker = MagicMock()

            person_data = {
                "person_name": "テスト",
                "category": "その他",
                "person_type": "REAL",
                "birth_year": 2020,
                "death_year": 2022,  # 2歳で亡くなった
            }

            episodes = bridge.generate_for_person(person_data, episodes_count=2)

            assert episodes == []


class TestGenerateSingleEpisode:
    """_generate_single_episodeメソッドテスト"""

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_generate_single_success(self, mock_generator):
        """単一エピソード生成成功"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        mock_gen_instance = MagicMock()
        mock_generator.return_value = mock_gen_instance
        mock_gen_instance.generate.return_value = {
            "person_name": "テスト",
            "age": 30,
            "episode_text": "テストエピソード",
        }

        bridge = EpisodeGenerationBridge(api_key="test")

        person_data = {
            "person_name": "テスト",
            "category": "科学・技術",
            "person_type": "REAL",
        }

        episode = bridge._generate_single_episode(person_data, 30)

        assert episode is not None
        assert episode["age"] == 30

    @patch("src.episode_generation_bridge.EpisodeGenerator")
    def test_generate_single_exception(self, mock_generator):
        """単一エピソード生成例外"""
        from src.episode_generation_bridge import EpisodeGenerationBridge

        mock_gen_instance = MagicMock()
        mock_generator.return_value = mock_gen_instance
        mock_gen_instance.generate.side_effect = Exception("API Error")

        bridge = EpisodeGenerationBridge(api_key="test")

        person_data = {
            "person_name": "テスト",
            "category": "科学・技術",
            "person_type": "REAL",
        }

        episode = bridge._generate_single_episode(person_data, 30)

        assert episode is None
