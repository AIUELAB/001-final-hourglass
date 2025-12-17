#!/usr/bin/env python3
"""
未評価エピソードにfame_tierを自動付与するスクリプト

対象: fame_tierが0またはnullのエピソード
方法: fame_scoreに基づいてfame_tierを計算
"""

import pandas as pd
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = (
    PROJECT_ROOT
    / "preserved"
    / "data"
    / f"MASTER_EPISODES_CURRENT_backup_before_tier_fill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)


def fame_score_to_tier(score):
    """
    fame_scoreからfame_tierを計算

    既存データの分析結果に基づく：
    - Tier 5: 8.4以上（世界的）
    - Tier 4: 5.0-8.3（全国的）
    - Tier 3: 4.0-4.9（地域的）
    - Tier 2: 3.0-3.9（専門的）
    - Tier 1: 3.0未満（限定的）
    """
    if pd.isna(score):
        return None

    if score >= 8.4:
        return 5
    elif score >= 5.0:
        return 4
    elif score >= 4.0:
        return 3
    elif score >= 3.0:
        return 2
    else:
        return 1


def estimate_fame_score_from_metadata(row):
    """
    メタデータからfame_scoreを推定

    優先順位：
    1. wikipedia_ja=1 → 高スコア
    2. textbook=1 → 中〜高スコア
    3. award_level → スコア加算
    4. カテゴリデフォルト
    """
    base_score = 6.0  # デフォルト

    # Wikipedia掲載は高評価
    if row.get("wikipedia_ja") == 1:
        base_score = 7.5

    # 教科書掲載も高評価
    if row.get("textbook") == 1:
        base_score = max(base_score, 7.0)

    # award_levelによる加算
    award_level = row.get("award_level")
    if pd.notna(award_level):
        try:
            award_level = float(award_level)
            if award_level >= 4.0:  # 国際的な賞
                base_score += 1.0
            elif award_level >= 3.0:  # 国内主要な賞
                base_score += 0.5
        except (ValueError, TypeError):
            pass

    # カテゴリに基づく調整
    category = row.get("category", "")
    if "経営" in category or "ビジネス" in category:
        base_score += 0.3
    elif "スポーツ" in category:
        base_score += 0.3
    elif "政治" in category or "社会" in category:
        base_score += 0.2

    # スコアの上限を10.0に制限
    return min(base_score, 10.0)


def main():
    print("🔧 未評価エピソードにfame_tierを付与します")
    print("=" * 80)

    # CSVを読み込み
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"📊 総エピソード数: {len(df):,}件")

    # 未評価エピソードを特定
    unrated_mask = (df["fame_tier"].isna()) | (df["fame_tier"] == 0)
    unrated_count = unrated_mask.sum()
    print(f"📋 未評価エピソード: {unrated_count:,}件")

    if unrated_count == 0:
        print("✅ 未評価エピソードはありません")
        return

    # バックアップ作成
    df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
    print(f"💾 バックアップ作成: {BACKUP_PATH.name}")
    print()

    # fame_tierを付与
    updated_count = 0
    tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for idx in df[unrated_mask].index:
        row = df.loc[idx]

        # fame_scoreが存在する場合はそれを使用
        if pd.notna(row["fame_score"]) and row["fame_score"] > 0:
            tier = fame_score_to_tier(row["fame_score"])
        else:
            # fame_scoreがない場合はメタデータから推定
            estimated_score = estimate_fame_score_from_metadata(row)
            df.loc[idx, "fame_score"] = estimated_score
            tier = fame_score_to_tier(estimated_score)

        if tier is not None:
            df.loc[idx, "fame_tier"] = tier
            tier_counts[tier] += 1
            updated_count += 1

    print(f"✅ {updated_count:,}件のfame_tierを付与しました")
    print()
    print("📊 Tier別内訳:")
    for tier in [5, 4, 3, 2, 1]:
        if tier_counts[tier] > 0:
            print(f"  Tier {tier}: {tier_counts[tier]:,}件")
    print()

    # CSVを保存
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"💾 マスターCSVを更新: {CSV_PATH.name}")

    # 検証
    remaining_unrated = ((df["fame_tier"].isna()) | (df["fame_tier"] == 0)).sum()
    print()
    print(f"📋 残りの未評価: {remaining_unrated:,}件")

    if remaining_unrated == 0:
        print("🎉 全てのエピソードにfame_tierが付与されました！")

    print()
    print("=" * 80)
    print("✅ 完了")


if __name__ == "__main__":
    main()
