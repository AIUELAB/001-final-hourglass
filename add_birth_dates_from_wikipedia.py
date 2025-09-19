#!/usr/bin/env python3
"""
WikipediaAPIから生年月日情報を抽出してデータセットに追加
"""

import pandas as pd
import requests
import time
import re
from datetime import datetime
import json

def extract_birth_date_from_wikitext(wikitext):
    """WikitextからInfoboxの生年月日を抽出"""

    # Infoboxのパターン
    patterns = [
        # 生年月日 = YYYY年MM月DD日
        r'生年月日\s*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日',
        # 生年月日 = {{生年月日と年齢|YYYY|MM|DD}}
        r'生年月日\s*=\s*\{\{生年月日と年齢\|(\d{4})\|(\d{1,2})\|(\d{1,2})',
        # 生年月日 = {{Birth date|YYYY|MM|DD}}
        r'生年月日\s*=\s*\{\{Birth date\|(\d{4})\|(\d{1,2})\|(\d{1,2})',
        # birth_date = YYYY|MM|DD
        r'birth_date\s*=\s*\{\{[^|]*\|(\d{4})\|(\d{1,2})\|(\d{1,2})',
        # 生誕 = YYYY年MM月DD日
        r'生誕\s*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日',
        # 出生 = YYYY年MM月DD日
        r'出生\s*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日',
    ]

    for pattern in patterns:
        match = re.search(pattern, wikitext)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return f"{year:04d}-{month:02d}-{day:02d}", year

    # 年のみのパターン
    year_patterns = [
        r'生年月日\s*=\s*(\d{4})年',
        r'生誕\s*=\s*(\d{4})年',
        r'出生\s*=\s*(\d{4})年',
    ]

    for pattern in year_patterns:
        match = re.search(pattern, wikitext)
        if match:
            year = int(match.group(1))
            return None, year

    return None, None

def extract_death_date_from_wikitext(wikitext):
    """Wikitextから没年月日を抽出"""

    patterns = [
        # 死亡日 = YYYY年MM月DD日
        r'死亡日\s*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日',
        # 没年月日 = YYYY年MM月DD日
        r'没年月日\s*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日',
        # 死去 = YYYY年MM月DD日
        r'死去\s*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日',
        # death_date = {{Death date|YYYY|MM|DD}}
        r'death_date\s*=\s*\{\{[^|]*\|(\d{4})\|(\d{1,2})\|(\d{1,2})',
    ]

    for pattern in patterns:
        match = re.search(pattern, wikitext)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return f"{year:04d}-{month:02d}-{day:02d}"

    return None

def get_wikipedia_birth_info(wikipedia_url):
    """WikipediaのURLから生年月日情報を取得"""

    if not wikipedia_url or pd.isna(wikipedia_url):
        return None, None, None

    # URLからページタイトルを抽出
    title_match = re.search(r'/wiki/(.+)$', wikipedia_url)
    if not title_match:
        return None, None, None

    page_title = title_match.group(1)

    # Wikipedia APIエンドポイント
    api_url = "https://ja.wikipedia.org/w/api.php"

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
        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()

            if 'query' in data and 'pages' in data['query']:
                pages = data['query']['pages']
                if pages and len(pages) > 0:
                    page = pages[0]
                    if 'revisions' in page and len(page['revisions']) > 0:
                        wikitext = page['revisions'][0]['slots']['main']['content']

                        # 生年月日を抽出
                        birth_date, birth_year = extract_birth_date_from_wikitext(wikitext)

                        # 没年月日を抽出
                        death_date = extract_death_date_from_wikitext(wikitext)

                        return birth_date, birth_year, death_date

    except Exception as e:
        print(f"  ❌ エラー: {e}")

    return None, None, None

def main():
    print("=" * 80)
    print("📅 Wikipedia APIから生年月日情報を抽出")
    print("=" * 80)

    # データ読み込み
    input_file = 'ultra_think_CLEANED_20250915_213042.csv'
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df):,}件")

    # 新しいカラムを追加
    df['birth_date'] = None
    df['birth_year_int'] = None
    df['death_date'] = None

    # Wikipedia URLがある人物を対象
    wiki_mask = df['wikipedia_url'].notna() & (df['wikipedia_url'] != '')
    target_df = df[wiki_mask]
    print(f"\n🎯 処理対象: Wikipedia URLがある {len(target_df):,}件")

    # バッチ処理設定
    batch_size = 100
    total_batches = (len(target_df) + batch_size - 1) // batch_size

    success_count = 0
    birth_date_count = 0
    birth_year_count = 0
    death_date_count = 0

    print(f"\n📡 Wikipedia APIから情報取得開始（{total_batches}バッチ）...")
    print("-" * 80)

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(target_df))
        batch = target_df.iloc[start_idx:end_idx]

        print(f"\n📦 バッチ {batch_num + 1}/{total_batches} ({start_idx + 1}-{end_idx}件目)")

        for i, (idx, row) in enumerate(batch.iterrows(), start=start_idx + 1):
            person_id = row['person_id']
            person_name = row['person_name_display']
            wikipedia_url = row['wikipedia_url']

            if i % 10 == 1:
                print(f"\n  処理中: {i}/{len(target_df)}")

            # Wikipedia APIから情報取得
            birth_date, birth_year, death_date = get_wikipedia_birth_info(wikipedia_url)

            if birth_date or birth_year or death_date:
                success_count += 1

                if birth_date:
                    df.at[idx, 'birth_date'] = birth_date
                    birth_date_count += 1
                    print(f"    ✅ {person_id}: {person_name} - 生年月日: {birth_date}")

                if birth_year:
                    df.at[idx, 'birth_year_int'] = birth_year
                    birth_year_count += 1
                    if not birth_date:
                        print(f"    📅 {person_id}: {person_name} - 生年: {birth_year}")

                if death_date:
                    df.at[idx, 'death_date'] = death_date
                    death_date_count += 1

            # レート制限対策
            time.sleep(0.5)

        print(f"  バッチ完了: 成功 {success_count}件")

    # 統計情報
    print("\n" + "=" * 80)
    print("📊 取得結果統計")
    print("=" * 80)
    print(f"  処理対象: {len(target_df):,}件")
    print(f"  情報取得成功: {success_count:,}件 ({success_count/len(target_df)*100:.1f}%)")
    print(f"  生年月日取得: {birth_date_count:,}件")
    print(f"  生年のみ取得: {birth_year_count - birth_date_count:,}件")
    print(f"  没年月日取得: {death_date_count:,}件")

    # 生年分布
    birth_years = df['birth_year_int'].dropna()
    if len(birth_years) > 0:
        print(f"\n📈 生年分布:")
        print(f"  最古: {int(birth_years.min())}年")
        print(f"  最新: {int(birth_years.max())}年")
        print(f"  平均: {birth_years.mean():.0f}年")

        # 世紀別集計
        centuries = ((birth_years // 100) + 1).value_counts().sort_index()
        print(f"\n  世紀別分布:")
        for century, count in centuries.items():
            print(f"    {int(century)}世紀: {int(count)}人")

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
            print(f"{i:2d}. {row['person_id']}: {row['person_name_display']}")
            print(f"    生年月日: {row['birth_date']}, 生年: {row['birth_year_int']}")
            if pd.notna(row['death_date']):
                print(f"    没年月日: {row['death_date']}")

    # サマリー
    print("\n" + "=" * 80)
    print("✅ 生年月日情報追加完了！")
    print("=" * 80)
    print(f"  入力: {input_file}")
    print(f"  出力: {output_file}")
    print(f"  追加フィールド:")
    print(f"    - birth_date: 生年月日 (YYYY-MM-DD形式)")
    print(f"    - birth_year_int: 生年 (整数)")
    print(f"    - death_date: 没年月日 (YYYY-MM-DD形式)")

    return output_file, df

if __name__ == "__main__":
    output_file, df = main()