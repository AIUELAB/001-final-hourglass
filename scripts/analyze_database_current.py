#!/usr/bin/env python3
"""
データベース現状分析スクリプト

カテゴリ分布、品質スコア、重複、データ完全性をチェック
"""

import json
from collections import Counter
from datetime import datetime

import pandas as pd


def analyze_database():
    """データベース分析を実行"""

    # CSVファイル読み込み
    df = pd.read_csv("MASTER_EPISODES_CURRENT.csv", encoding="utf-8-sig")

    print("=" * 80)
    print("📊 データベース現状分析レポート")
    print("=" * 80)
    print(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"総エピソード数: {len(df):,}件\n")

    # 1. カテゴリ分布分析
    print("=" * 80)
    print("1️⃣ カテゴリ分布")
    print("=" * 80)
    category_counts = df["category"].value_counts()
    print(f"\n総カテゴリ数: {len(category_counts)}種類\n")

    for category, count in category_counts.items():
        percentage = (count / len(df)) * 100
        bar = "█" * int(percentage / 2)
        print(f"{category:20s}: {count:4d}件 ({percentage:5.1f}%) {bar}")

    # 不足カテゴリ（50件未満）
    print("\n⚠️  不足カテゴリ（50件未満）:")
    insufficient = category_counts[category_counts < 50]
    for category, count in insufficient.items():
        print(f"  - {category}: {count}件（あと{50-count}件必要）")

    # 2. person_type分布
    print("\n" + "=" * 80)
    print("2️⃣ person_type分布")
    print("=" * 80)
    person_type_counts = df["person_type"].value_counts()
    for ptype, count in person_type_counts.items():
        percentage = (count / len(df)) * 100
        print(f"{ptype:15s}: {count:4d}件 ({percentage:5.1f}%)")

    # 3. 品質スコア分析
    print("\n" + "=" * 80)
    print("3️⃣ 品質スコア分析")
    print("=" * 80)

    if "composite_score" in df.columns:
        composite_scores = df["composite_score"].dropna()
        print("composite_score:")
        print(f"  - 平均: {composite_scores.mean():.2f}点")
        print(f"  - 中央値: {composite_scores.median():.2f}点")
        print(f"  - 最小: {composite_scores.min():.2f}点")
        print(f"  - 最大: {composite_scores.max():.2f}点")

        # スコア分布
        high_quality = len(composite_scores[composite_scores >= 80])
        medium_quality = len(composite_scores[(composite_scores >= 70) & (composite_scores < 80)])
        low_quality = len(composite_scores[composite_scores < 70])

        print("\n  スコア分布:")
        print(f"  - 高品質（80点以上）: {high_quality}件 ({high_quality/len(df)*100:.1f}%)")
        print(f"  - 中品質（70-79点）: {medium_quality}件 ({medium_quality/len(df)*100:.1f}%)")
        print(f"  - 低品質（70点未満）: {low_quality}件 ({low_quality/len(df)*100:.1f}%)")

    # 4. データ完全性チェック
    print("\n" + "=" * 80)
    print("4️⃣ データ完全性チェック")
    print("=" * 80)

    essential_columns = ["person_id", "person_name", "category", "episode_text", "person_type"]
    for col in essential_columns:
        null_count = df[col].isna().sum()
        empty_count = (df[col] == "").sum() if df[col].dtype == "object" else 0
        total_missing = null_count + empty_count

        if total_missing > 0:
            print(f"  ⚠️  {col}: {total_missing}件欠損")
        else:
            print(f"  ✅ {col}: 完全")

    # 5. 重複チェック
    print("\n" + "=" * 80)
    print("5️⃣ 重複チェック")
    print("=" * 80)

    # person_idの重複
    duplicate_ids = df[df.duplicated(subset=["person_id"], keep=False)]
    if len(duplicate_ids) > 0:
        print(f"  ⚠️  person_id重複: {len(duplicate_ids)}件")
        print(f"     重複ID数: {duplicate_ids['person_id'].nunique()}個")
    else:
        print("  ✅ person_id重複: なし")

    # episode_textの重複
    duplicate_texts = df[df.duplicated(subset=["episode_text"], keep=False)]
    if len(duplicate_texts) > 0:
        print(f"  ⚠️  episode_text重複: {len(duplicate_texts)}件")
    else:
        print("  ✅ episode_text重複: なし")

    # 6. fame_score分布
    print("\n" + "=" * 80)
    print("6️⃣ fame_score分布")
    print("=" * 80)

    if "fame_score" in df.columns:
        fame_scores = df["fame_score"].dropna()
        print(f"  - 平均: {fame_scores.mean():.1f}点")
        print(f"  - 中央値: {fame_scores.median():.1f}点")

        # スコア分布
        for score in [30, 50, 70, 90]:
            count = len(fame_scores[fame_scores >= score])
            print(f"  - {score}点以上: {count}件 ({count/len(df)*100:.1f}%)")

    # 7. 統計サマリー
    print("\n" + "=" * 80)
    print("7️⃣ 統計サマリー")
    print("=" * 80)

    print(f"  - ユニーク人物数: {df['person_name'].nunique():,}人")
    print(f"  - 平均年齢: {df['age'].mean():.1f}歳")
    print(f"  - 平均文字数: {df['char_count'].mean():.0f}文字")

    # エピソードタイプ分布
    if "episode_type" in df.columns:
        print("\n  エピソードタイプ:")
        type_counts = df["episode_type"].value_counts()
        for etype, count in type_counts.items():
            if pd.notna(etype):
                print(f"    - {etype}: {count}件")

    # 8. 推奨アクション
    print("\n" + "=" * 80)
    print("8️⃣ 推奨アクション")
    print("=" * 80)

    actions = []

    # 不足カテゴリチェック
    if len(insufficient) > 0:
        actions.append(f"⚠️  {len(insufficient)}カテゴリが50件未満 → エピソード追加が必要")

    # 架空キャラクター不足チェック
    fictional_count = len(df[df["person_type"] == "FICTIONAL"])
    if fictional_count < 100:
        actions.append(f"⚠️  架空キャラクター{fictional_count}件（目標100件以上） → 追加が必要")

    # 低品質エピソードチェック
    if "composite_score" in df.columns:
        if low_quality > 0:
            actions.append(f"⚠️  低品質エピソード{low_quality}件 → 品質改善が必要")

    # 重複チェック
    if len(duplicate_ids) > 0 or len(duplicate_texts) > 0:
        actions.append("⚠️  重複エピソード検出 → 削除が必要")

    if len(actions) == 0:
        print("  ✅ データベースは良好な状態です")
    else:
        for i, action in enumerate(actions, 1):
            print(f"  {i}. {action}")

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)

    # JSON形式でも出力
    report = {
        "total_episodes": len(df),
        "categories": category_counts.to_dict(),
        "insufficient_categories": insufficient.to_dict(),
        "person_type_distribution": person_type_counts.to_dict(),
        "quality_summary": {
            "high_quality_count": high_quality if "composite_score" in df.columns else 0,
            "medium_quality_count": medium_quality if "composite_score" in df.columns else 0,
            "low_quality_count": low_quality if "composite_score" in df.columns else 0,
        },
        "duplicates": {"person_id": len(duplicate_ids), "episode_text": len(duplicate_texts)},
        "recommended_actions": actions,
        "generated_at": datetime.now().isoformat(),
    }

    with open("reports/database_analysis_current.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n📄 詳細レポート保存: reports/database_analysis_current.json")


if __name__ == "__main__":
    analyze_database()
