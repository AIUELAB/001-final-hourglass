"""
tests/test_age_data_validator.py - age_data_validator.py ユニットテスト
"""

import pytest

from src.age_data_validator import (
    AgeDataValidator,
    PersonType,
    ValidationResult,
    ValidationStatus,
    validate_age_for_generation,
)


class TestPersonType:
    """PersonType Enumテスト"""

    def test_person_type_values(self):
        """PersonTypeの値"""
        assert PersonType.REAL.value == "REAL"
        assert PersonType.FICTIONAL.value == "FICTIONAL"
        assert PersonType.UNKNOWN.value == "UNKNOWN"

    def test_person_type_membership(self):
        """PersonTypeのメンバー"""
        assert len(PersonType) == 3


class TestValidationStatus:
    """ValidationStatus Enumテスト"""

    def test_validation_status_values(self):
        """ValidationStatusの値"""
        assert ValidationStatus.VALID.value == "VALID"
        assert ValidationStatus.INVALID_AGE_EXCEEDED.value == "INVALID_AGE_EXCEEDED"
        assert ValidationStatus.INVALID_FUTURE_AGE.value == "INVALID_FUTURE_AGE"
        assert ValidationStatus.INVALID_NEGATIVE_AGE.value == "INVALID_NEGATIVE_AGE"
        assert ValidationStatus.INVALID_DATA.value == "INVALID_DATA"
        assert ValidationStatus.SKIPPED.value == "SKIPPED"

    def test_validation_status_membership(self):
        """ValidationStatusのメンバー"""
        assert len(ValidationStatus) == 6


class TestValidationResult:
    """ValidationResult dataclassテスト"""

    def test_validation_result_creation(self):
        """ValidationResult作成"""
        result = ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            message="有効",
        )
        assert result.is_valid is True
        assert result.status == ValidationStatus.VALID
        assert result.message == "有効"
        assert result.suggested_max_age is None

    def test_validation_result_with_suggested_age(self):
        """suggested_max_age付きのValidationResult"""
        result = ValidationResult(
            is_valid=False,
            status=ValidationStatus.INVALID_AGE_EXCEEDED,
            message="年齢超過",
            suggested_max_age=80,
        )
        assert result.is_valid is False
        assert result.suggested_max_age == 80


class TestAgeDataValidatorInit:
    """AgeDataValidator初期化テスト"""

    def test_init_default_year(self):
        """デフォルト年（システム年）"""
        from datetime import datetime

        validator = AgeDataValidator()
        assert validator.current_year == datetime.now().year

    def test_init_custom_year(self):
        """カスタム年"""
        validator = AgeDataValidator(current_year=2025)
        assert validator.current_year == 2025


class TestValidateAgeNegative:
    """負の年齢テスト"""

    def test_negative_age(self):
        """負の年齢は無効"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(-5, "REAL")

        assert result.is_valid is False
        assert result.status == ValidationStatus.INVALID_NEGATIVE_AGE
        assert "-5" in result.message


class TestValidateAgeFictional:
    """架空キャラクターテスト"""

    def test_fictional_any_age(self):
        """架空キャラクターは任意の年齢OK"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(1000, "FICTIONAL")

        assert result.is_valid is True
        assert result.status == ValidationStatus.VALID
        assert "架空キャラクター" in result.message

    def test_fictional_lowercase(self):
        """小文字fictional"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(500, "fictional")

        assert result.is_valid is True

    def test_fictional_mixed_case(self):
        """混合ケースFictional"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(200, "Fictional")

        assert result.is_valid is True


class TestValidateAgeDeceased:
    """故人の年齢検証テスト"""

    def test_deceased_age_within_limit(self):
        """死亡年齢以内"""
        validator = AgeDataValidator(current_year=2025)
        # 吉田松陰: 1830-1859 (29歳で死亡)
        result = validator.validate_age(
            age=25,
            person_type="REAL",
            birth_year=1830,
            death_year=1859,
            death_age=29,
        )

        assert result.is_valid is True

    def test_deceased_age_exceeded_death_age(self):
        """死亡年齢超過（death_age指定）"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(
            age=35,
            person_type="REAL",
            birth_year=1830,
            death_year=1859,
            death_age=29,
        )

        assert result.is_valid is False
        assert result.status == ValidationStatus.INVALID_AGE_EXCEEDED
        assert result.suggested_max_age == 29

    def test_deceased_age_exceeded_calculated(self):
        """死亡年齢超過（birth/death年から計算）"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(
            age=35,
            person_type="REAL",
            birth_year=1830,
            death_year=1859,
        )

        assert result.is_valid is False
        assert result.status == ValidationStatus.INVALID_AGE_EXCEEDED
        assert result.suggested_max_age == 29  # 1859-1830

    def test_deceased_exact_death_age(self):
        """ちょうど死亡年齢"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(
            age=29,
            person_type="REAL",
            birth_year=1830,
            death_year=1859,
            death_age=29,
        )

        assert result.is_valid is True


class TestValidateAgeLiving:
    """存命者の年齢検証テスト"""

    def test_living_age_within_current(self):
        """現在年齢以内"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(
            age=20,
            person_type="REAL",
            birth_year=2000,
        )

        assert result.is_valid is True

    def test_living_age_exceeded_current(self):
        """現在年齢超過"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(
            age=30,
            person_type="REAL",
            birth_year=2000,
        )

        assert result.is_valid is False
        assert result.status == ValidationStatus.INVALID_FUTURE_AGE
        assert result.suggested_max_age == 25  # 2025-2000

    def test_living_exact_current_age(self):
        """ちょうど現在年齢"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(
            age=25,
            person_type="REAL",
            birth_year=2000,
        )

        assert result.is_valid is True


class TestValidateAgeUnknown:
    """不明な人物タイプテスト"""

    def test_unknown_type(self):
        """UNKNOWNタイプ"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(50, "UNKNOWN")

        assert result.is_valid is True
        assert result.status == ValidationStatus.VALID

    def test_none_type(self):
        """Noneタイプ"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(50, None)

        assert result.is_valid is True

    def test_empty_type(self):
        """空文字タイプ"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(50, "")

        assert result.is_valid is True


class TestValidateAgeNoDetails:
    """詳細情報なしのテスト"""

    def test_real_no_birth_death(self):
        """REALで生年/没年なし"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(100, "REAL")

        assert result.is_valid is True
        assert result.status == ValidationStatus.VALID


class TestValidateEpisodeAge:
    """validate_episode_ageメソッドテスト"""

    def test_standard_format_valid(self):
        """標準フォーマットから年齢抽出・検証（有効）"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_episode_age(
            episode_text="あなたと同じ25歳のとき、彼は偉業を成し遂げた",
            person_name="テスト太郎",
            person_type="REAL",
            birth_year=2000,
        )

        assert result.is_valid is True

    def test_standard_format_invalid(self):
        """標準フォーマットから年齢抽出・検証（無効）"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_episode_age(
            episode_text="あなたと同じ30歳のとき、彼は偉業を成し遂げた",
            person_name="テスト太郎",
            person_type="REAL",
            birth_year=2000,
        )

        assert result.is_valid is False
        assert result.status == ValidationStatus.INVALID_FUTURE_AGE

    def test_non_standard_format(self):
        """標準フォーマット以外"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_episode_age(
            episode_text="25歳の時に活躍した",
            person_name="テスト太郎",
            person_type="REAL",
        )

        assert result.is_valid is False
        assert result.status == ValidationStatus.INVALID_DATA
        assert "抽出できません" in result.message

    def test_episode_deceased_person(self):
        """故人のエピソード検証"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_episode_age(
            episode_text="あなたと同じ29歳のとき、松陰は処刑された",
            person_name="吉田松陰",
            person_type="REAL",
            birth_year=1830,
            death_year=1859,
            death_age=29,
        )

        assert result.is_valid is True

    def test_episode_deceased_exceeded(self):
        """故人のエピソード検証（超過）"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_episode_age(
            episode_text="あなたと同じ35歳のとき",
            person_name="吉田松陰",
            person_type="REAL",
            birth_year=1830,
            death_year=1859,
            death_age=29,
        )

        assert result.is_valid is False


class TestValidateAgeForGeneration:
    """validate_age_for_generation関数テスト"""

    def test_valid_age(self):
        """有効な年齢"""
        is_valid, message = validate_age_for_generation(
            age=25,
            person_type="REAL",
            birth_year=2000,
        )

        assert is_valid is True
        assert "有効" in message

    def test_invalid_age_deceased(self):
        """無効な年齢（故人）"""
        is_valid, message = validate_age_for_generation(
            age=40,
            person_type="REAL",
            birth_year=1830,
            death_year=1859,
        )

        assert is_valid is False
        assert "超えています" in message

    def test_fictional_character(self):
        """架空キャラクター"""
        is_valid, message = validate_age_for_generation(
            age=1000,
            person_type="FICTIONAL",
        )

        assert is_valid is True

    def test_no_birth_death_year(self):
        """生年/没年なし"""
        is_valid, message = validate_age_for_generation(
            age=50,
            person_type="REAL",
        )

        assert is_valid is True

    def test_with_death_year_only(self):
        """没年のみ（death_ageはNone）"""
        is_valid, message = validate_age_for_generation(
            age=50,
            person_type="REAL",
            death_year=2020,
        )

        assert is_valid is True


class TestEdgeCases:
    """エッジケーステスト"""

    def test_zero_age(self):
        """0歳"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(0, "REAL", birth_year=2025)

        assert result.is_valid is True

    def test_very_old_age_fictional(self):
        """非常に高齢（架空）"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(10000, "FICTIONAL")

        assert result.is_valid is True

    def test_person_type_real_lowercase(self):
        """person_type小文字real"""
        validator = AgeDataValidator(current_year=2025)
        result = validator.validate_age(
            age=30,
            person_type="real",
            birth_year=2000,
        )

        # REALとして処理される
        assert result.is_valid is False
        assert result.status == ValidationStatus.INVALID_FUTURE_AGE
