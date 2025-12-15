#!/usr/bin/env python3
"""
MASTER_EPISODES_CURRENT.csvから既存の受賞者エピソードを特定するスクリプト

使用方法:
    python3 identify_existing_award_episodes.py

出力:
    - レポート: reports/existing_award_episodes_report.txt
    - CSV: reports/existing_award_episodes.csv
"""

import csv
import os
import sys
from collections import defaultdict
from typing import List

MASTER_CSV = "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = "reports"
REPORT_TXT = os.path.join(REPORT_DIR, "existing_award_episodes_report.txt")
REPORT_CSV = os.path.join(REPORT_DIR, "existing_award_episodes.csv")

# 受賞関連キーワード辞書
AWARD_KEYWORDS = {
    "ノーベル賞": [
        "ノーベル賞",
        "ノーベル物理学賞",
        "ノーベル化学賞",
        "ノーベル生理学・医学賞",
        "ノーベル文学賞",
        "ノーベル平和賞",
        "ノーベル経済学賞",
    ],
    "アカデミー賞": [
        "アカデミー賞",
        "オスカー",
        "アカデミー作品賞",
        "アカデミー監督賞",
        "アカデミー主演男優賞",
        "アカデミー主演女優賞",
    ],
    "国際映画祭": [
        "カンヌ",
        "パルムドール",
        "ベルリン",
        "金熊賞",
        "ベネチア",
        "金獅子賞",
    ],
    "グラミー賞": ["グラミー", "Grammy"],
    "エミー賞": ["エミー賞", "Emmy"],
    "トニー賞": ["トニー賞", "Tony"],
    "フィールズ賞": ["フィールズ賞", "フィールズメダル"],
    "プリツカー賞": ["プリツカー賞", "プリツカー建築賞"],
    "チューリング賞": ["チューリング賞"],
    "ラスカー賞": ["ラスカー賞"],
    "京都賞": ["京都賞"],
    "直木賞": ["直木賞"],
    "芥川賞": ["芥川賞"],
    "日本アカデミー賞": ["日本アカデミー賞"],
    "文化勲章": ["文化勲章"],
    "文化功労者": ["文化功労者"],
    "オリンピック": [
        "オリンピック",
        "金メダル",
        "銀メダル",
        "銅メダル",
        "五輪",
    ],
    "ワールドカップ": ["ワールドカップ", "W杯"],
    "その他国際賞": [
        "ブッカー賞",
        "ゴンクール賞",
        "国際ブッカー賞",
        "ホワイトブレッド賞",
    ],
}


def detect_award_in_text(text: str) -> List[str]:
    """テキストから受賞関連キーワードを検出"""
    detected_awards = []
    for award_category, keywords in AWARD_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                detected_awards.append(award_category)
                break  # 1つのカテゴリで複数キーワード検出しても1回だけカウント
    return detected_awards


def analyze_award_level(award_level: str) -> str:
    """award_levelカラムの値を分類"""
    if not award_level or award_level.strip() == "":
        return "EMPTY"
    return award_level.strip()


def main():
    print("=" * 80)
    print("既存受賞者エピソード特定スクリプト")
    print("=" * 80)

    # レポートディレクトリ作成
    os.makedirs(REPORT_DIR, exist_ok=True)

    # MASTER_CSV読み込み
    try:
        with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            master_rows = list(reader)
    except FileNotFoundError:
        print(f"❌ マスターCSVが見つかりません: {MASTER_CSV}")
        sys.exit(1)

    print(f"\n総エピソード数: {len(master_rows)}件")
    print("分析中...")

    # 統計情報収集
    award_episodes = []  # 受賞エピソードのリスト
    award_category_counts = defaultdict(int)  # カテゴリ別カウント
    award_level_counts = defaultdict(int)  # award_levelカラムの統計
    person_awards = defaultdict(list)  # 人物別の受賞リスト

    for row in master_rows:
        episode_text = row.get("episode_text", "")
        award_level = row.get("award_level", "")
        person_name = row.get("person_name", "")
        person_id = row.get("person_id", "")
        age = row.get("age", "")
        category = row.get("category", "")

        # award_levelカラムの統計
        level_type = analyze_award_level(award_level)
        award_level_counts[level_type] += 1

        # テキストから受賞キーワード検出
        detected_awards = detect_award_in_text(episode_text)

        if detected_awards or level_type != "EMPTY":
            # 受賞エピソードとして記録
            award_info = {
                "person_id": person_id,
                "person_name": person_name,
                "age": age,
                "category": category,
                "episode_text": episode_text[:100] + "..." if len(episode_text) > 100 else episode_text,
                "detected_awards": ", ".join(detected_awards) if detected_awards else "なし",
                "award_level": award_level,
                "full_text": episode_text,
            }
            award_episodes.append(award_info)

            # カテゴリ別カウント
            for award_cat in detected_awards:
                award_category_counts[award_cat] += 1
                person_awards[person_name].append(award_cat)

    # レポート生成
    total_award_episodes = len(award_episodes)
    unique_persons = len(person_awards)

    print("\n✅ 分析完了")
    print(f"   受賞エピソード: {total_award_episodes}件")
    print(f"   受賞者数: {unique_persons}名")

    # テキストレポート作成
    with open(REPORT_TXT, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("既存受賞者エピソード分析レポート\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"総エピソード数: {len(master_rows)}件\n")
        f.write(f"受賞関連エピソード: {total_award_episodes}件 ({total_award_episodes/len(master_rows)*100:.1f}%)\n")
        f.write(f"受賞者数: {unique_persons}名\n\n")

        # award_levelカラム統計
        f.write("-" * 80 + "\n")
        f.write("award_levelカラム統計\n")
        f.write("-" * 80 + "\n")
        for level, count in sorted(award_level_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(master_rows) * 100
            f.write(f"  {level:20s}: {count:5d}件 ({percentage:5.1f}%)\n")
        f.write("\n")

        # カテゴリ別統計
        f.write("-" * 80 + "\n")
        f.write("受賞カテゴリ別統計（テキスト検出）\n")
        f.write("-" * 80 + "\n")
        for award_cat, count in sorted(award_category_counts.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {award_cat:20s}: {count:5d}件\n")
        f.write("\n")

        # 人物別受賞リスト（上位30名）
        f.write("-" * 80 + "\n")
        f.write("人物別受賞数（上位30名）\n")
        f.write("-" * 80 + "\n")
        sorted_persons = sorted(person_awards.items(), key=lambda x: len(x[1]), reverse=True)
        for i, (person_name, awards) in enumerate(sorted_persons[:30], 1):
            f.write(f"  {i:2d}. {person_name:20s}: {len(awards)}件 ({', '.join(set(awards))})\n")
        f.write("\n")

    # CSV出力
    csv_fieldnames = [
        "person_id",
        "person_name",
        "age",
        "category",
        "detected_awards",
        "award_level",
        "episode_text",
        "full_text",
    ]

    with open(REPORT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        writer.writeheader()
        writer.writerows(award_episodes)

    # コンソール出力
    print("\n" + "=" * 80)
    print("📊 分析結果サマリー")
    print("=" * 80)
    print(f"総エピソード数: {len(master_rows)}件")
    print(f"受賞関連エピソード: {total_award_episodes}件 ({total_award_episodes/len(master_rows)*100:.1f}%)")
    print(f"受賞者数: {unique_persons}名")

    print("\n主要カテゴリ（上位10件）:")
    for award_cat, count in sorted(award_category_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  • {award_cat:20s}: {count:5d}件")

    print("\n✅ レポート保存完了:")
    print(f"   テキスト: {REPORT_TXT}")
    print(f"   CSV: {REPORT_CSV}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
