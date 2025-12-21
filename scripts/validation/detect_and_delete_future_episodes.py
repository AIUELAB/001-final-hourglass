#!/usr/bin/env python3
"""
未来エピソードを検出・削除するスクリプト

生年データベースを使用して、未来の年齢に基づくエピソードを検出し、
オプションで削除または年齢調整を行う
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.birth_year_database import (
    BIRTH_YEARS,
    CURRENT_YEAR,
    get_birth_year,
)

# パス設定
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backup"
REPORTS_DIR = PROJECT_ROOT / "reports"


def detect_future_episodes(df: pd.DataFrame) -> list[dict]:
    """
    未来エピソードを検出

    Args:
        df: エピソードのDataFrame

    Returns:
        未来エピソードのリスト
    """
    future_episodes = []

    for idx, row in df.iterrows():
        person_name = row.get("person_name", "")
        person_type = row.get("person_type", "REAL")
        age = row.get("age")

        # 架空キャラクターはスキップ
        if person_type != "REAL":
            continue

        # 年齢が設定されていない場合はスキップ
        if pd.isna(age):
            continue

        age = int(age)
        birth_year = get_birth_year(person_name)

        if birth_year is None:
            continue

        episode_year = birth_year + age
        max_valid_age = CURRENT_YEAR - birth_year

        if episode_year > CURRENT_YEAR:
            future_episodes.append(
                {
                    "index": idx,
                    "episode_id": row.get("episode_id", ""),
                    "person_name": person_name,
                    "age": age,
                    "birth_year": birth_year,
                    "episode_year": episode_year,
                    "max_valid_age": max_valid_age,
                    "years_in_future": episode_year - CURRENT_YEAR,
                    "episode_type": row.get("episode_type", ""),
                    "episode_fame_score": row.get("episode_fame_score", 0),
                    "episode_text_preview": str(row.get("episode_text", ""))[:100],
                }
            )

    return future_episodes


def delete_future_episodes(df: pd.DataFrame, future_episodes: list[dict], dry_run: bool = True) -> pd.DataFrame:
    """
    未来エピソードを削除

    Args:
        df: エピソードのDataFrame
        future_episodes: 削除対象のエピソードリスト
        dry_run: ドライランモード

    Returns:
        処理後のDataFrame
    """
    if not future_episodes:
        print("削除対象の未来エピソードはありません")
        return df

    indices_to_delete = [ep["index"] for ep in future_episodes]

    if dry_run:
        print(f"\n[ドライラン] 削除対象: {len(indices_to_delete)}件")
        return df

    # 削除実行
    df_cleaned = df.drop(indices_to_delete)
    print(f"\n削除完了: {len(indices_to_delete)}件")

    return df_cleaned


def main():
    parser = argparse.ArgumentParser(description="未来エピソードを検出・削除")
    parser.add_argument("--input", default=str(MASTER_CSV), help="入力CSVファイル")
    parser.add_argument("--execute", action="store_true", help="実際に削除を実行")
    parser.add_argument("--output-report", default=None, help="レポート出力先")
    args = parser.parse_args()

    print("=" * 70)
    print("🔍 未来エピソード検出・削除ツール")
    print("=" * 70)
    print(f"現在の年: {CURRENT_YEAR}")
    print(f"生年データベース: {len(BIRTH_YEARS)}人登録")
    print(f"入力ファイル: {args.input}")
    print(f"実行モード: {'実行' if args.execute else 'ドライラン'}")
    print()

    # データ読み込み
    df = pd.read_csv(args.input, encoding="utf-8-sig")
    print(f"総エピソード数: {len(df):,}件")

    # 未来エピソード検出
    print("\n未来エピソードを検出中...")
    future_episodes = detect_future_episodes(df)
    print(f"検出された未来エピソード: {len(future_episodes)}件")

    if future_episodes:
        print("\n=== 検出された未来エピソード ===")
        for ep in future_episodes:
            print(f"\n🚨 {ep['episode_id']} | {ep['person_name']} {ep['age']}歳")
            print(f"   生年: {ep['birth_year']}年")
            print(f"   エピソード年: {ep['episode_year']}年（{ep['years_in_future']}年後）")
            print(f"   最大有効年齢: {ep['max_valid_age']}歳")
            print(f"   タイプ: {ep['episode_type']} | fame: {ep['episode_fame_score']}")
            print(f"   内容: {ep['episode_text_preview']}...")

    if not args.execute:
        print("\n" + "=" * 70)
        print("ドライランモード: 実際の削除は行いません")
        print("削除を実行するには --execute オプションを付けてください")
        print("=" * 70)

        # レポート出力
        if args.output_report or future_episodes:
            REPORTS_DIR.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = args.output_report or str(REPORTS_DIR / f"future_episodes_detection_{timestamp}.json")

            report = {
                "timestamp": timestamp,
                "current_year": CURRENT_YEAR,
                "total_episodes": len(df),
                "future_episodes_count": len(future_episodes),
                "future_episodes": future_episodes,
            }

            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\nレポート出力: {report_path}")

        return

    # 実行モード
    if not future_episodes:
        print("\n削除対象の未来エピソードはありません")
        return

    # バックアップ作成
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_before_future_delete_{timestamp}.csv"
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"\nバックアップ作成: {backup_path}")

    # 削除実行
    df_cleaned = delete_future_episodes(df, future_episodes, dry_run=False)

    # 保存
    df_cleaned.to_csv(args.input, index=False, encoding="utf-8-sig")
    print(f"保存完了: {args.input}")
    print(f"削除後のエピソード数: {len(df_cleaned):,}件")

    # レポート出力
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"future_episodes_deleted_{timestamp}.json"

    report = {
        "timestamp": timestamp,
        "current_year": CURRENT_YEAR,
        "total_episodes_before": len(df),
        "total_episodes_after": len(df_cleaned),
        "deleted_count": len(future_episodes),
        "deleted_episodes": future_episodes,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"レポート出力: {report_path}")

    print("\n" + "=" * 70)
    print("✅ 未来エピソードの削除が完了しました")
    print("=" * 70)


if __name__ == "__main__":
    main()
