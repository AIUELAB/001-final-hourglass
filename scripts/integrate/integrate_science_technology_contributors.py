#!/usr/bin/env python3
"""
科学技術功労者エピソードをMASTER_EPISODES_CURRENT.csvに統合するスクリプト

使用方法:
    python3 integrate_science_technology_contributors.py
"""

import csv
import sys
from datetime import datetime
from typing import Dict, List

# ファイルパス
SCIENCE_TECHNOLOGY_CSV = "generated/science_technology_contributors_episodes.csv"
MASTER_CSV = "MASTER_EPISODES_CURRENT.csv"


def is_valid_episode(row_dict: Dict[str, str]) -> bool:
    """エピソードが有効かチェック"""
    # person_idが空でないかチェック
    person_id = row_dict.get("person_id", "")
    if not person_id or person_id.strip() == "":
        print("   ❌ 無効（person_id空）")
        return False

    # episode_textが空でないかチェック
    episode_text = row_dict.get("episode_text", "")
    if not episode_text or len(episode_text.strip()) < 100:
        print("   ❌ 無効（episode_text短すぎる）")
        return False

    return True


def check_duplicate(new_row_dict: Dict[str, str], existing_rows: List[List[str]], master_header: List[str]) -> bool:
    """重複チェック（person_id + age の組み合わせ）"""
    new_person_id = new_row_dict.get("person_id", "")
    new_age = new_row_dict.get("age", "")

    person_id_idx = master_header.index("person_id") if "person_id" in master_header else -1
    age_idx = master_header.index("age") if "age" in master_header else -1

    if person_id_idx == -1 or age_idx == -1:
        return False  # インデックスが見つからない場合は重複なしとみなす

    for existing_row in existing_rows:
        if len(existing_row) > max(person_id_idx, age_idx):
            existing_person_id = existing_row[person_id_idx]
            existing_age = existing_row[age_idx]
            if existing_person_id == new_person_id and existing_age == new_age:
                return True  # 重複あり

    return False  # 重複なし


def main():
    print("=" * 80)
    print("科学技術功労者エピソード統合スクリプト")
    print("=" * 80)

    # 科学技術功労者CSV読み込み
    try:
        with open(SCIENCE_TECHNOLOGY_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            science_technology_rows_dict = list(reader)
            science_technology_header = reader.fieldnames
    except FileNotFoundError:
        print(f"❌ 科学技術功労者CSVが見つかりません: {SCIENCE_TECHNOLOGY_CSV}")
        sys.exit(1)

    print(f"\n科学技術功労者エピソード: {len(science_technology_rows_dict)}件")

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
    print(f"現在のエピソード数: {initial_count}件")

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{MASTER_CSV}.backup_{timestamp}"
    with open(backup_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(master_header)
        writer.writerows(master_rows)
    print(f"✅ バックアップ作成: {backup_file}")

    # 統合処理
    added_count = 0
    invalid_count = 0
    duplicate_count = 0

    for row_dict in science_technology_rows_dict:
        person_name = row_dict.get("person_name", "不明")
        age = row_dict.get("age", "?")
        category = row_dict.get("category", "")

        print(f"\nチェック: {person_name} ({age}歳, {category})...", end=" ")

        # バリデーション
        if not is_valid_episode(row_dict):
            invalid_count += 1
            continue

        # 重複チェック
        if check_duplicate(row_dict, master_rows, master_header):
            print("   ⚠️  スキップ（重複）")
            duplicate_count += 1
            continue

        # award_levelが空の場合に"SCIENCE_TECHNOLOGY"を設定
        if not row_dict.get("award_level", "") or row_dict.get("award_level", "").strip() == "":
            row_dict["award_level"] = "SCIENCE_TECHNOLOGY"

        # マスター形式の行を作成
        master_row = []
        for column in master_header:
            if column == "episode_id":
                # episode_idは空にする（後で自動生成される場合）
                master_row.append("")
            elif column == "episode_fame_tier":
                master_row.append("")
            elif column == "episode_fame_score":
                master_row.append("")
            elif column == "episode_fame_score_updated_at":
                master_row.append("")
            elif column in row_dict:
                # 科学技術功労者に存在する列はそのまま使用
                master_row.append(row_dict[column])
            else:
                # 存在しない列は空にする
                master_row.append("")

        master_rows.append(master_row)
        added_count += 1
        print("   ✅ 追加")

    # マスターCSVに書き戻し
    if added_count > 0:
        with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(master_header)
            writer.writerows(master_rows)

        print("\n" + "=" * 80)
        print("📊 統合結果")
        print("=" * 80)
        print(f"初期エピソード数: {initial_count}件")
        print(f"追加: {added_count}件")
        print(f"無効: {invalid_count}件")
        print(f"重複スキップ: {duplicate_count}件")
        print(f"最終エピソード数: {len(master_rows)}件")
        print(f"\n✅ 保存完了: {MASTER_CSV}")

        # award_level統計
        print("\n" + "-" * 80)
        print("award_level統計")
        print("-" * 80)
        award_level_idx = master_header.index("award_level") if "award_level" in master_header else -1
        if award_level_idx != -1:
            nobel_count = sum(1 for row in master_rows if row[award_level_idx] == "NOBEL")
            international_top_count = sum(1 for row in master_rows if row[award_level_idx] == "INTERNATIONAL_TOP")
            international_count = sum(1 for row in master_rows if row[award_level_idx] == "INTERNATIONAL")
            olympic_count = sum(1 for row in master_rows if row[award_level_idx] == "OLYMPIC")
            cultural_merit_count = sum(1 for row in master_rows if row[award_level_idx] == "CULTURAL_MERIT")
            industry_count = sum(1 for row in master_rows if row[award_level_idx] == "INDUSTRY")
            world_championship_count = sum(1 for row in master_rows if row[award_level_idx] == "WORLD_CHAMPIONSHIP")
            literary_award_count = sum(1 for row in master_rows if row[award_level_idx] == "LITERARY_AWARD")
            science_technology_count = sum(1 for row in master_rows if row[award_level_idx] == "SCIENCE_TECHNOLOGY")
            national_count = sum(1 for row in master_rows if row[award_level_idx] == "NATIONAL")
            print(f"NOBEL: {nobel_count}件")
            print(f"INTERNATIONAL_TOP: {international_top_count}件")
            print(f"INTERNATIONAL: {international_count}件")
            print(f"OLYMPIC: {olympic_count}件")
            print(f"CULTURAL_MERIT: {cultural_merit_count}件")
            print(f"INDUSTRY: {industry_count}件")
            print(f"WORLD_CHAMPIONSHIP: {world_championship_count}件")
            print(f"LITERARY_AWARD: {literary_award_count}件")
            print(f"SCIENCE_TECHNOLOGY: {science_technology_count}件")
            print(f"NATIONAL: {national_count}件")

    else:
        print("\n⚠️  追加されたエピソードがありません")
        if invalid_count > 0:
            print(f"無効なエピソード: {invalid_count}件")
        if duplicate_count > 0:
            print(f"重複エピソード: {duplicate_count}件")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
