#!/usr/bin/env python3
"""
EPUP反映パイプライン不具合修正スクリプト

修正対象:
1. category欠損（7件）: person_idから正しいcategoryを復元
2. 年齢境界違反（2件）: DBから削除
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def fix_category_missing(df: pd.DataFrame, dry_run: bool = True) -> pd.DataFrame:
    """category欠損をperson_idから復元"""
    # category欠損のエピソード
    missing_category = df[df["category"].isna() | (df["category"] == "")]

    logger.info(f"category欠損: {len(missing_category)}件")

    fixed_count = 0
    for idx, row in missing_category.iterrows():
        person_id = row["person_id"]
        person_name = row["person_name"]

        # 同じperson_idの他のエピソードからcategoryを取得
        same_person = df[(df["person_id"] == person_id) & (df["category"].notna()) & (df["category"] != "")]

        if len(same_person) > 0:
            category = same_person["category"].iloc[0]
            logger.info(f"  修正: {person_name} → {category}")

            if not dry_run:
                df.at[idx, "category"] = category
            fixed_count += 1
        else:
            logger.warning(f"  ⚠️ {person_name}: categoryを復元できません")

    logger.info(f"category修正: {fixed_count}件")
    return df


def delete_age_boundary_violations(df: pd.DataFrame, dry_run: bool = True) -> pd.DataFrame:
    """年齢境界違反エピソードを削除"""
    # 既知の年齢境界違反
    violations = [
        ("EP-260105225818578736", "有島武郎", 80, 45),  # 死亡45歳
        ("EP-260105225818578740", "堀辰雄", 80, 48),  # 死亡48歳
    ]

    logger.info(f"年齢境界違反チェック: {len(violations)}件")

    deleted_count = 0
    for ep_id, person_name, ep_age, death_age in violations:
        match = df[df["episode_id"] == ep_id]

        if len(match) > 0:
            logger.info(f"  削除対象: {ep_id} ({person_name} {ep_age}歳 > 死亡{death_age}歳)")

            if not dry_run:
                df = df[df["episode_id"] != ep_id]
            deleted_count += 1
        else:
            logger.info(f"  未検出: {ep_id}")

    logger.info(f"年齢境界違反削除: {deleted_count}件")
    return df


def main():
    parser = argparse.ArgumentParser(description="EPUP反映パイプライン不具合修正")
    parser.add_argument("--dry-run", action="store_true", default=True, help="変更を保存しない（デフォルト）")
    parser.add_argument("--execute", action="store_true", help="実際に変更を保存")
    args = parser.parse_args()

    dry_run = not args.execute

    logger.info("=" * 60)
    logger.info("EPUP反映パイプライン不具合修正")
    logger.info(f"モード: {'dry-run' if dry_run else '実行'}")
    logger.info("=" * 60)

    # CSV読み込み
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    original_count = len(df)
    logger.info(f"元データ: {original_count}件")

    # 修正1: category欠損
    df = fix_category_missing(df, dry_run)

    # 修正2: 年齢境界違反削除
    df = delete_age_boundary_violations(df, dry_run)

    final_count = len(df)

    logger.info("=" * 60)
    logger.info("【結果サマリー】")
    logger.info(f"  元データ: {original_count}件")
    logger.info(f"  最終データ: {final_count}件")
    logger.info(f"  削除: {original_count - final_count}件")
    logger.info("=" * 60)

    if not dry_run:
        # バックアップ作成
        backup_path = MASTER_CSV.with_suffix(f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False).to_csv(
            backup_path, index=False, encoding="utf-8-sig"
        )
        logger.info(f"バックアップ: {backup_path}")

        # 保存
        df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"保存完了: {MASTER_CSV}")
    else:
        logger.info("dry-runモード: 変更は保存されていません")
        logger.info("実行するには: python scripts/fix/fix_epup_reflection_issues.py --execute")


if __name__ == "__main__":
    main()
