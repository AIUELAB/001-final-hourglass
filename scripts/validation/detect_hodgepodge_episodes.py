#!/usr/bin/env python3
"""
寄せ集めエピソード検出スクリプト

検出基準:
1. 本文中に複数の異なる年齢が言及されている
2. 本文中に複数の異なる年が言及されている（5年以上離れた年）
3. 時系列ジャンプ語（その後/翌年/数年後等）が多用されている
4. 複数の作品名/受賞名が列挙されている

出力: src/reports/hodgepodge_episodes_report.json
"""

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
REPORTS_DIR = Path("src/reports")


def load_episodes():
    """エピソード読み込み"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


# 時系列ジャンプを示すキーワード
TIME_JUMP_PATTERNS = [
    r"その後",
    r"翌年",
    r"翌々年",
    r"数年後",
    r"数年前",
    r"〜年後",
    r"\d+年後",
    r"\d+年前",
    r"当時",
    r"以前に",
    r"以降",
    r"それから",
    r"やがて",
    r"後に",
    r"かつて",
    r"過去に",
]

# 作品・受賞を示すパターン
WORK_PATTERNS = [
    r"『[^』]+』",  # 『作品名』
    r"「[^」]+」",  # 「作品名」
]

AWARD_PATTERNS = [
    r"受賞",
    r"金獅子賞",
    r"パルムドール",
    r"アカデミー賞",
    r"ノーベル賞",
    r"グラミー賞",
    r"芥川賞",
    r"直木賞",
    r"金メダル",
    r"優勝",
    r"MVP",
]


def analyze_episode(row):
    """エピソードを分析し、寄せ集め度を評価"""
    text = row.get("episode_text", "")
    field_age_str = row.get("age", "")

    try:
        field_age = int(float(field_age_str)) if field_age_str else None
    except (ValueError, TypeError):
        field_age = None

    issues = []
    score = 0  # 寄せ集め度スコア

    # 1. 本文中の年齢言及をチェック
    ages_in_text = re.findall(r"(\d+)歳", text)
    ages_in_text = [int(a) for a in ages_in_text]
    unique_ages = set(ages_in_text)

    # フィールド年齢以外の年齢が言及されているか
    other_ages = [a for a in unique_ages if field_age is None or abs(a - field_age) > 2]
    if other_ages:
        issues.append(
            {
                "type": "multiple_ages",
                "detail": f"field_age={field_age}, other_ages={sorted(other_ages)}",
                "severity": "high" if len(other_ages) >= 2 else "medium",
            }
        )
        score += len(other_ages) * 2

    # 2. 本文中の年（西暦）言及をチェック
    years_in_text = re.findall(r"(\d{4})年", text)
    years_in_text = [int(y) for y in years_in_text]
    unique_years = set(years_in_text)

    if len(unique_years) >= 2:
        year_range = max(unique_years) - min(unique_years)
        if year_range >= 5:
            issues.append(
                {
                    "type": "wide_year_range",
                    "detail": f"years={sorted(unique_years)}, range={year_range}years",
                    "severity": "high" if year_range >= 10 else "medium",
                }
            )
            score += year_range // 5

    # 3. 時系列ジャンプ語のカウント
    time_jump_count = 0
    for pattern in TIME_JUMP_PATTERNS:
        matches = re.findall(pattern, text)
        time_jump_count += len(matches)

    if time_jump_count >= 3:
        issues.append(
            {
                "type": "time_jump_heavy",
                "detail": f"time_jump_count={time_jump_count}",
                "severity": "high" if time_jump_count >= 5 else "medium",
            }
        )
        score += time_jump_count

    # 4. 作品名の列挙チェック
    works = []
    for pattern in WORK_PATTERNS:
        works.extend(re.findall(pattern, text))
    unique_works = set(works)

    if len(unique_works) >= 3:
        issues.append(
            {
                "type": "multiple_works",
                "detail": f"works={list(unique_works)[:5]}",
                "severity": "high" if len(unique_works) >= 5 else "medium",
            }
        )
        score += len(unique_works)

    # 5. 受賞・業績の列挙チェック
    award_count = 0
    for pattern in AWARD_PATTERNS:
        award_count += len(re.findall(pattern, text))

    if award_count >= 3:
        issues.append(
            {
                "type": "multiple_awards",
                "detail": f"award_mentions={award_count}",
                "severity": "medium",
            }
        )
        score += award_count

    return {
        "issues": issues,
        "score": score,
        "ages_mentioned": sorted(unique_ages),
        "years_mentioned": sorted(unique_years),
        "works_count": len(unique_works),
        "time_jumps": time_jump_count,
    }


def main():
    print("=" * 60)
    print("寄せ集めエピソード検出")
    print("=" * 60)

    episodes = load_episodes()
    print(f"総エピソード数: {len(episodes)}")

    # 全件分析
    candidates = []

    for row in episodes:
        ep_id = row.get("episode_id", "")
        person_name = row.get("person_name", "")
        age = row.get("age", "")

        analysis = analyze_episode(row)

        if analysis["score"] >= 5:  # 寄せ集め度が高いもののみ
            candidates.append(
                {
                    "episode_id": ep_id,
                    "person_name": person_name,
                    "age": age,
                    "score": analysis["score"],
                    "issues": analysis["issues"],
                    "ages_mentioned": analysis["ages_mentioned"],
                    "years_mentioned": analysis["years_mentioned"],
                    "works_count": analysis["works_count"],
                    "time_jumps": analysis["time_jumps"],
                    "text_snippet": row.get("episode_text", "")[:150],
                }
            )

    # スコア順にソート
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # レポート生成
    report = {
        "scan_timestamp": datetime.now().isoformat(),
        "total_episodes": len(episodes),
        "hodgepodge_candidates": len(candidates),
        "severity_breakdown": {
            "critical": len([c for c in candidates if c["score"] >= 15]),
            "high": len([c for c in candidates if 10 <= c["score"] < 15]),
            "medium": len([c for c in candidates if 5 <= c["score"] < 10]),
        },
        "candidates": candidates,
    }

    # レポート保存
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "hodgepodge_episodes_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 画面出力
    print()
    print("【検出結果】")
    print(f"  寄せ集め候補: {len(candidates)}件")
    print(f"    - Critical (score>=15): {report['severity_breakdown']['critical']}件")
    print(f"    - High (score>=10): {report['severity_breakdown']['high']}件")
    print(f"    - Medium (score>=5): {report['severity_breakdown']['medium']}件")
    print()
    print(f"詳細レポート: {report_path}")

    # 上位10件を表示
    print()
    print("【上位10件】")
    for c in candidates[:10]:
        print(f"  {c['episode_id']} ({c['person_name']}, {c['age']}歳) score={c['score']}")
        issue_types = [i["type"] for i in c["issues"]]
        print(f"    問題: {', '.join(issue_types)}")

    return report


if __name__ == "__main__":
    main()
