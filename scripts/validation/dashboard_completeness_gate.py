#!/usr/bin/env python3
"""
Dashboard Completeness Gate

ダッシュボード表示前に全必須フィールドが埋まっていることを検証。
EPUP原則: 全フィールド埋充

RCA-20260110: 欠損値防止システム
"""

import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.config import MASTER_CSV

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ダッシュボード表示に必須のフィールド
DASHBOARD_REQUIRED_FIELDS = [
    # 8軸スコア
    "memorability_score",
    "empathy_score",
    "surprise_score",
    "generation_quality_score",
    "educational_value",
    "story_quality",  # CSVカラム名: story_quality
    "factual_density",
    "iconic_score",
    # 派生フィールド
    "episode_fame_v6",
    "episode_fame_tier_v6",
    # 基本情報
    "age",
    "episode_type",
    "super_total_score",
]

# オプショナル（あれば表示、なくてもOK）
OPTIONAL_FIELDS = [
    "fame_tier",
    "nendai",
    "overall_quality",
    "emotional_impact",
    "composite_score_5axis",
]


@dataclass
class ValidationResult:
    """検証結果"""

    passed: bool
    total_episodes: int = 0
    missing_count: int = 0
    missing_episodes: list = field(default_factory=list)
    field_stats: dict = field(default_factory=dict)

    def __str__(self) -> str:
        if self.passed:
            return f"✅ PASSED: {self.total_episodes}件すべて完全"
        return f"❌ FAILED: {self.missing_count}/{self.total_episodes}件で欠損あり"


def validate_dashboard_readiness(df: pd.DataFrame) -> ValidationResult:
    """ダッシュボード表示前の完全性検証"""
    missing_episodes = []
    field_missing_counts = {f: 0 for f in DASHBOARD_REQUIRED_FIELDS}

    for idx, row in df.iterrows():
        missing_fields = []
        for field_name in DASHBOARD_REQUIRED_FIELDS:
            val = row.get(field_name)
            if pd.isna(val) or str(val).strip() == "":
                missing_fields.append(field_name)
                field_missing_counts[field_name] += 1

        if missing_fields:
            missing_episodes.append(
                {
                    "episode_id": row.get("episode_id", f"row_{idx}"),
                    "person_name": row.get("person_name", "Unknown"),
                    "age": row.get("age", "?"),
                    "missing_fields": missing_fields,
                }
            )

    return ValidationResult(
        passed=len(missing_episodes) == 0,
        total_episodes=len(df),
        missing_count=len(missing_episodes),
        missing_episodes=missing_episodes[:100],  # 最大100件表示
        field_stats=field_missing_counts,
    )


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="ダッシュボード完全性ゲート - 欠損フィールド検出")
    parser.add_argument(
        "--csv",
        type=str,
        default=str(MASTER_CSV),
        help="検証するCSVファイル",
    )
    parser.add_argument(
        "--show-details",
        action="store_true",
        help="欠損の詳細を表示",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="詳細表示の件数上限",
    )
    args = parser.parse_args()

    # CSV読み込み
    logger.info(f"Loading: {args.csv}")
    df = pd.read_csv(args.csv, encoding="utf-8-sig")
    logger.info(f"Total episodes: {len(df)}")

    # 検証実行
    result = validate_dashboard_readiness(df)

    print("\n" + "=" * 60)
    print("ダッシュボード完全性ゲート結果")
    print("=" * 60)
    print(result)
    print()

    # フィールド別統計
    print("フィールド別欠損数:")
    for field_name, count in sorted(result.field_stats.items(), key=lambda x: -x[1]):
        if count > 0:
            pct = count / result.total_episodes * 100
            print(f"  {field_name}: {count}件 ({pct:.1f}%)")

    # 詳細表示
    if args.show_details and result.missing_episodes:
        print(f"\n欠損エピソード詳細（最大{args.limit}件）:")
        for ep in result.missing_episodes[: args.limit]:
            print(
                f"  {ep['episode_id']}: {ep['person_name']} ({ep['age']}歳) - "
                f"missing: {', '.join(ep['missing_fields'])}"
            )

    print("=" * 60)

    # 終了コード: 欠損があれば1
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
