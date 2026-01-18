#!/usr/bin/env python3
"""
年齢-本文不整合修正スクリプト

修正ロジック:
1. CSVを読み込む
2. 各エピソードの本文(episode_text)から「同じX歳」パターンを抽出してtext_ageを取得
3. age != text_age の場合、age = text_age に更新
4. CSVを保存

パターン例:
- 「あなたと同じ24歳のとき」
- 「同じ53歳のとき」
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"


def create_backup(csv_path: Path, operation: str) -> Path:
    """バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"MASTER_EPISODES_{operation}_{timestamp}.csv"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(csv_path, backup_path)
    return backup_path


def extract_text_age(episode_text: str) -> int | None:
    """
    本文から「同じX歳」パターンを抽出して年齢を返す

    パターン:
    - 「あなたと同じX歳のとき」
    - 「同じX歳のとき」
    """
    if not episode_text or pd.isna(episode_text):
        return None

    # パターン: 「あなたと同じX歳のとき」または「同じX歳のとき」
    pattern = r"(?:あなたと)?同じ(\d+)歳のとき"
    match = re.search(pattern, str(episode_text))

    if match:
        return int(match.group(1))
    return None


def fix_age_text_consistency(dry_run: bool = True) -> dict:
    """
    年齢-本文不整合を修正

    Args:
        dry_run: Trueの場合、実際には保存しない（プレビューのみ）

    Returns:
        修正結果の統計情報
    """
    print("=" * 60)
    print("年齢-本文不整合修正スクリプト")
    print("=" * 60)

    # CSV読み込み
    print(f"\n📂 CSV読み込み中: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, dtype={"episode_id": str})
    print(f"   総レコード数: {len(df):,}")

    # 不整合を検出・修正
    fixes = []

    for idx, row in df.iterrows():
        episode_id = row["episode_id"]
        current_age = row["age"]
        episode_text = row.get("episode_text", "")

        text_age = extract_text_age(episode_text)

        if text_age is not None and pd.notna(current_age):
            current_age_int = int(current_age)
            if current_age_int != text_age:
                fixes.append(
                    {
                        "episode_id": episode_id,
                        "person_name": row.get("person_name", ""),
                        "old_age": current_age_int,
                        "new_age": text_age,
                        "idx": idx,
                    }
                )

    # 結果表示
    print("\n📊 検出結果:")
    print(f"   不整合件数: {len(fixes)}")

    if fixes:
        print("\n📋 修正対象一覧:")
        print("-" * 80)
        for i, fix in enumerate(fixes, 1):
            print(
                f"   {i:2d}. {fix['episode_id']}: {fix['person_name'][:20]:20s} "
                f"age {fix['old_age']:3d} → {fix['new_age']:3d}"
            )
        print("-" * 80)

    # 修正実行
    if not dry_run and fixes:
        print("\n🔧 修正実行中...")

        # バックアップ作成
        backup_path = create_backup(MASTER_CSV, "age_text_consistency")
        print(f"   バックアップ作成: {backup_path.name}")

        # 修正適用
        for fix in fixes:
            df.at[fix["idx"], "age"] = fix["new_age"]

        # 保存
        df.to_csv(MASTER_CSV, index=False)
        print(f"   ✅ CSV保存完了: {MASTER_CSV}")
    elif dry_run:
        print("\n⚠️ ドライラン: 実際の修正は行いません")
        print("   実行するには --execute オプションを付けてください")

    return {"total_records": len(df), "fixes_count": len(fixes), "fixes": fixes}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="年齢-本文不整合修正スクリプト")
    parser.add_argument("--execute", action="store_true", help="実際に修正を実行する（デフォルトはドライラン）")

    args = parser.parse_args()

    result = fix_age_text_consistency(dry_run=not args.execute)

    print("\n📈 サマリー:")
    print(f"   総レコード数: {result['total_records']:,}")
    print(f"   修正件数: {result['fixes_count']}")

    if args.execute and result["fixes_count"] > 0:
        print("\n✅ 修正完了!")


if __name__ == "__main__":
    main()
