#!/usr/bin/env python3
"""
有名度スコア算出スクリプト

Final Hourglass プロジェクト
MASTER_EPISODES_CURRENT.csvに有名度関連カラムを追加し、スコアを計算する
"""

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


def calculate_fame_score(person: Dict[str, str]) -> int:
    """
    有名度スコアを計算

    Args:
        person: 人物データ辞書
            - fame_tier: 知名度ティア (1-5)
            - wikipedia_ja: Wikipedia有無 (TRUE/FALSE)
            - textbook: 教科書掲載 (TRUE/FALSE)
            - award_level: 受賞歴レベル (0-3)
            - notoriety: 悪名フラグ (TRUE/FALSE)

    Returns:
        int: 有名度スコア (0-100点)
    """
    try:
        # 基礎スコア（手動評価1-5）
        fame_tier = int(person.get("fame_tier", 0))
        base_score = fame_tier * 15  # 15-75点

        # データソース補正
        wikipedia_bonus = 15 if person.get("wikipedia_ja", "").upper() == "TRUE" else 0
        textbook_bonus = 10 if person.get("textbook", "").upper() == "TRUE" else 0
        award_level = int(person.get("award_level", 0))
        award_bonus = award_level * 3  # 0-9点

        # 悪名ペナルティ
        notoriety_penalty = -20 if person.get("notoriety", "").upper() == "TRUE" else 0

        # 合計
        raw_score = base_score + wikipedia_bonus + textbook_bonus + award_bonus + notoriety_penalty

        # 正規化（0-100点）
        fame_score = min(100, max(0, int(raw_score * 0.8)))

        return fame_score

    except (ValueError, TypeError) as e:
        print(f"⚠️  スコア計算エラー ({person.get('person_name', 'Unknown')}): {e}")
        return 0


def calculate_composite_score(fame_score: int, quality_score: float) -> int:
    """
    総合スコアを計算

    Args:
        fame_score: 有名度スコア (0-100点)
        quality_score: 品質スコア (0-10点)

    Returns:
        int: 総合スコア (0-100点)
    """
    try:
        # 総合スコア = 有名度60% + 品質40%
        composite = (fame_score * 0.6) + (quality_score * 10 * 0.4)
        return int(min(100, max(0, composite)))
    except (ValueError, TypeError):
        return fame_score  # 品質スコアがない場合は有名度スコアのみ


def add_fame_columns_to_csv(input_csv_path: Path, output_csv_path: Path) -> Tuple[int, int]:
    """
    CSVに有名度関連カラムを追加してスコアを計算

    Args:
        input_csv_path: 入力CSVファイルパス
        output_csv_path: 出力CSVファイルパス

    Returns:
        Tuple[int, int]: (処理件数, エラー件数)
    """
    # 新しいカラム名
    new_columns = [
        "fame_tier",
        "wikipedia_ja",
        "textbook",
        "award_level",
        "notoriety",
        "fame_score",
        "composite_score",
        "fame_score_updated_at",
    ]

    processed = 0
    errors = 0
    current_time = datetime.now().isoformat()

    try:
        with open(input_csv_path, "r", encoding="utf-8-sig") as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames

            # 既存のカラムに新カラムを追加
            output_fieldnames = list(fieldnames) + new_columns

            # 出力CSV準備
            with open(output_csv_path, "w", encoding="utf-8-sig", newline="") as outfile:
                writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
                writer.writeheader()

                for row in reader:
                    try:
                        # デフォルト値を設定（すべて未評価）
                        if not row.get("fame_tier"):
                            row["fame_tier"] = "0"  # 未評価
                        if not row.get("wikipedia_ja"):
                            row["wikipedia_ja"] = ""  # 未調査
                        if not row.get("textbook"):
                            row["textbook"] = ""  # 未調査
                        if not row.get("award_level"):
                            row["award_level"] = "0"
                        if not row.get("notoriety"):
                            row["notoriety"] = ""

                        # スコア計算（fame_tier > 0の場合のみ）
                        if int(row.get("fame_tier", 0)) > 0:
                            row["fame_score"] = str(calculate_fame_score(row))

                            # 総合スコア計算
                            quality_score = float(row.get("quality_score", 0) or 0)
                            row["composite_score"] = str(
                                calculate_composite_score(int(row["fame_score"]), quality_score)
                            )
                            row["fame_score_updated_at"] = current_time
                        else:
                            # 未評価の場合は空欄
                            row["fame_score"] = ""
                            row["composite_score"] = ""
                            row["fame_score_updated_at"] = ""

                        writer.writerow(row)
                        processed += 1

                    except Exception as e:
                        print(f"❌ 行処理エラー ({row.get('person_name', 'Unknown')}): {e}")
                        errors += 1
                        # エラー行もそのまま出力（スコアは空欄）
                        row["fame_score"] = ""
                        row["composite_score"] = ""
                        row["fame_score_updated_at"] = ""
                        writer.writerow(row)

        return processed, errors

    except FileNotFoundError:
        print(f"❌ ファイルが見つかりません: {input_csv_path}")
        return 0, 0
    except Exception as e:
        print(f"❌ CSV処理エラー: {e}")
        return 0, 0


def update_fame_scores_only(csv_path: Path) -> Tuple[int, int]:
    """
    既存のfame_tier等からfame_scoreとcomposite_scoreのみを再計算

    Args:
        csv_path: CSVファイルパス（上書き）

    Returns:
        Tuple[int, int]: (更新件数, エラー件数)
    """
    updated = 0
    errors = 0
    current_time = datetime.now().isoformat()

    try:
        # 一時ファイルに書き込み
        temp_path = csv_path.with_suffix(".tmp")

        with open(csv_path, "r", encoding="utf-8-sig") as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames

            with open(temp_path, "w", encoding="utf-8-sig", newline="") as outfile:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in reader:
                    try:
                        # 全てのデータに対してスコア計算
                        row["fame_score"] = str(calculate_fame_score(row))

                        quality_score = float(row.get("quality_score", 0) or 0)
                        row["composite_score"] = str(calculate_composite_score(int(row["fame_score"]), quality_score))
                        row["fame_score_updated_at"] = current_time
                        updated += 1

                        writer.writerow(row)

                    except Exception as e:
                        print(f"⚠️  行更新エラー ({row.get('person_name', 'Unknown')}): {e}")
                        errors += 1
                        writer.writerow(row)

        # 一時ファイルを元のファイルに置き換え
        temp_path.replace(csv_path)
        return updated, errors

    except Exception as e:
        print(f"❌ 更新エラー: {e}")
        return 0, 0


def display_score_distribution(csv_path: Path):
    """
    スコア分布を表示

    Args:
        csv_path: CSVファイルパス
    """
    scores = []
    notoriety_count = 0

    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                fame_score = row.get("fame_score", "")
                if fame_score and fame_score.isdigit():
                    scores.append(int(fame_score))

                if row.get("notoriety", "").upper() == "TRUE":
                    notoriety_count += 1

        if scores:
            print("\n📊 スコア分布:")
            print(f"  評価済み: {len(scores)}人")
            print(f"  最高点: {max(scores)}点")
            print(f"  最低点: {min(scores)}点")
            print(f"  平均点: {sum(scores) / len(scores):.1f}点")
            print(f"  悪名フラグ: {notoriety_count}人")

            # スコア範囲別集計
            ranges = {
                "90-100点": sum(1 for s in scores if 90 <= s <= 100),
                "80-89点": sum(1 for s in scores if 80 <= s < 90),
                "70-79点": sum(1 for s in scores if 70 <= s < 80),
                "60-69点": sum(1 for s in scores if 60 <= s < 70),
                "50-59点": sum(1 for s in scores if 50 <= s < 60),
                "50点未満": sum(1 for s in scores if s < 50),
            }

            print("\n  スコア範囲別:")
            for range_name, count in ranges.items():
                print(f"    {range_name}: {count}人")

    except Exception as e:
        print(f"❌ 分布表示エラー: {e}")


def main():
    """メイン処理"""
    print("=" * 60)
    print("有名度スコア算出スクリプト - Final Hourglass")
    print("=" * 60)

    # ファイルパス
    csv_path = project_root / "MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return

    # 新カラムが既に存在するかチェック
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        existing_columns = reader.fieldnames

    if "fame_score" in existing_columns:
        # 既にカラムが存在する場合は再計算のみ
        print("\n✅ 有名度カラムは既に存在します")
        print("📝 スコアを再計算します...")

        updated, errors = update_fame_scores_only(csv_path)

        print("\n✅ 更新完了:")
        print(f"  更新件数: {updated}件")
        if errors > 0:
            print(f"  ⚠️  エラー件数: {errors}件")

    else:
        # 新カラムを追加
        print("\n📝 新しいカラムを追加します...")
        output_path = csv_path.with_suffix(".new.csv")

        processed, errors = add_fame_columns_to_csv(csv_path, output_path)

        print("\n✅ 処理完了:")
        print(f"  処理件数: {processed}件")
        if errors > 0:
            print(f"  ⚠️  エラー件数: {errors}件")

        # バックアップと置き換え
        backup_path = csv_path.with_suffix(".backup.csv")
        csv_path.rename(backup_path)
        output_path.rename(csv_path)

        print("\n✅ ファイル更新:")
        print(f"  元ファイル → {backup_path.name}")
        print(f"  新ファイル → {csv_path.name}")

    # スコア分布を表示
    display_score_distribution(csv_path)

    print("\n" + "=" * 60)
    print("✅ すべての処理が完了しました")
    print("=" * 60)


if __name__ == "__main__":
    main()
