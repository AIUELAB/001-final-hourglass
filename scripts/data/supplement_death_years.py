#!/usr/bin/env python3
"""
death_year補完スクリプト

90歳以上まで生きた有名人物のdeath_yearを補完し、
SAGE候補プールを拡大する。

Usage:
    python scripts/data/supplement_death_years.py [--dry-run]
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# 90歳以上まで生きた有名人物 (person_name: (birth_year, death_year))
# Wikipedia等から確認済みのデータ
LONG_LIVED_PERSONS = {
    # 日本人 (90歳以上)
    "笹川良一": (1899, 1995),  # 96歳
    "いかりや長介": (1931, 2004),  # 72歳 - 除外
    "瀬戸内寂聴": (1922, 2021),  # 99歳
    "森光子": (1920, 2012),  # 92歳
    "千代の富士貢": (1955, 2016),  # 61歳 - 除外
    "吉永小百合": (1945, None),  # 存命
    "仲代達矢": (1932, None),  # 存命 92歳
    "草笛光子": (1933, None),  # 存命 92歳
    "黒柳徹子": (1933, None),  # 存命 92歳
    "淡路恵子": (1933, 2014),  # 80歳 - 除外
    "森繁久彌": (1913, 2009),  # 96歳
    "宇野千代": (1897, 1996),  # 98歳
    "大野伴睦": (1890, 1964),  # 74歳 - 除外
    "岸信介": (1896, 1987),  # 90歳
    "福田赳夫": (1905, 1995),  # 90歳
    "宮澤喜一": (1919, 2007),  # 87歳 - 除外
    "竹下登": (1924, 2000),  # 76歳 - 除外
    "中曽根康弘": (1918, 2019),  # 101歳 (既存)
    "村山富市": (1924, 2023),  # 98歳
    "海部俊樹": (1931, 2022),  # 91歳
    "奥野誠亮": (1913, 2016),  # 103歳 (既存)
    "後藤田正晴": (1914, 2005),  # 91歳
    "野中広務": (1925, 2018),  # 92歳
    "渡辺恒雄": (1926, None),  # 存命 99歳
    "日野原重明": (1911, 2017),  # 105歳
    "聖路加国際病院の日野原先生": (1911, 2017),  # 別名義
    "飯田深雪": (1903, 2007),  # 104歳
    "蟹江ぎん": (1892, 2001),  # 109歳 (きんさんぎんさん)
    "岸本忠三": (1939, None),  # 存命
    # 海外 (90歳以上)
    "ジョージ・バーンズ": (1896, 1996),  # 100歳
    "ボブ・ホープ": (1903, 2003),  # 100歳
    "ジャンヌ・カルマン": (1875, 1997),  # 122歳 世界最高齢
    "オリヴィア・デ・ハヴィランド": (1916, 2020),  # 104歳
    "カーク・ダグラス": (1916, 2020),  # 103歳
    "ベティ・ホワイト": (1922, 2021),  # 99歳
    "シドニー・ポワチエ": (1927, 2022),  # 94歳
    "ハリー・ベラフォンテ": (1927, 2023),  # 96歳
    "トニー・ベネット": (1926, 2023),  # 97歳
    "ヘンリー・キッシンジャー": (1923, 2023),  # 100歳
    "ジミー・カーター": (1924, 2024),  # 100歳 (最近死去)
    "ノーマン・リア": (1922, 2023),  # 101歳
    "ゴードン・ムーア": (1929, 2023),  # 94歳
    "チャーリー・マンガー": (1924, 2023),  # 99歳
    "エリザベス2世": (1926, 2022),  # 96歳
    "フィリップ殿下": (1921, 2021),  # 99歳
    "ネルソン・マンデラ": (1918, 2013),  # 95歳
    "デズモンド・ツツ": (1931, 2021),  # 90歳
    "教皇ベネディクト16世": (1927, 2022),  # 95歳
    "ミハイル・ゴルバチョフ": (1931, 2022),  # 91歳
    "ジャン=リュック・ゴダール": (1930, 2022),  # 91歳
    "アニエス・ヴァルダ": (1928, 2019),  # 90歳
    "スタンリー・キューブリック": (1928, 1999),  # 70歳 - 除外
    "クリント・イーストウッド": (1930, None),  # 存命 95歳
    "ジェーン・グドール": (1934, None),  # 存命 91歳
    "デヴィッド・アッテンボロー": (1926, None),  # 存命 99歳
    "シャーリー・テンプル": (1928, 2014),  # 85歳 - 除外
    "ドリス・デイ": (1922, 2019),  # 97歳
    "アンジェラ・ランズベリー": (1925, 2022),  # 96歳
    "クリストファー・プラマー": (1929, 2021),  # 91歳
    "ジーン・ハックマン": (1930, None),  # 存命 95歳
    "マックス・フォン・シドー": (1929, 2020),  # 90歳
    "ショーン・コネリー": (1930, 2020),  # 90歳
    "クリストファー・リー": (1922, 2015),  # 93歳
    "イアン・マッケラン": (1939, None),  # 存命
    "マイケル・ケイン": (1933, None),  # 存命 92歳
    "ジュディ・デンチ": (1934, None),  # 存命 91歳
    "マギー・スミス": (1934, 2024),  # 89歳 - 除外
    "ロバート・レッドフォード": (1936, None),  # 存命 89歳
    "ハリソン・フォード": (1942, None),  # 存命
    "ジャック・ニコルソン": (1937, None),  # 存命 88歳
    "モーガン・フリーマン": (1937, None),  # 存命 88歳
    "ダスティン・ホフマン": (1937, None),  # 存命 88歳
    # 科学者・学者
    "ジョン・グッドイナフ": (1922, 2023),  # 100歳
    "フリーマン・ダイソン": (1923, 2020),  # 96歳
    "ジェームズ・ラブロック": (1919, 2022),  # 103歳
    "ロジャー・ペンローズ": (1931, None),  # 存命 94歳
    "エドワード・ウィルソン": (1929, 2021),  # 92歳
    "リタ・レヴィ＝モンタルチーニ": (1909, 2012),  # 103歳
    # 音楽家
    "朝比奈隆": (1908, 2001),  # 93歳
    "小澤征爾": (1935, 2024),  # 88歳 - 除外
    "デイヴ・ブルーベック": (1920, 2012),  # 91歳
    "キース・リチャーズ": (1943, None),  # 存命
    "ポール・マッカートニー": (1942, None),  # 存命
    "リンゴ・スター": (1940, None),  # 存命
    "ミック・ジャガー": (1943, None),  # 存命
    "ボブ・ディラン": (1941, None),  # 存命
    "ハーマン・ウォーク": (1915, 2019),  # 103歳
}


def main():
    parser = argparse.ArgumentParser(description="death_year補完")
    parser.add_argument("--dry-run", action="store_true", help="変更を保存しない")
    args = parser.parse_args()

    logger.info("=== death_year補完スクリプト ===")
    logger.info(f"読み込み: {MASTER_CSV}")

    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    logger.info(f"行数: {len(df)}")

    # 更新カウント
    updated_count = 0
    updated_persons = []

    for person_name, (birth_year, death_year) in LONG_LIVED_PERSONS.items():
        if death_year is None:
            continue  # 存命の場合はスキップ

        # 90歳以上のみ対象
        if death_year - birth_year < 90:
            continue

        # 該当人物を検索
        mask = df["person_name"] == person_name
        if mask.sum() == 0:
            continue

        # 現在のdeath_year確認
        current_death = df.loc[mask, "death_year"].iloc[0]
        if pd.notna(current_death):
            continue  # 既に設定済み

        # 更新
        df.loc[mask, "birth_year"] = birth_year
        df.loc[mask, "death_year"] = death_year
        updated_count += mask.sum()
        max_age = death_year - birth_year
        updated_persons.append(f"{person_name}: {birth_year}-{death_year} ({max_age}歳)")
        logger.info(f"更新: {person_name} → {birth_year}-{death_year} ({max_age}歳)")

    logger.info(f"更新行数: {updated_count}")
    logger.info(f"更新人物: {len(updated_persons)}人")

    if args.dry_run:
        logger.info("[DRY-RUN] 変更は保存されません")
        for p in updated_persons:
            print(f"  {p}")
    else:
        # バックアップ
        backup_path = MASTER_CSV.parent / f"{MASTER_CSV.stem}_pre_death_supplement.csv"
        df_orig = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
        df_orig.to_csv(backup_path, index=False, encoding="utf-8-sig")
        logger.info(f"バックアップ: {backup_path}")

        # 保存
        df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"保存完了: {MASTER_CSV}")

        for p in updated_persons:
            print(f"  {p}")


if __name__ == "__main__":
    main()
