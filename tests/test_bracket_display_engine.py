#!/usr/bin/env python3
"""
bracket_display_engine.py のテストスイート

カバレッジ:
1. 架空キャラクターの判定テスト
2. グループ所属の判定テスト
3. ワード除去のテスト
4. 検証ロジックのテスト
"""

import sys
from pathlib import Path

import pytest

# テスト対象モジュールのインポート
sys.path.insert(0, str(Path(__file__).parent.parent))

from bracket_display_engine import (
    BracketDisplayEngine,
    BracketDisplayResult,
    EntityType,
    FameLevel,
    GroupStatus,
    create_episode_prompt_with_bracket_constraint,
    format_person_name_with_bracket,
)

# ================================================================================
# フィクスチャ
# ================================================================================


@pytest.fixture
def engine():
    """エンジンインスタンス"""
    return BracketDisplayEngine()


@pytest.fixture
def fictional_character_data():
    """架空キャラクターのサンプルデータ"""
    return {
        "person_name": "モンキー・D・ルフィ",
        "entity_type": "fictional_character",
        "primary_work": "ONE PIECE",
        "category": "架空キャラクター",
    }


@pytest.fixture
def active_comedian_data():
    """現役お笑いコンビのサンプルデータ"""
    return {
        "person_name": "又吉直樹",
        "entity_type": "real_person",
        "category": "お笑い芸人",
        "group_affiliation": "ピース",
        "group_status": "active",
        "fame_level": "equal",
    }


@pytest.fixture
def disbanded_band_data():
    """解散バンドのサンプルデータ"""
    return {
        "person_name": "YOSHIKI",
        "entity_type": "real_person",
        "category": "ミュージシャン",
        "group_affiliation": "X JAPAN",
        "group_status": "disbanded",
        "fame_level": "personal_more_famous",
    }


# ================================================================================
# 架空キャラクターのテスト
# ================================================================================


class TestFictionalCharacter:
    """架空キャラクターの判定テスト"""

    def test_fictional_character_always_show(self, engine, fictional_character_data):
        """架空キャラクターは常に作品名を表示"""
        result = engine.should_show_bracket(fictional_character_data)

        assert result.should_show
        assert result.bracket_text == "ONE PIECE"
        assert result.formatted_name == "モンキー・D・ルフィ(ONE PIECE)"
        assert "架空キャラクター" in result.reason

    def test_fictional_character_without_work(self, engine):
        """作品名が未設定の架空キャラクター"""
        data = {
            "person_name": "テストキャラ",
            "entity_type": "fictional_character",
            # primary_work が未設定
        }

        result = engine.should_show_bracket(data)

        assert not result.should_show
        assert result.bracket_text is None

    def test_multiple_fictional_characters(self, engine):
        """複数の架空キャラクター"""
        characters = [("竈門炭治郎", "鬼滅の刃"), ("孫悟空", "ドラゴンボール"), ("ドラえもん", "ドラえもん")]

        for name, work in characters:
            data = {"person_name": name, "entity_type": "fictional_character", "primary_work": work}

            result = engine.should_show_bracket(data)

            assert result.should_show
            assert result.bracket_text == work
            assert result.formatted_name == f"{name}({work})"


# ================================================================================
# グループ所属のテスト
# ================================================================================


class TestGroupAffiliation:
    """グループ所属の判定テスト"""

    def test_active_comedian_show(self, engine, active_comedian_data):
        """現役お笑いコンビは表示"""
        result = engine.should_show_bracket(active_comedian_data)

        assert result.should_show
        assert result.bracket_text == "ピース"
        assert result.formatted_name == "又吉直樹(ピース)"

    def test_disbanded_band_not_show(self, engine, disbanded_band_data):
        """解散バンドは表示しない"""
        result = engine.should_show_bracket(disbanded_band_data)

        assert not result.should_show
        assert result.bracket_text is None
        assert result.formatted_name == "YOSHIKI"
        assert "解散済み" in result.reason

    def test_hiatus_group_not_show(self, engine):
        """活動休止中のグループは表示しない"""
        data = {
            "person_name": "テストメンバー",
            "entity_type": "real_person",
            "category": "お笑い芸人",
            "group_affiliation": "テストグループ",
            "group_status": "hiatus",
            "fame_level": "equal",
        }

        result = engine.should_show_bracket(data)

        assert not result.should_show
        assert "活動休止中" in result.reason

    def test_personal_more_famous_not_show(self, engine):
        """本人の方が有名な場合は表示しない"""
        data = {
            "person_name": "HIKAKIN",
            "entity_type": "real_person",
            "category": "YouTuber",
            "group_affiliation": "HIKAKIN & SEIKIN",
            "group_status": "active",
            "fame_level": "personal_more_famous",
        }

        result = engine.should_show_bracket(data)

        assert not result.should_show
        assert "本人の知名度" in result.reason

    def test_no_group_affiliation(self, engine):
        """グループ所属情報がない場合"""
        data = {
            "person_name": "テスト太郎",
            "entity_type": "real_person",
            "category": "お笑い芸人",
            # group_affiliation が未設定
        }

        result = engine.should_show_bracket(data)

        assert not result.should_show
        assert "グループ所属情報なし" in result.reason


# ================================================================================
# カテゴリ別テスト
# ================================================================================


class TestCategoryBased:
    """カテゴリ別の判定テスト"""

    @pytest.mark.parametrize(
        "category", ["お笑い芸人", "コメディアン", "ミュージシャン", "バンド", "YouTuber", "アイドル"]
    )
    def test_eligible_categories(self, engine, category):
        """括弧表示対象カテゴリ"""
        data = {
            "person_name": "テストメンバー",
            "entity_type": "real_person",
            "category": category,
            "group_affiliation": "テストグループ",
            "group_status": "active",
            "fame_level": "group_more_famous",
        }

        result = engine.should_show_bracket(data)

        assert result.should_show

    def test_non_eligible_category(self, engine):
        """括弧表示対象外カテゴリ"""
        data = {
            "person_name": "テストスポーツ選手",
            "entity_type": "real_person",
            "category": "スポーツ選手",
            "group_affiliation": "テストチーム",
            "group_status": "active",
            "fame_level": "equal",
        }

        result = engine.should_show_bracket(data)

        assert not result.should_show
        assert "対象外" in result.reason


# ================================================================================
# 強制表示フラグのテスト
# ================================================================================


class TestForceDisplay:
    """強制表示フラグのテスト"""

    def test_force_show_with_flag(self, engine):
        """show_group_in_bracket=1 で強制表示"""
        data = {
            "person_name": "テストメンバー",
            "entity_type": "real_person",
            "show_group_in_bracket": 1,
            "bracket_display_text": "強制表示グループ",
        }

        result = engine.should_show_bracket(data)

        assert result.should_show
        assert result.bracket_text == "強制表示グループ"


# ================================================================================
# ワード除去のテスト
# ================================================================================


class TestWordRemoval:
    """ワード除去のテスト"""

    def test_remove_group_name_from_text(self, engine):
        """グループ名の除去"""
        text = "あなたと同じ31歳のとき、松本人志(ダウンタウン)はダウンタウンとして「ごっつええ感じ」で最高視聴率28.8％を記録した。"
        cleaned = engine.remove_bracket_word_from_text(text, "ダウンタウン", "松本人志")

        # 人物名部分の "ダウンタウン" は残る
        assert "松本人志(ダウンタウン)" in cleaned

        # エピソード本文の "ダウンタウン" は削除される
        text_without_name = cleaned.replace("松本人志(ダウンタウン)", "")
        assert "ダウンタウン" not in text_without_name

    def test_remove_work_name_from_text(self, engine):
        """作品名の除去"""
        text = "あなたと同じ19歳のとき、モンキー・D・ルフィ(ONE PIECE)はONE PIECEの冒険で東の海から偉大なる航路へと旅立った。"
        cleaned = engine.remove_bracket_word_from_text(text, "ONE PIECE", "モンキー・D・ルフィ")

        # 人物名部分の "ONE PIECE" は残る
        assert "モンキー・D・ルフィ(ONE PIECE)" in cleaned

        # エピソード本文の "ONE PIECE" は削除される
        text_without_name = cleaned.replace("モンキー・D・ルフィ(ONE PIECE)", "")
        assert "ONE PIECE" not in text_without_name

    def test_remove_various_patterns(self, engine):
        """様々なパターンのワード除去"""
        test_cases = [
            ("ピースは漫才コンビです", "ピース", "又吉直樹", "漫才コンビです"),
            ("ピースとして活動", "ピース", "又吉直樹", "活動"),
            ("ピースで出演", "ピース", "又吉直樹", "出演"),
            ("ピースの又吉直樹", "ピース", "又吉直樹", "又吉直樹"),
        ]

        for text, bracket_word, person_name, expected_fragment in test_cases:
            cleaned = engine.remove_bracket_word_from_text(text, bracket_word, person_name)
            text_without_name = cleaned.replace(f"{person_name}({bracket_word})", "")
            assert bracket_word not in text_without_name

    def test_no_removal_when_no_bracket_word(self, engine):
        """括弧内ワードがない場合は変更なし"""
        text = "テストエピソードテキスト"
        cleaned = engine.remove_bracket_word_from_text(text, "", "テスト太郎")

        assert cleaned == text


# ================================================================================
# 検証ロジックのテスト
# ================================================================================


class TestValidation:
    """検証ロジックのテスト"""

    def test_validate_no_duplication_success(self, engine):
        """重複なし（検証成功）"""
        text = "あなたと同じ31歳のとき、松本人志(ダウンタウン)は「ごっつええ感じ」で最高視聴率28.8％を記録した。"
        is_valid, duplications = engine.validate_no_word_duplication(text, "ダウンタウン", "松本人志")

        assert is_valid
        assert len(duplications) == 0

    def test_validate_duplication_detected(self, engine):
        """重複検出（検証失敗）"""
        text = "あなたと同じ31歳のとき、松本人志(ダウンタウン)はダウンタウンとして「ごっつええ感じ」で活躍した。"
        is_valid, duplications = engine.validate_no_word_duplication(text, "ダウンタウン", "松本人志")

        assert not is_valid
        assert len(duplications) > 0

    def test_validate_no_bracket_word(self, engine):
        """括弧内ワードなし（検証成功）"""
        text = "テストエピソード"
        is_valid, duplications = engine.validate_no_word_duplication(text, "", "テスト太郎")

        assert is_valid


# ================================================================================
# ヘルパー関数のテスト
# ================================================================================


class TestHelperFunctions:
    """ヘルパー関数のテスト"""

    def test_format_person_name_with_bracket(self):
        """人物名フォーマット"""
        data = {
            "person_name": "又吉直樹",
            "entity_type": "real_person",
            "category": "お笑い芸人",
            "group_affiliation": "ピース",
            "group_status": "active",
            "fame_level": "equal",
        }

        formatted_name, bracket_text = format_person_name_with_bracket(data)

        assert formatted_name == "又吉直樹(ピース)"
        assert bracket_text == "ピース"

    def test_create_episode_prompt_with_constraint(self):
        """括弧制約付きプロンプト生成"""
        data = {
            "person_name": "松本人志",
            "entity_type": "real_person",
            "category": "お笑い芸人",
            "group_affiliation": "ダウンタウン",
            "group_status": "active",
            "fame_level": "group_more_famous",
        }

        template = "あなたと同じ{age}歳のとき、{person_name}は"
        prompt = create_episode_prompt_with_bracket_constraint(data, 31, template)

        # 括弧付き名前が含まれている
        assert "松本人志(ダウンタウン)" in prompt

        # 制約が含まれている
        assert "ダウンタウン」という単語を使わない" in prompt


# ================================================================================
# 統合テスト
# ================================================================================


class TestIntegration:
    """統合テスト"""

    def test_full_workflow_fictional_character(self, engine):
        """架空キャラクターの全ワークフロー"""
        data = {"person_name": "竈門炭治郎", "entity_type": "fictional_character", "primary_work": "鬼滅の刃"}

        # 判定
        result = engine.should_show_bracket(data)
        assert result.should_show
        assert result.formatted_name == "竈門炭治郎(鬼滅の刃)"

        # ワード除去
        text = "あなたと同じ15歳のとき、竈門炭治郎(鬼滅の刃)は鬼滅の刃の世界で家族を守るため戦い続けた。"
        cleaned = engine.remove_bracket_word_from_text(text, "鬼滅の刃", "竈門炭治郎")

        # 検証
        is_valid, _ = engine.validate_no_word_duplication(cleaned, "鬼滅の刃", "竈門炭治郎")
        assert is_valid

    def test_full_workflow_real_person(self, engine):
        """実在人物の全ワークフロー"""
        data = {
            "person_name": "又吉直樹",
            "entity_type": "real_person",
            "category": "お笑い芸人",
            "group_affiliation": "ピース",
            "group_status": "active",
            "fame_level": "equal",
        }

        # 判定
        result = engine.should_show_bracket(data)
        assert result.should_show

        # エピソード生成（シミュレーション）
        episode_text = f"あなたと同じ30歳のとき、{result.formatted_name}は芥川賞を受賞した。"

        # ワード除去（この例では元々含まれていない）
        cleaned = engine.remove_bracket_word_from_text(episode_text, "ピース", "又吉直樹")

        # 検証
        is_valid, _ = engine.validate_no_word_duplication(cleaned, "ピース", "又吉直樹")
        assert is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
