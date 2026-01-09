#!/usr/bin/env python3
"""
composite_score一貫性検証スクリプト

石ノ森章太郎と他の人物のcomposite_score計算が
同じルール（7軸スコアの平均）で行われているかを検証
"""

from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).parent.parent.parent / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


def calculate_composite_score(row: pd.Series) -> float:
    """7軸スコアからcomposite_scoreを計算（共通ロジック）"""
    seven_axes = []

    for axis in [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]:
        val = row.get(axis)
        if pd.notna(val):
            try:
                seven_axes.append(float(val))
            except (ValueError, TypeError):
                pass

    if len(seven_axes) == 7:
        return sum(seven_axes) / 7
    else:
        return None


def verify_person(df: pd.DataFrame, person_name: str):
    """特定人物のcomposite_score検証"""
    person_df = df[df["person_name"] == person_name].copy()

    if len(person_df) == 0:
        print(f"  ⚠️  {person_name}: データなし")
        return True

    print(f"\n【{person_name}】({len(person_df)}件)")
    all_ok = True

    for idx, row in person_df.iterrows():
        expected_composite = calculate_composite_score(row)
        actual_composite = row["composite_score"]

        if expected_composite is None:
            print(f"  ⚠️  {row['age']}歳: 7軸スコア不完全（スキップ）")
            continue

        if pd.isna(actual_composite):
            print(f"  ❌ {row['age']}歳: composite_score欠損")
            all_ok = False
            continue

        diff = abs(actual_composite - expected_composite)
        status = "✅" if diff < 0.0001 else "❌"

        if diff >= 0.0001:
            print(
                f"  {status} {row['age']}歳: 期待={expected_composite:.6f}, 実際={actual_composite:.6f}, 差分={diff:.6f}"
            )
            all_ok = False
        else:
            print(f"  {status} {row['age']}歳: {actual_composite:.6f} (一致)")

    return all_ok


def main():
    print("=" * 80)
    print("📊 composite_score一貫性検証")
    print("=" * 80)
    print()

    # CSVファイル読み込み
    print("CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"✅ 読み込み完了: {len(df):,}件")
    print()

    # 検証対象の人物
    test_persons = [
        "石ノ森章太郎",  # 修正対象
        "AKB48",  # 他の人物（サンプル）
        "森三郎",  # 他の人物（サンプル）
        "棚橋弘至",  # 他の人物（サンプル）
        "梶田隆章",  # 他の人物（サンプル）
    ]

    results = {}

    print("=" * 80)
    print("検証開始")
    print("=" * 80)

    for person in test_persons:
        is_ok = verify_person(df, person)
        results[person] = is_ok

    print()
    print("=" * 80)
    print("検証結果サマリー")
    print("=" * 80)
    print()

    all_passed = True
    for person, is_ok in results.items():
        status = "✅ 合格" if is_ok else "❌ 不合格"
        print(f"  {status}: {person}")
        if not is_ok:
            all_passed = False

    print()

    if all_passed:
        print("✅ すべての人物でcomposite_scoreが正しく計算されています")
    else:
        print("❌ 一部の人物でcomposite_scoreに不整合があります")

    print()

    # 追加検証: 全エピソードの一貫性チェック
    print("=" * 80)
    print("全エピソードの一貫性チェック")
    print("=" * 80)
    print()

    inconsistent_count = 0
    missing_count = 0
    valid_count = 0

    for idx, row in df.iterrows():
        expected = calculate_composite_score(row)
        actual = row["composite_score"]

        if expected is None:
            continue  # 7軸スコア不完全

        if pd.isna(actual):
            missing_count += 1
            continue

        diff = abs(actual - expected)
        if diff >= 0.0001:
            inconsistent_count += 1
            if inconsistent_count <= 10:  # 最初の10件だけ表示
                print(f"  不整合: {row['person_name']} ({row['age']}歳) - 期待={expected:.6f}, 実際={actual:.6f}")
        else:
            valid_count += 1

    print()
    print("検証結果:")
    print(f"  ✅ 一致: {valid_count:,}件")
    print(f"  ❌ 不整合: {inconsistent_count:,}件")
    print(f"  ⚠️  欠損: {missing_count:,}件")
    print()

    if inconsistent_count == 0 and missing_count == 0:
        print("=" * 80)
        print("✅ すべてのエピソードでcomposite_scoreが正しく計算されています！")
        print("=" * 80)
    else:
        print("=" * 80)
        print(f"⚠️  不整合または欠損があります: 不整合{inconsistent_count}件、欠損{missing_count}件")
        print("=" * 80)


if __name__ == "__main__":
    main()
