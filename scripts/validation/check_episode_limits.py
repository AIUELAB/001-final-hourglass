#!/usr/bin/env python3
"""
エピソード数上限チェックスクリプト
- 1人物あたりのエピソード上限（デフォルト5件）を検証
- 同一人物×同一作品の重複を検知
- EPUP品質ゲートとして使用

使用方法:
    python scripts/validation/check_episode_limits.py [--limit 5] [--fix]
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
DEFAULT_LIMIT = 5


def extract_work_titles(episode_text: str) -> list[str]:
    """エピソードテキストから作品名を抽出"""
    # 『作品名』パターン
    pattern = r"『([^』]+)』"
    matches = re.findall(pattern, episode_text)
    return matches


def check_episode_limits(limit: int = DEFAULT_LIMIT) -> dict:
    """人物別エピソード数をチェック"""

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 人物別にエピソードを集計
    person_episodes = defaultdict(list)
    for row in rows:
        person_name = row.get("person_name", "")
        if person_name:
            person_episodes[person_name].append(row)

    violations = []
    duplicates = []

    for person_name, episodes in person_episodes.items():
        # 上限チェック
        if len(episodes) > limit:
            violations.append(
                {
                    "person_name": person_name,
                    "count": len(episodes),
                    "limit": limit,
                    "excess": len(episodes) - limit,
                    "episode_ids": [e["episode_id"] for e in episodes],
                }
            )

        # 同一作品重複チェック
        work_counts = defaultdict(list)
        for ep in episodes:
            works = extract_work_titles(ep.get("episode_text", ""))
            for work in works:
                work_counts[work].append(ep["episode_id"])

        for work, ep_ids in work_counts.items():
            if len(ep_ids) > 1:
                duplicates.append(
                    {
                        "person_name": person_name,
                        "work_title": work,
                        "count": len(ep_ids),
                        "episode_ids": ep_ids,
                    }
                )

    return {
        "total_persons": len(person_episodes),
        "violations": violations,
        "duplicates": duplicates,
    }


def main():
    parser = argparse.ArgumentParser(description="エピソード数上限チェック")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="人物別上限")
    parser.add_argument("--fix", action="store_true", help="違反を自動修正（未実装）")
    args = parser.parse_args()

    print(f"=== エピソード上限チェック (limit={args.limit}) ===\n")

    result = check_episode_limits(args.limit)

    print(f"総人物数: {result['total_persons']}")
    print(f"上限違反: {len(result['violations'])}件")
    print(f"作品重複: {len(result['duplicates'])}件\n")

    if result["violations"]:
        print("--- 上限違反 ---")
        for v in sorted(result["violations"], key=lambda x: -x["count"])[:10]:
            print(f"  {v['person_name']}: {v['count']}件 (超過{v['excess']}件)")

    if result["duplicates"]:
        print("\n--- 同一作品重複（上位10件） ---")
        for d in sorted(result["duplicates"], key=lambda x: -x["count"])[:10]:
            print(f"  {d['person_name']} / 『{d['work_title']}』: {d['count']}件")

    # 終了コード
    if result["violations"] or result["duplicates"]:
        print("\n❌ 品質ゲート失敗")
        sys.exit(1)
    else:
        print("\n✅ 品質ゲート通過")
        sys.exit(0)


if __name__ == "__main__":
    main()
