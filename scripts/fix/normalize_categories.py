#!/usr/bin/env python3
"""
カテゴリ正規化スクリプト

311種のカテゴリを標準カテゴリにマッピング・統合する。

Usage:
    # dry-run（統計確認）
    python scripts/fix/normalize_categories.py --dry-run

    # 実行
    python scripts/fix/normalize_categories.py --execute
"""

import argparse
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

# 正規化マッピング（重複・類似カテゴリ統合）
CATEGORY_MAPPING = {
    # 表記揺れ統合
    "エンターテインメント": "エンターテイメント",
    "スターウォーズ": "スター・ウォーズ",
    "俳優": "俳優・女優",
    "女優": "俳優・女優",
    "映画": "映画・演劇",
    "実業家": "ビジネス",
    "政治家": "政治・社会",
    "医学・健康": "科学・技術",
    "長寿者": "歴史",
    "歴史的事件": "歴史",
    "戦国武将": "歴史",
    "皇室": "歴史",
    # 複合職業を統合
    "哲学者・教育学者": "学術・研究",
    "経済学者": "学術・研究",
    "経済学者・哲学者": "学術・研究",
    "コンピュータ科学者": "科学・技術",
    "宇宙飛行士": "科学・技術",
    "推理作家": "文学",
    "小説家・劇作家": "文学",
    "小説家・軍医": "文学",
    "発明家・実業家": "ビジネス",
    "実業家・投資家": "ビジネス",
    "教育者・医師": "学術・研究",
    "医師・神学者": "学術・研究",
    "哲学者・作家": "学術・研究",
    "哲学者・政治思想家": "学術・研究",
    "ビジネス・起業": "ビジネス",
    "幕臣・政治家": "歴史",
    "公家・政治家": "歴史",
    "宗教改革者": "歴史",
    # その他（神話系は維持、作品名系も維持）
}


def normalize_categories(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """カテゴリを正規化"""
    df = df.copy()
    changes: dict[str, int] = {}

    for old_cat, new_cat in CATEGORY_MAPPING.items():
        mask = df["category"] == old_cat
        count = mask.sum()
        if count > 0:
            df.loc[mask, "category"] = new_cat
            changes[f"{old_cat} → {new_cat}"] = count

    return df, changes


def main():
    parser = argparse.ArgumentParser(description="カテゴリ正規化")
    parser.add_argument("--dry-run", action="store_true", help="統計確認のみ")
    parser.add_argument("--execute", action="store_true", help="実行")
    args = parser.parse_args()

    # 読み込み
    logger.info(f"読み込み: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)

    original_cats = df["category"].nunique()
    logger.info(f"正規化前カテゴリ数: {original_cats}")

    # 正規化
    df_normalized, changes = normalize_categories(df)

    new_cats = df_normalized["category"].nunique()
    logger.info(f"正規化後カテゴリ数: {new_cats}")
    logger.info(f"削減: {original_cats - new_cats}カテゴリ")

    if changes:
        logger.info("\n=== 変更内容 ===")
        for change, count in sorted(changes.items(), key=lambda x: -x[1]):
            logger.info(f"  {change}: {count}件")
        logger.info(f"\n合計: {sum(changes.values())}件のエピソードを更新")

    if args.dry_run:
        return

    if args.execute:
        # バックアップ
        backup_path = (
            PROJECT_ROOT
            / "preserved"
            / "backups"
            / f"MASTER_pre_cat_norm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        logger.info(f"バックアップ: {backup_path}")

        # 保存
        df_normalized.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"保存完了: {MASTER_CSV}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
