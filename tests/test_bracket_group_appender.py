#!/usr/bin/env python3
"""
bracket_group_appender.py のユニットテスト
"""

import pytest

from src.bracket_group_appender import (
    should_append_group,
    append_group_bracket_to_lead,
    validate_appended_text,
)


class TestShouldAppendGroup:
    """should_append_group() のテスト"""

    def test_basic_append_case(self):
        """基本的な追記ケース: 実在人物・グループ所属・本文に重複なし"""
        should, reason = should_append_group(
            person_name="桜井和寿",
            group_name="Mr.Children",
            episode_text="あなたと同じ27歳のとき、桜井和寿は音楽活動を続けていました。",
            person_type="REAL",
            is_group_member="True",
        )
        assert should is True
        assert reason == ""

    def test_person_type_not_real(self):
        """person_type != "REAL" → スキップ"""
        should, reason = should_append_group(
            person_name="ドラえもん",
            group_name="",
            episode_text="あなたと同じ10歳のとき、ドラえもんは未来から来ました。",
            person_type="FICTIONAL",
            is_group_member="False",
        )
        assert should is False
        assert reason == "person_type_not_real"

    def test_not_group_member(self):
        """is_group_member != "True" → スキップ"""
        should, reason = should_append_group(
            person_name="宇多田ヒカル",
            group_name="",
            episode_text="あなたと同じ20歳のとき、宇多田ヒカルはアルバムを発表しました。",
            person_type="REAL",
            is_group_member="False",
        )
        assert should is False
        assert reason == "not_group_member"

    def test_no_group_name_empty(self):
        """group_name が空 → スキップ"""
        should, reason = should_append_group(
            person_name="田中太郎",
            group_name="",
            episode_text="あなたと同じ30歳のとき、田中太郎は活動していました。",
            person_type="REAL",
            is_group_member="True",
        )
        assert should is False
        assert reason == "no_group_name"

    def test_no_group_name_nan(self):
        """group_name が "nan" → スキップ"""
        should, reason = should_append_group(
            person_name="田中太郎",
            group_name="nan",
            episode_text="あなたと同じ30歳のとき、田中太郎は活動していました。",
            person_type="REAL",
            is_group_member="True",
        )
        assert should is False
        assert reason == "no_group_name"

    def test_no_group_name_unregistered(self):
        """group_name が "未登録" → スキップ"""
        should, reason = should_append_group(
            person_name="田中太郎",
            group_name="未登録",
            episode_text="あなたと同じ30歳のとき、田中太郎は活動していました。",
            person_type="REAL",
            is_group_member="True",
        )
        assert should is False
        assert reason == "no_group_name"

    def test_solo_artist(self):
        """SOLO_ARTISTSに登録済み → スキップ"""
        should, reason = should_append_group(
            person_name="宇多田ヒカル",
            group_name="何かのグループ",  # グループ名があっても無視
            episode_text="あなたと同じ20歳のとき、宇多田ヒカルはアルバムを発表しました。",
            person_type="REAL",
            is_group_member="True",
        )
        assert should is False
        assert reason == "solo_artist"

    def test_already_has_bracket_fullwidth(self):
        """既に全角括弧がある → スキップ"""
        should, reason = should_append_group(
            person_name="岸田裕子",
            group_name="何かのグループ",
            episode_text="あなたと同じ50歳のとき、岸田裕子（岸田文雄夫人）は活動していました。",
            person_type="REAL",
            is_group_member="True",
        )
        assert should is False
        assert reason == "already_has_bracket"

    def test_already_has_bracket_halfwidth(self):
        """既に半角括弧がある → スキップ"""
        should, reason = should_append_group(
            person_name="John Doe",
            group_name="Some Band",
            episode_text="あなたと同じ30歳のとき、John Doe(Some Band)は活動していました。",
            person_type="REAL",
            is_group_member="True",
        )
        assert should is False
        assert reason == "already_has_bracket"

    def test_group_name_in_text(self):
        """本文にグループ名が含まれる → スキップ"""
        should, reason = should_append_group(
            person_name="桜井和寿",
            group_name="Mr.Children",
            episode_text="あなたと同じ27歳のとき、桜井和寿はMr.Childrenのメンバーとして活動していました。",
            person_type="REAL",
            is_group_member="True",
        )
        assert should is False
        assert reason == "group_name_in_text"


class TestAppendGroupBracketToLead:
    """append_group_bracket_to_lead() のテスト"""

    def test_basic_append(self):
        """基本的な括弧追記"""
        original = "あなたと同じ27歳のとき、桜井和寿は音楽活動を続けていました。"
        result = append_group_bracket_to_lead(
            original,
            "桜井和寿",
            "Mr.Children",
        )
        expected = "あなたと同じ27歳のとき、桜井和寿（Mr.Children）は音楽活動を続けていました。"
        assert result == expected

    def test_append_with_long_text(self):
        """長文のエピソードでも正しく追記"""
        original = (
            "あなたと同じ40歳のとき、福山雅治は音楽活動と俳優業を両立させながら、"
            "数々のヒット曲をリリースし、ドラマや映画にも出演していました。"
        )
        result = append_group_bracket_to_lead(
            original,
            "福山雅治",
            "テストグループ",
        )
        assert result.startswith("あなたと同じ40歳のとき、福山雅治（テストグループ）は")
        assert "音楽活動と俳優業" in result

    def test_invalid_lead_format(self):
        """リード文形式が不正 → ValueError"""
        with pytest.raises(ValueError, match="リード文のパターンが想定外"):
            append_group_bracket_to_lead(
                "突然始まる文章です。",
                "田中太郎",
                "グループX",
            )

    def test_person_name_mismatch(self):
        """人物名が一致しない → ValueError"""
        with pytest.raises(ValueError, match="人物名が一致しません"):
            append_group_bracket_to_lead(
                "あなたと同じ30歳のとき、山田太郎は活動していました。",
                "田中太郎",  # 不一致
                "グループX",
            )


class TestValidateAppendedText:
    """validate_appended_text() のテスト"""

    def test_valid_append(self):
        """正しく追記された場合"""
        original = "あなたと同じ27歳のとき、桜井和寿は音楽活動を続けていました。"
        appended = "あなたと同じ27歳のとき、桜井和寿（Mr.Children）は音楽活動を続けていました。"
        assert validate_appended_text(original, appended, "Mr.Children") is True

    def test_invalid_no_bracket(self):
        """括弧が追記されていない"""
        original = "あなたと同じ27歳のとき、桜井和寿は音楽活動を続けていました。"
        appended = original  # 変更なし
        assert validate_appended_text(original, appended, "Mr.Children") is False

    def test_invalid_length(self):
        """長さの変化が不正"""
        original = "あなたと同じ27歳のとき、桜井和寿は音楽活動を続けていました。"
        appended = original + "余分な文字列"
        assert validate_appended_text(original, appended, "Mr.Children") is False


class TestIdempotency:
    """冪等性のテスト"""

    def test_already_appended_should_skip(self):
        """既に括弧がある場合、2回目はスキップ"""
        original = "あなたと同じ27歳のとき、桜井和寿は音楽活動を続けていました。"

        # 1回目: 追記すべき
        should_1, reason_1 = should_append_group(
            "桜井和寿",
            "Mr.Children",
            original,
            "REAL",
            "True",
        )
        assert should_1 is True

        # 追記実行
        appended = append_group_bracket_to_lead(original, "桜井和寿", "Mr.Children")

        # 2回目: 既に括弧があるのでスキップ
        should_2, reason_2 = should_append_group(
            "桜井和寿",
            "Mr.Children",
            appended,
            "REAL",
            "True",
        )
        assert should_2 is False
        assert reason_2 == "already_has_bracket"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
