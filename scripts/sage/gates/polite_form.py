#!/usr/bin/env python3
"""
丁寧語ゲート - 文体統一チェック

新規生成/更新時に丁寧語漏れをチェックし、
必要に応じて自動修正する。

使用法:
    from scripts.sage.gates.polite_form import check_polite_form, auto_fix_polite_form

    # チェックのみ
    result = check_polite_form(episode_text)
    if not result.passed:
        print(f"問題: {result.issues}")

    # 自動修正
    fixed_text = auto_fix_polite_form(episode_text)
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.polite_form_normalizer import PoliteFormNormalizer


@dataclass
class PoliteFormCheckResult:
    """丁寧語チェック結果"""

    passed: bool
    issue_count: int = 0
    issues: list[dict] = field(default_factory=list)
    message: str = ""


# シングルトンインスタンス
_normalizer: Optional[PoliteFormNormalizer] = None


def _get_normalizer() -> PoliteFormNormalizer:
    """正規化エンジンのシングルトン取得"""
    global _normalizer
    if _normalizer is None:
        _normalizer = PoliteFormNormalizer()
    return _normalizer


def check_polite_form(
    episode_text: str,
    strict: bool = False,
) -> PoliteFormCheckResult:
    """
    エピソードテキストの丁寧語チェック

    Args:
        episode_text: チェック対象のテキスト
        strict: True=1件でもあれば失敗、False=許容範囲内なら通過

    Returns:
        PoliteFormCheckResult: チェック結果
    """
    if not episode_text:
        return PoliteFormCheckResult(
            passed=True,
            issue_count=0,
            message="テキストなし",
        )

    normalizer = _get_normalizer()
    issues = normalizer.detect_issues(episode_text)

    if not issues:
        return PoliteFormCheckResult(
            passed=True,
            issue_count=0,
            message="丁寧語チェック通過",
        )

    # 厳格モード: 1件でもあれば失敗
    if strict:
        return PoliteFormCheckResult(
            passed=False,
            issue_count=len(issues),
            issues=issues,
            message=f"丁寧語漏れ検出: {len(issues)}件",
        )

    # 非厳格モード: 3件以上で失敗
    threshold = 3
    if len(issues) >= threshold:
        return PoliteFormCheckResult(
            passed=False,
            issue_count=len(issues),
            issues=issues,
            message=f"丁寧語漏れ検出: {len(issues)}件 (閾値{threshold}超)",
        )

    return PoliteFormCheckResult(
        passed=True,
        issue_count=len(issues),
        issues=issues,
        message=f"丁寧語漏れ軽微: {len(issues)}件 (許容範囲内)",
    )


def auto_fix_polite_form(
    episode_text: str,
    max_risk: str = "low",
) -> str:
    """
    エピソードテキストの丁寧語を自動修正

    Args:
        episode_text: 修正対象のテキスト
        max_risk: 適用ルールの最大リスク (low/medium/high)

    Returns:
        str: 修正後のテキスト
    """
    if not episode_text:
        return episode_text

    normalizer = _get_normalizer()
    fixed_text, changes = normalizer.transform_text(
        episode_text,
        max_risk=max_risk,
        dry_run=False,
    )

    return fixed_text


def check_and_fix_polite_form(
    episode_text: str,
    auto_fix: bool = True,
    max_risk: str = "low",
    strict: bool = False,
) -> tuple[PoliteFormCheckResult, str]:
    """
    チェックと修正を一括実行

    Args:
        episode_text: 対象テキスト
        auto_fix: True=修正も実行
        max_risk: 修正時の最大リスク
        strict: チェックの厳格度

    Returns:
        tuple[PoliteFormCheckResult, str]: (チェック結果, 修正後テキスト)
    """
    result = check_polite_form(episode_text, strict=strict)

    if result.passed or not auto_fix:
        return result, episode_text

    fixed_text = auto_fix_polite_form(episode_text, max_risk=max_risk)

    # 修正後に再チェック
    result_after = check_polite_form(fixed_text, strict=strict)

    return result_after, fixed_text


# ゲートインターフェース（他のゲートとの統一）
def gate_check(episode_text: str, **kwargs) -> dict:
    """
    ゲート統一インターフェース

    Returns:
        dict: {
            "passed": bool,
            "gate_name": str,
            "message": str,
            "details": dict
        }
    """
    strict = kwargs.get("strict", False)
    result = check_polite_form(episode_text, strict=strict)

    return {
        "passed": result.passed,
        "gate_name": "polite_form",
        "message": result.message,
        "details": {
            "issue_count": result.issue_count,
            "issues": result.issues[:5],  # 最大5件
        },
    }
