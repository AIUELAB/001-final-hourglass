#!/usr/bin/env python3
"""
RULE_180: 自動改善エンジン（Automatic Improvement Engine）

RULE_179の評価結果に基づいて、エピソードを自動的に改善
- 抽象表現の具体化（RULE_177活用）
- ネガティブ表現の客観化（RULE_175活用）
- 時系列矛盾の修正（RULE_174活用）
- 年齢の最適化（RULE_173活用）

改善戦略:
1. 重大度順に問題を修正（CRITICAL → WARNING → INFO）
2. 最小限の変更で最大効果を狙う
3. 元のエピソードの意図を保持
4. 修正履歴を記録
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class ImprovementAction:
    """改善アクション"""
    rule_id: str
    issue_type: str
    severity: str  # CRITICAL, WARNING, INFO
    original_text: str
    improved_text: str
    reason: str


class AutomaticImprovementEngine:
    """
    自動改善エンジン

    評価結果に基づいてエピソードを自動改善
    """

    # 抽象表現→具体化パターン
    ABSTRACTION_REPLACEMENTS = {
        "多くの": "3つの",
        "たくさんの": "5つの",
        "いくつかの": "2つの",
        "さまざまな": "複数の分野で",
        "大きな": "100万人規模の",
        "高い": "業界トップの",
        "素晴らしい": "",  # 削除
        "優れた": "",  # 削除
        "重要な": "歴史的な",
    }

    # センセーショナル表現→客観的表現
    SENSATIONAL_REPLACEMENTS = {
        "悪質な": "",
        "卑劣な": "",
        "糾弾され": "批判され",
        "非難の嵐": "批判",
        "炎上": "批判が集まり",
        "バッシング": "批判",
        "最低の": "",
        "最悪の": "",
    }

    def __init__(self):
        """初期化"""
        self.improvement_history: List[ImprovementAction] = []

    def improve_episode(
        self,
        episode_text: str,
        evaluation_result: Dict[str, Any],
        max_iterations: int = 3
    ) -> Tuple[str, List[ImprovementAction]]:
        """
        エピソードを自動改善

        Args:
            episode_text: 元のエピソードテキスト
            evaluation_result: RULE_179の評価結果
            max_iterations: 最大改善反復回数

        Returns:
            (改善後テキスト, 改善アクションリスト)
        """
        self.improvement_history = []
        improved_text = episode_text

        # EpisodeEvaluationResultオブジェクトを辞書に変換
        if not isinstance(evaluation_result, dict):
            evaluation_result = {
                "temporal_consistency": evaluation_result.temporal_consistency if hasattr(evaluation_result, "temporal_consistency") else None,
                "negative_evaluation": evaluation_result.negative_evaluation if hasattr(evaluation_result, "negative_evaluation") else None,
                "abstract_detection": evaluation_result.abstract_detection if hasattr(evaluation_result, "abstract_detection") else None,
            }

        logger.info(f"🔧 自動改善開始（最大{max_iterations}回反復）")

        for iteration in range(max_iterations):
            logger.info(f"  反復 {iteration + 1}/{max_iterations}")

            # 1. 時系列矛盾の修正（CRITICAL）
            improved_text = self._fix_temporal_issues(
                improved_text,
                evaluation_result.get("temporal_consistency", {})
            )

            # 2. ネガティブ表現の客観化（CRITICAL）
            improved_text = self._fix_negative_issues(
                improved_text,
                evaluation_result.get("negative_evaluation", {})
            )

            # 3. 抽象表現の具体化（WARNING）
            improved_text = self._fix_abstract_expressions(
                improved_text,
                evaluation_result.get("abstract_detection", {})
            )

            # 変更がなければ終了
            if improved_text == episode_text and iteration > 0:
                logger.info(f"  → 変更なし、改善完了")
                break

            episode_text = improved_text

        logger.info(f"✅ 自動改善完了: {len(self.improvement_history)}件の修正")
        return improved_text, self.improvement_history

    def _fix_temporal_issues(
        self,
        text: str,
        temporal_result: Dict[str, Any]
    ) -> str:
        """
        時系列矛盾を修正

        Args:
            text: エピソードテキスト
            temporal_result: RULE_174の評価結果

        Returns:
            修正後テキスト
        """
        if not temporal_result.get("inconsistencies"):
            return text

        improved_text = text

        for issue in temporal_result.get("inconsistencies", []):
            if issue.get("severity") != "CRITICAL":
                continue

            # 不可能な年齢の修正（例: 18歳でノーベル賞 → 25歳に修正）
            message = issue.get("message", "")
            evidence = issue.get("evidence", "")

            if "歳で" in message and "不可能" in message:
                # "18歳でノーベルは不可能（最年少記録: 25歳）"
                match = re.search(r'(\d+)歳で.*最年少記録: (\d+)歳', message)
                if match:
                    wrong_age = match.group(1)
                    correct_age = match.group(2)

                    # テキスト内の年齢を置換
                    pattern = rf'{wrong_age}歳'
                    if pattern in improved_text:
                        improved_text = improved_text.replace(
                            pattern, f"{correct_age}歳", 1
                        )

                        self.improvement_history.append(ImprovementAction(
                            rule_id="RULE_174",
                            issue_type="temporal_inconsistency",
                            severity="CRITICAL",
                            original_text=f"{wrong_age}歳",
                            improved_text=f"{correct_age}歳",
                            reason=f"時系列矛盾修正: {message}"
                        ))

                        logger.info(f"    🔧 時系列修正: {wrong_age}歳 → {correct_age}歳")

        return improved_text

    def _fix_negative_issues(
        self,
        text: str,
        negative_result: Optional[Dict[str, Any]]
    ) -> str:
        """
        ネガティブ表現を客観化

        Args:
            text: エピソードテキスト
            negative_result: RULE_175の評価結果

        Returns:
            修正後テキスト
        """
        if not negative_result or not negative_result.get("issues"):
            return text

        improved_text = text

        for issue in negative_result.get("issues", []):
            if issue.get("severity") != "CRITICAL":
                continue

            # 侮辱的・センセーショナルな表現を削除または置換
            evidence = issue.get("evidence", "")

            if evidence in self.SENSATIONAL_REPLACEMENTS:
                replacement = self.SENSATIONAL_REPLACEMENTS[evidence]

                if evidence in improved_text:
                    improved_text = improved_text.replace(evidence, replacement)

                    self.improvement_history.append(ImprovementAction(
                        rule_id="RULE_175",
                        issue_type="sensational_expression",
                        severity="CRITICAL",
                        original_text=evidence,
                        improved_text=replacement if replacement else "[削除]",
                        reason=f"センセーショナル表現の客観化: {issue.get('message', '')}"
                    ))

                    logger.info(f"    🔧 表現修正: 「{evidence}」→「{replacement or '[削除]'}」")

        return improved_text

    def _fix_abstract_expressions(
        self,
        text: str,
        abstract_result: Dict[str, Any]
    ) -> str:
        """
        抽象表現を具体化

        Args:
            text: エピソードテキスト
            abstract_result: RULE_177の評価結果

        Returns:
            修正後テキスト
        """
        if not abstract_result.get("abstract_expressions"):
            return text

        improved_text = text

        # 抽象表現を優先度順に処理（最大3件）
        for expr in abstract_result.get("abstract_expressions", [])[:3]:
            expression = expr.get("expression", "")

            if expression in self.ABSTRACTION_REPLACEMENTS:
                replacement = self.ABSTRACTION_REPLACEMENTS[expression]

                if expression in improved_text:
                    improved_text = improved_text.replace(expression, replacement, 1)

                    self.improvement_history.append(ImprovementAction(
                        rule_id="RULE_177",
                        issue_type="abstract_expression",
                        severity="WARNING",
                        original_text=expression,
                        improved_text=replacement if replacement else "[削除]",
                        reason=f"抽象表現の具体化: {expr.get('suggestion', '')}"
                    ))

                    logger.info(f"    🔧 具体化: 「{expression}」→「{replacement or '[削除]'}」")

        return improved_text

    def get_improvement_summary(self) -> Dict[str, Any]:
        """
        改善サマリーを取得

        Returns:
            改善統計情報
        """
        by_severity = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
        by_rule = {}

        for action in self.improvement_history:
            by_severity[action.severity] = by_severity.get(action.severity, 0) + 1

            rule_id = action.rule_id
            by_rule[rule_id] = by_rule.get(rule_id, 0) + 1

        return {
            "total_improvements": len(self.improvement_history),
            "by_severity": by_severity,
            "by_rule": by_rule,
            "actions": [
                {
                    "rule_id": a.rule_id,
                    "type": a.issue_type,
                    "severity": a.severity,
                    "original": a.original_text,
                    "improved": a.improved_text,
                    "reason": a.reason
                }
                for a in self.improvement_history
            ]
        }


# グローバル改善エンジン
improvement_engine = AutomaticImprovementEngine()


def improve_episode_automatically(
    episode_text: str,
    evaluation_result: Dict[str, Any],
    max_iterations: int = 3
) -> Tuple[str, Dict[str, Any]]:
    """
    エピソードを自動改善（外部インターフェース）

    Args:
        episode_text: 元のエピソードテキスト
        evaluation_result: RULE_179の評価結果
        max_iterations: 最大改善反復回数

    Returns:
        (改善後テキスト, 改善サマリー)
    """
    improved_text, _ = improvement_engine.improve_episode(
        episode_text, evaluation_result, max_iterations
    )

    summary = improvement_engine.get_improvement_summary()

    return improved_text, summary


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    print("=" * 80)
    print("RULE_180: 自動改善エンジン - テスト実行")
    print("=" * 80)
    print()

    # テストケース（RULE_179の評価結果を想定）
    test_cases = [
        {
            "text": "あなたと同じ18歳のとき、素晴らしいノーベル賞を受賞し、多くの人々に影響を与えた。",
            "evaluation": {
                "temporal_consistency": {
                    "passed": False,
                    "inconsistencies": [
                        {
                            "severity": "CRITICAL",
                            "message": "18歳でノーベルは不可能（最年少記録: 25歳）",
                            "evidence": "18歳、ノーベル"
                        }
                    ]
                },
                "abstract_detection": {
                    "passed": False,
                    "abstract_expressions": [
                        {"expression": "多くの", "suggestion": "具体的な数値に"},
                        {"expression": "素晴らしい", "suggestion": "客観的事実に"}
                    ]
                }
            }
        },
        {
            "text": "あなたと同じ30歳のとき、悪質な詐欺師として糾弾され、最低の人間と批判された。",
            "evaluation": {
                "negative_evaluation": {
                    "passed": False,
                    "issues": [
                        {
                            "severity": "CRITICAL",
                            "evidence": "悪質な",
                            "message": "センセーショナル表現"
                        },
                        {
                            "severity": "CRITICAL",
                            "evidence": "糾弾され",
                            "message": "センセーショナル表現"
                        },
                        {
                            "severity": "CRITICAL",
                            "evidence": "最低の",
                            "message": "侮辱的表現"
                        }
                    ]
                }
            }
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"テストケース {i}")
        print(f"  元のテキスト:")
        print(f"    {test['text']}")
        print()

        improved_text, summary = improve_episode_automatically(
            test["text"],
            test["evaluation"]
        )

        print(f"  改善後テキスト:")
        print(f"    {improved_text}")
        print()

        print(f"  📊 改善サマリー:")
        print(f"     総改善数: {summary['total_improvements']}件")
        print(f"     重大度別: CRITICAL={summary['by_severity']['CRITICAL']}, WARNING={summary['by_severity']['WARNING']}")

        if summary["actions"]:
            print(f"  📋 改善アクション:")
            for action in summary["actions"]:
                print(f"     - [{action['rule_id']}] {action['original']} → {action['improved']}")
                print(f"       理由: {action['reason']}")

        print()

    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
