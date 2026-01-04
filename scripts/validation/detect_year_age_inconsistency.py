#!/usr/bin/env python3
"""年齢×年号×重要イベントの時系列矛盾検出スクリプト

検出パターン:
1. 本文に年号(YYYY年)があり、birth_year + age と一定差以上の乖離がある
2. 重要イベント語（ノーベル/受賞/就任/引退/創業）の近傍の年号が年齢と合わない

出力: src/reports/year_age_inconsistency_report.json
"""

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from birth_year_database import get_birth_year

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
OUTPUT_JSON = PROJECT_ROOT / "src/reports/year_age_inconsistency_report.json"

# 重要イベント語（これらの近傍に年号があれば要チェック）
IMPORTANT_EVENT_KEYWORDS = [
    "ノーベル",
    "受賞",
    "就任",
    "引退",
    "創業",
    "設立",
    "発見",
    "発明",
    "結婚",
    "離婚",
    "死去",
    "逝去",
    "デビュー",
    "優勝",
    "メダル",
    "初",
    "世界記録",
    "金メダル",
    "銀メダル",
    "銅メダル",
]

# 年号抽出パターン
YEAR_PATTERN = re.compile(r"(\d{4})年")

# 許容差分（年齢と年号の差がこれ以上なら矛盾候補）
YEAR_TOLERANCE = 3


def extract_years_from_text(text: str) -> list[int]:
    """本文から年号（YYYY年）を抽出"""
    matches = YEAR_PATTERN.findall(text)
    return [int(y) for y in matches if 1000 <= int(y) <= 2100]


def find_event_year_pairs(text: str) -> list[tuple[str, int]]:
    """重要イベント語の近傍（前後30文字）にある年号を検出"""
    pairs = []
    for keyword in IMPORTANT_EVENT_KEYWORDS:
        idx = text.find(keyword)
        if idx != -1:
            # 前後30文字の範囲で年号を探す
            start = max(0, idx - 30)
            end = min(len(text), idx + len(keyword) + 30)
            snippet = text[start:end]
            years = extract_years_from_text(snippet)
            for y in years:
                pairs.append((keyword, y))
    return pairs


def detect_inconsistencies(max_rows: int | None = None) -> dict:
    """全エピソードをスキャンして時系列矛盾を検出"""
    results = {
        "scan_timestamp": datetime.now().isoformat(),
        "total_episodes": 0,
        "episodes_with_years": 0,
        "inconsistencies": [],
        "summary": {
            "critical": 0,  # 5年以上の乖離
            "warning": 0,  # 3-5年の乖離
            "info": 0,  # 生年データなし
        },
    }

    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            if max_rows and i >= max_rows:
                break

            results["total_episodes"] += 1

            episode_id = row.get("episode_id", "")
            person_name = row.get("person_name", "")
            age_str = row.get("age", "")
            episode_text = row.get("episode_text", "")
            person_type = row.get("person_type", "REAL")

            # 架空キャラクターはスキップ
            if person_type == "FICTIONAL":
                continue

            # 年齢が数値でない場合はスキップ
            try:
                age = int(float(age_str))
            except (ValueError, TypeError):
                continue

            # 本文から年号を抽出
            years_in_text = extract_years_from_text(episode_text)
            if not years_in_text:
                continue

            results["episodes_with_years"] += 1

            # 生年データを取得
            birth_year = get_birth_year(person_name)

            if birth_year is None:
                # 生年データなしの場合、重要イベント年号のみ記録
                event_pairs = find_event_year_pairs(episode_text)
                if event_pairs:
                    results["inconsistencies"].append(
                        {
                            "episode_id": episode_id,
                            "person_name": person_name,
                            "age": age,
                            "years_in_text": years_in_text,
                            "birth_year": None,
                            "expected_year": None,
                            "event_year_pairs": event_pairs,
                            "severity": "info",
                            "reason": "生年データなし - 重要イベント年号あり",
                        }
                    )
                    results["summary"]["info"] += 1
                continue

            # 想定年を計算
            expected_year = birth_year + age

            # 年号との差分をチェック
            for year in years_in_text:
                diff = abs(year - expected_year)

                if diff > YEAR_TOLERANCE:
                    event_pairs = find_event_year_pairs(episode_text)
                    severity = "critical" if diff >= 5 else "warning"

                    results["inconsistencies"].append(
                        {
                            "episode_id": episode_id,
                            "person_name": person_name,
                            "age": age,
                            "birth_year": birth_year,
                            "expected_year": expected_year,
                            "year_in_text": year,
                            "year_diff": diff,
                            "event_year_pairs": event_pairs,
                            "severity": severity,
                            "reason": f"本文の年号({year}年)と想定年({expected_year}年)に{diff}年の乖離",
                            "episode_text_snippet": episode_text[:200],
                        }
                    )
                    results["summary"][severity] += 1

    return results


def main():
    print("年齢×年号 時系列矛盾検出スキャン開始...")
    results = detect_inconsistencies()

    # JSON出力
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # サマリー表示
    print("\n✅ スキャン完了")
    print(f"  総エピソード数: {results['total_episodes']}")
    print(f"  年号含むエピソード: {results['episodes_with_years']}")
    print(f"  矛盾候補: {len(results['inconsistencies'])}件")
    print(f"    - CRITICAL (5年以上乖離): {results['summary']['critical']}件")
    print(f"    - WARNING (3-5年乖離): {results['summary']['warning']}件")
    print(f"    - INFO (生年データなし): {results['summary']['info']}件")
    print(f"\n📄 詳細レポート: {OUTPUT_JSON}")

    # CRITICAL/WARNINGがある場合は詳細表示
    if results["summary"]["critical"] > 0 or results["summary"]["warning"] > 0:
        print("\n⚠️ 要確認エピソード:")
        for item in results["inconsistencies"]:
            if item["severity"] in ("critical", "warning"):
                print(f"  [{item['severity'].upper()}] {item['episode_id']} - {item['person_name']} ({item['age']}歳)")
                print(f"    理由: {item['reason']}")
                if item.get("event_year_pairs"):
                    print(f"    イベント: {item['event_year_pairs']}")

    return results


if __name__ == "__main__":
    main()
