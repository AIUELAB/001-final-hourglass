#!/usr/bin/env python3
"""
episode_name_validator.py のユニットテスト

対象: extract_lead_name(), validate_episode_name(), EpisodeNameValidatorクラス
"""

import pytest

from src.validators.episode_name_validator import (
    EpisodeNameValidator,
    NameValidationResult,
    ValidationResult,
    extract_lead_name,
    validate_episode_name,
)


# ============================================================
# extract_lead_name() テスト
# ============================================================


class TestExtractLeadName:
    """extract_lead_name() 関数のテスト"""

    def test_returns_none_for_empty_text(self):
        """空テキストはNoneを返す"""
        assert extract_lead_name("") is None

    def test_returns_none_for_none_text(self):
        """Noneテキストはエラーにならず空扱い"""
        assert extract_lead_name(None) is None  # type: ignore[arg-type]

    def test_extracts_name_from_normal_format(self):
        """通常形式「あなたと同じN歳のとき、{名前}は」から名前を抽出"""
        text = "あなたと同じ30歳のとき、山田太郎は起業した。"
        assert extract_lead_name(text) == "山田太郎"

    def test_extracts_name_from_fictional_format(self):
        """架空キャラ形式「あなたと同じN歳のとき、{名前}『{作品名}』は」から名前を抽出"""
        text = "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会で優勝した。"
        assert extract_lead_name(text) == "毛利蘭"

    def test_extracts_with_person_name_hint_normal(self):
        """person_nameヒントで通常形式を優先チェック"""
        text = "あなたと同じ30歳のとき、山田太郎は起業した。"
        assert extract_lead_name(text, person_name="山田太郎") == "山田太郎"

    def test_extracts_with_person_name_hint_fictional(self):
        """person_nameヒントで架空キャラ形式を優先チェック"""
        text = "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会で優勝した。"
        assert extract_lead_name(text, person_name="毛利蘭") == "毛利蘭"

    def test_returns_none_for_non_matching_format(self):
        """リード文パターンに一致しないテキストはNoneを返す"""
        text = "これは不正なフォーマットです。"
        assert extract_lead_name(text) is None

    def test_handles_decimal_age(self):
        """小数年齢を含むリード文を処理"""
        text = "あなたと同じ0.5歳のとき、赤ちゃんは笑った。"
        result = extract_lead_name(text)
        assert result == "赤ちゃん"

    def test_fallback_when_person_name_not_match(self):
        """person_nameが一致しない場合にフォールバックで抽出"""
        text = "あなたと同じ30歳のとき、実際の名前は活躍した。"
        result = extract_lead_name(text, person_name="別の名前")
        assert result == "実際の名前"


# ============================================================
# validate_episode_name() テスト
# ============================================================


class TestValidateEpisodeName:
    """validate_episode_name() 関数のテスト"""

    def test_valid_match_returns_valid(self):
        """名前が一致する場合はVALIDを返す"""
        result = validate_episode_name(
            "山田太郎",
            "あなたと同じ30歳のとき、山田太郎は起業した。",
            strict=False,
        )
        assert result.result == ValidationResult.VALID
        assert result.message == "OK"

    def test_valid_fictional_match(self):
        """架空キャラ形式で名前が一致する場合はVALIDを返す"""
        result = validate_episode_name(
            "毛利蘭",
            "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会で優勝した。",
            strict=False,
        )
        assert result.result == ValidationResult.VALID

    def test_mismatch_returns_mismatch(self):
        """名前が不一致の場合はMISMATCHを返す（非厳密モード）"""
        result = validate_episode_name(
            "エイダ・ラヴレース",
            "あなたと同じ30歳のとき、Ada Lovelaceはプログラムを書いた。",
            strict=False,
        )
        assert result.result == ValidationResult.MISMATCH
        assert "不一致" in result.message

    def test_mismatch_raises_in_strict_mode(self):
        """名前が不一致の場合、厳密モードではValueErrorを送出"""
        with pytest.raises(ValueError, match="不一致"):
            validate_episode_name(
                "エイダ・ラヴレース",
                "あなたと同じ30歳のとき、Ada Lovelaceはプログラムを書いた。",
                strict=True,
            )

    def test_no_pattern_returns_no_pattern(self):
        """リード文パターンが見つからない場合はNO_PATTERNを返す"""
        result = validate_episode_name(
            "田中一郎",
            "これは不正なフォーマットです。",
            strict=False,
        )
        assert result.result == ValidationResult.NO_PATTERN
        assert result.text_name is None

    def test_no_pattern_does_not_raise_in_strict(self):
        """NO_PATTERNの場合は厳密モードでもValueErrorは発生しない"""
        result = validate_episode_name(
            "田中一郎",
            "これは不正なフォーマットです。",
            strict=True,
        )
        assert result.result == ValidationResult.NO_PATTERN

    def test_result_contains_person_name(self):
        """結果にperson_nameが含まれる"""
        result = validate_episode_name(
            "テスト太郎",
            "あなたと同じ25歳のとき、テスト太郎は成功した。",
            strict=False,
        )
        assert result.person_name == "テスト太郎"

    def test_result_contains_text_name(self):
        """結果にtext_nameが含まれる"""
        result = validate_episode_name(
            "テスト太郎",
            "あなたと同じ25歳のとき、テスト太郎は成功した。",
            strict=False,
        )
        assert result.text_name == "テスト太郎"


# ============================================================
# EpisodeNameValidator クラステスト
# ============================================================


class TestEpisodeNameValidator:
    """EpisodeNameValidatorクラスのテスト"""

    def test_init_default_strict(self):
        """デフォルトでstrictモード"""
        validator = EpisodeNameValidator()
        assert validator.strict is True
        assert validator.validation_count == 0
        assert validator.mismatch_count == 0

    def test_init_non_strict(self):
        """非strictモードで初期化"""
        validator = EpisodeNameValidator(strict=False)
        assert validator.strict is False

    def test_validate_increments_count(self):
        """validateを呼ぶとカウントが増加する"""
        validator = EpisodeNameValidator(strict=False)
        validator.validate("テスト", "あなたと同じ25歳のとき、テストは成功した。")
        assert validator.validation_count == 1

    def test_validate_increments_mismatch_count(self):
        """不一致時にmismatch_countが増加する"""
        validator = EpisodeNameValidator(strict=False)
        validator.validate("テストA", "あなたと同じ25歳のとき、テストBは成功した。")
        assert validator.mismatch_count == 1

    def test_validate_valid_does_not_increment_mismatch(self):
        """一致時はmismatch_countは増加しない"""
        validator = EpisodeNameValidator(strict=False)
        validator.validate("テスト", "あなたと同じ25歳のとき、テストは成功した。")
        assert validator.mismatch_count == 0

    def test_validate_strict_raises_on_mismatch(self):
        """strictモードで不一致時にValueErrorを送出"""
        validator = EpisodeNameValidator(strict=True)
        with pytest.raises(ValueError, match="不一致"):
            validator.validate("名前A", "あなたと同じ25歳のとき、名前Bは活躍した。")

    def test_get_stats_structure(self):
        """get_statsが正しい構造を返す"""
        validator = EpisodeNameValidator(strict=False)
        stats = validator.get_stats()
        assert "validation_count" in stats
        assert "mismatch_count" in stats
        assert "mismatch_rate" in stats

    def test_get_stats_initial_values(self):
        """初期状態のstats値"""
        validator = EpisodeNameValidator(strict=False)
        stats = validator.get_stats()
        assert stats["validation_count"] == 0
        assert stats["mismatch_count"] == 0
        assert stats["mismatch_rate"] == 0.0

    def test_get_stats_after_multiple_validations(self):
        """複数回バリデーション後のstats"""
        validator = EpisodeNameValidator(strict=False)
        validator.validate("テスト", "あなたと同じ25歳のとき、テストは成功した。")
        validator.validate("名前A", "あなたと同じ30歳のとき、名前Bは失敗した。")
        validator.validate("名前C", "あなたと同じ35歳のとき、名前Cは復活した。")
        stats = validator.get_stats()
        assert stats["validation_count"] == 3
        assert stats["mismatch_count"] == 1
        assert stats["mismatch_rate"] == pytest.approx(1 / 3)


# ============================================================
# ValidationResult Enum テスト
# ============================================================


class TestValidationResultEnum:
    """ValidationResult Enumのテスト"""

    def test_valid_value(self):
        assert ValidationResult.VALID.value == "valid"

    def test_mismatch_value(self):
        assert ValidationResult.MISMATCH.value == "mismatch"

    def test_no_pattern_value(self):
        assert ValidationResult.NO_PATTERN.value == "no_pattern"


# ============================================================
# NameValidationResult データクラステスト
# ============================================================


class TestNameValidationResult:
    """NameValidationResultデータクラスのテスト"""

    def test_dataclass_fields(self):
        """正しいフィールドを持つ"""
        result = NameValidationResult(
            result=ValidationResult.VALID,
            person_name="テスト",
            text_name="テスト",
            message="OK",
        )
        assert result.result == ValidationResult.VALID
        assert result.person_name == "テスト"
        assert result.text_name == "テスト"
        assert result.message == "OK"

    def test_text_name_can_be_none(self):
        """text_nameはNoneを許容"""
        result = NameValidationResult(
            result=ValidationResult.NO_PATTERN,
            person_name="テスト",
            text_name=None,
            message="パターンなし",
        )
        assert result.text_name is None
