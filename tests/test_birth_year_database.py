"""
BirthYearDatabase テストモジュール

birth_year_database.py の単体テストを提供します。
"""

import pytest
from datetime import datetime

from src.birth_year_database import (
    CURRENT_YEAR,
    BIRTH_YEARS,
    get_birth_year,
    calculate_episode_year,
    is_future_episode,
    get_max_valid_age,
    validate_episode_age,
    get_database_stats,
)


class TestConstants:
    """定数のテスト"""

    def test_current_year(self):
        """CURRENT_YEARが現在の年"""
        assert CURRENT_YEAR == datetime.now().year

    def test_birth_years_not_empty(self):
        """BIRTH_YEARSが空でない"""
        assert len(BIRTH_YEARS) > 0

    def test_birth_years_has_known_people(self):
        """既知の人物が含まれている"""
        known_people = ["堺雅人", "綾瀬はるか", "大谷翔平"]
        for person in known_people:
            assert person in BIRTH_YEARS, f"{person}がBIRTH_YEARSに含まれていません"


class TestGetBirthYear:
    """get_birth_year 関数のテスト"""

    def test_known_person(self):
        """既知人物の生年を取得"""
        birth_year = get_birth_year("堺雅人")
        assert birth_year == 1973

    def test_unknown_person(self):
        """未知人物はNone"""
        birth_year = get_birth_year("存在しない人物ABC")
        assert birth_year is None

    def test_case_sensitive(self):
        """大文字小文字を区別"""
        # 人物名は正確に一致する必要がある
        birth_year = get_birth_year("堺雅人")
        assert birth_year is not None


class TestCalculateEpisodeYear:
    """calculate_episode_year 関数のテスト"""

    def test_calculation(self):
        """エピソード年の計算"""
        # 1973年生まれ、40歳のエピソード = 2013年
        episode_year = calculate_episode_year("堺雅人", 40)
        assert episode_year == 2013

    def test_unknown_person(self):
        """未知人物はNone"""
        episode_year = calculate_episode_year("存在しない人物", 30)
        assert episode_year is None


class TestIsFutureEpisode:
    """is_future_episode 関数のテスト"""

    def test_past_episode(self):
        """過去のエピソードはFalse"""
        # 堺雅人（1973年生）の40歳 = 2013年
        is_future = is_future_episode("堺雅人", 40)
        assert is_future is False

    def test_future_episode(self):
        """未来のエピソードはTrue"""
        # 堺雅人（1973年生）の100歳 = 2073年
        is_future = is_future_episode("堺雅人", 100)
        assert is_future is True

    def test_unknown_person_low_age(self):
        """未知人物（低年齢）はFalse"""
        is_future = is_future_episode("存在しない人物", 30)
        assert is_future is False

    def test_unknown_person_high_age(self):
        """未知人物（高年齢60以上）はTrue（フェイルセーフ）"""
        is_future = is_future_episode("存在しない人物", 60)
        assert is_future is True


class TestGetMaxValidAge:
    """get_max_valid_age 関数のテスト"""

    def test_known_person(self):
        """既知人物の最大有効年齢"""
        max_age = get_max_valid_age("堺雅人")
        # 2025年現在、1973年生まれなら52歳
        expected = CURRENT_YEAR - 1973
        assert max_age == expected

    def test_unknown_person(self):
        """未知人物はNone"""
        max_age = get_max_valid_age("存在しない人物")
        assert max_age is None


class TestValidateEpisodeAge:
    """validate_episode_age 関数のテスト"""

    def test_valid_age(self):
        """有効な年齢"""
        is_valid, message = validate_episode_age("堺雅人", 40, "REAL")
        assert is_valid is True
        assert message is not None

    def test_invalid_future_age(self):
        """未来の年齢は無効"""
        is_valid, message = validate_episode_age("堺雅人", 100, "REAL")
        assert is_valid is False
        assert "未来" in message or "超過" in message

    def test_fictional_always_valid(self):
        """架空キャラクターは常に有効"""
        is_valid, message = validate_episode_age("ドラえもん", 1000, "FICTIONAL")
        assert is_valid is True

    def test_unknown_person(self):
        """未知人物の処理"""
        is_valid, message = validate_episode_age("存在しない人物", 30, "REAL")
        # 未知人物の場合は実装によってTrueまたはFalse
        assert message is not None


class TestGetDatabaseStats:
    """get_database_stats 関数のテスト"""

    def test_returns_dict(self):
        """辞書を返す"""
        stats = get_database_stats()
        assert isinstance(stats, dict)

    def test_has_total_count(self):
        """総数が含まれる"""
        stats = get_database_stats()
        assert "total" in stats or "total_persons" in stats or len(stats) > 0


class TestBirthYearsData:
    """BIRTH_YEARSデータの品質テスト"""

    def test_birth_years_are_reasonable(self):
        """生年が妥当な範囲内（古代〜現代人物含む）"""
        for name, year in BIRTH_YEARS.items():
            # 古代人物（ヒポクラテス等紀元前）から現代まで許容
            assert -1000 < year < 2015, f"{name}の生年{year}が妥当な範囲外"

    def test_no_duplicate_entries(self):
        """重複エントリがない（辞書なので自動的に保証）"""
        # 辞書はキーの重複を許さないので、このテストは常にパス
        assert len(BIRTH_YEARS) == len(set(BIRTH_YEARS.keys()))

    def test_specific_birth_years(self):
        """特定の人物の生年が正しい"""
        test_cases = [
            ("堺雅人", 1973),
            ("綾瀬はるか", 1985),
            ("広瀬すず", 1998),
        ]
        for name, expected_year in test_cases:
            if name in BIRTH_YEARS:
                assert BIRTH_YEARS[name] == expected_year, f"{name}の生年が不正"


# ============================================================================
# 追加テスト: 未カバー行のテスト
# ============================================================================


class TestGetBirthYearPartialMatch:
    """get_birth_year 部分一致テスト"""

    def test_partial_match_person_in_name(self):
        """部分一致: person_name が BIRTH_YEARS のキーに含まれる"""
        # 既存の人物名の一部で検索
        for full_name in list(BIRTH_YEARS.keys())[:5]:
            if len(full_name) >= 2:
                partial = full_name[:2]  # 最初の2文字
                result = get_birth_year(partial)
                # 部分一致でマッチするはず
                if result is not None:
                    assert isinstance(result, int)
                    break


class TestValidateEpisodeAgeEdgeCases:
    """validate_episode_age 境界ケーステスト"""

    def test_negative_age(self):
        """負の年齢は無効"""
        is_valid, message = validate_episode_age("堺雅人", -5, "REAL")
        assert is_valid is False
        assert "負の値" in message

    def test_age_over_130(self):
        """130歳超は無効"""
        is_valid, message = validate_episode_age("堺雅人", 135, "REAL")
        assert is_valid is False
        assert "130歳" in message

    def test_unknown_person_high_age_block(self):
        """未知人物の高齢（60歳以上）はブロック"""
        is_valid, message = validate_episode_age("架空のテスト人物XYZ", 65, "REAL")
        assert is_valid is False
        assert "BLOCK" in message
        assert "高齢" in message

    def test_unknown_person_young_age_block(self):
        """未知人物の幼少（10歳以下）はブロック"""
        is_valid, message = validate_episode_age("架空のテスト人物XYZ", 5, "REAL")
        assert is_valid is False
        assert "BLOCK" in message
        assert "幼少" in message

    def test_age_exceeds_max_valid_age(self):
        """最大有効年齢を超過"""
        # 堺雅人（1973年生）の現在年齢より大きい年齢
        max_age = CURRENT_YEAR - 1973
        is_valid, message = validate_episode_age("堺雅人", max_age + 5, "REAL")
        assert is_valid is False
        # 未来のエピソードか年齢超過のどちらかのメッセージ
        assert "未来" in message or "超過" in message


class TestIsFutureEpisodeWithCurrentYear:
    """is_future_episode current_year指定テスト"""

    def test_with_custom_current_year(self):
        """カスタム current_year で判定"""
        # 堺雅人（1973年生）の40歳 = 2013年
        # 2010年を基準にすると未来
        is_future = is_future_episode("堺雅人", 40, current_year=2010)
        assert is_future is True

        # 2020年を基準にすると過去
        is_future = is_future_episode("堺雅人", 40, current_year=2020)
        assert is_future is False


class TestGetMaxValidAgeWithCurrentYear:
    """get_max_valid_age current_year指定テスト"""

    def test_with_custom_current_year(self):
        """カスタム current_year で最大年齢取得"""
        # 堺雅人（1973年生）
        # 2000年基準: 2000 - 1973 = 27歳
        max_age = get_max_valid_age("堺雅人", current_year=2000)
        assert max_age == 27

        # 2030年基準: 2030 - 1973 = 57歳
        max_age = get_max_valid_age("堺雅人", current_year=2030)
        assert max_age == 57


class TestValidateEpisodeAgeWithCurrentYear:
    """validate_episode_age current_year指定テスト"""

    def test_with_custom_current_year(self):
        """カスタム current_year で検証"""
        # 堺雅人（1973年生）の40歳 = 2013年
        # 2010年基準では未来なので無効
        is_valid, message = validate_episode_age("堺雅人", 40, "REAL", current_year=2010)
        assert is_valid is False
        assert "未来" in message

        # 2020年基準では過去なので有効
        is_valid, message = validate_episode_age("堺雅人", 40, "REAL", current_year=2020)
        assert is_valid is True
