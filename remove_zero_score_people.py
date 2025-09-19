#!/usr/bin/env python3
"""
fame_score=0かつsearch_result_count=0の人物を削除
有名人とは言えない人物をデータベースから除外
"""

import pandas as pd
from datetime import datetime

def main():
    print("=" * 80)
    print("🗑️ fame_score=0かつsearch_result_count=0の人物を削除")
    print("=" * 80)

    # 最新のスコア付きデータを読み込み
    input_file = 'ultra_think_SCORED_FIXED_20250915_211322.csv'
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df):,}件")

    # 削除対象を特定
    delete_condition = (df['fame_score'] == 0) & (df['search_result_count'] == 0)
    delete_targets = df[delete_condition]

    print(f"\n🎯 削除対象:")
    print(f"  fame_score = 0: {len(df[df['fame_score'] == 0]):,}件")
    print(f"  search_result_count = 0: {len(df[df['search_result_count'] == 0]):,}件")
    print(f"  両方が0（削除対象）: {len(delete_targets):,}件")

    # 削除対象の詳細を表示
    if len(delete_targets) > 0:
        print("\n📋 削除対象の例（最初の20件）:")
        print("-" * 80)
        for i, (idx, row) in enumerate(delete_targets.head(20).iterrows(), 1):
            print(f"{i:3d}. {row['person_id']}: {row['person_name_display'][:40]:40s} | Wikipedia: {row.get('wikipedia_status', 'N/A')}")

        # カテゴリ別集計
        print("\n📊 削除対象のカテゴリ別分布:")
        category_counts = delete_targets['category'].value_counts().head(10)
        for cat, count in category_counts.items():
            print(f"  {cat}: {count}件")

        # Wikipedia状態別集計
        print("\n📚 削除対象のWikipedia状態:")
        wiki_counts = delete_targets['wikipedia_status'].value_counts()
        for status, count in wiki_counts.items():
            print(f"  {status}: {count}件")

    # 削除実行
    print("\n🔄 削除を実行中...")
    df_cleaned = df[~delete_condition].copy()

    # 削除結果
    deleted_count = len(df) - len(df_cleaned)
    print(f"✅ {deleted_count}件を削除しました")

    # 削除後の統計
    print("\n📈 削除後の統計:")
    print(f"  残存レコード数: {len(df_cleaned):,}件")
    print(f"  削除率: {deleted_count/len(df)*100:.1f}%")
    print(f"  fame_score > 0: {len(df_cleaned[df_cleaned['fame_score'] > 0]):,}件")
    print(f"  平均fame_score: {df_cleaned['fame_score'].mean():.1f}")

    # スコア分布（削除後）
    print("\n📊 削除後のfame_score分布:")
    print(f"  超S級（9000-10000）: {len(df_cleaned[df_cleaned['fame_score'] >= 9000]):,}件")
    print(f"  S級（7000-8999）: {len(df_cleaned[(df_cleaned['fame_score'] >= 7000) & (df_cleaned['fame_score'] < 9000)]):,}件")
    print(f"  A級（5000-6999）: {len(df_cleaned[(df_cleaned['fame_score'] >= 5000) & (df_cleaned['fame_score'] < 7000)]):,}件")
    print(f"  B級（3000-4999）: {len(df_cleaned[(df_cleaned['fame_score'] >= 3000) & (df_cleaned['fame_score'] < 5000)]):,}件")
    print(f"  C級（1000-2999）: {len(df_cleaned[(df_cleaned['fame_score'] >= 1000) & (df_cleaned['fame_score'] < 3000)]):,}件")
    print(f"  D級（1-999）: {len(df_cleaned[(df_cleaned['fame_score'] >= 1) & (df_cleaned['fame_score'] < 1000)]):,}件")

    # ファイル保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_CLEANED_{timestamp}.csv'

    print(f"\n💾 クリーンなデータを保存中...")
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        df_cleaned.to_csv(f, index=False)

    print(f"✅ 保存完了: {output_file}")

    # 削除リストも保存
    if len(delete_targets) > 0:
        delete_list_file = f'deleted_people_{timestamp}.csv'
        with open(delete_list_file, 'w', encoding='utf-8-sig') as f:
            delete_targets[['person_id', 'person_name_display', 'category', 'wikipedia_status']].to_csv(f, index=False)
        print(f"📄 削除リスト: {delete_list_file}")

    # サマリー
    print("\n" + "=" * 80)
    print("✅ クリーニング完了！")
    print("=" * 80)
    print(f"  削除件数: {deleted_count}件")
    print(f"  残存件数: {len(df_cleaned):,}件")
    print(f"  出力ファイル: {output_file}")

    return output_file, df_cleaned

if __name__ == "__main__":
    output_file, df = main()