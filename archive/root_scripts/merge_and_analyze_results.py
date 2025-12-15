#!/usr/bin/env python3
"""
知名度評価結果と元データを結合して分析
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json

def merge_and_analyze():
    """評価結果と元データを結合して分析"""
    print("="*60)
    print("📊 知名度評価結果分析（データ結合版）")
    print("="*60)

    # データ読み込み
    results_file = "recognition_evaluation_20250910_173754.csv"
    original_file = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"

    df_results = pd.read_csv(results_file)
    df_original = pd.read_csv(original_file)

    print(f"📂 評価結果: {len(df_results)}件")
    print(f"📂 元データ: {len(df_original)}件")

    # person_idで結合してentity_typeを取得
    df = df_results.merge(
        df_original[['person_id', 'entity_type']],
        on='person_id',
        how='left'
    )
    print(f"📂 結合後: {len(df)}件")

    # 基本統計
    print("\n📈 基本統計:")
    print(f"  平均スコア: {df['final_score'].mean():.2f}")
    print(f"  中央値: {df['final_score'].median():.2f}")
    print(f"  標準偏差: {df['final_score'].std():.2f}")
    print(f"  最小値: {df['final_score'].min():.2f}")
    print(f"  最大値: {df['final_score'].max():.2f}")

    # スコア分布
    print("\n📊 スコア分布:")
    bins = [0, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    labels = ['0-2', '2-3', '3-4', '4-5', '5-6', '6-7', '7-8', '8-9', '9-10']
    df['score_range'] = pd.cut(df['final_score'], bins=bins, labels=labels, include_lowest=True)
    score_dist = df['score_range'].value_counts().sort_index()

    for range_label, count in score_dist.items():
        percent = count / len(df) * 100
        bar = '█' * int(percent / 2)
        print(f"  {range_label}: {count:4d}件 ({percent:5.1f}%) {bar}")

    # entity_type別統計
    print("\n🏷️ entity_type別統計:")
    for entity_type in df['entity_type'].unique():
        if pd.notna(entity_type):
            type_df = df[df['entity_type'] == entity_type]
            avg_score = type_df['final_score'].mean()
            count = len(type_df)
            print(f"  {entity_type}: {count}件, 平均スコア: {avg_score:.2f}")

    # 削除候補の判定
    print("\n🗑️ 削除候補の判定:")

    # 削除基準
    DELETE_THRESHOLD = 3.0  # スコア3.0以下を削除候補

    # ただし、グループと架空キャラクターは特別扱い
    # グループは削除しない
    # 架空キャラクターは文化的影響度が高ければ保持

    # 削除候補を特定
    delete_candidates = df[
        (df['final_score'] <= DELETE_THRESHOLD) &
        (df['entity_type'] != 'group')  # グループは削除しない
    ].copy()

    keep_records = df[
        (df['final_score'] > DELETE_THRESHOLD) |
        (df['entity_type'] == 'group')  # グループは必ず保持
    ].copy()

    print(f"  削除閾値: {DELETE_THRESHOLD}")
    print(f"  削除候補: {len(delete_candidates)}件 ({len(delete_candidates)/len(df)*100:.1f}%)")
    print(f"  保持対象: {len(keep_records)}件 ({len(keep_records)/len(df)*100:.1f}%)")

    # 削除候補の詳細分析
    if len(delete_candidates) > 0:
        print("\n📋 削除候補の詳細:")
        print(f"  スコア分布:")
        score_counts = delete_candidates['final_score'].value_counts().sort_index()
        for score, count in score_counts.items():
            if count > 0:
                print(f"    スコア {score:.1f}: {count}件")

        print("\n  entity_type別:")
        for entity_type in delete_candidates['entity_type'].unique():
            if pd.notna(entity_type):
                count = len(delete_candidates[delete_candidates['entity_type'] == entity_type])
                print(f"    {entity_type}: {count}件")

        # 削除候補の例
        print("\n  削除候補の例（スコアが低い順）:")
        examples = delete_candidates.nsmallest(10, 'final_score')[['person_id', 'person_name_ja', 'final_score', 'entity_type']]
        for idx, row in examples.iterrows():
            print(f"    {row['person_id']}: {row['person_name_ja']} (スコア: {row['final_score']}, {row['entity_type']})")

    # 高スコアの確認
    print("\n🏆 高スコア（保持確定）:")
    high_scores = df[df['final_score'] >= 7.0]
    print(f"  スコア7.0以上: {len(high_scores)}件")

    top_10 = df.nlargest(10, 'final_score')[['person_id', 'person_name_ja', 'final_score', 'entity_type']]
    print("\n  トップ10:")
    for idx, row in top_10.iterrows():
        print(f"    {row['person_id']}: {row['person_name_ja']} (スコア: {row['final_score']}, {row['entity_type']})")

    # グループの確認
    print("\n👥 グループの保護:")
    groups = df[df['entity_type'] == 'group']
    print(f"  総数: {len(groups)}件")
    if len(groups) > 0:
        print("  グループリスト:")
        for idx, row in groups.iterrows():
            status = "✅ 保持（グループ）"
            print(f"    {row['person_id']}: {row['person_name_ja']} (スコア: {row['final_score']}) - {status}")

    # 架空キャラクターの保護確認
    print("\n🎭 架空キャラクターの分析:")
    fictional = df[df['entity_type'] == 'fictional_character']
    print(f"  総数: {len(fictional)}件")
    if len(fictional) > 0:
        print(f"  平均スコア: {fictional['final_score'].mean():.2f}")

        fictional_delete = fictional[fictional['final_score'] <= DELETE_THRESHOLD]
        fictional_keep = fictional[fictional['final_score'] > DELETE_THRESHOLD]
        print(f"  削除候補: {len(fictional_delete)}件")
        print(f"  保持対象: {len(fictional_keep)}件")

        # 有名作品のキャラクター確認
        famous_characters = ['竈門炭治郎', '孫悟空', 'ドラえもん', 'ピカチュウ', 'ルフィ', 'エヴァンゲリオン初号機', 'セーラームーン']
        print("\n  有名キャラクターの確認:")
        for char_name in famous_characters:
            char_record = df[df['person_name_ja'] == char_name]
            if not char_record.empty:
                score = char_record.iloc[0]['final_score']
                status = "✅ 保持" if score > DELETE_THRESHOLD else "⚠️ 要検討"
                print(f"    {char_name}: スコア {score:.1f} - {status}")

    # 中間スコアの分析
    print("\n⚠️ 中間スコア（要検討）:")
    middle_scores = df[(df['final_score'] > DELETE_THRESHOLD) & (df['final_score'] < 7.0)]
    print(f"  スコア{DELETE_THRESHOLD}-7.0: {len(middle_scores)}件")

    # 削除候補をCSVに保存
    if len(delete_candidates) > 0:
        delete_file = f"delete_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        delete_candidates.to_csv(delete_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 削除候補リスト保存: {delete_file}")

    # 保持対象をCSVに保存
    keep_file = f"keep_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    keep_records.to_csv(keep_file, index=False, encoding='utf-8-sig')
    print(f"💾 保持対象リスト保存: {keep_file}")

    # 最終データベースの作成（保持対象のみ）
    final_db = df_original[df_original['person_id'].isin(keep_records['person_id'])].copy()
    final_file = f"ultra_think_FINAL_DATABASE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    final_db.to_csv(final_file, index=False, encoding='utf-8-sig')
    print(f"💾 最終データベース保存: {final_file} ({len(final_db)}件)")

    # サマリーレポート
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_records": len(df),
        "delete_threshold": DELETE_THRESHOLD,
        "delete_candidates": len(delete_candidates),
        "keep_records": len(keep_records),
        "deletion_rate": len(delete_candidates) / len(df) * 100,
        "average_score": float(df['final_score'].mean()),
        "median_score": float(df['final_score'].median()),
        "high_scores_7plus": len(high_scores),
        "groups": {
            "total": len(groups),
            "all_kept": True
        },
        "fictional_characters": {
            "total": len(fictional),
            "delete": len(fictional_delete) if len(fictional) > 0 else 0,
            "keep": len(fictional_keep) if len(fictional) > 0 else 0
        },
        "entity_type_stats": {}
    }

    # entity_type別の統計を追加
    for entity_type in df['entity_type'].unique():
        if pd.notna(entity_type):
            type_df = df[df['entity_type'] == entity_type]
            type_delete = delete_candidates[delete_candidates['entity_type'] == entity_type]
            summary["entity_type_stats"][entity_type] = {
                "total": len(type_df),
                "delete": len(type_delete),
                "keep": len(type_df) - len(type_delete),
                "average_score": float(type_df['final_score'].mean())
            }

    with open('recognition_analysis_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n📝 分析サマリー保存: recognition_analysis_summary.json")

    return delete_candidates, keep_records, final_db

if __name__ == "__main__":
    delete_candidates, keep_records, final_db = merge_and_analyze()

    print("\n" + "="*60)
    print("📊 分析完了")
    print("="*60)
    print(f"削除候補: {len(delete_candidates)}件")
    print(f"保持対象: {len(keep_records)}件")
    print(f"削除率: {len(delete_candidates)/(len(delete_candidates)+len(keep_records))*100:.1f}%")
    print(f"最終データベース: {len(final_db)}件")
