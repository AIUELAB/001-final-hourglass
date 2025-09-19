#!/usr/bin/env python3
"""
WikipediaAPIから生年月日情報を抽出（User-Agent設定版）
"""

import pandas as pd
import requests
import time
import re
from datetime import datetime
import urllib.parse

def extract_birth_info_from_wikitext(wikitext):
    """Wikitextから生年月日情報を抽出"""

    # 生年月日パターン
    patterns = [
        # {{生年月日と年齢|YYYY|MM|DD}}
        (r'\{\{生年月日と年齢\|(\d{4})\|(\d{1,2})\|(\d{1,2})', True),
        # {{Birth date|YYYY|MM|DD}}
        (r'\{\{Birth date\|(\d{4})\|(\d{1,2})\|(\d{1,2})', True),
        # {{Birth date and age|YYYY|MM|DD}}
        (r'\{\{Birth date and age\|(\d{4})\|(\d{1,2})\|(\d{1,2})', True),
        # YYYY年MM月DD日
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日', True),
        # 生年のみ: YYYY年
        (r'(\d{4})年', False),
    ]

    # 生年月日セクションを探す
    birth_section = None
    if '生年月日' in wikitext:
        match = re.search(r'生年月日[^=]*=([^\n|]+)', wikitext)
        if match:
            birth_section = match.group(1)
    elif '生誕' in wikitext:
        match = re.search(r'生誕[^=]*=([^\n|]+)', wikitext)
        if match:
            birth_section = match.group(1)

    if birth_section:
        # セクション内でパターンマッチ
        for pattern, is_full_date in patterns:
            match = re.search(pattern, birth_section)
            if match:
                year = int(match.group(1))
                if is_full_date and len(match.groups()) >= 3:
                    month = int(match.group(2))
                    day = int(match.group(3))
                    return f"{year:04d}-{month:02d}-{day:02d}", year
                else:
                    return None, year

    # セクションが見つからない場合は全文検索
    for pattern, is_full_date in patterns:
        match = re.search(pattern, wikitext[:3000])  # 最初の3000文字のみ
        if match:
            year = int(match.group(1))
            if is_full_date and len(match.groups()) >= 3:
                month = int(match.group(2))
                day = int(match.group(3))
                # 妥当性チェック
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return f"{year:04d}-{month:02d}-{day:02d}", year
            else:
                return None, year

    return None, None

def get_wikipedia_content(wikipedia_url):
    """Wikipedia URLからページコンテンツを取得"""

    if not wikipedia_url or pd.isna(wikipedia_url):
        return None

    # URLからページタイトルを抽出
    title_match = re.search(r'/wiki/(.+)$', wikipedia_url)
    if not title_match:
        return None

    page_title = urllib.parse.unquote(title_match.group(1))

    # Wikipedia APIエンドポイント
    api_url = "https://ja.wikipedia.org/w/api.php"

    # User-Agentを設定
    headers = {
        'User-Agent': 'BirthDateExtractor/1.0 (https://example.com/contact)'
    }

    params = {
        'action': 'query',
        'prop': 'revisions',
        'titles': page_title,
        'rvslots': '*',
        'rvprop': 'content',
        'format': 'json',
        'formatversion': '2'
    }

    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()

            if 'query' in data and 'pages' in data['query']:
                pages = data['query']['pages']
                if pages and len(pages) > 0:
                    page = pages[0]
                    if 'revisions' in page and len(page['revisions']) > 0:
                        wikitext = page['revisions'][0]['slots']['main']['content']
                        return wikitext

    except Exception as e:
        return None

    return None

def main():
    print("=" * 80)
    print("📅 Wikipedia APIから生年月日情報を抽出（User-Agent設定版）")
    print("=" * 80)

    # データ読み込み
    input_file = 'ultra_think_CLEANED_20250915_213042.csv'
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df):,}件")

    # 新しいカラムを追加
    if 'birth_date' not in df.columns:
        df['birth_date'] = None
    if 'birth_year_int' not in df.columns:
        df['birth_year_int'] = None

    # Wikipedia URLがある人物を対象（最初の50件でテスト）
    wiki_mask = df['wikipedia_url'].notna() & (df['wikipedia_url'] != '')
    target_df = df[wiki_mask].head(50)
    print(f"\n🎯 処理対象: Wikipedia URLがある最初の {len(target_df)}件")

    success_count = 0
    birth_date_count = 0
    birth_year_count = 0

    print(f"\n📡 Wikipedia APIから情報取得開始...")
    print("-" * 80)

    for i, (idx, row) in enumerate(target_df.iterrows(), 1):
        person_id = row['person_id']
        person_name = row['person_name_display']
        wikipedia_url = row['wikipedia_url']

        if i % 10 == 1:
            print(f"\n処理中: {i}/{len(target_df)}")

        # Wikipedia コンテンツ取得
        wikitext = get_wikipedia_content(wikipedia_url)

        if wikitext:
            # 生年月日を抽出
            birth_date, birth_year = extract_birth_info_from_wikitext(wikitext)

            if birth_date or birth_year:
                success_count += 1

                if birth_date:
                    df.at[idx, 'birth_date'] = birth_date
                    birth_date_count += 1
                    print(f"  ✅ {person_name}: 生年月日 {birth_date}")

                if birth_year:
                    df.at[idx, 'birth_year_int'] = birth_year
                    birth_year_count += 1
                    if not birth_date:
                        print(f"  📅 {person_name}: 生年 {birth_year}")

        # レート制限対策
        time.sleep(0.5)

    # 統計情報
    print("\n" + "=" * 80)
    print("📊 取得結果統計")
    print("=" * 80)
    print(f"  処理対象: {len(target_df)}件")
    print(f"  情報取得成功: {success_count}件 ({success_count/len(target_df)*100:.1f}%)")
    print(f"  生年月日取得: {birth_date_count}件")
    print(f"  生年のみ取得: {birth_year_count - birth_date_count}件")

    # 生年分布
    birth_years = df['birth_year_int'].dropna()
    if len(birth_years) > 0:
        print(f"\n📈 生年分布:")
        print(f"  最古: {int(birth_years.min())}年")
        print(f"  最新: {int(birth_years.max())}年")
        print(f"  平均: {birth_years.mean():.0f}年")

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