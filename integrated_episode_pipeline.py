#!/usr/bin/env python3
"""
統合エピソード生成パイプライン
Integrated Episode Generation Pipeline

有名人データベース → 候補選定 → エピソード生成 → マージ
の全プロセスを統合した自動化システム

アーキテクチャ:
┌─────────────────────────────────────────────────────────────┐
│  episode_database.db (2,702名の有名人データベース)           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  EpisodeCandidateSelector (候補選定)                        │
│  - CharacterTypeClassifier (架空キャラクター除外)            │
│  - 知名度スコアと年齢分散でランキング                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  ProductionEpisodeGenerator (バッチ生成)                    │
│  - SmartIterationEngine (最大3回反復改善)                   │
│  - InstantQualityGate (8項目検証)                          │
│  - HybridImpactEvaluator (LLM評価30点)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  EpisodeMergeTool (既存データとマージ)                       │
│  - 品質ベース選択 (min_gate_score: 8.0)                     │
│  - 重複除外                                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  episodes_merged.csv (最終出力)                             │
└─────────────────────────────────────────────────────────────┘

Created: 2025-10-02
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# プロジェクト内モジュール
from episode_candidate_selector import EpisodeCandidateSelector, EpisodeCandidate
from production_episode_generator import ProductionEpisodeGenerator
from episode_merge_tool import EpisodeMergeTool

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """パイプライン設定"""
    # 候補選定
    min_recognition_score: float = 0.0  # 最小知名度スコア
    max_candidates: int = 100            # 最大候補数
    exclude_fictional: bool = True       # 架空キャラクター除外
    age_range: tuple = (20, 70)          # エピソード生成年齢範囲

    # エピソード生成
    llm_provider: str = "openai"         # LLMプロバイダー
    llm_model: Optional[str] = None      # モデル名
    max_iterations: int = 3              # 最大反復回数
    target_score: float = 8.0            # 目標Gateスコア
    episodes_per_person: int = 2         # 1人あたりエピソード数

    # マージ
    min_gate_score: float = 8.0          # 最小Gateスコア
    min_total_score: float = 25.0        # 最小総合スコア
    prefer_new: bool = False             # 新規エピソード優先


@dataclass
class PipelineResult:
    """パイプライン実行結果"""
    success: bool
    total_candidates: int
    episodes_generated: int
    episodes_succeeded: int
    episodes_failed: int
    episodes_merged: int
    execution_time: float
    output_files: Dict[str, str]
    statistics: Dict
    errors: List[str]


class IntegratedEpisodePipeline:
    """統合エピソード生成パイプライン"""

    def __init__(
        self,
        config: PipelineConfig,
        database_path: str = "episode_database.db",
        existing_episodes_path: Optional[str] = None
    ):
        """
        初期化

        Args:
            config: パイプライン設定
            database_path: 有名人データベースパス
            existing_episodes_path: 既存エピソードCSVパス
        """
        self.config = config
        self.database_path = database_path
        self.existing_episodes_path = existing_episodes_path

        # コンポーネント初期化
        self.candidate_selector = EpisodeCandidateSelector(
            db_path=database_path,
            min_recognition_score=config.min_recognition_score,
            max_candidates=config.max_candidates
        )

        self.episode_generator = ProductionEpisodeGenerator(
            llm_provider=config.llm_provider,
            model=config.llm_model,
            enable_llm_evaluation=True,
            max_iterations=config.max_iterations,
            target_score=config.target_score
        )

        self.merge_tool = EpisodeMergeTool(
            min_gate_score=config.min_gate_score,
            min_total_score=config.min_total_score,
            prefer_new=config.prefer_new
        )

        logger.info(f"🚀 統合エピソード生成パイプライン初期化完了")

    def run(
        self,
        categories: Optional[List[str]] = None,
        output_prefix: str = "pipeline"
    ) -> PipelineResult:
        """
        パイプライン全体を実行

        Args:
            categories: カテゴリフィルター
            output_prefix: 出力ファイル名プレフィックス

        Returns:
            実行結果
        """
        start_time = datetime.now()
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        errors = []

        try:
            # ========================================
            # Step 1: 候補選定
            # ========================================
            logger.info(f"\n{'='*60}")
            logger.info(f"📋 Step 1: エピソード候補選定")
            logger.info(f"{'='*60}")

            candidates = self.candidate_selector.select_candidates(
                categories=categories,
                exclude_fictional=self.config.exclude_fictional,
                age_range=self.config.age_range
            )

            if not candidates:
                raise ValueError("候補が0件です。min_recognition_scoreを下げてください。")

            # 候補リストをCSV出力
            candidates_csv = f"{output_prefix}_candidates_{timestamp}.csv"
            self.candidate_selector.export_to_csv(candidates, candidates_csv)

            logger.info(f"✅ 候補選定完了: {len(candidates)}名")

            # ========================================
            # Step 2: バッチ入力生成
            # ========================================
            logger.info(f"\n{'='*60}")
            logger.info(f"🎬 Step 2: バッチ入力生成")
            logger.info(f"{'='*60}")

            batch_input = self.candidate_selector.generate_episode_batch_input(
                candidates,
                episodes_per_person=self.config.episodes_per_person
            )

            logger.info(f"✅ バッチ入力生成完了: {len(batch_input)}エピソード")

            # ========================================
            # Step 3: エピソード生成
            # ========================================
            logger.info(f"\n{'='*60}")
            logger.info(f"🎨 Step 3: エピソード生成")
            logger.info(f"{'='*60}")

            # バッチ入力を人物リストに変換
            persons = [
                {
                    'name': item['person_name'],
                    'age': item['age'],
                    'category': item['category'],
                    'person_id': item.get('person_id'),
                    'birth_year': item.get('birth_year')
                }
                for item in batch_input
            ]

            # バッチ生成
            results = self.episode_generator.generate_batch(persons)

            # 生成結果をCSV出力
            generated_csv = f"{output_prefix}_generated_{timestamp}.csv"
            self.episode_generator.save_to_csv(results, generated_csv)

            episodes_succeeded = sum(1 for r in results if r['success'])
            episodes_failed = len(results) - episodes_succeeded

            logger.info(f"✅ エピソード生成完了")
            logger.info(f"  成功: {episodes_succeeded}/{len(results)}")
            logger.info(f"  失敗: {episodes_failed}/{len(results)}")

            # ========================================
            # Step 4: 既存データとマージ
            # ========================================
            if self.existing_episodes_path:
                logger.info(f"\n{'='*60}")
                logger.info(f"🔀 Step 4: 既存データとマージ")
                logger.info(f"{'='*60}")

                # 既存エピソード読み込み
                existing = self.merge_tool.load_csv(self.existing_episodes_path)

                # 新規エピソード読み込み
                new = self.merge_tool.load_csv(generated_csv)

                # マージ実行
                merged = self.merge_tool.merge(existing, new)

                # マージ結果を保存
                merged_csv = f"{output_prefix}_merged_{timestamp}.csv"
                self.merge_tool.save_merged(merged, merged_csv)

                # 統計表示
                self.merge_tool.print_statistics()

                # レポート保存
                self.merge_tool.save_report(merged_csv)

                logger.info(f"✅ マージ完了: {len(merged)}エピソード")

                output_files = {
                    'candidates': candidates_csv,
                    'generated': generated_csv,
                    'merged': merged_csv
                }
                episodes_merged = len(merged)

            else:
                logger.info(f"\n既存エピソードパスが指定されていないため、マージをスキップ")
                output_files = {
                    'candidates': candidates_csv,
                    'generated': generated_csv
                }
                episodes_merged = 0

            # ========================================
            # 完了
            # ========================================
            execution_time = (datetime.now() - start_time).total_seconds()

            result = PipelineResult(
                success=True,
                total_candidates=len(candidates),
                episodes_generated=len(results),
                episodes_succeeded=episodes_succeeded,
                episodes_failed=episodes_failed,
                episodes_merged=episodes_merged,
                execution_time=execution_time,
                output_files=output_files,
                statistics={
                    'avg_gate_score': sum(r['gate_score'] for r in results if r['success']) / max(1, episodes_succeeded),
                    'avg_llm_score': sum(r['llm_score'] for r in results if r['success'] and r['llm_score']) / max(1, episodes_succeeded),
                    'avg_iterations': sum(r['iterations'] for r in results) / len(results),
                    'total_tokens': sum(r['tokens_used'] for r in results),
                },
                errors=errors
            )

            logger.info(f"\n{'='*60}")
            logger.info(f"🎉 パイプライン完了")
            logger.info(f"{'='*60}")
            logger.info(f"実行時間: {execution_time:.1f}秒")
            logger.info(f"総候補数: {result.total_candidates}名")
            logger.info(f"生成数: {result.episodes_generated}エピソード")
            logger.info(f"成功率: {episodes_succeeded}/{result.episodes_generated} ({episodes_succeeded/max(1, result.episodes_generated)*100:.1f}%)")
            logger.info(f"出力ファイル:")
            for key, path in output_files.items():
                logger.info(f"  {key}: {path}")

            return result

        except Exception as e:
            logger.error(f"❌ パイプラインエラー: {e}")
            import traceback
            traceback.print_exc()

            execution_time = (datetime.now() - start_time).total_seconds()

            return PipelineResult(
                success=False,
                total_candidates=0,
                episodes_generated=0,
                episodes_succeeded=0,
                episodes_failed=0,
                episodes_merged=0,
                execution_time=execution_time,
                output_files={},
                statistics={},
                errors=[str(e)]
            )


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="Integrated Episode Pipeline")

    # 候補選定
    parser.add_argument('--max-candidates', type=int, default=50, help='最大候補数')
    parser.add_argument('--min-score', type=float, default=0.0, help='最小知名度スコア')
    parser.add_argument('--categories', nargs='+', help='カテゴリフィルター')

    # エピソード生成
    parser.add_argument('--provider', choices=['openai', 'anthropic'], default='openai', help='LLMプロバイダー')
    parser.add_argument('--model', help='モデル名')
    parser.add_argument('--episodes-per-person', type=int, default=2, help='1人あたりエピソード数')

    # マージ
    parser.add_argument('--existing', help='既存エピソードCSVパス')
    parser.add_argument('--output-prefix', default='pipeline', help='出力ファイル名プレフィックス')

    args = parser.parse_args()

    # 設定作成
    config = PipelineConfig(
        min_recognition_score=args.min_score,
        max_candidates=args.max_candidates,
        llm_provider=args.provider,
        llm_model=args.model,
        episodes_per_person=args.episodes_per_person
    )

    # パイプライン実行
    pipeline = IntegratedEpisodePipeline(
        config=config,
        existing_episodes_path=args.existing
    )

    result = pipeline.run(
        categories=args.categories,
        output_prefix=args.output_prefix
    )

    # 終了コード
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
