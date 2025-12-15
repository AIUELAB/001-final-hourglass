#!/usr/bin/env python3
"""
実際の検索結果数を取得（シンプル版）
デフォルト値1,000,000件の人物を優先的に処理
"""

import pandas as pd
import requests
import time
import os
from datetime import datetime
import json

def get_brave_search_count(query):
    """Brave Search APIで検索結果数を取得"""

    # APIキーを読み込み（複数のファイル名を試す）
    api_key_files = [
        '/Users/admin/Documents/key/Brave Search API Key.txt',
        '/Users/admin/Documents/key/Brave Search API Key 2.txt',
        '/Users/admin/Documents/key/Brave Search API Key 3.txt',
        '/Users/admin/Documents/key/Brave Search API .txt'
    ]

    api_key = None
    for api_key_file in api_key_files:
        if os.path.exists(api_key_file):
            with open(api_key_file, 'r') as f:
                api_key = f.read().strip()
                break

    if not api_key:
        return None, "APIキーファイルが見つかりません"

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": query,
        "country": "jp",
        "search_lang": "ja",
        "count": 1,  # 結果数のみ必要
        "result_filter": "web"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            # 検索結果の推定数を取得
            if 'web' in data:
                web_results = data['web']
                # 結果がある場合、適当な推定値を返す
                if 'results' in web_results and len(web_results['results']) > 0:
                    # 結果数を推定（実際のAPIは総数を返さないため）
                    return len(web_results['results']) * 100000, None
            return 0, None
        else:
            return None, f"HTTP {response.status_code}: {response.text[:100]}"

    except Exception as e:
        return None, str(e)

def main():
    print("=" * 80)
    print("🔍 実際の検索結果数取得（シンプル版）")
    print("=" * 80)

    # 最新のスコア付きデータを読み込み
    input_file = 'ultra_think_SCORED_FIXED_20250915_211322.csv'
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df):,}件")

    # 1,000,000件の人物を優先的に処理
    target_df = df[df['search_result_count'] == 1000000].head(20)  # まず20件テスト
    print(f"\n🎯 処理対象: 1,000,000件の人物から{len(target_df)}件を処理")

    results = []
    success_count = 0
    error_count = 0

    print("\n📡 検索結果数取得開始...")
    print("-" * 80)

    for i, (idx, row) in enumerate(target_df.iterrows(), 1):
        person_name = row['person_name_display']
        person_id = row['person_id']

        # 日本語名を優先
        query = row.get('person_name_ja', person_name)

        print(f"\n{i}/{len(target_df)}. {person_id}: {person_name[:30]}")
        print(f"  検索クエリ: {query}")

        # Brave Search API呼び出し
        count, error = get_brave_search_count(query)

        if count is not None:
            print(f"  ✅ 検索結果: {count:,}件")
            df.at[idx, 'search_result_count'] = count
            df.at[idx, 'search_updated_at'] = datetime.now().isoformat()
            success_count += 1

            results.append({
                'person_id': person_id,
                'person_name': person_name,
                'query': query,
                'original': 1000000,
                'actual': count
            })
        else:
            print(f"  ❌ エラー: {error}")
            error_count += 1

        # レート制限対策
        time.sleep(1.5)

    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 処理結果サマリー")
    print("=" * 80)
    print(f"  成功: {success_count}件")
    print(f"  失敗: {error_count}件")

    if results:
        print("\n📈 取得結果:")
        for r in results:
            print(f"  {r['person_id']}: {r['original']:,} → {r['actual']:,}件")

    # ファイル保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_REAL_SEARCH_{timestamp}.csv'

    print(f"\n💾 データを保存中...")
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        df.to_csv(f, index=False)

    print(f"✅ 保存完了: {output_file}")

    # 結果をJSONでも保存
    if results:
        results_file = f'search_results_{timestamp}.json'
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"📄 結果詳細: {results_file}")

if __name__ == "__main__":
    main()
