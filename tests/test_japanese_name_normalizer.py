#!/usr/bin/env python3
"""
EPUP: 日本人名正規化バリデータ 回帰テスト

テスト観点:
1. ローマ字パターン検出
2. カタカナ音訳パターン検出
3. Wikidata照合
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validators.japanese_name_normalizer import (
    is_katakana_romaji,
    is_likely_japanese_romaji,
)


class TestRomajiDetection:
    """ローマ字パターン検出テスト"""

    def test_detects_kurosawa(self):
        """黒澤明のローマ字表記を検出"""
        assert is_likely_japanese_romaji("Akira Kurosawa") is True

    def test_detects_miyazaki(self):
        """宮崎駿のローマ字表記を検出"""
        assert is_likely_japanese_romaji("Hayao Miyazaki") is True

    def test_detects_murakami(self):
        """村上春樹のローマ字表記を検出"""
        assert is_likely_japanese_romaji("Haruki Murakami") is True

    def test_detects_honda(self):
        """本田宗一郎のローマ字表記を検出"""
        assert is_likely_japanese_romaji("Soichiro Honda") is True

    def test_ignores_non_japanese_western(self):
        """西洋人名は検出しない"""
        assert is_likely_japanese_romaji("Michael Jackson") is False

    def test_ignores_non_japanese_european(self):
        """ヨーロッパ人名は検出しない"""
        assert is_likely_japanese_romaji("Albert Einstein") is False

    def test_ignores_single_word(self):
        """単語1つは検出しない"""
        assert is_likely_japanese_romaji("Kurosawa") is False

    def test_ignores_kanji(self):
        """漢字表記は検出しない"""
        assert is_likely_japanese_romaji("黒澤明") is False


class TestKatakanaRomajiDetection:
    """カタカナ音訳パターン検出テスト"""

    def test_detects_kurosawa_katakana(self):
        """アキラ・クロサワを検出"""
        assert is_katakana_romaji("アキラ・クロサワ") is True

    def test_detects_miyazaki_katakana(self):
        """ハヤオ・ミヤザキを検出"""
        assert is_katakana_romaji("ハヤオ・ミヤザキ") is True

    def test_ignores_normal_katakana(self):
        """通常のカタカナ名は検出しない"""
        assert is_katakana_romaji("マイケル・ジャクソン") is False

    def test_ignores_kanji(self):
        """漢字表記は検出しない"""
        assert is_katakana_romaji("黒澤明") is False

    def test_ignores_hiragana(self):
        """ひらがな表記は検出しない"""
        assert is_katakana_romaji("あいみょん") is False


class TestKnownAliases:
    """KNOWN_ALIASESの網羅性テスト"""

    def test_known_aliases_exist(self):
        """KNOWN_ALIASESが存在する"""
        from scripts.detect_person_id_duplicates import KNOWN_ALIASES

        assert len(KNOWN_ALIASES) > 0

    def test_kurosawa_in_aliases(self):
        """黒澤明がエイリアスに含まれる"""
        from scripts.detect_person_id_duplicates import KNOWN_ALIASES

        assert "アキラ・クロサワ" in KNOWN_ALIASES
        assert "Akira Kurosawa" in KNOWN_ALIASES
        assert KNOWN_ALIASES["アキラ・クロサワ"] == "黒澤明"
        assert KNOWN_ALIASES["Akira Kurosawa"] == "黒澤明"

    def test_miyazaki_in_aliases(self):
        """宮崎駿がエイリアスに含まれる"""
        from scripts.detect_person_id_duplicates import KNOWN_ALIASES

        assert "Hayao Miyazaki" in KNOWN_ALIASES
        assert KNOWN_ALIASES["Hayao Miyazaki"] == "宮崎駿"

    def test_murakami_in_aliases(self):
        """村上春樹がエイリアスに含まれる"""
        from scripts.detect_person_id_duplicates import KNOWN_ALIASES

        assert "Haruki Murakami" in KNOWN_ALIASES
        assert KNOWN_ALIASES["Haruki Murakami"] == "村上春樹"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
