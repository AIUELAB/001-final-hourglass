#!/usr/bin/env python3
"""
Wikipedia APIから生年月日情報を抽出（バッチ7）
fame_score上位の人物を優先的に処理
"""

import pandas as pd
import requests
import time
import re
from datetime import datetime
import urllib.parse
from pathlib import Path
import json

def extract_birth_info_from_wikitext(wikitext, person_name=None):
    """Wikitextから生年月日情報を抽出（改良版）"""

    if not wikitext:
        return None, None

    # より多様なパターンに対応
    patterns = [
        # {{生年月日と年齢|YYYY|MM|DD}}
        (r'\{\{(?:生年月日と年齢?|birth\s*date(?:\s*and\s*age)?)[^|]*\|(\d{4})\|(\d{1,2})\|(\d{1,2})', 'full'),
        # {{生年月日|YYYY年|MM月|DD日}}
        (r'\{\{生年月日[^|]*\|(\d{4})年\|(\d{1,2})月\|(\d{1,2})日', 'full'),
        # 生年月日 = YYYY年MM月DD日
        (r'生年月日[^=]*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日', 'full'),
        # 誕生日 = YYYY年MM月DD日
        (r'誕生日[^=]*=\s*(\d{4})年(\d{1,2})月(\d{1,2})日', 'full'),
        # YYYY年MM月DD日生まれ
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日生まれ', 'full'),
        # (YYYY年MM月DD日 -
        (r'[\(（](\d{4})年(\d{1,2})月(\d{1,2})日\s*[-–]', 'full'),
        # born MM/DD/YYYY or DD/MM/YYYY
        (r'born[^0-9]*(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', 'mdy'),
        # {{Birth year and age|YYYY}}
        (r'\{\{(?:Birth\s*year(?:\s*and\s*age)?|生年)[^|]*\|(\d{4})', 'year'),
        # YYYY年生まれ
        (r'(\d{4})年.*?生まれ', 'year'),
        # (YYYY年 - または（YYYY -
        (r'[\(（](\d{4})(?:年)?\s*[-–]', 'year'),
    ]

    # 最初の3000文字をチェック（効率化のため）
    search_text = wikitext[:3000]

    for pattern, pattern_type in patterns:
        match = re.search(pattern, search_text, re.IGNORECASE)
        if match:
            if pattern_type == 'full':
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                if 1800 <= year <= 2024 and 1 <= month <= 12 and 1 <= day <= 31:
                    return f"{year:04d}-{month:02d}-{day:02d}", year
            elif pattern_type == 'mdy':
                # 月/日/年または日/月/年の判定
                first = int(match.group(1))
                second = int(match.group(2))
                year = int(match.group(3))
                if 1800 <= year <= 2024:
                    # 月が12以下の場合、月/日として扱う
                    if first <= 12 and 1 <= second <= 31:
                        return f"{year:04d}-{first:02d}-{second:02d}", year
                    # 日/月の可能性
                    elif second <= 12 and 1 <= first <= 31:
                        return f"{year:04d}-{second:02d}-{first:02d}", year
            elif pattern_type == 'year':
                year = int(match.group(1))
                if 1800 <= year <= 2024:
                    return None, year

    return None, None

def get_wikipedia_content(wikipedia_url, session=None):
    """Wikipedia URLからページコンテンツを取得（修正版）"""

    if not wikipedia_url or pd.isna(wikipedia_url) or wikipedia_url == '':
        return None

    # URLからページタイトルを抽出
    title_match = re.search(r'/wiki/(.+)$', wikipedia_url)
    if not title_match:
        return None

    page_title = urllib.parse.unquote(title_match.group(1))

    # 日本語版Wikipedia API
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

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    try:
        if session:
            response = session.get(api_url, params=params, headers=headers, timeout=10)
        else:
            response = requests.get(api_url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            # JSONのデコードをチェック
            content_type = response.headers.get('content-type', '')
            if 'json' not in content_type:
                print(f"Unexpected content type: {content_type}")
                return None

            data = response.json()

            if 'query' in data and 'pages' in data['query']:
                pages = data['query']['pages']
                if pages and len(pages) > 0:
                    page = pages[0]
                    if 'revisions' in page and len(page['revisions']) > 0:
                        wikitext = page['revisions'][0]['slots']['main']['content']
                        return wikitext

    except Exception as e:
        print(f"Error fetching Wikipedia content: {e}")
        return None

    return None

def process_batch(df_batch, session, log_file):
    """バッチ単位で処理"""

    results = []

    for idx, row in df_batch.iterrows():
        person_name = row['person_name_display']
        wikipedia_url = row.get('wikipedia_url', '')
        current_birth_date = row.get('birth_date', None)
        current_birth_year = row.get('birth_year_int', None)

        # すでに完全な生年月日がある場合はスキップ
        if pd.notna(current_birth_date):
            results.append({
                'index': idx,
                'birth_date': current_birth_date,
                'birth_year_int': current_birth_year,
                'status': 'already_exists'
            })
            continue

        # Wikipedia URLがない場合はスキップ
        if pd.isna(wikipedia_url) or wikipedia_url == '':
            results.append({
                'index': idx,
                'birth_date': None,
                'birth_year_int': current_birth_year,
                'status': 'no_wikipedia'
            })
            continue

        # Wikipedia コンテンツを取得
        print(f"Processing {person_name}...", end=' ')
        wikitext = get_wikipedia_content(wikipedia_url, session)

        if wikitext:
            birth_date, birth_year = extract_birth_info_from_wikitext(wikitext, person_name)

            if birth_date:
                print(f"✓ Found: {birth_date}")
                log_file.write(f"SUCCESS: {person_name} - {birth_date}\n")
                results.append({
                    'index': idx,
                    'birth_date': birth_date,
                    'birth_year_int': birth_year,
                    'status': 'found_full'
                })
            elif birth_year:
                print(f"△ Year only: {birth_year}")
                log_file.write(f"YEAR_ONLY: {person_name} - {birth_year}\n")
                results.append({
                    'index': idx,
                    'birth_date': None,
                    'birth_year_int': birth_year,
                    'status': 'found_year'
                })
            else:
                print("✗ Not found")
                log_file.write(f"NOT_FOUND: {person_name}\n")
                results.append({
                    'index': idx,
                    'birth_date': None,
                    'birth_year_int': current_birth_year,
                    'status': 'not_found'
                })
        else:
            print("✗ Failed to fetch")
            log_file.write(f"FETCH_ERROR: {person_name}\n")
            results.append({
                'index': idx,
                'birth_date': None,
                'birth_year_int': current_birth_year,
                'status': 'fetch_error'
            })

        # API制限対策
        time.sleep(0.5)

    return results

def main():
    # 最新のCSVファイルを読み込み
    input_file = 'ultra_think_WITH_BIRTH_DATES_BATCH6_20250917_100511.csv'
    print(f"Loading {input_file}...")

    df = pd.read_csv(input_file, encoding='utf-8-sig')
    print(f"Total records: {len(df)}")

    # 生年月日が欠落している人物を抽出
    df_missing = df[df['birth_date'].isna()].copy()
    print(f"Records with missing birth_date: {len(df_missing)}")

    # fame_scoreで降順ソート（高優先度）
    df_missing_sorted = df_missing.sort_values('fame_score', ascending=False)

    # 上位50人を処理対象とする（まずは少数でテスト）
    df_to_process = df_missing_sorted.head(50)
    print(f"Processing top {len(df_to_process)} records by fame_score...")

    # セッションを作成（接続再利用で高速化）
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })

    # ログファイルを開く
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f'birth_date_batch7_log_{timestamp}.txt'

    with open(log_filename, 'w', encoding='utf-8') as log_file:
        log_file.write(f"Birth Date Collection Batch 7 - {timestamp}\n")
        log_file.write("=" * 50 + "\n\n")

        # バッチサイズを10に設定（デバッグ用）
        batch_size = 10
        all_results = []

        for i in range(0, len(df_to_process), batch_size):
            batch_num = i // batch_size + 1
            print(f"\n--- Processing batch {batch_num} ({i+1}-{min(i+batch_size, len(df_to_process))}) ---")

            df_batch = df_to_process.iloc[i:i+batch_size]
            batch_results = process_batch(df_batch, session, log_file)
            all_results.extend(batch_results)

            # バッチ間で少し待機
            if i + batch_size < len(df_to_process):
                print("Waiting between batches...")
                time.sleep(2)

        # 結果をDataFrameに適用
        print("\nApplying results to DataFrame...")

        found_full = 0
        found_year = 0
        not_found = 0

        for result in all_results:
            idx = result['index']
            if result['status'] == 'found_full':
                df.at[idx, 'birth_date'] = result['birth_date']
                df.at[idx, 'birth_year_int'] = result['birth_year_int']
                found_full += 1
            elif result['status'] == 'found_year':
                df.at[idx, 'birth_year_int'] = result['birth_year_int']
                found_year += 1
            elif result['status'] in ['not_found', 'fetch_error', 'no_wikipedia']:
                not_found += 1

        # 統計をログに記録
        log_file.write("\n" + "=" * 50 + "\n")
        log_file.write("SUMMARY\n")
        log_file.write(f"Total processed: {len(all_results)}\n")
        log_file.write(f"Found full date: {found_full}\n")
        log_file.write(f"Found year only: {found_year}\n")
        log_file.write(f"Not found: {not_found}\n")

        print(f"\n=== Summary ===")
        print(f"Found full date: {found_full}")
        print(f"Found year only: {found_year}")
        print(f"Not found: {not_found}")

    # 更新されたCSVを保存
    output_file = f'ultra_think_WITH_BIRTH_DATES_BATCH7_{timestamp}.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nSaved to {output_file}")

    # 更新前後の統計
    print("\n=== Final Statistics ===")
    print(f"Total records: {len(df)}")
    print(f"Records with birth_date: {df['birth_date'].notna().sum()} ({df['birth_date'].notna().sum()/len(df)*100:.1f}%)")
    print(f"Records with birth_year_int: {df['birth_year_int'].notna().sum()} ({df['birth_year_int'].notna().sum()/len(df)*100:.1f}%)")

if __name__ == '__main__':
    main()