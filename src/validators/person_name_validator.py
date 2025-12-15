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
    ORG_TITLE_CONTAMINATION = "org_title_contamination"  # 組織名・肩書き混入


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

        # 組織名・肩書き混入検出用のnormalizer（遅延初期化）
        self._normalizer = None

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

        # 3. 組織名・肩書き混入チェック（新規）
        org_title_issue = self._check_org_title_contamination(person_name)
        if org_title_issue:
            issues.append(org_title_issue)

        # 4. 別名・通称チェック（2025-12-15追加）★NEW
        alias_issue = self._check_alias_usage(person_name)
        if alias_issue:
            issues.append(alias_issue)

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

    def _get_normalizer(self):
        """PersonNameNormalizerを遅延初期化して取得"""
        if self._normalizer is None:
            # 循環インポート回避のため、ここでインポート
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from scripts.normalize_person_names import PersonNameNormalizer

            self._normalizer = PersonNameNormalizer(min_confidence=0.85)
        return self._normalizer

    def _check_org_title_contamination(self, person_name: str) -> Optional[ValidationIssue]:
        """
        組織名・肩書き混入をチェック

        例:
        - 「日本人実業家の稲盛和夫」 → 「稲盛和夫」
        - 「辻調 辻芳樹」 → 「辻芳樹」
        - 「維新松井一郎」 → 「松井一郎」
        - 「お笑い・とんねるず石橋貴明」 → 「石橋貴明」

        Args:
            person_name: 人物名

        Returns:
            問題があればValidationIssue、なければNone
        """
        normalizer = self._get_normalizer()
        result = normalizer.normalize(person_name)

        if result:
            # 正規化が必要 = 組織名・肩書き混入あり
            detail = f"パターン: {result.pattern_type}"
            if result.title:
                detail += f", 肩書: {result.title}"
            if result.affiliation:
                detail += f", 所属: {result.affiliation}"

            return ValidationIssue(
                issue_type=IssueType.ORG_TITLE_CONTAMINATION,
                severity=Severity.ERROR,
                person_name=person_name,
                message=f"人物名に組織名・肩書きが混入: '{person_name}' → '{result.normalized_name}' ({detail})",
                suggestion=f"正規化後の名前 '{result.normalized_name}' を使用してください",
                auto_fixable=True,
                fixed_value=result.normalized_name,
            )

        return None

    def _check_alias_usage(self, person_name: str) -> Optional[ValidationIssue]:
        """
        別名・通称の使用を検出

        例: 「山中教授」→「山中伸弥」を使用すべき

        Args:
            person_name: 人物名

        Returns:
            問題があればValidationIssue、なければNone
        """
        # normalize_person_names.pyのALIAS_KEYWORDSを参照
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from scripts.normalize_person_names import ALIAS_KEYWORDS

        if person_name in ALIAS_KEYWORDS:
            canonical = ALIAS_KEYWORDS[person_name]
            return ValidationIssue(
                issue_type=IssueType.VARIANT_NAME,
                severity=Severity.WARNING,
                person_name=person_name,
                message=f"別名「{person_name}」が使用されています",
                suggestion=f"正規表記「{canonical}」を使用してください",
                auto_fixable=True,
                fixed_value=canonical,
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
        result: dict[str, str | bool | None] = {
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
        canonical_name = result["canonical_name"]
        if isinstance(canonical_name, str) and canonical_name in self.group_member_map:
            result["group_name"] = self.group_member_map[canonical_name]
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
        suggested_fix: Optional[dict[str, str | bool]] = None
        if first_error.auto_fixable and first_error.fixed_value:
            suggested_fix = {
                "person_name": first_error.fixed_value,
            }
            # グループ名を抽出
            canonical_info = validator.get_canonical_info(person_name)
            group_name = canonical_info.get("group_name")
            if group_name and isinstance(group_name, str):
                suggested_fix["group_name"] = group_name
                suggested_fix["is_group_member"] = True

        return False, first_error.message, suggested_fix

    return True, "OK", None
