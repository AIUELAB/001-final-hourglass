#!/usr/bin/env python3
"""
矛盾エピソード修正スクリプト

同一人物・同一イベントで年齢が大幅にずれているエピソードを検出し、
不正確なものを削除する
"""

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv.bak_fact_check"
REPORT_PATH = PROJECT_ROOT / "src/reports/contradiction_fix_report.json"

# 史実データベース（正しい年齢を定義）
KNOWN_FACTS = {
    # ノーベル賞受賞者
    "朝永振一郎": {"ノーベル": 59},
    "南部陽一郎": {"ノーベル": 87},
    "下村脩": {"ノーベル": 80},
    "真鍋淑郎": {"ノーベル": 90},
    "大江健三郎": {"ノーベル": 59},
    "川端康成": {"ノーベル": 69},
    "湯川秀樹": {"ノーベル": 42},
    "ガブリエル・ガルシア＝マルケス": {"ノーベル": 55},
    "アルベルト・アインシュタイン": {"ノーベル": 42},
    "マリー・キュリー": {"ノーベル": 36},  # 1回目
    "ミルトン・フリードマン": {"ノーベル": 64},
    "フリードリヒ・ハイエク": {"ノーベル": 75},
    "根岸隆": {"ノーベル": 75},  # 根岸英一と混同の可能性
    "根岸英一": {"ノーベル": 75},
    # 創業者
    "稲盛和夫": {"創業": 27, "設立": 27},
    "永守重信": {"創業": 28},
    "堀江貴文": {"創業": 23, "設立": 23},
    "孫正義": {"創業": 24},
    "渋沢栄一": {"設立": 33},  # 第一国立銀行
    # デビュー
    "尾崎豊": {"デビュー": 18},
    "宇多田ヒカル": {"デビュー": 15},
    "美空ひばり": {"デビュー": 9},
    "石川さゆり": {"デビュー": 15},
    "高橋留美子": {"デビュー": 21},
    "吉永小百合": {"デビュー": 15},
    "松任谷由実": {"デビュー": 17},
    # 作品完成
    "葛飾北斎": {"完成": 72, "富嶽": 72},  # 富嶽三十六景
    "黒澤明": {"七人の侍": 44, "羅生門": 40},
    # 記録
    "古橋廣之進": {"世界記録": 21},
    # 引退
    "ロッシーニ": {"引退": 37},
}


def extract_event_keywords(text: str) -> list[str]:
    """テキストからイベントキーワードを抽出"""
    keywords = []

    patterns = [
        r"ノーベル",
        r"創業",
        r"設立",
        r"創設",
        r"デビュー",
        r"完成",
        r"発表",
        r"受賞",
        r"引退",
        r"世界記録",
        r"富嶽",
        r"七人の侍",
        r"羅生門",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            keywords.append(pattern)

    return keywords


def find_correct_age(person_name: str, keywords: list[str]) -> Optional[int]:
    """史実データベースから正しい年齢を検索"""
    if person_name not in KNOWN_FACTS:
        return None

    facts = KNOWN_FACTS[person_name]

    for keyword in keywords:
        for fact_key, correct_age in facts.items():
            if keyword in fact_key or fact_key in keyword:
                return correct_age

    return None


def load_episodes() -> tuple[list[dict], list[str]]:
    """エピソードを読み込み"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    return rows, fieldnames


def save_episodes(rows: list[dict], fieldnames: list[str]):
    """エピソードを保存"""
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def detect_and_fix_contradictions(rows: list[dict], dry_run: bool = True) -> dict:
    """矛盾を検出して修正"""

    # 人物・イベントごとにグループ化
    person_events = defaultdict(lambda: defaultdict(list))

    for i, row in enumerate(rows):
        person_id = row.get("person_id", "")
        person_name = row.get("person_name", "")
        episode_id = row.get("episode_id", "")
        age_str = row.get("age", "")
        text = row.get("episode_text", "")

        if not (person_id and text and age_str):
            continue

        try:
            age = float(age_str)
        except (ValueError, TypeError):
            continue

        keywords = extract_event_keywords(text)
        if not keywords:
            continue

        key = frozenset(keywords)
        person_events[(person_id, person_name)][key].append(
            {
                "index": i,
                "episode_id": episode_id,
                "age": age,
                "keywords": keywords,
                "text_snippet": text[:150],
            }
        )

    # 修正対象を特定
    episodes_to_delete = []
    report = {
        "analyzed_at": datetime.now().isoformat(),
        "dry_run": dry_run,
        "contradictions_found": 0,
        "episodes_deleted": 0,
        "details": [],
    }

    for (person_id, person_name), events in person_events.items():
        for keywords, occurrences in events.items():
            if len(occurrences) < 2:
                continue

            ages = [o["age"] for o in occurrences]
            age_spread = max(ages) - min(ages)

            if age_spread < 5:  # 5歳未満の差は許容
                continue

            report["contradictions_found"] += 1

            # 正しい年齢を特定
            correct_age = find_correct_age(person_name, list(keywords))

            detail = {
                "person_name": person_name,
                "person_id": person_id,
                "keywords": list(keywords),
                "ages_found": sorted(set(ages)),
                "correct_age": correct_age,
                "deleted_episodes": [],
                "kept_episodes": [],
            }

            if correct_age:
                # 正しい年齢から5歳以上離れているものを削除対象に
                for occ in occurrences:
                    if abs(occ["age"] - correct_age) > 5:
                        episodes_to_delete.append(occ["index"])
                        detail["deleted_episodes"].append(
                            {
                                "episode_id": occ["episode_id"],
                                "age": occ["age"],
                                "reason": f'史実({correct_age}歳)と{abs(occ["age"] - correct_age):.0f}歳のズレ',
                            }
                        )
                    else:
                        detail["kept_episodes"].append(
                            {
                                "episode_id": occ["episode_id"],
                                "age": occ["age"],
                            }
                        )
            else:
                # 史実不明の場合は、年齢が極端に離れているもの（中央値から20歳以上）を削除
                median_age = sorted(ages)[len(ages) // 2]
                for occ in occurrences:
                    if abs(occ["age"] - median_age) > 20:
                        episodes_to_delete.append(occ["index"])
                        detail["deleted_episodes"].append(
                            {
                                "episode_id": occ["episode_id"],
                                "age": occ["age"],
                                "reason": f'中央値({median_age}歳)から{abs(occ["age"] - median_age):.0f}歳離れている',
                            }
                        )
                    else:
                        detail["kept_episodes"].append(
                            {
                                "episode_id": occ["episode_id"],
                                "age": occ["age"],
                            }
                        )

            if detail["deleted_episodes"]:
                report["details"].append(detail)

    # 削除実行
    episodes_to_delete = sorted(set(episodes_to_delete), reverse=True)
    report["episodes_deleted"] = len(episodes_to_delete)

    if not dry_run and episodes_to_delete:
        # バックアップ作成
        print(f"バックアップ作成: {BACKUP_PATH}")
        import shutil

        shutil.copy(CSV_PATH, BACKUP_PATH)

        # 削除
        for idx in episodes_to_delete:
            del rows[idx]

    return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="矛盾エピソード修正")
    parser.add_argument("--execute", action="store_true", help="実際に削除を実行")
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 60)
    print("矛盾エピソード修正スクリプト")
    print("=" * 60)
    print(f"モード: {'ドライラン' if dry_run else '★実行★'}")

    print("\nエピソード読み込み中...")
    rows, fieldnames = load_episodes()
    print(f"総エピソード数: {len(rows)}")

    print("\n矛盾検出・修正中...")
    report = detect_and_fix_contradictions(rows, dry_run=dry_run)

    print("\n=== 結果 ===")
    print(f"検出した矛盾: {report['contradictions_found']}件")
    print(f"削除対象エピソード: {report['episodes_deleted']}件")

    print("\n=== 削除対象（上位20件） ===")
    for i, detail in enumerate(report["details"][:20], 1):
        print(f"\n{i}. {detail['person_name']}")
        print(f"   キーワード: {detail['keywords']}")
        print(f"   史実年齢: {detail['correct_age']}")
        for ep in detail["deleted_episodes"][:3]:
            print(f"   ✗ {ep['episode_id']} (age={ep['age']}) - {ep['reason']}")

    # レポート保存
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nレポート保存: {REPORT_PATH}")

    if not dry_run:
        print("\nCSV保存中...")
        save_episodes(rows, fieldnames)
        print(f"保存完了: {CSV_PATH}")
        print(f"削除後エピソード数: {len(rows)}")
    else:
        print("\n💡 ドライラン完了。--execute で実際に削除を実行")


if __name__ == "__main__":
    main()
