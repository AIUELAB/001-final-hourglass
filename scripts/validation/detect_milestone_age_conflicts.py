#!/usr/bin/env python3
"""
マイルストーン年齢不整合検出

同一人物の同一イベント（デビュー、受賞、就任等）が
複数の年齢で発生したように書かれている不整合を検出する。

検出例:
- ❌ 「レコードデビュー」が15歳/16歳/18歳の複数EPで断定されている
- ❌ 「ノーベル賞受賞」が複数年齢で書かれている
"""

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
OUTPUT_DIR = PROJECT_ROOT / "src/reports"

# マイルストーンキーワード（年齢が重要なイベント）
MILESTONE_PATTERNS = {
    "デビュー": [
        r"デビューを果たし",
        r"デビューした",
        r"でデビュー",
        r"デビュー作",
    ],
    "受賞": [
        r"受賞した",
        r"受賞を果たし",
        r"を受賞",
    ],
    "就任": [
        r"就任した",
        r"に就任",
        r"就任を果たし",
    ],
    "引退": [
        r"引退した",
        r"引退を表明",
        r"現役を退",
    ],
    "創業": [
        r"創業した",
        r"を創業",
        r"を設立",
        r"設立した",
    ],
    "初優勝": [
        r"初優勝を果たし",
        r"初優勝した",
    ],
    "金メダル": [
        r"金メダルを獲得",
        r"金メダルに輝",
    ],
}


def extract_milestones(text: str) -> list[str]:
    """テキストからマイルストーンを抽出"""
    found = []
    for milestone, patterns in MILESTONE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                found.append(milestone)
                break  # 同一マイルストーンは1回のみカウント
    return found


def scan_milestone_conflicts() -> dict:
    """マイルストーン年齢不整合をスキャン"""
    # person_id -> milestone -> [(age, episode_id, text_snippet)]
    person_milestones = defaultdict(lambda: defaultdict(list))

    with open(MASTER_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("person_id", "")
            person_name = row.get("person_name", "")
            episode_id = row.get("episode_id", "")
            age = float(row.get("age") or 0)
            text = row.get("episode_text", "")

            milestones = extract_milestones(text)
            for milestone in milestones:
                person_milestones[person_id][milestone].append(
                    {
                        "age": age,
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "text_snippet": text[:100],
                    }
                )

    # 不整合を検出（同一マイルストーンが複数年齢で出現）
    conflicts = []
    for person_id, milestones in person_milestones.items():
        for milestone, occurrences in milestones.items():
            ages = set(o["age"] for o in occurrences)
            if len(ages) > 1:
                # 複数年齢で同一マイルストーンが出現
                person_name = occurrences[0]["person_name"]
                conflicts.append(
                    {
                        "person_id": person_id,
                        "person_name": person_name,
                        "milestone": milestone,
                        "ages": sorted(ages),
                        "age_spread": max(ages) - min(ages),
                        "occurrences": occurrences,
                    }
                )

    # age_spread でソート（大きい順）
    conflicts.sort(key=lambda x: -x["age_spread"])

    return {
        "scan_date": datetime.now().isoformat(),
        "total_conflicts": len(conflicts),
        "conflicts": conflicts,
        "summary_by_milestone": {
            m: sum(1 for c in conflicts if c["milestone"] == m) for m in MILESTONE_PATTERNS.keys()
        },
    }


def main():
    """メイン処理"""
    print("=" * 60)
    print("マイルストーン年齢不整合スキャン")
    print("=" * 60)

    results = scan_milestone_conflicts()

    print(f"\n検出件数: {results['total_conflicts']}")
    print("\nマイルストーン別:")
    for milestone, count in results["summary_by_milestone"].items():
        if count > 0:
            print(f"  {milestone}: {count}件")

    # サンプル表示
    print("\n" + "=" * 60)
    print("検出例（上位5件）")
    print("=" * 60)
    for conflict in results["conflicts"][:5]:
        print(f"\n{conflict['person_name']} ({conflict['person_id']})")
        print(f"  マイルストーン: {conflict['milestone']}")
        print(f"  年齢: {conflict['ages']} (スプレッド: {conflict['age_spread']})")
        for occ in conflict["occurrences"]:
            print(f"    - {occ['age']}歳: {occ['text_snippet'][:50]}...")

    # JSON出力
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "milestone_age_conflicts.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ レポート出力: {output_path}")

    return results


if __name__ == "__main__":
    main()
