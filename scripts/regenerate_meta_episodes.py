#!/usr/bin/env python3
"""
メタエピソード再生成スクリプト

削除されたメタ的エピソード（作品制作・放送等の外部視点）を
正しい内容（物語内の出来事）で再生成する。

Usage:
    # dry-run
    python scripts/regenerate_meta_episodes.py --dry-run

    # 実行（バッチAPI送信）
    python scripts/regenerate_meta_episodes.py --execute
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd


REGEN_LIST = PROJECT_ROOT / "src" / "reports" / "logs" / "meta_episodes_regen_list.csv"
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


def prepare_candidates(regen_df: pd.DataFrame) -> list[dict]:
    """再生成候補リストを準備"""
    candidates = []
    for _, row in regen_df.iterrows():
        candidates.append(
            {
                "person_id": row["person_id"],
                "person_name": row["person_name"],
                "age": int(row["age"]),
                "category": row["category"],
                "person_type": row["person_type"],
            }
        )
    return candidates


def submit_batch_job(candidates: list[dict], dry_run: bool = True) -> str:
    """バッチジョブを送信"""
    import asyncio
    from scripts.sage.batch_processor import BatchProcessor, BatchRequest
    from scripts.sage.prompts.category_prompts import get_static_system_prompt

    print("\n📦 バッチジョブ準備中...")
    print(f"  候補数: {len(candidates)}")

    if dry_run:
        print("\n[DRY-RUN] バッチジョブは送信されません")
        return "dry-run-batch-id"

    # リクエスト構築
    batch_requests = []
    system_prompt = get_static_system_prompt()

    for cand in candidates:
        # 架空キャラ専用の追加プロンプト
        fictional_instruction = """
【重要】このキャラクターは架空（FICTIONAL）です。
- 物語の「中」で起きた出来事のみを書いてください
- 禁止：アニメ化、放送開始、興行収入、視聴率、連載、原作、声優
- 禁止：「読者」「視聴者」「ファン」「社会現象」
- 作品内の冒険、戦い、成長、関係性の変化などを具体的に描写してください
"""

        user_prompt = f"""{cand['person_name']}『{cand['category']}』の{cand['age']}歳のときのエピソードを生成してください。
{fictional_instruction}
必ず以下の形式で開始:
「あなたと同じ{cand['age']}歳のとき、{cand['person_name']}は」

物語内の具体的な出来事（戦い、冒険、成長、関係性の変化など）を300-400文字で記述してください。"""

        custom_id = f"{cand['person_id']}_{cand['age']}"

        batch_requests.append(
            BatchRequest(
                custom_id=custom_id,
                person_name=cand["person_name"],
                age=cand["age"],
                category=cand["category"],
                prompt=f"{system_prompt}\n\n{user_prompt}",
                model="claude-3-5-haiku-20241022",
                max_tokens=600,
            )
        )

    print(f"  BatchRequest {len(batch_requests)} 件を作成")

    # Batch API送信
    processor = BatchProcessor()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    job = loop.run_until_complete(processor.submit_batch(batch_requests))
    print(f"✅ バッチジョブ送信完了: {job.batch_id}")

    return job.batch_id


def main():
    parser = argparse.ArgumentParser(description="メタエピソード再生成")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン")
    parser.add_argument("--execute", action="store_true", help="実行")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("--dry-run または --execute を指定してください")
        return 1

    print("=" * 60)
    print("🔄 メタエピソード再生成")
    print("=" * 60)

    # 再生成リスト読み込み
    if not REGEN_LIST.exists():
        print(f"❌ 再生成リストが見つかりません: {REGEN_LIST}")
        return 1

    regen_df = pd.read_csv(REGEN_LIST)
    print(f"\n📋 再生成対象: {len(regen_df)}件")

    # カテゴリ別
    cat_dist = regen_df["category"].value_counts()
    print("\nカテゴリ別:")
    for cat, count in list(cat_dist.items())[:10]:
        print(f"  {cat}: {count}件")

    # 候補準備
    candidates = prepare_candidates(regen_df)

    # バッチ送信
    dry_run = not args.execute
    batch_id = submit_batch_job(candidates, dry_run=dry_run)

    if not dry_run:
        # 結果追跡用に保存
        tracking = {
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "count": len(candidates),
            "type": "meta_episode_regeneration",
        }
        tracking_path = (
            PROJECT_ROOT / "src" / "reports" / "logs" / f"regen_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(tracking_path, "w", encoding="utf-8") as f:
            json.dump(tracking, f, ensure_ascii=False, indent=2)
        print(f"\n📄 追跡ファイル: {tracking_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
