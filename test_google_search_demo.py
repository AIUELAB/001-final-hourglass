#!/usr/bin/env python3
"""
Google検索結果数取得のデモテスト（5件のみ）
"""

import asyncio
import sys
import os

# 親ディレクトリのモジュールをインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from get_google_search_counts import GoogleSearchCounter
import pandas as pd

async def test_demo():
    """デモテスト実行"""

    print("=" * 60)
    print("Google検索結果数取得 - デモテスト（5件）")
    print("=" * 60)

    # テストデータ作成
    test_data = pd.DataFrame([
        {
            'person_name': 'ひかきん',
            'person_name_display': 'HIKAKIN',
            'occupation': 'YouTuber',
            'category': 'エンタメ',
            'group_name': '',
            'name_recognition': 95,
            'wikipedia_status': '存在',
            'wikipedia_content_length': 15000
        },
        {
            'person_name': 'おおたにしょうへい',
            'person_name_display': '大谷翔平',
            'occupation': '野球選手',
            'category': 'スポーツ',
            'group_name': '',
            'name_recognition': 98,
            'wikipedia_status': '存在',
            'wikipedia_content_length': 25000
        },
        {
            'person_name': 'あらしだん',
            'person_name_display': '嵐',
            'occupation': 'アイドルグループ',
            'category': 'エンタメ',
            'group_name': '嵐',
            'name_recognition': 90,
            'wikipedia_status': '存在',
            'wikipedia_content_length': 20000
        },
        {
            'person_name': 'よねづけんし',
            'person_name_display': '米津玄師',
            'occupation': 'シンガーソングライター',
            'category': 'エンタメ',
            'group_name': '',
            'name_recognition': 85,
            'wikipedia_status': '存在',
            'wikipedia_content_length': 12000
        },
        {
            'person_name': 'あべしんぞう',
            'person_name_display': '安倍晋三',
            'occupation': '政治家',
            'category': '政治',
            'group_name': '',
            'name_recognition': 95,
            'wikipedia_status': '存在',
            'wikipedia_content_length': 30000
        }
    ])

    # 検索カウンター初期化
    counter = GoogleSearchCounter()

    # 優先度スコア計算
    test_data = counter.calculate_priority_score(test_data)

    print("\n📊 テストデータの優先度スコア:")
    for idx, row in test_data.iterrows():
        print(f"  {row['person_name_display']}: {row['priority_score']:.1f}点")

    # 新しいカラムを追加
    test_data['google_search_count'] = 0
    test_data['search_query'] = ''
    test_data['search_timestamp'] = ''
    test_data['is_predicted'] = False

    # 検索実行
    print("\n🔍 Google検索実行中...")
    test_data = await counter.batch_search(test_data, limit=5)

    # 結果表示
    print("\n✅ 検索結果:")
    for idx, row in test_data.iterrows():
        if row['google_search_count'] > 0:
            print(f"  {row['person_name_display']}: {row['google_search_count']:,}件")
            print(f"    クエリ: {row['search_query']}")

    # 統計表示
    valid_results = test_data[test_data['google_search_count'] > 0]
    if len(valid_results) > 0:
        print(f"\n📊 統計:")
        print(f"  成功: {len(valid_results)}/5件")
        print(f"  平均: {valid_results['google_search_count'].mean():,.0f}件")
        print(f"  最大: {valid_results['google_search_count'].max():,}件")
        print(f"  最小: {valid_results['google_search_count'].min():,}件")

    return test_data

if __name__ == "__main__":
    result = asyncio.run(test_demo())
    print("\n✅ デモテスト完了！")