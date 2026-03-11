"""
SensitiveFilter テストモジュール

sensitive_filter.py の単体テストを提供します。
"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml

from src.sensitive_filter import SensitiveFilter
from src.source_adapters.base import PersonCandidate


@pytest.fixture
def mock_config():
    """テスト用の設定"""
    return {
        "sensitive_categories": ["犯罪者", "テロリスト", "詐欺師"],
        "sensitive_keywords": ["逮捕", "殺人", "詐欺"],
        "review_required_categories": ["政治家", "宗教家"],
        "allow_list": ["マンデラ"],
    }


@pytest.fixture
def filter_with_mock_config(mock_config, tmp_path):
    """モック設定を使用したフィルター"""
    config_file = tmp_path / "sensitive_keywords.yaml"
    config_file.write_text(yaml.dump(mock_config), encoding="utf-8")
    return SensitiveFilter(config_path=str(config_file))


class TestSensitiveFilterInit:
    """初期化テスト"""

    def test_init_with_custom_config(self, mock_config, tmp_path):
        """カスタム設定ファイルで初期化できる"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml.dump(mock_config), encoding="utf-8")

        filter_obj = SensitiveFilter(config_path=str(config_file))
        assert filter_obj.config is not None
        assert "sensitive_categories" in filter_obj.config

    def test_init_loads_config_correctly(self, filter_with_mock_config, mock_config):
        """設定が正しくロードされる"""
        assert filter_with_mock_config.config["sensitive_categories"] == mock_config["sensitive_categories"]
        assert filter_with_mock_config.config["sensitive_keywords"] == mock_config["sensitive_keywords"]

    def test_init_with_default_config_path(self, tmp_path, mock_config):
        """デフォルトconfig_pathでの初期化 (L49)"""
        # get_project_rootをモックしてtmp_pathを返す
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "sensitive_keywords.yaml"
        config_file.write_text(yaml.dump(mock_config), encoding="utf-8")

        with patch("src.sensitive_filter.get_project_root", return_value=tmp_path):
            filter_obj = SensitiveFilter()  # config_path=None

        assert filter_obj.config is not None
        assert "sensitive_categories" in filter_obj.config


class TestIsSensitive:
    """is_sensitive メソッドのテスト"""

    def test_sensitive_category_detected(self, filter_with_mock_config):
        """センシティブカテゴリを検出"""
        candidate = PersonCandidate(person_name="テスト太郎", category="犯罪者")
        is_sensitive, reason = filter_with_mock_config.is_sensitive(candidate)

        assert is_sensitive is True
        assert "sensitive_category" in reason
        assert "犯罪者" in reason

    def test_sensitive_keyword_detected(self, filter_with_mock_config):
        """センシティブキーワードを検出"""
        candidate = PersonCandidate(person_name="テスト太郎", category="その他", description="詐欺で逮捕された人物")
        is_sensitive, reason = filter_with_mock_config.is_sensitive(candidate)

        assert is_sensitive is True
        assert "sensitive_keyword" in reason

    def test_allow_list_bypasses_check(self, filter_with_mock_config):
        """許可リストの人物はセンシティブ判定をスキップ"""
        candidate = PersonCandidate(person_name="マンデラ", category="政治家", description="逮捕歴あり")
        is_sensitive, reason = filter_with_mock_config.is_sensitive(candidate)

        assert is_sensitive is False
        assert reason == ""

    def test_normal_person_not_sensitive(self, filter_with_mock_config):
        """通常の人物はセンシティブではない"""
        candidate = PersonCandidate(person_name="山中伸弥", category="科学者", description="ノーベル賞受賞者")
        is_sensitive, reason = filter_with_mock_config.is_sensitive(candidate)

        assert is_sensitive is False
        assert reason == ""


class TestRequiresReview:
    """requires_review メソッドのテスト"""

    def test_review_required_category(self, filter_with_mock_config):
        """レビュー必要カテゴリを検出"""
        candidate = PersonCandidate(person_name="安倍晋三", category="政治家")
        requires_review, reason = filter_with_mock_config.requires_review(candidate)

        assert requires_review is True
        assert "review_required_category" in reason
        assert "政治家" in reason

    def test_no_review_for_normal_category(self, filter_with_mock_config):
        """通常カテゴリはレビュー不要"""
        candidate = PersonCandidate(person_name="イチロー", category="スポーツ選手")
        requires_review, reason = filter_with_mock_config.requires_review(candidate)

        assert requires_review is False
        assert reason == ""


class TestFilterCandidates:
    """filter_candidates メソッドのテスト"""

    def test_filter_separates_correctly(self, filter_with_mock_config):
        """候補を正しく分類する"""
        candidates = [
            PersonCandidate(person_name="科学者A", category="科学者"),
            PersonCandidate(person_name="政治家B", category="政治家"),
            PersonCandidate(person_name="犯罪者C", category="犯罪者"),
        ]

        approved, review, blocked = filter_with_mock_config.filter_candidates(candidates, allow_sensitive=False)

        assert len(approved) == 1
        assert approved[0].person_name == "科学者A"
        assert len(review) == 1
        assert review[0].person_name == "政治家B"
        assert len(blocked) == 1
        assert blocked[0].person_name == "犯罪者C"

    def test_allow_sensitive_flag(self, filter_with_mock_config):
        """allow_sensitiveフラグで承認"""
        candidates = [
            PersonCandidate(person_name="犯罪者C", category="犯罪者"),
        ]

        approved, review, blocked = filter_with_mock_config.filter_candidates(candidates, allow_sensitive=True)

        assert len(approved) == 1
        assert len(blocked) == 0

    def test_empty_candidates_list(self, filter_with_mock_config):
        """空のリストを処理"""
        approved, review, blocked = filter_with_mock_config.filter_candidates([])

        assert approved == []
        assert review == []
        assert blocked == []

    def test_skip_reason_is_set(self, filter_with_mock_config):
        """スキップ理由が設定される"""
        candidates = [
            PersonCandidate(person_name="犯罪者C", category="犯罪者"),
        ]

        _, _, blocked = filter_with_mock_config.filter_candidates(candidates, allow_sensitive=False)

        assert blocked[0].skip_reason is not None
        assert "sensitive" in blocked[0].skip_reason


class TestGetStatistics:
    """get_statistics メソッドのテスト"""

    def test_returns_correct_counts(self, filter_with_mock_config, mock_config):
        """正しい統計情報を返す"""
        stats = filter_with_mock_config.get_statistics()

        assert stats["sensitive_categories"] == len(mock_config["sensitive_categories"])
        assert stats["sensitive_keywords"] == len(mock_config["sensitive_keywords"])
        assert stats["review_required_categories"] == len(mock_config["review_required_categories"])
        assert stats["allow_list"] == len(mock_config["allow_list"])

    def test_statistics_keys(self, filter_with_mock_config):
        """必要なキーが存在する"""
        stats = filter_with_mock_config.get_statistics()

        expected_keys = [
            "sensitive_categories",
            "sensitive_keywords",
            "review_required_categories",
            "allow_list",
        ]
        for key in expected_keys:
            assert key in stats
