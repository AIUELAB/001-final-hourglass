#!/usr/bin/env python3
"""
WikipediaAPIから生年月日情報を抽出して既存のCSVに追加
"""

import pandas as pd
import requests
import time
import re
from datetime import datetime
import urllib.parse
import json
from pathlib import Path

def extract_birth_info_from_wikitext(wikitext):
    """Wikitextから生年月日情報を抽出（改良版）"""

    # 生年月日フィールドを探す（複数パターンに対応）
    field_patterns = [
        r'生年月日[^=]*=([^\n|]+)',
        r'生誕[^=]*=([^\n|]+)',
        r'birth_date[^=]*=([^\n|]+)',
        r'出生[^=]*=([^\n|]+)',
        r'生まれ[^=]*=([^\n|]+)',
        r'Born[^=]*=([^\n|]+)',
    ]

    birth_section = None
    for field_pattern in field_patterns:
        match = re.search(field_pattern, wikitext, re.IGNORECASE)
        if match:
            birth_section = match.group(1)
            break

    if birth_section:
        # テンプレート内の年月日を抽出
        # {{生年月日と年齢|YYYY|MM|DD}}
        match = re.search(r'\{\{[^|]*\|(\d{4})\|(\d{1,2})\|(\d{1,2})', birth_section)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            # 妥当性チェック（未来の日付を除外）
            if 1800 <= year <= 2024 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}", year

        # YYYY年MM月DD日形式
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', birth_section)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            if 1800 <= year <= 2024 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}", year

        # 西暦YYYY年形式
        match = re.search(r'(\d{4})年', birth_section)
        if match:
            year = int(match.group(1))
            if 1800 <= year <= 2024:
                return None, year

    # 本文から生年を探す
    # 「YYYY年生まれ」「YYYY年 - 」パターン
    text_patterns = [
        r'(\d{4})年生まれ',
        r'(\d{4})年\s*-\s*(?:\d{4}年)?',
        r'（(\d{4})年.*?生）',
        r'\((\d{4})年.*?生\)',
    ]

    for pattern in text_patterns:
        match = re.search(pattern, wikitext)
        if match:
            year = int(match.group(1))
            if 1800 <= year <= 2024:
                return None, year

    return None, None

def get_wikipedia_content(wikipedia_url):
    """Wikipedia URLからページコンテンツを取得"""

    if not wikipedia_url or pd.isna(wikipedia_url) or wikipedia_url == '':
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
        'User-Agent': 'BirthDateExtractor/1.0 (Educational Purpose)'
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
        print(f"  ⚠️ エラー: {e}")
        return None

    return None

def main():
    print("=" * 80)
    print("📅 Wikipedia APIから生年月日情報を抽出")
    print("=" * 80)

    # 最新のCSVファイルを探す
    input_file = 'ultra_think_WITH_BIRTH_20250915_231434.csv'

    if not Path(input_file).exists():
        print(f"❌ ファイルが見つかりません: {input_file}")
        return

    # データ読み込み
    print(f"\n📂 データ読み込み中: {input_file}")
    df = pd.read_csv(input_file, encoding='utf-8-sig')
    print(f"✅ データ読み込み完了: {len(df):,}件")

    # birth_dateとbirth_year_intカラムが無い場合は追加
    if 'birth_date' not in df.columns:
        df['birth_date'] = None
    if 'birth_year_int' not in df.columns:
        df['birth_year_int'] = None

    # 既にデータがある件数を確認
    existing_birth_date = df['birth_date'].notna().sum()
    existing_birth_year = df['birth_year_int'].notna().sum()
    print(f"\n📊 既存データ:")
    print(f"  - 生年月日: {existing_birth_date:,}件")
    print(f"  - 生年: {existing_birth_year:,}件")

    # Wikipedia URLがあり、まだ生年データがない人物を対象
    wiki_mask = (
        df['wikipedia_url'].notna() &
        (df['wikipedia_url'] != '') &
        df['birth_year_int'].isna()
    )
    target_df = df[wiki_mask]
    print(f"\n🎯 処理対象: Wikipedia URLがあり生年データがない {len(target_df):,}件")

    if len(target_df) == 0:
        print("✅ 処理対象がありません")
        return

    # バッチ処理設定
    batch_size = 20  # APIレート制限を考慮
    total_batches = (len(target_df) + batch_size - 1) // batch_size

    success_count = 0
    birth_date_count = 0
    birth_year_count = 0
    error_count = 0

    print(f"\n📡 Wikipedia APIから情報取得開始（{total_batches}バッチ）...")
    print("-" * 80)

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(target_df))
        batch = target_df.iloc[start_idx:end_idx]

        print(f"\n📦 バッチ {batch_num + 1}/{total_batches} 処理中...")

        for idx, row in batch.iterrows():
            person_name = row['person_name_display']
            wikipedia_url = row['wikipedia_url']

            # Wikipedia APIから情報取得
            wikitext = get_wikipedia_content(wikipedia_url)

            if wikitext:
                # 生年月日情報を抽出
                birth_date, birth_year = extract_birth_info_from_wikitext(wikitext)

                if birth_date or birth_year:
                    success_count += 1

                    if birth_date:
                        df.at[idx, 'birth_date'] = birth_date
                        df.at[idx, 'birth_year_int'] = birth_year
                        birth_date_count += 1
                        print(f"  ✅ {person_name}: 生年月日 {birth_date}")
                    elif birth_year:
                        df.at[idx, 'birth_year_int'] = birth_year
                        birth_year_count += 1
                        print(f"  📅 {person_name}: 生年 {birth_year}")
                else:
                    print(f"  ⚪ {person_name}: 生年情報なし")
            else:
                error_count += 1
                print(f"  ❌ {person_name}: Wikipedia取得失敗")

            # レート制限対策
            time.sleep(0.5)

        # バッチ間の休憩
        if batch_num < total_batches - 1:
            print(f"\n⏳ 次のバッチまで待機中...")
            time.sleep(2)

    # 結果の保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_WITH_BIRTH_DATES_{timestamp}.csv'

    # UTF-8 BOM付きで保存（Excel対応）
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 処理結果サマリー")
    print("=" * 80)
    print(f"✅ 成功: {success_count:,}件")
    print(f"  - 生年月日取得: {birth_date_count:,}件")
    print(f"  - 生年のみ取得: {birth_year_count:,}件")
    print(f"❌ エラー: {error_count:,}件")
    print(f"\n💾 保存先: {output_file}")

    # 最終的なデータ状況
    final_birth_date = df['birth_date'].notna().sum()
    final_birth_year = df['birth_year_int'].notna().sum()
    print(f"\n📈 最終データ状況:")
    print(f"  - 生年月日: {final_birth_date:,}件 (増加: +{final_birth_date - existing_birth_date:,})")
    print(f"  - 生年: {final_birth_year:,}件 (増加: +{final_birth_year - existing_birth_year:,})")
    print(f"  - カバー率: {final_birth_year / len(df) * 100:.1f}%")

if __name__ == '__main__':
    main()