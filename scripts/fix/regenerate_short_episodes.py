#!/usr/bin/env python3
"""
短文エピソード再生成スクリプト

200文字未満のエピソードを検出し、Batch APIで200文字以上に再生成する。

Usage:
    # dry-run（対象確認）
    python scripts/fix/regenerate_short_episodes.py --dry-run

    # 実行（バッチAPI送信）
    python scripts/fix/regenerate_short_episodes.py --execute

    # 結果取得
    python scripts/fix/regenerate_short_episodes.py --retrieve BATCH_ID
"""

import argparse
import json
import logging
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
OUTPUT_DIR = PROJECT_ROOT / "src" / "reports"
MIN_LENGTH = 200


def find_short_episodes(df: pd.DataFrame) -> pd.DataFrame:
    """200文字未満のエピソードを検出"""
    df["text_len"] = df["episode_text"].str.len()
    short: pd.DataFrame = df[df["text_len"] < MIN_LENGTH].copy()  # type: ignore[assignment]
    return short


def create_batch_requests(short_df: pd.DataFrame) -> list[dict]:
    """Batch API用のリクエストを生成"""
    requests = []

    system_prompt = """あなたはエピソード生成AIです。以下のルールを絶対に守ってください。

【絶対遵守ルール】
1. すべての文を常体（だ・である調）で終えてください
2. 主語は人物名または「彼/彼女」を使用してください
3. 「私は」「私の」「私が」は絶対に使用しないでください
4. 冒頭は必ず「あなたと同じX歳のとき、[人物名]は」形式で開始してください

【品質基準】
- 具体的な年号を2つ以上
- 固有名詞を5つ以上
- 具体的な数値を3つ以上
- 250〜350文字で完結（重要：200文字以上必須）"""

    for _, row in short_df.iterrows():
        person_name = row["person_name"]
        age = int(row["age"])
        category = row["category"]
        episode_id = row["episode_id"]

        user_prompt = f"""# エピソード再生成タスク

## 対象
- 人物名: {person_name}
- 年齢: {age}歳
- カテゴリ: {category}

## 現在のエピソード（短すぎる）
{row["episode_text"]}

## 要求
上記エピソードを参考に、同じ人物・年齢・内容テーマで**250〜350文字**の新しいエピソードを生成してください。

## 必須条件
1. 冒頭は「あなたと同じ{age}歳のとき、{person_name}は」で開始
2. 250文字以上（絶対条件）
3. 具体的な年号、固有名詞、数値を含める
4. 常体（だ・である調）で記述

## 出力形式
エピソードテキストのみを出力してください。"""

        requests.append(
            {
                "custom_id": f"regen_{episode_id}",
                "params": {
                    "model": "claude-sonnet-4-20250514",
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
    jsonl_path = OUTPUT_DIR / f"short_regen_batch_{timestamp}.jsonl"

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False) + "\n")

    logger.info(f"バッチファイル作成: {jsonl_path}")

    # Batch API送信（型キャスト）
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
    return batch.id


def retrieve_and_apply(batch_id: str) -> int:
    """バッチ結果を取得して適用"""
    import anthropic

    client = anthropic.Anthropic()

    # バッチ状態確認
    batch = client.messages.batches.retrieve(batch_id)
    logger.info(f"バッチ状態: {batch.processing_status}")

    if batch.processing_status != "ended":
        logger.warning(f"バッチ未完了: {batch.processing_status}")
        return 0

    # 結果取得
    results = list(client.messages.batches.results(batch_id))
    logger.info(f"結果取得: {len(results)}件")

    # マスターCSV読み込み
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)

    updated = 0
    for result in results:
        if result.result.type != "succeeded":
            logger.warning(f"失敗: {result.custom_id}")
            continue

        episode_id = result.custom_id.replace("regen_", "")
        content_block = result.result.message.content[0]
        if not hasattr(content_block, "text"):
            logger.warning(f"{episode_id}: テキストブロックなし")
            continue
        new_text = content_block.text.strip()  # type: ignore[union-attr]

        # 長さチェック
        if len(new_text) < MIN_LENGTH:
            logger.warning(f"{episode_id}: 再生成後も短い ({len(new_text)}文字)")
            continue

        # 更新
        mask = df["episode_id"] == episode_id
        if mask.sum() == 1:
            df.loc[mask, "episode_text"] = new_text
            updated += 1

    # 保存
    if updated > 0:
        backup_path = (
            PROJECT_ROOT
            / "preserved"
            / "backups"
            / f"MASTER_pre_short_regen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        df_original = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
        df_original.to_csv(backup_path, index=False, encoding="utf-8-sig")
        logger.info(f"バックアップ: {backup_path}")

        df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"マスターCSV更新: {updated}件")

    return updated


def main():
    parser = argparse.ArgumentParser(description="短文エピソード再生成")
    parser.add_argument("--dry-run", action="store_true", help="対象確認のみ")
    parser.add_argument("--execute", action="store_true", help="バッチAPI送信")
    parser.add_argument("--retrieve", type=str, help="バッチ結果取得")
    args = parser.parse_args()

    if args.retrieve:
        updated = retrieve_and_apply(args.retrieve)
        logger.info(f"更新完了: {updated}件")
        return

    # マスターCSV読み込み
    logger.info(f"読み込み: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)

    # 短文エピソード検出
    short_df = find_short_episodes(df)
    logger.info(f"200文字未満: {len(short_df)}件")

    if len(short_df) == 0:
        logger.info("対象なし")
        return

    # 統計
    lengths = short_df["text_len"]
    logger.info(f"  文字数範囲: {lengths.min()}-{lengths.max()}")
    logger.info(f"  平均: {lengths.mean():.1f}文字")

    if args.dry_run:
        logger.info("\n=== dry-run: 対象サンプル ===")
        for _, row in short_df.head(5).iterrows():
            logger.info(f"  {row['person_name']} ({row['age']}歳): {row['text_len']}文字")
        return

    if args.execute:
        # バッチリクエスト作成・送信
        requests = create_batch_requests(short_df)
        batch_id = submit_batch(requests)
        logger.info("\n結果取得コマンド:")
        logger.info(f"  python scripts/fix/regenerate_short_episodes.py --retrieve {batch_id}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
