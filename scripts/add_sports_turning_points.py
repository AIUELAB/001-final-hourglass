#!/usr/bin/env python3
"""
スポーツ転機エピソード追加スクリプト

スポーツ選手の重要な転機エピソードを追加する。
"""

import csv
import hashlib
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

# 追加するエピソード定義
EPISODES_TO_ADD = [
    {
        "person_id": "P7F524A2",
        "person_name": "山本由伸",
        "age": 25,  # 1998年8月17日生、2023年12月21日契約
        "year": 2023,
        "episode_text": "あなたと同じ25歳のとき、山本由伸は2023年12月21日にロサンゼルス・ドジャースと12年総額3億2500万ドル（約460億円）の契約を結びました。日本人投手として史上最高額となるこの契約は、オリックス・バファローズで3年連続沢村賞を受賞し、WBC優勝に貢献した実績が評価されたものです。2024年からMLBでの挑戦を開始し、日本球界を代表する投手として新たな舞台に立つことになりました。",
        "episode_type": "達成",
        "category": "スポーツ",
    },
]


def generate_episode_id() -> str:
    """ユニークなエピソードIDを生成"""
    timestamp = datetime.now().strftime("%y%m%d%H%M%S%f")[:15]
    hash_suffix = hashlib.md5(timestamp.encode()).hexdigest()[:3].upper()
    return f"EP-{timestamp}{hash_suffix}"


def get_age_group(age: int) -> str:
    """年代を算出"""
    if age < 10:
        return "0代"
    elif age >= 90:
        return "90代以上"
    else:
        return f"{(age // 10) * 10}代"


def main(dry_run: bool = True):
    # 既存データ読み込み（BOM対応）
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"=== スポーツ転機エピソード追加 {'(ドライラン)' if dry_run else '(実行)'} ===\n")
    print(f"既存エピソード数: {len(rows)}")

    # 重複チェック: 同じperson_idで類似テキストがあるかチェック
    existing_texts = {}
    for r in rows:
        pid = r.get("person_id", "")
        text = r.get("episode_text", "")
        if pid not in existing_texts:
            existing_texts[pid] = []
        existing_texts[pid].append(text)

    to_add = []
    for ep in EPISODES_TO_ADD:
        # キーワードで重複判定
        key_phrases = ["ドジャース", "3億2500万ドル", "460億円"]
        is_duplicate = False
        for text in existing_texts.get(ep["person_id"], []):
            if any(kw in text for kw in key_phrases):
                is_duplicate = True
                print(f"⏭️ スキップ: {ep['person_name']} (類似EP既存)")
                break
        if not is_duplicate:
            to_add.append(ep)

    print(f"追加予定: {len(to_add)}件\n")

    new_rows = []
    for ep in to_add:
        episode_id = generate_episode_id()

        # 既存レコードから人物情報を取得
        person_rows = [r for r in rows if r["person_id"] == ep["person_id"]]
        if not person_rows:
            print(f"⚠️ {ep['person_name']}: person_id {ep['person_id']} が見つかりません")
            continue

        template = person_rows[0]

        new_row = {k: "" for k in fieldnames}
        new_row["episode_id"] = episode_id
        new_row["person_id"] = ep["person_id"]
        new_row["person_name"] = ep["person_name"]
        new_row["episode_count"] = template.get("episode_count", "1")
        new_row["age"] = str(float(ep["age"]))
        new_row["category"] = ep["category"]
        new_row["char_count"] = str(len(ep["episode_text"]))
        new_row["episode_text"] = ep["episode_text"]
        new_row["episode_type"] = ep["episode_type"]
        new_row["fact_check_result"] = "確認済み"
        new_row["group_name"] = template.get("group_name", "未登録")
        new_row["is_group_member"] = template.get("is_group_member", "False")
        new_row["person_type"] = template.get("person_type", "REAL")
        new_row["quality_score"] = "8.5"
        new_row["source"] = "SPORTS_TURNING_POINT"
        new_row["tier"] = template.get("tier", "WEEK_1")
        new_row["generation_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row["fame_tier"] = template.get("fame_tier", "4.0")
        new_row["人生の節目タグ"] = "壮年期の挑戦" if ep["age"] >= 40 else "若き挑戦"
        new_row["年代"] = get_age_group(ep["age"])
        new_row["celebrity_score_v2"] = template.get("celebrity_score_v2", "")
        new_row["category_original"] = ep["category"]

        new_rows.append(new_row)
        print(f"✓ {ep['person_name']} ({ep['age']}歳, {ep['year']}年)")
        print(f"  ID: {episode_id}")
        print(f"  本文: {ep['episode_text'][:60]}...")
        print()

    if dry_run:
        print("=== ドライラン完了（変更なし） ===")
        return

    # 実行モード: CSVに追記
    rows.extend(new_rows)
    with open(MASTER_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"=== 追加完了: {len(new_rows)}件 ===")
    print(f"新エピソード数: {len(rows)}")


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    main(dry_run)
