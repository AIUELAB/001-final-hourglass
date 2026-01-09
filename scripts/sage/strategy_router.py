"""
Strategy Router

生成戦略の切り替えとルーティングを管理。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .adapters import (
    Candidate,
    EPGENAdapter,
    GenerationResult,
    GeneratorAdapter,
    LegacyGeneratorAdapter,
    MockEPGENAdapter,
    TokenUsage,
)
from .config import Strategy


@dataclass
class StrategyStats:
    """戦略統計"""

    strategy: Strategy
    total_attempts: int = 0
    epgen_attempts: int = 0
    legacy_attempts: int = 0
    epgen_successes: int = 0
    legacy_successes: int = 0
    fallback_count: int = 0
    average_super_total: float = 0.0
    total_super_total: float = 0.0
    # Phase 1: コスト計測
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_llm_calls: int = 0
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        total_tokens = self.total_input_tokens + self.total_output_tokens
        avg_tokens = total_tokens / self.total_attempts if self.total_attempts > 0 else 0
        avg_calls = self.total_llm_calls / self.total_attempts if self.total_attempts > 0 else 0
        return {
            "strategy": self.strategy.value,
            "total_attempts": self.total_attempts,
            "epgen_attempts": self.epgen_attempts,
            "legacy_attempts": self.legacy_attempts,
            "epgen_successes": self.epgen_successes,
            "legacy_successes": self.legacy_successes,
            "fallback_count": self.fallback_count,
            "epgen_success_rate": (self.epgen_successes / self.epgen_attempts if self.epgen_attempts > 0 else 0.0),
            "legacy_success_rate": (self.legacy_successes / self.legacy_attempts if self.legacy_attempts > 0 else 0.0),
            "average_super_total": self.average_super_total,
            # Phase 1: コスト計測
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": total_tokens,
            "total_llm_calls": self.total_llm_calls,
            "avg_tokens_per_episode": round(avg_tokens, 1),
            "avg_llm_calls_per_episode": round(avg_calls, 2),
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
        }


@dataclass
class ABCompareResult:
    """A/B比較結果"""

    epgen_result: Optional[GenerationResult]
    legacy_result: Optional[GenerationResult]
    winner: str  # 'epgen', 'legacy', 'none'
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "epgen_success": self.epgen_result.success if self.epgen_result else False,
            "legacy_success": (self.legacy_result.success if self.legacy_result else False),
            "winner": self.winner,
            "reason": self.reason,
        }


class StrategyRouter:
    """
    戦略ルーター

    生成戦略に応じて適切なアダプターを選択・実行。
    """

    def __init__(
        self,
        strategy: Strategy = Strategy.EPGEN_FIRST,
        use_mock: bool = False,
        use_haiku_evaluation: bool = True,  # Phase 3: 評価にHaiku使用
        use_compact_prompt: bool = True,  # Phase 10: 圧縮版プロンプト使用
        enable_cache: bool = True,  # H4最適化: Prompt Caching
    ):
        self.strategy = strategy
        self.use_mock = use_mock
        self.use_haiku_evaluation = use_haiku_evaluation
        self.use_compact_prompt = use_compact_prompt
        self.enable_cache = enable_cache
        self._stats = StrategyStats(strategy=strategy)

        # アダプター初期化
        if use_mock:
            self._epgen = MockEPGENAdapter()
        else:
            self._epgen = EPGENAdapter(
                use_haiku_evaluation=use_haiku_evaluation,
                use_compact_prompt=use_compact_prompt,
                enable_cache=enable_cache,  # H4: Prompt Caching
            )
        self._legacy = LegacyGeneratorAdapter()

    @property
    def stats(self) -> StrategyStats:
        return self._stats

    def reset_stats(self) -> None:
        """統計をリセット（アダプター含む）"""
        self._stats = StrategyStats(strategy=self.strategy)
        # Phase 18: アダプターの統計もリセット
        self._epgen.reset_stats()
        self._legacy.reset_stats()

    def route(self, candidate: Candidate) -> GenerationResult:
        """
        戦略に応じて生成を実行

        Args:
            candidate: 生成候補

        Returns:
            GenerationResult: 生成結果
        """
        self._stats.total_attempts += 1

        if self.strategy == Strategy.EPGEN_FIRST:
            return self._epgen_first(candidate)
        elif self.strategy == Strategy.LEGACY_FIRST:
            return self._legacy_first(candidate)
        elif self.strategy == Strategy.AB_COMPARE:
            compare_result = self._ab_compare(candidate)
            # 勝者の結果を返す
            if compare_result.winner == "epgen" and compare_result.epgen_result:
                return compare_result.epgen_result
            elif compare_result.winner == "legacy" and compare_result.legacy_result:
                return compare_result.legacy_result
            else:
                # どちらも失敗した場合
                return compare_result.epgen_result or GenerationResult(
                    success=False, candidate=candidate, error_message="Both failed"
                )
        else:
            return self._epgen_first(candidate)

    def route_without_eval(self, candidate: Candidate) -> GenerationResult:
        """
        戦略に応じて生成を実行（評価なし）

        Phase 18: バッチ評価用に評価を分離。
        生成のみ実行し、評価は後でbatch_evaluateで一括実行。

        Args:
            candidate: 生成候補

        Returns:
            GenerationResult: 生成結果（evaluationはNone）
        """
        self._stats.total_attempts += 1

        # EPGEN_FIRST戦略のみ対応（主要パス）
        if self.strategy == Strategy.EPGEN_FIRST:
            return self._epgen_first_without_eval(candidate)
        else:
            # 他の戦略は従来通り（評価付き）
            return self.route(candidate)

    def _epgen_first_without_eval(self, candidate: Candidate) -> GenerationResult:
        """
        EPGEN優先戦略（評価なし）

        Phase 18: 生成のみ実行。
        """
        self._stats.epgen_attempts += 1

        # generate_onlyを使用（評価なし）
        if hasattr(self._epgen, "generate_only"):
            result = self._epgen.generate_only(candidate)
        else:
            # フォールバック: 従来のgenerate
            result = self._epgen.generate(candidate)

        if result.success:
            self._stats.epgen_successes += 1
            return result

        # フォールバック（評価なしでは品質判定できないため、生成成功のみ確認）
        self._stats.fallback_count += 1
        self._stats.legacy_attempts += 1

        if hasattr(self._legacy, "generate_only"):
            fallback_result = self._legacy.generate_only(candidate)
        else:
            fallback_result = self._legacy.generate(candidate)

        if fallback_result.success:
            self._stats.legacy_successes += 1

        return fallback_result

    def batch_evaluate(self, results: list[GenerationResult], batch_size: int = 50) -> list[GenerationResult]:
        """
        複数の生成結果を一括評価

        Phase 18: バッチ評価でLLM呼び出しを大幅削減。

        Args:
            results: 評価対象のGenerationResultリスト
            batch_size: バッチサイズ

        Returns:
            list[GenerationResult]: 評価結果が追加されたリスト
        """
        if hasattr(self._epgen, "batch_evaluate"):
            return self._epgen.batch_evaluate(results, batch_size=batch_size)
        else:
            # フォールバック: 個別評価
            for r in results:
                if r.success and r.episode_text and not r.evaluation:
                    r.evaluation = self._epgen.evaluate(r.episode_text, r.candidate)
            return results

    def _epgen_first(self, candidate: Candidate) -> GenerationResult:
        """
        EPGEN優先戦略

        EPGENで生成を試み、失敗時はLegacyにフォールバック。
        """
        # EPGENで試行
        self._stats.epgen_attempts += 1
        result = self._epgen.generate_with_retry(candidate)

        if result.success and self._is_quality_sufficient(result):
            self._stats.epgen_successes += 1
            self._update_super_total_stats(result)
            return result

        # フォールバック
        self._stats.fallback_count += 1
        self._stats.legacy_attempts += 1
        fallback_result = self._legacy.generate_with_retry(candidate)

        if fallback_result.success:
            self._stats.legacy_successes += 1
            self._update_super_total_stats(fallback_result)

        return fallback_result

    def _legacy_first(self, candidate: Candidate) -> GenerationResult:
        """
        Legacy優先戦略

        Legacyで生成を試み、品質不足時はEPGENで補強。
        """
        # Legacyで試行
        self._stats.legacy_attempts += 1
        result = self._legacy.generate_with_retry(candidate)

        if result.success and self._is_quality_sufficient(result):
            self._stats.legacy_successes += 1
            self._update_super_total_stats(result)
            return result

        # EPGENで補強
        self._stats.fallback_count += 1
        self._stats.epgen_attempts += 1
        epgen_result = self._epgen.generate_with_retry(candidate)

        if epgen_result.success:
            self._stats.epgen_successes += 1
            self._update_super_total_stats(epgen_result)

        return epgen_result

    def _ab_compare(self, candidate: Candidate) -> ABCompareResult:
        """
        A/B比較戦略

        両方で生成して品質を比較。
        """
        # 両方で生成
        self._stats.epgen_attempts += 1
        self._stats.legacy_attempts += 1

        epgen_result = self._epgen.generate_with_retry(candidate)
        legacy_result = self._legacy.generate_with_retry(candidate)

        # 成功カウント
        if epgen_result.success:
            self._stats.epgen_successes += 1
        if legacy_result.success:
            self._stats.legacy_successes += 1

        # 比較
        winner = self._compare_results(epgen_result, legacy_result)

        if winner == "epgen":
            self._update_super_total_stats(epgen_result)
        elif winner == "legacy":
            self._update_super_total_stats(legacy_result)

        return ABCompareResult(
            epgen_result=epgen_result,
            legacy_result=legacy_result,
            winner=winner,
            reason=self._get_comparison_reason(epgen_result, legacy_result),
        )

    def _is_quality_sufficient(self, result: GenerationResult) -> bool:
        """品質が十分か判定"""
        if not result.success or not result.evaluation:
            return False

        # ゲートパス確認
        if not result.evaluation.passed_gate:
            return False

        # 統合スコア確認
        if result.evaluation.composite_score < 470:  # retry_composite
            return False

        return True

    def _compare_results(self, epgen: GenerationResult, legacy: GenerationResult) -> str:
        """結果を比較して勝者を決定"""
        if not epgen.success and not legacy.success:
            return "none"
        if not epgen.success:
            return "legacy"
        if not legacy.success:
            return "epgen"

        # 両方成功した場合は品質で比較
        epgen_score = self._get_quality_score(epgen)
        legacy_score = self._get_quality_score(legacy)

        if epgen_score > legacy_score:
            return "epgen"
        elif legacy_score > epgen_score:
            return "legacy"
        else:
            # 同点の場合はEPGEN優先
            return "epgen"

    def _get_quality_score(self, result: GenerationResult) -> float:
        """品質スコアを取得"""
        if not result.evaluation:
            return 0.0

        # 超総合スコアがあればそれを使用
        if result.evaluation.super_total_score > 0:
            return result.evaluation.super_total_score

        # なければ統合スコアを使用
        return result.evaluation.composite_score * 1000

    def _get_comparison_reason(self, epgen: GenerationResult, legacy: GenerationResult) -> str:
        """比較理由を生成"""
        epgen_score = self._get_quality_score(epgen)
        legacy_score = self._get_quality_score(legacy)

        return f"EPGEN: {epgen_score:.0f}, Legacy: {legacy_score:.0f}, Diff: {abs(epgen_score - legacy_score):.0f}"

    def _update_super_total_stats(self, result: GenerationResult) -> None:
        """超総合スコア統計を更新"""
        if result.evaluation and result.evaluation.super_total_score > 0:
            self._stats.total_super_total += result.evaluation.super_total_score
            success_count = self._stats.epgen_successes + self._stats.legacy_successes
            if success_count > 0:
                self._stats.average_super_total = self._stats.total_super_total / success_count

        # Phase 1: トークン使用量を記録
        if result.token_usage:
            self._stats.total_input_tokens += result.token_usage.input_tokens
            self._stats.total_output_tokens += result.token_usage.output_tokens
            self._stats.total_llm_calls += 1
            self._stats.estimated_cost_usd += result.token_usage.estimated_cost_usd

    def collect_adapter_stats(self) -> dict[str, Any]:
        """アダプターから統計を収集"""
        epgen_stats = self._epgen.get_stats()
        legacy_stats = self._legacy.get_stats()

        # アダプターのトークン統計を集約
        total_input = epgen_stats.get("total_input_tokens", 0) + legacy_stats.get("total_input_tokens", 0)
        total_output = epgen_stats.get("total_output_tokens", 0) + legacy_stats.get("total_output_tokens", 0)
        total_calls = epgen_stats.get("llm_call_count", 0) + legacy_stats.get("llm_call_count", 0)
        total_cost = epgen_stats.get("estimated_cost_usd", 0) + legacy_stats.get("estimated_cost_usd", 0)

        # StrategyStatsを更新
        self._stats.total_input_tokens = total_input
        self._stats.total_output_tokens = total_output
        self._stats.total_llm_calls = total_calls
        self._stats.estimated_cost_usd = total_cost

        return {
            "epgen": epgen_stats,
            "legacy": legacy_stats,
            "combined": {
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "total_llm_calls": total_calls,
                "estimated_cost_usd": round(total_cost, 4),
            },
        }


def create_router(
    strategy: str = "epgen_first",
    use_mock: bool = False,
    use_haiku_evaluation: bool = True,  # Phase 3: 評価にHaiku使用
    use_compact_prompt: bool = True,  # Phase 10: 圧縮版プロンプト使用
    enable_cache: bool = True,  # H4最適化: Prompt Caching
) -> StrategyRouter:
    """
    ルーターを作成

    Args:
        strategy: 戦略名 ('epgen_first', 'legacy_first', 'ab_compare')
        use_mock: モックを使用するか
        use_haiku_evaluation: 評価にHaikuを使用（True=コスト-92%、False=Sonnet高精度）
        use_compact_prompt: 圧縮版プロンプト使用（True=-60%トークン, False=通常版）
        enable_cache: Prompt Caching有効化（True=-25%コスト, 同一人物連続処理時）

    Returns:
        StrategyRouter: ルーター
    """
    strategy_enum = Strategy(strategy)
    return StrategyRouter(
        strategy=strategy_enum,
        use_mock=use_mock,
        use_haiku_evaluation=use_haiku_evaluation,
        use_compact_prompt=use_compact_prompt,
        enable_cache=enable_cache,
    )
