#!/usr/bin/env python3
"""
APIレート制限管理システム
複数のAPIのレート制限を統合的に管理し、最適な待機時間を計算
"""

import os
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import aiofiles
from collections import deque

logger = logging.getLogger(__name__)


class APIProvider(Enum):
    """API提供者の定義"""
    GOOGLE = "google"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    NEWS = "news"
    BRAVE = "brave"


@dataclass
class RateLimitConfig:
    """各APIのレート制限設定"""
    provider: APIProvider
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    retry_after_seconds: int = 60  # デフォルト待機時間
    max_retries: int = 3
    backoff_multiplier: float = 2.0  # 指数バックオフの倍率


@dataclass
class APICallRecord:
    """API呼び出し記録"""
    provider: APIProvider
    timestamp: float
    success: bool
    status_code: Optional[int] = None
    retry_after: Optional[int] = None  # サーバーから返されたRetry-After


class RateLimitManager:
    """レート制限管理クラス"""
    
    def __init__(self, cache_dir: str = ".rate_limit_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 各APIのレート制限設定
        self.limits = {
            APIProvider.GOOGLE: RateLimitConfig(
                provider=APIProvider.GOOGLE,
                requests_per_minute=60,
                requests_per_hour=1000,
                requests_per_day=10000,
                retry_after_seconds=10
            ),
            APIProvider.YOUTUBE: RateLimitConfig(
                provider=APIProvider.YOUTUBE,
                requests_per_minute=100,
                requests_per_hour=3000,
                requests_per_day=10000,  # クォータベース
                retry_after_seconds=3600  # クォータ超過時は1時間待機
            ),
            APIProvider.TWITTER: RateLimitConfig(
                provider=APIProvider.TWITTER,
                requests_per_minute=15,  # v2 APIの制限
                requests_per_hour=300,
                requests_per_day=1000,
                retry_after_seconds=900  # 15分ウィンドウ
            ),
            APIProvider.NEWS: RateLimitConfig(
                provider=APIProvider.NEWS,
                requests_per_minute=30,
                requests_per_hour=500,
                requests_per_day=1000,
                retry_after_seconds=60
            ),
            APIProvider.BRAVE: RateLimitConfig(
                provider=APIProvider.BRAVE,
                requests_per_minute=60,
                requests_per_hour=1000,
                requests_per_day=5000,
                retry_after_seconds=60
            )
        }
        
        # 各APIの呼び出し履歴（メモリ内キャッシュ）
        self.call_history: Dict[APIProvider, deque] = {
            provider: deque(maxlen=10000)
            for provider in APIProvider
        }
        
        # 現在の待機状態
        self.wait_until: Dict[APIProvider, float] = {
            provider: 0.0 for provider in APIProvider
        }
        
        # 連続失敗カウンター
        self.consecutive_failures: Dict[APIProvider, int] = {
            provider: 0 for provider in APIProvider
        }
        
        # 統計情報
        self.stats = {
            "total_calls": 0,
            "total_waits": 0,
            "total_wait_time": 0.0
        }
        
        # 履歴をファイルから復元
        self._load_history()
    
    def _load_history(self):
        """履歴をファイルから読み込み"""
        history_file = self.cache_dir / "rate_limit_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    # 最近1時間のデータのみ復元
                    cutoff_time = time.time() - 3600
                    for provider_str, records in data.get("history", {}).items():
                        provider = APIProvider(provider_str)
                        for record in records:
                            if record["timestamp"] > cutoff_time:
                                self.call_history[provider].append(
                                    APICallRecord(
                                        provider=provider,
                                        timestamp=record["timestamp"],
                                        success=record["success"],
                                        status_code=record.get("status_code"),
                                        retry_after=record.get("retry_after")
                                    )
                                )
                    self.stats = data.get("stats", self.stats)
                    logger.info(f"履歴を復元: {sum(len(h) for h in self.call_history.values())}件")
            except Exception as e:
                logger.warning(f"履歴復元エラー: {e}")
    
    async def save_history(self):
        """履歴をファイルに保存"""
        history_file = self.cache_dir / "rate_limit_history.json"
        data = {
            "history": {
                provider.value: [
                    {
                        "timestamp": record.timestamp,
                        "success": record.success,
                        "status_code": record.status_code,
                        "retry_after": record.retry_after
                    }
                    for record in list(self.call_history[provider])[-1000:]  # 最新1000件
                ]
                for provider in APIProvider
            },
            "stats": self.stats,
            "saved_at": datetime.now().isoformat()
        }
        
        async with aiofiles.open(history_file, 'w') as f:
            await f.write(json.dumps(data, indent=2))
    
    def record_call(self, provider: APIProvider, success: bool, 
                    status_code: Optional[int] = None, 
                    retry_after: Optional[int] = None):
        """API呼び出しを記録"""
        record = APICallRecord(
            provider=provider,
            timestamp=time.time(),
            success=success,
            status_code=status_code,
            retry_after=retry_after
        )
        
        self.call_history[provider].append(record)
        self.stats["total_calls"] += 1
        
        if success:
            self.consecutive_failures[provider] = 0
        else:
            self.consecutive_failures[provider] += 1
            
            # サーバーからRetry-Afterが返された場合
            if retry_after:
                self.wait_until[provider] = time.time() + retry_after
            # 429エラーの場合、デフォルト待機時間を設定
            elif status_code == 429:
                wait_time = self.calculate_backoff_time(provider)
                self.wait_until[provider] = time.time() + wait_time
    
    def calculate_backoff_time(self, provider: APIProvider) -> float:
        """指数バックオフ時間を計算"""
        config = self.limits[provider]
        failures = self.consecutive_failures[provider]
        
        # 指数バックオフ（最大10分）
        base_wait = config.retry_after_seconds
        wait_time = min(
            base_wait * (config.backoff_multiplier ** failures),
            600  # 最大10分
        )
        
        # ジッター追加（±10%）
        import random
        jitter = wait_time * 0.1 * (2 * random.random() - 1)
        
        return wait_time + jitter
    
    def get_rate_limit_status(self, provider: APIProvider) -> Dict:
        """現在のレート制限状態を取得"""
        config = self.limits[provider]
        now = time.time()
        
        # 時間窓ごとの使用状況を計算
        last_minute = [r for r in self.call_history[provider] 
                      if r.timestamp > now - 60]
        last_hour = [r for r in self.call_history[provider] 
                    if r.timestamp > now - 3600]
        last_day = [r for r in self.call_history[provider] 
                   if r.timestamp > now - 86400]
        
        return {
            "provider": provider.value,
            "usage": {
                "per_minute": {
                    "used": len(last_minute),
                    "limit": config.requests_per_minute,
                    "remaining": max(0, config.requests_per_minute - len(last_minute))
                },
                "per_hour": {
                    "used": len(last_hour),
                    "limit": config.requests_per_hour,
                    "remaining": max(0, config.requests_per_hour - len(last_hour))
                },
                "per_day": {
                    "used": len(last_day),
                    "limit": config.requests_per_day,
                    "remaining": max(0, config.requests_per_day - len(last_day))
                }
            },
            "wait_until": self.wait_until[provider] if self.wait_until[provider] > now else None,
            "consecutive_failures": self.consecutive_failures[provider]
        }
    
    async def wait_if_needed(self, provider: APIProvider) -> float:
        """必要に応じて待機"""
        now = time.time()
        wait_time = 0.0
        
        # 強制待機時間がある場合
        if self.wait_until[provider] > now:
            wait_time = self.wait_until[provider] - now
            logger.info(f"⏳ {provider.value}: {wait_time:.1f}秒待機（レート制限）")
            await asyncio.sleep(wait_time)
            self.stats["total_waits"] += 1
            self.stats["total_wait_time"] += wait_time
            return wait_time
        
        # レート制限チェック
        status = self.get_rate_limit_status(provider)
        
        # 分単位の制限チェック
        if status["usage"]["per_minute"]["remaining"] <= 0:
            wait_time = 60 - (now % 60)  # 次の分まで待機
            logger.info(f"⏳ {provider.value}: {wait_time:.1f}秒待機（分制限）")
            await asyncio.sleep(wait_time)
            self.stats["total_waits"] += 1
            self.stats["total_wait_time"] += wait_time
            return wait_time
        
        # API間の最小間隔を確保（0.5秒）
        if self.call_history[provider]:
            last_call = self.call_history[provider][-1].timestamp
            min_interval = 0.5
            if now - last_call < min_interval:
                wait_time = min_interval - (now - last_call)
                await asyncio.sleep(wait_time)
                return wait_time
        
        return 0.0
    
    def get_optimal_batch_size(self, providers: List[APIProvider]) -> int:
        """最適なバッチサイズを計算"""
        # 各APIの残り容量から最小値を取得
        min_capacity = float('inf')
        
        for provider in providers:
            status = self.get_rate_limit_status(provider)
            min_capacity = min(
                min_capacity,
                status["usage"]["per_minute"]["remaining"]
            )
        
        # 安全マージンを考慮（80%）
        return max(1, int(min_capacity * 0.8))
    
    def predict_completion_time(self, total_requests: int, 
                               providers: List[APIProvider]) -> float:
        """完了予測時間を計算"""
        # 各APIの処理能力から推定
        max_time = 0.0
        
        for provider in providers:
            config = self.limits[provider]
            rate_per_second = config.requests_per_minute / 60
            
            # 現在の待機時間を考慮
            wait_time = max(0, self.wait_until[provider] - time.time())
            
            # 処理時間 = 待機時間 + (リクエスト数 / レート)
            process_time = wait_time + (total_requests / rate_per_second)
            max_time = max(max_time, process_time)
        
        return max_time
    
    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        total_success = sum(
            1 for provider in APIProvider
            for record in self.call_history[provider]
            if record.success
        )
        
        total_failures = sum(
            1 for provider in APIProvider
            for record in self.call_history[provider]
            if not record.success
        )
        
        return {
            "total_calls": self.stats["total_calls"],
            "total_success": total_success,
            "total_failures": total_failures,
            "success_rate": total_success / max(1, total_success + total_failures),
            "total_waits": self.stats["total_waits"],
            "total_wait_time": self.stats["total_wait_time"],
            "average_wait_time": self.stats["total_wait_time"] / max(1, self.stats["total_waits"]),
            "by_provider": {
                provider.value: {
                    "calls": len(self.call_history[provider]),
                    "failures": self.consecutive_failures[provider],
                    "status": self.get_rate_limit_status(provider)
                }
                for provider in APIProvider
            }
        }


class AdaptiveRateLimiter:
    """適応型レート制限管理"""
    
    def __init__(self, manager: RateLimitManager):
        self.manager = manager
        self.performance_history = deque(maxlen=100)  # 最近のパフォーマンス履歴
        
    async def execute_with_retry(self, provider: APIProvider, 
                                 func, *args, **kwargs):
        """リトライ機能付きで実行"""
        config = self.manager.limits[provider]
        
        for attempt in range(config.max_retries):
            # レート制限待機
            await self.manager.wait_if_needed(provider)
            
            try:
                # 関数実行
                start_time = time.time()
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 成功を記録
                self.manager.record_call(provider, True)
                self.performance_history.append({
                    "provider": provider.value,
                    "success": True,
                    "execution_time": execution_time,
                    "attempt": attempt + 1
                })
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                status_code = None
                retry_after = None
                
                # エラーからステータスコードを抽出
                if "429" in error_msg:
                    status_code = 429
                elif "403" in error_msg:
                    status_code = 403
                elif "401" in error_msg:
                    status_code = 401
                
                # Retry-Afterヘッダーの値を抽出（可能な場合）
                if "retry-after" in error_msg.lower():
                    import re
                    match = re.search(r'retry-after[:\s]+(\d+)', error_msg, re.IGNORECASE)
                    if match:
                        retry_after = int(match.group(1))
                
                # 失敗を記録
                self.manager.record_call(provider, False, status_code, retry_after)
                
                # 最後の試行でなければ待機してリトライ
                if attempt < config.max_retries - 1:
                    wait_time = self.manager.calculate_backoff_time(provider)
                    logger.warning(
                        f"🔄 {provider.value}: リトライ {attempt + 1}/{config.max_retries} "
                        f"({wait_time:.1f}秒後)"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # 最後の試行後はエラーを再発生
                    logger.error(f"❌ {provider.value}: 全リトライ失敗")
                    raise
        
        raise RuntimeError(f"{provider.value}: 全リトライ失敗")
    
    def get_performance_report(self) -> Dict:
        """パフォーマンスレポートを生成"""
        if not self.performance_history:
            return {"message": "データなし"}
        
        by_provider = {}
        for record in self.performance_history:
            provider = record["provider"]
            if provider not in by_provider:
                by_provider[provider] = {
                    "total": 0,
                    "success": 0,
                    "total_time": 0,
                    "avg_attempts": []
                }
            
            by_provider[provider]["total"] += 1
            if record["success"]:
                by_provider[provider]["success"] += 1
            by_provider[provider]["total_time"] += record["execution_time"]
            by_provider[provider]["avg_attempts"].append(record["attempt"])
        
        # 統計を計算
        for provider, stats in by_provider.items():
            stats["success_rate"] = stats["success"] / max(1, stats["total"])
            stats["avg_time"] = stats["total_time"] / max(1, stats["total"])
            stats["avg_attempts"] = sum(stats["avg_attempts"]) / max(1, len(stats["avg_attempts"]))
        
        return {
            "summary": {
                "total_requests": len(self.performance_history),
                "providers": list(by_provider.keys())
            },
            "by_provider": by_provider,
            "recommendations": self._generate_recommendations(by_provider)
        }
    
    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """パフォーマンスに基づく推奨事項を生成"""
        recommendations = []
        
        for provider, data in stats.items():
            if data["success_rate"] < 0.5:
                recommendations.append(
                    f"⚠️ {provider}の成功率が低い({data['success_rate']:.1%})。"
                    f"レート制限を緩和するか、代替APIを検討してください。"
                )
            
            if data["avg_attempts"] > 2:
                recommendations.append(
                    f"⚠️ {provider}の平均リトライ回数が多い({data['avg_attempts']:.1f}回)。"
                    f"初回待機時間を増やすことを検討してください。"
                )
            
            if data["avg_time"] > 5:
                recommendations.append(
                    f"⏱️ {provider}の平均応答時間が長い({data['avg_time']:.1f}秒)。"
                    f"タイムアウト設定の見直しを検討してください。"
                )
        
        if not recommendations:
            recommendations.append("✅ 全APIが良好なパフォーマンスを示しています。")
        
        return recommendations


# 使用例
async def example_usage():
    """使用例"""
    manager = RateLimitManager()
    limiter = AdaptiveRateLimiter(manager)
    
    # レート制限状態を確認
    for provider in APIProvider:
        status = manager.get_rate_limit_status(provider)
        logger.info(f"{provider.value}: {status}")
    
    # API呼び出しをリトライ機能付きで実行
    async def mock_api_call():
        # 実際のAPI呼び出しをここに実装
        return {"result": "success"}
    
    try:
        result = await limiter.execute_with_retry(
            APIProvider.GOOGLE,
            mock_api_call
        )
        logger.info(f"結果: {result}")
    except Exception as e:
        logger.error(f"エラー: {e}")
    
    # 統計情報を表示
    stats = manager.get_statistics()
    logger.info(f"統計: {json.dumps(stats, indent=2)}")
    
    # パフォーマンスレポート
    report = limiter.get_performance_report()
    logger.info(f"レポート: {json.dumps(report, indent=2)}")
    
    # 履歴を保存
    await manager.save_history()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())