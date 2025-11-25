#!/usr/bin/env python3
"""
新しいBrave Search APIキーを使って残り全件（2,569件）の検索を実行
既存の1,000件と合わせて全3,569件を完成させる
"""

import pandas as pd
import time
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()

def main():
    print("=" * 60)
    print("🚀 Brave Search API - 全件取得（残り2,569件）")
    print("=" * 60)

    # 新しいAPIキーを読み込み
    api_key_file = '/Users/admin/Documents/key/Brave Search API Key 2.txt'
    with open(api_key_file, 'r') as f:
        new_api_key = f.read().strip()

    print(f"✅ 新しいAPIキー読み込み完了")
    print(f"   キー: {new_api_key[:10]}...")

    # CSVファイルを読み込み
    csv_file = 'ultra_think_with_search_counts_20250915_140948.csv'
    print(f"\n📂 ファイル読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    print(f"✅ {len(df)}件のデータを読み込みました")

    # 既にBrave Searchで取得済みのデータを確認
    already_searched = df[df['search_source'] == 'brave_search']
    print(f"\n📊 既存のBrave Search取得済み: {len(already_searched)}件")

    # 未取得のデータ（predictionのもの）を抽出
    not_searched = df[df['search_source'] != 'brave_search'].copy()
    print(f"📊 未取得データ: {len(not_searched)}件")

    if len(not_searched) == 0:
        print("✅ すべてのデータは既に取得済みです")
        return

    print(f"\n🎯 全{len(not_searched)}件を取得予定")
    print(f"   予想処理時間: 約{len(not_searched) * 0.5 / 60:.1f}分（0.5秒/件）")

    # MCPツールで取得するため、対象リストを保存
    target_persons = []
    for _, row in not_searched.iterrows():
        target_persons.append({
            'person_id': row['person_id'],
            'person_name_display': row['person_name_display'],
            'category': row['category'],
            'index': row.name
        })

    # バッチサイズを設定（100件ずつ処理）
    batch_size = 100
    num_batches = (len(target_persons) + batch_size - 1) // batch_size

    print(f"\n📦 バッチ処理設定:")
    print(f"   バッチサイズ: {batch_size}件")
    print(f"   バッチ数: {num_batches}")

    # 処理対象をJSON形式で保存
    config = {
        'api_key': new_api_key,
        'csv_file': csv_file,
        'total_targets': len(target_persons),
        'batch_size': batch_size,
        'num_batches': num_batches,
        'timestamp': datetime.now().isoformat(),
        'targets': target_persons
    }

    config_file = 'brave_search_all_config.json'
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 設定ファイル作成: {config_file}")
    print(f"   総対象数: {len(target_persons)}件")

    # 最初の10件を表示
    print(f"\n📋 最初の10件:")
    for i, person in enumerate(target_persons[:10], 1):
        print(f"  {i:2d}. {person['person_name_display']} ({person['category']})")

    print(f"\n💡 次のステップ:")
    print(f"   1. MCPのBrave Searchツールで処理実行")
    print(f"   2. バッチごとに進捗を確認")
    print(f"   3. 全件完了後、CSVファイルを統合")
    print(f"   4. Google Sheetsに最終同期")

    # 統計情報
    print(f"\n📊 APIキー使用計画:")
    print(f"   既存キー1: 1,000件使用済み / 2,000件")
    print(f"   新規キー2: {len(not_searched)}件使用予定 / 2,000件")

    if len(not_searched) > 2000:
        print(f"   ⚠️ 警告: 必要件数が無料枠を超えています")
        print(f"   不足分: {len(not_searched) - 2000}件")
    else:
        print(f"   ✅ 無料枠内で全件取得可能")
        print(f"   残り枠: {2000 - len(not_searched)}件")

if __name__ == "__main__":
    main()
