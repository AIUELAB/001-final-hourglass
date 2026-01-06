"""
Improvement Loop

品質不足のエピソードを改善するループ処理。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..adapters.base import GenerationResult, GeneratorAdapter
from ..config import GENERATION_RULES, QUALITY_THRESHOLDS, RejectionReason
from .evaluator import QualityEvaluator


class ImprovementAction(Enum):
    """改善アクション"""

    ACCEPT = "accept"  # そのまま採用
    RETRY = "retry"  # 再生成
    IMPROVE = "improve"  # 改善生成
    REJECT = "reject"  # 棄却


@dataclass
class ImprovementFeedback:
    """改善フィードバック"""

    action: ImprovementAction
    reason: str
    suggestions: list[str] = field(default_factory=list)


IMPROVEMENT_TEMPLATES = {
    RejectionReason.LOW_FACTUAL_DENSITY: {
        "feedback": "事実密度が不足しています。",
        "suggestions": [
            "具体的な年号（YYYY年）を追加",
            "固有名詞（作品名、イベント名、組織名）を追加",
            "数値データ（記録、統計）を追加",
            "検証可能な出来事への言及を追加",
        ],
    },
    RejectionReason.LOW_GENERATION_QUALITY: {
        "feedback": "生成品質が不足しています。",
        "suggestions": [
            "文章の流れを改善",
            "冗長な表現を削除",
            "具体的なエピソードに焦点を当てる",
            "ストーリー性を高める",
        ],
    },
    RejectionReason.FILLER_DETECTED: {
        "feedback": "具体性が不足しています（埋め草検出）。",
        "suggestions": [
            "抽象的な表現を具体的な出来事に置き換え",
            "「ある日」「いつか」などの曖昧表現を削除",
            "具体的な年号、場所、人物を追加",
        ],
    },
    RejectionReason.PROHIBITED_PATTERN: {
        "feedback": "禁止パターンが検出されました。",
        "suggestions": [
            "メタ表現（「このエピソード」等）を削除",
            "未来予測表現を削除",
            "推測表現を事実表現に置き換え",
        ],
    },
    RejectionReason.HIGH_SIMILARITY: {
        "feedback": "既存エピソードと類似度が高すぎます。",
        "suggestions": [
            "異なる角度からのエピソードを生成",
            "同じ人物の別の出来事を選択",
            "より具体的な詳細を追加",
        ],
    },
}


class ImprovementLoop:
    """
    改善ループ

    品質不足のエピソードを改善または再生成。
    """

    def __init__(
        self,
        adapter: GeneratorAdapter,
        max_retries: int = None,
        thresholds: dict = None,
    ):
        self.adapter = adapter
        self.max_retries = max_retries or GENERATION_RULES.get("max_retries", 2)
        self.thresholds = thresholds or QUALITY_THRESHOLDS.copy()
        self.evaluator = QualityEvaluator(self.thresholds)

    def analyze(self, result: GenerationResult) -> ImprovementFeedback:
        """
        結果を分析して改善アクションを決定

        Args:
            result: 生成結果

        Returns:
            ImprovementFeedback: 改善フィードバック
        """
        if not result.success:
            return ImprovementFeedback(
                action=ImprovementAction.RETRY,
                reason="Generation failed",
                suggestions=["Retry generation with same parameters"],
            )

        if result.evaluation is None:
            return ImprovementFeedback(
                action=ImprovementAction.RETRY,
                reason="No evaluation available",
                suggestions=["Retry with evaluation enabled"],
            )

        # 品質ゲートチェック
        gate_result = self.evaluator.check_quality_gates(result.evaluation.axis_scores)

        if gate_result.passed:
            # 統合スコアチェック
            passed, action = self.evaluator.check_composite_threshold(result.evaluation.composite_score)
            if action == "accept":
                return ImprovementFeedback(
                    action=ImprovementAction.ACCEPT,
                    reason="Quality gate passed, composite score acceptable",
                )
            elif action == "retry":
                return ImprovementFeedback(
                    action=ImprovementAction.IMPROVE,
                    reason="Quality gate passed but composite score could be higher",
                    suggestions=["Improve memorability and surprise"],
                )
            else:
                return ImprovementFeedback(
                    action=ImprovementAction.REJECT,
                    reason="Composite score too low",
                    suggestions=["Consider different episode angle"],
                )
        else:
            # ゲート失敗
            reason = gate_result.reason
            template = IMPROVEMENT_TEMPLATES.get(reason, {})

            return ImprovementFeedback(
                action=ImprovementAction.IMPROVE,
                reason=template.get("feedback", "Quality gate failed"),
                suggestions=template.get("suggestions", []),
            )

    def improve(self, result: GenerationResult, feedback: ImprovementFeedback) -> Optional[GenerationResult]:
        """
        エピソードを改善

        Args:
            result: 元の生成結果
            feedback: 改善フィードバック

        Returns:
            GenerationResult: 改善された結果、または None
        """
        if feedback.action == ImprovementAction.ACCEPT:
            return result

        if feedback.action == ImprovementAction.REJECT:
            return None

        # 改善または再生成
        feedback_text = f"{feedback.reason}\n改善提案:\n"
        for s in feedback.suggestions:
            feedback_text += f"- {s}\n"

        improved = self.adapter.improve(result, feedback_text)
        return improved

    def run(self, result: GenerationResult) -> tuple[GenerationResult, int]:
        """
        改善ループを実行

        Args:
            result: 初期生成結果

        Returns:
            (final_result, retry_count): 最終結果とリトライ回数
        """
        current = result
        retry_count = 0

        while retry_count < self.max_retries:
            feedback = self.analyze(current)

            if feedback.action == ImprovementAction.ACCEPT:
                return current, retry_count

            if feedback.action == ImprovementAction.REJECT:
                return current, retry_count

            # 改善を試みる
            improved = self.improve(current, feedback)
            if improved is None:
                return current, retry_count

            current = improved
            retry_count += 1

        return current, retry_count


def should_retry(result: GenerationResult) -> bool:
    """
    リトライすべきか判定

    Args:
        result: 生成結果

    Returns:
        bool: リトライすべきか
    """
    if not result.success:
        return True

    if result.evaluation is None:
        return True

    # 即棄却ラインより低い場合はリトライしても無駄
    min_composite = QUALITY_THRESHOLDS.get("min_composite", 380)
    if result.evaluation.composite_score < min_composite:
        return False

    # ゲート失敗かつ改善可能な場合はリトライ
    if not result.evaluation.passed_gate:
        return True

    return False
