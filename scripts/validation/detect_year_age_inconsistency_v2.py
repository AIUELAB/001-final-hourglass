#!/usr/bin/env python3
"""年齢×年号×重要イベントの時系列矛盾検出スクリプト v2

v1からの改善点:
- 「生年言及」「創立年言及」「回顧言及」を除外して誤検出を削減
- 「主題年」（その年齢の時の出来事）のみを検出対象に

検出パターン:
1. 本文に年号(YYYY年)があり、birth_year + age と一定差以上の乖離がある
2. ただし以下は除外:
   - 「XXXX年生まれ」「XXXX年生」→ 生年言及
   - 「XXXX年創立」「XXXX年設立」→ 創立年言及
   - 「XXXX年に...していた」「XXXX年代」→ 回顧言及

出力: src/reports/year_age_inconsistency_report_v2.json
"""

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from birth_year_database import get_birth_year

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
OUTPUT_JSON = PROJECT_ROOT / "src/reports/year_age_inconsistency_report_v2.json"

# 年号抽出パターン
YEAR_PATTERN = re.compile(r"(\d{4})年")

# 除外パターン（誤検出を防ぐ）
EXCLUSION_PATTERNS = [
    re.compile(r"\d{4}年生(?:まれ)?"),  # 生年言及
    re.compile(r"\d{4}年創立"),  # 創立年言及
    re.compile(r"\d{4}年設立"),  # 設立年言及
    re.compile(r"\d{4}年代"),  # 年代言及
    re.compile(r"\d{4}年(?:頃|ころ)"),  # 「頃」言及
    re.compile(r"(?:昭和|明治|大正|平成|令和)\d+年"),  # 和暦
]

# 許容差分
YEAR_TOLERANCE = 3


def extract_subject_years(text: str) -> list[tuple[int, str]]:
    """
    本文から「主題年」（その年齢の時の出来事）を抽出
    除外パターンにマッチするものは除く

    Returns:
        list of (year, context): 年号とその周辺文脈
    """
    results = []

    for match in YEAR_PATTERN.finditer(text):
        year_str = match.group(1)
        year = int(year_str)

        # 範囲チェック
        if not (1000 <= year <= 2100):
            continue

        # 周辺文脈を取得（前後30文字）
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        context = text[start:end]

        # 除外パターンチェック
        excluded = False
        for pattern in EXCLUSION_PATTERNS:
            if pattern.search(context):
                excluded = True
                break

        if not excluded:
            results.append((year, context))

    return results


def check_death_year_violation(person_name: str, age: int) -> dict | None:
    """
    死亡年齢を超えたエピソードを検出

    特定の人物の死亡年齢を確認し、それを超えるエピソードは不可能
    """
    # 死亡年齢データ（拡張可能）
    DEATH_AGES = {
        "坂本龍馬": 33,
        "夏目漱石": 49,
        "野口英世": 51,
        "手塚治虫": 60,
        "マイケル・ジャクソン": 50,
        "織田信長": 49,
        "豊臣秀吉": 62,
    }

    death_age = DEATH_AGES.get(person_name)
    if death_age and age > death_age:
        return {
            "type": "death_age_violation",
            "person_name": person_name,
            "age": age,
            "death_age": death_age,
            "reason": f"{person_name}は{death_age}歳で死亡したため、{age}歳のエピソードは不可能",
        }
    return None


def detect_inconsistencies(max_rows: int | None = None) -> dict:
    """全エピソードをスキャンして時系列矛盾を検出（v2改良版）"""
    results = {
        "scan_timestamp": datetime.now().isoformat(),
        "version": "2.0",
        "improvements": [
            "生年言及（XXXX年生まれ）を除外",
            "創立年言及（XXXX年創立）を除外",
            "年代言及（XXXX年代）を除外",
            "死亡年齢超過チェックを追加",
        ],
        "total_episodes": 0,
        "episodes_with_years": 0,
        "inconsistencies": [],
        "death_age_violations": [],
        "summary": {
            "critical": 0,
            "warning": 0,
            "death_violation": 0,
            "info": 0,
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

            # 年齢パース
            try:
                age = int(float(age_str))
            except (ValueError, TypeError):
                continue

            # 死亡年齢超過チェック
            death_violation = check_death_year_violation(person_name, age)
            if death_violation:
                death_violation["episode_id"] = episode_id
                death_violation["episode_text_snippet"] = episode_text[:150]
                results["death_age_violations"].append(death_violation)
                results["summary"]["death_violation"] += 1
                continue  # このエピソードは年号チェック不要

            # 本文から主題年を抽出（除外パターン適用済み）
            subject_years = extract_subject_years(episode_text)
            if not subject_years:
                continue

            results["episodes_with_years"] += 1

            # 生年データを取得
            birth_year = get_birth_year(person_name)
            if birth_year is None:
                results["summary"]["info"] += 1
                continue

            # 想定年を計算
            expected_year = birth_year + age

            # 年号との差分をチェック
            for year, context in subject_years:
                diff = abs(year - expected_year)

                if diff > YEAR_TOLERANCE:
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
                            "context": context,
                            "severity": severity,
                            "reason": f"本文の年号({year}年)と想定年({expected_year}年)に{diff}年の乖離",
                            "episode_text_snippet": episode_text[:200],
                        }
                    )
                    results["summary"][severity] += 1

    return results


def main():
    print("年齢×年号 時系列矛盾検出スキャン v2 開始...")
    results = detect_inconsistencies()

    # JSON出力
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # サマリー表示
    print("\n✅ スキャン完了（v2改良版）")
    print(f"  総エピソード数: {results['total_episodes']}")
    print(f"  年号含むエピソード: {results['episodes_with_years']}")
    print(f"\n  矛盾候補: {len(results['inconsistencies'])}件")
    print(f"    - CRITICAL (5年以上乖離): {results['summary']['critical']}件")
    print(f"    - WARNING (3-5年乖離): {results['summary']['warning']}件")
    print(f"    - INFO (生年データなし): {results['summary']['info']}件")
    print(f"\n  死亡年齢超過: {results['summary']['death_violation']}件")

    if results["death_age_violations"]:
        print("\n🔴 死亡年齢超過（即時修正必要）:")
        for item in results["death_age_violations"]:
            print(f"  - {item['episode_id']}: {item['person_name']} ({item['age']}歳)")
            print(f"    {item['reason']}")

    print(f"\n📄 詳細レポート: {OUTPUT_JSON}")

    return results


if __name__ == "__main__":
    main()
