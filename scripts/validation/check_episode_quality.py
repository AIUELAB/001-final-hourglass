#!/usr/bin/env python3
"""
エピソード品質チェックスクリプト（EPUP品質ゲート）
- 埋め草エピソードの検出
- 具体性スコアの算出
- 10件制限チェック

使用方法:
    python scripts/validation/check_episode_quality.py [--fix-limit]
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 共通モジュール
from scripts.validation.filler_detector import (
    calc_specificity_score,
    count_filler_phrases,
    is_filler,
)

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
EPISODE_LIMIT = 10


def main():
    parser = argparse.ArgumentParser(description="エピソード品質チェック")
    parser.add_argument("--fix-limit", action="store_true", help="10件超過を自動修正")
    args = parser.parse_args()

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 人物別集計
    person_episodes = defaultdict(list)
    for row in rows:
        name = row.get("person_name", "")
        if name:
            person_episodes[name].append(row)

    # チェック結果
    limit_violations = []
    filler_episodes = []

    for name, eps in person_episodes.items():
        # 10件超過チェック
        if len(eps) > EPISODE_LIMIT:
            limit_violations.append(
                {
                    "person_name": name,
                    "count": len(eps),
                    "excess": len(eps) - EPISODE_LIMIT,
                }
            )

        # 埋め草チェック
        for ep in eps:
            text = ep.get("episode_text", "")
            if is_filler(text):
                filler_episodes.append(
                    {
                        "episode_id": ep["episode_id"],
                        "person_name": name,
                        "age": ep.get("age", ""),
                        "specificity": calc_specificity_score(text),
                        "filler_count": count_filler_phrases(text),
                    }
                )

    # 結果表示
    print("=== エピソード品質チェック ===\n")
    print(f"総エピソード数: {len(rows)}")
    print(f"総人物数: {len(person_episodes)}")
    print(f"\n--- {EPISODE_LIMIT}件超過 ---")
    print(f"違反人物数: {len(limit_violations)}")

    if limit_violations:
        print("\n上位10件:")
        for v in sorted(limit_violations, key=lambda x: -x["count"])[:10]:
            print(f"  {v['person_name']}: {v['count']}件 (+{v['excess']})")

    print("\n--- 埋め草候補 ---")
    print(f"候補数: {len(filler_episodes)}")

    if filler_episodes:
        print("\n代表例（上位10件）:")
        for f in filler_episodes[:10]:
            print(f"  {f['episode_id']} / {f['person_name']} / {f['age']}歳")

    # 終了コード
    if limit_violations or filler_episodes:
        print("\n❌ 品質ゲート: 要確認")
        sys.exit(1)
    else:
        print("\n✅ 品質ゲート: 通過")
        sys.exit(0)


if __name__ == "__main__":
    main()
