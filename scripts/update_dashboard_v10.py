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

            # slot または age から nendai (年代ラベル) を生成
            nendai_labels = {1: "幼少期", 10: "10代", 20: "20代", 30: "30代", 40: "40代", 50: "50代", 60: "60歳以上"}
            if slot in nendai_labels:
                nendai = nendai_labels[slot]
            elif age >= 60:
                nendai = "60歳以上"
            elif age >= 10:
                nendai = f"{(age // 10) * 10}代"
            elif age >= 1:
                nendai = "幼少期"
            else:
                nendai = None

            episode = {
                "episode_id": row.get("episode_id", ""),
                "person_id": row.get("person_id", ""),
                "person_name": row.get("person_name", ""),
                "age": age,
                "slot": slot,
                "nendai": nendai,
                "category": row.get("category", ""),
                "episode_type": row.get("episode_type", ""),
                "generation_timestamp": row.get("generation_timestamp", ""),
                "episode_text": row.get("episode_text", "")[:500].replace("\n", " ").replace("\r", ""),
                "entity_type": row.get("person_type", "REAL").lower(),
                "person_type": row.get("person_type", "REAL"),
                "work_title": row.get("work_title", "") or "",
                "group_name": row.get("group_name", "") or "",
                "is_group_member": row.get("is_group_member", "False") == "True",
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
                # Episode Fame (メインスコア - 常に最新バージョンを使用)
                # RULE: ダッシュボードは常に episode_fame_score を表示（v6と同期済み）
                "episode_fame_score": float(row.get("episode_fame_score", 0) or 0),
                # Episode Fame v6 (多シグナル統合)
                "episode_fame_v6": float(row.get("episode_fame_v6", 0) or 0),
                "episode_fame_tier_v6": int(float(row.get("episode_fame_tier_v6", 0) or 0)),
                # 超総合スコア (v1.1.0)
                "super_total_score": float(row.get("super_total_score", 0) or 0),
                # 7軸スコア (原本)
                "memorability_score": float(row.get("記憶性スコア", 0) or 0),
                "empathy_score": float(row.get("共感性スコア", 0) or 0),
                "surprise_score": float(row.get("意外性スコア", 0) or 0),
                "generation_quality_score": float(row.get("生成品質スコア", 0) or 0),
                "educational_value": float(row.get("教育的価値", 0) or 0),
                "storytelling_quality": float(row.get("ストーリー品質", 0) or 0),
                "factual_density": float(row.get("事実密度", 0) or 0),
                # composite_score
                "composite_score": float(row.get("composite_score", 0) or 0),
                "composite_score_5axis": float(row.get("composite_score_5axis", 0) or 0),
            }
            # 7軸チャート用エイリアス
            episode["quality_score"] = episode["generation_quality_score"]
            episode["educational_score"] = episode["educational_value"]
            episode["narrative_score"] = episode["storytelling_quality"]
            episode["factual_score"] = episode["factual_density"]
            # 5軸スコア - CSVから読み込み（存在しない場合のみ計算でフォールバック）
            # RCA-20260106: CSVの総合品質/感情インパクトを無視していた問題を修正
            mem = episode["memorability_score"]
            gen = episode["generation_quality_score"]
            emp = episode["empathy_score"]
            sur = episode["surprise_score"]
            # 総合品質: CSVから読み込み、なければ計算
            csv_overall = row.get("総合品質", "")
            if csv_overall and csv_overall.strip():
                episode["overall_quality"] = float(csv_overall)
            else:
                episode["overall_quality"] = (mem + gen) / 2 if (mem and gen) else None
            # 感情インパクト: CSVから読み込み、なければ計算
            csv_emotional = row.get("感情インパクト", "")
            if csv_emotional and csv_emotional.strip():
                episode["emotional_impact"] = float(csv_emotional)
            else:
                episode["emotional_impact"] = (emp + sur) / 2 if (emp and sur) else None
            episode["educational_value_5"] = episode["educational_value"] or None
            episode["story_quality_5"] = episode["storytelling_quality"] or None
            episode["factual_density_5"] = episode["factual_density"] or None
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
