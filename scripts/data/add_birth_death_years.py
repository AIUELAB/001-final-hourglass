"""
birth_year/death_year カラム追加スクリプト

マスターCSVに生年・没年カラムを追加し、
既存エピソードから推定する。

使用法:
    python scripts/data/add_birth_death_years.py [--dry-run]
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


def estimate_birth_death_years(df: pd.DataFrame) -> pd.DataFrame:
    """
    既存エピソードデータからbirth_year/death_yearを推定

    推定ロジック:
    1. 各人物の最大年齢(max_age)を取得
    2. エピソードに含まれる年代情報から推定
    3. 架空人物は除外（person_type != 'REAL'）
    """
    logger.info("birth_year/death_year推定開始")

    # 人物ごとの集計
    person_stats = (
        df.groupby("person_id")
        .agg(
            {
                "person_name": "first",
                "person_type": "first",
                "age": ["min", "max"],
                "年代": lambda x: x.dropna().astype(str).tolist(),
            }
        )
        .reset_index()
    )
    person_stats.columns = ["person_id", "person_name", "person_type", "min_age", "max_age", "decades"]

    logger.info(f"人物数: {len(person_stats)}")

    # 実在人物のみ
    real_persons = person_stats[person_stats["person_type"] == "REAL"].copy()
    logger.info(f"実在人物: {len(real_persons)}")

    # 年代情報から生年を推定
    def estimate_birth_from_decades(row):
        """年代リストから生年を推定"""
        decades = row["decades"]
        min_age = row["min_age"]

        if not decades:
            return None

        # 年代文字列から数値抽出
        years = []
        for d in decades:
            try:
                # "1950年代" -> 1955, "1950" -> 1950
                if "年代" in str(d):
                    year = int(str(d).replace("年代", "")) + 5
                elif str(d).isdigit():
                    year = int(d)
                else:
                    continue
                years.append(year)
            except (ValueError, TypeError):
                continue

        if not years:
            return None

        # 最も早い年代での推定
        earliest_year = min(years)
        # 生年 = その年 - その時の年齢（推定）
        # 簡易推定: 最も早い年代での年齢を20-40歳と仮定
        estimated_birth = earliest_year - 30  # 中央値として30歳と仮定

        return estimated_birth

    # 推定実行
    real_persons["estimated_birth_year"] = real_persons.apply(estimate_birth_from_decades, axis=1)

    # max_ageが90以上の人物は確実に長寿
    # death_year = birth_year + max_age として推定
    real_persons["estimated_death_year"] = real_persons.apply(
        lambda row: (row["estimated_birth_year"] + row["max_age"]) if pd.notna(row["estimated_birth_year"]) else None,
        axis=1,
    )

    # 統計
    has_estimates = real_persons[real_persons["estimated_birth_year"].notna()]
    logger.info(f"推定成功: {len(has_estimates)}/{len(real_persons)}人")

    long_lived = has_estimates[has_estimates["max_age"] >= 90]
    logger.info(f"90歳以上まで生きた人物: {len(long_lived)}人")

    return real_persons[["person_id", "estimated_birth_year", "estimated_death_year", "max_age"]]


def add_columns_to_master(df: pd.DataFrame, estimates: pd.DataFrame, dry_run: bool = True) -> pd.DataFrame:
    """マスターCSVにbirth_year/death_yearカラムを追加"""

    # 既存カラムチェック
    if "birth_year" in df.columns:
        logger.warning("birth_yearカラムは既に存在します")
    if "death_year" in df.columns:
        logger.warning("death_yearカラムは既に存在します")

    # カラム追加
    df["birth_year"] = None
    df["death_year"] = None

    # 推定値をマッピング
    estimate_map = estimates.set_index("person_id")[["estimated_birth_year", "estimated_death_year"]].to_dict("index")

    updated_count = 0
    for idx, row in df.iterrows():
        pid = row["person_id"]
        if pid in estimate_map:
            est = estimate_map[pid]
            if pd.notna(est["estimated_birth_year"]):
                df.at[idx, "birth_year"] = int(est["estimated_birth_year"])
                df.at[idx, "death_year"] = (
                    int(est["estimated_death_year"]) if pd.notna(est["estimated_death_year"]) else None
                )
                updated_count += 1

    logger.info(f"更新行数: {updated_count}")

    return df


def main():
    parser = argparse.ArgumentParser(description="birth_year/death_yearカラム追加")
    parser.add_argument("--dry-run", action="store_true", help="変更を保存しない")
    args = parser.parse_args()

    logger.info("=== birth_year/death_year カラム追加 ===")

    # マスターCSV読み込み
    logger.info(f"読み込み: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    logger.info(f"行数: {len(df)}")

    # 推定
    estimates = estimate_birth_death_years(df)

    # カラム追加
    df_updated = add_columns_to_master(df, estimates, dry_run=args.dry_run)

    # 統計
    has_birth = df_updated["birth_year"].notna().sum()
    logger.info(f"birth_year設定済み: {has_birth}行")

    if args.dry_run:
        logger.info("[DRY-RUN] 変更は保存されません")
    else:
        # バックアップ
        backup_path = MASTER_CSV.parent / "MASTER_EPISODES_BACKUP_pre_birthyear.csv"
        df.to_csv(backup_path, index=False, encoding="utf-8-sig")
        logger.info(f"バックアップ: {backup_path}")

        # 保存
        df_updated.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"保存完了: {MASTER_CSV}")

    # サンプル表示
    logger.info("")
    logger.info("=== 長寿人物サンプル ===")
    long_lived = estimates[estimates["max_age"] >= 90].head(10)
    for _, row in long_lived.iterrows():
        pid = row["person_id"]
        name = df[df["person_id"] == pid]["person_name"].iloc[0]
        birth = int(row["estimated_birth_year"]) if pd.notna(row["estimated_birth_year"]) else "?"
        death = int(row["estimated_death_year"]) if pd.notna(row["estimated_death_year"]) else "?"
        max_age = int(row["max_age"])
        print(f"  {name}: {birth}-{death} (max {max_age}歳)")


if __name__ == "__main__":
    main()
