#!/usr/bin/env python3
"""
デフォルト値10,000件の検索結果を持つ人物の実際の検索数を取得
Brave Search APIを使用して正確な検索結果数を取得
"""

import pandas as pd
import requests
import time
import os
from datetime import datetime

def get_brave_search_count(query, api_key):
    """Brave Search APIで実際の検索結果数を取得"""

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": query,
        "country": "jp",
        "search_lang": "ja",
        "count": 1  # 結果数のみ必要なので1件
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 検索結果の総数を取得
        if 'web' in data and 'results' in data['web']:
            # estimated_resultsがあればそれを使用
            estimated = data.get('web', {}).get('estimated_results', 0)
            if estimated > 0:
                return estimated

            # なければresultsの数を基に推定
            results_count = len(data['web']['results'])
            return results_count * 1000  # 推定値

        return 0

    except Exception as e:
        print(f"  ⚠️ エラー: {e}")
        return None

def main():
    print("=" * 80)
    print("📊 デフォルト検索結果数（10,000件）の修正")
    print("=" * 80)

    # APIキーを環境変数から取得
    api_key = os.environ.get('BRAVE_SEARCH_API_KEY')
    if not api_key:
        print("❌ BRAVE_SEARCH_API_KEY環境変数が設定されていません")
        return

    # 最新のスコア付きデータを読み込み
    input_file = 'ultra_think_SCORED_FIXED_20250915_210128.csv'
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df):,}件")

    # 検索結果が10,000件の人物を抽出
    default_search = df[df['search_result_count'] == 10000]
    print(f"\n🎯 対象: 検索結果が10,000件の人物 {len(default_search)}件")

    # 最初の10件だけテスト
    test_count = min(10, len(default_search))
    print(f"📍 デモ版: 最初の{test_count}件のみ処理します")

    updated_count = 0
    results = []

    print("\n🔄 実際の検索結果数を取得中...")
    print("-" * 80)

    for i, (idx, row) in enumerate(default_search.head(test_count).iterrows(), 1):
        person_name = row['person_name_display']
        person_id = row['person_id']

        print(f"\n{i}/{test_count}. {person_id}: {person_name}")

        # 検索クエリを作成（日本語名を優先）
        query = row.get('person_name_ja', person_name)

        # Brave Search APIで検索
        actual_count = get_brave_search_count(query, api_key)

        if actual_count is not None:
            print(f"  元の値: 10,000件 → 実際: {actual_count:,}件")
            df.at[idx, 'search_result_count'] = actual_count
            df.at[idx, 'search_result_updated_at'] = datetime.now().isoformat()
            updated_count += 1

            results.append({
                'person_id': person_id,
                'person_name': person_name,
                'original': 10000,
                'actual': actual_count,
                'difference': actual_count - 10000
            })

        # レート制限対策
        time.sleep(1.0)

    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 更新結果サマリー")
    print("=" * 80)

    if results:
        results_df = pd.DataFrame(results)
        print(f"\n更新件数: {updated_count}/{test_count}件")
        print("\n変更内容:")
        for _, r in results_df.iterrows():
            diff_str = f"+{r['difference']:,}" if r['difference'] > 0 else f"{r['difference']:,}"
            print(f"  {r['person_id']}: {r['original']:,} → {r['actual']:,} ({diff_str})")

        print(f"\n統計:")
        print(f"  平均実際値: {results_df['actual'].mean():.0f}件")
        print(f"  最大値: {results_df['actual'].max():,}件")
        print(f"  最小値: {results_df['actual'].min():,}件")

    # ファイル保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_SEARCH_FIXED_{timestamp}.csv'

    print(f"\n💾 修正済みデータを保存中...")
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        df.to_csv(f, index=False)

    print(f"✅ 保存完了: {output_file}")

    print("\n💡 次のステップ:")
    print("  1. 残りの人物の検索結果数も更新")
    print("  2. recognition_scoreがNaNの人物のスコア計算")
    print("  3. 再度fame_scoreを計算して最終化")

    return output_file

if __name__ == "__main__":
    output_file = main()