#!/usr/bin/env python3
"""
物語整合性違反エピソード削除スクリプト

Type 1: 実在機関言及（架空キャラに NHK/MIT/NASA 等が登場）
Type 2: 架空世界に現代年号（ドラゴンボール/ONE PIECE 等に2024年が登場）
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime

CSV_PATH = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass/preserved/data/MASTER_EPISODES_CURRENT.csv")

# 実在機関パターン
REAL_INSTITUTIONS = [
    "NHK",
    "東京大学",
    "国連",
    "MIT",
    "甲子園",
    "NASA",
    "FBI",
    "CIA",
    "紅白歌合戦",
    "オリンピック",
    "ワールドカップ",
    "ノーベル賞",
    "アカデミー賞",
    "グラミー賞",
]
REAL_INSTITUTIONS_PATTERN = r"(" + "|".join(REAL_INSTITUTIONS) + r")"

# 現代年号パターン（1900-2029年）
MODERN_YEAR_PATTERN = r"(19[0-9]{2}|20[0-2][0-9])年"

# 架空世界作品（work_title で判別）
FICTIONAL_WORLD_WORKS = [
    # SF/ファンタジー世界（現実世界と異なる設定）
    "ドラゴンボール",
    "ONE PIECE",
    "NARUTO",
    "進撃の巨人",
    "スター・ウォーズ",
    "Star Wars",
    "ガンダム",
    "機動戦士ガンダム",
    "ハリー・ポッター",
    "Harry Potter",
    "ロード・オブ・ザ・リング",
    "指輪物語",
    "鋼の錬金術師",
    "ハガレン",
    "ジョジョの奇妙な冒険",
    "ポケットモンスター",
    "ポケモン",
    "遊戯王",
    "ブリーチ",
    "BLEACH",
    "ワンパンマン",
    "僕のヒーローアカデミア",
    "ヒロアカ",
    "呪術廻戦",
    "チェンソーマン",
    "SPY×FAMILY",
    "キングダム",
    "ベルセルク",
    "犬夜叉",
    "るろうに剣心",
    "鬼滅の刃",
    "約束のネバーランド",
    "東京喰種",
    "トーキョーグール",
    "デスノート",
    "コードギアス",
    "エヴァンゲリオン",
    "新世紀エヴァンゲリオン",
    "ファイナルファンタジー",
    "FF",
    "ドラゴンクエスト",
    "ドラクエ",
    "ゼルダの伝説",
    "キングダムハーツ",
    # 追加: 年号検出で残っていた作品
    "幽☆遊☆白書",
    "幽遊白書",
    "聖闘士星矢",
    "ジブリ",
    "となりのトトロ",
    "もののけ姫",
    "千と千尋の神隠し",
    "ハウルの動く城",
    "風の谷のナウシカ",
    "天空の城ラピュタ",
    "ディズニー",
    "Disney",
    "サンリオ",
    "グラップラー刃牙",
    "刃牙",
    "銀魂",
    "ホラー映画",
    "バイオハザード",
    "アンパンマン",
    "リトル・マーメイド",
    "黒子のバスケ",
    "はじめの一歩",
    "スラムダンク",
    "SLAM DUNK",
    "HUNTER×HUNTER",
    "ハンターハンター",
    "北斗の拳",
    "シティーハンター",
    "ルパン三世",
    "名探偵コナン",
    "クレヨンしんちゃん",
    "ドラえもん",
    "サザエさん",
    "ちびまる子ちゃん",
    "ワンピース",
    "FAIRY TAIL",
    "七つの大罪",
    "Re:ゼロ",
    "リゼロ",
    "転生したらスライムだった件",
    "転スラ",
    "ソードアート・オンライン",
    "SAO",
    "この素晴らしい世界に祝福を",
    "このすば",
    "盾の勇者の成り上がり",
    "無職転生",
    "葬送のフリーレン",
    "推しの子",
    "怪獣8号",
]

# 架空世界キャラパターン（person_name で判別）- work_titleがない場合のフォールバック
FICTIONAL_WORLD_CHARS = [
    # ドラゴンボール系
    "孫悟空",
    "悟空",
    "ベジータ",
    "ピッコロ",
    "フリーザ",
    "セル",
    "魔人ブウ",
    "クリリン",
    "ヤムチャ",
    "天津飯",
    "ブルマ",
    "トランクス",
    "孫悟飯",
    # スター・ウォーズ系
    "ルーク・スカイウォーカー",
    "ダース・ベイダー",
    "レイア",
    "ヨーダ",
    "オビ=ワン",
    "アナキン",
    "パルパティーン",
    "ハン・ソロ",
    # ONE PIECE系
    "モンキー・D・ルフィ",
    "ルフィ",
    "ロロノア・ゾロ",
    "ゾロ",
    "ナミ",
    "サンジ",
    "トニートニー・チョッパー",
    "ニコ・ロビン",
    "フランキー",
    "ブルック",
    "ジンベエ",
    "ポートガス・D・エース",
    "シャンクス",
    "トラファルガー・ロー",
    # 進撃の巨人
    "エレン・イェーガー",
    "ミカサ・アッカーマン",
    "アルミン",
    "リヴァイ",
    # NARUTO
    "うずまきナルト",
    "うちはサスケ",
    "春野サクラ",
    "はたけカカシ",
    # 鬼滅の刃
    "竈門炭治郎",
    "竈門禰豆子",
    "我妻善逸",
    "嘴平伊之助",
    "煉獄杏寿郎",
    "栗花落カナヲ",
    "冨岡義勇",
    "胡蝶しのぶ",
    # エヴァンゲリオン
    "碇シンジ",
    "綾波レイ",
    "惣流・アスカ",
    "碇ゲンドウ",
    # ガンダム
    "アムロ・レイ",
    "シャア・アズナブル",
    # ハリー・ポッター
    "ハリー・ポッター",
    "ハーマイオニー",
    "ロン・ウィーズリー",
    # その他
    "ゴン・フリークス",
    "キルア",
    "クラピカ",  # ハンターハンター
    "夜神月",
    "L",  # デスノート
]


def get_content(row):
    """episode_content または episode_text からコンテンツを取得"""
    content = row.get("episode_content", "")
    if pd.isna(content) or str(content).strip() == "":
        content = row.get("episode_text", "")
    return str(content) if pd.notna(content) else ""


def is_fictional_world_char(row):
    """架空世界キャラかどうかを判定"""
    work_title = str(row.get("work_title", ""))
    person_name = str(row.get("person_name", ""))

    # work_title で判定
    for work in FICTIONAL_WORLD_WORKS:
        if work.lower() in work_title.lower():
            return True

    # person_name で判定（フォールバック）
    for char in FICTIONAL_WORLD_CHARS:
        if char in person_name:
            return True

    return False


def main():
    print("=" * 70)
    print("物語整合性違反エピソード削除スクリプト")
    print("=" * 70)
    print(f"\n開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # CSV読み込み
    print(f"\nCSV読み込み中: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", low_memory=False)
    original_count = len(df)
    print(f"元のエピソード数: {original_count:,}")

    # 架空キャラのみ抽出
    fictional_df = df[df["person_type"] == "FICTIONAL"].copy()
    fictional_count = len(fictional_df)
    print(f"架空キャラエピソード数: {fictional_count:,}")

    # 違反検出
    type1_violations = []  # 実在機関言及
    type2_violations = []  # 現代年号

    for idx, row in fictional_df.iterrows():
        content = get_content(row)
        text = str(row.get("episode_text", "")) if pd.notna(row.get("episode_text")) else ""
        combined_content = content + " " + text  # 両方チェック
        person_name = str(row.get("person_name", ""))
        episode_id = row.get("episode_id", "")

        # Type 1: 実在機関言及チェック（全架空キャラ対象）
        if re.search(REAL_INSTITUTIONS_PATTERN, combined_content):
            matches = re.findall(REAL_INSTITUTIONS_PATTERN, combined_content)
            type1_violations.append(
                {
                    "episode_id": episode_id,
                    "person_name": person_name,
                    "violation_type": "実在機関言及",
                    "matched": ", ".join(set(matches)),
                }
            )

        # Type 2: 架空世界キャラ + 現代年号チェック
        if is_fictional_world_char(row):
            if re.search(MODERN_YEAR_PATTERN, combined_content):
                matches = re.findall(MODERN_YEAR_PATTERN, combined_content)
                type2_violations.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "violation_type": "架空世界現代年号",
                        "matched": ", ".join(set(matches)),
                    }
                )

    # 削除対象ID収集
    violation_ids = set()
    violation_ids.update([v["episode_id"] for v in type1_violations])
    violation_ids.update([v["episode_id"] for v in type2_violations])

    print("\n" + "=" * 70)
    print("検出結果")
    print("=" * 70)
    print(f"Type 1 (実在機関言及): {len(type1_violations):,} 件")
    print(f"Type 2 (架空世界現代年号): {len(type2_violations):,} 件")
    print(f"合計削除対象（重複除く）: {len(violation_ids):,} 件")

    # サンプル表示
    print("\n--- Type 1 サンプル (最大10件) ---")
    for v in type1_violations[:10]:
        print(f"  {v['episode_id']}: {v['person_name']} - {v['matched']}")

    print("\n--- Type 2 サンプル (最大10件) ---")
    for v in type2_violations[:10]:
        print(f"  {v['episode_id']}: {v['person_name']} - {v['matched']}")

    # 削除実行
    if violation_ids:
        print("\n削除実行中...")
        df_cleaned = df[~df["episode_id"].isin(violation_ids)]
        new_count = len(df_cleaned)
        deleted_count = original_count - new_count

        # CSV保存
        df_cleaned.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"\n保存完了: {CSV_PATH}")
        print(f"削除件数: {deleted_count:,}")
        print(f"残りエピソード数: {new_count:,}")
    else:
        print("\n削除対象なし")

    # 詳細レポート出力
    report_path = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass/src/reports/narrative_fix_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 物語整合性違反修正レポート\n\n")
        f.write(f"**実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## サマリー\n\n")
        f.write("| 項目 | 件数 |\n")
        f.write("|------|------|\n")
        f.write(f"| 元のエピソード数 | {original_count:,} |\n")
        f.write(f"| Type 1 (実在機関言及) | {len(type1_violations):,} |\n")
        f.write(f"| Type 2 (架空世界現代年号) | {len(type2_violations):,} |\n")
        f.write(f"| 削除合計（重複除く） | {len(violation_ids):,} |\n")
        f.write(f"| 残りエピソード数 | {original_count - len(violation_ids):,} |\n")

        f.write("\n## Type 1: 実在機関言及 詳細\n\n")
        if type1_violations:
            f.write("| episode_id | person_name | 検出された機関 |\n")
            f.write("|------------|-------------|----------------|\n")
            for v in type1_violations:
                f.write(f"| {v['episode_id']} | {v['person_name']} | {v['matched']} |\n")
        else:
            f.write("該当なし\n")

        f.write("\n## Type 2: 架空世界現代年号 詳細\n\n")
        if type2_violations:
            f.write("| episode_id | person_name | 検出された年号 |\n")
            f.write("|------------|-------------|----------------|\n")
            for v in type2_violations:
                f.write(f"| {v['episode_id']} | {v['person_name']} | {v['matched']} |\n")
        else:
            f.write("該当なし\n")

    print(f"\nレポート保存: {report_path}")
    print("\n完了!")

    return {
        "type1_count": len(type1_violations),
        "type2_count": len(type2_violations),
        "total_deleted": len(violation_ids),
        "remaining": original_count - len(violation_ids),
    }


if __name__ == "__main__":
    main()
