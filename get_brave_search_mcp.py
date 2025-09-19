#!/usr/bin/env python3
"""
MCP Brave Searchツールを使って残り1,000件の検索結果数を取得
既存の1,000件に追加して合計2,000件にする
"""

import pandas as pd
import time
from datetime import datetime
import json
import os

def main():
    print("=" * 60)
    print("🔍 Brave Search (MCP) - 追加1,000件取得")
    print("=" * 60)

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

    # 優先度スコアを再計算して上位1,000件を選択
    not_searched['priority_score'] = (
        not_searched['name_recognition'].fillna(0) * 0.4 +
        (not_searched['wikipedia_url'].notna().astype(int) * 20) * 0.3 +
        not_searched['category'].map({
            'エンタメ': 10, 'スポーツ': 9, '政治': 8,
            'ビジネス': 7, '科学': 6, '芸術': 5,
            '歴史': 4, 'その他': 3, '架空の存在': 2
        }).fillna(0) * 0.3
    )

    # 優先度順にソートして上位1,000件を選択
    not_searched = not_searched.nlargest(1000, 'priority_score')
    print(f"\n🎯 追加取得対象: {len(not_searched)}件（優先度順）")

    # 最初の10件のみを処理（テスト）
    test_count = 10
    print(f"\n⚠️ テストモード: 最初の{test_count}件のみ処理します")
    not_searched = not_searched.head(test_count)

    # 取得対象を表示
    print("\n📋 取得対象リスト:")
    for i, (_, row) in enumerate(not_searched.head(10).iterrows(), 1):
        print(f"  {i:2d}. {row['person_name_display']}")

    # 処理実行の確認
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_brave_mcp_{timestamp}.csv'

    print(f"\n💾 結果は以下のファイルに保存されます:")
    print(f"  {output_file}")

    # 設定を保存
    config = {
        'csv_file': csv_file,
        'output_file': output_file,
        'target_count': len(not_searched),
        'timestamp': timestamp
    }

    config_file = 'brave_search_config.json'
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 設定ファイル作成: {config_file}")
    print("\n🚀 MCPツールで検索を実行してください")

if __name__ == "__main__":
    main()