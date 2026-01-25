"""
Load Balanced Adapter - Phase 7B

動的プロバイダ負荷分散アダプター。
レート制限を監視し、複数プロバイダ間で自動切り替え。
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .base import (
    AxisScores,
    Candidate,
    EvaluationResult,
    GenerationResult,
    GeneratorAdapter,
    GeneratorType,
)
from .multi_provider_adapter import MultiProviderAdapter
from .providers import (
    ProviderType,
    get_available_providers,
)

logger = logging.getLogger(__name__)


@dataclass
class ProviderStatus:
    """プロバイダステータス"""

    provider: ProviderType
    is_available: bool = True
    rate_limited_until: Optional[datetime] = None
    consecutive_errors: int = 0
    total_requests: int = 0
    total_errors: int = 0
    last_request_time: Optional[datetime] = None
    avg_latency_ms: float = 0.0

    def is_rate_limited(self) -> bool:
        """レート制限中かどうか"""
        if self.rate_limited_until is None:
            return False
        return datetime.now() < self.rate_limited_until

    def mark_rate_limited(self, duration_seconds: float = 60.0) -> None:
        """レート制限をマーク"""
        self.rate_limited_until = datetime.now() + timedelta(seconds=duration_seconds)
        self.is_available = False
        logger.warning(f"{self.provider.value} rate limited for {duration_seconds}s")

    def mark_success(self, latency_ms: float) -> None:
        """成功をマーク"""
        self.consecutive_errors = 0
        self.total_requests += 1
        self.last_request_time = datetime.now()
        # 移動平均でレイテンシを更新
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = self.avg_latency_ms * 0.9 + latency_ms * 0.1

    def mark_error(self) -> None:
        """エラーをマーク"""
        self.consecutive_errors += 1
        self.total_errors += 1
        self.total_requests += 1
        # 連続エラーが多い場合、一時的に無効化
        if self.consecutive_errors >= 3:
            self.mark_rate_limited(30.0)

    def refresh_availability(self) -> None:
        """可用性を更新"""
        if self.rate_limited_until and datetime.now() >= self.rate_limited_until:
            self.rate_limited_until = None
            self.is_available = True
            self.consecutive_errors = 0
            logger.info(f"{self.provider.value} is now available again")


@dataclass
class LoadBalanceConfig:
    """負荷分散設定"""

    # プロバイダ優先順位
    provider_priority: list[ProviderType] = field(
        default_factory=lambda: [
            ProviderType.ANTHROPIC,
            ProviderType.OPENAI,
            ProviderType.GOOGLE,
        ]
    )

    # レート制限検出キーワード
    rate_limit_keywords: list[str] = field(
        default_factory=lambda: [
            "rate_limit",
            "rate limit",
            "429",
            "too many requests",
            "quota exceeded",
            "overloaded",
        ]
    )

    # フォールバック有効化
    enable_fallback: bool = True

    # 最大リトライ回数（プロバイダあたり）
    max_retries_per_provider: int = 2

    # レート制限時のデフォルト待機時間（秒）
    default_rate_limit_duration: float = 60.0

    # 低レイテンシプロバイダを優先
    prefer_low_latency: bool = True


class LoadBalancedAdapter(GeneratorAdapter):
    """
    負荷分散アダプター

    複数のLLMプロバイダ間で負荷を分散し、
    レート制限時に自動的にフォールバック。

    機能:
    - 動的プロバイダ切り替え
    - レート制限検出・回避
    - 低レイテンシプロバイダ優先
    - フォールバックチェーン
    """

    def __init__(
        self,
        config: Optional[LoadBalanceConfig] = None,
    ):
        super().__init__("load_balanced", GeneratorType.EPGEN)
        self.config = config or LoadBalanceConfig()

        # 利用可能なプロバイダを取得
        self._available_providers = get_available_providers()

        # プロバイダステータス初期化
        self._provider_status: dict[ProviderType, ProviderStatus] = {}
        for provider in self.config.provider_priority:
            if provider in self._available_providers:
                self._provider_status[provider] = ProviderStatus(provider=provider)

        # アダプターキャッシュ
        self._adapters: dict[ProviderType, MultiProviderAdapter] = {}

        logger.info(
            f"LoadBalancedAdapter initialized with providers: {[p.value for p in self._provider_status.keys()]}"
        )

    def _get_adapter(self, provider: ProviderType) -> MultiProviderAdapter:
        """プロバイダ用アダプターを取得（遅延初期化）"""
        if provider not in self._adapters:
            self._adapters[provider] = MultiProviderAdapter(provider_type=provider)
        return self._adapters[provider]

    def _get_best_provider(self) -> Optional[ProviderType]:
        """
        最適なプロバイダを選択

        Returns:
            Optional[ProviderType]: 利用可能な最適プロバイダ
        """
        # 可用性を更新
        for status in self._provider_status.values():
            status.refresh_availability()

        # 利用可能なプロバイダをフィルタ
        available = [
            (provider, status)
            for provider, status in self._provider_status.items()
            if status.is_available and not status.is_rate_limited()
        ]

        if not available:
            logger.warning("No providers available")
            return None

        if self.config.prefer_low_latency:
            # レイテンシでソート（低い順）
            available.sort(key=lambda x: x[1].avg_latency_ms if x[1].avg_latency_ms > 0 else float("inf"))
        else:
            # 優先順位でソート
            priority_map = {p: i for i, p in enumerate(self.config.provider_priority)}
            available.sort(key=lambda x: priority_map.get(x[0], 999))

        return available[0][0]

    def _is_rate_limit_error(self, error_message: str) -> bool:
        """レート制限エラーかどうかを判定"""
        error_lower = error_message.lower()
        return any(kw in error_lower for kw in self.config.rate_limit_keywords)

    def evaluate(self, text: str, candidate: Candidate) -> EvaluationResult:
        """
        エピソードを評価（負荷分散）

        Args:
            text: エピソードテキスト
            candidate: 候補情報

        Returns:
            EvaluationResult: 評価結果
        """
        provider = self._get_best_provider()
        if provider is None:
            # プロバイダが利用できない場合、デフォルト評価を返す
            return EvaluationResult(
                axis_scores=AxisScores(),
                passed_gate=False,
                gate_failures=["no_provider_available"],
            )

        adapter = self._get_adapter(provider)
        return adapter.evaluate(text, candidate)

    def improve(self, result: GenerationResult, feedback: str) -> Optional[GenerationResult]:
        """
        エピソードを改善（負荷分散）

        Args:
            result: 元の生成結果
            feedback: 改善フィードバック

        Returns:
            GenerationResult: 改善された生成結果、または None
        """
        provider = self._get_best_provider()
        if provider is None:
            return None

        adapter = self._get_adapter(provider)
        return adapter.improve(result, feedback)

    def generate(self, candidate: Candidate) -> GenerationResult:
        """
        エピソード生成（負荷分散）

        Args:
            candidate: 生成候補

        Returns:
            GenerationResult: 生成結果
        """
        tried_providers: set[ProviderType] = set()
        last_error = ""

        while True:
            provider = self._get_best_provider()

            if provider is None or provider in tried_providers:
                # 全プロバイダ試行済み or 利用不可
                return GenerationResult(
                    success=False,
                    candidate=candidate,
                    error_message=f"All providers exhausted. Last error: {last_error}",
                    generator_type=self.generator_type,
                )

            tried_providers.add(provider)
            status = self._provider_status[provider]

            logger.debug(f"Trying provider: {provider.value}")

            # 生成実行
            start_time = time.time()
            try:
                adapter = self._get_adapter(provider)
                result = adapter.generate(candidate)
                latency_ms = (time.time() - start_time) * 1000

                if result.success:
                    status.mark_success(latency_ms)
                    return result
                else:
                    # エラー内容を確認
                    error_msg = result.error_message or ""
                    last_error = error_msg

                    if self._is_rate_limit_error(error_msg):
                        status.mark_rate_limited(self.config.default_rate_limit_duration)
                    else:
                        status.mark_error()

                    if not self.config.enable_fallback:
                        return result

                    # フォールバックを試行
                    logger.info(f"Falling back from {provider.value}: {error_msg[:100]}")
                    continue

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                error_msg = str(e)
                last_error = error_msg

                if self._is_rate_limit_error(error_msg):
                    status.mark_rate_limited(self.config.default_rate_limit_duration)
                else:
                    status.mark_error()

                if not self.config.enable_fallback:
                    return GenerationResult(
                        success=False,
                        candidate=candidate,
                        error_message=error_msg,
                        generator_type=self.generator_type,
                    )

                logger.info(f"Falling back from {provider.value}: {error_msg[:100]}")
                continue

    def get_provider_stats(self) -> dict[str, dict]:
        """
        プロバイダ統計を取得

        Returns:
            dict: プロバイダごとの統計情報
        """
        stats = {}
        for provider, status in self._provider_status.items():
            stats[provider.value] = {
                "is_available": status.is_available,
                "is_rate_limited": status.is_rate_limited(),
                "total_requests": status.total_requests,
                "total_errors": status.total_errors,
                "error_rate": (status.total_errors / status.total_requests if status.total_requests > 0 else 0.0),
                "avg_latency_ms": status.avg_latency_ms,
                "consecutive_errors": status.consecutive_errors,
            }
        return stats

    def print_stats(self) -> None:
        """統計情報を表示"""
        print("\n=== Load Balanced Adapter Stats ===")
        stats = self.get_provider_stats()
        for provider, data in stats.items():
            status = "✓" if data["is_available"] and not data["is_rate_limited"] else "✗"
            print(f"{status} {provider}:")
            print(f"    Requests: {data['total_requests']}")
            print(f"    Errors: {data['total_errors']} ({data['error_rate'] * 100:.1f}%)")
            print(f"    Avg Latency: {data['avg_latency_ms']:.0f}ms")


# ==============================================================================
# 便利関数
# ==============================================================================


def create_load_balanced_adapter(
    providers: Optional[list[str]] = None,
    prefer_low_latency: bool = True,
) -> LoadBalancedAdapter:
    """
    負荷分散アダプターを作成

    Args:
        providers: 使用するプロバイダリスト（省略時は全て）
        prefer_low_latency: 低レイテンシを優先するか

    Returns:
        LoadBalancedAdapter: アダプター
    """
    config = LoadBalanceConfig(prefer_low_latency=prefer_low_latency)

    if providers:
        provider_types = []
        for p in providers:
            try:
                provider_types.append(ProviderType(p.lower()))
            except ValueError:
                logger.warning(f"Unknown provider: {p}")
        config.provider_priority = provider_types

    return LoadBalancedAdapter(config)


# ==============================================================================
# テスト
# ==============================================================================


if __name__ == "__main__":
    import os

    print("=== LoadBalancedAdapter Test ===")

    # APIキー設定
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            api_key = open("/Users/admin/Documents/key/anthropic_api_key.txt").read().strip()
            os.environ["ANTHROPIC_API_KEY"] = api_key
        except FileNotFoundError:
            print("ANTHROPIC_API_KEY not found")

    # アダプター作成
    adapter = create_load_balanced_adapter(prefer_low_latency=True)

    # 統計表示
    adapter.print_stats()

    # テスト生成
    from .base import Candidate

    candidate = Candidate(
        person_id="TEST001",
        person_name="テスト太郎",
        age=30,
        category="テスト",
        person_type="REAL",
    )

    print("\n--- Test Generation ---")
    result = adapter.generate(candidate)
    print(f"Success: {result.success}")
    if result.success:
        print(f"Text length: {len(result.episode_text or '')}")
    else:
        print(f"Error: {result.error_message}")

    # 統計表示
    adapter.print_stats()

    print("\n=== Test Complete ===")
