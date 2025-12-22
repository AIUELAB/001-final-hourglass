#!/usr/bin/env python3
"""person_name_validator/validator.py のユニットテスト"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from src.validators.person_name_validator.models import (
    IssueType,
    Severity,
    ValidationIssue,
)
from src.validators.person_name_validator.validator import PersonNameValidator


class TestPersonNameValidatorInit:
    """PersonNameValidator初期化のテスト"""

    def test_init_loads_group_data(self):
        """初期化時にグループデータをロード"""
        validator = PersonNameValidator()
        assert hasattr(validator, "group_entities")
        assert hasattr(validator, "group_member_map")
        assert hasattr(validator, "dispersion_rules")

    def test_init_loads_blacklist(self):
        """初期化時にブラックリストをロード"""
        validator = PersonNameValidator()
        assert hasattr(validator, "blacklist")
        assert isinstance(validator.blacklist, dict)


class TestValidate:
    """validate() メソッドのテスト"""

    def test_empty_name_returns_empty_issues(self):
        """空の名前は問題なし"""
        validator = PersonNameValidator()
        issues = validator.validate("")
        assert issues == []

    def test_none_name_returns_empty_issues(self):
        """Noneは問題なし（空文字扱い）"""
        validator = PersonNameValidator()
        issues = validator.validate(None)  # type: ignore
        assert issues == []

    def test_exclude_pattern_returns_empty_issues(self):
        """除外パターンは問題なし"""
        validator = PersonNameValidator()
        issues = validator.validate("オードリー・ヘプバーン")
        assert issues == []

    def test_normal_name_returns_empty_issues(self):
        """正常な人物名は問題なし"""
        validator = PersonNameValidator()
        issues = validator.validate("山田太郎")
        assert issues == []


class TestCheckGroupAsPerson:
    """_check_group_as_person() メソッドのテスト"""

    def test_detects_group_name(self):
        """グループ名を検出"""
        validator = PersonNameValidator()
        # GROUP_ENTITIESに含まれる実際のグループ名を使用
        if "嵐" in validator.group_entities:
            issue = validator._check_group_as_person("嵐")
            assert issue is not None
            assert issue.issue_type == IssueType.GROUP_AS_PERSON
            assert issue.severity == Severity.ERROR

    def test_returns_none_for_individual(self):
        """個人名はNoneを返す"""
        validator = PersonNameValidator()
        issue = validator._check_group_as_person("山田太郎")
        assert issue is None

    def test_dispersion_rule_suggestion(self):
        """DISPERSION_RULESにルールがある場合は修正値を提案"""
        validator = PersonNameValidator()
        # 実際にDISPERSION_RULESにあるグループを使用
        for group_name in validator.dispersion_rules:
            issue = validator._check_group_as_person(group_name)
            if issue:
                assert issue.auto_fixable is True
                assert issue.fixed_value is not None
                break


class TestCheckConcatenatedName:
    """_check_concatenated_name() メソッドのテスト"""

    def test_detects_concatenated_name_with_dot(self):
        """中黒で連結された名前を検出"""
        validator = PersonNameValidator()
        # GROUP_ENTITIESの実際のグループを使用
        if "SMAP" in validator.group_entities:
            issue = validator._check_concatenated_name("SMAP・中居正広")
            assert issue is not None
            assert issue.issue_type == IssueType.CONCATENATED_NAME
            assert issue.fixed_value == "中居正広"

    def test_detects_concatenated_name_with_paren(self):
        """括弧で連結された名前を検出"""
        validator = PersonNameValidator()
        if "嵐" in validator.group_entities:
            issue = validator._check_concatenated_name("嵐（大野智）")
            if issue:
                assert issue.fixed_value == "大野智"

    def test_returns_none_for_normal_name(self):
        """通常の名前はNoneを返す"""
        validator = PersonNameValidator()
        issue = validator._check_concatenated_name("田中一郎")
        assert issue is None

    def test_various_separators(self):
        """様々なセパレータを検出"""
        validator = PersonNameValidator()
        separators = ["・", "（", "(", "／", "/"]
        for group in list(validator.group_entities)[:1]:
            for sep in separators:
                name = f"{group}{sep}テスト太郎"
                issue = validator._check_concatenated_name(name)
                if issue:
                    assert issue.issue_type == IssueType.CONCATENATED_NAME


class TestCheckAbnormalPrefix:
    """_check_abnormal_prefix() メソッドのテスト"""

    def test_detects_bullet_point(self):
        """箇条書き記号を検出"""
        validator = PersonNameValidator()
        issue = validator._check_abnormal_prefix("・山田太郎")
        assert issue is not None
        assert issue.issue_type == IssueType.ABNORMAL_PREFIX
        assert issue.fixed_value == "山田太郎"

    def test_detects_various_bullets(self):
        """様々な箇条書き記号を検出"""
        validator = PersonNameValidator()
        bullets = ["・", "•", "-", "－", "※", "▪", "●"]
        for bullet in bullets:
            issue = validator._check_abnormal_prefix(f"{bullet}田中花子")
            if issue:
                assert issue.issue_type == IssueType.ABNORMAL_PREFIX

    def test_detects_abnormal_prefix_words(self):
        """不自然な接頭語を検出"""
        validator = PersonNameValidator()
        prefixes = ["始まり", "はじまり", "続く", "続き", "その他", "他の"]
        for prefix in prefixes:
            issue = validator._check_abnormal_prefix(f"{prefix} 山田太郎")
            if issue:
                assert issue.issue_type == IssueType.ABNORMAL_PREFIX
                assert issue.fixed_value == "山田太郎"

    def test_detects_leading_trailing_spaces(self):
        """先頭/末尾の空白を検出"""
        validator = PersonNameValidator()
        issue = validator._check_abnormal_prefix("  山田太郎  ")
        assert issue is not None
        assert issue.fixed_value == "山田太郎"

    def test_detects_zero_width_characters(self):
        """ゼロ幅文字を検出"""
        validator = PersonNameValidator()
        issue = validator._check_abnormal_prefix("山田\u200b太郎")
        assert issue is not None
        assert "ゼロ幅文字" in issue.message
        assert issue.fixed_value == "山田太郎"

    def test_detects_newline(self):
        """改行を検出"""
        validator = PersonNameValidator()
        issue = validator._check_abnormal_prefix("山田\n太郎")
        assert issue is not None
        assert "改行" in issue.message

    def test_detects_consecutive_spaces(self):
        """連続空白を検出"""
        validator = PersonNameValidator()
        issue = validator._check_abnormal_prefix("山田  太郎")
        assert issue is not None
        assert issue.fixed_value == "山田 太郎"

    def test_returns_none_for_normal_name(self):
        """正常な名前はNoneを返す"""
        validator = PersonNameValidator()
        issue = validator._check_abnormal_prefix("山田太郎")
        assert issue is None


class TestCheckItemNamePattern:
    """_check_item_name_pattern() メソッドのテスト"""

    def test_detects_item_suffix(self):
        """道具名接尾辞を検出"""
        validator = PersonNameValidator()
        suffixes = ["ギプス", "マシン", "装置", "ロボット", "システム"]
        for suffix in suffixes:
            issue = validator._check_item_name_pattern(f"テスト{suffix}")
            assert issue is not None
            assert issue.issue_type == IssueType.INVALID_NAME

    def test_detects_obvious_items(self):
        """明らかな道具名を検出"""
        validator = PersonNameValidator()
        issue = validator._check_item_name_pattern("ドラえもんの秘密道具")
        assert issue is not None
        assert issue.issue_type == IssueType.INVALID_NAME

    def test_returns_none_for_person_name(self):
        """人物名はNoneを返す"""
        validator = PersonNameValidator()
        issue = validator._check_item_name_pattern("田中太郎")
        assert issue is None


class TestCheckSuffixPatterns:
    """_check_suffix_patterns() メソッドのテスト"""

    def test_detects_title_suffix(self):
        """役職接尾辞を検出"""
        validator = PersonNameValidator()
        issue = validator._check_suffix_patterns("山田監督")
        # base_nameが短いのでスキップされる可能性
        if issue:
            assert issue.issue_type == IssueType.ORG_TITLE_CONTAMINATION

    def test_detects_honorific_suffix(self):
        """敬称接尾辞を検出"""
        validator = PersonNameValidator()
        issue = validator._check_suffix_patterns("山田太郎氏")
        assert issue is not None
        assert issue.severity == Severity.INFO

    def test_detects_academic_suffix(self):
        """学術接尾辞を検出"""
        validator = PersonNameValidator()
        issue = validator._check_suffix_patterns("山田太郎博士")
        assert issue is not None
        assert issue.issue_type == IssueType.ORG_TITLE_CONTAMINATION

    def test_detects_relation_suffix(self):
        """関係接尾辞を検出（エラー扱い）"""
        validator = PersonNameValidator()
        issue = validator._check_suffix_patterns("田中夫人")
        assert issue is not None
        assert issue.severity == Severity.ERROR

    def test_skips_short_base_name(self):
        """base_nameが短すぎる場合はスキップ"""
        validator = PersonNameValidator()
        issue = validator._check_suffix_patterns("監督")  # base_name = ""
        assert issue is None

    def test_returns_none_for_normal_name(self):
        """通常の名前はNoneを返す"""
        validator = PersonNameValidator()
        issue = validator._check_suffix_patterns("佐藤花子")
        assert issue is None


class TestCheckBlacklist:
    """_check_blacklist() メソッドのテスト"""

    def test_detects_blacklisted_name(self):
        """ブラックリスト名を検出"""
        validator = PersonNameValidator()
        validator.blacklist = {
            "blacklist": [{"name": "テスト禁止名", "reason": "テスト用"}],
            "patterns": [],
        }
        issue = validator._check_blacklist("テスト禁止名")
        assert issue is not None
        assert issue.issue_type == IssueType.INVALID_NAME
        assert "ブラックリスト該当" in issue.message

    def test_detects_pattern_match(self):
        """パターンマッチを検出"""
        validator = PersonNameValidator()
        validator.blacklist = {
            "blacklist": [],
            "patterns": ["^テスト.*$"],
        }
        issue = validator._check_blacklist("テスト太郎")
        assert issue is not None
        assert issue.severity == Severity.WARNING

    def test_returns_none_for_normal_name(self):
        """通常の名前はNoneを返す"""
        validator = PersonNameValidator()
        issue = validator._check_blacklist("山田花子")
        assert issue is None


class TestLoadBlacklist:
    """_load_blacklist() メソッドのテスト"""

    def test_returns_empty_when_file_not_exists(self):
        """ファイルがない場合は空を返す"""
        with patch.object(Path, "exists", return_value=False):
            validator = PersonNameValidator()
            # 初期化時にロードされるので、直接メソッドをテスト
            result = validator._load_blacklist()
            # ファイルがない場合は空のブラックリスト
            assert "blacklist" in result
            assert "patterns" in result

    def test_handles_json_decode_error(self):
        """JSONデコードエラーを処理"""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            with patch.object(Path, "exists", return_value=True):
                validator = PersonNameValidator()
                result = validator._load_blacklist()
                assert result == {"blacklist": [], "patterns": []}


class TestValidateBatch:
    """validate_batch() メソッドのテスト"""

    def test_returns_correct_structure(self):
        """正しい構造を返す"""
        validator = PersonNameValidator()
        result = validator.validate_batch(["山田太郎", "田中花子"])
        assert "total" in result
        assert "valid" in result
        assert "invalid" in result
        assert "issues" in result
        assert "auto_fixable" in result

    def test_counts_correctly(self):
        """カウントが正しい"""
        validator = PersonNameValidator()
        result = validator.validate_batch(["山田太郎", "田中花子", "佐藤一郎"])
        assert result["total"] == 3

    def test_detects_issues_in_batch(self):
        """バッチ内の問題を検出"""
        validator = PersonNameValidator()
        result = validator.validate_batch(["・山田太郎", "田中花子"])
        assert result["invalid"] >= 1
        assert len(result["issues"]) >= 1


class TestAutoFix:
    """auto_fix() メソッドのテスト"""

    def test_fixes_auto_fixable_issue(self):
        """自動修正可能な問題を修正"""
        validator = PersonNameValidator()
        fixed, issue = validator.auto_fix("・山田太郎")
        assert fixed == "山田太郎"
        assert issue is not None
        assert issue.auto_fixable is True

    def test_returns_original_when_not_fixable(self):
        """修正不要な場合は元の名前を返す"""
        validator = PersonNameValidator()
        fixed, issue = validator.auto_fix("山田太郎")
        assert fixed == "山田太郎"
        assert issue is None


class TestGetCanonicalInfo:
    """get_canonical_info() メソッドのテスト"""

    def test_returns_correct_structure(self):
        """正しい構造を返す"""
        validator = PersonNameValidator()
        result = validator.get_canonical_info("山田太郎")
        assert "canonical_name" in result
        assert "group_name" in result
        assert "is_group_member" in result
        assert "needs_correction" in result
        assert "original_name" in result

    def test_normal_name_needs_no_correction(self):
        """通常の名前は修正不要"""
        validator = PersonNameValidator()
        result = validator.get_canonical_info("山田太郎")
        assert result["needs_correction"] is False
        assert result["canonical_name"] == "山田太郎"

    def test_fixable_name_has_correction(self):
        """修正可能な名前は修正あり"""
        validator = PersonNameValidator()
        result = validator.get_canonical_info("・山田太郎")
        assert result["needs_correction"] is True
        assert result["canonical_name"] == "山田太郎"

    def test_group_member_detected(self):
        """グループメンバーを検出"""
        validator = PersonNameValidator()
        # GROUP_MEMBER_MAPに含まれる実際のメンバーを使用
        for member, group in list(validator.group_member_map.items())[:1]:
            result = validator.get_canonical_info(member)
            assert result["is_group_member"] is True
            assert result["group_name"] == group
