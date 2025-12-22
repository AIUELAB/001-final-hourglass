#!/usr/bin/env python3
"""person_name_validator/api.py のユニットテスト"""

from unittest.mock import MagicMock, patch

import pytest

from src.validators.person_name_validator.api import (
    _validator,
    get_validator,
    validate_before_episode_generation,
)
from src.validators.person_name_validator.models import (
    IssueType,
    Severity,
    ValidationIssue,
)
from src.validators.person_name_validator.validator import PersonNameValidator


class TestGetValidator:
    """get_validator() のテスト"""

    def test_returns_validator_instance(self):
        """PersonNameValidatorインスタンスを返す"""
        validator = get_validator()
        assert isinstance(validator, PersonNameValidator)

    def test_singleton_returns_same_instance(self):
        """シングルトンとして同じインスタンスを返す"""
        v1 = get_validator()
        v2 = get_validator()
        assert v1 is v2

    def test_creates_new_instance_when_none(self):
        """_validatorがNoneの場合、新しいインスタンスを作成"""
        import src.validators.person_name_validator.api as api_module

        original = api_module._validator
        try:
            api_module._validator = None
            validator = get_validator()
            assert validator is not None
            assert isinstance(validator, PersonNameValidator)
        finally:
            api_module._validator = original


class TestValidateBeforeEpisodeGeneration:
    """validate_before_episode_generation() のテスト"""

    def test_valid_name_returns_true(self):
        """正常な人物名はTrueを返す"""
        is_valid, message, fix = validate_before_episode_generation("山田太郎")
        assert is_valid is True
        assert message == "OK"
        assert fix is None

    def test_returns_error_for_critical_issue(self):
        """重大な問題がある場合はFalseを返す"""
        with patch.object(PersonNameValidator, "validate") as mock_validate:
            mock_validate.return_value = [
                ValidationIssue(
                    issue_type=IssueType.GROUP_AS_PERSON,
                    severity=Severity.ERROR,
                    person_name="嵐",
                    message="グループ名が人物名として登録されています",
                    auto_fixable=False,
                )
            ]
            is_valid, message, fix = validate_before_episode_generation("嵐")

        assert is_valid is False
        assert "グループ名" in message
        assert fix is None

    def test_variant_name_treated_as_error(self):
        """VARIANT_NAMEはエラーとして扱われる"""
        with patch.object(PersonNameValidator, "validate") as mock_validate:
            mock_validate.return_value = [
                ValidationIssue(
                    issue_type=IssueType.VARIANT_NAME,
                    severity=Severity.WARNING,  # WARNINGでもエラー扱い
                    person_name="木村拓也",
                    message="別名が使用されています",
                    auto_fixable=True,
                    fixed_value="木村拓哉",
                )
            ]
            is_valid, message, fix = validate_before_episode_generation("木村拓也")

        assert is_valid is False
        assert "別名" in message

    def test_returns_suggested_fix_when_auto_fixable(self):
        """自動修正可能な場合は修正値を返す"""
        with patch.object(PersonNameValidator, "validate") as mock_validate:
            with patch.object(PersonNameValidator, "get_canonical_info") as mock_info:
                mock_validate.return_value = [
                    ValidationIssue(
                        issue_type=IssueType.CONCATENATED_NAME,
                        severity=Severity.ERROR,
                        person_name="嵐・大野智",
                        message="連結名が検出されました",
                        auto_fixable=True,
                        fixed_value="大野智",
                    )
                ]
                mock_info.return_value = {"group_name": "嵐"}

                is_valid, message, fix = validate_before_episode_generation("嵐・大野智")

        assert is_valid is False
        assert fix is not None
        assert fix["person_name"] == "大野智"
        assert fix["group_name"] == "嵐"
        assert fix["is_group_member"] is True

    def test_no_group_name_in_fix_when_not_group_member(self):
        """グループ名がない場合はfixにgroup_nameを含まない"""
        with patch.object(PersonNameValidator, "validate") as mock_validate:
            with patch.object(PersonNameValidator, "get_canonical_info") as mock_info:
                mock_validate.return_value = [
                    ValidationIssue(
                        issue_type=IssueType.VARIANT_NAME,
                        severity=Severity.ERROR,
                        person_name="イチロー",
                        message="別名が使用されています",
                        auto_fixable=True,
                        fixed_value="鈴木一朗",
                    )
                ]
                mock_info.return_value = {}  # グループ名なし

                is_valid, message, fix = validate_before_episode_generation("イチロー")

        assert is_valid is False
        assert fix is not None
        assert fix["person_name"] == "鈴木一朗"
        assert "group_name" not in fix
        assert "is_group_member" not in fix

    def test_warning_only_returns_valid(self):
        """WARNINGのみの場合はTrueを返す（VARIANT_NAME以外）"""
        with patch.object(PersonNameValidator, "validate") as mock_validate:
            mock_validate.return_value = [
                ValidationIssue(
                    issue_type=IssueType.PROFESSION_PREFIX,
                    severity=Severity.WARNING,
                    person_name="歌手・山田太郎",
                    message="職業接頭辞が検出されました",
                    auto_fixable=True,
                    fixed_value="山田太郎",
                )
            ]
            is_valid, message, fix = validate_before_episode_generation("歌手・山田太郎")

        assert is_valid is True
        assert message == "OK"
        assert fix is None

    def test_empty_issues_returns_valid(self):
        """問題がない場合はTrueを返す"""
        with patch.object(PersonNameValidator, "validate") as mock_validate:
            mock_validate.return_value = []
            is_valid, message, fix = validate_before_episode_generation("正常な名前")

        assert is_valid is True
        assert message == "OK"
        assert fix is None
