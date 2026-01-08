#!/usr/bin/env python3
"""
欠落している象徴的業績をBatch APIで生成するスクリプト

使用例:
    python scripts/batch_iconic_submit.py --execute
    python scripts/batch_iconic_submit.py --dry-run
"""

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.audit_iconic_achievements import run_audit
from scripts.sage.batch_processor import BatchProcessor, BatchRequest
from scripts.sage.config import HybridConfig


def get_missing_achievements() -> list[dict]:
    """欠落している象徴的業績を取得"""
    results = run_audit(verbose=False)
    return results.get("missing_achievements", [])


def build_iconic_prompt(achievement: dict) -> str:
    """象徴的業績用のプロンプトを構築"""
    person_name = achievement["person_name"]
    age = achievement["age"]
    achievement_text = achievement["achievement"]
    year = achievement.get("year", "")
    keywords = achievement.get("keywords", [])

    prompt = f"""あなたは歴史的人物の重要な出来事を記録するエピソードライターです。

【対象人物】{person_name}
【年齢】{age}歳
【記録すべき業績】{achievement_text}
【発生年】{year}年
【含めるべきキーワード】{', '.join(keywords)}

上記の具体的な史実に基づいて、この人物の{age}歳時のエピソードを生成してください。

【必須要件】
1. 上記の業績を中心に、具体的な事実を詳細に記述すること
2. キーワードの要素を自然に盛り込むこと
3. 物語的な表現ではなく、事実ベースの記述をすること
4. 400-600文字程度で簡潔にまとめること
5. 「私は」などの一人称は使わず、客観的な視点で記述すること
6. 敬体（です・ます調）で記述すること

【禁止事項】
- 「のような人物です」「という記録があります」などのメタ表現
- 推測や解釈の挿入
- 過度な形容詞や修飾語

エピソードを生成してください:"""

    return prompt


async def submit_batch(achievements: list[dict], dry_run: bool = True) -> None:
    """Batch APIで送信"""
    config = HybridConfig()
    processor = BatchProcessor(config)

    # バッチリクエストを作成（インデックス付きでユニークなcustom_idを生成）
    import hashlib
    from datetime import datetime

    requests = []
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    for idx, ach in enumerate(achievements):
        prompt = build_iconic_prompt(ach)

        # ユニークなcustom_idを生成（インデックス付き）
        name_hash = hashlib.md5(ach["person_name"].encode()).hexdigest()[:8]
        custom_id = f"ep_{name_hash}_{ach['age']}_{timestamp}_{idx:03d}"

        req = BatchRequest(
            custom_id=custom_id,
            person_name=ach["person_name"],
            age=ach["age"],
            category=ach.get("category", "歴史"),
            prompt=prompt,
            model=config.generation_model,
        )
        requests.append(req)

    print("\n" + "=" * 60)
    print("象徴的業績 Batch API 送信")
    print("=" * 60)
    print(f"欠落業績数: {len(achievements)}")
    print(f"モード: {'dry-run' if dry_run else '実行'}")
    print()

    print("【送信対象】")
    for i, ach in enumerate(achievements[:10], 1):
        print(f"  {i}. {ach['person_name']} ({ach['age']}歳): {ach['achievement'][:30]}...")
    if len(achievements) > 10:
        print(f"  ... 他 {len(achievements) - 10} 件")
    print()

    if dry_run:
        print("(dry-run: 実際には送信しません)")
        print("\n実行するには: python scripts/batch_iconic_submit.py --execute")
        return

    # バッチ送信
    job = await processor.submit_batch(requests)

    print("=" * 60)
    print("Batch API 送信完了 (50%コスト削減)")
    print("=" * 60)
    print(f"バッチID: {job.batch_id}")
    print(f"リクエスト数: {job.request_count}")
    print(f"ステータス: {job.status}")
    print()
    print("結果を取得するには:")
    print(f"  python scripts/sage/cli.py --batch-status {job.batch_id}")
    print(f"  python scripts/sage/cli.py --batch-results {job.batch_id}")
    print()
    print("結果をマスターに統合:")
    print(f"  python scripts/sage/process_batch_results.py {job.batch_id}")
    print()
    print("注意: 結果は通常2-24時間後に取得可能になります。")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="象徴的業績をBatch APIで生成")
    parser.add_argument("--dry-run", action="store_true", default=True, help="dry-runモード")
    parser.add_argument("--execute", action="store_true", help="実際に送信")
    args = parser.parse_args()

    dry_run = not args.execute

    # 欠落業績を取得
    missing = get_missing_achievements()
    if not missing:
        print("欠落している象徴的業績はありません。")
        return

    # バッチ送信
    asyncio.run(submit_batch(missing, dry_run=dry_run))


if __name__ == "__main__":
    main()
