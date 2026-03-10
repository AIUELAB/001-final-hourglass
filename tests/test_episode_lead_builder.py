"""
EpisodeLeadBuilder テストモジュール

episode_lead_builder.py の単体テストを提供します。
"""

import pytest

from src.episode_lead_builder import (
    PersonType,
    LeadSentenceResult,
    WORK_TITLE_MAP,
    get_work_title,
    build_episode_lead_sentence,
    convert_episode_lead,
    check_episode_lead_format,
)


class TestPersonType:
    """PersonType Enumのテスト"""

    def test_real_type(self):
        """REAL タイプが存在"""
        assert PersonType.REAL.value == "REAL"

    def test_fictional_type(self):
        """FICTIONAL タイプが存在"""
        assert PersonType.FICTIONAL.value == "FICTIONAL"


class TestLeadSentenceResult:
    """LeadSentenceResult データクラスのテスト"""

    def test_creation_with_all_fields(self):
        """全フィールドで作成"""
        result = LeadSentenceResult(
            lead_sentence="あなたと同じ25歳のとき、イチローは",
            person_type=PersonType.REAL,
            work_title_used="作品名",
            warning="警告",
        )
        assert result.lead_sentence == "あなたと同じ25歳のとき、イチローは"
        assert result.person_type == PersonType.REAL
        assert result.work_title_used == "作品名"
        assert result.warning == "警告"

    def test_defaults(self):
        """デフォルト値"""
        result = LeadSentenceResult(
            lead_sentence="リード文",
            person_type=PersonType.REAL,
        )
        assert result.work_title_used is None
        assert result.warning is None


class TestWorkTitleMap:
    """WORK_TITLE_MAP 定数のテスト"""

    def test_known_characters_mapped(self):
        """既知キャラクターがマッピングされている"""
        assert "ピカチュウ" in WORK_TITLE_MAP
        assert "ドラえもん" in WORK_TITLE_MAP
        assert "毛利蘭" in WORK_TITLE_MAP

    def test_correct_work_titles(self):
        """作品名が正しい"""
        assert WORK_TITLE_MAP["ピカチュウ"] == "ポケットモンスター"
        assert WORK_TITLE_MAP["ドラえもん"] == "ドラえもん"
        assert WORK_TITLE_MAP["毛利蘭"] == "名探偵コナン"


class TestGetWorkTitle:
    """get_work_title 関数のテスト"""

    def test_explicit_work_title(self):
        """明示的な作品名を返す"""
        title, warning = get_work_title("キャラ", "明示的作品名")
        assert title == "明示的作品名"
        assert warning is None

    def test_map_fallback(self):
        """MAPからフォールバック"""
        title, warning = get_work_title("ピカチュウ", None)
        assert title == "ポケットモンスター"
        assert warning is None

    def test_unknown_character(self):
        """不明キャラクターは警告"""
        title, warning = get_work_title("不明キャラ", None)
        assert title is None
        assert warning is not None
        assert "見つかりません" in warning

    def test_nan_work_title_ignored(self):
        """'nan'は無視される"""
        title, warning = get_work_title("ドラえもん", "nan")
        assert title == "ドラえもん"

    def test_empty_work_title_ignored(self):
        """空文字列は無視される"""
        title, warning = get_work_title("ドラえもん", "")
        assert title == "ドラえもん"


class TestBuildEpisodeLeadSentence:
    """build_episode_lead_sentence 関数のテスト"""

    def test_real_person(self):
        """実在人物のリード文"""
        result = build_episode_lead_sentence("イチロー", 45, "REAL")
        assert result.lead_sentence == "あなたと同じ45歳のとき、イチローは"
        assert result.person_type == PersonType.REAL
        assert result.work_title_used is None

    def test_fictional_with_work_title(self):
        """作品名付き架空キャラクター"""
        result = build_episode_lead_sentence("毛利蘭", 17, "FICTIONAL", "名探偵コナン")
        assert result.lead_sentence == "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は"
        assert result.person_type == PersonType.FICTIONAL
        assert result.work_title_used == "名探偵コナン"

    def test_fictional_with_map_fallback(self):
        """MAPからフォールバック"""
        result = build_episode_lead_sentence("ピカチュウ", 66, "FICTIONAL", None)
        assert "『ポケットモンスター』" in result.lead_sentence
        assert result.work_title_used == "ポケットモンスター"

    def test_fictional_without_work_title(self):
        """作品名なしの架空キャラクター（警告付き）"""
        result = build_episode_lead_sentence("不明キャラ", 20, "FICTIONAL", None)
        assert result.lead_sentence == "あなたと同じ20歳のとき、不明キャラは"
        assert result.warning is not None

    def test_none_person_type(self):
        """person_typeがNoneの場合はREAL扱い"""
        result = build_episode_lead_sentence("テスト", 30, None)
        assert result.person_type == PersonType.REAL

    def test_lowercase_person_type(self):
        """小文字のperson_type"""
        result = build_episode_lead_sentence("テスト", 30, "real")
        assert result.person_type == PersonType.REAL

    def test_age_as_float(self):
        """年齢がfloatでも正しく処理"""
        result = build_episode_lead_sentence("テスト", 30.5, "REAL")
        assert "30歳" in result.lead_sentence


class TestConvertEpisodeLead:
    """convert_episode_lead 関数のテスト"""

    def test_real_person_no_change(self):
        """実在人物は変換しない"""
        original = "あなたと同じ45歳のとき、イチローは引退した。"
        converted, warning = convert_episode_lead(original, "イチロー", 45, "REAL")
        assert converted == original
        assert warning is None

    def test_fictional_conversion(self):
        """架空キャラクターを変換"""
        original = "あなたと同じ17歳のとき、毛利蘭は空手をしていた。"
        converted, warning = convert_episode_lead(original, "毛利蘭", 17, "FICTIONAL", "名探偵コナン")
        assert "『名探偵コナン』" in converted
        assert warning is None

    def test_already_converted(self):
        """すでに変換済みは変更しない"""
        original = "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手をしていた。"
        converted, warning = convert_episode_lead(original, "毛利蘭", 17, "FICTIONAL", "名探偵コナン")
        assert converted == original
        assert warning is None

    def test_pattern_mismatch(self):
        """パターン不一致で警告"""
        original = "別のフォーマットのテキスト"
        converted, warning = convert_episode_lead(original, "毛利蘭", 17, "FICTIONAL", "名探偵コナン")
        assert converted == original
        assert warning is not None

    def test_fictional_conversion_with_warning(self):
        """架空キャラクター変換でwarning発生時 (L204)"""
        # current_patternに一致するが、work_titleがないFICTIONALキャラ
        original = "あなたと同じ20歳のとき、不明キャラは冒険をしていた。"
        converted, warning = convert_episode_lead(original, "不明キャラ", 20, "FICTIONAL", None)
        # warningが返され、テキストは変換されない
        assert converted == original
        assert warning is not None


class TestCheckEpisodeLeadFormat:
    """check_episode_lead_format 関数のテスト"""

    def test_valid_real_format(self):
        """有効な実在人物フォーマット"""
        text = "あなたと同じ45歳のとき、イチローは引退した。"
        is_valid, msg = check_episode_lead_format(text, "REAL")
        assert is_valid is True
        assert "実在人物" in msg

    def test_valid_fictional_format(self):
        """有効な架空キャラクターフォーマット"""
        text = "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会に出場した。"
        is_valid, msg = check_episode_lead_format(text, "FICTIONAL")
        assert is_valid is True
        assert "架空キャラクター" in msg

    def test_fictional_without_work_title(self):
        """架空キャラクターで作品名なしは不正"""
        text = "あなたと同じ17歳のとき、毛利蘭は空手大会に出場した。"
        is_valid, msg = check_episode_lead_format(text, "FICTIONAL")
        assert is_valid is False
        assert "作品名が含まれていません" in msg

    def test_invalid_format(self):
        """無効なフォーマット"""
        text = "まったく違うフォーマットのテキスト"
        is_valid, msg = check_episode_lead_format(text, "REAL")
        assert is_valid is False
        assert "準拠していません" in msg

    def test_none_person_type(self):
        """person_typeがNoneはREAL扱い"""
        text = "あなたと同じ30歳のとき、テストは何かした。"
        is_valid, msg = check_episode_lead_format(text, None)
        assert is_valid is True

    def test_fictional_completely_invalid_format(self):
        """架空キャラクターで完全に不正なフォーマット (L244)"""
        text = "まったく違うフォーマットのテキスト"
        is_valid, msg = check_episode_lead_format(text, "FICTIONAL")
        assert is_valid is False
        assert "標準フォーマットに準拠していません" in msg
