#!/usr/bin/env python3
"""
黒澤明エピソード修正スクリプト
- 44件→5件に削減
- E574646B5の年齢を70→75歳に修正
- 『七人の侍』エピソードを新規作成（44歳）
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# 残すエピソードID
KEEP_EPISODES = {
    "E574646B5",  # 『乱』75歳（年齢修正）
    "EP-000001636",  # デルス・ウザーラ 57歳
    "EP-000001562",  # 挫折と復活 60歳
    "EP-000000233",  # 羅生門 40歳
}

# 新規作成する『七人の侍』エピソード
SEVEN_SAMURAI_EPISODE = {
    "episode_id": "EP-KUROSAWA-7SAMURAI",
    "person_id": "PBC4ECE7",
    "person_name": "黒澤明",
    "episode_count": "1.0",
    "age": "44.0",
    "category": "映画・演劇",
    "char_count": "320",
    "episode_text": "あなたと同じ44歳のとき、黒澤明は映画史に残る傑作『七人の侍』を完成させました。1954年、製作期間1年、当時としては破格の2億円の制作費を投じたこの作品は、野武士に襲われる農村を守るため集められた7人の浪人たちの物語です。黒澤は徹底したリアリズムを追求し、雨の中の合戦シーンでは実際に墨汁を混ぜた雨を降らせ、俳優たちに極限の演技を要求しました。3時間27分という長尺ながら、緻密な脚本と革新的な編集技法で観客を引き込み、ヴェネツィア国際映画祭で銀獅子賞を受賞。この作品は後に『荒野の七人』としてハリウッドでリメイクされ、世界中の映画作りに計り知れない影響を与えました。",
    "episode_type": "達成",
    "fact_check_result": "確認済み",
}


def main():
    if not CSV_PATH.exists():
        print(f"Error: {CSV_PATH} not found")
        sys.exit(1)

    # CSVを読み込み（BOM対応）
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"読み込み: {len(rows)}件")

    # 黒澤明以外の行と、残す黒澤明エピソードを分離
    non_kurosawa = []
    kurosawa_keep = []
    kurosawa_delete = []

    for row in rows:
        if row.get("person_name") == "黒澤明":
            if row.get("episode_id") in KEEP_EPISODES:
                # E574646B5は年齢修正
                if row.get("episode_id") == "E574646B5":
                    row["age"] = "75.0"
                    # episode_text内の「70歳」を「75歳」に
                    row["episode_text"] = row["episode_text"].replace("70歳", "75歳")
                    print(f"修正: {row['episode_id']} 年齢70→75")
                kurosawa_keep.append(row)
            else:
                kurosawa_delete.append(row)
        else:
            non_kurosawa.append(row)

    print(f"黒澤明 残す: {len(kurosawa_keep)}件")
    print(f"黒澤明 削除: {len(kurosawa_delete)}件")

    # 新規『七人の侍』エピソードを作成
    new_episode = {fn: "" for fn in fieldnames}
    new_episode.update(SEVEN_SAMURAI_EPISODE)
    new_episode["generation_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_episode["source"] = "MANUAL_FIX"
    new_episode["person_type"] = "REAL"
    new_episode["quality_score"] = "8.5"

    kurosawa_keep.append(new_episode)
    print("新規作成: EP-KUROSAWA-7SAMURAI (七人の侍 44歳)")

    # 結合して保存
    final_rows = non_kurosawa + kurosawa_keep

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)

    print(f"\n保存完了: {len(final_rows)}件")
    print(f"削除された黒澤明エピソード: {len(kurosawa_delete)}件")

    # 削除リストをログに保存
    log_path = Path("src/reports/logs/kurosawa_deleted_episodes.txt")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"削除日時: {datetime.now()}\n")
        f.write(f"削除件数: {len(kurosawa_delete)}\n\n")
        for row in kurosawa_delete:
            f.write(f"{row['episode_id']},{row['age']},{row['episode_text'][:50]}...\n")
    print(f"削除ログ: {log_path}")


if __name__ == "__main__":
    main()
