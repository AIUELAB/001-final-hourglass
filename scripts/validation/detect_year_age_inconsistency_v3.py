#!/usr/bin/env python3
"""年齢×年号×重要イベントの時系列矛盾検出スクリプト v3

v2からの改善点:
- 「回顧型言及」パターンを除外
  - 「XXXX年の〜以来」「XXXX年から〜」
  - 「XXXX年のデビュー/連載開始/結成」
  - 「XXXX年に〜した後」「XXXX年当時」

検出対象を「その年齢の時に起きた主題イベント」に限定

出力: src/reports/year_age_inconsistency_report_v3.json
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
OUTPUT_JSON = PROJECT_ROOT / "src/reports/year_age_inconsistency_report_v3.json"

# 年号抽出パターン
YEAR_PATTERN = re.compile(r"(\d{4})年")

# 除外パターン（v2からの継続）
EXCLUSION_PATTERNS_V2 = [
    re.compile(r"\d{4}年生(?:まれ)?"),  # 生年言及
    re.compile(r"\d{4}年創立"),  # 創立年言及
    re.compile(r"\d{4}年設立"),  # 設立年言及
    re.compile(r"\d{4}年代"),  # 年代言及
    re.compile(r"\d{4}年(?:頃|ころ)"),  # 「頃」言及
]

# 回顧型除外パターン（v3で追加）
RETROSPECTIVE_PATTERNS = [
    re.compile(r"\d{4}年の.{0,10}以来"),  # 「〜年の〜以来」
    re.compile(r"\d{4}年から"),  # 「〜年から」
    re.compile(r"\d{4}年のデビュー"),  # デビュー年
    re.compile(r"\d{4}年の連載"),  # 連載開始年
    re.compile(r"\d{4}年の結成"),  # 結成年
    re.compile(r"\d{4}年の(?:コンビ|グループ)"),  # コンビ/グループ結成
    re.compile(r"\d{4}年当時"),  # 「当時」
    re.compile(r"\d{4}年に.{0,15}(?:した後|してから)"),  # 「〜した後」
    re.compile(r"\d{4}年に(?:始|開始)"),  # 開始年
    re.compile(r"(?:若|幼|少年|少女).{0,5}\d{4}年"),  # 若い頃の言及
    re.compile(r"(?:かつて|過去に|昔).{0,10}\d{4}年"),  # 過去の言及
    re.compile(r"\d{4}年(?:スタート|発売|公開|リリース)"),  # スタート等
    # v3.1で追加: より広範な回顧パターン
    re.compile(r"後に.{0,20}\d{4}年"),  # 「後に〜年に」
    re.compile(r"この(?:功績|業績|実績).{0,10}\d{4}年"),  # 功績による後の受賞
    re.compile(r"\d{4}年には"),  # 「〜年には」（後の出来事）
    re.compile(r"\d+年(?:以上|後)"),  # 「〜年以上」「〜年後」
    re.compile(r"(?:受賞|獲得).{0,5}\d{4}年"),  # 受賞年
    re.compile(r"\d{4}年(?:の|に)(?:ノーベル|アカデミー|オリンピック|ワールドカップ)"),  # 著名な賞
    re.compile(r"\d{4}年(?:の|に)(?:引退|復帰|復活)"),  # 引退・復帰
    re.compile(r"その後.{0,15}\d{4}年"),  # 「その後〜年に」
    re.compile(r"\d{4}年(?:まで|現在)"),  # 「〜年まで」「〜年現在」
]

# 許容差分
YEAR_TOLERANCE = 3


def is_retrospective_reference(context: str) -> bool:
    """回顧型言及かどうかを判定"""
    for pattern in RETROSPECTIVE_PATTERNS:
        if pattern.search(context):
            return True
    return False


def extract_subject_years_v3(text: str) -> list[tuple[int, str, bool]]:
    """
    本文から「主題年」を抽出（v3改良版）

    Returns:
        list of (year, context, is_retrospective): 年号、周辺文脈、回顧型かどうか
    """
    results = []

    for match in YEAR_PATTERN.finditer(text):
        year_str = match.group(1)
        year = int(year_str)

        if not (1000 <= year <= 2100):
            continue

        # 周辺文脈を取得（前後50文字）
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end]

        # v2除外パターンチェック
        excluded = False
        for pattern in EXCLUSION_PATTERNS_V2:
            if pattern.search(context):
                excluded = True
                break

        if excluded:
            continue

        # 回顧型判定
        is_retro = is_retrospective_reference(context)

        results.append((year, context, is_retro))

    return results


def check_death_year_violation(person_name: str, age: int) -> dict | None:
    """死亡年齢超過チェック"""
    DEATH_AGES = {
        "坂本龍馬": 33,
        "夏目漱石": 49,
        "野口英世": 51,
        "手塚治虫": 60,
        "マイケル・ジャクソン": 50,
        "織田信長": 49,
        "豊臣秀吉": 62,
        "徳川家康": 75,
        "尾崎豊": 26,
        "hide": 33,
        "美空ひばり": 52,
        "石原裕次郎": 52,
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


def detect_inconsistencies_v3(max_rows: int | None = None) -> dict:
    """全エピソードをスキャンして時系列矛盾を検出（v3改良版）"""
    results = {
        "scan_timestamp": datetime.now().isoformat(),
        "version": "3.0",
        "improvements": [
            "v2の改善を継続",
            "回顧型言及パターンを除外（〜以来、〜から、デビュー年等）",
            "死亡年齢データを拡充",
        ],
        "total_episodes": 0,
        "episodes_with_years": 0,
        "inconsistencies": [],
        "retrospective_excluded": 0,  # 回顧型として除外した件数
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

            if person_type == "FICTIONAL":
                continue

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
                continue

            # 主題年を抽出
            subject_years = extract_subject_years_v3(episode_text)
            if not subject_years:
                continue

            # 回顧型以外のみをカウント
            non_retro_years = [(y, c) for y, c, is_retro in subject_years if not is_retro]
            retro_count = len(subject_years) - len(non_retro_years)
            results["retrospective_excluded"] += retro_count

            if not non_retro_years:
                continue

            results["episodes_with_years"] += 1

            birth_year = get_birth_year(person_name)
            if birth_year is None:
                results["summary"]["info"] += 1
                continue

            expected_year = birth_year + age

            for year, context in non_retro_years:
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
    print("年齢×年号 時系列矛盾検出スキャン v3 開始...")
    results = detect_inconsistencies_v3()

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n✅ スキャン完了（v3改良版）")
    print(f"  総エピソード数: {results['total_episodes']}")
    print(f"  年号含むエピソード: {results['episodes_with_years']}")
    print(f"  回顧型として除外: {results['retrospective_excluded']}件")
    print(f"\n  矛盾候補: {len(results['inconsistencies'])}件")
    print(f"    - CRITICAL (5年以上乖離): {results['summary']['critical']}件")
    print(f"    - WARNING (3-5年乖離): {results['summary']['warning']}件")
    print(f"    - INFO (生年データなし): {results['summary']['info']}件")
    print(f"\n  死亡年齢超過: {results['summary']['death_violation']}件")

    if results["death_age_violations"]:
        print("\n🔴 死亡年齢超過:")
        for item in results["death_age_violations"]:
            print(f"  - {item['episode_id']}: {item['person_name']} ({item['age']}歳)")

    print(f"\n📄 詳細レポート: {OUTPUT_JSON}")

    return results


if __name__ == "__main__":
    main()
