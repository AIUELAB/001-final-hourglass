#!/usr/bin/env python3
"""
サンプル評価データ適用スクリプト

sample_fame_evaluation_10.csvの評価をMASTER_EPISODES_CURRENT.csvに適用する
"""

import csv
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


def apply_sample_evaluations():
    """サンプル評価データをメインCSVに適用"""
    sample_csv = Path(__file__).parent / "sample_fame_evaluation_10.csv"
    main_csv = project_root / "MASTER_EPISODES_CURRENT.csv"

    # サンプル評価データを読み込み
    evaluations = {}
    with open(sample_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_name = row["person_name"]
            evaluations[person_name] = {
                "fame_tier": row["fame_tier"],
                "wikipedia_ja": row["wikipedia_ja"],
                "textbook": row["textbook"],
                "award_level": row["award_level"],
                "notoriety": row["notoriety"],
            }

    print(f"✅ サンプル評価データ読み込み: {len(evaluations)}人")

    # メインCSVを更新
    temp_csv = main_csv.with_suffix(".tmp")
    updated_count = 0

    with open(main_csv, "r", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        with open(temp_csv, "w", encoding="utf-8-sig", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                person_name = row["person_name"]

                # サンプル評価データがあれば適用
                if person_name in evaluations:
                    eval_data = evaluations[person_name]
                    row["fame_tier"] = eval_data["fame_tier"]
                    row["wikipedia_ja"] = eval_data["wikipedia_ja"]
                    row["textbook"] = eval_data["textbook"]
                    row["award_level"] = eval_data["award_level"]
                    row["notoriety"] = eval_data["notoriety"]
                    updated_count += 1
                    print(f"  ✅ {person_name}: fame_tier={eval_data['fame_tier']}")

                writer.writerow(row)

    # ファイル置き換え
    temp_csv.replace(main_csv)

    print(f"\n✅ 更新完了: {updated_count}人")
    print("\n次のステップ:")
    print("  python3 backend/scripts/fame_score_calculator.py")
    print("  → スコアを再計算してください")


if __name__ == "__main__":
    apply_sample_evaluations()
