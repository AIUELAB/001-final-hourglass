#!/usr/bin/env python3
"""
エピソード人物名整合性の回帰テスト

テスト観点表:
┌─────────────────────────────────────────────────────────────────────────┐
│ 等価分割                                                                │
├─────────────────┬───────────────────────────────────────────────────────┤
│ カテゴリ        │ テストケース                                          │
├─────────────────┼───────────────────────────────────────────────────────┤
│ 正常系          │ 1. 実在人物: person_name == 本文冒頭名                 │
│                 │ 2. 架空キャラ: person_name『作品名』形式              │
│                 │ 3. 日本語名に「は」を含む（栗原はるみ等）             │
├─────────────────┼───────────────────────────────────────────────────────┤
│ 異常系          │ 4. 英語名混入: person_name=日本語, 本文=英語          │
│ （ブロック必須）│ 5. 表記ゆれ: 微妙に異なる表記                         │
│                 │ 6. 名前重複バグ: 「はるみはるみ」等                   │
├─────────────────┼───────────────────────────────────────────────────────┤
│ 境界値          │ 7. 1文字の名前                                        │
│                 │ 8. 長い名前（フルネーム）                             │
│                 │ 9. 特殊文字を含む名前（・、＝等）                     │
└─────────────────┴───────────────────────────────────────────────────────┘
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.validators.episode_name_validator import (
    EpisodeNameValidator,
    ValidationResult,
    validate_episode_name,
    extract_lead_name,
)


class TestExtractLeadName:
    """リード文からの人物名抽出テスト"""

    def test_normal_real_person(self):
        """実在人物の通常フォーマット"""
        text = "あなたと同じ30歳のとき、山田太郎は起業した。"
        assert extract_lead_name(text) == "山田太郎"

    def test_fictional_with_work_title(self):
        """架空キャラ『作品名』形式"""
        text = "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会で優勝した。"
        assert extract_lead_name(text, "毛利蘭") == "毛利蘭"

    def test_name_with_ha_character(self):
        """名前に「は」を含むケース"""
        text = "あなたと同じ45歳のとき、栗原はるみは料理研究家として活躍した。"
        assert extract_lead_name(text, "栗原はるみ") == "栗原はるみ"

    def test_name_with_special_chars(self):
        """特殊文字を含む名前"""
        text = "あなたと同じ35歳のとき、モンキー・D・ルフィ『ONE PIECE』は海賊王を目指した。"
        assert extract_lead_name(text, "モンキー・D・ルフィ") == "モンキー・D・ルフィ"

    def test_invalid_format(self):
        """不正なフォーマット"""
        text = "これは不正なフォーマットです。"
        assert extract_lead_name(text) is None


class TestValidateEpisodeName:
    """人物名整合性バリデーションテスト"""

    # === 正常系 ===

    def test_valid_real_person(self):
        """正常: 実在人物の一致"""
        result = validate_episode_name("山田太郎", "あなたと同じ30歳のとき、山田太郎は起業した。", strict=False)
        assert result.result == ValidationResult.VALID

    def test_valid_fictional_character(self):
        """正常: 架空キャラ『作品名』形式"""
        result = validate_episode_name(
            "毛利蘭", "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会で優勝した。", strict=False
        )
        assert result.result == ValidationResult.VALID

    def test_valid_name_with_ha(self):
        """正常: 名前に「は」を含む"""
        result = validate_episode_name(
            "栗原はるみ", "あなたと同じ45歳のとき、栗原はるみは料理研究家として活躍した。", strict=False
        )
        assert result.result == ValidationResult.VALID

    # === 異常系（ブロック必須）===

    def test_mismatch_english_name(self):
        """異常: 英語名混入"""
        result = validate_episode_name(
            "エイダ・ラヴレース", "あなたと同じ30歳のとき、Ada Lovelaceはプログラムを書いた。", strict=False
        )
        assert result.result == ValidationResult.MISMATCH
        assert "Ada Lovelace" in result.message

    def test_mismatch_different_notation(self):
        """異常: 表記ゆれ"""
        result = validate_episode_name(
            "ベートーヴェン", "あなたと同じ40歳のとき、ベートーベンは交響曲を作曲した。", strict=False
        )
        assert result.result == ValidationResult.MISMATCH

    def test_mismatch_partial_name(self):
        """異常: 部分一致（姓のみ）"""
        result = validate_episode_name("山田太郎", "あなたと同じ30歳のとき、山田は起業した。", strict=False)
        assert result.result == ValidationResult.MISMATCH

    def test_strict_mode_raises(self):
        """厳密モード: 不一致で例外"""
        with pytest.raises(ValueError) as excinfo:
            validate_episode_name(
                "エイダ・ラヴレース", "あなたと同じ30歳のとき、Ada Lovelaceはプログラムを書いた。", strict=True
            )
        assert "人物名不一致" in str(excinfo.value)

    # === 境界値 ===

    def test_single_char_name(self):
        """境界値: 1文字の名前"""
        result = validate_episode_name("蘭", "あなたと同じ17歳のとき、蘭は空手大会に出場した。", strict=False)
        assert result.result == ValidationResult.VALID

    def test_long_full_name(self):
        """境界値: 長いフルネーム"""
        result = validate_episode_name(
            "ヨハン・ヴォルフガング・フォン・ゲーテ",
            "あなたと同じ50歳のとき、ヨハン・ヴォルフガング・フォン・ゲーテは詩を書いた。",
            strict=False,
        )
        assert result.result == ValidationResult.VALID

    def test_name_with_special_characters(self):
        """境界値: 特殊文字を含む名前"""
        result = validate_episode_name(
            "L'Arc〜en〜Cielのhyde", "あなたと同じ35歳のとき、L'Arc〜en〜Cielのhydeはソロ活動を開始した。", strict=False
        )
        assert result.result == ValidationResult.VALID

    # === パターン不一致 ===

    def test_no_pattern(self):
        """パターン不一致"""
        result = validate_episode_name("山田太郎", "これは不正なフォーマットです。", strict=False)
        assert result.result == ValidationResult.NO_PATTERN


class TestEpisodeNameValidator:
    """バリデータークラスのテスト"""

    def test_validator_stats(self):
        """統計機能のテスト"""
        validator = EpisodeNameValidator(strict=False)

        # 正常
        validator.validate("山田", "あなたと同じ30歳のとき、山田は起業した。")
        # 不一致
        validator.validate("山田", "あなたと同じ30歳のとき、田中は起業した。")
        # 正常
        validator.validate("佐藤", "あなたと同じ40歳のとき、佐藤は転職した。")

        stats = validator.get_stats()
        assert stats["validation_count"] == 3
        assert stats["mismatch_count"] == 1
        assert stats["mismatch_rate"] == pytest.approx(1 / 3)


class TestRegressionScenarios:
    """実際に発生した問題の回帰テスト"""

    def test_regression_ada_lovelace(self):
        """回帰: EP-000006312 エイダ・ラヴレースの英語名混入"""
        result = validate_episode_name(
            "エイダ・ラヴレース", "あなたと同じ30歳のとき、Ada Lovelaceはプログラムを書いた。", strict=False
        )
        assert result.result == ValidationResult.MISMATCH

    def test_regression_charles_babbage(self):
        """回帰: EP-000007849 チャールズ・バベッジの英語名混入"""
        result = validate_episode_name(
            "チャールズ・バベッジ", "あなたと同じ40歳のとき、Charles Babbageは計算機を設計した。", strict=False
        )
        assert result.result == ValidationResult.MISMATCH

    def test_regression_name_duplication(self):
        """回帰: 名前重複バグ（栗原はるみはるみ）"""
        # 修正後は「栗原はるみ」で正しく認識される
        result = validate_episode_name(
            "栗原はるみ", "あなたと同じ45歳のとき、栗原はるみは料理研究家として活躍した。", strict=False
        )
        assert result.result == ValidationResult.VALID

    def test_regression_fictional_format(self):
        """回帰: 架空キャラ『作品名』形式は正常"""
        result = validate_episode_name(
            "毛利蘭", "あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会で優勝した。", strict=False
        )
        assert result.result == ValidationResult.VALID


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
