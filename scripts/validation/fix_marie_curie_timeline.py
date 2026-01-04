#!/usr/bin/env python3
"""マリー・キュリーのエピソード時系列矛盾修正スクリプト

EP-000004833: 35歳エピソードに39歳・44歳の出来事が混在している問題を修正

修正内容:
- 旧: ピエール死亡(39歳)、教授就任(39歳)、1911年2度目ノーベル賞(44歳)
- 新: 1902年(35歳)のラジウム純粋分離成功を中心としたエピソード
"""

import csv
from pathlib import Path
from datetime import datetime

MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
TARGET_EPISODE_ID = "EP-000004833"

# 修正後のエピソードテキスト（35歳/1902年の出来事として適切な内容）
NEW_EPISODE_TEXT = (
    "あなたと同じ35歳のとき、マリー・キュリーは4年間の過酷な作業の末、"
    "ついに純粋なラジウムの分離に成功した。夫ピエールと共に8トンもの"
    "ピッチブレンド鉱石を処理し続け、わずか0.1グラムの塩化ラジウムを抽出。"
    "この偉業は翌年のノーベル物理学賞受賞へと繋がり、女性科学者として"
    "初めて世界最高の栄誉を手にする道を切り開いた。"
    "困難な研究環境の中で決して諦めなかった彼女の姿勢が、科学史に残る発見を生んだ。"
)


def fix_episode():
    """EP-000004833のエピソードテキストを修正"""
    rows = []
    modified = False
    old_text = None

    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            if row["episode_id"] == TARGET_EPISODE_ID:
                old_text = row["episode_text"]
                row["episode_text"] = NEW_EPISODE_TEXT
                row["char_count"] = str(len(NEW_EPISODE_TEXT))
                row["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # キーフレーズも更新
                row["episode_fame_v5_keyphrase"] = "マリー・キュリー ラジウム 純粋分離 ノーベル賞"
                # 人生の節目タグを更新
                row["人生の節目タグ"] = "発見,受賞"
                modified = True
            rows.append(row)

    if modified:
        with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"✅ {TARGET_EPISODE_ID} を修正しました")
        print(f"\n【修正前】\n{old_text[:200]}...")
        print(f"\n【修正後】\n{NEW_EPISODE_TEXT}")
        print(f"\n文字数: {len(NEW_EPISODE_TEXT)}")
        return True
    else:
        print(f"❌ {TARGET_EPISODE_ID} が見つかりませんでした")
        return False


if __name__ == "__main__":
    fix_episode()
