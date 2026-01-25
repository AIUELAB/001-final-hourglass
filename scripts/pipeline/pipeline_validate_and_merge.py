#!/usr/bin/env python3
"""
Stage 4: validate-and-merge - 品質ゲート・マージ統合

curated_episodes.csvを読み込み、詳細なバリデーションを実施後、
品質ゲートを通過したエピソードをMASTER_EPISODES_CURRENT.csvにマージします。

Input: generated/curated_episodes.csv
Output:
  - MASTER_EPISODES_CURRENT.csv (マージ)
  - generated/review_queue.csv (レビュー必要)
  - generated/failed_episodes.csv (品質ゲート不合格)
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import json
import logging
import shutil
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd

from src.models.curated_episode import CuratedEpisode
from src.validators.post_llm_validator import PostLLMValidator, QualityLevel

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# デフォルトパス
PROJECT_ROOT = Path(__file__).parent.parent
CURATED_EPISODES_PATH = PROJECT_ROOT / "generated" / "curated_episodes.csv"
MASTER_CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REVIEW_QUEUE_PATH = PROJECT_ROOT / "generated" / "review_queue.csv"
FAILED_EPISODES_PATH = PROJECT_ROOT / "generated" / "failed_episodes.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def generate_episode_id() -> str:
    """
    新しいepisode_idを生成

    Format: EP-YYMMDDHHMMSSmmm
    Example: EP-251217220504123

    Returns:
        生成されたepisode_id
    """
    now = datetime.now()
    timestamp = now.strftime("%y%m%d%H%M%S")
    milliseconds = now.microsecond // 1000
    return f"EP-{timestamp}{milliseconds:03d}"


def check_duplicate_source_id(source_id: str, master_df: pd.DataFrame) -> Optional[str]:
    """
    source_idの重複チェック

    Args:
        source_id: チェックするsource_id
        master_df: マスターCSVのDataFrame

    Returns:
        重複する既存のepisode_id、重複がなければNone
    """
    # source_urlカラムで検索（MASTER_CSVにはsource_idカラムがない場合の対応）
    if "source_url" in master_df.columns:
        duplicates = master_df[master_df["source_url"] == source_id]
        if not duplicates.empty:
            return duplicates.iloc[0]["episode_id"]
    return None


def validate_episode(episode: CuratedEpisode, validator: PostLLMValidator) -> Tuple[str, Dict]:
    """
    エピソードの詳細バリデーション

    Args:
        episode: CuratedEpisodeインスタンス
        validator: PostLLMValidatorインスタンス

    Returns:
        (status, validation_info) タプル
        status: "passed" | "failed" | "review"
        validation_info: バリデーション詳細情報
    """
    # PostLLMValidatorでバリデーション
    result = validator.validate(
        episode_text=episode.episode_text,
        age=episode.age,
        person_type=episode.person_type,
    )

    validation_info = {
        "is_valid": result.is_valid,
        "quality_score": result.quality_score,
        "quality_level": result.quality_level.value,
        "errors": result.errors,
        "warnings": result.warnings,
        "retryable": result.retryable,
        "retry_hints": result.retry_hints,
    }

    # 品質ゲート判定
    if result.is_valid and result.quality_level in [
        QualityLevel.EXCELLENT,
        QualityLevel.GOOD,
    ]:
        # EXCELLENT/GOOD: 自動マージ
        status = "passed"
    elif result.is_valid and result.quality_level == QualityLevel.ACCEPTABLE:
        # ACCEPTABLE: レビュー必要
        status = "review"
    else:
        # POOR/UNACCEPTABLE または is_valid=False: 不合格
        status = "failed"

    return status, validation_info


def merge_to_master(
    episode: CuratedEpisode,
    episode_id: str,
    master_df: pd.DataFrame,
    validation_info: Dict,
) -> pd.DataFrame:
    """
    エピソードをマスターCSVにマージ

    Args:
        episode: CuratedEpisodeインスタンス
        episode_id: 生成されたepisode_id
        master_df: マスターCSVのDataFrame
        validation_info: バリデーション情報

    Returns:
        更新されたマスターDataFrame
    """
    # episode_idを設定
    episode.episode_id = episode_id
    episode.validation_status = "passed"

    # MASTER形式に変換
    master_row = episode.to_master_format()

    # 品質スコアを設定
    master_row["quality_score"] = validation_info["quality_score"]

    # 新しい行を追加
    new_df = pd.concat([master_df, pd.DataFrame([master_row])], ignore_index=True)

    return new_df


def process_curated_episodes(
    input_csv: Path,
    master_csv: Path,
    review_queue_csv: Path,
    failed_episodes_csv: Path,
    dry_run: bool = True,
) -> Dict[str, any]:
    """
    curated_episodes.csvを処理してマージ・品質ゲート実施

    Args:
        input_csv: 入力CSV（curated_episodes.csv）
        master_csv: マスターCSV（MASTER_EPISODES_CURRENT.csv）
        review_queue_csv: レビューキューCSV
        failed_episodes_csv: 不合格エピソードCSV
        dry_run: True=ドライラン（ファイル書き込みなし）

    Returns:
        統計情報の辞書
    """
    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Processing curated episodes...")
    logger.info(f"Input: {input_csv}")
    logger.info(f"Master CSV: {master_csv}")

    # 入力CSV読み込み
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    curated_episodes = CuratedEpisode.load_from_csv(input_csv)
    logger.info(f"Loaded {len(curated_episodes)} curated episodes")

    # マスターCSV読み込み
    if not master_csv.exists():
        raise FileNotFoundError(f"Master CSV not found: {master_csv}")

    master_df = pd.read_csv(master_csv, encoding="utf-8-sig")
    logger.info(f"Loaded {len(master_df)} episodes from master CSV")
    original_count = len(master_df)

    # バリデーター初期化
    validator = PostLLMValidator()

    # 統計
    stats = {
        "total_episodes": len(curated_episodes),
        "passed": 0,
        "review": 0,
        "failed": 0,
        "duplicates": 0,
        "excellent": 0,
        "good": 0,
        "acceptable": 0,
        "poor": 0,
        "unacceptable": 0,
    }

    # 結果リスト
    passed_episodes = []
    review_episodes = []
    failed_episodes = []

    for idx, episode in enumerate(curated_episodes):
        logger.info(f"Processing [{idx + 1}/{len(curated_episodes)}]: {episode.person_name} ({episode.age}歳)")

        # 重複チェック
        duplicate_id = check_duplicate_source_id(episode.source_id, master_df)
        if duplicate_id:
            logger.warning(f"  ⚠️  Duplicate source_id detected: {duplicate_id}")
            stats["duplicates"] += 1
            continue

        # バリデーション
        status, validation_info = validate_episode(episode, validator)
        quality_level = validation_info["quality_level"]

        # 品質レベル統計
        stats[quality_level] += 1

        if status == "passed":
            logger.info(f"  ✅ PASSED ({quality_level}): {episode.episode_text[:60]}...")
            stats["passed"] += 1

            # episode_id生成
            episode_id = generate_episode_id()

            # マスターにマージ
            master_df = merge_to_master(episode, episode_id, master_df, validation_info)
            passed_episodes.append(episode)

        elif status == "review":
            logger.info(f"  📝 REVIEW ({quality_level}): {episode.episode_text[:60]}...")
            stats["review"] += 1

            # レビュー情報を追加
            episode.mark_review(f"Quality: {quality_level}, Warnings: {', '.join(validation_info['warnings'])}")
            review_episodes.append((episode, validation_info))

        else:  # failed
            logger.warning(f"  ❌ FAILED ({quality_level}): Errors={validation_info['errors']}")
            stats["failed"] += 1

            # 失敗情報を追加
            episode.mark_failed(json.dumps(validation_info, ensure_ascii=False))
            failed_episodes.append((episode, validation_info))

    # ファイル保存
    if not dry_run:
        # バックアップ作成
        backup_path = (
            master_csv.parent
            / f"MASTER_EPISODES_CURRENT_backup_before_merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        shutil.copy(master_csv, backup_path)
        logger.info(f"Backup created: {backup_path.name}")

        # マスターCSV保存
        logger.info(f"Saving {len(master_df) - original_count} new episodes to master CSV")
        master_df.to_csv(master_csv, index=False, encoding="utf-8-sig")
        logger.info(f"✅ Master CSV updated: {len(master_df)} total episodes")

        # レビューキュー保存
        if review_episodes:
            review_data = []
            for episode, validation_info in review_episodes:
                row = episode.to_dict()
                row["validation_quality_score"] = validation_info["quality_score"]
                row["validation_quality_level"] = validation_info["quality_level"]
                row["validation_warnings"] = "; ".join(validation_info["warnings"])
                review_data.append(row)

            review_df = pd.DataFrame(review_data)
            review_df.to_csv(review_queue_csv, index=False, encoding="utf-8-sig")
            logger.info(f"Review queue saved: {len(review_episodes)} episodes")

        # 不合格エピソード保存
        if failed_episodes:
            failed_data = []
            for episode, validation_info in failed_episodes:
                row = episode.to_dict()
                row["validation_quality_score"] = validation_info["quality_score"]
                row["validation_quality_level"] = validation_info["quality_level"]
                row["validation_errors"] = "; ".join(validation_info["errors"])
                failed_data.append(row)

            failed_df = pd.DataFrame(failed_data)
            failed_df.to_csv(failed_episodes_csv, index=False, encoding="utf-8-sig")
            logger.info(f"Failed episodes saved: {len(failed_episodes)} episodes")

        # 統計レポート保存
        report_path = REPORTS_DIR / f"validate_and_merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "input_csv": str(input_csv),
                    "master_csv": str(master_csv),
                    "original_count": original_count,
                    "new_count": len(master_df) - original_count,
                    "total_count": len(master_df),
                    "statistics": stats,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info(f"Report saved: {report_path}")

    elif dry_run:
        logger.info(f"[DRY-RUN] Would merge {stats['passed']} episodes to master CSV")
        logger.info(f"[DRY-RUN] Would save {stats['review']} episodes to review queue")
        logger.info(f"[DRY-RUN] Would save {stats['failed']} episodes to failed CSV")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 4: Validate and merge curated episodes to master CSV")
    parser.add_argument(
        "--input",
        type=Path,
        default=CURATED_EPISODES_PATH,
        help="Input CSV path (curated_episodes.csv)",
    )
    parser.add_argument(
        "--master",
        type=Path,
        default=MASTER_CSV_PATH,
        help="Master CSV path (MASTER_EPISODES_CURRENT.csv)",
    )
    parser.add_argument(
        "--review-queue",
        type=Path,
        default=REVIEW_QUEUE_PATH,
        help="Review queue CSV path",
    )
    parser.add_argument(
        "--failed",
        type=Path,
        default=FAILED_EPISODES_PATH,
        help="Failed episodes CSV path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (no file writes)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute mode (write files)",
    )

    args = parser.parse_args()

    # dry_run判定
    dry_run = not args.execute if not args.dry_run else True

    print("=" * 80)
    print("🔧 Stage 4: validate-and-merge - 品質ゲート・マージ統合")
    print("=" * 80)
    print()

    try:
        stats = process_curated_episodes(
            input_csv=args.input,
            master_csv=args.master,
            review_queue_csv=args.review_queue,
            failed_episodes_csv=args.failed,
            dry_run=dry_run,
        )

        # 統計表示
        print()
        print("📊 統計:")
        print(f"  総エピソード数: {stats['total_episodes']}")
        print(f"  ✅ 合格（自動マージ）: {stats['passed']}")
        print(f"  📝 レビュー必要: {stats['review']}")
        print(f"  ❌ 不合格: {stats['failed']}")
        print(f"  🔁 重複: {stats['duplicates']}")
        print()
        print("📈 品質レベル分布:")
        print(f"  EXCELLENT: {stats['excellent']}")
        print(f"  GOOD: {stats['good']}")
        print(f"  ACCEPTABLE: {stats['acceptable']}")
        print(f"  POOR: {stats['poor']}")
        print(f"  UNACCEPTABLE: {stats['unacceptable']}")
        print()

        if dry_run:
            print("ℹ️  ドライランモードで実行しました")
            print("   実際にファイルを書き込むには --execute を指定してください")
        else:
            print("✅ 完了")

        print("=" * 80)
        return 0

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
