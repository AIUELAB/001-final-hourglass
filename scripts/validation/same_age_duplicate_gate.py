#!/usr/bin/env python3
"""
同一人物・同一年齢 重複エピソード検出ゲート

同一人物（person_id）で同一年齢のエピソードが複数存在し、
内容が類似している場合に検出してCRITICAL/WARNINGを返す。

例: マーロン・ブランド 80歳 死去エピソードが2件存在

Usage:
    python scripts/validation/same_age_duplicate_gate.py [--fix]

Exit codes:
    0: OK
    1: CRITICAL（重複あり）
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/same_age_duplicate_gate_result.json"

# 類似度閾値
SIMILARITY_THRESHOLD = 0.6  # 60%以上類似で重複とみなす


@dataclass
class SameAgeDuplicate:
    """同一年齢重複"""

    person_id: str
    person_name: str
    age: float
    episode_ids: list
    similarity: float
    severity: str
    text_snippets: list


def text_similarity(text1: str, text2: str) -> float:
    """テキスト類似度を計算（0-1）"""
    return SequenceMatcher(None, text1, text2).ratio()


def scan_same_age_duplicates() -> dict:
    """同一人物・同一年齢の重複をスキャン"""
    # 人物・年齢ごとにグループ化
    person_age_groups = defaultdict(list)

    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("person_id", "")
            person_name = row.get("person_name", "")
            episode_id = row.get("episode_id", "")
            age_str = row.get("age", "")
            text = row.get("episode_text", "")
            episode_type = row.get("episode_type", "")

            if not (person_id and text and age_str):
                continue

            try:
                age = float(age_str)
            except (ValueError, TypeError):
                continue

            key = (person_id, person_name, age)
            person_age_groups[key].append(
                {
                    "episode_id": episode_id,
                    "text": text,
                    "episode_type": episode_type,
                }
            )

    # 重複検出
    duplicates = []
    for (person_id, person_name, age), episodes in person_age_groups.items():
        if len(episodes) < 2:
            continue

        # 類似度チェック（総当たり）
        for i in range(len(episodes)):
            for j in range(i + 1, len(episodes)):
                sim = text_similarity(episodes[i]["text"], episodes[j]["text"])

                if sim >= SIMILARITY_THRESHOLD:
                    # 重大度判定
                    if sim >= 0.9:
                        severity = "critical"  # ほぼ同一
                    elif sim >= 0.75:
                        severity = "high"  # 非常に類似
                    elif sim >= 0.6:
                        severity = "medium"  # 類似
                    else:
                        severity = "low"

                    duplicates.append(
                        SameAgeDuplicate(
                            person_id=person_id,
                            person_name=person_name,
                            age=age,
                            episode_ids=[episodes[i]["episode_id"], episodes[j]["episode_id"]],
                            similarity=round(sim, 3),
                            severity=severity,
                            text_snippets=[
                                episodes[i]["text"][:100],
                                episodes[j]["text"][:100],
                            ],
                        )
                    )

    # 重大度順にソート
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    duplicates.sort(key=lambda x: (severity_order[x.severity], -x.similarity))

    # 統計
    severity_counts = {
        "critical": sum(1 for d in duplicates if d.severity == "critical"),
        "high": sum(1 for d in duplicates if d.severity == "high"),
        "medium": sum(1 for d in duplicates if d.severity == "medium"),
        "low": sum(1 for d in duplicates if d.severity == "low"),
    }

    return {
        "scan_date": datetime.now().isoformat(),
        "total_duplicates": len(duplicates),
        "severity_counts": severity_counts,
        "duplicates": [asdict(d) for d in duplicates],
    }


def main():
    parser = argparse.ArgumentParser(description="同一人物・同一年齢重複検出ゲート")
    parser.add_argument("--info-only", action="store_true", help="ゲートを落とさず情報のみ表示")
    args = parser.parse_args()

    print("=" * 60)
    print("同一人物・同一年齢 重複エピソード検出ゲート")
    print("=" * 60)

    result = scan_same_age_duplicates()

    # レポート出力（内容が同じ場合はscan_date更新をスキップしてファイルを変更しない）
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result_comparable = {k: v for k, v in result.items() if k != "scan_date"}
    skip_write = False
    if REPORT_PATH.exists():
        with open(REPORT_PATH, encoding="utf-8") as f:
            existing = json.load(f)
        existing_comparable = {k: v for k, v in existing.items() if k != "scan_date"}
        if existing_comparable == result_comparable:
            skip_write = True

    if not skip_write:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write("\n")

    # 結果表示
    print(f"\n総重複数: {result['total_duplicates']}")
    print(f"  CRITICAL (90%以上類似): {result['severity_counts']['critical']}")
    print(f"  HIGH (75-89%類似): {result['severity_counts']['high']}")
    print(f"  MEDIUM (60-74%類似): {result['severity_counts']['medium']}")
    print(f"  LOW (類似度低): {result['severity_counts']['low']}")

    if result["duplicates"]:
        print("\n--- 検出された重複 ---")
        for d in result["duplicates"][:10]:
            print(f"\n  [{d['severity'].upper()}] {d['person_name']} ({d['age']}歳)")
            print(f"    類似度: {d['similarity'] * 100:.1f}%")
            print(f"    エピソード: {d['episode_ids']}")
            print(f"    テキスト1: {d['text_snippets'][0][:60]}...")
            print(f"    テキスト2: {d['text_snippets'][1][:60]}...")

    print(f"\n✅ レポート: {REPORT_PATH}")

    # 閾値判定
    critical_count = result["severity_counts"]["critical"]
    high_count = result["severity_counts"]["high"]

    if critical_count > 0 or high_count > 0:
        print(f"\n❌ CRITICAL/HIGH重複: {critical_count + high_count}件検出")
        if not args.info_only:
            return 1

    print("\n✅ OK: 重複なし" if result["total_duplicates"] == 0 else "\n⚠️ MEDIUM/LOW重複あり（ゲート通過）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
