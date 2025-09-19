#!/usr/bin/env python3
"""
生年月日未取得データの分析と効率的な処理戦略の策定
"""

import pandas as pd
from pathlib import Path
import numpy as np

def analyze_remaining_data():
    """残りのデータを分析して効率的な処理戦略を提案"""

    print("=" * 80)
    print("📊 生年月日未取得データの分析")
    print("=" * 80)

    # 最新のフェーズ6結果を読み込み
    input_file = 'ultra_think_WITH_BIRTH_DATES_PHASE6_20250916_230216.csv'

    if not Path(input_file).exists():
        print(f"❌ ファイルが見つかりません: {input_file}")
        return

    df = pd.read_csv(input_file, encoding='utf-8-sig')
    print(f"\n📂 総データ数: {len(df):,}件")

    # 現在の状況
    has_birth = df['birth_year_int'].notna()
    has_wiki = df['wikipedia_url'].notna() & (df['wikipedia_url'] != '')
    needs_processing = has_wiki & ~has_birth

    print(f"\n✅ 生年データ取得済み: {has_birth.sum():,}件")
    print(f"📚 Wikipedia URL保有: {has_wiki.sum():,}件")
    print(f"🎯 処理対象（Wiki有り・生年無し）: {needs_processing.sum():,}件")

    # 処理対象の詳細分析
    target_df = df[needs_processing].copy()

    print("\n" + "=" * 80)
    print("📈 未処理データの分析")
    print("=" * 80)

    # 1. カテゴリ別の分布
    print("\n【カテゴリ別分布】")
    if 'category' in target_df.columns:
        category_counts = target_df['category'].value_counts()
        for cat, count in category_counts.head(10).items():
            print(f"  {cat}: {count:,}件 ({count/len(target_df)*100:.1f}%)")

    # 2. 認知度スコアの分布
    print("\n【認知度スコア分布】")
    if 'recognition_score' in target_df.columns:
        score_stats = target_df['recognition_score'].describe()
        print(f"  平均: {score_stats['mean']:.2f}")
        print(f"  中央値: {score_stats['50%']:.2f}")
        print(f"  最大値: {score_stats['max']:.2f}")
        print(f"  最小値: {score_stats['min']:.2f}")

        # スコア別の人数
        print("\n  スコア別人数:")
        bins = [0, 10, 20, 30, 40, 50, 100]
        labels = ['0-10', '10-20', '20-30', '30-40', '40-50', '50+']
        if not target_df['recognition_score'].isna().all():
            score_bins = pd.cut(target_df['recognition_score'].fillna(0), bins=bins, labels=labels)
            for label in labels:
                count = (score_bins == label).sum()
                if count > 0:
                    print(f"    {label}: {count:,}件")

    # 3. Fame Scoreの分布
    print("\n【Fame Score分布】")
    if 'fame_score' in target_df.columns:
        fame_stats = target_df['fame_score'].describe()
        print(f"  平均: {fame_stats['mean']:.0f}")
        print(f"  中央値: {fame_stats['50%']:.0f}")
        print(f"  最大値: {fame_stats['max']:.0f}")
        print(f"  最小値: {fame_stats['min']:.0f}")

    # 4. entity_type別の分布
    print("\n【エンティティタイプ別分布】")
    if 'entity_type' in target_df.columns:
        type_counts = target_df['entity_type'].value_counts()
        for etype, count in type_counts.head(5).items():
            print(f"  {etype}: {count:,}件")

    # 5. 高優先度の人物（認知度高い順）
    print("\n【高優先度の人物（未処理・認知度高い順TOP20）】")
    if 'recognition_score' in target_df.columns:
        high_priority = target_df.nlargest(20, 'recognition_score')[['person_name_display', 'recognition_score', 'category', 'wikipedia_url']]
        for idx, row in high_priority.iterrows():
            print(f"  {row['person_name_display']}: スコア{row['recognition_score']:.1f} ({row['category']})")

    # 6. 職業別の分布
    print("\n【職業別分布（TOP10）】")
    if 'occupation' in target_df.columns:
        occupation_counts = target_df['occupation'].value_counts()
        for occ, count in occupation_counts.head(10).items():
            if pd.notna(occ):
                print(f"  {occ}: {count:,}件")

    # 7. 処理済みデータの成功パターン分析
    print("\n" + "=" * 80)
    print("💡 成功パターンの分析")
    print("=" * 80)

    success_df = df[has_birth]

    if len(success_df) > 0:
        print(f"\n成功した{len(success_df)}件の特徴:")

        if 'category' in success_df.columns:
            print("\n【成功率が高いカテゴリ】")
            for cat in success_df['category'].value_counts().head(5).index:
                total_in_cat = (df['category'] == cat).sum()
                success_in_cat = (success_df['category'] == cat).sum()
                if total_in_cat > 0:
                    rate = success_in_cat / total_in_cat * 100
                    print(f"  {cat}: {rate:.1f}% ({success_in_cat}/{total_in_cat})")

        if 'occupation' in success_df.columns:
            print("\n【成功率が高い職業】")
            for occ in success_df['occupation'].value_counts().head(5).index:
                if pd.notna(occ):
                    total_in_occ = (df['occupation'] == occ).sum()
                    success_in_occ = (success_df['occupation'] == occ).sum()
                    if total_in_occ > 0:
                        rate = success_in_occ / total_in_occ * 100
                        print(f"  {occ}: {rate:.1f}% ({success_in_occ}/{total_in_occ})")

    # 効率的な処理戦略の提案
    print("\n" + "=" * 80)
    print("🚀 効率的な処理戦略の提案")
    print("=" * 80)

    print("""
1. 【優先度ベースの処理】
   - 認知度スコアが高い人物を優先（スコア30以上）
   - カテゴリ「スポーツ」「エンタメ」を優先
   - 成功率が高い職業（歌手、俳優、タレント）を優先

2. 【並列処理による高速化】
   - 5つのプロセスで同時処理（各プロセス20件）
   - API制限を考慮してプロセス間で遅延を設定

3. 【Wikidataからの一括取得】
   - SPARQL経由で生年月日を一括取得
   - Wikipedia IDからWikidata IDをマッピング

4. 【バッチ最適化】
   - 認知度スコア上位500件を優先処理
   - その後、カテゴリ別に処理

5. 【キャッシュの活用】
   - 取得済みWikitextをローカル保存
   - 再処理時の高速化
    """)

    # 統計サマリーをCSVで保存
    summary_file = 'birth_date_analysis_summary.csv'

    summary_data = {
        '項目': ['総データ数', '生年取得済み', 'Wikipedia保有', '処理対象', '推定成功可能数'],
        '件数': [
            len(df),
            has_birth.sum(),
            has_wiki.sum(),
            needs_processing.sum(),
            int(needs_processing.sum() * 0.3)  # 30%成功と仮定
        ],
        'カバー率': [
            '100%',
            f'{has_birth.sum()/len(df)*100:.1f}%',
            f'{has_wiki.sum()/len(df)*100:.1f}%',
            f'{needs_processing.sum()/len(df)*100:.1f}%',
            f'{int(needs_processing.sum() * 0.3)/len(df)*100:.1f}%'
        ]
    }

    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
    print(f"\n📊 分析結果を保存: {summary_file}")

if __name__ == '__main__':
    analyze_remaining_data()