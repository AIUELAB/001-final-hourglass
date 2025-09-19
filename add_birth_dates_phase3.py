#!/usr/bin/env python3
"""
WikipediaAPIから生年月日情報を抽出（フェーズ2 - 継続処理版）
"""

import pandas as pd
import requests
import time
import re
from datetime import datetime
import urllib.parse
from pathlib import Path

def extract_birth_info_from_wikitext(wikitext):
    """Wikitextから生年月日情報を抽出（シンプル版）"""

    # 最も一般的なパターンだけに絞る
    # {{生年月日と年齢|YYYY|MM|DD}}
    match = re.search(r'\{\{(?:生年月日|birth\s*date)[^|]*\|(\d{4})\|(\d{1,2})\|(\d{1,2})', wikitext, re.IGNORECASE)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        if 1800 <= year <= 2024 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}", year

    # YYYY年MM月DD日形式
    match = re.search(r'生年月日[^=]*=.*?(\d{4})年(\d{1,2})月(\d{1,2})日', wikitext[:2000])
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        if 1800 <= year <= 2024 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}", year

    # 年のみ（YYYY年生まれ）
    match = re.search(r'(\d{4})年.*?生まれ', wikitext[:2000])
    if match:
        year = int(match.group(1))
        if 1800 <= year <= 2024:
            return None, year

    # 年のみ（YYYY年 - ）
    match = re.search(r'（(\d{4})年.*?[-–]', wikitext[:1000])
    if match:
        year = int(match.group(1))
        if 1800 <= year <= 2024:
            return None, year

    return None, None

def get_wikipedia_content(wikipedia_url, session=None):
    """Wikipedia URLからページコンテンツを取得（セッション使用）"""

    if not wikipedia_url or pd.isna(wikipedia_url) or wikipedia_url == '':
        return None

    # URLからページタイトルを抽出
    title_match = re.search(r'/wiki/(.+)$', wikipedia_url)
    if not title_match:
        return None

    page_title = urllib.parse.unquote(title_match.group(1))

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
        if session:
            response = session.get(api_url, params=params, timeout=5)
        else:
            response = requests.get(api_url, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()

            if 'query' in data and 'pages' in data['query']:
                pages = data['query']['pages']
                if pages and len(pages) > 0:
                    page = pages[0]
                    if 'revisions' in page and len(page['revisions']) > 0:
                        wikitext = page['revisions'][0]['slots']['main']['content']
                        return wikitext

    except Exception:
        return None

    return None

def main():
    print("=" * 80)
    print("📅 Wikipedia APIから生年月日情報を抽出（フェーズ3 - 継続処理）")
    print("=" * 80)

    # 前回の処理結果を入力として使用（フェーズ2の結果）
    input_file = 'ultra_think_WITH_BIRTH_DATES_PHASE2_20250916_063623.csv'

    if not Path(input_file).exists():
        print(f"❌ ファイルが見つかりません: {input_file}")
        return

    # データ読み込み
    print(f"\n📂 データ読み込み中: {input_file}")
    df = pd.read_csv(input_file, encoding='utf-8-sig')
    print(f"✅ データ読み込み完了: {len(df):,}件")

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

    # 次の100件を処理（スキップして101-200件目を処理）
    skip = 0  # 前回100件処理済みなので、今回は0からスタート（既に処理済みのものは除外されている）
    limit = 100
    if len(target_df) > skip:
        print(f"⚠️ フェーズ3: {skip+1}〜{min(skip+limit, len(target_df))}件目を処理")
        target_df = target_df.iloc[skip:skip+limit]
    else:
        print("✅ 処理対象がありません")
        return

    if len(target_df) == 0:
        print("✅ 処理対象がありません")
        return

    # セッションを使用して高速化
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'BirthDateExtractor/1.0 (Educational Purpose)'
    })

    success_count = 0
    birth_date_count = 0
    birth_year_count = 0
    error_count = 0

    print(f"\n📡 Wikipedia APIから情報取得開始（{len(target_df)}件）...")
    print("-" * 80)

    # プログレスバー表示
    for i, (idx, row) in enumerate(target_df.iterrows(), 1):
        person_name = row['person_name_display']
        wikipedia_url = row['wikipedia_url']

        # Wikipedia APIから情報取得
        wikitext = get_wikipedia_content(wikipedia_url, session)

        if wikitext:
            # 生年月日情報を抽出
            birth_date, birth_year = extract_birth_info_from_wikitext(wikitext)

            if birth_date or birth_year:
                success_count += 1

                if birth_date:
                    df.at[idx, 'birth_date'] = birth_date
                    df.at[idx, 'birth_year_int'] = birth_year
                    birth_date_count += 1
                    print(f"[{i:3d}/{len(target_df)}] ✅ {person_name}: 生年月日 {birth_date}")
                elif birth_year:
                    df.at[idx, 'birth_year_int'] = birth_year
                    birth_year_count += 1
                    print(f"[{i:3d}/{len(target_df)}] 📅 {person_name}: 生年 {birth_year}")
            else:
                print(f"[{i:3d}/{len(target_df)}] ⚪ {person_name}: 生年情報なし")
        else:
            error_count += 1
            print(f"[{i:3d}/{len(target_df)}] ❌ {person_name}: Wikipedia取得失敗")

        # レート制限対策（短い間隔）
        if i % 10 == 0:
            time.sleep(0.5)
        else:
            time.sleep(0.1)

        # 進捗表示
        if i % 50 == 0:
            print(f"\n📊 進捗: {i}/{len(target_df)} ({i/len(target_df)*100:.1f}%)")
            print(f"   成功: {success_count} | 生年月日: {birth_date_count} | 生年: {birth_year_count} | エラー: {error_count}\n")

    # セッションを閉じる
    session.close()

    # 結果の保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_WITH_BIRTH_DATES_PHASE3_{timestamp}.csv'

    # UTF-8 BOM付きで保存（Excel対応）
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 フェーズ3処理結果サマリー")
    print("=" * 80)
    print(f"✅ 成功: {success_count:,}件")
    print(f"  - 生年月日取得: {birth_date_count:,}件")
    print(f"  - 生年のみ取得: {birth_year_count:,}件")
    print(f"❌ エラー: {error_count:,}件")
    print(f"\n💾 保存先: {output_file}")

    # 最終的なデータ状況
    final_birth_date = df['birth_date'].notna().sum()
    final_birth_year = df['birth_year_int'].notna().sum()
    print(f"\n📈 累積データ状況:")
    print(f"  - 生年月日: {final_birth_date:,}件 (増加: +{final_birth_date - existing_birth_date:,})")
    print(f"  - 生年: {final_birth_year:,}件 (増加: +{final_birth_year - existing_birth_year:,})")
    print(f"  - カバー率: {final_birth_year / len(df) * 100:.1f}%")

    # 残り件数
    remaining = df['wikipedia_url'].notna().sum() - final_birth_year
    print(f"\n📋 残り処理対象: {remaining:,}件")
    if remaining > 0:
        phases_needed = (remaining + 99) // 100  # 100件ずつの場合の必要フェーズ数
        print(f"  → あと約{phases_needed}フェーズ必要")

if __name__ == '__main__':
    main()