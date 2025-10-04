#!/usr/bin/env python3
"""
Production Episode Processor - 本番エピソード処理システム
Phase 5 - Real Production Operations
"""

import asyncio
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import os
import sys
from dataclasses import dataclass, asdict
import logging
from pathlib import Path
import aiohttp
import numpy as np
from collections import defaultdict
import time

# 既存システムのインポート
from integrated_quality_system import IntegratedQualitySystem
from multi_agent_orchestrator import MultiAgentOrchestrator
from autonomous_quality_system import AutonomousQualitySystem
from prometheus_exporter import MetricsExporter

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessingMetrics:
    """処理メトリクス"""
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    average_time: float = 0.0
    error_rate: float = 0.0
    consensus_rate: float = 0.0
    ml_accuracy: float = 0.0
    cache_hits: int = 0
    timestamp: str = ""

@dataclass
class BatchResult:
    """バッチ処理結果"""
    batch_id: str
    start_time: datetime
    end_time: datetime
    total_episodes: int
    successful: int
    failed: int
    errors: List[Dict]
    metrics: ProcessingMetrics
    quality_distribution: Dict[str, int]

class ProductionEpisodeProcessor:
    """本番エピソード処理システム"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._load_config()
        self.quality_system = None
        self.orchestrator = None
        self.autonomous_system = None
        self.metrics_exporter = None

        # 処理統計
        self.total_metrics = ProcessingMetrics()
        self.batch_history = []
        self.error_patterns = defaultdict(int)

        # キャッシュ
        self.decision_cache = {}
        self.cache_ttl = 3600  # 1時間

        # バッチ設定
        self.batch_size = self.config.get('batch_size', 100)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 5)

    def _load_config(self) -> Dict:
        """設定ロード"""
        config_path = Path('.env.production')
        if config_path.exists():
            config = {}
            with open(config_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        config[key] = value
            return config

        # デフォルト設定
        return {
            'batch_size': 100,
            'max_workers': 10,
            'timeout': 30,
            'enable_cache': True,
            'enable_metrics': True,
            'ml_auto_retrain': True,
            'ml_retrain_threshold': 0.85
        }

    async def initialize(self):
        """システム初期化"""
        logger.info("="*70)
        logger.info("🚀 Production Episode Processor 初期化")
        logger.info("="*70)

        # 各システムの初期化
        self.quality_system = IntegratedQualitySystem(enable_collaboration=True)
        await self.quality_system.initialize()

        self.orchestrator = MultiAgentOrchestrator()
        self.autonomous_system = AutonomousQualitySystem(
            orchestrator=self.orchestrator,
            auto_improve=True
        )
        await self.autonomous_system.initialize()

        # メトリクスエクスポーター
        if self.config.get('enable_metrics'):
            self.metrics_exporter = MetricsExporter(port=9090)
            asyncio.create_task(self.metrics_exporter.start())

        logger.info("✅ システム初期化完了")

    async def process_batch(
        self,
        episodes: List[Dict],
        batch_id: Optional[str] = None
    ) -> BatchResult:
        """バッチ処理"""
        batch_id = batch_id or f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        logger.info(f"\n📦 バッチ処理開始: {batch_id}")
        logger.info(f"   エピソード数: {len(episodes)}")

        results = []
        errors = []
        quality_distribution = defaultdict(int)

        # 並列処理用のタスク作成
        tasks = []
        for i, episode in enumerate(episodes):
            # キャッシュチェック
            cache_key = self._get_cache_key(episode)
            if cache_key in self.decision_cache:
                cached = self.decision_cache[cache_key]
                if self._is_cache_valid(cached):
                    results.append(cached['result'])
                    self.total_metrics.cache_hits += 1
                    continue

            # 処理タスク追加
            tasks.append(self._process_single_episode(episode, i))

        # 並列実行
        if tasks:
            processed = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(processed):
                if isinstance(result, Exception):
                    error_info = {
                        'episode_index': i,
                        'error': str(result),
                        'type': type(result).__name__
                    }
                    errors.append(error_info)
                    self.error_patterns[error_info['type']] += 1
                    logger.error(f"❌ エピソード処理エラー: {error_info}")
                else:
                    results.append(result)
                    quality_distribution[result.get('quality_status', 'unknown')] += 1

                    # キャッシュ保存
                    cache_key = self._get_cache_key(episodes[i])
                    self.decision_cache[cache_key] = {
                        'result': result,
                        'timestamp': time.time()
                    }

        # メトリクス計算
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        successful = len(results)
        failed = len(errors)

        batch_result = BatchResult(
            batch_id=batch_id,
            start_time=start_time,
            end_time=end_time,
            total_episodes=len(episodes),
            successful=successful,
            failed=failed,
            errors=errors,
            metrics=ProcessingMetrics(
                total_processed=len(episodes),
                successful=successful,
                failed=failed,
                average_time=processing_time / len(episodes) if episodes else 0,
                error_rate=failed / len(episodes) if episodes else 0,
                consensus_rate=self._calculate_consensus_rate(results),
                ml_accuracy=await self._get_ml_accuracy(),
                cache_hits=self.total_metrics.cache_hits,
                timestamp=datetime.now().isoformat()
            ),
            quality_distribution=dict(quality_distribution)
        )

        # 統計更新
        self._update_total_metrics(batch_result)
        self.batch_history.append(batch_result)

        # メトリクスエクスポート
        if self.metrics_exporter:
            await self._export_metrics(batch_result)

        # レポート表示
        self._display_batch_report(batch_result)

        return batch_result

    async def _process_single_episode(
        self,
        episode: Dict,
        index: int
    ) -> Dict:
        """単一エピソード処理"""
        try:
            start = time.time()

            # マルチエージェント協議
            decision = await self.orchestrator.process(
                episode.get('episode_text', ''),
                {
                    'person_name': episode.get('person_name'),
                    'episode_age': episode.get('episode_age'),
                    'person_id': episode.get('person_id', f'P{index:03d}')
                },
                consensus_method='weighted'
            )

            # 品質ゲートチェック
            gate_result = self.quality_system.quality_gate.check_episode(episode)

            # 結果統合
            result = {
                **episode,
                'quality_status': self._determine_status(decision, gate_result),
                'consensus': decision.consensus,
                'confidence': decision.confidence,
                'quality_score': gate_result.score,
                'processing_time': time.time() - start,
                'agent_votes': {
                    agent.agent_id: vote.decision.value
                    for agent, vote in zip(
                        self.orchestrator.agents,
                        decision.votes
                    )
                },
                'timestamp': datetime.now().isoformat()
            }

            # 進捗表示
            if (index + 1) % 10 == 0:
                logger.info(f"   進捗: {index + 1} 完了")

            return result

        except Exception as e:
            logger.error(f"Episode {index} processing error: {e}")
            raise

    def _determine_status(self, decision, gate_result) -> str:
        """最終ステータス決定"""
        if decision.result == 'APPROVE' and gate_result.score >= 80:
            return 'approved'
        elif decision.result == 'APPROVE' and gate_result.score >= 70:
            return 'approved_with_caution'
        elif decision.result == 'REJECT':
            return 'rejected'
        else:
            return 'review_required'

    def _get_cache_key(self, episode: Dict) -> str:
        """キャッシュキー生成"""
        return hashlib.md5(
            f"{episode.get('person_name', '')}_{episode.get('episode_text', '')}".encode()
        ).hexdigest()

    def _is_cache_valid(self, cached: Dict) -> bool:
        """キャッシュ有効性チェック"""
        if not self.config.get('enable_cache'):
            return False
        return time.time() - cached['timestamp'] < self.cache_ttl

    def _calculate_consensus_rate(self, results: List[Dict]) -> float:
        """コンセンサス率計算"""
        if not results:
            return 0.0
        consensus_count = sum(1 for r in results if r.get('consensus'))
        return consensus_count / len(results)

    async def _get_ml_accuracy(self) -> float:
        """ML精度取得"""
        if self.autonomous_system and self.autonomous_system.ml_model:
            return self.autonomous_system.current_accuracy
        return 0.0

    def _update_total_metrics(self, batch_result: BatchResult):
        """総合メトリクス更新"""
        self.total_metrics.total_processed += batch_result.total_episodes
        self.total_metrics.successful += batch_result.successful
        self.total_metrics.failed += batch_result.failed

        # 移動平均で更新
        alpha = 0.1  # 平滑化係数
        self.total_metrics.average_time = (
            alpha * batch_result.metrics.average_time +
            (1 - alpha) * self.total_metrics.average_time
        )
        self.total_metrics.error_rate = (
            alpha * batch_result.metrics.error_rate +
            (1 - alpha) * self.total_metrics.error_rate
        )
        self.total_metrics.consensus_rate = (
            alpha * batch_result.metrics.consensus_rate +
            (1 - alpha) * self.total_metrics.consensus_rate
        )

    async def _export_metrics(self, batch_result: BatchResult):
        """メトリクスエクスポート"""
        if not self.metrics_exporter:
            return

        # バッチメトリクス記録
        for i in range(batch_result.successful):
            self.metrics_exporter.record_episode_processing(
                agent='orchestrator',
                status='success',
                duration=batch_result.metrics.average_time
            )

        for i in range(batch_result.failed):
            self.metrics_exporter.record_episode_processing(
                agent='orchestrator',
                status='error',
                duration=batch_result.metrics.average_time
            )

        # ML精度更新
        self.metrics_exporter.update_ml_metrics(
            accuracy=batch_result.metrics.ml_accuracy,
            prediction_time=0.05
        )

    def _display_batch_report(self, batch_result: BatchResult):
        """バッチレポート表示"""
        print("\n" + "="*70)
        print(f"📊 バッチ処理レポート: {batch_result.batch_id}")
        print("="*70)
        print(f"処理時間: {(batch_result.end_time - batch_result.start_time).total_seconds():.2f}秒")
        print(f"総エピソード数: {batch_result.total_episodes}")
        print(f"成功: {batch_result.successful} ({batch_result.successful/batch_result.total_episodes*100:.1f}%)")
        print(f"失敗: {batch_result.failed}")
        print(f"平均処理時間: {batch_result.metrics.average_time:.3f}秒/エピソード")
        print(f"エラー率: {batch_result.metrics.error_rate:.2%}")
        print(f"コンセンサス率: {batch_result.metrics.consensus_rate:.1%}")
        print(f"ML精度: {batch_result.metrics.ml_accuracy:.1%}")
        print(f"キャッシュヒット: {batch_result.metrics.cache_hits}")

        if batch_result.quality_distribution:
            print("\n品質分布:")
            for status, count in batch_result.quality_distribution.items():
                print(f"  {status}: {count}")

        if batch_result.errors:
            print(f"\n⚠️ エラー: {len(batch_result.errors)}件")
            for error in batch_result.errors[:3]:  # 最初の3件のみ表示
                print(f"  - {error['type']}: {error['error'][:50]}...")

    async def process_production_data(
        self,
        csv_file: str,
        output_file: Optional[str] = None
    ) -> pd.DataFrame:
        """本番データ処理"""
        logger.info(f"\n🏭 本番データ処理開始: {csv_file}")

        # データ読み込み
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        total_episodes = len(df)
        logger.info(f"   総エピソード数: {total_episodes}")

        # バッチ分割
        batches = []
        for i in range(0, total_episodes, self.batch_size):
            batch_df = df.iloc[i:i+self.batch_size]
            batches.append(batch_df.to_dict('records'))

        logger.info(f"   バッチ数: {len(batches)} (各{self.batch_size}件)")

        # バッチごとに処理
        all_results = []
        for i, batch in enumerate(batches, 1):
            logger.info(f"\n🔄 バッチ {i}/{len(batches)} 処理中...")

            batch_result = await self.process_batch(
                batch,
                batch_id=f"prod_batch_{i:03d}"
            )

            # 結果収集
            all_results.extend(batch_result.metrics.__dict__)

            # ML再訓練チェック
            if (self.config.get('ml_auto_retrain') and
                batch_result.metrics.ml_accuracy < float(self.config.get('ml_retrain_threshold', 0.85))):
                logger.info("🧠 ML精度低下検出 - 再訓練開始...")
                await self.autonomous_system.retrain_model()

        # 結果をDataFrameに変換
        result_df = pd.DataFrame(all_results)

        # 保存
        if output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = output_file or f'production_results_{timestamp}.csv'
            result_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"\n✅ 結果保存: {output_path}")

        # 最終レポート
        self._display_final_report()

        return result_df

    def _display_final_report(self):
        """最終レポート表示"""
        print("\n" + "="*70)
        print("📈 本番処理最終レポート")
        print("="*70)
        print(f"総処理エピソード: {self.total_metrics.total_processed}")
        print(f"成功: {self.total_metrics.successful}")
        print(f"失敗: {self.total_metrics.failed}")
        print(f"総合エラー率: {self.total_metrics.error_rate:.2%}")
        print(f"平均処理時間: {self.total_metrics.average_time:.3f}秒")
        print(f"平均コンセンサス率: {self.total_metrics.consensus_rate:.1%}")
        print(f"最終ML精度: {self.total_metrics.ml_accuracy:.1%}")
        print(f"総キャッシュヒット: {self.total_metrics.cache_hits}")

        if self.error_patterns:
            print("\nエラーパターン分析:")
            for error_type, count in sorted(
                self.error_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]:
                print(f"  {error_type}: {count}件")

    async def shutdown(self):
        """シャットダウン"""
        logger.info("\n⚙️ システムシャットダウン中...")

        if self.quality_system:
            await self.quality_system.shutdown()

        if self.autonomous_system:
            # モデル保存
            self.autonomous_system.save_model('production_model.pkl')

        logger.info("✅ シャットダウン完了")

async def main():
    """メイン処理"""
    processor = ProductionEpisodeProcessor()

    try:
        await processor.initialize()

        # テストデータまたは実データで実行
        test_file = 'episodes_quality_integrated_20250923_083411.csv'

        if os.path.exists(test_file):
            result_df = await processor.process_production_data(
                test_file,
                output_file='production_results.csv'
            )
            print(f"\n✅ 処理完了: {len(result_df)}件")
        else:
            # デモデータ生成
            demo_episodes = [
                {
                    'person_name': f'Person_{i}',
                    'episode_age': 20 + i % 40,
                    'episode_text': f'これはテストエピソード{i}です。' * 10,
                    'person_id': f'P{i:03d}'
                }
                for i in range(200)  # 200件のデモデータ
            ]

            result = await processor.process_batch(
                demo_episodes,
                batch_id='demo_batch_001'
            )
            print(f"\n✅ デモ処理完了: {result.successful}/{result.total_episodes}件")

    except KeyboardInterrupt:
        logger.info("\n⚠️ 処理中断")
    except Exception as e:
        logger.error(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await processor.shutdown()

if __name__ == "__main__":
    import hashlib  # Add missing import
    asyncio.run(main())