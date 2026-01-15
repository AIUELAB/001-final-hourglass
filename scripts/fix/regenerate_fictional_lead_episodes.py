#!/usr/bin/env python3
"""
FICTIONAL文頭違反エピソード再生成スクリプト

FICTIONAL形式に違反しているエピソードをBatch APIで再生成する。
必須形式: 「あなたと同じ{age}歳のとき、{name}『{work_title}』は」

Usage:
    # dry-run（対象確認）
    python scripts/fix/regenerate_fictional_lead_episodes.py --dry-run

    # 実行（バッチAPI送信）
    python scripts/fix/regenerate_fictional_lead_episodes.py --execute

    # 結果取得
    python scripts/fix/regenerate_fictional_lead_episodes.py --retrieve BATCH_ID
"""

import argparse
import json
import logging
import re
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
TARGETS_FILE = OUTPUT_DIR / "fictional_lead_regen_targets.json"

# FICTIONAL文頭パターン
FICTIONAL_LEAD_PATTERN = re.compile(r"^あなたと同じ\d+歳のとき、[^『]+『[^』]+』は")


def find_violations(df: pd.DataFrame) -> pd.DataFrame:
    """FICTIONAL文頭違反を検出"""
    fictional = df[df["person_type"] == "FICTIONAL"].copy()
    violations = fictional[~fictional["episode_text"].str.match(FICTIONAL_LEAD_PATTERN, na=False)]
    return violations


def create_batch_requests(violations_df: pd.DataFrame) -> list[dict]:
    """Batch API用のリクエストを生成"""
    requests = []

    system_prompt = """あなたはエピソード生成AIです。以下のルールを絶対に守ってください。

【絶対遵守ルール - FICTIONAL専用】
1. 冒頭は必ず「あなたと同じ{age}歳のとき、{person_name}『{work_title}』は」形式で開始
   - 人物名の直後に『作品名』を必ず含める
   - スペースや句読点を入れない
2. すべての文を丁寧語（です・ます調）で終える
3. 「私は」「私の」「私が」は絶対に使用しない
4. メタ的表現は禁止（「架空の」「設定上」「作中で」等）

【品質基準】
- 具体的な年号を2つ以上
- 固有名詞を5つ以上
- 具体的な数値を3つ以上
- 250〜400文字で完結
- キャラクターの行動や出来事を具体的に描写"""

    for _, row in violations_df.iterrows():
        person_name = row["person_name"]
        age = int(row["age"])
        work_title = row["work_title"]
        episode_id = row["episode_id"]
        current_text = str(row["episode_text"])[:200] if pd.notna(row["episode_text"]) else ""

        user_prompt = f"""# FICTIONAL文頭形式エピソード再生成タスク

## 対象キャラクター
- 人物名: {person_name}
- 年齢: {age}歳
- 作品名: {work_title}

## 現在のエピソード（形式違反）
{current_text}...

## 要求
上記を参考に、**正しいFICTIONAL文頭形式**で新しいエピソードを生成してください。

## 【絶対必須】文頭形式
必ず以下の形式で開始すること:
「あなたと同じ{age}歳のとき、{person_name}『{work_title}』は」

## 例
「あなたと同じ17歳のとき、竈門炭治郎『鬼滅の刃』は鬼殺隊に入隊しました。」

## 必須条件
1. 【最重要】冒頭は「あなたと同じ{age}歳のとき、{person_name}『{work_title}』は」で開始
2. 250〜400文字程度
3. 具体的なエピソード内容を含める
4. 丁寧語（です・ます調）で記述
5. メタ表現禁止（「架空の」「フィクション」「設定上」等）

## 出力形式
エピソードテキストのみを出力してください。"""

        requests.append(
            {
                "custom_id": f"flead_{episode_id}",
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
    jsonl_path = OUTPUT_DIR / f"fictional_lead_regen_batch_{timestamp}.jsonl"

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
    batch_info_path = OUTPUT_DIR / "fictional_lead_regen_batch_info.json"
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
        episode_id = custom_id.replace("flead_", "")

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
    results_path = OUTPUT_DIR / f"fictional_lead_regen_results_{batch_id[:20]}.json"
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
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_before_flead_regen_{timestamp}.csv"
    shutil.copy2(MASTER_CSV, backup_path)
    logger.info(f"バックアップ作成: {backup_path}")

    # CSV読み込み
    df = pd.read_csv(MASTER_CSV, low_memory=False)
    df = df.set_index("episode_id")

    success_count = 0
    fail_count = 0
    still_invalid = 0

    for r in results:
        if not r["success"]:
            fail_count += 1
            continue

        episode_id = r["episode_id"]
        new_text = r["new_text"]

        # 形式チェック
        if not FICTIONAL_LEAD_PATTERN.match(new_text):
            logger.warning(f"再生成結果も形式違反: {episode_id}")
            still_invalid += 1
            continue

        # 更新
        if episode_id in df.index:
            df.at[episode_id, "episode_text"] = new_text
            success_count += 1

    # 保存
    df = df.reset_index()
    df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")

    logger.info(f"適用完了: 成功={success_count}, 失敗={fail_count}, 形式違反継続={still_invalid}")

    return success_count


def main():
    parser = argparse.ArgumentParser(description="FICTIONAL文頭違反エピソード再生成")
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

    # 違反検出
    logger.info(f"マスターCSV読み込み: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, low_memory=False)
    violations = find_violations(df)

    logger.info(f"FICTIONAL文頭違反: {len(violations)}件")

    if len(violations) == 0:
        logger.info("違反なし。終了します。")
        return

    # サンプル表示
    print("\n--- 違反サンプル（5件）---")
    for _, row in violations.head(5).iterrows():
        print(f"[{row['episode_id']}] {row['person_name']} ({row['work_title']})")
        text = str(row["episode_text"])[:60] if pd.notna(row["episode_text"]) else ""
        print(f"  文頭: {text}...")
        print()

    if args.dry_run or (not args.execute):
        logger.info("dry-runモード: バッチ送信はスキップ")
        logger.info("実行するには --execute フラグを付けてください")
        return

    if args.execute:
        # バッチリクエスト作成
        requests = create_batch_requests(violations)
        logger.info(f"バッチリクエスト作成: {len(requests)}件")

        # 送信
        batch_id = submit_batch(requests)
        print("\n=== バッチ送信完了 ===")
        print(f"Batch ID: {batch_id}")
        print(f"件数: {len(requests)}")
        print()
        print("結果取得コマンド:")
        print(f"  python scripts/fix/regenerate_fictional_lead_episodes.py --status {batch_id}")
        print(f"  python scripts/fix/regenerate_fictional_lead_episodes.py --retrieve {batch_id}")


if __name__ == "__main__":
    main()
