#!/usr/bin/env python3
"""
3つのBrave Search APIキーを使って全3,569件の検索を実行
APIキー1: 既に1,000件使用済み（残り1,000件）
APIキー2: 2,000件使用可能
APIキー3: 2,000件使用可能
合計: 5,000件の枠で2,569件を取得
"""

import pandas as pd
import time
from datetime import datetime
import json
import os
import sys

def test_brave_api(api_key):
    """Brave Search APIのテスト"""
    import requests

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": "test",
        "count": 1
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        return response.status_code == 200
    except:
        return False

def main():
    print("=" * 60)
    print("🚀 Brave Search API - 全3,569件取得")
    print("=" * 60)

    # APIキーを読み込み
    api_keys = []

    # APIキー2（新規）
    with open('/Users/admin/Documents/key/Brave Search API Key 2.txt', 'r') as f:
        api_key2 = f.read().strip()
        api_keys.append(('APIキー2', api_key2, 2000))

    # APIキー3（新規）
    with open('/Users/admin/Documents/key/Brave Search API Key 3.txt', 'r') as f:
        api_key3 = f.read().strip()
        api_keys.append(('APIキー3', api_key3, 2000))

    print(f"\n✅ APIキー読み込み完了:")
    print(f"   APIキー1: 1,000件使用済み（残り1,000件）")
    print(f"   APIキー2: 2,000件使用可能")
    print(f"   APIキー3: 2,000件使用可能")
    print(f"   合計: 5,000件の枠")

    # APIキーをテスト
    print(f"\n🔍 APIキー検証中...")
    for name, key, _ in api_keys:
        if test_brave_api(key):
            print(f"   ✅ {name}: 正常")
        else:
            print(f"   ❌ {name}: エラー")
            sys.exit(1)

    # CSVファイルを読み込み
    csv_file = 'ultra_think_with_search_counts_20250915_140948.csv'
    print(f"\n📂 ファイル読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    print(f"✅ {len(df)}件のデータを読み込みました")

    # 既にBrave Searchで取得済みのデータを確認
    already_searched = df[df['search_source'] == 'brave_search']
    print(f"\n📊 既存のBrave Search取得済み: {len(already_searched)}件")

    # 未取得のデータ（predictionのもの）を抽出
    not_searched = df[df['search_source'] != 'brave_search']
    print(f"📊 未取得データ: {len(not_searched)}件")

    if len(not_searched) == 0:
        print("✅ すべてのデータは既に取得済みです")
        return

    # 処理計画を表示
    print(f"\n📋 処理計画:")
    print(f"   総レコード数: {len(df):,}件")
    print(f"   既に取得済み: {len(already_searched):,}件")
    print(f"   今回取得予定: {len(not_searched):,}件")

    # 実行プランを作成
    plan = {
        'total_records': len(df),
        'already_done': len(already_searched),
        'to_process': len(not_searched),
        'api_keys': [
            {'name': 'APIキー2', 'quota': 2000},
            {'name': 'APIキー3', 'quota': 2000}
        ],
        'timestamp': datetime.now().isoformat()
    }

    # プランを保存
    plan_file = 'brave_search_execution_plan.json'
    with open(plan_file, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 実行プラン保存: {plan_file}")

    # 実行確認
    print(f"\n🎯 実行内容:")
    print(f"   1. APIキー2で最初の2,000件を取得")
    print(f"   2. APIキー3で残り{len(not_searched)-2000}件を取得")
    print(f"   3. 合計{len(not_searched)}件の実データを追加")
    print(f"   4. 最終的に全{len(df)}件が実データに")

    print(f"\n⏱️ 予想処理時間: 約{len(not_searched) * 0.3 / 60:.1f}分")
    print(f"\n💡 別スクリプトで実際の検索を実行してください")

if __name__ == "__main__":
    main()