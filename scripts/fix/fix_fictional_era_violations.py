#!/usr/bin/env python3
"""
架空キャラクター時代設定違反エピソード修正スクリプト

時代設定に違反するエピソード（歴史設定作品に現代年号を含むなど）を
Batch APIで再生成して修正する。

Usage:
    # dry-run（対象確認）
    python scripts/fix/fix_fictional_era_violations.py --dry-run

    # 実行（バッチAPI送信）
    python scripts/fix/fix_fictional_era_violations.py --execute

    # 結果取得
    python scripts/fix/fix_fictional_era_violations.py --retrieve BATCH_ID
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

from scripts.validation.fictional_episode_validator import (
    WORK_ERA_SETTINGS,
    FictionalEpisodeValidator,
    ViolationType,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
OUTPUT_DIR = PROJECT_ROOT / "src" / "reports"


# =============================================================================
# 時代設定を考慮したプロンプト
# =============================================================================

SYSTEM_PROMPT = """あなたは物語世界のエピソード生成AIです。以下のルールを絶対に守ってください。

【絶対遵守ルール】
1. すべての文を常体（だ・である調）で終えてください
2. 主語は人物名または「彼/彼女」を使用してください
3. 「私は」「私の」「私が」は絶対に使用しないでください
4. 冒頭は必ず「あなたと同じX歳のとき、[人物名]は」形式で開始してください

【作品世界観ルール】
5. 現実世界の西暦年号（1900年、2000年など）は絶対に使用しないでください
6. 作品の世界観・時代設定に沿った表現のみを使用してください
7. 「『作品名』」や「アニメ」「漫画」「映画」などのメタ的表現は禁止です
8. キャラクターは作品世界内の実在人物として扱ってください

【品質基準】
- 作品内の具体的なイベント・場所・人物を2つ以上
- 固有名詞を3つ以上
- 250〜350文字で完結"""


def get_era_aware_prompt(
    person_name: str,
    age: int,
    work_title: str,
    era_name: str,
    era_note: str,
    current_text: str,
) -> str:
    """時代設定を考慮したプロンプトを生成"""
    return f"""# エピソード再生成タスク

## 対象
- 人物名: {person_name}
- 年齢: {age}歳
- 作品: {work_title}
- 時代設定: {era_name}

## 現在のエピソード（時代設定に違反）
{current_text}

## 問題点
現在のエピソードは現代の西暦年号やメタ的表現を含んでいます。
これは作品の時代設定（{era_name}）に反しています。

## 要求
上記を参考に、**作品世界観に忠実な**新しいエピソードを生成してください。
{era_note}

## 必須条件
1. 冒頭は「あなたと同じ{age}歳のとき、{person_name}は」で開始
2. 250文字以上
3. 西暦年号（19XX年、20XX年など）を使用しない
4. 「『{work_title}』」のようなメタ参照をしない
5. 常体（だ・である調）で記述

## 出力形式
エピソードテキストのみを出力してください。"""


def find_era_violations(df: pd.DataFrame) -> pd.DataFrame:
    """時代設定違反エピソードを検出"""
    validator = FictionalEpisodeValidator()

    violations = []
    for _, row in df.iterrows():
        person_type = str(row.get("person_type", "")).upper()
        if "FICTIONAL" not in person_type:
            continue

        # validate_episodeはrow: dictを引数に取る
        row_dict = row.to_dict()
        result = validator.validate_episode(row_dict)

        # ERRORレベルの違反（MODERN_YEAR_IN_HISTORICALまたはWORK_FACT_ERROR）のみ
        has_error = any(
            v.severity == "ERROR"
            and v.violation_type in (ViolationType.MODERN_YEAR_IN_HISTORICAL, ViolationType.WORK_FACT_ERROR)
            for v in result.violations
        )

        if has_error:
            violations.append(row_dict)

    return pd.DataFrame(violations)


def create_batch_requests(violation_df: pd.DataFrame) -> list[dict]:
    """Batch API用のリクエストを生成"""
    requests = []

    for _, row in violation_df.iterrows():
        person_name = str(row["person_name"])
        age = int(row["age"])
        work_title = str(row.get("work_title", ""))
        episode_id = str(row["episode_id"])
        episode_text = str(row["episode_text"])

        # 作品の時代設定を取得
        era_setting = WORK_ERA_SETTINGS.get(
            work_title,
            {"era_name": "架空世界", "year_range": None, "note": ""},
        )
        era_name = era_setting.get("era_name", "架空世界")
        era_note = era_setting.get("note", "作品世界観に忠実に記述してください。")

        user_prompt = get_era_aware_prompt(
            person_name=person_name,
            age=age,
            work_title=work_title,
            era_name=era_name,
            era_note=era_note,
            current_text=episode_text,
        )

        requests.append(
            {
                "custom_id": f"fix_era_{episode_id}",
                "params": {
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "system": SYSTEM_PROMPT,
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

    # JSONLファイルを作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = OUTPUT_DIR / f"fictional_era_fix_batch_{timestamp}.jsonl"

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
        logger.info(f"  成功: {batch.request_counts.succeeded}")
        logger.info(f"  処理中: {batch.request_counts.processing}")
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

        episode_id = result.custom_id.replace("fix_era_", "")
        content_block = result.result.message.content[0]
        if not hasattr(content_block, "text"):
            logger.warning(f"{episode_id}: テキストブロックなし")
            continue
        new_text = content_block.text.strip()  # type: ignore[union-attr]

        # 長さチェック
        if len(new_text) < 200:
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
            / f"MASTER_pre_era_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        df_original = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
        df_original.to_csv(backup_path, index=False, encoding="utf-8-sig")
        logger.info(f"バックアップ: {backup_path}")

        df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"マスターCSV更新: {updated}件")

    return updated


def main():
    parser = argparse.ArgumentParser(description="架空キャラクター時代設定違反修正")
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

    # 違反エピソード検出
    logger.info("時代設定違反を検出中...")
    violation_df = find_era_violations(df)
    logger.info(f"時代設定違反（ERROR）: {len(violation_df)}件")

    if len(violation_df) == 0:
        logger.info("対象なし")
        return

    # 統計
    work_counts = violation_df["work_title"].value_counts().head(10)
    logger.info("作品別件数（上位10）:")
    for work, cnt in work_counts.items():
        logger.info(f"  {work}: {cnt}件")

    if args.dry_run:
        logger.info("\n=== dry-run: 対象サンプル ===")
        for _, row in violation_df.head(5).iterrows():
            logger.info(f"  {row['person_name']} ({row['age']}歳) - {row['work_title']}")
        return

    if args.execute:
        # バッチリクエスト作成・送信
        requests = create_batch_requests(violation_df)
        batch_id = submit_batch(requests)
        logger.info("\n結果取得コマンド:")
        logger.info(f"  python scripts/fix/fix_fictional_era_violations.py --retrieve {batch_id}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
