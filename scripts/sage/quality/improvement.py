"""
Improvement Loop

品質不足のエピソードを改善するループ処理。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..adapters.base import GenerationResult, GeneratorAdapter
from ..config import GENERATION_RULES, QUALITY_THRESHOLDS, RejectionReason

# QualityEvaluatorは循環インポート回避のため遅延インポート
# from .evaluator import QualityEvaluator


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
        "feedback": "factual_densityが不足しています。",
        "suggestions": [
            "具体的な年号（YYYY年）を追加",
            "固有名詞（作品名、イベント名、組織名）を追加",
            "数値データ（記録、統計）を追加",
            "検証可能な出来事への言及を追加",
        ],
        "retryable": True,
    },
    RejectionReason.LOW_GENERATION_QUALITY: {
        "feedback": "生成品質が不足しています。",
        "suggestions": [
            "文章の流れを改善",
            "冗長な表現を削除",
            "具体的なエピソードに焦点を当てる",
            "ストーリー性を高める",
        ],
        "retryable": True,
    },
    RejectionReason.FILLER_DETECTED: {
        "feedback": "具体性が極めて不足しています（即棄却）。",
        "suggestions": [],
        "retryable": False,  # score < 1 は即棄却
    },
    RejectionReason.LOW_SPECIFICITY: {
        "feedback": "具体性がやや不足しています（リトライ可）。",
        "suggestions": [
            "西暦年号を2つ以上追加",
            "固有名詞（人名、作品名、組織名、地名）を5つ以上追加",
            "「」で囲んだ作品名・イベント名を2つ以上追加",
            "数値データを3つ以上追加",
        ],
        "retryable": True,  # score 1-2 はリトライ可
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


# Phase 5: 失敗理由別プロンプト注入テンプレート
# gate_failures文字列パターン → リトライ時のプロンプト追加指示
FAILURE_PROMPT_INJECTIONS = {
    # factual_density不足
    "factual_density": {
        "pattern": "factual_density",
        "injection": (
            "【重要】前回はfactual_densityが不足していました。以下を必ず含めてください:\n"
            "- 西暦年号を2つ以上（例: 1995年、2003年）\n"
            "- 固有名詞を5つ以上（人名、作品名、組織名、地名）\n"
            "- 数値データを3つ以上（記録、金額、順位など）\n"
            "- 「」で囲んだ作品名・イベント名を2つ以上"
        ),
        "retryable": True,
        "priority": 1,
    },
    # 生成品質不足
    "generation_quality": {
        "pattern": "generation_quality",
        "injection": (
            "【重要】前回は生成品質が不足していました。以下を改善してください:\n"
            "- 文章の流れを自然にする\n"
            "- 冗長な表現を削除\n"
            "- 一つの出来事に焦点を当てる\n"
            "- 起承転結のある構成にする"
        ),
        "retryable": True,
        "priority": 2,
    },
    # 記憶性不足
    "memorability": {
        "pattern": "memorability",
        "injection": (
            "【重要】前回は記憶に残りにくい内容でした。以下を意識してください:\n"
            "- 印象的なエピソードを選ぶ\n"
            "- 意外性のある事実を含める\n"
            "- 具体的な数字や記録を強調\n"
            "- 「あの時」が伝わる臨場感"
        ),
        "retryable": True,
        "priority": 3,
    },
    # 意外性不足
    "surprise": {
        "pattern": "surprise",
        "injection": (
            "【重要】前回は意外性が不足していました。以下を意識してください:\n"
            "- あまり知られていない事実を含める\n"
            "- 一般的なイメージと異なる側面を描く\n"
            "- 「知らなかった！」と思える情報を入れる"
        ),
        "retryable": True,
        "priority": 4,
    },
    # story_quality不足
    "story_quality": {
        "pattern": "story_quality",
        "injection": (
            "【重要】前回はストーリー性が不足していました。以下を意識してください:\n"
            "- 起承転結のある構成にする\n"
            "- 挑戦→困難→克服の流れを作る\n"
            "- 読者が感情移入できる描写を入れる"
        ),
        "retryable": True,
        "priority": 5,
    },
    # educational_value不足
    "educational_value": {
        "pattern": "educational_value",
        "injection": (
            "【重要】前回はeducational_valueが不足していました。以下を意識してください:\n"
            "- 学びや気づきにつながる内容を入れる\n"
            "- 成功の要因や努力の過程を描く\n"
            "- 読者の人生に活かせる教訓を含める"
        ),
        "retryable": True,
        "priority": 6,
    },
    # 共感性不足
    "empathy": {
        "pattern": "empathy",
        "injection": (
            "【重要】前回は共感性が不足していました。以下を意識してください:\n"
            "- 感情が伝わる描写を入れる\n"
            "- 苦悩や喜びの瞬間を描く\n"
            "- 読者が「わかる」と思える要素を入れる"
        ),
        "retryable": True,
        "priority": 7,
    },
    # 超総合スコア不足
    "super_total": {
        "pattern": "super_total",
        "injection": (
            "【重要】前回は総合的な品質が不足していました。以下をすべて意識してください:\n"
            "- 具体的な事実（年号、数値、固有名詞）\n"
            "- 印象的で記憶に残る内容\n"
            "- 自然で読みやすい文章\n"
            "- 学びや気づきのある内容"
        ),
        "retryable": True,
        "priority": 0,
    },
}


def get_retry_prompt_injection(gate_failures: list[str]) -> str:
    """
    失敗理由に基づいてリトライ用のプロンプト注入テキストを生成

    Args:
        gate_failures: 失敗理由リスト（例: ["factual_density 5.5 < 6.5"]）

    Returns:
        str: プロンプトに追加する改善指示テキスト
    """
    if not gate_failures:
        return ""

    injections = []
    seen_patterns = set()

    for failure in gate_failures:
        for key, template in FAILURE_PROMPT_INJECTIONS.items():
            pattern = template["pattern"]
            if pattern in failure and pattern not in seen_patterns:
                if template.get("retryable", True):
                    injections.append((template["priority"], template["injection"]))
                    seen_patterns.add(pattern)
                break

    if not injections:
        return ""

    # 優先度順にソート
    injections.sort(key=lambda x: x[0])

    # 最大2つまで（トークン節約）
    injection_texts = [inj[1] for inj in injections[:2]]

    return "\n\n".join(injection_texts)


def is_retryable_failure(gate_failures: list[str]) -> bool:
    """
    失敗理由がリトライ可能かどうかを判定

    Args:
        gate_failures: 失敗理由リスト

    Returns:
        bool: リトライ可能な場合True
    """
    if not gate_failures:
        return False

    for failure in gate_failures:
        for template in FAILURE_PROMPT_INJECTIONS.values():
            if template["pattern"] in failure:
                if template.get("retryable", True):
                    return True
    return False


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
        # 循環インポート回避のため遅延インポート
        from .evaluator import QualityEvaluator

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


def should_retry(
    result: GenerationResult,
    reason: RejectionReason = None,
    retry_count: int = 0,
    max_retries: int = 2,
) -> bool:
    """
    リトライすべきか判定

    即棄却とリトライ可能な棄却を区別。

    Args:
        result: 生成結果
        reason: 棄却理由（あれば）
        retry_count: 現在のリトライ回数
        max_retries: 最大リトライ回数

    Returns:
        bool: リトライすべきか
    """
    # リトライ上限チェック
    if retry_count >= max_retries:
        return False

    # 生成失敗時はリトライ
    if not result.success:
        return True

    if result.evaluation is None:
        return True

    # 棄却理由に基づく判定
    if reason:
        # 即棄却（リトライ不可）の理由
        immediate_reject_reasons = {
            RejectionReason.PROHIBITED_PATTERN,
            RejectionReason.FABRICATION_DETECTED,
            RejectionReason.AGE_BOUNDARY_VIOLATION,
            RejectionReason.FILLER_DETECTED,  # score < 1
            RejectionReason.SAME_AGE_DUPLICATE,
            RejectionReason.HIGH_SIMILARITY,
        }

        if reason in immediate_reject_reasons:
            return False

        # リトライ可能な理由
        retryable_reasons = {
            RejectionReason.LOW_SPECIFICITY,  # score 1-2
            RejectionReason.LOW_FACTUAL_DENSITY,
            RejectionReason.LOW_GENERATION_QUALITY,
            RejectionReason.LOW_COMPOSITE_SCORE,
        }

        if reason in retryable_reasons:
            return True

    # 即棄却ラインより低い場合はリトライしても無駄
    min_composite = QUALITY_THRESHOLDS.get("min_composite", 380)
    if result.evaluation.composite_score < min_composite:
        return False

    # リトライ閾値以下だがリトライで改善可能な場合
    retry_composite = QUALITY_THRESHOLDS.get("retry_composite", 470)
    if result.evaluation.composite_score < retry_composite:
        return True

    # ゲート失敗かつ改善可能な場合はリトライ
    if not result.evaluation.passed_gate:
        # ゲート失敗理由がリトライ可能かチェック
        for failure in result.evaluation.gate_failures:
            template = IMPROVEMENT_TEMPLATES.get(failure, {})
            if template.get("retryable", True):
                return True
        return False

    return False
