"""
EpisodeAgeValidator テストモジュール

episode_age_validator.py の単体テストを提供します。
"""

import pytest
from unittest.mock import patch

from src.episode_age_validator import (
    EpisodeAgeValidator,
    ValidationResult,
    validate_episode_before_generation,
    generate_episode_with_validation,
)


class TestValidationResult:
    """ValidationResult データクラスのテスト"""

    def test_validation_result_creation(self):
        """ValidationResult が正しく作成できる"""
        result = ValidationResult(
            is_valid=True,
            error_code=None,
            message="OK",
            suggested_age=25,
            birth_year=1973,
            episode_year=1998,
        )
        assert result.is_valid is True
        assert result.error_code is None
        assert result.message == "OK"
        assert result.suggested_age == 25
        assert result.birth_year == 1973
        assert result.episode_year == 1998

    def test_validation_result_defaults(self):
        """デフォルト値が正しく設定される"""
        result = ValidationResult(is_valid=False, error_code="ERROR", message="エラー")
        assert result.suggested_age is None
        assert result.birth_year is None
        assert result.episode_year is None


class TestEpisodeAgeValidator:
    """EpisodeAgeValidator クラスのテスト"""

    @pytest.fixture
    def validator(self):
        """テスト用バリデーター（現在年を2025に固定）"""
        return EpisodeAgeValidator(current_year=2025, strict_mode=True)

    @pytest.fixture
    def non_strict_validator(self):
        """非厳格モードのバリデーター"""
        return EpisodeAgeValidator(current_year=2025, strict_mode=False)

    def test_init_default_year(self):
        """デフォルトの現在年で初期化できる"""
        validator = EpisodeAgeValidator()
        assert validator.current_year >= 2024

    def test_init_custom_year(self):
        """カスタム年で初期化できる"""
        validator = EpisodeAgeValidator(current_year=2020)
        assert validator.current_year == 2020

    def test_fictional_character_always_valid(self, validator):
        """架空キャラクターは常に有効"""
        result = validator.validate("ドラえもん", 100, "FICTIONAL")
        assert result.is_valid is True
        assert "架空" in result.message

    def test_negative_age_invalid(self, validator):
        """負の年齢は無効"""
        result = validator.validate("テスト太郎", -5, "REAL")
        assert result.is_valid is False
        assert result.error_code == EpisodeAgeValidator.ERROR_AGE_NEGATIVE

    def test_age_over_130_invalid(self, validator):
        """130歳超えは無効"""
        result = validator.validate("テスト太郎", 150, "REAL")
        assert result.is_valid is False
        assert result.error_code == EpisodeAgeValidator.ERROR_AGE_TOO_HIGH

    @patch("src.episode_age_validator.get_birth_year")
    def test_known_person_valid_age(self, mock_get_birth_year, validator):
        """既知人物の有効な年齢"""
        mock_get_birth_year.return_value = 1973  # 堺雅人の生年
        result = validator.validate("堺雅人", 40, "REAL")
        assert result.is_valid is True
        assert result.birth_year == 1973
        assert result.episode_year == 2013

    @patch("src.episode_age_validator.get_birth_year")
    def test_known_person_future_episode(self, mock_get_birth_year, validator):
        """既知人物の未来エピソード検出"""
        mock_get_birth_year.return_value = 1973  # 堺雅人の生年
        result = validator.validate("堺雅人", 60, "REAL")  # 2033年のエピソード
        assert result.is_valid is False
        assert result.error_code == EpisodeAgeValidator.ERROR_FUTURE_EPISODE
        assert result.suggested_age == 52  # 2025 - 1973

    @patch("src.episode_age_validator.get_birth_year")
    def test_unknown_person_strict_mode(self, mock_get_birth_year, validator):
        """厳格モードで未知人物はエラー"""
        mock_get_birth_year.return_value = None
        result = validator.validate("未知の人物", 50, "REAL")
        assert result.is_valid is False
        assert result.error_code == EpisodeAgeValidator.ERROR_BIRTH_YEAR_UNKNOWN

    @patch("src.episode_age_validator.get_birth_year")
    def test_unknown_person_non_strict_mode(self, mock_get_birth_year, non_strict_validator):
        """非厳格モードで未知人物は警告付きで有効"""
        mock_get_birth_year.return_value = None
        result = non_strict_validator.validate("未知の人物", 50, "REAL")
        assert result.is_valid is True
        assert "警告" in result.message

    @patch("src.episode_age_validator.get_birth_year")
    def test_get_valid_age_range_known_person(self, mock_get_birth_year, validator):
        """既知人物の有効年齢範囲を取得"""
        mock_get_birth_year.return_value = 1990
        min_age, max_age = validator.get_valid_age_range("テスト人物")
        assert min_age == 0
        assert max_age == 35  # 2025 - 1990

    @patch("src.episode_age_validator.get_birth_year")
    def test_get_valid_age_range_unknown_person(self, mock_get_birth_year, validator):
        """未知人物はデフォルト範囲を返す"""
        mock_get_birth_year.return_value = None
        min_age, max_age = validator.get_valid_age_range("未知の人物")
        assert min_age == 0
        assert max_age == 100

    @patch("src.episode_age_validator.get_birth_year")
    def test_suggest_valid_age(self, mock_get_birth_year, validator):
        """有効な年齢を提案"""
        mock_get_birth_year.return_value = 2000
        suggested = validator.suggest_valid_age("若い人", 50)
        assert suggested == 25  # min(50, 25)

    @patch("src.episode_age_validator.get_birth_year")
    def test_suggest_valid_age_within_range(self, mock_get_birth_year, validator):
        """範囲内の年齢はそのまま返す"""
        mock_get_birth_year.return_value = 1980
        suggested = validator.suggest_valid_age("人物", 30)
        assert suggested == 30  # 範囲内なのでそのまま


class TestValidateEpisodeBeforeGeneration:
    """validate_episode_before_generation 関数のテスト"""

    @patch("src.episode_age_validator.get_birth_year")
    def test_valid_episode(self, mock_get_birth_year):
        """有効なエピソードの検証"""
        mock_get_birth_year.return_value = 1990
        is_valid, message, suggested = validate_episode_before_generation("テスト人物", 30, "REAL", current_year=2025)
        assert is_valid is True

    @patch("src.episode_age_validator.get_birth_year")
    def test_invalid_future_episode(self, mock_get_birth_year):
        """未来エピソードは無効"""
        mock_get_birth_year.return_value = 1990
        is_valid, message, suggested = validate_episode_before_generation("テスト人物", 50, "REAL", current_year=2025)
        assert is_valid is False
        assert suggested == 35

    def test_fictional_always_valid(self):
        """架空キャラクターは常に有効"""
        is_valid, message, suggested = validate_episode_before_generation(
            "ドラえもん", 1000, "FICTIONAL", current_year=2025
        )
        assert is_valid is True


class TestGenerateEpisodeWithValidation:
    """generate_episode_with_validation 関数のテスト"""

    @patch("src.episode_age_validator.get_birth_year")
    def test_valid_generation(self, mock_get_birth_year):
        """有効な場合は生成関数を呼び出す"""
        mock_get_birth_year.return_value = 1990

        def mock_generate(**kwargs):
            return f"Episode for {kwargs['person_name']}"

        result = generate_episode_with_validation(mock_generate, "テスト人物", 30, "REAL")
        assert result == "Episode for テスト人物"

    @patch("src.episode_age_validator.get_birth_year")
    def test_invalid_raises_error(self, mock_get_birth_year):
        """無効な場合は ValueError を発生"""
        mock_get_birth_year.return_value = 1990

        def mock_generate(**kwargs):
            return "Episode"

        with pytest.raises(ValueError, match="未来"):
            generate_episode_with_validation(mock_generate, "テスト人物", 100, "REAL")

    def test_invalid_raises_error_without_suggested_age(self):
        """suggested_age=Noneの場合、メッセージのみのValueError (L190)"""

        # 負の年齢 -> suggested_ageはNone
        def mock_generate(**kwargs):
            return "Episode"

        with pytest.raises(ValueError):
            generate_episode_with_validation(mock_generate, "テスト人物", -5, "REAL")
