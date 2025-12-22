#!/usr/bin/env python3
"""人物名バリデーション - データモデル"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IssueType(Enum):
    """検出された問題の種類"""

    GROUP_AS_PERSON = "group_as_person"
    CONCATENATED_NAME = "concatenated_name"
    VARIANT_NAME = "variant_name"
    UNKNOWN_GROUP = "unknown_group"
    ORG_TITLE_CONTAMINATION = "org_title_contamination"  # 組織名・肩書き混入
    INVALID_NAME = "invalid_name"  # 不正な人物名（道具名・アイテム名等）
    PROFESSION_PREFIX = "profession_prefix"  # 職業接頭辞パターン（Phase 8追加）
    ABNORMAL_PREFIX = "abnormal_prefix"  # 先頭不自然記号（2025-12-21追加）


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
