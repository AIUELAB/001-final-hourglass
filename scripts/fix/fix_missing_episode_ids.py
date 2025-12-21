#!/usr/bin/env python3
"""
マスターCSVのエピソードID欠落を修復するスクリプト
"""

import csv
import re
from datetime import datetime
from pathlib import Path
import shutil

MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
BACKUP_DIR = Path("backup/master_csv")


def generate_episode_id(base_timestamp: str, counter: int) -> str:
    """エピソードIDを生成"""
    # EP-YYMMDDHHMMSSTTT形式
    return f"EP-{base_timestamp}{counter:03d}"


def fix_missing_episode_ids():
    """エピソードID欠落を修復"""
    # バックアップ作成
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_{timestamp}.csv"
    shutil.copy2(MASTER_CSV, backup_path)
    print(f"✅ バックアップ作成: {backup_path}")

    # ファイル読み込み
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    print(f"📊 総行数: {len(lines)}")

    # 修復処理
    fixed_lines = [lines[0]]  # ヘッダー
    missing_count = 0
    counter = 0
    base_timestamp = datetime.now().strftime("%y%m%d%H%M%S")

    for i, line in enumerate(lines[1:], start=2):
        if line.startswith(","):
            # エピソードID欠落 → 生成
            new_id = generate_episode_id(base_timestamp, counter)
            fixed_line = new_id + line
            fixed_lines.append(fixed_line)
            missing_count += 1
            counter += 1

            if missing_count <= 5:
                print(f"  行{i}: ID付与 → {new_id}")
        else:
            # 正常行
            fixed_lines.append(line)

    # 修復後のファイル書き込み
    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        f.writelines(fixed_lines)

    print("\n✅ 修復完了:")
    print(f"  - エピソードID付与: {missing_count}件")
    print(f"  - 総行数: {len(fixed_lines)}（ヘッダー含む）")
    print(f"  - 総エピソード数: {len(fixed_lines) - 1}")

    return missing_count, len(fixed_lines) - 1


if __name__ == "__main__":
    print("🔧 エピソードID欠落修復スクリプト")
    print("=" * 60)

    try:
        missing_count, total_episodes = fix_missing_episode_ids()

        print("\n📊 修復後の統計:")
        print(f"  - 修復されたエピソード: {missing_count}件")
        print(f"  - 総エピソード数: {total_episodes}件")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback

        traceback.print_exc()
