#!/usr/bin/env python3
"""
セッション間のエピソード増減分析スクリプト

前回セッション（2025-11-23）から現在までの差分を分析
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

def analyze_diff():
    """差分分析"""
    # CSVファイル読み込み
    csv_path = Path("MASTER_EPISODES_CURRENT.csv")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    print("=" * 80)
    print("📊 エピソード差分分析レポート")
    print("=" * 80)
    print(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"CSVファイル: {csv_path}")
    print()

    # 基本統計
    total_csv = len(df)
    print("=" * 80)
    print("1️⃣ 基本統計")
    print("=" * 80)
    print(f"CSVファイル総エピソード数: {total_csv:,}件")
    print(f"前回セッション（2025-11-23 20:45）: 1,448件")
    print(f"増加数: +{total_csv - 1448:,}件 ({((total_csv - 1448) / 1448 * 100):.1f}%増)")
    print()

    # カテゴリ別分析
    print("=" * 80)
    print("2️⃣ カテゴリ別エピソード数（上位20）")
    print("=" * 80)
    category_counts = df['category'].value_counts()
    for i, (cat, count) in enumerate(category_counts.head(20).items(), 1):
        pct = count / total_csv * 100
        bar = '█' * int(pct / 2)
        print(f"{i:2d}. {cat:25s}: {count:4d}件 ({pct:5.1f}%) {bar}")
    print()

    # 50件未満のカテゴリ
    print("=" * 80)
    print("3️⃣ 不足カテゴリ（50件未満）")
    print("=" * 80)
    under_50 = category_counts[category_counts < 50]
    print(f"不足カテゴリ数: {len(under_50)}個")
    print(f"不足エピソード総数: {(50 * len(under_50)) - under_50.sum()}件")
    print()
    for cat, count in under_50.items():
        shortage = 50 - count
        print(f"  - {cat}: {count}件（あと{shortage}件必要）")
    print()

    # person_type分析
    print("=" * 80)
    print("4️⃣ person_type分布")
    print("=" * 80)
    type_counts = df['person_type'].value_counts()
    for ptype, count in type_counts.items():
        pct = count / total_csv * 100
        print(f"{ptype:30s}: {count:4d}件 ({pct:5.1f}%)")
    print()

    fictional = df[df['person_type'].str.contains('FICTIONAL', na=False)]['person_type'].value_counts().sum()
    print(f"📌 架空キャラクター総数: {fictional}件")
    print(f"   目標: 100件以上 → あと{max(0, 100 - fictional)}件必要")
    print()

    # 品質スコア分析
    print("=" * 80)
    print("5️⃣ 品質スコア分析")
    print("=" * 80)
    if 'composite_score' in df.columns:
        avg_score = df['composite_score'].mean()
        median_score = df['composite_score'].median()
        min_score = df['composite_score'].min()
        max_score = df['composite_score'].max()

        print(f"平均品質スコア: {avg_score:.2f}点")
        print(f"中央値: {median_score:.2f}点")
        print(f"最小値: {min_score:.2f}点")
        print(f"最大値: {max_score:.2f}点")
        print()

        high_quality = len(df[df['composite_score'] >= 80])
        mid_quality = len(df[(df['composite_score'] >= 70) & (df['composite_score'] < 80)])
        low_quality = len(df[df['composite_score'] < 70])

        print(f"高品質（80点以上）: {high_quality}件 ({high_quality / total_csv * 100:.1f}%)")
        print(f"中品質（70-79点）: {mid_quality}件 ({mid_quality / total_csv * 100:.1f}%)")
        print(f"低品質（70点未満）: {low_quality}件 ({low_quality / total_csv * 100:.1f}%)")
    else:
        print("⚠️  composite_scoreカラムが見つかりません")
    print()

    # 重複チェック
    print("=" * 80)
    print("6️⃣ 重複チェック")
    print("=" * 80)
    duplicate_persons = df['person_id'].value_counts()
    duplicates = duplicate_persons[duplicate_persons > 1]
    print(f"person_id重複数: {len(duplicates)}個")
    print(f"重複エピソード総数: {duplicates.sum() - len(duplicates)}件")
    print()

    episode_duplicates = df['episode_text'].value_counts()
    ep_duplicates = episode_duplicates[episode_duplicates > 1]
    print(f"episode_text重複数: {len(ep_duplicates)}個")
    if len(ep_duplicates) > 0:
        print("⚠️  同一エピソード文が複数存在します（削除推奨）")
    print()

    # CSV vs データベース
    print("=" * 80)
    print("7️⃣ CSV vs データベース")
    print("=" * 80)
    print(f"CSVファイル: {total_csv:,}件")
    print(f"データベース（API応答）: 1,962件")
    print(f"差分: {total_csv - 1962:,}件")
    print()
    if total_csv > 1962:
        print("⚠️  CSVファイルにデータベースにない{:,}件のエピソードがあります".format(total_csv - 1962))
        print("   → データベース再同期が必要かもしれません")
    print()

    # サマリー
    print("=" * 80)
    print("8️⃣ サマリー")
    print("=" * 80)
    print(f"✅ 前回から+{total_csv - 1448}件増加")
    print(f"✅ 平均品質スコア: {df['composite_score'].mean():.2f}点" if 'composite_score' in df.columns else "")
    print(f"⚠️  不足カテゴリ: {len(under_50)}個")
    print(f"⚠️  架空キャラクター: {fictional}件（目標100件）")
    print()

    print("=" * 80)
    print("分析完了")
    print("=" * 80)

if __name__ == "__main__":
    analyze_diff()
