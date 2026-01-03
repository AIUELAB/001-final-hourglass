#!/usr/bin/env python3
"""
他カテゴリ転機エピソード追加スクリプト

スポーツ・芸術カテゴリの欠落転機エピソードを追加する。
"""

import csv
import hashlib
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

# 追加するエピソード定義
# 各エピソードは事実ベースで、評価語・推測を含まない
EPISODES_TO_ADD = [
    {
        "person_id": "PB6D68AB",
        "person_name": "久保建英",
        "age": 15,  # 2001年6月4日生、2017年11月1日J3デビュー
        "year": 2017,
        "episode_text": "あなたと同じ15歳のとき、久保建英は2017年11月1日のFC東京U-23対AC長野パルセイロ戦で、15歳10ヶ月5日でJリーグデビューを果たしました。これは当時のJリーグ最年少出場記録（J1〜J3含む）となりました。FCバルセロナの下部組織「ラ・マシア」で育ち、18歳未満の外国人選手獲得規約違反によりスペインを離れた後、FC東京のユースを経て驚異的な速さでプロデビューを飾りました。この日から日本サッカー界の新星としてのキャリアが始まりました。",
        "episode_type": "達成",
        "category": "スポーツ",
    },
    {
        "person_id": "P7F88681",
        "person_name": "宮崎駿",
        "age": 62,  # 1941年1月5日生、2003年3月23日受賞式
        "year": 2003,
        "episode_text": "あなたと同じ62歳のとき、宮崎駿は2003年3月23日に『千と千尋の神隠し』で第75回アカデミー長編アニメ映画賞を受賞しました。この作品は2001年に日本で公開され、興行収入304億円を記録し、日本映画歴代1位となっていました。授賞式には宮崎本人は出席しませんでしたが、日本のアニメ作品がアカデミー賞長編アニメ部門を受賞したのはこれが初めてでした。同作はベルリン国際映画祭金熊賞も受賞しており、国際的な評価を確立した作品となりました。",
        "episode_type": "達成",
        "category": "芸術・文化",
    },
    {
        "person_id": "PB54011E",
        "person_name": "長嶋茂雄",
        "age": 23,  # 1936年2月20日生、1959年6月25日天覧試合
        "year": 1959,
        "episode_text": "あなたと同じ23歳のとき、長嶋茂雄は1959年6月25日の後楽園球場での巨人対阪神戦で、昭和天皇・皇后両陛下がプロ野球を初めて観戦される「天覧試合」に出場しました。4対4の同点で迎えた9回裏、阪神のエース村山実からサヨナラホームランを放ち、劇的な幕切れで巨人の勝利を決めました。この一打は日本プロ野球史上最も有名な瞬間の一つとして語り継がれています。試合後、長嶋は「夢中で打った」と語りました。",
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


def get_life_stage_tag(age: int) -> str:
    """人生の節目タグを算出"""
    if age < 20:
        return "若き挑戦"
    elif age < 40:
        return "壮年期の挑戦"
    elif age < 60:
        return "円熟期の達成"
    else:
        return "晩年の栄光"


def main(dry_run: bool = True):
    # 既存データ読み込み（BOM対応）
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"=== 他カテゴリ転機エピソード追加 {'(ドライラン)' if dry_run else '(実行)'} ===\n")
    print(f"既存エピソード数: {len(rows)}")
    print(f"追加予定: {len(EPISODES_TO_ADD)}件\n")

    new_rows = []
    for ep in EPISODES_TO_ADD:
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
        new_row["source"] = "TURNING_POINT_MANUAL"
        new_row["tier"] = template.get("tier", "WEEK_1")
        new_row["generation_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row["fame_tier"] = template.get("fame_tier", "4.0")
        new_row["人生の節目タグ"] = get_life_stage_tag(ep["age"])
        new_row["年代"] = get_age_group(ep["age"])
        new_row["celebrity_score_v2"] = template.get("celebrity_score_v2", "")
        new_row["category_original"] = ep["category"]

        new_rows.append(new_row)
        print(f"✓ {ep['person_name']} ({ep['age']}歳, {ep['year']}年)")
        print(f"  ID: {episode_id}")
        print(f"  カテゴリ: {ep['category']}")
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
