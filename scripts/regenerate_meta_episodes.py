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
import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


REGEN_LIST = PROJECT_ROOT / "src" / "reports" / "logs" / "meta_episodes_regen_list.csv"

# 必須カラム
REQUIRED_COLUMNS = ["person_id", "person_name", "age", "category", "person_type"]


def validate_dataframe(df: pd.DataFrame) -> None:
    """DataFrameの必須カラムを検証

    Raises:
        ValueError: 必須カラムが欠落している場合
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"再生成リストに必須カラムが欠落: {missing}")


def prepare_candidates(regen_df: pd.DataFrame) -> list[dict]:
    """再生成候補リストを準備

    Args:
        regen_df: 再生成対象のDataFrame

    Returns:
        候補リスト

    Raises:
        ValueError: データ形式が不正な場合
    """
    validate_dataframe(regen_df)

    candidates = []
    skipped = 0

    for idx, row in regen_df.iterrows():
        try:
            age_value = row["age"]
            # NaN/null チェック（スカラー値なのでbool()で変換）
            if bool(pd.isna(age_value)):
                logger.warning(f"行 {idx}: ageがnull - スキップ")
                skipped += 1
                continue

            candidates.append(
                {
                    "person_id": row["person_id"],
                    "person_name": row["person_name"],
                    "age": int(float(age_value)),  # "24.0" -> 24 対応
                    "category": row["category"],
                    "person_type": row["person_type"],
                }
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"行 {idx}: データ変換エラー - {e}")
            skipped += 1
            continue

    if skipped > 0:
        logger.warning(f"{skipped}件のレコードをスキップしました")

    return candidates


def submit_batch_job(candidates: list[dict], dry_run: bool = True) -> str:
    """バッチジョブを送信

    Args:
        candidates: 候補リスト
        dry_run: ドライランモード

    Returns:
        バッチID

    Raises:
        ImportError: 必要なモジュールがない場合
        Exception: API送信に失敗した場合
    """
    from scripts.sage.batch_processor import BatchProcessor, BatchRequest
    from scripts.sage.prompts.category_prompts import get_static_system_prompt

    logger.info(f"バッチジョブ準備中... 候補数: {len(candidates)}")

    if dry_run:
        logger.info("[DRY-RUN] バッチジョブは送信されません")
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

    logger.info(f"BatchRequest {len(batch_requests)} 件を作成")

    # Batch API送信
    processor = BatchProcessor()

    try:
        job = asyncio.run(processor.submit_batch(batch_requests))
    except Exception as e:
        logger.error(f"バッチ送信エラー: {e}")
        raise

    logger.info(f"✅ バッチジョブ送信完了: {job.batch_id}")
    return job.batch_id


def save_tracking_file(batch_id: str, count: int) -> Path | None:
    """追跡ファイルを保存

    Args:
        batch_id: バッチID
        count: 候補数

    Returns:
        保存したファイルパス、失敗時はNone
    """
    tracking = {
        "batch_id": batch_id,
        "timestamp": datetime.now().isoformat(),
        "count": count,
        "type": "meta_episode_regeneration",
    }
    tracking_path = (
        PROJECT_ROOT
        / "src"
        / "reports"
        / "logs"
        / f"regen_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    try:
        with open(tracking_path, "w", encoding="utf-8") as f:
            json.dump(tracking, f, ensure_ascii=False, indent=2)
        logger.info(f"📄 追跡ファイル: {tracking_path}")
        return tracking_path
    except IOError as e:
        logger.warning(f"追跡ファイル保存失敗: {e}")
        logger.info(f"手動追跡用バッチID: {batch_id}")
        return None


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
        logger.error(f"再生成リストが見つかりません: {REGEN_LIST}")
        return 1

    try:
        regen_df = pd.read_csv(REGEN_LIST)
    except pd.errors.EmptyDataError:
        logger.error(f"再生成リストが空です: {REGEN_LIST}")
        return 1
    except pd.errors.ParserError as e:
        logger.error(f"CSV解析エラー: {e}")
        return 1
    except Exception as e:
        logger.error(f"再生成リスト読み込みエラー: {e}")
        return 1

    logger.info(f"📋 再生成対象: {len(regen_df)}件")

    # カテゴリ別
    cat_dist = regen_df["category"].value_counts()
    print("\nカテゴリ別:")
    for cat, count in list(cat_dist.items())[:10]:
        print(f"  {cat}: {count}件")

    # 候補準備
    try:
        candidates = prepare_candidates(regen_df)
    except ValueError as e:
        logger.error(f"候補準備エラー: {e}")
        return 1

    if not candidates:
        logger.warning("有効な候補がありません")
        return 0

    # バッチ送信
    dry_run = not args.execute
    try:
        batch_id = submit_batch_job(candidates, dry_run=dry_run)
    except ImportError as e:
        logger.error(f"必要なモジュールがありません: {e}")
        return 1
    except Exception as e:
        logger.error(f"バッチ送信失敗: {e}")
        return 1

    if not dry_run:
        save_tracking_file(batch_id, len(candidates))

    return 0


if __name__ == "__main__":
    sys.exit(main())
