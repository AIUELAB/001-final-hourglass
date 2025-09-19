#!/usr/bin/env python3
"""
WikipediaAPIから生年月日情報を高速抽出（最初の100件のみ）
"""

import pandas as pd
import requests
import time
import re
from datetime import datetime
import json

def extract_birth_info_from_wikitext(wikitext):
    """Wikitextから生年月日情報を高速抽出"""

    # 最も一般的なパターンのみチェック
    # 生年月日 = {{生年月日と年齢|YYYY|MM|DD}}
    match = re.search(r'生年月日\s*=\s*\{\{生年月日と年齢\|(\d{4})\|(\d{1,2})\|(\d{1,2})', wikitext)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}", year

    # 生年月日 = YYYY年MM月DD日
    match = re.search(r'生年月日\s*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日', wikitext)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}", year

    # 年のみ
    match = re.search(r'生年月日\s*=\s*(\d{4})年', wikitext)
    if match:
        year = int(match.group(1))
        return None, year

    return None, None

def get_wikipedia_birth_info_batch(titles_batch):
    """複数のWikipediaページから一括で生年月日情報を取得"""

    api_url = "https://ja.wikipedia.org/w/api.php"

    # パイプで区切って複数タイトルを一度にクエリ
    titles_str = '|'.join(titles_batch)

    params = {
        'action': 'query',
        'prop': 'revisions',
        'titles': titles_str,
        'rvslots': '*',
        'rvprop': 'content',
        'format': 'json',
        'formatversion': '2'
    }

    results = {}

    try:
        response = requests.get(api_url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()

            if 'query' in data and 'pages' in data['query']:
                for page in data['query']['pages']:
                    if 'title' in page and 'revisions' in page and len(page['revisions']) > 0:
                        title = page['title']
                        wikitext = page['revisions'][0]['slots']['main']['content']
                        birth_date, birth_year = extract_birth_info_from_wikitext(wikitext)
                        results[title] = (birth_date, birth_year)

    except Exception as e:
        print(f"  ❌ バッチエラー: {e}")

    return results

def main():
    print("=" * 80)
    print("📅 Wikipedia APIから生年月日情報を高速抽出（最初の100件）")
    print("=" * 80)

    # データ読み込み
    input_file = 'ultra_think_CLEANED_20250915_213042.csv'
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df):,}件")

    # 新しいカラムを追加
    df['birth_date'] = None
    df['birth_year_int'] = None

    # Wikipedia URLがある人物を対象（最初の100件のみ）
    wiki_mask = df['wikipedia_url'].notna() & (df['wikipedia_url'] != '')
    target_df = df[wiki_mask].head(100)  # 最初の100件に限定
    print(f"\n🎯 処理対象: Wikipedia URLがある最初の {len(target_df)}件")

    # URLからタイトルを抽出
    titles_map = {}
    for idx, row in target_df.iterrows():
        url = row['wikipedia_url']
        title_match = re.search(r'/wiki/(.+)$', url)
        if title_match:
            title = title_match.group(1)
            titles_map[title] = idx

    print(f"📡 {len(titles_map)}件のWikipediaページを処理...")

    # 10件ずつバッチ処理
    titles_list = list(titles_map.keys())
    batch_size = 10
    success_count = 0
    birth_date_count = 0
    birth_year_count = 0

    for i in range(0, len(titles_list), batch_size):
        batch = titles_list[i:i + batch_size]
        print(f"\n  バッチ {i//batch_size + 1}/{(len(titles_list) + batch_size - 1)//batch_size} 処理中...")

        results = get_wikipedia_birth_info_batch(batch)

        for title, (birth_date, birth_year) in results.items():
            if title in titles_map:
                idx = titles_map[title]
                person_name = df.at[idx, 'person_name_display']

                if birth_date or birth_year:
                    success_count += 1

                    if birth_date:
                        df.at[idx, 'birth_date'] = birth_date
                        birth_date_count += 1
                        print(f"    ✅ {person_name}: 生年月日 {birth_date}")

                    if birth_year:
                        df.at[idx, 'birth_year_int'] = birth_year
                        birth_year_count += 1
                        if not birth_date:
                            print(f"    📅 {person_name}: 生年 {birth_year}")

        # レート制限対策
        time.sleep(1)

    # 統計情報
    print("\n" + "=" * 80)
    print("📊 取得結果統計")
    print("=" * 80)
    print(f"  処理対象: {len(target_df)}件")
    print(f"  情報取得成功: {success_count}件 ({success_count/len(target_df)*100:.1f}%)")
    print(f"  生年月日取得: {birth_date_count}件")
    print(f"  生年のみ取得: {birth_year_count - birth_date_count}件")

    # ファイル保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_WITH_BIRTH_{timestamp}.csv'

    print(f"\n💾 生年月日情報を追加したデータを保存中...")
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        df.to_csv(f, index=False)

    print(f"✅ 保存完了: {output_file}")

    # サンプル表示
    sample_with_birth = df[df['birth_date'].notna()].head(10)
    if len(sample_with_birth) > 0:
        print("\n📋 生年月日取得成功例:")
        print("-" * 80)
        for i, (idx, row) in enumerate(sample_with_birth.iterrows(), 1):
            print(f"{i:2d}. {row['person_name_display']}")
            print(f"    生年月日: {row['birth_date']}, 生年: {row['birth_year_int']}")

    # サマリー
    print("\n" + "=" * 80)
    print("✅ 生年月日情報追加完了！")
    print("=" * 80)
    print(f"  出力: {output_file}")
    print(f"  追加フィールド:")
    print(f"    - birth_date: 生年月日 (YYYY-MM-DD形式)")
    print(f"    - birth_year_int: 生年 (整数)")

    return output_file, df

if __name__ == "__main__":
    output_file, df = main()