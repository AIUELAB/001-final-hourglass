#!/usr/bin/env python3
"""
統合最適化知名度評価システム
4つの最適化戦略を統合して98日→4日を実現
"""

import pandas as pd
import numpy as np
import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Import optimization components
from ml_pre_filter import MLPreFilter, PredictionResult
from parallel_processor import ParallelProcessor, ProcessingResult
from three_layer_cache import ThreeLayerCache
from tiered_evaluation import TieredEvaluator, EvaluationTier

# Import existing components
from rate_limit_manager import RateLimitManager, APIProvider
from progress_tracker import ProgressTracker, ProgressMonitor
# from improved_recognition_system import ImprovedRecognitionScore  # Not needed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class OptimizationMetrics:
    """最適化メトリクス"""
    total_records: int
    api_calls_saved: int
    cache_hits: int
    parallel_speedup: float
    estimated_time_hours: float
    actual_time_hours: float = 0.0
    
    @property
    def api_reduction_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.api_calls_saved / self.total_records) * 100
    
    @property
    def cache_hit_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.cache_hits / self.total_records) * 100
    
    @property
    def speedup_factor(self) -> float:
        if self.actual_time_hours == 0:
            return 0.0
        baseline = self.total_records * 0.5  # 30分/件のベースライン
        return baseline / self.actual_time_hours


class OptimizedRecognitionSystem:
    """統合最適化システム"""
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        
        # Initialize components
        logger.info("🚀 最適化システム初期化中...")
        
        # 1. ML Pre-filter
        self.ml_filter = MLPreFilter()
        if Path("ml_prefilter_model.pkl").exists():
            self.ml_filter.load_model()
            logger.info("✅ MLモデル読み込み完了")
        
        # 2. Parallel Processor
        self.parallel_processor = ParallelProcessor(num_workers=5)
        logger.info("✅ 5ワーカー並列処理システム初期化")
        
        # 3. Three-layer Cache
        self.cache = ThreeLayerCache()
        logger.info("✅ 3層キャッシュシステム初期化")
        
        # 4. Tiered Evaluator
        self.tiered_evaluator = TieredEvaluator()
        logger.info("✅ 階層評価システム初期化")
        
        # 5. Existing components
        self.rate_limiter = RateLimitManager()
        self.progress_tracker = None
        self.progress_monitor = None
        # Note: ImprovedRecognitionScore is created per record, not here
        
        # Metrics
        self.metrics = None
        
        logger.info("✅ 統合最適化システム準備完了")
    
    async def process_database(
        self,
        csv_path: str,
        output_path: Optional[str] = None
    ) -> pd.DataFrame:
        """データベース処理のメインエントリポイント"""
        
        start_time = time.time()
        
        # Load data
        logger.info(f"📂 データベース読み込み中: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        if self.test_mode:
            df = df.head(20)
            logger.info(f"⚠️ テストモード: 最初の20件のみ処理")
        
        total_records = len(df)
        logger.info(f"✅ {total_records}件のレコードを読み込みました")
        
        # Initialize metrics
        self.metrics = OptimizationMetrics(
            total_records=total_records,
            api_calls_saved=0,
            cache_hits=0,
            parallel_speedup=1.0,
            estimated_time_hours=self._estimate_time(total_records)
        )
        
        # Display optimization plan
        self._display_optimization_plan(total_records)
        
        # Initialize progress tracking
        self.progress_tracker = ProgressTracker(total_records)
        self.progress_monitor = ProgressMonitor(self.progress_tracker)
        monitor_task = asyncio.create_task(self.progress_monitor.start_monitoring())
        
        try:
            # Phase 1: ML Pre-filtering
            logger.info("\n📊 Phase 1: ML事前フィルタリング")
            filtered_df = await self._phase1_ml_prefilter(df)
            
            # Phase 2: Cache Warming
            logger.info("\n📊 Phase 2: キャッシュウォーミング")
            await self._phase2_cache_warming(filtered_df)
            
            # Phase 3: Tiered Evaluation
            logger.info("\n📊 Phase 3: 階層評価決定")
            evaluation_plan = await self._phase3_tiered_evaluation(filtered_df)
            
            # Phase 4: Parallel Processing
            logger.info("\n📊 Phase 4: 並列処理実行")
            result_df = await self._phase4_parallel_processing(filtered_df, evaluation_plan)
            
            # Phase 5: Final Scoring
            logger.info("\n📊 Phase 5: 最終スコア計算")
            final_df = await self._phase5_final_scoring(result_df)
            
            # Calculate actual time
            elapsed_time = time.time() - start_time
            self.metrics.actual_time_hours = elapsed_time / 3600
            
            # Display results
            self._display_final_results(final_df)
            
            # Save results
            if output_path:
                self._save_results(final_df, output_path)
            
            return final_df
            
        finally:
            # Cleanup
            self.progress_monitor.stop_monitoring()
            await monitor_task
            self.cache.cleanup_expired()
    
    async def _phase1_ml_prefilter(self, df: pd.DataFrame) -> pd.DataFrame:
        """Phase 1: ML事前フィルタリング"""
        
        logger.info("🔍 ML事前フィルタリング実行中...")
        
        # Apply ML pre-filtering
        predictions, needs_api_df = self.ml_filter.predict(df)
        
        # Add predictions to dataframe
        for pred in predictions:
            mask = df['person_id'] == pred.person_id
            df.loc[mask, 'ml_score'] = pred.predicted_score
            df.loc[mask, 'ml_confidence'] = pred.confidence
            df.loc[mask, 'skip_api'] = pred.skip_api
            
            if pred.skip_api:
                self.metrics.api_calls_saved += 1
                df.loc[mask, 'final_score'] = pred.predicted_score
        
        stats = self.ml_filter.get_statistics(predictions)
        logger.info(f"✅ ML事前フィルタリング完了:")
        logger.info(f"   APIスキップ: {stats['api_skipped']} ({stats['skip_rate']:.1f}%)")
        logger.info(f"   API必要: {stats['api_required']}")
        
        return df
    
    async def _phase2_cache_warming(self, df: pd.DataFrame) -> None:
        """Phase 2: キャッシュウォーミング"""
        
        logger.info("🔥 キャッシュウォーミング中...")
        
        # Check cache for existing results
        cache_hits = 0
        for idx, row in df.iterrows():
            if row.get('skip_api', False):
                continue
            
            name = row.get('person_name_ja', row.get('person_name', ''))
            
            # Check each API cache
            for api in ['Google', 'YouTube', 'Twitter', 'News', 'Brave']:
                cached_value, layer = self.cache.get(api, name)
                if cached_value is not None:
                    cache_hits += 1
                    df.loc[idx, f'{api.lower()}_cached'] = True
        
        self.metrics.cache_hits = cache_hits
        logger.info(f"✅ キャッシュヒット: {cache_hits}件")
        
        # Optimize cache distribution
        self.cache.optimize_cache_distribution()
    
    async def _phase3_tiered_evaluation(self, df: pd.DataFrame) -> Dict:
        """Phase 3: 階層評価決定"""
        
        logger.info("📊 階層評価プラン作成中...")
        
        evaluation_plan = {}
        tier_counts = {tier: 0 for tier in EvaluationTier}
        
        for idx, row in df.iterrows():
            if row.get('skip_api', False):
                continue
            
            # Determine tier based on ML score and category
            ml_score = row.get('ml_score', 5.0)
            tier = self.tiered_evaluator.determine_tier(row, ml_score)
            
            evaluation_plan[row['person_id']] = {
                'tier': tier,
                'apis': self.tiered_evaluator.get_apis_for_tier(tier),
                'ml_score': ml_score
            }
            tier_counts[tier] += 1
        
        # Display tier distribution
        logger.info("✅ 階層評価分布:")
        for tier, count in tier_counts.items():
            if count > 0:
                logger.info(f"   {tier.value}: {count}件")
        
        return evaluation_plan
    
    async def _phase4_parallel_processing(
        self,
        df: pd.DataFrame,
        evaluation_plan: Dict
    ) -> pd.DataFrame:
        """Phase 4: 並列処理実行"""
        
        logger.info("🚀 5ワーカー並列処理開始...")
        
        # Prepare data for parallel processing
        needs_api_df = df[~df.get('skip_api', False)].copy()
        
        # Add tier information
        for person_id, plan in evaluation_plan.items():
            mask = needs_api_df['person_id'] == person_id
            needs_api_df.loc[mask, 'evaluation_tier'] = plan['tier'].value
            needs_api_df.loc[mask, 'required_apis'] = ','.join(plan['apis'])
        
        # Execute parallel processing
        start_time = time.time()
        result_df = await self.parallel_processor.process_batch_async(
            needs_api_df,
            tiered_strategy=True,
            cache_enabled=True
        )
        elapsed = time.time() - start_time
        
        # Calculate speedup
        sequential_estimate = len(needs_api_df) * 30  # 30秒/件の推定
        self.metrics.parallel_speedup = sequential_estimate / elapsed
        
        logger.info(f"✅ 並列処理完了: {elapsed:.1f}秒")
        logger.info(f"   スピードアップ: {self.metrics.parallel_speedup:.1f}x")
        
        # Merge results back
        for col in result_df.columns:
            if col not in df.columns:
                df[col] = None
        
        for idx, row in result_df.iterrows():
            mask = df['person_id'] == row['person_id']
            for col in result_df.columns:
                df.loc[mask, col] = row[col]
        
        return df
    
    async def _phase5_final_scoring(self, df: pd.DataFrame) -> pd.DataFrame:
        """Phase 5: 最終スコア計算"""
        
        logger.info("🎯 最終スコア計算中...")
        
        for idx, row in df.iterrows():
            if pd.notna(row.get('final_score')):
                continue  # Already has final score from ML
            
            # Aggregate API results
            api_scores = []
            
            # Parse API results
            for api in ['Google', 'YouTube', 'Twitter', 'News', 'Brave']:
                result_col = f'{api.lower()}_result'
                if result_col in row and pd.notna(row[result_col]):
                    try:
                        result = eval(row[result_col]) if isinstance(row[result_col], str) else row[result_col]
                        if isinstance(result, dict):
                            # Extract score based on API type
                            if api == 'Google' and 'results' in result:
                                score = self._calculate_google_score(result['results'])
                            elif api == 'YouTube' and 'views' in result:
                                score = self._calculate_youtube_score(result['views'])
                            elif api == 'Twitter' and 'mentions' in result:
                                score = self._calculate_twitter_score(result['mentions'])
                            elif api == 'News' and 'articles' in result:
                                score = self._calculate_news_score(result['articles'])
                            elif api == 'Brave' and 'results' in result:
                                score = self._calculate_brave_score(result['results'])
                            else:
                                score = 5.0
                            
                            api_scores.append(score)
                    except:
                        pass
            
            # Calculate final score
            if api_scores:
                final_score = np.mean(api_scores)
            else:
                final_score = row.get('ml_score', 5.0)
            
            df.loc[idx, 'final_score'] = final_score
            
            # Update progress
            if self.progress_tracker:
                self.progress_tracker.update(1)
        
        logger.info("✅ 最終スコア計算完了")
        return df
    
    def _calculate_google_score(self, results: int) -> float:
        """Google検索結果からスコア計算"""
        if results >= 100_000_000:
            return 10.0
        elif results >= 10_000_000:
            return 9.0
        elif results >= 1_000_000:
            return 8.0
        elif results >= 100_000:
            return 7.0
        elif results >= 10_000:
            return 6.0
        elif results >= 1_000:
            return 5.0
        elif results >= 100:
            return 4.0
        elif results >= 10:
            return 3.0
        elif results >= 1:
            return 2.0
        else:
            return 1.0
    
    def _calculate_youtube_score(self, views: int) -> float:
        """YouTube視聴回数からスコア計算"""
        if views >= 100_000_000:
            return 10.0
        elif views >= 10_000_000:
            return 9.0
        elif views >= 1_000_000:
            return 8.0
        elif views >= 100_000:
            return 7.0
        elif views >= 10_000:
            return 6.0
        else:
            return 5.0
    
    def _calculate_twitter_score(self, mentions: int) -> float:
        """Twitterメンションからスコア計算"""
        if mentions >= 1_000_000:
            return 10.0
        elif mentions >= 100_000:
            return 9.0
        elif mentions >= 10_000:
            return 8.0
        elif mentions >= 1_000:
            return 7.0
        else:
            return 6.0
    
    def _calculate_news_score(self, articles: int) -> float:
        """ニュース記事数からスコア計算"""
        if articles >= 1_000:
            return 10.0
        elif articles >= 100:
            return 8.0
        elif articles >= 10:
            return 6.0
        else:
            return 4.0
    
    def _calculate_brave_score(self, results: int) -> float:
        """Brave検索結果からスコア計算"""
        if results >= 10_000:
            return 9.0
        elif results >= 1_000:
            return 7.0
        elif results >= 100:
            return 5.0
        else:
            return 3.0
    
    def _estimate_time(self, total_records: int) -> float:
        """処理時間推定（時間）"""
        # Optimized estimation
        # ML filtering: 35% skip
        api_calls = total_records * 0.65
        
        # Parallel processing: 5x speedup
        # Caching: 20% hit rate
        # Tiered evaluation: 40% reduction in API calls
        
        effective_calls = api_calls * 0.8 * 0.6
        time_per_call = 5  # 5 seconds average with optimization
        
        total_seconds = effective_calls * time_per_call / 5  # 5 parallel workers
        return total_seconds / 3600
    
    def _display_optimization_plan(self, total_records: int):
        """最適化プラン表示"""
        print("\n" + "=" * 70)
        print("📊 最適化実行プラン - 98日→4日短縮")
        print("=" * 70)
        
        print(f"\n📈 処理対象: {total_records}件")
        print(f"⏱️ 推定処理時間: {self.metrics.estimated_time_hours:.1f}時間 ({self.metrics.estimated_time_hours/24:.1f}日)")
        
        print("\n🚀 最適化戦略:")
        print("  1. ML事前フィルタリング: ~35% API呼び出し削減")
        print("  2. 3層キャッシュ: ~20% 再利用率")
        print("  3. 階層評価: ~40% API呼び出し削減")
        print("  4. 5ワーカー並列処理: ~5x高速化")
        
        print("\n📊 期待される改善:")
        baseline_hours = total_records * 0.5  # 30分/件
        print(f"  ベースライン: {baseline_hours:.1f}時間 ({baseline_hours/24:.1f}日)")
        print(f"  最適化後: {self.metrics.estimated_time_hours:.1f}時間 ({self.metrics.estimated_time_hours/24:.1f}日)")
        print(f"  短縮率: {(1 - self.metrics.estimated_time_hours/baseline_hours)*100:.1f}%")
        print("=" * 70)
    
    def _display_final_results(self, df: pd.DataFrame):
        """最終結果表示"""
        print("\n" + "=" * 70)
        print("✅ 処理完了")
        print("=" * 70)
        
        print(f"\n📊 処理統計:")
        print(f"  総レコード数: {self.metrics.total_records}")
        print(f"  API呼び出し削減: {self.metrics.api_calls_saved} ({self.metrics.api_reduction_rate:.1f}%)")
        print(f"  キャッシュヒット: {self.metrics.cache_hits} ({self.metrics.cache_hit_rate:.1f}%)")
        print(f"  並列化高速化: {self.metrics.parallel_speedup:.1f}x")
        
        print(f"\n⏱️ 処理時間:")
        print(f"  推定時間: {self.metrics.estimated_time_hours:.1f}時間")
        print(f"  実際の時間: {self.metrics.actual_time_hours:.1f}時間")
        print(f"  高速化率: {self.metrics.speedup_factor:.1f}x")
        
        # Score distribution
        print(f"\n📈 スコア分布:")
        score_dist = pd.cut(df['final_score'], bins=[0, 2, 4, 6, 8, 10], 
                          labels=['1-2', '3-4', '5-6', '7-8', '9-10'])
        for category, count in score_dist.value_counts().sort_index().items():
            print(f"  {category}: {count}件")
        
        print("=" * 70)
    
    def _save_results(self, df: pd.DataFrame, output_path: str):
        """結果保存"""
        # Save with UTF-8 BOM for Excel
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)
        
        logger.info(f"✅ 結果を保存しました: {output_path}")
        
        # Save metrics
        metrics_path = output_path.replace('.csv', '_metrics.json')
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump({
                'total_records': self.metrics.total_records,
                'api_calls_saved': self.metrics.api_calls_saved,
                'api_reduction_rate': self.metrics.api_reduction_rate,
                'cache_hits': self.metrics.cache_hits,
                'cache_hit_rate': self.metrics.cache_hit_rate,
                'parallel_speedup': self.metrics.parallel_speedup,
                'estimated_time_hours': self.metrics.estimated_time_hours,
                'actual_time_hours': self.metrics.actual_time_hours,
                'speedup_factor': self.metrics.speedup_factor
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ メトリクスを保存しました: {metrics_path}")


async def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='最適化知名度評価システム')
    parser.add_argument('--input', '-i', required=True, help='入力CSVファイル')
    parser.add_argument('--output', '-o', help='出力CSVファイル')
    parser.add_argument('--test', action='store_true', help='テストモード（20件のみ）')
    
    args = parser.parse_args()
    
    # Default output path
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'optimized_recognition_{timestamp}.csv'
    
    # Initialize system
    system = OptimizedRecognitionSystem(test_mode=args.test)
    
    # Process database
    try:
        result_df = await system.process_database(
            csv_path=args.input,
            output_path=args.output
        )
        
        print(f"\n✅ 処理が正常に完了しました")
        print(f"📁 結果ファイル: {args.output}")
        
    except Exception as e:
        logger.error(f"❌ エラーが発生しました: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())