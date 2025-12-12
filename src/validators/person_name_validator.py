#!/usr/bin/env python3
"""
PersonNameValidator - 人物名バリデーション

機能:
1. グループ名検出
2. 連結名パターン検出
3. 表記ゆれ検出
4. 自動修正提案
"""

import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.group_master import (
    GROUP_ENTITIES,
    GROUP_MEMBER_MAP,
    DISPERSION_RULES,
    DispersionStrategy,
)


class IssueType(Enum):
    """検出された問題の種類"""

    GROUP_AS_PERSON = "group_as_person"
    CONCATENATED_NAME = "concatenated_name"
    VARIANT_NAME = "variant_name"
    UNKNOWN_GROUP = "unknown_group"


class Severity(Enum):
    """問題の重大度"""

    ERROR = "error"  # 即時修正必要
    WARNING = "warning"  # 修正推奨
    INFO = "info"  # 情報のみ


@dataclass
class ValidationIssue:
    """バリデーション問題"""

    issue_type: IssueType
    severity: Severity
    person_name: str
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    fixed_value: Optional[str] = None


class PersonNameValidator:
    """人物名バリデータ"""

    # グループ名＋個人名の区切りパターン
    SEPARATORS = ["・", "（", "(", "／", "/", "　", " "]

    # 誤検出除外パターン（グループ名と同名だが個人名として正しいもの）
    EXCLUDE_PERSON_NAMES = {
        # お笑いコンビ「オードリー」と同名の女優
        "オードリー・ヘプバーン",
        "オードリー・タトゥ",
    }

    def __init__(self):
        """初期化"""
        self.group_entities = GROUP_ENTITIES
        self.group_member_map = GROUP_MEMBER_MAP
        self.dispersion_rules = DISPERSION_RULES

    def validate(self, person_name: str) -> list[ValidationIssue]:
        """
        人物名をバリデーション

        Args:
            person_name: 検証対象の人物名

        Returns:
            検出された問題のリスト
        """
        issues: list[ValidationIssue] = []

        if not person_name:
            return issues

        # 除外パターンをチェック
        if person_name in self.EXCLUDE_PERSON_NAMES:
            return issues

        # 1. グループ名が直接登録されていないか
        group_issue = self._check_group_as_person(person_name)
        if group_issue:
            issues.append(group_issue)

        # 2. グループ名＋個人名の連結パターンか
        concat_issue = self._check_concatenated_name(person_name)
        if concat_issue:
            issues.append(concat_issue)

        return issues

    def _check_group_as_person(self, person_name: str) -> Optional[ValidationIssue]:
        """
        グループ名が人物名として登録されていないかチェック

        Args:
            person_name: 人物名

        Returns:
            問題があればValidationIssue、なければNone
        """
        if person_name in self.group_entities:
            # DISPERSION_RULESにルールがあるか確認
            if person_name in self.dispersion_rules:
                rule = self.dispersion_rules[person_name]
                if rule.strategy == DispersionStrategy.ALL:
                    suggestion = f"全メンバーに分散: {rule.members}"
                else:
                    suggestion = f"代表メンバーに変換: {rule.members[0]}"
                fixed_value = rule.members[0] if rule.members else None
            else:
                suggestion = "DISPERSION_RULESにルール追加が必要"
                fixed_value = None

            return ValidationIssue(
                issue_type=IssueType.GROUP_AS_PERSON,
                severity=Severity.ERROR,
                person_name=person_name,
                message=f"グループ名 '{person_name}' が人物名として登録されています",
                suggestion=suggestion,
                auto_fixable=fixed_value is not None,
                fixed_value=fixed_value,
            )

        return None

    def _check_concatenated_name(self, person_name: str) -> Optional[ValidationIssue]:
        """
        グループ名＋個人名の連結パターンをチェック

        例: "ビートルズ・ジョン・レノン" → "ジョン・レノン"

        Args:
            person_name: 人物名

        Returns:
            問題があればValidationIssue、なければNone
        """
        for group in self.group_entities:
            for sep in self.SEPARATORS:
                prefix = f"{group}{sep}"
                if person_name.startswith(prefix):
                    individual = person_name[len(prefix) :]

                    # 閉じ括弧を除去
                    individual = individual.rstrip("）)")

                    if individual:
                        return ValidationIssue(
                            issue_type=IssueType.CONCATENATED_NAME,
                            severity=Severity.ERROR,
                            person_name=person_name,
                            message=f"グループ名 '{group}' と個人名 '{individual}' が連結されています",
                            suggestion=f"個人名 '{individual}' のみに分離",
                            auto_fixable=True,
                            fixed_value=individual,
                        )

        return None

    def validate_batch(self, person_names: list[str]) -> dict:
        """
        複数の人物名をバリデーション

        Args:
            person_names: 人物名リスト

        Returns:
            {
                "total": 検証数,
                "valid": 問題なし数,
                "invalid": 問題あり数,
                "issues": 問題リスト,
                "auto_fixable": 自動修正可能数,
            }
        """
        all_issues = []

        for name in person_names:
            issues = self.validate(name)
            all_issues.extend(issues)

        auto_fixable = [i for i in all_issues if i.auto_fixable]

        return {
            "total": len(person_names),
            "valid": len(person_names) - len(set(i.person_name for i in all_issues)),
            "invalid": len(set(i.person_name for i in all_issues)),
            "issues": all_issues,
            "auto_fixable": len(auto_fixable),
        }

    def auto_fix(self, person_name: str) -> tuple[str, Optional[ValidationIssue]]:
        """
        人物名を自動修正

        Args:
            person_name: 人物名

        Returns:
            (修正後の名前, 修正した問題) のタプル
            修正不要/不可能な場合は (元の名前, None)
        """
        issues = self.validate(person_name)

        for issue in issues:
            if issue.auto_fixable and issue.fixed_value:
                return issue.fixed_value, issue

        return person_name, None

    def get_canonical_info(self, person_name: str) -> dict:
        """
        人物名から正規化された情報を取得

        Args:
            person_name: 人物名

        Returns:
            {
                "canonical_name": 正規化された個人名,
                "group_name": グループ名（所属があれば）,
                "is_group_member": グループメンバーかどうか,
                "needs_correction": 修正が必要かどうか,
                "original_name": 元の名前,
            }
        """
        result = {
            "canonical_name": person_name,
            "group_name": None,
            "is_group_member": None,
            "needs_correction": False,
            "original_name": person_name,
        }

        # 自動修正を試行
        fixed_name, issue = self.auto_fix(person_name)

        if issue:
            result["canonical_name"] = fixed_name
            result["needs_correction"] = True

            # 連結パターンの場合はグループ名を抽出
            if issue.issue_type == IssueType.CONCATENATED_NAME:
                # グループ名を取得（メッセージからパース）
                for group in self.group_entities:
                    for sep in self.SEPARATORS:
                        if person_name.startswith(f"{group}{sep}"):
                            result["group_name"] = group
                            result["is_group_member"] = True
                            break

        # グループマスタから情報を補完
        if result["canonical_name"] in self.group_member_map:
            result["group_name"] = self.group_member_map[result["canonical_name"]]
            result["is_group_member"] = True

        return result


# シングルトンインスタンス
_validator = None


def get_validator() -> PersonNameValidator:
    """バリデータのシングルトンインスタンスを取得"""
    global _validator
    if _validator is None:
        _validator = PersonNameValidator()
    return _validator


def validate_before_episode_generation(
    person_name: str, person_type: str = "REAL", group_name: Optional[str] = None
) -> tuple[bool, str, Optional[dict]]:
    """
    エピソード生成前に人物名を検証（簡易版API）

    Args:
        person_name: 人物名
        person_type: 人物タイプ
        group_name: グループ名

    Returns:
        (is_valid, message, suggested_fix)
    """
    validator = get_validator()
    issues = validator.validate(person_name)

    errors = [i for i in issues if i.severity == Severity.ERROR]

    if errors:
        first_error = errors[0]
        suggested_fix = None
        if first_error.auto_fixable and first_error.fixed_value:
            suggested_fix = {
                "person_name": first_error.fixed_value,
            }
            # グループ名を抽出
            canonical_info = validator.get_canonical_info(person_name)
            if canonical_info.get("group_name"):
                suggested_fix["group_name"] = canonical_info["group_name"]
                suggested_fix["is_group_member"] = True

        return False, first_error.message, suggested_fix

    return True, "OK", None
