#!/usr/bin/env python3
"""人物名バリデーション - API関数"""

from typing import Optional

from .models import IssueType, Severity
from .validator import PersonNameValidator

# シングルトンインスタンス
_validator: Optional[PersonNameValidator] = None


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

    # ERROR または VARIANT_NAME（ALIAS_KEYWORDS違反）をFail-Fastとして扱う
    # 2025-12-21: PERSON ID統合再発防止のため、別名使用もエラーとして扱う
    critical_issues = [i for i in issues if i.severity == Severity.ERROR or i.issue_type == IssueType.VARIANT_NAME]

    if critical_issues:
        first_error = critical_issues[0]
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
