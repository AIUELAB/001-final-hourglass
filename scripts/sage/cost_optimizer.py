"""
Cost Optimizer - SAGE コスト最適化

Anthropic Batch API対応、プロンプトキャッシュ活用。
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from .config import CACHE_DIR


# ==============================================================================
# プロンプトキャッシュ
# ==============================================================================


@dataclass
class CacheEntry:
    """キャッシュエントリ"""

    key: str
    value: str
    created_at: str
    ttl_hours: int = 24
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        """期限切れチェック"""
        created = datetime.fromisoformat(self.created_at)
        return datetime.now() > created + timedelta(hours=self.ttl_hours)


class PromptCache:
    """
    プロンプトキャッシュ

    同一プロンプトの再利用でトークン節約。
    Anthropicのprompt_caching機能を活用。
    """

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir / "prompt_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.cache_dir / "index.json"
        self._index: dict[str, CacheEntry] = {}
        self._load_index()

    def _load_index(self) -> None:
        """インデックス読み込み"""
        if self._index_file.exists():
            try:
                with open(self._index_file, encoding="utf-8") as f:
                    data = json.load(f)
                for key, entry in data.items():
                    self._index[key] = CacheEntry(**entry)
            except (json.JSONDecodeError, KeyError):
                self._index = {}

    def _save_index(self) -> None:
        """インデックス保存"""
        data = {k: v.__dict__ for k, v in self._index.items()}
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _hash_prompt(self, prompt: str) -> str:
        """プロンプトのハッシュ生成"""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def get(self, prompt: str) -> Optional[str]:
        """
        キャッシュから取得

        Args:
            prompt: プロンプト

        Returns:
            キャッシュされた応答、またはNone
        """
        key = self._hash_prompt(prompt)
        entry = self._index.get(key)

        if entry is None:
            return None

        if entry.is_expired:
            del self._index[key]
            self._save_index()
            return None

        # ヒットカウント更新
        entry.hit_count += 1
        self._save_index()

        return entry.value

    def set(self, prompt: str, response: str, ttl_hours: int = 24) -> None:
        """
        キャッシュに保存

        Args:
            prompt: プロンプト
            response: 応答
            ttl_hours: TTL（時間）
        """
        key = self._hash_prompt(prompt)
        self._index[key] = CacheEntry(
            key=key,
            value=response,
            created_at=datetime.now().isoformat(),
            ttl_hours=ttl_hours,
            hit_count=0,
        )
        self._save_index()

    def get_stats(self) -> dict[str, Any]:
        """統計情報を取得"""
        total = len(self._index)
        expired = sum(1 for e in self._index.values() if e.is_expired)
        total_hits = sum(e.hit_count for e in self._index.values())

        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "total_hits": total_hits,
        }

    def cleanup(self) -> int:
        """期限切れエントリを削除"""
        expired_keys = [k for k, v in self._index.items() if v.is_expired]
        for key in expired_keys:
            del self._index[key]
        self._save_index()
        return len(expired_keys)


# ==============================================================================
# Batch API対応
# ==============================================================================


@dataclass
class BatchRequest:
    """バッチリクエスト"""

    custom_id: str
    prompt: str
    system: str = ""
    max_tokens: int = 4096


@dataclass
class BatchResult:
    """バッチ結果"""

    custom_id: str
    success: bool
    response: str = ""
    error: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class BatchProcessor:
    """
    Anthropic Batch API プロセッサ

    大量リクエストを50%割引で処理。
    24時間以内の結果返却。
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        """遅延初期化"""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed")
        return self._client

    def create_batch(
        self,
        requests: list[BatchRequest],
        model: str = "claude-sonnet-4-20250514",
    ) -> str:
        """
        バッチ作成

        Args:
            requests: リクエストリスト
            model: モデル名

        Returns:
            batch_id: バッチID
        """
        client = self._get_client()

        # Message Batches API形式に変換
        batch_requests = []
        for req in requests:
            batch_requests.append(
                {
                    "custom_id": req.custom_id,
                    "params": {
                        "model": model,
                        "max_tokens": req.max_tokens,
                        "system": req.system if req.system else "You are a helpful assistant.",
                        "messages": [{"role": "user", "content": req.prompt}],
                    },
                }
            )

        # バッチ作成
        batch = client.messages.batches.create(requests=batch_requests)
        return batch.id

    def get_batch_status(self, batch_id: str) -> dict[str, Any]:
        """
        バッチステータス取得

        Args:
            batch_id: バッチID

        Returns:
            ステータス情報
        """
        client = self._get_client()
        batch = client.messages.batches.retrieve(batch_id)

        return {
            "id": batch.id,
            "status": batch.processing_status,
            "created_at": batch.created_at,
            "ended_at": batch.ended_at,
            "request_counts": {
                "processing": batch.request_counts.processing,
                "succeeded": batch.request_counts.succeeded,
                "errored": batch.request_counts.errored,
                "canceled": batch.request_counts.canceled,
                "expired": batch.request_counts.expired,
            },
        }

    def get_batch_results(self, batch_id: str) -> list[BatchResult]:
        """
        バッチ結果取得

        Args:
            batch_id: バッチID

        Returns:
            結果リスト
        """
        client = self._get_client()
        results = []

        # 結果をストリーミング取得
        for result in client.messages.batches.results(batch_id):
            if result.result.type == "succeeded":
                message = result.result.message
                response_text = message.content[0].text if message.content else ""
                results.append(
                    BatchResult(
                        custom_id=result.custom_id,
                        success=True,
                        response=response_text,
                        input_tokens=message.usage.input_tokens,
                        output_tokens=message.usage.output_tokens,
                    )
                )
            else:
                error = result.result.error if hasattr(result.result, "error") else "Unknown error"
                results.append(
                    BatchResult(
                        custom_id=result.custom_id,
                        success=False,
                        error=str(error),
                    )
                )

        return results

    def estimate_cost(self, requests: list[BatchRequest], model: str = "claude-sonnet-4-20250514") -> dict[str, float]:
        """
        コスト推定

        Args:
            requests: リクエストリスト
            model: モデル名

        Returns:
            コスト情報
        """
        # 料金表（Batch APIは50%割引）
        pricing = {
            "claude-sonnet-4-20250514": {"input": 1.5, "output": 7.5},  # 通常の50%
            "claude-3-5-sonnet-20241022": {"input": 1.5, "output": 7.5},
            "claude-3-5-haiku-20241022": {"input": 0.125, "output": 0.625},
        }

        price = pricing.get(model, pricing["claude-sonnet-4-20250514"])

        # トークン数推定
        total_input_tokens = sum(len(r.prompt) // 4 + len(r.system) // 4 for r in requests)
        estimated_output_tokens = len(requests) * 500  # 平均500トークン/応答と仮定

        input_cost = (total_input_tokens / 1_000_000) * price["input"]
        output_cost = (estimated_output_tokens / 1_000_000) * price["output"]

        return {
            "estimated_input_tokens": total_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(input_cost + output_cost, 6),
            "savings_vs_sync": round((input_cost + output_cost), 6),  # 同期APIの50%
        }


# ==============================================================================
# コストオプティマイザー
# ==============================================================================


class CostOptimizer:
    """
    コストオプティマイザー

    機能:
    - プロンプトキャッシュ活用
    - Batch API自動切替
    - コスト追跡
    """

    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        batch_threshold: int = 10,
        use_cache: bool = True,
    ):
        self.prompt_cache = PromptCache(cache_dir) if use_cache else None
        self.batch_processor = BatchProcessor()
        self.batch_threshold = batch_threshold
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "sync_calls": 0,
            "batch_calls": 0,
            "total_tokens_saved": 0,
            "total_cost_saved": 0.0,
        }

    def should_use_batch(self, request_count: int) -> bool:
        """バッチAPIを使うべきか判定"""
        return request_count >= self.batch_threshold

    def get_cached_or_call(
        self,
        prompt: str,
        call_fn: callable,
        cache_key: Optional[str] = None,
    ) -> tuple[str, bool]:
        """
        キャッシュから取得、なければAPI呼び出し

        Args:
            prompt: プロンプト
            call_fn: API呼び出し関数
            cache_key: カスタムキャッシュキー

        Returns:
            tuple: (応答, キャッシュヒットか)
        """
        if self.prompt_cache is None:
            response = call_fn(prompt)
            self._stats["sync_calls"] += 1
            return response, False

        # キャッシュチェック
        cached = self.prompt_cache.get(cache_key or prompt)
        if cached is not None:
            self._stats["cache_hits"] += 1
            self._stats["total_tokens_saved"] += len(prompt) // 4
            return cached, True

        # API呼び出し
        response = call_fn(prompt)
        self._stats["cache_misses"] += 1
        self._stats["sync_calls"] += 1

        # キャッシュに保存
        self.prompt_cache.set(cache_key or prompt, response)

        return response, False

    def get_stats(self) -> dict[str, Any]:
        """統計情報を取得"""
        cache_stats = self.prompt_cache.get_stats() if self.prompt_cache else {}
        return {
            **self._stats,
            "cache_stats": cache_stats,
            "cache_hit_rate": (
                self._stats["cache_hits"] / (self._stats["cache_hits"] + self._stats["cache_misses"])
                if (self._stats["cache_hits"] + self._stats["cache_misses"]) > 0
                else 0.0
            ),
        }


# ==============================================================================
# 便利関数
# ==============================================================================


def estimate_batch_savings(request_count: int, avg_prompt_tokens: int = 500) -> dict[str, float]:
    """
    バッチAPI使用時の節約額を推定

    Args:
        request_count: リクエスト数
        avg_prompt_tokens: 平均プロンプトトークン数

    Returns:
        節約情報
    """
    # 同期API料金
    sync_input_cost = (request_count * avg_prompt_tokens / 1_000_000) * 3.0
    sync_output_cost = (request_count * 500 / 1_000_000) * 15.0
    sync_total = sync_input_cost + sync_output_cost

    # Batch API料金（50%割引）
    batch_total = sync_total * 0.5

    return {
        "sync_cost_usd": round(sync_total, 4),
        "batch_cost_usd": round(batch_total, 4),
        "savings_usd": round(sync_total - batch_total, 4),
        "savings_percent": 50.0,
    }


if __name__ == "__main__":
    # テスト
    print("=== Cost Optimizer Test ===")

    # キャッシュテスト
    cache = PromptCache()
    cache.set("test_prompt", "test_response")
    cached = cache.get("test_prompt")
    print(f"Cache test: {'PASS' if cached == 'test_response' else 'FAIL'}")

    # 統計
    print(f"Cache stats: {cache.get_stats()}")

    # バッチ節約推定
    savings = estimate_batch_savings(100)
    print(f"Batch savings for 100 requests: ${savings['savings_usd']:.4f} ({savings['savings_percent']}%)")
