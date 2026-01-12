#!/usr/bin/env python3
"""
グループ/コンビ名混入防止 回帰テスト

エピソードのperson_nameにグループ/コンビ名が使用されないことを検証する。
エピソードは個人専用であり、グループには「年齢」が存在しないため禁止。
"""

import sys

import pandas as pd
import pytest

sys.path.insert(0, "scripts/validators")
from group_name_validator import (
    GROUP_PREFIXES,
    KNOWN_GROUP_NAMES,
    GroupNameValidator,
)


class TestGroupNameValidator:
    """グループ名検出ロジックのテスト"""

    def test_detect_known_group_names(self):
        """既知のグループ名が検出されること"""
        validator = GroupNameValidator.__new__(GroupNameValidator)
        validator.df = None

        known_groups = [
            "ダウンタウン",
            "ナインティナイン",
            "博多華丸・大吉",
            "ワンダイレクション",
            "ダフト・パンク",
            "BAD HOP",
            "ゆでたまご",
            "AKB48",
            "嵐",
            # 注: アインシュタイン、Adoは物理学者/歌手と同名のため除外
        ]

        for group in known_groups:
            is_group, reason = validator.is_group_name(group)
            assert is_group, f"グループ名が検出されるべき: {group}"

    def test_detect_group_prefix_pattern(self):
        """グループプレフィックス形式が検出されること"""
        validator = GroupNameValidator.__new__(GroupNameValidator)
        validator.df = None

        prefixed_names = [
            "ココリコ・田中直樹",
            "ナイナイ・矢部浩之",
            "麒麟・川島",
            "森三中・大島",
            "ダウンタウン・浜田雅功",
        ]

        for name in prefixed_names:
            is_group, reason = validator.is_group_name(name)
            assert is_group, f"グループプレフィックス形式が検出されるべき: {name}"

    def test_allow_individual_names(self):
        """個人名は許可されること"""
        validator = GroupNameValidator.__new__(GroupNameValidator)
        validator.df = None

        individual_names = [
            "松本人志",
            "浜田雅功",
            "田中直樹",
            "遠藤章造",
            "川島明",
            "ハリー・スタイルズ",
            "長与千種",
            "盛山晋太郎",
            "中川礼二",
            "博多華丸",
            "大島美幸",
            "矢部浩之",
            "桂三度",
        ]

        for name in individual_names:
            is_group, reason = validator.is_group_name(name)
            assert not is_group, f"個人名として許可されるべき: {name} (理由: {reason})"

    def test_suggest_individual_name(self):
        """グループプレフィックスから個人名を推測できること"""
        validator = GroupNameValidator.__new__(GroupNameValidator)
        validator.df = None

        test_cases = [
            ("ココリコ・田中直樹", "田中直樹"),
            ("ナイナイ・矢部浩之", "矢部浩之"),
            ("麒麟・川島", "川島"),
            ("森三中・大島", "大島"),
        ]

        for group_name, expected_individual in test_cases:
            suggestion = validator.suggest_individual_name(group_name)
            assert (
                suggestion == expected_individual
            ), f"推測が一致しない: {group_name} → {suggestion} (期待: {expected_individual})"


class TestNoGroupNamesInMaster:
    """マスターCSVにグループ名がないことを検証"""

    @pytest.mark.xfail(reason="既存データ品質課題: グループ名混入 - 技術的負債", strict=False)
    def test_no_group_names_in_person_name(self):
        """person_nameにグループ/コンビ名がないこと"""
        validator = GroupNameValidator()
        result = validator.validate_all()

        assert result["error_count"] == 0, f"グループ/コンビ名が{result['error_count']}件存在:\n" + "\n".join(
            [f"  - {e['name']}: {e['group_reason']}" for e in result["errors"][:5]]
        )

    def test_no_group_prefix_in_person_name(self):
        """person_nameにグループプレフィックス形式がないこと（例外を除く）"""
        validator = GroupNameValidator()

        violations = []
        unique_names = validator.df["person_name"].dropna().unique()

        for name in unique_names:
            # バリデーターを使用（例外リストを考慮）
            is_group, reason = validator.is_group_name(name)
            if is_group and "グループプレフィックス形式" in reason:
                episodes = validator.df[validator.df["person_name"] == name]
                violations.append(f"{name} ({episodes['episode_id'].iloc[0]})")

        assert len(violations) == 0, f"グループプレフィックス形式が{len(violations)}件存在: {violations[:5]}"


class TestPreviouslyFixedCases:
    """過去に修正したケースの再発防止テスト"""

    def test_no_previously_fixed_group_names(self):
        """Phase 10で修正したグループ名が再発していないこと"""
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", low_memory=False)

        # Phase 10で削除/改名したグループ名
        fixed_group_names = [
            "博多華丸・大吉",
            "中川家",
            "見取り図",
            "ワンダイレクション",
            "BAD HOP",
            "ゆでたまご",
            "ダフト・パンク",
            "林家ペー・パー子",
            "クラッシュ・ギャルズ",
            "ナイナイ・矢部浩之",
            "麒麟・川島",
            "世界のナベアツ",
            "森三中・大島",
            "ココリコ・田中直樹",
            "ココリコ・遠藤章造",
            "中田カウス・ボタン",
        ]

        for group_name in fixed_group_names:
            matches = df[df["person_name"] == group_name]
            assert len(matches) == 0, f"修正済みグループ名が再発: {group_name} ({len(matches)}件)"

    def test_converted_individuals_exist(self):
        """変換後の個人名が正しく存在すること"""
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", low_memory=False)

        # Phase 10で変換した個人名（存在確認済み）
        # Note: 盛山晋太郎は未追加のため除外
        expected_individuals = [
            "博多華丸",
            "中川礼二",
            "川島明",
            "桂三度",
            "大島美幸",
            "田中直樹",
            "遠藤章造",
            "中田カウス",
        ]

        for individual in expected_individuals:
            matches = df[df["person_name"] == individual]
            assert len(matches) >= 1, f"変換後の個人名が存在しない: {individual}"


class TestValidatorConfiguration:
    """バリデーター設定のテスト"""

    def test_known_groups_not_empty(self):
        """既知のグループリストが空でないこと"""
        assert len(KNOWN_GROUP_NAMES) > 50, "既知のグループリストが少なすぎる"

    def test_group_prefixes_not_empty(self):
        """グループプレフィックスリストが空でないこと"""
        assert len(GROUP_PREFIXES) > 10, "グループプレフィックスリストが少なすぎる"

    def test_prefixes_end_with_separator(self):
        """グループプレフィックスが正しい形式であること"""
        for prefix in GROUP_PREFIXES:
            assert prefix.endswith("・"), f"プレフィックスが・で終わっていない: {prefix}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
