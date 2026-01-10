"""
birth_year/death_year カラム追加スクリプト V2

エピソードテキストから年を抽出し、
age と組み合わせて birth_year を計算。

使用法:
    python scripts/data/add_birth_death_years_v2.py [--dry-run]
"""

import argparse
import logging
import re
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# 有名人の既知の生没年（手動追加）
KNOWN_BIRTH_DEATH = {
    "トニー・ベネット": (1926, 2023),
    "クリント・イーストウッド": (1930, None),  # 存命
    "ジェーン・グドール": (1934, None),  # 存命
    "ショーン・コネリー": (1930, 2020),
    "岸信介": (1896, 1987),
    "ジョン・グッドイナフ": (1922, 2023),
    "朝比奈隆": (1908, 2001),
    "ジョアン・ミロ": (1893, 1983),
    "トーマス・ホッブズ": (1588, 1679),
    "ジュリア・チャイルド": (1912, 2004),
    "市川崑": (1915, 2008),
    "武良布枝": (1932, 2023),
    "中曽根康弘": (1918, 2019),
    "ヘンリー・キッシンジャー": (1923, 2023),
    "成田きん": (1892, 2000),
    "オリヴィア・デ・ハヴィランド": (1916, 2020),
    "ディック・ヴァン・ダイク": (1925, None),  # 存命
    "三笠宮崇仁": (1915, 2016),
    "カーク・ダグラス": (1916, 2020),
    "飯田深雪": (1903, 2007),
    "日野原重明": (1911, 2017),
    "金子みすゞ": (1903, 1930),
    "アルフレッド・ヒッチコック": (1899, 1980),
    "パブロ・ピカソ": (1881, 1973),
    "チャールズ・シュルツ": (1922, 2000),
    "ネルソン・マンデラ": (1918, 2013),
    "エリザベス2世": (1926, 2022),
    "アルベルト・シュヴァイツァー": (1875, 1965),
    "ジャンヌ・カルマン": (1875, 1997),  # 世界最高齢記録
    "渋沢栄一": (1840, 1931),
    "聖路加国際病院の日野原先生": (1911, 2017),
    "ジミー・カーター": (1924, None),  # 存命
}


def extract_year_from_text(text: str) -> list:
    """エピソードテキストから年を抽出"""
    if pd.isna(text):
        return []
    years = re.findall(r"(1[89]\d{2}|20[0-2]\d)年?", str(text))
    return [int(y) for y in years if 1500 <= int(y) <= 2026]


def estimate_birth_death(df: pd.DataFrame) -> pd.DataFrame:
    """各人物のbirth_year/death_yearを推定"""
    logger.info("birth_year/death_year推定開始")

    # 人物ごとの統計
    person_data = []

    for pid, group in df.groupby("person_id"):
        name = group["person_name"].iloc[0]
        person_type = group["person_type"].iloc[0] if "person_type" in group.columns else "REAL"

        # 架空人物は除外
        if person_type != "REAL":
            continue

        max_age = int(group["age"].max())
        min_age = int(group["age"].min())

        # 既知のデータをチェック
        if name in KNOWN_BIRTH_DEATH:
            birth, death = KNOWN_BIRTH_DEATH[name]
            person_data.append(
                {
                    "person_id": pid,
                    "person_name": name,
                    "birth_year": birth,
                    "death_year": death,
                    "max_age": max_age,
                    "source": "known",
                }
            )
            continue

        # エピソードテキストから年を抽出
        all_years = []
        for _, row in group.iterrows():
            years = extract_year_from_text(row.get("episode_text", ""))
            all_years.extend(years)

        if not all_years:
            continue

        # 最も頻出する年 or 最大年齢エピソードの年から推定
        max_age_row = group[group["age"] == max_age].iloc[0]
        max_age_years = extract_year_from_text(max_age_row.get("episode_text", ""))

        if max_age_years:
            # 最大年齢エピソードの年から birth_year を計算
            episode_year = max(max_age_years)  # 最も新しい年
            birth_year = episode_year - max_age
            death_year = episode_year if max_age >= 85 else None  # 85歳以上なら没年と推定

            person_data.append(
                {
                    "person_id": pid,
                    "person_name": name,
                    "birth_year": birth_year,
                    "death_year": death_year,
                    "max_age": max_age,
                    "source": "calculated",
                }
            )

    result_df = pd.DataFrame(person_data)
    logger.info(f"推定成功: {len(result_df)}人")

    # 長寿人物統計
    long_lived = result_df[result_df["max_age"] >= 90]
    logger.info(f"90歳以上: {len(long_lived)}人")

    return result_df


def add_columns_to_master(df: pd.DataFrame, estimates: pd.DataFrame) -> pd.DataFrame:
    """マスターCSVにbirth_year/death_yearカラムを追加"""

    # カラム追加
    if "birth_year" not in df.columns:
        df["birth_year"] = None
    if "death_year" not in df.columns:
        df["death_year"] = None

    # 推定値をマッピング
    estimate_map = estimates.set_index("person_id")[["birth_year", "death_year"]].to_dict("index")

    updated_count = 0
    for idx, row in df.iterrows():
        pid = row["person_id"]
        if pid in estimate_map:
            est = estimate_map[pid]
            df.at[idx, "birth_year"] = est["birth_year"]
            df.at[idx, "death_year"] = est["death_year"]
            updated_count += 1

    logger.info(f"更新行数: {updated_count}")
    return df


def main():
    parser = argparse.ArgumentParser(description="birth_year/death_yearカラム追加 V2")
    parser.add_argument("--dry-run", action="store_true", help="変更を保存しない")
    args = parser.parse_args()

    logger.info("=== birth_year/death_year カラム追加 V2 ===")

    # マスターCSV読み込み
    logger.info(f"読み込み: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    logger.info(f"行数: {len(df)}")

    # 推定
    estimates = estimate_birth_death(df)

    # カラム追加
    df_updated = add_columns_to_master(df.copy(), estimates)

    # 統計
    has_birth = df_updated["birth_year"].notna().sum()
    logger.info(f"birth_year設定済み: {has_birth}行")

    # サンプル表示（長寿人物）
    logger.info("")
    logger.info("=== 長寿人物 (90歳以上) ===")
    long_lived = estimates[estimates["max_age"] >= 90].sort_values("max_age", ascending=False)
    for _, row in long_lived.head(15).iterrows():
        name = row["person_name"]
        birth = int(row["birth_year"]) if pd.notna(row["birth_year"]) else "?"
        death = int(row["death_year"]) if pd.notna(row["death_year"]) else "存命"
        max_age = int(row["max_age"])
        src = row["source"]
        print(f"  {name}: {birth}-{death} (max {max_age}歳) [{src}]")

    if args.dry_run:
        logger.info("")
        logger.info("[DRY-RUN] 変更は保存されません")
        logger.info("実行するには: python scripts/data/add_birth_death_years_v2.py")
    else:
        # バックアップ
        backup_path = MASTER_CSV.parent / "MASTER_EPISODES_BACKUP_pre_birthyear.csv"
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        logger.info(f"バックアップ: {backup_path}")

        # 保存
        df_updated.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"保存完了: {MASTER_CSV}")

    return 0


if __name__ == "__main__":
    main()
