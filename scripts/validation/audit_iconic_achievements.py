#!/usr/bin/env python3
"""
audit_iconic_achievements.py - 象徴的業績カバレッジ監査ツール

目的:
- 重要人物の象徴的業績がエピソードとしてカバーされているか検証
- 欠落している業績を検出し、レポート出力
- 自動補完の提案を生成

使用例:
    # 監査のみ
    python scripts/validation/audit_iconic_achievements.py

    # 詳細レポート
    python scripts/validation/audit_iconic_achievements.py --verbose

    # JSON出力
    python scripts/validation/audit_iconic_achievements.py --output json

EPUPルール:
    - 象徴的業績カバレッジ: 重要人物は必須業績エピソードを持つこと
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

# パス設定
PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
ACHIEVEMENTS_MASTER = PROJECT_ROOT / "preserved" / "data" / "iconic_achievements_master.json"
REPORT_DIR = PROJECT_ROOT / "src" / "reports"


def load_achievements_master() -> dict:
    """象徴的業績マスターデータを読み込む"""
    with open(ACHIEVEMENTS_MASTER, encoding="utf-8") as f:
        return json.load(f)


def load_episodes() -> list[dict]:
    """エピソードCSVを読み込む"""
    episodes = []
    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    return episodes


def check_achievement_coverage(
    person_name: str,
    required_episodes: list[dict],
    person_episodes: list[dict],
) -> dict:
    """
    人物の業績カバレッジをチェック

    Returns:
        {
            "covered": [...],
            "missing": [...],
            "coverage_rate": float
        }
    """
    covered = []
    missing = []

    for req in required_episodes:
        achievement = req["achievement"]
        keywords = req.get("keywords", [])
        target_age = req.get("age")

        # エピソードを検索
        found = False
        matched_ep = None

        for ep in person_episodes:
            text = ep.get("episode_text", "")
            ep_age = ep.get("age", "")

            # キーワードマッチング
            keyword_matches = sum(1 for kw in keywords if kw in text)
            keyword_ratio = keyword_matches / len(keywords) if keywords else 0

            # 年齢マッチング（±1年の許容）
            age_match = False
            if ep_age and target_age:
                try:
                    ep_age_int = int(float(ep_age))
                    if abs(ep_age_int - target_age) <= 1:
                        age_match = True
                except (ValueError, TypeError):
                    pass

            # 判定: キーワード50%以上マッチ、または年齢一致+キーワード30%以上
            if keyword_ratio >= 0.5 or (age_match and keyword_ratio >= 0.3):
                found = True
                matched_ep = ep
                break

        if found:
            covered.append(
                {
                    "achievement": achievement,
                    "age": target_age,
                    "matched_episode_id": matched_ep.get("episode_id"),
                    "keywords": keywords,
                }
            )
        else:
            missing.append(
                {
                    "achievement": achievement,
                    "age": target_age,
                    "year": req.get("year"),
                    "keywords": keywords,
                    "importance": req.get("importance", 9.0),
                    "priority": req.get("priority", 5),
                }
            )

    total = len(required_episodes)
    coverage_rate = len(covered) / total if total > 0 else 1.0

    return {
        "covered": covered,
        "missing": missing,
        "coverage_rate": coverage_rate,
        "total_required": total,
        "total_covered": len(covered),
    }


def run_audit(verbose: bool = False) -> dict:
    """全人物の業績カバレッジ監査を実行"""
    master = load_achievements_master()
    episodes = load_episodes()

    # 人物ごとにエピソードをグループ化
    episodes_by_person: dict[str, list[dict]] = {}
    for ep in episodes:
        pn = ep.get("person_name", "")
        if pn:
            if pn not in episodes_by_person:
                episodes_by_person[pn] = []
            episodes_by_person[pn].append(ep)

    results = {
        "audit_date": datetime.now().isoformat(),
        "version": master.get("version", "unknown"),
        "summary": {
            "total_persons_checked": 0,
            "fully_covered": 0,
            "partially_covered": 0,
            "not_covered": 0,
            "total_missing_achievements": 0,
        },
        "persons": {},
        "missing_achievements": [],
    }

    for person_name, person_data in master.get("persons", {}).items():
        required = person_data.get("required_episodes", [])
        person_episodes = episodes_by_person.get(person_name, [])

        coverage = check_achievement_coverage(person_name, required, person_episodes)

        results["persons"][person_name] = {
            "person_id": person_data.get("person_id"),
            "category": person_data.get("category"),
            "episode_count": len(person_episodes),
            "coverage_rate": coverage["coverage_rate"],
            "covered_count": coverage["total_covered"],
            "required_count": coverage["total_required"],
            "covered": coverage["covered"],
            "missing": coverage["missing"],
        }

        # 欠落業績をリストに追加
        for m in coverage["missing"]:
            results["missing_achievements"].append(
                {
                    "person_name": person_name,
                    "person_id": person_data.get("person_id"),
                    "category": person_data.get("category"),
                    **m,
                }
            )

        # サマリー更新
        results["summary"]["total_persons_checked"] += 1
        results["summary"]["total_missing_achievements"] += len(coverage["missing"])

        if coverage["coverage_rate"] == 1.0:
            results["summary"]["fully_covered"] += 1
        elif coverage["coverage_rate"] > 0:
            results["summary"]["partially_covered"] += 1
        else:
            results["summary"]["not_covered"] += 1

    # 優先度でソート
    results["missing_achievements"].sort(key=lambda x: (x.get("priority", 99), -x.get("importance", 0)))

    return results


def print_report(results: dict, verbose: bool = False):
    """レポートを出力"""
    print("=" * 70)
    print("象徴的業績カバレッジ監査レポート")
    print("=" * 70)
    print(f"監査日時: {results['audit_date']}")
    print(f"マスターバージョン: {results['version']}")
    print()

    summary = results["summary"]
    print("【サマリー】")
    print(f"  チェック人物数: {summary['total_persons_checked']}")
    print(f"  完全カバー: {summary['fully_covered']}")
    print(f"  部分カバー: {summary['partially_covered']}")
    print(f"  未カバー: {summary['not_covered']}")
    print(f"  欠落業績数: {summary['total_missing_achievements']}")
    print()

    if results["missing_achievements"]:
        print("【欠落している象徴的業績】")
        for i, m in enumerate(results["missing_achievements"][:20], 1):
            print(f"  {i}. {m['person_name']} ({m['age']}歳): {m['achievement']}")
            print(f"     優先度: {m.get('priority', '-')} / 重要度: {m.get('importance', '-')}")
            if verbose:
                print(f"     キーワード: {', '.join(m.get('keywords', []))}")
            print()

    if verbose:
        print("【人物別詳細】")
        for person_name, data in results["persons"].items():
            rate = data["coverage_rate"]
            status = "✓" if rate == 1.0 else "△" if rate > 0.5 else "✗"
            print(f"  {status} {person_name}: {rate*100:.0f}% ({data['covered_count']}/{data['required_count']})")
            if data["missing"]:
                for m in data["missing"]:
                    print(f"      欠落: {m['achievement']} ({m['age']}歳)")


def save_report(results: dict, output_path: Path):
    """レポートをJSONで保存"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nレポート保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="象徴的業績カバレッジ監査")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細レポート出力")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="出力形式")
    parser.add_argument("--save", action="store_true", help="レポートをファイル保存")
    args = parser.parse_args()

    results = run_audit(verbose=args.verbose)

    if args.output == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_report(results, verbose=args.verbose)

    if args.save:
        output_path = REPORT_DIR / f"iconic_achievements_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_report(results, output_path)

    # 欠落があれば警告
    missing_count = results["summary"]["total_missing_achievements"]
    if missing_count > 0:
        print(f"\n⚠️ 警告: {missing_count}件の象徴的業績が欠落しています")
        return 1
    else:
        print("\n✓ すべての象徴的業績がカバーされています")
        return 0


if __name__ == "__main__":
    exit(main())
