#!/usr/bin/env python3
"""
状態ラベル正規化のテスト

状態ラベル（「ポケモン博士」「赤ちゃん」「金色の」「老」など）が
付いた人物名の正規化と、誤検出防止のテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fix.normalize_state_labels import NORMALIZATION_MAP


# ==================== ヘルパー関数 ====================


def normalize(name: str) -> str:
    """
    状態ラベル付き人物名を正規化する

    Args:
        name: 正規化対象の人物名

    Returns:
        正規化後の人物名（マッピングにない場合は元の名前をそのまま返す）
    """
    return NORMALIZATION_MAP.get(name, name)


# 誤検出を避けるべき名前のセット（老、王、金などで始まるが正規名として保持すべきもの）
FALSE_POSITIVE_EXCLUSIONS = {
    # 「老」で始まる正規名
    "老子",  # 道家の思想家
    "老界王神",  # ドラゴンボール - 界王神とは別キャラ
    # 「王」で始まる正規名
    "王貞治",  # 野球選手
    "王蟲",  # ナウシカ
    "王様",  # 一般的な呼称
    # 「金」で始まる正規名
    "金田一",  # 探偵
    "金太郎",  # 昔話
}


def check_person_name(name: str) -> tuple[bool, str]:
    """
    人物名が状態ラベル付きかどうかをチェックする

    Args:
        name: チェック対象の人物名

    Returns:
        tuple[is_valid, message]:
            - is_valid: 正規名として有効な場合True、状態ラベル付きならFalse
            - message: 検出された問題の説明（問題なければ空文字列）
    """
    # 誤検出除外リストにある場合は有効
    if name in FALSE_POSITIVE_EXCLUSIONS:
        return True, ""

    # 正規化マッピングに存在する場合は無効（状態ラベル付き）
    if name in NORMALIZATION_MAP:
        normalized = NORMALIZATION_MAP[name]
        return False, f"状態ラベル付き: '{name}' → '{normalized}' に正規化すべき"

    # 問題なし
    return True, ""


# ==================== 正規化マッピングテスト ====================


class TestNormalizationMapping:
    """正規化マッピングのテスト"""

    def test_pokemon_professor_araragi_normalized(self):
        """ポケモン博士アララギ → アララギ博士"""
        assert normalize("ポケモン博士アララギ") == "アララギ博士"

    def test_pokemon_professor_okido_normalized(self):
        """ポケモン博士オーキド → オーキド博士"""
        assert normalize("ポケモン博士オーキド") == "オーキド博士"

    def test_pokemon_professor_utsugi_normalized(self):
        """ポケモン博士ウツギ → ウツギ博士"""
        assert normalize("ポケモン博士ウツギ") == "ウツギ博士"

    def test_pokemon_professor_odamaki_normalized(self):
        """ポケモン博士オダマキ → オダマキ博士"""
        assert normalize("ポケモン博士オダマキ") == "オダマキ博士"

    def test_pokemon_professor_nanakamado_normalized(self):
        """ポケモン博士ナナカマド → ナナカマド博士"""
        assert normalize("ポケモン博士ナナカマド") == "ナナカマド博士"

    def test_pokemon_professor_platane_normalized(self):
        """ポケモン博士プラターヌ → プラターヌ博士"""
        assert normalize("ポケモン博士プラターヌ") == "プラターヌ博士"

    def test_pokemon_professor_kukui_normalized(self):
        """ポケモン博士ククイ → ククイ博士"""
        assert normalize("ポケモン博士ククイ") == "ククイ博士"

    def test_pokemon_professor_magnolia_normalized(self):
        """ポケモン博士マグノリア → マグノリア博士"""
        assert normalize("ポケモン博士マグノリア") == "マグノリア博士"

    def test_pokemon_professor_orim_normalized(self):
        """ポケモン博士オーリム → オーリム博士"""
        assert normalize("ポケモン博士オーリム") == "オーリム博士"

    def test_pokemon_professor_futuu_normalized(self):
        """ポケモン博士フトゥー → フトゥー博士"""
        assert normalize("ポケモン博士フトゥー") == "フトゥー博士"

    def test_baby_pikachu_normalized(self):
        """赤ちゃんピカチュウ → ピカチュウ"""
        assert normalize("赤ちゃんピカチュウ") == "ピカチュウ"

    def test_baby_shinnosuke_normalized(self):
        """赤ちゃんしんのすけ → 野原しんのすけ"""
        assert normalize("赤ちゃんしんのすけ") == "野原しんのすけ"

    def test_baby_shizuku_normalized(self):
        """赤ちゃんしずくちゃん → しずくちゃん"""
        assert normalize("赤ちゃんしずくちゃん") == "しずくちゃん"

    def test_baby_melonpanna_normalized(self):
        """赤ちゃんメロンパンナちゃん → メロンパンナちゃん"""
        assert normalize("赤ちゃんメロンパンナちゃん") == "メロンパンナちゃん"

    def test_golden_frieza_normalized(self):
        """金色のフリーザ → フリーザ"""
        assert normalize("金色のフリーザ") == "フリーザ"

    def test_old_sophie_normalized(self):
        """老ソフィー → ソフィー"""
        assert normalize("老ソフィー") == "ソフィー"


# ==================== 誤検出防止テスト ====================


class TestFalsePositivePreservation:
    """誤検出防止のテスト - 正規名は変更されないことを確認"""

    def test_false_positive_preserved_oh_sadaharu(self):
        """王貞治は変更なし"""
        assert normalize("王貞治") == "王貞治"

    def test_false_positive_preserved_laozi(self):
        """老子は変更なし"""
        assert normalize("老子") == "老子"

    def test_false_positive_preserved_ohmu(self):
        """王蟲は変更なし"""
        assert normalize("王蟲") == "王蟲"

    def test_old_kaioshin_excluded(self):
        """老界王神は別キャラなので変更なし"""
        assert normalize("老界王神") == "老界王神"

    def test_kindaichi_preserved(self):
        """金田一は変更なし"""
        assert normalize("金田一") == "金田一"

    def test_kintaro_preserved(self):
        """金太郎は変更なし"""
        assert normalize("金太郎") == "金太郎"

    def test_normal_name_preserved(self):
        """通常の名前は変更なし"""
        assert normalize("ピカチュウ") == "ピカチュウ"
        assert normalize("サトシ") == "サトシ"
        assert normalize("野原しんのすけ") == "野原しんのすけ"


# ==================== 状態ラベルゲートテスト ====================


class TestStateLabelGate:
    """状態ラベルゲートのテスト"""

    def test_gate_detects_pokemon_professor(self):
        """ポケモン博士アララギを検出"""
        is_valid, message = check_person_name("ポケモン博士アララギ")
        assert not is_valid
        assert "アララギ博士" in message

    def test_gate_detects_baby_prefix(self):
        """赤ちゃんプレフィックスを検出"""
        is_valid, message = check_person_name("赤ちゃんピカチュウ")
        assert not is_valid
        assert "ピカチュウ" in message

    def test_gate_detects_golden_prefix(self):
        """金色のプレフィックスを検出"""
        is_valid, message = check_person_name("金色のフリーザ")
        assert not is_valid
        assert "フリーザ" in message

    def test_gate_detects_old_prefix(self):
        """老プレフィックスを検出（老ソフィー）"""
        is_valid, message = check_person_name("老ソフィー")
        assert not is_valid
        assert "ソフィー" in message

    def test_gate_allows_normal_name(self):
        """通常の名前は許可"""
        is_valid, message = check_person_name("ピカチュウ")
        assert is_valid
        assert message == ""

    def test_gate_allows_oh_sadaharu(self):
        """王貞治は許可（誤検出除外）"""
        is_valid, message = check_person_name("王貞治")
        assert is_valid
        assert message == ""

    def test_gate_allows_laozi(self):
        """老子は許可（誤検出除外）"""
        is_valid, message = check_person_name("老子")
        assert is_valid
        assert message == ""

    def test_gate_allows_ohmu(self):
        """王蟲は許可（誤検出除外）"""
        is_valid, message = check_person_name("王蟲")
        assert is_valid
        assert message == ""

    def test_gate_allows_old_kaioshin(self):
        """老界王神は許可（別キャラとして除外）"""
        is_valid, message = check_person_name("老界王神")
        assert is_valid
        assert message == ""


# ==================== 正規化マップ整合性テスト ====================


class TestNormalizationMapIntegrity:
    """正規化マップの整合性テスト"""

    def test_map_has_expected_count(self):
        """正規化マップは16件のエントリを持つ"""
        assert len(NORMALIZATION_MAP) == 16

    def test_pokemon_professors_count(self):
        """ポケモン博士は10件"""
        pokemon_professors = [k for k in NORMALIZATION_MAP.keys() if k.startswith("ポケモン博士")]
        assert len(pokemon_professors) == 10

    def test_baby_characters_count(self):
        """赤ちゃんキャラは4件"""
        baby_chars = [k for k in NORMALIZATION_MAP.keys() if k.startswith("赤ちゃん")]
        assert len(baby_chars) == 4

    def test_form_prefix_count(self):
        """形態プレフィックスは2件"""
        form_prefixes = ["金色のフリーザ", "老ソフィー"]
        for name in form_prefixes:
            assert name in NORMALIZATION_MAP

    def test_normalized_names_are_different(self):
        """正規化後の名前は元の名前と異なる"""
        for original, normalized in NORMALIZATION_MAP.items():
            assert original != normalized, f"{original} は自身に正規化されています"

    def test_no_circular_normalization(self):
        """循環正規化がない"""
        # 正規化後の名前がマッピングのキーに存在しないことを確認
        for normalized in NORMALIZATION_MAP.values():
            assert normalized not in NORMALIZATION_MAP, f"{normalized} は循環正規化されます"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
