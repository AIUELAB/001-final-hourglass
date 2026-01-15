#!/usr/bin/env python3
"""
低スコアエピソード再生成スクリプト

composite_score < 100のエピソードをBatch APIで再生成する。

Usage:
    # dry-run（対象確認）
    python scripts/fix/regenerate_low_score_episodes.py --dry-run

    # 実行（バッチAPI送信）
    python scripts/fix/regenerate_low_score_episodes.py --execute

    # 結果取得
    python scripts/fix/regenerate_low_score_episodes.py --retrieve BATCH_ID
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"
OUTPUT_DIR = PROJECT_ROOT / "src" / "reports"
TARGETS_FILE = OUTPUT_DIR / "low_score_regen_targets.json"

SCORE_THRESHOLD = 100


def find_low_score_episodes(df: pd.DataFrame) -> pd.DataFrame:
    """低スコアエピソードを検出"""
    return df[df["composite_score"] < SCORE_THRESHOLD].copy()


def create_batch_requests(low_df: pd.DataFrame) -> list[dict]:
    """Batch API用のリクエストを生成"""
    requests = []

    for _, row in low_df.iterrows():
        person_name = row["person_name"]
        age = int(row["age"])
        person_type = row["person_type"]
        work_title = str(row["work_title"]) if pd.notna(row["work_title"]) else ""
        category = str(row["category"]) if pd.notna(row["category"]) else ""
        episode_id = row["episode_id"]

        # person_type別のプロンプト
        if person_type == "FICTIONAL":
            system_prompt = """あなたはエピソード生成AIです。以下のルールを絶対に守ってください。

【絶対遵守ルール - FICTIONAL専用】
1. 冒頭は必ず「あなたと同じ{age}歳のとき、{person_name}『{work_title}』は」形式で開始
2. すべての文を丁寧語（です・ます調）で終える
3. 「私は」「私の」「私が」は絶対に使用しない
4. メタ的表現は禁止（「架空の」「設定上」「作中で」「連載が」等）

【品質基準 - 高品質エピソード】
- 具体的な年号を2つ以上
- 固有名詞を5つ以上
- 具体的な数値を3つ以上
- 250〜400文字で完結
- キャラクターの行動や出来事を具体的に描写
- 印象的で記憶に残る内容"""

            user_prompt = f"""# FICTIONAL高品質エピソード生成タスク

## 対象キャラクター
- 人物名: {person_name}
- 年齢: {age}歳
- 作品名: {work_title}

## 【絶対必須】文頭形式
必ず以下の形式で開始すること:
「あなたと同じ{age}歳のとき、{person_name}『{work_title}』は」

## 要求
- 印象的で記憶に残るエピソードを生成
- 具体的な出来事や行動を描写
- 抽象的な表現を避ける
- 250〜400文字程度

## 出力形式
エピソードテキストのみを出力してください。"""

        elif person_type == "ANIMAL":
            system_prompt = """あなたはエピソード生成AIです。以下のルールを絶対に守ってください。

【絶対遵守ルール - 動物専用】
1. 冒頭は必ず「あなたと同じ{age}歳のとき、{person_name}は」形式で開始
2. すべての文を丁寧語（です・ます調）で終える
3. 「私は」「私の」「私が」は絶対に使用しない
4. 動物の特性や行動を具体的に描写

【品質基準 - 高品質エピソード】
- 具体的な年号を2つ以上
- 固有名詞を5つ以上
- 具体的な数値を3つ以上
- 250〜400文字で完結
- 印象的で記憶に残る内容"""

            user_prompt = f"""# 動物高品質エピソード生成タスク

## 対象
- 名前: {person_name}
- 年齢: {age}歳
- カテゴリ: {category}

## 【絶対必須】文頭形式
必ず以下の形式で開始すること:
「あなたと同じ{age}歳のとき、{person_name}は」

## 要求
- 印象的で記憶に残るエピソードを生成
- 具体的な出来事や行動を描写
- 抽象的な表現を避ける
- 250〜400文字程度

## 出力形式
エピソードテキストのみを出力してください。"""

        else:  # REAL
            system_prompt = """あなたはエピソード生成AIです。以下のルールを絶対に守ってください。

【絶対遵守ルール - 実在人物】
1. 冒頭は必ず「あなたと同じ{age}歳のとき、{person_name}は」形式で開始
2. すべての文を丁寧語（です・ます調）で終える
3. 「私は」「私の」「私が」は絶対に使用しない
4. 歴史的事実に基づいた内容

【品質基準 - 高品質エピソード】
- 具体的な年号を2つ以上
- 固有名詞を5つ以上
- 具体的な数値を3つ以上
- 250〜400文字で完結
- 印象的で記憶に残る内容"""

            user_prompt = f"""# 実在人物高品質エピソード生成タスク

## 対象
- 人物名: {person_name}
- 年齢: {age}歳
- カテゴリ: {category}

## 【絶対必須】文頭形式
必ず以下の形式で開始すること:
「あなたと同じ{age}歳のとき、{person_name}は」

## 要求
- 印象的で記憶に残るエピソードを生成
- 具体的な出来事や行動を描写
- 歴史的事実に基づく
- 250〜400文字程度

## 出力形式
エピソードテキストのみを出力してください。"""

        requests.append(
            {
                "custom_id": f"lscore_{episode_id}",
                "params": {
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 1000,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            }
        )

    return requests


def submit_batch(requests: list[dict]) -> str:
    """Batch APIにリクエストを送信"""
    import anthropic
    from anthropic.types.messages import BatchCreateParams

    client = anthropic.Anthropic()

    # JSONLファイルを作成（ログ用）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = OUTPUT_DIR / f"low_score_regen_batch_{timestamp}.jsonl"

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False) + "\n")

    logger.info(f"バッチファイル作成: {jsonl_path}")

    # Batch API送信
    batch_requests: list[BatchCreateParams.Request] = [  # type: ignore[name-defined]
        {
            "custom_id": req["custom_id"],
            "params": {
                "model": req["params"]["model"],
                "max_tokens": req["params"]["max_tokens"],
                "system": req["params"]["system"],
                "messages": req["params"]["messages"],
            },
        }
        for req in requests
    ]
    batch = client.messages.batches.create(requests=batch_requests)  # type: ignore[arg-type]

    logger.info(f"バッチ送信完了: {batch.id}")

    # バッチIDをファイルに保存
    batch_info = {
        "batch_id": batch.id,
        "submitted_at": datetime.now().isoformat(),
        "request_count": len(requests),
        "jsonl_path": str(jsonl_path),
    }
    batch_info_path = OUTPUT_DIR / "low_score_regen_batch_info.json"
    with open(batch_info_path, "w", encoding="utf-8") as f:
        json.dump(batch_info, f, ensure_ascii=False, indent=2)

    return batch.id


def check_batch_status(batch_id: str) -> dict:
    """バッチステータスを確認"""
    import anthropic

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(batch_id)

    return {
        "id": batch.id,
        "processing_status": batch.processing_status,
        "request_counts": {
            "processing": batch.request_counts.processing,
            "succeeded": batch.request_counts.succeeded,
            "errored": batch.request_counts.errored,
            "canceled": batch.request_counts.canceled,
            "expired": batch.request_counts.expired,
        },
    }


def retrieve_and_apply(batch_id: str) -> int:
    """バッチ結果を取得して適用"""
    import anthropic

    client = anthropic.Anthropic()

    # ステータス確認
    batch = client.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        logger.warning(f"バッチがまだ完了していません: {batch.processing_status}")
        logger.info(
            f"進捗: {batch.request_counts.succeeded}/{batch.request_counts.processing + batch.request_counts.succeeded}"
        )
        return 0

    # 結果取得
    logger.info("バッチ結果を取得中...")
    results = []

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        episode_id = custom_id.replace("lscore_", "")

        if result.result.type == "succeeded":
            message = result.result.message
            new_text = ""
            for block in message.content:
                if block.type == "text":
                    new_text = block.text
                    break
            results.append(
                {
                    "episode_id": episode_id,
                    "new_text": new_text.strip(),
                    "success": True,
                }
            )
        else:
            results.append(
                {
                    "episode_id": episode_id,
                    "new_text": "",
                    "success": False,
                    "error": str(result.result),
                }
            )

    # 結果をファイルに保存
    results_path = OUTPUT_DIR / f"low_score_regen_results_{batch_id[:20]}.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"結果保存: {results_path}")

    # マスターCSVに適用
    success_count = apply_results(results)

    return success_count


def apply_results(results: list[dict]) -> int:
    """結果をマスターCSVに適用"""
    # バックアップ作成
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_before_lscore_regen_{timestamp}.csv"
    shutil.copy2(MASTER_CSV, backup_path)
    logger.info(f"バックアップ作成: {backup_path}")

    # CSV読み込み
    df = pd.read_csv(MASTER_CSV, low_memory=False)
    df = df.set_index("episode_id")

    success_count = 0
    fail_count = 0
    short_count = 0

    for r in results:
        if not r["success"]:
            fail_count += 1
            continue

        episode_id = r["episode_id"]
        new_text = r["new_text"]

        # 長さチェック
        if len(new_text) < 200:
            logger.warning(f"再生成結果が短すぎる: {episode_id} ({len(new_text)}字)")
            short_count += 1
            continue

        # 更新
        if episode_id in df.index:
            df.at[episode_id, "episode_text"] = new_text
            success_count += 1

    # 保存
    df = df.reset_index()
    df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")

    logger.info(f"適用完了: 成功={success_count}, 失敗={fail_count}, 短文={short_count}")

    return success_count


def main():
    parser = argparse.ArgumentParser(description="低スコアエピソード再生成")
    parser.add_argument("--dry-run", action="store_true", help="対象確認のみ")
    parser.add_argument("--execute", action="store_true", help="バッチAPI送信")
    parser.add_argument("--status", type=str, help="バッチステータス確認")
    parser.add_argument("--retrieve", type=str, help="結果取得と適用")

    args = parser.parse_args()

    if args.status:
        status = check_batch_status(args.status)
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return

    if args.retrieve:
        success = retrieve_and_apply(args.retrieve)
        print(f"適用成功: {success}件")
        return

    # 低スコア検出
    logger.info(f"マスターCSV読み込み: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, low_memory=False)
    low_score = find_low_score_episodes(df)

    logger.info(f"低スコアエピソード (< {SCORE_THRESHOLD}): {len(low_score)}件")

    if len(low_score) == 0:
        logger.info("低スコアエピソードなし。終了します。")
        return

    # person_type別集計
    print("\n--- person_type別 ---")
    for ptype, group in low_score.groupby("person_type"):
        print(f"  {ptype}: {len(group)}件")

    # サンプル表示
    print("\n--- サンプル（5件）---")
    for _, row in low_score.head(5).iterrows():
        print(f"[{row['episode_id']}] {row['person_name']} ({row['person_type']})")
        print(f"  score: {row['composite_score']:.1f}")
        text = str(row["episode_text"])[:60] if pd.notna(row["episode_text"]) else ""
        print(f"  文頭: {text}...")
        print()

    if args.dry_run or (not args.execute):
        logger.info("dry-runモード: バッチ送信はスキップ")
        logger.info("実行するには --execute フラグを付けてください")
        return

    if args.execute:
        # バッチリクエスト作成
        requests = create_batch_requests(low_score)
        logger.info(f"バッチリクエスト作成: {len(requests)}件")

        # 送信
        batch_id = submit_batch(requests)
        print("\n=== バッチ送信完了 ===")
        print(f"Batch ID: {batch_id}")
        print(f"件数: {len(requests)}")
        print()
        print("結果取得コマンド:")
        print(f"  python scripts/fix/regenerate_low_score_episodes.py --status {batch_id}")
        print(f"  python scripts/fix/regenerate_low_score_episodes.py --retrieve {batch_id}")


if __name__ == "__main__":
    main()
