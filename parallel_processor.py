#!/usr/bin/env python3
"""
5ワーカー並列処理システム
API別にワーカーを分離して高速処理を実現
"""

import asyncio
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
import time
from queue import Queue
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """ワーカー設定"""
    worker_id: str
    api_name: str
    rate_limit: int  # requests per minute
    batch_size: int
    retry_count: int = 3
    timeout: int = 30


@dataclass
class ProcessingResult:
    """処理結果"""
    person_id: str
    api_name: str
    result: Any
    success: bool
    processing_time: float
    wait_time: float = 0.0


class ParallelProcessor:
    """並列処理マネージャー"""
    
    def __init__(self, num_workers: int = 5):
        self.num_workers = num_workers
        self.workers_config = self._initialize_workers()
        self.results_queue = mp.Queue()
        self.tasks_queue = mp.Queue()
        self.progress = mp.Value('i', 0)
        self.total_records = mp.Value('i', 0)
        
    def _initialize_workers(self) -> List[WorkerConfig]:
        """ワーカー初期化"""
        return [
            WorkerConfig(
                worker_id="worker_1",
                api_name="Google",
                rate_limit=100,  # SerpAPI制限
                batch_size=20
            ),
            WorkerConfig(
                worker_id="worker_2",
                api_name="Brave",
                rate_limit=100,  # Brave Search制限
                batch_size=20
            ),
            WorkerConfig(
                worker_id="worker_3",
                api_name="YouTube",
                rate_limit=10,  # 厳しい制限
                batch_size=5
            ),
            WorkerConfig(
                worker_id="worker_4",
                api_name="Twitter",
                rate_limit=15,  # 15/15min
                batch_size=3
            ),
            WorkerConfig(
                worker_id="worker_5",
                api_name="News",
                rate_limit=20,
                batch_size=10
            )
        ]
    
    async def process_batch_async(
        self, 
        df: pd.DataFrame,
        tiered_strategy: bool = True,
        cache_enabled: bool = True
    ) -> pd.DataFrame:
        """非同期バッチ処理"""
        
        logger.info(f"🚀 並列処理開始: {len(df)}件")
        self.total_records.value = len(df)
        
        # タスク分配
        if tiered_strategy:
            task_distribution = self._distribute_tasks_tiered(df)
        else:
            task_distribution = self._distribute_tasks_uniform(df)
        
        # 並列実行
        start_time = time.time()
        
        # 非同期タスク作成
        tasks = []
        for worker_config in self.workers_config:
            worker_tasks = task_distribution.get(worker_config.api_name, [])
            if worker_tasks:
                task = asyncio.create_task(
                    self._worker_process_async(worker_config, worker_tasks, cache_enabled)
                )
                tasks.append(task)
        
        # すべてのワーカーの完了を待つ
        results = await asyncio.gather(*tasks)
        
        # 結果統合
        all_results = []
        for worker_results in results:
            all_results.extend(worker_results)
        
        elapsed = time.time() - start_time
        logger.info(f"✅ 並列処理完了: {elapsed:.1f}秒")
        
        # 結果をDataFrameに統合
        return self._merge_results(df, all_results)
    
    def _distribute_tasks_tiered(self, df: pd.DataFrame) -> Dict[str, List]:
        """階層的タスク分配"""
        distribution = {api: [] for api in ["Google", "Brave", "YouTube", "Twitter", "News"]}
        
        for idx, row in df.iterrows():
            # カテゴリとメタデータから優先度判定
            category = row.get('category', '')
            
            # Tier 1: 高速API（Google, Brave）で全件
            distribution["Google"].append(row)
            distribution["Brave"].append(row)
            
            # Tier 2: 中優先度（YouTube）
            if category in ['YouTuber', '歌手', '俳優', 'アイドル']:
                distribution["YouTube"].append(row)
            
            # Tier 3: 低優先度（Twitter, News）
            if category in ['政治家', 'ジャーナリスト', '実業家']:
                distribution["Twitter"].append(row)
                distribution["News"].append(row)
        
        # ログ出力
        for api, tasks in distribution.items():
            logger.info(f"  {api}: {len(tasks)}件")
        
        return distribution
    
    def _distribute_tasks_uniform(self, df: pd.DataFrame) -> Dict[str, List]:
        """均等タスク分配"""
        distribution = {api: [] for api in ["Google", "Brave", "YouTube", "Twitter", "News"]}
        
        # すべてのAPIに均等分配
        for idx, row in df.iterrows():
            for api in distribution.keys():
                distribution[api].append(row)
        
        return distribution
    
    async def _worker_process_async(
        self,
        config: WorkerConfig,
        tasks: List,
        cache_enabled: bool
    ) -> List[ProcessingResult]:
        """ワーカー非同期処理"""
        
        results = []
        logger.info(f"🔧 {config.worker_id} ({config.api_name}) 開始: {len(tasks)}件")
        
        # キャッシュチェック
        cache = self._load_cache(config.api_name) if cache_enabled else {}
        
        # レート制限管理
        last_request_time = 0
        request_count = 0
        minute_start = time.time()
        
        for task in tasks:
            person_id = task.get('person_id', '')
            person_name = task.get('person_name_ja', task.get('person_name', ''))
            
            # キャッシュチェック
            cache_key = f"{config.api_name}:{person_name}"
            if cache_key in cache:
                results.append(ProcessingResult(
                    person_id=person_id,
                    api_name=config.api_name,
                    result=cache[cache_key],
                    success=True,
                    processing_time=0.0
                ))
                continue
            
            # レート制限チェック
            current_time = time.time()
            if current_time - minute_start >= 60:
                # 1分経過でリセット
                request_count = 0
                minute_start = current_time
            
            if request_count >= config.rate_limit:
                # レート制限に達した場合は待機
                wait_time = 60 - (current_time - minute_start)
                if wait_time > 0:
                    logger.info(f"⏳ {config.worker_id} レート制限待機: {wait_time:.1f}秒")
                    await asyncio.sleep(wait_time)
                    request_count = 0
                    minute_start = time.time()
            
            # API呼び出しシミュレーション
            start_time = time.time()
            
            try:
                # 実際のAPI呼び出しの代わりにシミュレーション
                result = await self._simulate_api_call(config.api_name, person_name)
                
                # キャッシュ保存
                if cache_enabled:
                    cache[cache_key] = result
                
                results.append(ProcessingResult(
                    person_id=person_id,
                    api_name=config.api_name,
                    result=result,
                    success=True,
                    processing_time=time.time() - start_time
                ))
                
                request_count += 1
                self.progress.value += 1
                
                # 進捗表示（10%ごと）
                if self.progress.value % max(1, self.total_records.value // 10) == 0:
                    progress_pct = (self.progress.value / self.total_records.value) * 100
                    logger.info(f"📊 進捗: {progress_pct:.1f}% ({self.progress.value}/{self.total_records.value})")
                
            except Exception as e:
                logger.error(f"❌ {config.worker_id} エラー: {e}")
                results.append(ProcessingResult(
                    person_id=person_id,
                    api_name=config.api_name,
                    result=None,
                    success=False,
                    processing_time=time.time() - start_time
                ))
        
        # キャッシュ保存
        if cache_enabled:
            self._save_cache(config.api_name, cache)
        
        logger.info(f"✅ {config.worker_id} 完了: {len(results)}件処理")
        return results
    
    async def _simulate_api_call(self, api_name: str, query: str) -> Dict:
        """API呼び出しシミュレーション"""
        # 実際のAPIの代わりにシミュレーション
        await asyncio.sleep(np.random.uniform(0.1, 0.5))
        
        if api_name == "Google":
            return {"results": np.random.randint(10000, 100000000)}
        elif api_name == "Brave":
            return {"results": np.random.randint(100, 10000)}
        elif api_name == "YouTube":
            return {"views": np.random.randint(1000, 50000000)}
        elif api_name == "Twitter":
            return {"mentions": np.random.randint(10, 100000)}
        elif api_name == "News":
            return {"articles": np.random.randint(0, 1000)}
        else:
            return {}
    
    def _merge_results(self, df: pd.DataFrame, results: List[ProcessingResult]) -> pd.DataFrame:
        """結果統合"""
        # 結果をDataFrameに変換
        results_dict = {}
        
        for result in results:
            if result.person_id not in results_dict:
                results_dict[result.person_id] = {}
            
            results_dict[result.person_id][f"{result.api_name}_result"] = result.result
            results_dict[result.person_id][f"{result.api_name}_success"] = result.success
        
        # 元のDataFrameに結果を追加
        for person_id, api_results in results_dict.items():
            for col, value in api_results.items():
                df.loc[df['person_id'] == person_id, col] = str(value)
        
        return df
    
    def _load_cache(self, api_name: str) -> Dict:
        """キャッシュ読み込み"""
        cache_file = Path(f"cache_{api_name.lower()}.json")
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self, api_name: str, cache: Dict):
        """キャッシュ保存"""
        cache_file = Path(f"cache_{api_name.lower()}.json")
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache, f)
        except Exception as e:
            logger.warning(f"キャッシュ保存失敗: {e}")
    
    def get_performance_stats(self, results: List[ProcessingResult]) -> Dict:
        """パフォーマンス統計"""
        if not results:
            return {}
        
        stats = {
            'total_processed': len(results),
            'success_count': sum(1 for r in results if r.success),
            'failure_count': sum(1 for r in results if not r.success),
            'avg_processing_time': np.mean([r.processing_time for r in results]),
            'total_wait_time': sum(r.wait_time for r in results),
        }
        
        # API別統計
        api_stats = {}
        for api in ["Google", "Brave", "YouTube", "Twitter", "News"]:
            api_results = [r for r in results if r.api_name == api]
            if api_results:
                api_stats[api] = {
                    'count': len(api_results),
                    'success_rate': sum(1 for r in api_results if r.success) / len(api_results),
                    'avg_time': np.mean([r.processing_time for r in api_results])
                }
        
        stats['api_stats'] = api_stats
        return stats


async def demo_parallel_processing():
    """デモ実行"""
    # テストデータ
    test_data = pd.DataFrame([
        {"person_id": f"P{i:03d}", "person_name": f"Person_{i}", 
         "person_name_ja": f"人物{i}", "category": ["YouTuber", "歌手", "俳優"][i % 3]}
        for i in range(20)
    ])
    
    # プロセッサー初期化
    processor = ParallelProcessor(num_workers=5)
    
    print("🚀 並列処理デモ開始")
    print(f"  データ件数: {len(test_data)}")
    print(f"  ワーカー数: 5")
    print(f"  階層評価: 有効")
    print(f"  キャッシュ: 有効")
    print("=" * 60)
    
    # 実行
    start_time = time.time()
    result_df = await processor.process_batch_async(
        test_data,
        tiered_strategy=True,
        cache_enabled=True
    )
    elapsed = time.time() - start_time
    
    print(f"\n✅ 処理完了")
    print(f"  処理時間: {elapsed:.1f}秒")
    print(f"  処理速度: {len(test_data) / elapsed:.1f} rec/sec")
    
    # 結果サンプル表示
    print("\n📊 結果サンプル:")
    print(result_df.head(3).to_string())
    
    return result_df


if __name__ == "__main__":
    asyncio.run(demo_parallel_processing())