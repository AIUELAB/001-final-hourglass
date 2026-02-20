#!/usr/bin/env python3
"""
Fill Missing Dashboard Fields

既存エピソードの欠損フィールドを補完。
RCA-20260110: 欠損値防止システム

対象フィールド:
- iconic_score: IconicScoreCalculatorで計算
- episode_fame_v6: 7軸平均から計算
- episode_fame_tier_v6: v6スコアからtier算出
- fame_score_v3: 人物マスターから取得（欠損時のみ）
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.config import MASTER_CSV
from scripts.sage.quality.evaluator import IconicScoreCalculator
from scripts.sage.gates.completeness import auto_fill_all_derived_fields
from scripts.sage.persistence.backup import create_pre_operation_backup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_episode_fame_v6(row: pd.Series) -> float:
    """episode_fame_v6を計算（7軸スコア平均 * 10 + ボーナス）"""
    scores = [
        row.get("memorability_score"),
        row.get("empathy_score"),
        row.get("surprise_score"),
        row.get("generation_quality_score"),
        row.get("educational_value"),
        row.get("story_quality"),
        row.get("factual_density"),
    ]
    valid_scores = [s for s in scores if pd.notna(s) and s > 0]
    if not valid_scores:
        return 0.0

    avg = sum(valid_scores) / len(valid_scores)

    # ボーナス: fame_score_v3がある場合
    fame_v3 = row.get("fame_score_v3", 0)
    if pd.notna(fame_v3) and fame_v3 > 0:
        bonus = float(fame_v3) / 100  # 500 → 5.0
    else:
        bonus = 0

    return round(avg * 10 + bonus, 2)


def calculate_episode_fame_tier_v6(fame_v6: float) -> int:
    """episode_fame_tier_v6を算出"""
    if fame_v6 >= 90:
        return 5  # 世界的
    elif fame_v6 >= 80:
        return 4  # 国際的
    elif fame_v6 >= 70:
        return 3  # 国内著名
    elif fame_v6 >= 60:
        return 2  # 業界有名
    else:
        return 1  # ローカル


def fill_missing_fields(df: pd.DataFrame, dry_run: bool = True) -> tuple[pd.DataFrame, dict]:
    """欠損フィールドを補完"""
    stats = {
        "iconic_score_filled": 0,
        "story_quality_filled": 0,
        "episode_fame_v6_filled": 0,
        "episode_fame_tier_v6_filled": 0,
        "fame_score_v3_filled": 0,
        "total_processed": 0,
    }

    iconic_calc = IconicScoreCalculator()

    # 人物マスターからfame_score_v3を取得するためのマップ作成
    person_fame_map = {}
    for _, row in df.drop_duplicates("person_id").iterrows():
        pid = row.get("person_id")
        fame = row.get("fame_score_v3")
        if pid and pd.notna(fame):
            person_fame_map[pid] = float(fame)

    for idx, row in df.iterrows():
        modified = False
        stats["total_processed"] += 1

        # iconic_score の補完
        iconic = row.get("iconic_score")
        if pd.isna(iconic) or iconic == 0:
            text = row.get("episode_text", "")
            name = row.get("person_name", "")
            age = row.get("age", 0)
            if text and name:
                new_iconic = iconic_calc.calculate(text, name, age)
                df.at[idx, "iconic_score"] = new_iconic
                stats["iconic_score_filled"] += 1
                modified = True

        # story_quality の補完（他スコアから推定）
        story_q = row.get("story_quality")
        if pd.isna(story_q) or story_q == 0:
            # 関連スコアから推定: (memorability + empathy + generation_quality) / 3
            mem = row.get("memorability_score")
            emp = row.get("empathy_score")
            gen = row.get("generation_quality_score")
            valid_scores = [s for s in [mem, emp, gen] if pd.notna(s) and s > 0]
            if valid_scores:
                new_story_q = round(sum(valid_scores) / len(valid_scores), 1)
                df.at[idx, "story_quality"] = new_story_q
                stats["story_quality_filled"] += 1
                modified = True
            else:
                # デフォルト値
                df.at[idx, "story_quality"] = 7.0
                stats["story_quality_filled"] += 1
                modified = True

        # fame_score_v3 の補完（人物マスターから）
        fame_v3 = row.get("fame_score_v3")
        if pd.isna(fame_v3) or fame_v3 == 0:
            pid = row.get("person_id")
            if pid and pid in person_fame_map:
                df.at[idx, "fame_score_v3"] = person_fame_map[pid]
                stats["fame_score_v3_filled"] += 1
                modified = True
            else:
                # デフォルト値
                df.at[idx, "fame_score_v3"] = 500
                stats["fame_score_v3_filled"] += 1
                modified = True

        # episode_fame_v6 の補完
        fame_v6 = row.get("episode_fame_v6")
        if pd.isna(fame_v6) or fame_v6 == 0:
            # 再取得（fame_score_v3が更新されている可能性）
            new_fame_v6 = calculate_episode_fame_v6(df.loc[idx])
            if new_fame_v6 > 0:
                df.at[idx, "episode_fame_v6"] = new_fame_v6
                stats["episode_fame_v6_filled"] += 1
                modified = True

        # episode_fame_tier_v6 の補完
        tier_v6 = row.get("episode_fame_tier_v6")
        current_fame_v6 = df.at[idx, "episode_fame_v6"] if "episode_fame_v6" in df.columns else 0
        if pd.isna(tier_v6) or tier_v6 == 0:
            if pd.notna(current_fame_v6) and current_fame_v6 > 0:
                new_tier = calculate_episode_fame_tier_v6(float(current_fame_v6))
                df.at[idx, "episode_fame_tier_v6"] = new_tier
                stats["episode_fame_tier_v6_filled"] += 1
                modified = True

        if modified and stats["total_processed"] % 1000 == 0:
            logger.info(f"Processed {stats['total_processed']} episodes...")

    return df, stats


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="欠損ダッシュボードフィールドを補完")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライランモード（書き込みしない）",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(MASTER_CSV),
        help="対象CSVファイル",
    )
    args = parser.parse_args()

    logger.info(f"Loading: {args.csv}")
    df = pd.read_csv(args.csv, encoding="utf-8-sig", low_memory=False)
    logger.info(f"Total episodes: {len(df)}")

    # 補完前の欠損状況
    logger.info("補完前の欠損状況:")
    for col in ["iconic_score", "story_quality", "episode_fame_v6", "episode_fame_tier_v6", "fame_score_v3"]:
        if col in df.columns:
            missing = df[col].isna().sum() + (df[col] == 0).sum()
            logger.info(f"  {col}: {missing}件")

    # 補完実行
    logger.info("補完処理開始...")
    df, stats = fill_missing_fields(df, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("欠損フィールド補完結果")
    print("=" * 60)
    print(f"処理エピソード数: {stats['total_processed']}")
    print(f"iconic_score 補完: {stats['iconic_score_filled']}件")
    print(f"story_quality 補完: {stats['story_quality_filled']}件")
    print(f"fame_score_v3 補完: {stats['fame_score_v3_filled']}件")
    print(f"episode_fame_v6 補完: {stats['episode_fame_v6_filled']}件")
    print(f"episode_fame_tier_v6 補完: {stats['episode_fame_tier_v6_filled']}件")

    if args.dry_run:
        print("\n[DRY-RUN] 実際の書き込みは行われていません")
    else:
        # バックアップ作成
        create_pre_operation_backup("fill_missing_dashboard_fields")

        # 保存
        df.to_csv(args.csv, index=False, encoding="utf-8-sig")
        print(f"\n✅ 保存完了: {args.csv}")

    print("=" * 60)


if __name__ == "__main__":
    main()
