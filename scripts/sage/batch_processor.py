"""
Anthropic Batch API Processor

50%コスト削減のための非同期バッチ処理。
24時間以内に結果が返る（通常は数時間）。

使い方:
1. バッチリクエストを作成・送信
2. batch_idを保存
3. 後で結果をポーリング・取得
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None  # type: ignore

from .config import LOGS_DIR, HybridConfig


@dataclass
class BatchRequest:
    """バッチリクエストの1件"""

    custom_id: str
    person_name: str
    age: int
    category: str
    prompt: str
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024


@dataclass
class BatchJob:
    """バッチジョブの状態"""

    batch_id: str
    created_at: str
    status: str  # "in_progress", "ended", "canceling", "canceled", "expired"
    request_count: int
    succeeded_count: int = 0
    failed_count: int = 0
    expired_count: int = 0
    canceled_count: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "created_at": self.created_at,
            "status": self.status,
            "request_count": self.request_count,
            "succeeded_count": self.succeeded_count,
            "failed_count": self.failed_count,
            "expired_count": self.expired_count,
            "canceled_count": self.canceled_count,
            "results_count": len(self.results),
        }


class BatchProcessor:
    """
    Anthropic Batch API プロセッサ

    非同期バッチ処理で50%コスト削減を実現。
    """

    def __init__(self, config: HybridConfig = None):
        self.config = config or HybridConfig()
        self._client: Optional[AsyncAnthropic] = None
        self._jobs_dir = LOGS_DIR / "batch_jobs"
        self._jobs_dir.mkdir(parents=True, exist_ok=True)

    @property
    def client(self) -> AsyncAnthropic:
        if self._client is None:
            if AsyncAnthropic is None:
                raise ImportError("anthropic package required. Run: pip install anthropic")
            self._client = AsyncAnthropic()
        return self._client

    async def submit_batch(
        self,
        requests: list[BatchRequest],
    ) -> BatchJob:
        """
        バッチリクエストを送信

        Args:
            requests: バッチリクエストのリスト

        Returns:
            BatchJob: 送信されたバッチジョブ
        """
        if not requests:
            raise ValueError("No requests provided")

        # Anthropic形式に変換
        api_requests = []
        for req in requests:
            api_requests.append(
                {
                    "custom_id": req.custom_id,
                    "params": {
                        "model": req.model,
                        "max_tokens": req.max_tokens,
                        "messages": [{"role": "user", "content": req.prompt}],
                    },
                }
            )

        # バッチ送信
        batch = await self.client.messages.batches.create(requests=api_requests)

        job = BatchJob(
            batch_id=batch.id,
            created_at=datetime.now().isoformat(),
            status=batch.processing_status,
            request_count=len(requests),
        )

        # ジョブ情報を保存
        self._save_job(job, requests)

        return job

    async def check_status(self, batch_id: str) -> BatchJob:
        """
        バッチステータスを確認

        Args:
            batch_id: バッチID

        Returns:
            BatchJob: 更新されたバッチジョブ
        """
        batch = await self.client.messages.batches.retrieve(batch_id)

        # ジョブ情報を読み込み
        job_path = self._jobs_dir / f"{batch_id}.json"
        if job_path.exists():
            with open(job_path, encoding="utf-8") as f:
                job_data = json.load(f)
            job = BatchJob(
                batch_id=batch_id,
                created_at=job_data.get("created_at", ""),
                status=batch.processing_status,
                request_count=job_data.get("request_count", 0),
            )
        else:
            job = BatchJob(
                batch_id=batch_id,
                created_at="",
                status=batch.processing_status,
                request_count=batch.request_counts.total if batch.request_counts else 0,
            )

        # カウント更新
        if batch.request_counts:
            job.succeeded_count = batch.request_counts.succeeded
            job.failed_count = batch.request_counts.errored
            job.expired_count = batch.request_counts.expired
            job.canceled_count = batch.request_counts.canceled

        return job

    async def get_results(self, batch_id: str) -> list[dict[str, Any]]:
        """
        バッチ結果を取得

        Args:
            batch_id: バッチID

        Returns:
            list: 結果のリスト
        """
        results = []
        result_stream = await self.client.messages.batches.results(batch_id)

        async for entry in result_stream:
            result_entry = {
                "custom_id": entry.custom_id,
                "result_type": entry.result.type,
            }

            if entry.result.type == "succeeded":
                # 成功した結果からテキストを抽出
                message = entry.result.message
                text_content = ""
                for block in message.content:
                    if hasattr(block, "text"):
                        text_content += block.text

                result_entry["text"] = text_content
                result_entry["usage"] = {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                }
            elif entry.result.type == "errored":
                result_entry["error"] = str(entry.result.error)
            elif entry.result.type == "expired":
                result_entry["error"] = "Request expired"
            elif entry.result.type == "canceled":
                result_entry["error"] = "Request canceled"

            results.append(result_entry)

        # 結果を保存
        self._save_results(batch_id, results)

        return results

    async def wait_for_completion(
        self,
        batch_id: str,
        poll_interval: int = 60,
        timeout: int = 86400,  # 24時間
    ) -> BatchJob:
        """
        バッチ完了を待機

        Args:
            batch_id: バッチID
            poll_interval: ポーリング間隔（秒）
            timeout: タイムアウト（秒）

        Returns:
            BatchJob: 完了したバッチジョブ
        """
        start_time = time.time()

        while True:
            job = await self.check_status(batch_id)

            if job.status == "ended":
                # 結果を取得
                job.results = await self.get_results(batch_id)
                return job

            if job.status in ("canceled", "expired"):
                return job

            # タイムアウトチェック
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Batch {batch_id} timed out after {timeout}s")

            # 待機
            await asyncio.sleep(poll_interval)

    async def cancel_batch(self, batch_id: str) -> BatchJob:
        """
        バッチをキャンセル

        Args:
            batch_id: バッチID

        Returns:
            BatchJob: キャンセルされたバッチジョブ
        """
        await self.client.messages.batches.cancel(batch_id)
        return await self.check_status(batch_id)

    def list_pending_jobs(self) -> list[dict[str, Any]]:
        """
        保留中のジョブをリスト

        Returns:
            list: ジョブ情報のリスト
        """
        jobs = []
        for job_file in self._jobs_dir.glob("*.json"):
            with open(job_file, encoding="utf-8") as f:
                job_data = json.load(f)
            if job_data.get("status") == "in_progress":
                jobs.append(job_data)
        return jobs

    def _save_job(self, job: BatchJob, requests: list[BatchRequest]) -> None:
        """ジョブ情報を保存"""
        job_path = self._jobs_dir / f"{job.batch_id}.json"
        job_data = job.to_dict()
        job_data["requests"] = [
            {
                "custom_id": r.custom_id,
                "person_name": r.person_name,
                "age": r.age,
                "category": r.category,
            }
            for r in requests
        ]
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job_data, f, ensure_ascii=False, indent=2)

    def _save_results(self, batch_id: str, results: list[dict[str, Any]]) -> None:
        """結果を保存"""
        results_path = self._jobs_dir / f"{batch_id}_results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)


def create_batch_request(
    person_name: str,
    age: int,
    category: str,
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
) -> BatchRequest:
    """
    バッチリクエストを作成

    Args:
        person_name: 人物名
        age: 年齢
        category: カテゴリ
        prompt: プロンプト
        model: 使用モデル

    Returns:
        BatchRequest: バッチリクエスト
    """
    # custom_idは英数字のみ許可（^[a-zA-Z0-9_-]{1,64}$）
    import hashlib

    name_hash = hashlib.md5(person_name.encode()).hexdigest()[:8]
    custom_id = f"ep_{name_hash}_{age}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return BatchRequest(
        custom_id=custom_id,
        person_name=person_name,
        age=age,
        category=category,
        prompt=prompt,
        model=model,
    )


async def demo_batch_processing():
    """デモ: バッチ処理の例"""
    processor = BatchProcessor()

    # サンプルリクエスト
    requests = [
        create_batch_request(
            person_name="テスト太郎",
            age=30,
            category="テスト",
            prompt="Hello, this is a test request.",
        ),
        create_batch_request(
            person_name="テスト花子",
            age=25,
            category="テスト",
            prompt="Another test request.",
        ),
    ]

    # バッチ送信
    job = await processor.submit_batch(requests)
    print(f"Batch submitted: {job.batch_id}")

    # 完了を待機（デモ用に短い間隔）
    job = await processor.wait_for_completion(job.batch_id, poll_interval=10)
    print(f"Batch completed: {job.succeeded_count}/{job.request_count} succeeded")

    # 結果を表示
    for result in job.results:
        print(f"  {result['custom_id']}: {result.get('text', result.get('error', 'unknown'))[:50]}...")


if __name__ == "__main__":
    asyncio.run(demo_batch_processing())
