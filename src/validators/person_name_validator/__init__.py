#!/usr/bin/env python3
"""人物名バリデーション パッケージ

機能:
1. グループ名検出
2. 連結名パターン検出
3. 表記ゆれ検出
4. 自動修正提案
"""

from .api import get_validator, validate_before_episode_generation
from .models import IssueType, Severity, ValidationIssue
from .validator import PersonNameValidator

__all__ = [
    # Models
    "IssueType",
    "Severity",
    "ValidationIssue",
    # Validator
    "PersonNameValidator",
    # API
    "get_validator",
    "validate_before_episode_generation",
]
