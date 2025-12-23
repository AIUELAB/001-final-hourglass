#!/usr/bin/env python3
"""
異体字正規化モジュールのテスト

テストケース:
- 宮崎あおい / 宮﨑あおい（プロンプトで指定された例）
- 正常系・異常系・境界値
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.validators.variant_normalizer import (
    detect_variant_duplicates,
    get_variant_info,
    has_variant_chars,
    normalize_person_name,
    validate_new_person_name,
)


class TestNormalizePersonName:
    """normalize_person_name関数のテスト"""

    def test_miyazaki_aoi_variant(self):
        """宮﨑あおい → 宮崎あおい（プロンプト指定例）"""
        assert normalize_person_name("宮﨑あおい") == "宮崎あおい"

    def test_miyazaki_hayao_variant(self):
        """宮﨑駿 → 宮崎駿"""
        assert normalize_person_name("宮﨑駿") == "宮崎駿"

    def test_already_canonical(self):
        """正規形はそのまま"""
        assert normalize_person_name("宮崎駿") == "宮崎駿"

    def test_yamasaki_kento(self):
        """山﨑賢人 → 山崎賢人"""
        assert normalize_person_name("山﨑賢人") == "山崎賢人"

    def test_akasaki_isamu(self):
        """赤﨑勇 → 赤崎勇"""
        assert normalize_person_name("赤﨑勇") == "赤崎勇"

    def test_kawasaki_munenori(self):
        """川﨑宗則 → 川崎宗則"""
        assert normalize_person_name("川﨑宗則") == "川崎宗則"

    def test_fullwidth_space(self):
        """全角空白は半角に統一"""
        assert normalize_person_name("山田　太郎") == "山田 太郎"

    def test_empty_string(self):
        """空文字列はそのまま"""
        assert normalize_person_name("") == ""

    def test_none(self):
        """Noneはそのまま"""
        assert normalize_person_name(None) is None

    def test_no_variant(self):
        """異体字なしの名前はそのまま"""
        assert normalize_person_name("田中太郎") == "田中太郎"


class TestHasVariantChars:
    """has_variant_chars関数のテスト"""

    def test_has_saki_variant(self):
        """﨑を含む場合True"""
        assert has_variant_chars("宮﨑駿") is True

    def test_no_variant(self):
        """異体字なしの場合False"""
        assert has_variant_chars("宮崎駿") is False

    def test_empty_string(self):
        """空文字列はFalse"""
        assert has_variant_chars("") is False

    def test_none(self):
        """NoneはFalse"""
        assert has_variant_chars(None) is False


class TestGetVariantInfo:
    """get_variant_info関数のテスト"""

    def test_saki_variant_info(self):
        """﨑の情報を取得"""
        info = get_variant_info("宮﨑駿")
        assert len(info) == 1
        assert info[0]["variant_char"] == "\ufa11"
        assert info[0]["canonical_char"] == "\u5d0e"
        assert info[0]["variant_code"] == "U+FA11"
        assert info[0]["canonical_code"] == "U+5D0E"

    def test_no_variant(self):
        """異体字なしは空リスト"""
        info = get_variant_info("宮崎駿")
        assert len(info) == 0


class TestDetectVariantDuplicates:
    """detect_variant_duplicates関数のテスト"""

    def test_detect_miyazaki_variants(self):
        """宮崎/宮﨑の重複を検出"""
        df = pd.DataFrame(
            {
                "person_id": ["P001", "P002"],
                "person_name": ["宮崎あおい", "宮﨑あおい"],
            }
        )
        duplicates = detect_variant_duplicates(df)
        assert len(duplicates) == 1
        assert duplicates[0]["normalized"] == "宮崎あおい"
        assert len(duplicates[0]["variants"]) == 2

    def test_no_duplicates(self):
        """重複なしの場合は空リスト"""
        df = pd.DataFrame(
            {
                "person_id": ["P001", "P002"],
                "person_name": ["山田太郎", "鈴木花子"],
            }
        )
        duplicates = detect_variant_duplicates(df)
        assert len(duplicates) == 0

    def test_missing_column(self):
        """person_nameカラムがない場合は空リスト"""
        df = pd.DataFrame(
            {
                "person_id": ["P001", "P002"],
                "name": ["山田太郎", "鈴木花子"],
            }
        )
        duplicates = detect_variant_duplicates(df)
        assert len(duplicates) == 0


class TestValidateNewPersonName:
    """validate_new_person_name関数のテスト"""

    def test_valid_new_name(self):
        """新規名前が重複なしの場合"""
        existing = {"山田太郎", "鈴木花子"}
        is_valid, conflict, msg = validate_new_person_name("田中次郎", existing)
        assert is_valid is True
        assert conflict is None

    def test_variant_conflict(self):
        """異体字で重複する場合"""
        existing = {"宮崎あおい"}
        is_valid, conflict, msg = validate_new_person_name("宮﨑あおい", existing)
        assert is_valid is False
        assert conflict == "宮崎あおい"
        assert "異体字重複" in msg

    def test_same_name_conflict(self):
        """完全一致は重複とみなさない（既存名を再登録）"""
        existing = {"宮崎あおい"}
        is_valid, conflict, msg = validate_new_person_name("宮崎あおい", existing)
        assert is_valid is True  # 同一名は許可


class TestIntegration:
    """統合テスト"""

    def test_normalization_consistency(self):
        """正規化の一貫性テスト"""
        # 同じ人物の異なる表記は同じ結果になる
        variants = ["宮﨑あおい", "宮崎あおい"]
        normalized = [normalize_person_name(v) for v in variants]
        assert len(set(normalized)) == 1
        assert normalized[0] == "宮崎あおい"

    def test_all_prompt_examples(self):
        """プロンプトで指定された例のテスト"""
        # 宮崎あおい / 宮﨑あおい
        assert normalize_person_name("宮崎あおい") == normalize_person_name("宮﨑あおい")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
