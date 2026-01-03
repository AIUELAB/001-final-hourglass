#!/usr/bin/env python3
"""
アインシュタイン「1905年 奇跡の年」エピソード追加

事実根拠:
- 1905年（26歳）: 奇跡の年（Annus Mirabilis）
- 3月: 光量子仮説（後にノーベル賞受賞の論文）
- 5月: ブラウン運動の理論
- 6月: 特殊相対性理論
- 9月: E=mc²（質量とエネルギーの等価性）
- 生年月日: 1879年3月14日 → 1905年は26歳
"""

import csv
import uuid
from datetime import datetime
from pathlib import Path


def generate_episode_id():
    return f"EP-{uuid.uuid4().hex[:8].upper()}"


EINSTEIN_1905_EPISODE = {
    "person_id": "P93F1DB1",
    "person_name": "アインシュタイン",
    "age": 26.0,
    "category": "科学・技術",
    "episode_text": (
        "あなたと同じ26歳のとき、アインシュタインは1905年、「奇跡の年」と呼ばれる"
        "驚異的な業績を成し遂げました。スイス特許庁の技術者として働きながら、"
        "わずか1年間で物理学の根幹を揺るがす4本の論文を発表。光量子仮説、"
        "ブラウン運動の理論、特殊相対性理論、そしてE=mc²（質量とエネルギーの等価性）"
        "を世に問いました。特に6月に発表した特殊相対性理論は、ニュートン以来200年続いた"
        "物理学の常識を覆し、時間と空間の概念を根本から変革しました。この年の業績により"
        "アインシュタインは物理学の世界に衝撃を与え、後にノーベル物理学賞（1921年）を"
        "受賞する基盤を築いたのです。"
    ),
    "episode_type": "達成",
}


def main():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        existing = list(reader)
        fieldnames = reader.fieldnames

    print(f"既存エピソード数: {len(existing)}")

    # 重複チェック
    ep = EINSTEIN_1905_EPISODE
    duplicates = [
        row
        for row in existing
        if row.get("person_id") == ep["person_id"] and abs(float(row.get("age") or 0) - ep["age"]) < 1
    ]
    if duplicates:
        print("警告: 同一年齢のエピソードが既に存在します")
        for dup in duplicates:
            print(f"  - {dup['episode_id']}: {dup['episode_text'][:50]}...")
        print("追加をスキップします。")
        return

    template_row = existing[0].copy()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = template_row.copy()
    row["episode_id"] = generate_episode_id()
    row["person_id"] = ep["person_id"]
    row["person_name"] = ep["person_name"]
    row["age"] = str(ep["age"])
    row["category"] = ep["category"]
    row["char_count"] = str(len(ep["episode_text"]))
    row["episode_text"] = ep["episode_text"]
    row["episode_type"] = ep["episode_type"]
    row["fact_check_result"] = "確認済み"
    row["source"] = "TURNING_POINT_MANUAL"
    row["generation_timestamp"] = timestamp
    row["person_type"] = "REAL"

    print("\n追加するエピソード:")
    print(f"  ID: {row['episode_id']}")
    print(f"  人物: {ep['person_name']} (ID: {ep['person_id']})")
    print(f"  年齢: {ep['age']}歳")
    print(f"  タイプ: {ep['episode_type']}")
    print(f"  本文: {ep['episode_text'][:80]}...")

    all_episodes = existing + [row]

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_episodes)

    print(f"\n合計: {len(all_episodes)}件 (+1件追加)")
    print("完了: アインシュタイン「1905年 奇跡の年」エピソードを追加しました")


if __name__ == "__main__":
    main()
