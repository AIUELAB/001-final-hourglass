#!/usr/bin/env python3
"""
エピソード重要度スコアリングシステム

新規カラムを追加し、石ノ森章太郎の4つのエピソードにスコアを適用します。

使用方法:
    python3 add_importance_scores.py
"""

import csv
import sys
from datetime import datetime
from typing import Dict, List

# ファイルパス
MASTER_CSV = "MASTER_EPISODES_CURRENT.csv"

# 石ノ森章太郎のスコア（Step 4で設計した値）
ISHINOMORI_SCORES = {
    "P596E029_58": {  # エピソード1: ギネス記録
        "historical_significance_score": 10.0,
        "verifiability_score": 10.0,
        "cultural_impact_score": 9.0,
        "essential_insight_score": 9.0,
        "temporal_permanence_score": 10.0,
        "episode_importance_score": 9.65,
    },
    "P596E029_26": {  # エピソード2: サイボーグ009
        "historical_significance_score": 9.0,
        "verifiability_score": 9.0,
        "cultural_impact_score": 8.0,
        "essential_insight_score": 8.0,
        "temporal_permanence_score": 10.0,
        "episode_importance_score": 8.80,
    },
    "P596E029_33": {  # エピソード3: 仮面ライダー
        "historical_significance_score": 10.0,
        "verifiability_score": 9.0,
        "cultural_impact_score": 10.0,
        "essential_insight_score": 8.0,
        "temporal_permanence_score": 10.0,
        "episode_importance_score": 9.50,
    },
    "P596E029_21": {  # エピソード4: 姉の死
        "historical_significance_score": 6.0,
        "verifiability_score": 7.0,
        "cultural_impact_score": 7.0,
        "essential_insight_score": 10.0,
        "temporal_permanence_score": 9.0,
        "episode_importance_score": 7.65,
    },
}

# 新規カラム
NEW_COLUMNS = [
    "historical_significance_score",
    "verifiability_score",
    "cultural_impact_score",
    "essential_insight_score",
    "temporal_permanence_score",
    "episode_importance_score",
]


def main():
    print("=" * 80)
    print("エピソード重要度スコアリングシステム")
    print("=" * 80)

    # マスターCSV読み込み
    try:
        with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            original_header = reader.fieldnames
            rows = list(reader)
    except FileNotFoundError:
        print(f"❌ マスターCSVが見つかりません: {MASTER_CSV}")
        sys.exit(1)

    print(f"\n現在のエピソード数: {len(rows)}件")
    print(f"現在のカラム数: {len(original_header)}列")

    # 新規カラムの確認
    existing_new_columns = [col for col in NEW_COLUMNS if col in original_header]
    if existing_new_columns:
        print(f"\n⚠️  以下のカラムは既に存在します: {existing_new_columns}")
    else:
        print(f"\n✅ 新規カラムを追加します: {NEW_COLUMNS}")

    # 新しいヘッダーを作成（category_originalの直後に挿入）
    if "category_original" in original_header:
        insert_idx = original_header.index("category_original") + 1
    else:
        insert_idx = len(original_header)

    new_header = list(original_header[:insert_idx])
    for col in NEW_COLUMNS:
        if col not in original_header:
            new_header.append(col)
    new_header.extend(original_header[insert_idx:])

    # 重複排除
    seen = set()
    final_header = []
    for col in new_header:
        if col not in seen:
            final_header.append(col)
            seen.add(col)

    print(f"更新後のカラム数: {len(final_header)}列")

    # バックアップ作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{MASTER_CSV}.backup_{timestamp}"
    with open(backup_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=original_header)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ バックアップ作成: {backup_file}")

    # スコアの適用
    updated_count = 0
    for row in rows:
        person_id = row.get("person_id", "")
        age = row.get("age", "")
        key = f"{person_id}_{age}"

        if key in ISHINOMORI_SCORES:
            scores = ISHINOMORI_SCORES[key]
            for score_name, score_value in scores.items():
                row[score_name] = str(score_value)
            updated_count += 1
            print(
                f"✅ スコア適用: {row.get('person_name', '?')} ({age}歳) - 重要度={scores['episode_importance_score']}"
            )
        else:
            # 新規カラムに空文字を設定
            for col in NEW_COLUMNS:
                if col not in row:
                    row[col] = ""

    # マスターCSVに書き戻し
    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=final_header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 80)
    print("📊 更新結果")
    print("=" * 80)
    print(f"スコア適用エピソード数: {updated_count}件")
    print(f"最終カラム数: {len(final_header)}列")
    print(f"\n✅ 保存完了: {MASTER_CSV}")

    # 石ノ森章太郎エピソードのスコアサマリー
    if updated_count > 0:
        print("\n" + "-" * 80)
        print("石ノ森章太郎エピソード重要度スコア")
        print("-" * 80)
        total_importance = 0.0
        for key, scores in ISHINOMORI_SCORES.items():
            total_importance += scores["episode_importance_score"]
        avg_importance = total_importance / len(ISHINOMORI_SCORES)
        print(f"平均重要度スコア: {avg_importance:.2f}点 / 10.00点")
        print("最高スコア: 9.65点 (ギネス世界記録)")
        print("最低スコア: 7.65点 (姉の死)")
        print("スコア範囲: 2.00点")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
