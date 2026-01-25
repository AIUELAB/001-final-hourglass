"""
Async Orchestrator - Phase 7B

非同期並列オーケストレータ。複数候補を同時に処理して生成スループットを向上。
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pandas as pd

from .adapters import Candidate, GenerationResult
from .config import (
    LOGS_DIR,
    HybridConfig,
    RejectionReason,
)
from .gates import (
    AntiGamingMonitor,
    CandidatePrioritizer,
    DiversityManager,
    DuplicateDetector,
    FactChecker,
)
from .inventory_manager import InventoryManager, ReplacementTarget
from .orchestrator import GenerationRun, HybridOrchestrator, ProcessingResult
from .persistence import SafeCSVWriter
from .pre_generation_rules import PreGenerationRules, check_prohibited_patterns, check_specificity
from .quality import QualityEvaluator, SuperTotalCalculator
from .strategy_router import StrategyRouter

logger = logging.getLogger(__name__)


@dataclass
class AsyncConfig:
    """非同期実行設定"""

    max_concurrent: int = 10  # 最大同時処理数
    timeout_seconds: float = 120.0  # 候補ごとのタイムアウト
    retry_on_timeout: bool = True  # タイムアウト時リトライ
    max_retries: int = 2  # 最大リトライ回数


@dataclass
class AsyncResult:
    """非同期処理結果"""

    candidate: Candidate
    processing_result: Optional[ProcessingResult] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    retries: int = 0


class AsyncOrchestrator:
    """
    非同期並列オーケストレータ

    複数候補を同時に処理することで、生成スループットを3-5倍向上。

    特徴:
    - asyncio.Semaphore による同時実行数制御
    - 候補ごとのタイムアウト処理
    - エラー時の自動リトライ
    - 既存の HybridOrchestrator と同じゲートチェック
    """

    def __init__(
        self,
        config: Optional[HybridConfig] = None,
        async_config: Optional[AsyncConfig] = None,
    ):
        self.config = config or HybridConfig()
        self.async_config = async_config or AsyncConfig()

        # 同期オーケストレータのコンポーネントを再利用
        self._sync_orchestrator = HybridOrchestrator(self.config)

        # 非同期用のセマフォ
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def run_parallel(
        self,
        candidates: list[Candidate],
        dry_run: bool = True,
    ) -> GenerationRun:
        """
        複数候補を並列処理

        Args:
            candidates: 生成候補リスト
            dry_run: True の場合、書き込みをスキップ

        Returns:
            GenerationRun: 実行結果
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run = GenerationRun(
            run_id=run_id,
            started_at=datetime.now().isoformat(),
            strategy=str(self.config.strategy.value),
            target_count=len(candidates),
            dry_run=dry_run,
        )

        logger.info(f"Starting async run {run_id} with {len(candidates)} candidates")
        logger.info(f"Max concurrent: {self.async_config.max_concurrent}")

        # セマフォ初期化
        self._semaphore = asyncio.Semaphore(self.async_config.max_concurrent)

        # 全候補を並列処理
        tasks = [self._process_candidate_async(candidate) for candidate in candidates]

        async_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 結果集計
        accepted_results: list[GenerationResult] = []
        rejections: list[dict] = []
        replacements: list[dict] = []

        for async_result in async_results:
            if isinstance(async_result, Exception):
                logger.error(f"Task exception: {async_result}")
                run.rejected_count += 1
                rejections.append(
                    {
                        "person_id": "unknown",
                        "person_name": "unknown",
                        "reason": "async_error",
                        "message": str(async_result),
                    }
                )
                continue

            if not isinstance(async_result, AsyncResult):
                continue

            run.generated_count += 1

            if async_result.error:
                run.rejected_count += 1
                rejections.append(
                    {
                        "person_id": async_result.candidate.person_id,
                        "person_name": async_result.candidate.person_name,
                        "reason": "async_error",
                        "message": async_result.error,
                    }
                )
                continue

            proc_result = async_result.processing_result
            if proc_result is None:
                continue

            if proc_result.result and proc_result.result.success:
                if proc_result.is_replacement and proc_result.replacement_target:
                    # 置換処理（同期で実行）
                    replace_result = self._sync_orchestrator._writer.replace(
                        old_episode_id=proc_result.replacement_target.episode_id,
                        new_result=proc_result.result,
                        dry_run=dry_run,
                    )
                    if replace_result.success:
                        run.replaced_count += 1
                        replacements.append(
                            {
                                "person_name": async_result.candidate.person_name,
                                "age": async_result.candidate.age,
                                "old_episode_id": proc_result.replacement_target.episode_id,
                                "old_score": proc_result.replacement_target.score,
                                "new_score": (
                                    proc_result.result.evaluation.super_total_score
                                    if proc_result.result.evaluation
                                    else 0
                                ),
                            }
                        )
                    else:
                        run.rejected_count += 1
                        rejections.append(
                            {
                                "person_id": async_result.candidate.person_id,
                                "person_name": async_result.candidate.person_name,
                                "reason": "replacement_failed",
                                "message": replace_result.error_message,
                            }
                        )
                else:
                    # 通常の追加
                    accepted_results.append(proc_result.result)
                    run.accepted_count += 1
            else:
                run.rejected_count += 1
                if proc_result.rejection:
                    rejections.append(proc_result.rejection)

        # 永続化（同期で実行）
        if accepted_results:
            if dry_run:
                run.write_result = self._sync_orchestrator._writer.dry_run(accepted_results)
            else:
                run.write_result = self._sync_orchestrator._writer.write(accepted_results)

        run.results = accepted_results
        run.rejections = rejections
        run.replacements = replacements
        run.completed_at = datetime.now().isoformat()

        # ログ保存
        self._sync_orchestrator._save_run_log(run)

        logger.info(
            f"Async run completed: {run.accepted_count}/{run.generated_count} accepted ({run.replaced_count} replaced)"
        )

        return run

    async def _process_candidate_async(self, candidate: Candidate) -> AsyncResult:
        """
        単一候補を非同期で処理

        Args:
            candidate: 生成候補

        Returns:
            AsyncResult: 非同期処理結果
        """
        start_time = datetime.now()
        retries = 0

        async with self._semaphore:
            while retries <= self.async_config.max_retries:
                try:
                    # タイムアウト付きで同期処理を実行
                    loop = asyncio.get_event_loop()
                    proc_result = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            self._sync_orchestrator._process_candidate,
                            candidate,
                        ),
                        timeout=self.async_config.timeout_seconds,
                    )

                    duration = (datetime.now() - start_time).total_seconds()
                    return AsyncResult(
                        candidate=candidate,
                        processing_result=proc_result,
                        duration_seconds=duration,
                        retries=retries,
                    )

                except asyncio.TimeoutError:
                    retries += 1
                    if retries > self.async_config.max_retries:
                        duration = (datetime.now() - start_time).total_seconds()
                        return AsyncResult(
                            candidate=candidate,
                            error=f"Timeout after {self.async_config.timeout_seconds}s (retries: {retries})",
                            duration_seconds=duration,
                            retries=retries,
                        )
                    logger.warning(
                        f"Timeout for {candidate.person_name}, retry {retries}/{self.async_config.max_retries}"
                    )

                except Exception as e:
                    duration = (datetime.now() - start_time).total_seconds()
                    return AsyncResult(
                        candidate=candidate,
                        error=str(e),
                        duration_seconds=duration,
                        retries=retries,
                    )

        # ここには到達しないはず
        return AsyncResult(
            candidate=candidate,
            error="Unexpected flow",
            duration_seconds=0,
        )

    def get_recommended_candidates(self, count: int = 10) -> list[Candidate]:
        """
        推奨候補を取得（同期オーケストレータに委譲）

        Args:
            count: 取得件数

        Returns:
            list[Candidate]: 推奨候補リスト
        """
        return self._sync_orchestrator.get_recommended_candidates(count)

    def run_sync(self, candidates: list[Candidate], dry_run: bool = True) -> GenerationRun:
        """
        同期実行（互換性用）

        Args:
            candidates: 生成候補リスト
            dry_run: True の場合、書き込みをスキップ

        Returns:
            GenerationRun: 実行結果
        """
        return asyncio.run(self.run_parallel(candidates, dry_run))


# ==============================================================================
# 便利関数
# ==============================================================================


def run_async_generation(
    candidates: list[Candidate],
    max_concurrent: int = 10,
    dry_run: bool = True,
    use_mock: bool = False,
) -> GenerationRun:
    """
    非同期生成を実行する便利関数

    Args:
        candidates: 生成候補リスト
        max_concurrent: 最大同時処理数
        dry_run: True の場合、書き込みをスキップ
        use_mock: True の場合、モックアダプターを使用

    Returns:
        GenerationRun: 実行結果
    """
    config = HybridConfig(use_mock=use_mock)
    async_config = AsyncConfig(max_concurrent=max_concurrent)
    orchestrator = AsyncOrchestrator(config, async_config)
    return orchestrator.run_sync(candidates, dry_run)


# ==============================================================================
# テスト
# ==============================================================================


if __name__ == "__main__":
    import time

    print("=== AsyncOrchestrator Test ===")

    # モックモードでテスト
    config = HybridConfig(use_mock=True)
    async_config = AsyncConfig(max_concurrent=5)
    orchestrator = AsyncOrchestrator(config, async_config)

    # 候補取得
    candidates = orchestrator.get_recommended_candidates(10)
    print(f"Candidates: {len(candidates)}")

    # 同期実行（比較用）
    print("\n--- Sync execution ---")
    sync_start = time.time()
    sync_orchestrator = HybridOrchestrator(config)
    sync_result = sync_orchestrator.run(candidates[:5], dry_run=True)
    sync_duration = time.time() - sync_start
    print(f"Sync: {sync_result.accepted_count}/{sync_result.generated_count} in {sync_duration:.2f}s")

    # 非同期実行
    print("\n--- Async execution ---")
    async_start = time.time()
    async_result = orchestrator.run_sync(candidates[:5], dry_run=True)
    async_duration = time.time() - async_start
    print(f"Async: {async_result.accepted_count}/{async_result.generated_count} in {async_duration:.2f}s")

    # 速度比較
    if sync_duration > 0:
        speedup = sync_duration / async_duration
        print(f"\nSpeedup: {speedup:.2f}x")

    print("\n=== Test Complete ===")
