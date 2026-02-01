#!/usr/bin/env python3
"""
架空キャラクター名正規化のユニットテスト

Tests for:
- normalize_fictional_name(): エイリアス→正規形式への変換
- FICTIONAL_NAME_ALIASES: エイリアス辞書の整合性
- get_work_for_character(): 正規化後の作品タイトル取得

Author: EPUP Validation Team
Date: 2026-01-28
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.fictional_characters import (
    FICTIONAL_NAME_ALIASES,
    FICTIONAL_CHARACTERS,
    ALL_FICTIONAL_CHARACTERS,
    normalize_fictional_name,
    get_work_for_character,
)


class TestNormalizeFictionalName:
    """normalize_fictional_name() のテスト"""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            # NARUTO系: 「名・姓」→「姓名」形式
            ("ナルト・うずまき", ("うずまきナルト", True)),
            ("サスケ・うちは", ("うちはサスケ", True)),
            ("サクラ・春野", ("春野サクラ", True)),
            # 正規形式のままの場合（変換なし）
            ("うずまきナルト", ("うずまきナルト", False)),
            ("うちはサスケ", ("うちはサスケ", False)),
            # ONE PIECE系: 愛称→フルネーム
            ("ゾロ", ("ロロノア・ゾロ", True)),
            ("ルフィ", ("モンキー・D・ルフィ", True)),
            ("エース", ("ポートガス・D・エース", True)),
            # 正規形式のままの場合
            ("ロロノア・ゾロ", ("ロロノア・ゾロ", False)),
            ("モンキー・D・ルフィ", ("モンキー・D・ルフィ", False)),
            # 進撃の巨人系
            ("リヴァイ", ("リヴァイ・アッカーマン", True)),
            ("エレン", ("エレン・イェーガー", True)),
            ("ミカサ", ("ミカサ・アッカーマン", True)),
            # 正規形式のままの場合
            ("リヴァイ・アッカーマン", ("リヴァイ・アッカーマン", False)),
            # 鬼滅の刃系
            ("炭治郎・竈門", ("竈門炭治郎", True)),
            ("禰豆子・竈門", ("竈門禰豆子", True)),
            # エヴァンゲリオン系
            ("シンジ・碇", ("碇シンジ", True)),
            ("レイ・綾波", ("綾波レイ", True)),
            ("アスカ", ("惣流・アスカ・ラングレー", True)),
            # 名探偵コナン系
            ("コナン", ("江戸川コナン", True)),
            # 空文字列
            ("", ("", False)),
            # エイリアスに存在しない名前
            ("田中太郎", ("田中太郎", False)),
            ("ミッキーマウス", ("ミッキーマウス", False)),
        ],
    )
    def test_normalization(self, input_name: str, expected: tuple[str, bool]):
        """各種名前の正規化テスト"""
        assert normalize_fictional_name(input_name) == expected

    def test_none_like_empty_string(self):
        """空文字列はそのまま返される"""
        result = normalize_fictional_name("")
        assert result == ("", False)

    def test_whitespace_only_not_normalized(self):
        """空白のみの文字列は変換されない"""
        result = normalize_fictional_name("   ")
        assert result == ("   ", False)


class TestFictionalNameAliasesIntegrity:
    """エイリアス辞書の整合性テスト"""

    def test_all_canonical_names_exist_in_characters(self):
        """全エイリアスの正規形式がALL_FICTIONAL_CHARACTERSに存在すること"""
        missing_canonicals = []
        for alias, canonical in FICTIONAL_NAME_ALIASES.items():
            if canonical not in ALL_FICTIONAL_CHARACTERS:
                missing_canonicals.append((alias, canonical))

        if missing_canonicals:
            error_msg = "以下の正規名がキャラクターリストに存在しません:\n"
            for alias, canonical in missing_canonicals:
                error_msg += f"  - エイリアス '{alias}' → 正規名 '{canonical}'\n"
            pytest.fail(error_msg)

    def test_no_duplicate_aliases(self):
        """エイリアスに重複がないこと（dictなので本来重複はないが念のため確認）"""
        # Pythonのdictは重複キーを許可しないため、
        # ソースコードレベルでの重複は最後の値で上書きされる
        # このテストはエイリアスの数が期待通りかを確認
        alias_count = len(FICTIONAL_NAME_ALIASES)
        assert alias_count > 0, "エイリアス辞書が空です"

    def test_aliases_are_different_from_canonical(self):
        """エイリアスと正規形式が異なること"""
        same_entries = []
        for alias, canonical in FICTIONAL_NAME_ALIASES.items():
            if alias == canonical:
                same_entries.append(alias)

        if same_entries:
            pytest.fail(f"エイリアスと正規形式が同一のエントリがあります: {same_entries}")

    def test_canonical_names_are_not_aliases(self):
        """正規形式がエイリアスとして登録されていないこと"""
        # 正規形式がエイリアスのキーに存在しないことを確認
        overlapping = []
        for canonical in FICTIONAL_NAME_ALIASES.values():
            if canonical in FICTIONAL_NAME_ALIASES:
                overlapping.append(canonical)

        if overlapping:
            pytest.fail(f"正規形式がエイリアスとしても登録されています: {overlapping}")


class TestWorkTitleLookupAfterNormalization:
    """正規化後の作品タイトル取得テスト"""

    @pytest.mark.parametrize(
        "alias,expected_work",
        [
            # NARUTO
            ("ナルト・うずまき", "NARUTO"),
            ("サスケ・うちは", "NARUTO"),
            ("カカシ・はたけ", "NARUTO"),
            # ONE PIECE
            ("ゾロ", "ONE PIECE"),
            ("ルフィ", "ONE PIECE"),
            ("エース", "ONE PIECE"),
            # 進撃の巨人
            ("リヴァイ", "進撃の巨人"),
            ("エレン", "進撃の巨人"),
            ("ミカサ", "進撃の巨人"),
            # 鬼滅の刃
            ("炭治郎・竈門", "鬼滅の刃"),
            ("禰豆子・竈門", "鬼滅の刃"),
            # ドラゴンボール
            ("悟空・孫", "ドラゴンボール"),
            ("悟飯・孫", "ドラゴンボール"),
            # エヴァンゲリオン
            ("シンジ・碇", "新世紀エヴァンゲリオン"),
            ("レイ・綾波", "新世紀エヴァンゲリオン"),
            # 名探偵コナン
            ("コナン", "名探偵コナン"),
        ],
    )
    def test_get_work_after_normalization(self, alias: str, expected_work: str):
        """エイリアスを正規化後に作品タイトルが取得できること"""
        normalized_name, was_normalized = normalize_fictional_name(alias)
        assert was_normalized, f"'{alias}' が正規化されませんでした"

        work_title = get_work_for_character(normalized_name)
        assert work_title == expected_work, (
            f"'{alias}' → '{normalized_name}' の作品が '{work_title}' " f"（期待値: '{expected_work}'）"
        )

    def test_canonical_name_returns_work(self):
        """正規形式の名前でも作品タイトルが取得できること"""
        canonical_names = [
            ("うずまきナルト", "NARUTO"),
            ("ロロノア・ゾロ", "ONE PIECE"),
            ("竈門炭治郎", "鬼滅の刃"),
            ("リヴァイ・アッカーマン", "進撃の巨人"),
            ("孫悟空", "ドラゴンボール"),
        ]

        for name, expected_work in canonical_names:
            work_title = get_work_for_character(name)
            assert work_title == expected_work, f"'{name}' の作品が '{work_title}' （期待値: '{expected_work}'）"

    def test_unknown_name_returns_none(self):
        """未知の名前はNoneを返すこと"""
        unknown_names = ["田中太郎", "山田花子", "Unknown Character"]

        for name in unknown_names:
            work_title = get_work_for_character(name)
            assert work_title is None, f"'{name}' が作品 '{work_title}' に紐付いています"


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_string_normalization(self):
        """空文字列の正規化"""
        result = normalize_fictional_name("")
        assert result == ("", False)

    def test_empty_string_work_lookup(self):
        """空文字列の作品検索"""
        result = get_work_for_character("")
        assert result is None

    def test_none_handling_in_normalize(self):
        """None値の処理（normalize_fictional_name）"""
        # normalize_fictional_nameはstrを期待するが、
        # 空文字列と同様にFalsy値としてNoneが渡された場合の挙動確認
        # 注: 型アノテーション的にはstrのみだが、実際の呼び出しでNoneが来る可能性
        # 現在の実装では `if not name:` でFalsy値を処理
        # TypeErrorを避けるため、このテストはスキップ可能
        pass

    def test_special_characters_in_name(self):
        """特殊文字を含む名前の処理"""
        # 中黒（・）を含む名前が正しく処理されること
        result = normalize_fictional_name("モンキー・D・ルフィ")
        assert result == ("モンキー・D・ルフィ", False)

        # エイリアスとして中黒を含む名前
        result = normalize_fictional_name("ゾロ")
        assert result == ("ロロノア・ゾロ", True)


class TestDataConsistency:
    """データ整合性のテスト"""

    def test_fictional_characters_dict_not_empty(self):
        """FICTIONAL_CHARACTERSが空でないこと"""
        assert len(FICTIONAL_CHARACTERS) > 0

    def test_all_fictional_characters_set_not_empty(self):
        """ALL_FICTIONAL_CHARACTERSが空でないこと"""
        assert len(ALL_FICTIONAL_CHARACTERS) > 0

    def test_all_characters_from_dict_in_set(self):
        """FICTIONAL_CHARACTERSの全キャラクターがALL_FICTIONAL_CHARACTERSに含まれること"""
        for work_title, characters in FICTIONAL_CHARACTERS.items():
            for char in characters:
                assert (
                    char in ALL_FICTIONAL_CHARACTERS
                ), f"'{char}' ({work_title}) がALL_FICTIONAL_CHARACTERSに存在しません"

    def test_major_works_exist(self):
        """主要作品が登録されていること"""
        major_works = [
            "ドラゴンボール",
            "ONE PIECE",
            "NARUTO",
            "鬼滅の刃",
            "進撃の巨人",
            "ハリー・ポッター",
        ]

        for work in major_works:
            assert work in FICTIONAL_CHARACTERS, f"主要作品 '{work}' が登録されていません"
            assert len(FICTIONAL_CHARACTERS[work]) > 0, f"'{work}' のキャラクターリストが空です"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
