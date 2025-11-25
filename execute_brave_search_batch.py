#!/usr/bin/env python3
"""
Brave Search APIを使って実際に検索を実行
新しいAPIキーで最大2,000件を取得
"""

import pandas as pd
import requests
import time
from datetime import datetime
import json
import os

def search_brave(query, api_key):
    """Brave Search APIで検索を実行（結果数の推定）"""
    url = "https://api.search.brave.com/res/v1/web/search"

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }

    params = {
        "q": query,
        "count": 10,  # 10件取得して結果を推定
        "text_decorations": False,
        "spellcheck": False
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            # 検索結果から推定値を計算
            if "web" in data and "results" in data["web"]:
                results = data["web"]["results"]
                result_count = len(results)

                # 結果数に基づいて推定値を返す
                if result_count >= 10:
                    return 1000000  # 10件完全 = 100万件以上と推定
                elif result_count >= 5:
                    return 100000   # 5-9件 = 10万件程度と推定
                elif result_count >= 1:
                    return 10000    # 1-4件 = 1万件程度と推定
                else:
                    return 100      # 結果なし = 100件未満
            return 0

        elif response.status_code == 429:
            print(f"⚠️ レート制限")
            return None
        else:
            print(f"❌ エラー: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ 例外: {e}")
        return None

def main():
    print("=" * 60)
    print("🚀 Brave Search API実行 - 新APIキーで2,000件取得")
    print("=" * 60)

    # 新しいAPIキーを読み込み
    api_key_file = '/Users/admin/Documents/key/Brave Search API Key 2.txt'
    with open(api_key_file, 'r') as f:
        api_key = f.read().strip()

    print(f"✅ APIキー読み込み完了")

    # 設定ファイルを読み込み
    with open('brave_search_all_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    targets = config['targets'][:2000]  # 最初の2,000件のみ
    print(f"\n📊 処理対象: {len(targets)}件")

    # CSVファイルを読み込み
    csv_file = config['csv_file']
    df = pd.read_csv(csv_file)
    print(f"📂 CSVファイル: {csv_file}")

    # バッチ処理
    batch_size = 50  # 50件ずつ処理
    success_count = 0
    error_count = 0

    print("\n" + "=" * 60)
    print("📡 検索実行開始")
    print("=" * 60)

    for batch_idx in range(0, len(targets), batch_size):
        batch = targets[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        total_batches = (len(targets) + batch_size - 1) // batch_size

        print(f"\n📦 バッチ {batch_num}/{total_batches} 処理中...")

        for person in batch:
            query = f'"{person["person_name_display"]}"'

            # API呼び出し
            result = search_brave(query, api_key)

            if result is not None:
                # データフレームを更新
                idx = person['index']
                df.loc[idx, 'search_result_count'] = result
                df.loc[idx, 'search_query'] = query
                df.loc[idx, 'search_timestamp'] = datetime.now().isoformat()
                df.loc[idx, 'search_source'] = 'brave_search_v2'

                success_count += 1

                # 進捗表示（10件ごと）
                if success_count % 10 == 0:
                    print(f"   ✅ {success_count}件完了")
            else:
                error_count += 1
                if error_count > 50:
                    print("⚠️ エラーが多いため中断")
                    break

            # レート制限対策（0.3秒待機）
            time.sleep(0.3)

        # バッチごとに保存（バックアップ）
        if success_count % 100 == 0:
            backup_file = f'brave_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            with open(backup_file, 'w', encoding='utf-8-sig') as f:
                df.to_csv(f, index=False)
            print(f"   💾 バックアップ保存: {backup_file}")

    # 最終結果を保存
    print("\n" + "=" * 60)
    print("💾 最終結果を保存")
    print("=" * 60)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_brave_complete_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        df.to_csv(f, index=False)

    print(f"✅ 保存完了: {output_file}")

    # 統計表示
    brave_count = len(df[(df['search_source'] == 'brave_search') |
                         (df['search_source'] == 'brave_search_v2')])

    print(f"\n📊 最終統計:")
    print(f"  総レコード数: {len(df):,}件")
    print(f"  Brave Search取得済み: {brave_count:,}件 ({brave_count/len(df)*100:.1f}%)")
    print(f"    - 既存キー: {len(df[df['search_source'] == 'brave_search']):,}件")
    print(f"    - 新規キー: {success_count:,}件")
    print(f"  残り: {len(df) - brave_count:,}件")

if __name__ == "__main__":
    main()
