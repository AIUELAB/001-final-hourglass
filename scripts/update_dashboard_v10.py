#!/usr/bin/env python3
"""
ダッシュボードv10の埋め込みデータを最新CSVで更新。
"""

import csv
import json
import re
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
DASHBOARD_PATH = Path("preserved/episode_database_dashboard_v10.html")


def load_csv_data():
    """CSVからデータを読み込み"""
    episodes = []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle slot (can be number or string like 'WEEK_1')
            slot_raw = row.get("slot", "0")
            try:
                slot = int(float(slot_raw))
            except (ValueError, TypeError):
                slot = 0

            # Handle age
            age_raw = row.get("age", "0")
            try:
                age = int(float(age_raw))
            except (ValueError, TypeError):
                age = 0

            episode = {
                "person_id": row.get("person_id", ""),
                "person_name": row.get("person_name", ""),
                "age": age,
                "slot": slot,
                "category": row.get("category", ""),
                "episode_text": row.get("episode_text", "")[:500],
                "entity_type": row.get("person_type", "REAL").lower(),
                "person_type": row.get("person_type", "REAL"),
                "work_title": row.get("work_title", "") or "",
                "episode_count": int(float(row.get("episode_count", 1) or 1)),
                "fame_score": float(row.get("fame_score_v3", 0) or 0),
                "fame_score_japan": float(row.get("fame_score_japan", 0) or 0),
                "fame_tier": int(float(row.get("fame_tier", 0) or 0)),
                "is_japanese": row.get("is_japanese", "False") == "True",
                "sitelinks_count": int(float(row.get("sitelinks_count", 0) or 0)),
                "multi_lang_pv": int(float(row.get("multi_lang_pv", 0) or 0)),
                # v2 (感銘重視スコア)
                "episode_fame_v2": float(row.get("episode_fame_v2", 0) or 0),
                "episode_fame_tier_v2": int(float(row.get("episode_fame_tier_v2", 0) or 0)),
                # Celebrity Score v2 (体感ランキング)
                "celebrity_score_v2": float(row.get("celebrity_score_v2", 0) or 0),
                "celebrity_rank_v2": int(float(row.get("celebrity_rank_v2", 0) or 0)),
            }
            episodes.append(episode)
    return episodes


def update_dashboard(episodes):
    """ダッシュボードHTMLの埋め込みデータを更新"""
    with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # EMBEDDED_EPISODE_DATA を探して置換
    pattern = r"const EMBEDDED_EPISODE_DATA = \[[\s\S]*?\];"

    # 新しいデータを作成
    json_data = json.dumps(episodes, ensure_ascii=False, indent=2)
    new_data = f"const EMBEDDED_EPISODE_DATA = {json_data};"

    # 置換
    new_html, count = re.subn(pattern, new_data, html)

    if count == 0:
        print("警告: EMBEDDED_EPISODE_DATA が見つかりませんでした")
        return False

    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)

    return True


def main():
    print("=== ダッシュボードv10 更新 ===\n")

    print("CSVデータ読み込み中...")
    episodes = load_csv_data()
    print(f"エピソード数: {len(episodes)}")

    # 統計
    persons = {}
    for ep in episodes:
        pid = ep["person_id"]
        if pid not in persons:
            persons[pid] = ep

    print(f"人物数: {len(persons)}")

    # Top 5 fame scores (Global)
    sorted_persons = sorted(persons.values(), key=lambda x: x["fame_score"], reverse=True)
    print("\nTop 5 Fame Score (Global):")
    for p in sorted_persons[:5]:
        print(f"  {p['person_name']}: {p['fame_score']:.2f}")

    # Top 5 fame scores (Japan)
    sorted_japan = sorted(persons.values(), key=lambda x: x["fame_score_japan"], reverse=True)
    print("\nTop 5 Fame Score (Japan):")
    for p in sorted_japan[:5]:
        jp_flag = "🇯🇵" if p["is_japanese"] else ""
        print(f"  {p['person_name']}: {p['fame_score_japan']:.2f} {jp_flag}")

    # Top 10 Celebrity Score v2 (体感ランキング)
    sorted_celeb_v2 = sorted(persons.values(), key=lambda x: x["celebrity_score_v2"], reverse=True)
    print("\nTop 10 Celebrity Score v2 (体感ランキング):")
    for i, p in enumerate(sorted_celeb_v2[:10], 1):
        jp_flag = "🇯🇵" if p["is_japanese"] else ""
        print(f"  {i:2d}. {p['person_name']}: {p['celebrity_score_v2']:.1f} {jp_flag}")

    print("\nダッシュボード更新中...")
    if update_dashboard(episodes):
        print(f"✓ 更新完了: {DASHBOARD_PATH}")
    else:
        print("✗ 更新失敗")


if __name__ == "__main__":
    main()
