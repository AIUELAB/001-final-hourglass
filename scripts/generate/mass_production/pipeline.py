#!/usr/bin/env python3
"""
統合パイプラインモジュール

Selector → Generator → Evaluator → Deduplicator → Ranker → Persister
"""

import asyncio
import csv
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .config import (
    DEFAULT_CONFIG,
    MASTER_CSV_PATH,
    MassProductionConfig,
)
from .deduplicator import FastDeduplicator, PersonAgeDeduplicator
from .evaluator import BatchEvaluator, FinalRanker
from .generator import GenerationInput, ParallelGenerator
from .selector import MassProductionSelector

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """パイプライン実行統計"""

    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # 各段階の件数
    candidates_selected: int = 0
    episodes_generated: int = 0
    episodes_passed_gate: int = 0
    episodes_non_duplicate: int = 0
    episodes_final: int = 0

    # エラー統計
    generation_errors: int = 0
    evaluation_errors: int = 0

    # 時間統計（秒）
    selection_time: float = 0.0
    generation_time: float = 0.0
    evaluation_time: float = 0.0
    deduplication_time: float = 0.0
    ranking_time: float = 0.0
    persist_time: float = 0.0

    @property
    def total_time(self) -> float:
        """総実行時間"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def gate_pass_rate(self) -> float:
        """品質ゲート通過率"""
        if self.episodes_generated == 0:
            return 0.0
        return self.episodes_passed_gate / self.episodes_generated

    @property
    def dedup_pass_rate(self) -> float:
        """重複チェック通過率"""
        if self.episodes_passed_gate == 0:
            return 0.0
        return self.episodes_non_duplicate / self.episodes_passed_gate

    @property
    def overall_yield(self) -> float:
        """総合歩留まり（最終/生成）"""
        if self.episodes_generated == 0:
            return 0.0
        return self.episodes_final / self.episodes_generated

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_time_seconds": self.total_time,
            "candidates_selected": self.candidates_selected,
            "episodes_generated": self.episodes_generated,
            "episodes_passed_gate": self.episodes_passed_gate,
            "episodes_non_duplicate": self.episodes_non_duplicate,
            "episodes_final": self.episodes_final,
            "generation_errors": self.generation_errors,
            "evaluation_errors": self.evaluation_errors,
            "gate_pass_rate": self.gate_pass_rate,
            "dedup_pass_rate": self.dedup_pass_rate,
            "overall_yield": self.overall_yield,
            "time_breakdown": {
                "selection": self.selection_time,
                "generation": self.generation_time,
                "evaluation": self.evaluation_time,
                "deduplication": self.deduplication_time,
                "ranking": self.ranking_time,
                "persist": self.persist_time,
            },
        }

    def summary(self) -> str:
        """サマリー文字列"""
        return f"""
=== パイプライン実行結果 ===
総実行時間: {self.total_time:.1f}秒

【件数】
  候補選択: {self.candidates_selected}件
  生成完了: {self.episodes_generated}件
  品質通過: {self.episodes_passed_gate}件 ({self.gate_pass_rate:.1%})
  重複除外: {self.episodes_non_duplicate}件 ({self.dedup_pass_rate:.1%})
  最終出力: {self.episodes_final}件 ({self.overall_yield:.1%})

【エラー】
  生成エラー: {self.generation_errors}件
  評価エラー: {self.evaluation_errors}件

【時間内訳】
  候補選択: {self.selection_time:.1f}秒
  生成: {self.generation_time:.1f}秒
  評価: {self.evaluation_time:.1f}秒
  重複チェック: {self.deduplication_time:.1f}秒
  ランキング: {self.ranking_time:.1f}秒
  永続化: {self.persist_time:.1f}秒
"""


@dataclass
class PipelineResult:
    """パイプライン実行結果"""

    stats: PipelineStats
    episodes: List[Dict[str, Any]]
    output_path: Optional[Path] = None


class MassProductionPipeline:
    """大量生産パイプライン"""

    def __init__(
        self,
        llm_client: Any,
        config: Optional[MassProductionConfig] = None,
        master_csv_path: Optional[Path] = None,
        top_k: int = 1,
    ):
        """
        Args:
            llm_client: LLMクライアント（generate_async メソッドを持つ）
            config: パイプライン設定
            master_csv_path: マスターCSVパス
            top_k: 各人物×年齢グループから選択する件数
        """
        self.llm = llm_client
        self.config = config or DEFAULT_CONFIG
        self.master_csv_path = master_csv_path or MASTER_CSV_PATH
        self.top_k = top_k

        # コンポーネント初期化
        self._init_components()

    def _init_components(self) -> None:
        """コンポーネント初期化"""
        # セレクター
        self.selector = MassProductionSelector(
            master_csv_path=self.master_csv_path,
            config=self.config.selection,
        )

        # ジェネレーター
        self.generator = ParallelGenerator(
            llm_client=self.llm,
            config=self.config.generation,
        )

        # 評価器
        self.evaluator = BatchEvaluator(
            llm_client=self.llm,
            config=self.config.quality,
        )

        # ランカー
        self.ranker = FinalRanker()

    def _load_existing_texts(self) -> tuple[List[str], List[str]]:
        """既存エピソードテキストをロード"""
        import pandas as pd

        df = pd.read_csv(self.master_csv_path, dtype=str, low_memory=False)
        texts = df["episode_text"].fillna("").tolist()
        ids = df["episode_id"].fillna("").tolist()
        return texts, ids

    async def run_async(
        self,
        target_count: int = 500,
        category_filter: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        dry_run: bool = False,
    ) -> PipelineResult:
        """
        パイプライン非同期実行

        Args:
            target_count: 目標候補数
            category_filter: カテゴリフィルタ
            progress_callback: 進捗コールバック (stage, completed, total)
            dry_run: ドライラン（永続化しない）

        Returns:
            PipelineResult
        """
        stats = PipelineStats()

        def report(stage: str, completed: int, total: int):
            if progress_callback:
                progress_callback(stage, completed, total)
            logger.info(f"[{stage}] {completed}/{total}")

        # 1. 候補選択
        logger.info("=== Stage 1: 候補選択 ===")
        t0 = time.time()

        # Note: category_filterは将来拡張用（現在は使用されない）
        _ = category_filter  # unused for now
        candidates = self.selector.select_candidates(
            target_count=target_count,
        )
        stats.candidates_selected = len(candidates)
        stats.selection_time = time.time() - t0

        report("selection", len(candidates), target_count)

        if not candidates:
            logger.warning("候補が0件のため終了")
            stats.end_time = datetime.now()
            return PipelineResult(stats=stats, episodes=[])

        # 2. 生成入力作成
        inputs = [
            GenerationInput(
                person_id=c.person_id,
                person_name=c.person_name,
                age=c.age,
                category=c.category,
                birth_year=c.birth_year,
                death_year=c.death_year,
            )
            for c in candidates
        ]

        # 3. 並列生成
        logger.info("=== Stage 2: 並列生成 ===")
        t0 = time.time()

        gen_results = await self.generator.generate_batch(
            inputs,
            progress_callback=lambda c, t: report("generation", c, t),
        )
        stats.generation_time = time.time() - t0

        # 成功/失敗集計
        successful = [r for r in gen_results if r.success]
        stats.episodes_generated = len(successful)
        stats.generation_errors = len(gen_results) - len(successful)

        logger.info(f"生成完了: {len(successful)}件, エラー: {stats.generation_errors}件")

        if not successful:
            logger.warning("生成成功が0件のため終了")
            stats.end_time = datetime.now()
            return PipelineResult(stats=stats, episodes=[])

        # 4. 評価（品質ゲート）
        logger.info("=== Stage 3: 品質評価 ===")
        t0 = time.time()

        # GenerationResult → Dict 変換
        # birth_yearをinputsから取得してマップ
        birth_year_map = {(inp.person_name, inp.age): inp.birth_year for inp in inputs}
        episodes_for_eval = [
            {
                "person_id": r.person_id,
                "person_name": r.person_name,
                "age": r.age,
                "category": r.category,
                "episode_text": r.episode_text,
                "variation": r.variation,
                "template_style": r.template_style,
                "generation_time_ms": r.generation_time_ms,
                "birth_year": birth_year_map.get((r.person_name, r.age)),  # 年齢境界チェック用
                "person_type": "REAL",  # デフォルトは実在人物
            }
            for r in successful
        ]

        eval_results = self.evaluator.evaluate_batch(
            episodes_for_eval,
            progress_callback=lambda c, t: report("evaluation", c, t),
        )
        # EvaluationResult → Dict 変換
        evaluated = [
            {
                "person_id": ep.get("person_id", ""),
                "person_name": r.person_name,
                "age": r.age,
                "category": ep.get("category", ""),
                "episode_text": r.episode_text,
                "template_style": ep.get("template_style", ""),
                "scores": r.scores.to_dict(),
                "gate_passed": r.passed_gate,
                "gate_failures": r.gate_failures,
            }
            for r, ep in zip(eval_results, episodes_for_eval)
        ]
        stats.evaluation_time = time.time() - t0

        # ゲート通過のみ抽出
        passed = [ep for ep in evaluated if ep.get("gate_passed", False)]
        stats.episodes_passed_gate = len(passed)

        logger.info(f"品質通過: {len(passed)}/{len(evaluated)}件 ({stats.gate_pass_rate:.1%})")

        if not passed:
            logger.warning("品質通過が0件のため終了")
            stats.end_time = datetime.now()
            return PipelineResult(stats=stats, episodes=[])

        # 5. 重複チェック
        logger.info("=== Stage 4: 重複チェック ===")
        t0 = time.time()

        existing_texts, existing_ids = self._load_existing_texts()
        deduplicator = FastDeduplicator(
            existing_texts=existing_texts,
            existing_ids=existing_ids,
            threshold=self.config.quality.max_similarity_threshold,
        )

        non_duplicates = deduplicator.filter_non_duplicates(passed)
        stats.episodes_non_duplicate = len(non_duplicates)
        stats.deduplication_time = time.time() - t0

        logger.info(f"重複除外: {len(non_duplicates)}/{len(passed)}件 ({stats.dedup_pass_rate:.1%})")

        if not non_duplicates:
            logger.warning("重複除外後0件のため終了")
            stats.end_time = datetime.now()
            return PipelineResult(stats=stats, episodes=[])

        # 6. ランキング（人物×年齢ごとにベストN選択）
        logger.info(f"=== Stage 5: ランキング (top_k={self.top_k}) ===")
        t0 = time.time()

        final_episodes = self.ranker.select_best(non_duplicates, top_k=self.top_k)
        stats.episodes_final = len(final_episodes)
        stats.ranking_time = time.time() - t0

        logger.info(f"最終選択: {len(final_episodes)}件")

        # 7. 永続化
        output_path = None
        if not dry_run and final_episodes:
            logger.info("=== Stage 6: 永続化 ===")
            t0 = time.time()

            output_path = self._persist_episodes(final_episodes)
            stats.persist_time = time.time() - t0

            logger.info(f"保存完了: {output_path}")

        stats.end_time = datetime.now()

        return PipelineResult(
            stats=stats,
            episodes=final_episodes,
            output_path=output_path,
        )

    def run(
        self,
        target_count: int = 500,
        category_filter: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        dry_run: bool = False,
    ) -> PipelineResult:
        """
        パイプライン同期実行

        Args:
            target_count: 目標候補数
            category_filter: カテゴリフィルタ
            progress_callback: 進捗コールバック
            dry_run: ドライラン

        Returns:
            PipelineResult
        """
        return asyncio.run(
            self.run_async(
                target_count=target_count,
                category_filter=category_filter,
                progress_callback=progress_callback,
                dry_run=dry_run,
            )
        )

    def _persist_episodes(self, episodes: List[Dict]) -> Path:
        """
        エピソードを永続化

        Args:
            episodes: エピソードリスト

        Returns:
            出力ファイルパス
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.master_csv_path.parent / "generated"
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / f"mass_production_{timestamp}.csv"

        # 出力フィールド
        fieldnames = [
            "episode_id",
            "person_id",
            "person_name",
            "age",
            "category",
            "episode_text",
            "template_style",
            "factual_density_5",
            "generation_quality_5",
            "memorability_5",
            "unexpectedness_5",
            "story_quality_5",
            "educational_value_5",
            "empathy_5",
            "composite_score",
            "generated_at",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for ep in episodes:
                # エピソードID生成
                ep_id = f"EP-{timestamp}-{ep.get('person_id', 'UNK')[-4:]}"

                row = {
                    "episode_id": ep_id,
                    "person_id": ep.get("person_id", ""),
                    "person_name": ep.get("person_name", ""),
                    "age": ep.get("age", ""),
                    "category": ep.get("category", ""),
                    "episode_text": ep.get("episode_text", ""),
                    "template_style": ep.get("template_style", ""),
                    "factual_density_5": ep.get("scores", {}).get("factual_density", ""),
                    "generation_quality_5": ep.get("scores", {}).get("generation_quality", ""),
                    "memorability_5": ep.get("scores", {}).get("memorability", ""),
                    "unexpectedness_5": ep.get("scores", {}).get("unexpectedness", ""),
                    "story_quality_5": ep.get("scores", {}).get("story_quality", ""),
                    "educational_value_5": ep.get("scores", {}).get("educational_value", ""),
                    "empathy_5": ep.get("scores", {}).get("empathy", ""),
                    "composite_score": ep.get("scores", {}).get("composite", ""),
                    "generated_at": timestamp,
                }
                writer.writerow(row)

        return output_path


class DryRunPipeline:
    """ドライラン用軽量パイプライン"""

    def __init__(
        self,
        config: Optional[MassProductionConfig] = None,
        master_csv_path: Optional[Path] = None,
    ):
        self.config = config or DEFAULT_CONFIG
        self.master_csv_path = master_csv_path or MASTER_CSV_PATH

    def analyze(self, target_count: int = 500) -> Dict[str, Any]:
        """
        実行せずに分析

        Args:
            target_count: 目標候補数

        Returns:
            分析結果
        """
        selector = MassProductionSelector(
            master_csv_path=self.master_csv_path,
            config=self.config.selection,
        )

        candidates = selector.select_candidates(target_count=target_count)

        # カテゴリ分布
        category_dist: Dict[str, int] = {}
        for c in candidates:
            category_dist[c.category] = category_dist.get(c.category, 0) + 1

        # 選択理由分布
        reason_dist: Dict[str, int] = {}
        for c in candidates:
            reason_dist[c.selection_reason] = reason_dist.get(c.selection_reason, 0) + 1

        # 推定値
        expected_generated = len(candidates) * self.config.generation.candidates_per_input
        expected_passed = int(expected_generated * 0.6)  # 推定60%通過
        expected_final = int(expected_passed * 0.9)  # 推定90%重複除外

        return {
            "candidates": len(candidates),
            "expected_generated": expected_generated,
            "expected_passed_gate": expected_passed,
            "expected_final": expected_final,
            "category_distribution": category_dist,
            "reason_distribution": reason_dist,
            "config": {
                "max_workers": self.config.generation.max_workers,
                "candidates_per_input": self.config.generation.candidates_per_input,
                "quality_thresholds": {
                    "factual_density": self.config.quality.min_factual_density,
                    "generation_quality": self.config.quality.min_generation_quality,
                },
            },
        }


def main():
    """デモ実行"""
    from .generator import MockLLMClient

    print("=== パイプラインデモ（ドライラン） ===")

    # ドライラン分析
    dry_run = DryRunPipeline()
    analysis = dry_run.analyze(target_count=100)

    print(f"\n候補数: {analysis['candidates']}")
    print(f"推定生成数: {analysis['expected_generated']}")
    print(f"推定品質通過: {analysis['expected_passed_gate']}")
    print(f"推定最終出力: {analysis['expected_final']}")

    print("\nカテゴリ分布:")
    for cat, count in sorted(analysis["category_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    print("\n選択理由分布:")
    for reason, count in sorted(analysis["reason_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")

    # モックでパイプライン実行
    print("\n=== モック実行 ===")
    mock_llm = MockLLMClient(delay=0.01)
    pipeline = MassProductionPipeline(llm_client=mock_llm)

    result = pipeline.run(target_count=10, dry_run=True)

    print(result.stats.summary())


if __name__ == "__main__":
    main()
