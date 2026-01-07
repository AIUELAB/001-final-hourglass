#!/usr/bin/env python3
"""
Batch API ジョブ監視スクリプト

保留中のBatch APIジョブのステータスを監視し、完了したジョブの結果を取得します。
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.batch_processor import BatchProcessor
from scripts.sage.config import HybridConfig, CACHE_DIR


def format_duration(seconds: float) -> str:
    """秒を読みやすい形式に変換"""
    if seconds < 60:
        return f"{seconds:.0f}秒"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}分"
    else:
        return f"{seconds / 3600:.1f}時間"


async def check_all_jobs():
    """全てのジョブのステータスをチェック"""
    config = HybridConfig()
    processor = BatchProcessor(config)

    # 保留中のジョブを取得
    pending_jobs = processor.list_pending_jobs()

    print("\n" + "=" * 70)
    print("Batch API ジョブ監視")
    print("=" * 70)
    print(f"確認時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"保留中ジョブ数: {len(pending_jobs)}")
    print()

    if not pending_jobs:
        print("保留中のジョブはありません。")
        return

    # 各ジョブのステータスをチェック
    completed_jobs = []
    in_progress_jobs = []
    failed_jobs = []

    for job_info in pending_jobs:
        batch_id = job_info["batch_id"]
        try:
            job = await processor.check_status(batch_id)

            status_info = {
                "batch_id": batch_id,
                "status": job.status,
                "request_count": job.request_count,
                "succeeded_count": job.succeeded_count,
                "failed_count": job.failed_count,
                "created_at": job_info.get("created_at", "不明"),
            }

            if job.status == "ended":
                completed_jobs.append(status_info)
            elif job.status in ["failed", "canceled", "expired"]:
                failed_jobs.append(status_info)
            else:
                in_progress_jobs.append(status_info)

        except Exception as e:
            print(f"エラー: {batch_id} - {e}")

    # 進行中のジョブ
    if in_progress_jobs:
        print("📊 進行中のジョブ:")
        print("-" * 70)
        for job in in_progress_jobs:
            print(f"  ID: {job['batch_id']}")
            print(f"    ステータス: {job['status']}")
            print(f"    リクエスト数: {job['request_count']}")
            print(f"    作成日時: {job['created_at']}")
            print()

    # 完了したジョブ
    if completed_jobs:
        print("✅ 完了したジョブ:")
        print("-" * 70)
        for job in completed_jobs:
            success_rate = job["succeeded_count"] / job["request_count"] * 100 if job["request_count"] > 0 else 0
            print(f"  ID: {job['batch_id']}")
            print(f"    成功: {job['succeeded_count']}/{job['request_count']} ({success_rate:.1f}%)")
            print(f"    失敗: {job['failed_count']}")
            print()
            print("    結果取得コマンド:")
            print(f"      python scripts/sage/cli.py --batch-results {job['batch_id']}")
            print()

    # 失敗したジョブ
    if failed_jobs:
        print("❌ 失敗したジョブ:")
        print("-" * 70)
        for job in failed_jobs:
            print(f"  ID: {job['batch_id']}")
            print(f"    ステータス: {job['status']}")
            print()

    # サマリー
    print("=" * 70)
    print("サマリー:")
    print(f"  進行中: {len(in_progress_jobs)}")
    print(f"  完了: {len(completed_jobs)}")
    print(f"  失敗: {len(failed_jobs)}")
    print("=" * 70)


def main():
    """メイン処理"""
    asyncio.run(check_all_jobs())


if __name__ == "__main__":
    main()
