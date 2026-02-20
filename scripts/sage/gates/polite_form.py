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
    """丁寧語チェック（無効化済み: 常体が正しい前提）"""
    return PoliteFormCheckResult(
        passed=True,
        issue_count=0,
        message="丁寧語チェック無効（常体正規化済み）",
    )


def auto_fix_polite_form(
    episode_text: str,
    max_risk: str = "low",
) -> str:
    """丁寧語自動修正（無効化済み: 常体が正しい前提）"""
    return episode_text


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
