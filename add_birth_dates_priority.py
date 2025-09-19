#!/usr/bin/env python3
"""
優先度ベースで効率的に生年月日情報を抽出
成功率の高いカテゴリ・職業を優先的に処理
"""

import pandas as pd
import requests
import time
import re
from datetime import datetime
import urllib.parse
from pathlib import Path
import concurrent.futures
from threading import Lock
import json

# グローバルロック（並列処理時のデータ競合防止）
df_lock = Lock()
progress_lock = Lock()

# グローバルカウンタ
global_counters = {
    'processed': 0,
    'success': 0,
    'birth_dates': 0,
    'birth_years': 0,
    'errors': 0
}

def extract_birth_info_from_wikitext(wikitext):
    """Wikitextから生年月日情報を抽出（シンプル版）"""

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

def process_batch(df, batch_indices, thread_id):
    """バッチ処理（スレッド毎）"""

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'BirthDateExtractor/1.0 (Educational Purpose)'
    })

    local_success = 0
    local_birth_dates = 0
    local_birth_years = 0
    local_errors = 0

    for i, idx in enumerate(batch_indices, 1):
        row = df.loc[idx]
        person_name = row['person_name_display']
        wikipedia_url = row['wikipedia_url']

        # Wikipedia APIから情報取得
        wikitext = get_wikipedia_content(wikipedia_url, session)

        if wikitext:
            # 生年月日情報を抽出
            birth_date, birth_year = extract_birth_info_from_wikitext(wikitext)

            if birth_date or birth_year:
                local_success += 1

                with df_lock:
                    if birth_date:
                        df.at[idx, 'birth_date'] = birth_date
                        df.at[idx, 'birth_year_int'] = birth_year
                        local_birth_dates += 1
                        print(f"[Thread{thread_id}][{i:3d}/{len(batch_indices)}] ✅ {person_name}: 生年月日 {birth_date}")
                    elif birth_year:
                        df.at[idx, 'birth_year_int'] = birth_year
                        local_birth_years += 1
                        print(f"[Thread{thread_id}][{i:3d}/{len(batch_indices)}] 📅 {person_name}: 生年 {birth_year}")
            else:
                print(f"[Thread{thread_id}][{i:3d}/{len(batch_indices)}] ⚪ {person_name}: 生年情報なし")
        else:
            local_errors += 1
            print(f"[Thread{thread_id}][{i:3d}/{len(batch_indices)}] ❌ {person_name}: Wikipedia取得失敗")

        # レート制限対策（スレッド毎に調整）
        time.sleep(0.2 + thread_id * 0.1)  # スレッド毎に少しずつ遅延を変える

        # グローバルカウンタ更新
        with progress_lock:
            global_counters['processed'] += 1
            if global_counters['processed'] % 20 == 0:
                print(f"\n📊 全体進捗: {global_counters['processed']}件処理済み\n")

    session.close()

    # 結果を返す
    return {
        'success': local_success,
        'birth_dates': local_birth_dates,
        'birth_years': local_birth_years,
        'errors': local_errors
    }

def main():
    print("=" * 80)
    print("🎯 優先度ベースで効率的に生年月日情報を抽出")
    print("=" * 80)

    # 最新のCSVファイルを読み込み
    input_file = 'ultra_think_WITH_BIRTH_DATES_PHASE6_20250916_230216.csv'

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
    target_df = df[wiki_mask].copy()

    print(f"\n🎯 処理対象: Wikipedia URLがあり生年データがない {len(target_df):,}件")

    # 優先度スコアを計算
    print("\n📈 優先度スコアを計算中...")

    # カテゴリ優先度（成功率ベース）
    category_priority = {
        '歴史的偉人': 10,
        '文化・芸術': 8,
        '政治': 7,
        '文化・学術': 6,
        'エンタメ': 5,
        'スポーツ': 4,
        '政治・経済': 3,
        'その他': 2
    }

    # 職業優先度（成功率ベース）
    occupation_priority = {
        '政治家': 10,
        '作家': 9,
        '大統領': 8,
        '野球選手': 7,
        'お笑い芸人': 6,
        '俳優': 5,
        '歌手': 4,
        'YouTuber': 3
    }

    # 優先度スコアを計算
    target_df['priority_score'] = 0

    # カテゴリによるスコア
    if 'category' in target_df.columns:
        for cat, score in category_priority.items():
            mask = target_df['category'] == cat
            target_df.loc[mask, 'priority_score'] += score * 100

    # 職業によるスコア
    if 'occupation' in target_df.columns:
        for occ, score in occupation_priority.items():
            mask = target_df['occupation'] == occ
            target_df.loc[mask, 'priority_score'] += score * 50

    # fame_scoreによるスコア（正規化して0-100に）
    if 'fame_score' in target_df.columns:
        max_fame = target_df['fame_score'].max()
        if max_fame > 0:
            target_df['priority_score'] += (target_df['fame_score'] / max_fame * 100).fillna(0)

    # 優先度でソート
    target_df = target_df.sort_values('priority_score', ascending=False)

    print("📊 優先度上位20件:")
    top_20 = target_df.head(20)
    for idx, row in top_20.iterrows():
        print(f"  {row['person_name_display']}: スコア{row['priority_score']:.0f} ({row.get('category', 'N/A')}/{row.get('occupation', 'N/A')})")

    # 処理件数を制限（500件）
    limit = 500
    if len(target_df) > limit:
        print(f"\n⚠️ 効率化のため上位{limit}件のみ処理します")
        target_df = target_df.head(limit)

    # インデックスを保持
    target_indices = target_df.index.tolist()

    # 並列処理の設定
    num_threads = 5
    batch_size = len(target_indices) // num_threads
    batches = []

    for i in range(num_threads):
        start = i * batch_size
        if i == num_threads - 1:
            # 最後のスレッドは残り全てを処理
            batch = target_indices[start:]
        else:
            batch = target_indices[start:start + batch_size]
        if batch:
            batches.append(batch)

    print(f"\n🚀 {num_threads}スレッドで並列処理を開始（各スレッド約{batch_size}件）...")
    print("-" * 80)

    # 並列実行
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for i, batch in enumerate(batches):
            future = executor.submit(process_batch, df, batch, i+1)
            futures.append(future)

        # 結果を集計
        total_results = {
            'success': 0,
            'birth_dates': 0,
            'birth_years': 0,
            'errors': 0
        }

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            for key in total_results:
                total_results[key] += result[key]

    # 結果の保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_WITH_BIRTH_DATES_PRIORITY_{timestamp}.csv'

    # UTF-8 BOM付きで保存（Excel対応）
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 優先度ベース処理結果サマリー")
    print("=" * 80)
    print(f"✅ 成功: {total_results['success']:,}件")
    print(f"  - 生年月日取得: {total_results['birth_dates']:,}件")
    print(f"  - 生年のみ取得: {total_results['birth_years']:,}件")
    print(f"❌ エラー: {total_results['errors']:,}件")
    print(f"📈 成功率: {total_results['success']/len(target_indices)*100:.1f}%")
    print(f"\n💾 保存先: {output_file}")

    # 最終的なデータ状況
    final_birth_date = df['birth_date'].notna().sum()
    final_birth_year = df['birth_year_int'].notna().sum()
    print(f"\n📈 累積データ状況:")
    print(f"  - 生年月日: {final_birth_date:,}件 (増加: +{final_birth_date - existing_birth_date:,})")
    print(f"  - 生年: {final_birth_year:,}件 (増加: +{final_birth_year - existing_birth_year:,})")
    print(f"  - カバー率: {final_birth_year / len(df) * 100:.1f}%")

if __name__ == '__main__':
    main()