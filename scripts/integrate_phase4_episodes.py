#!/usr/bin/env python3
"""
Phase 4生成エピソードをMASTER_EPISODES_CURRENT.csvに統合するスクリプト
"""

import csv
import sys
from typing import List

# 生成されたCSVファイル
GENERATED_FILES = [
    "generated/literature_batch3_episodes.csv",
    "generated/medicine_health_batch3_episodes.csv",
]

MASTER_CSV = "MASTER_EPISODES_CURRENT.csv"


def is_valid_episode(row: list, expected_columns: int) -> bool:
    """エピソードが有効かチェック"""
    # 列数チェック
    if len(row) != expected_columns:
        return False

    # episode_textにエラーメッセージが含まれているかチェック
    episode_text = row[6] if len(row) > 6 else ""
    error_keywords = [
        "申し訳ございません",
        "エピソードを生成することができません",
        "亡くなっている",
        "もし",
        "ご提案できます",
    ]

    for keyword in error_keywords:
        if keyword in episode_text:
            print(f"   ❌ 無効（エラーメッセージ検出: {keyword}）")
            return False

    # person_idが空でないかチェック
    person_id = row[0] if len(row) > 0 else ""
    if not person_id or person_id.strip() == "":
        print("   ❌ 無効（person_id空）")
        return False

    # episode_textが空でないかチェック
    if not episode_text or len(episode_text.strip()) < 100:
        print("   ❌ 無効（episode_text短すぎる）")
        return False

    return True


def map_generated_to_master(generated_row: list, generated_header: list, master_header: list) -> list:
    """生成されたCSVの行をマスターCSVの形式にマッピング"""
    # 生成されたデータを辞書化
    generated_dict = dict(zip(generated_header, generated_row))

    # マスターCSVの形式で行を作成
    master_row = []
    for column in master_header:
        if column == "episode_id":
            # episode_idは空にする（後で自動生成される）
            master_row.append("")
        elif column == "episode_fame_tier":
            master_row.append("")
        elif column == "episode_fame_score":
            master_row.append("")
        elif column == "episode_fame_score_updated_at":
            master_row.append("")
        elif column in generated_dict:
            # 生成されたCSVに存在する列はそのまま使用
            master_row.append(generated_dict[column])
        else:
            # 存在しない列は空にする
            master_row.append("")

    return master_row


def main():
    print("=" * 80)
    print("Phase 4エピソード統合スクリプト")
    print("=" * 80)

    # マスターCSV読み込み
    try:
        with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            master_header = next(reader)
            master_rows = list(reader)
    except FileNotFoundError:
        print(f"❌ マスターCSVが見つかりません: {MASTER_CSV}")
        sys.exit(1)

    initial_count = len(master_rows)
    print(f"\n現在のエピソード数: {initial_count}件")

    # 各生成ファイルを処理
    total_added = 0
    total_invalid = 0

    for generated_file in GENERATED_FILES:
        print(f"\n処理中: {generated_file}")

        try:
            with open(generated_file, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                generated_header = next(reader)
                generated_rows = list(reader)
        except FileNotFoundError:
            print("   ⚠️  ファイルが見つかりません。スキップします。")
            continue

        print(f"   読み込み: {len(generated_rows)}件")

        # 列数チェック
        expected_columns = len(generated_header)
        added = 0
        invalid = 0

        for row in generated_rows:
            person_name = row[1] if len(row) > 1 else "不明"
            print(f"   チェック: {person_name}...", end=" ")

            if is_valid_episode(row, expected_columns):
                # マスター形式にマッピング
                master_row = map_generated_to_master(row, generated_header, master_header)
                master_rows.append(master_row)
                added += 1
                print("✅ 追加")
            else:
                invalid += 1

        print(f"   結果: {added}件追加、{invalid}件無効")
        total_added += added
        total_invalid += invalid

    # マスターCSVに書き戻し
    if total_added > 0:
        with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(master_header)
            writer.writerows(master_rows)

        print("\n" + "=" * 80)
        print("📊 統合結果")
        print("=" * 80)
        print(f"初期エピソード数: {initial_count}件")
        print(f"追加: {total_added}件")
        print(f"無効: {total_invalid}件")
        print(f"最終エピソード数: {len(master_rows)}件")
        print(f"\n✅ 保存完了: {MASTER_CSV}")
    else:
        print("\n⚠️  追加されたエピソードがありません")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
