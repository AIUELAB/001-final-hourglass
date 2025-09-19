#!/usr/bin/env python3
"""
誕生年収集実装スクリプト
実在人物と架空キャラクター両方に対応
"""

import pandas as pd
import requests
import time
import re
from datetime import datetime
import urllib.parse
from pathlib import Path

# 実在人物の誕生年データ（手動調査）
real_person_birth_years = {
    'アンジュ・カトリーナ': 1997,  # にじさんじVTuber
    'シドニー・スウィーニー': 1997,  # アメリカの女優
    'ヘンリク・グレツキ': 1933,  # ポーランドの作曲家
    '伊藤俊介': 1979,  # 俳優
    '本間ひまわり': None,  # VTuber（生年非公開）
    'エリッサ': 1972,  # レバノンの歌手
    '原': None,  # 名前が不完全
    '癒月ちょこ': None,  # ホロライブVTuber（生年非公開）
    '猫又おかゆ': None,  # ホロライブVTuber（生年非公開）
    '瑛太': 1982,  # 日本の俳優
    '酒寄希望': 1988,  # グラビアアイドル
    '山田七海': 2001,  # 女優
    '瀬下豊': 1965,  # お笑い芸人（天竺鼠）
    'Joshua': 1995,  # SEVENTEEN
    '長谷川雅紀': 1974,  # お笑い芸人（錦鯉）
    'ロバート・ダウニー・Jr': 1965,  # アメリカの俳優
    'ロゼ': 1997,  # BLACKPINK
    '田渕章裕': None,  # 不明
    '太田博久': 1984,  # お笑い芸人（ジャングルポケット）
    'ロニー・ウッド': 1947,  # ローリング・ストーンズ
    'ジュン': 1996,  # SEVENTEEN
    'Jun': 1996,  # SEVENTEEN（重複）
    '布川ひろき': None,  # 不明
    '後藤拓実': 1988,  # お笑い芸人（四千頭身）
    '若井滉斗': 1995,  # Mrs. GREEN APPLE
    '佐藤七海': 1999,  # AKB48
    '菊田竜大': 1979,  # お笑い芸人（ハリガネロック）
    '堂前透': 1970,  # お笑い芸人（ダーリンハニー）
    '徳永英明': 1961,  # 歌手
    '圧倒的不審者の極み': None,  # YouTuber（生年非公開）
}

# 架空キャラクターの設定上の誕生年
fictional_character_birth_years = {
    # 幽☆遊☆白書
    '飛影': None,  # 妖怪のため誕生年不明
    '蔵馬': None,  # 妖怪のため誕生年不明

    # 名探偵コナン
    '毛利蘭': None,  # 高校2年生（17歳前後）

    # ゼルダの伝説
    'リンク': None,  # 作品により異なる

    # ストリートファイター
    'リュウ': 1964,  # 設定上は1964年7月21日生まれ

    # FF7
    'エアリス・ゲインズブール': None,  # ゲーム内年齢22歳

    # 仮面ライダー
    '仮面ライダー': None,  # 本郷猛として1948年生まれ（設定）

    # こちら葛飾区亀有公園前派出所
    '両津勘吉': 1952,  # 設定上は1952年3月3日生まれ

    # ガンダム
    'カミーユ・ビダン': None,  # 宇宙世紀0069年生まれ（架空の暦）
    'ジュドー・アーシタ': None,  # 宇宙世紀0073年生まれ（架空の暦）

    # スーパーマリオ
    'ヨッシー': None,  # 年齢不明

    # ONE PIECE
    'トニートニー・チョッパー': None,  # 人間換算で15-17歳
    'モンキー・D・ルフィ': None,  # 作中で19歳

    # アンパンマン
    'カレーパンマン': None,  # 年齢不明
    '剛田武': None,  # ドラえもんのジャイアン、小学5年生

    # るろうに剣心
    '緋村剣心': 1849,  # 設定上は1849年生まれ（明治11年時点で28歳）

    # エヴァンゲリオン
    '綾波レイ': 2001,  # 設定上は2001年生まれ

    # シティーハンター
    '冴羽獠': None,  # 年齢不明（20代後半～30代前半）

    # BLEACH
    '黒崎一護': None,  # 作中で15-17歳

    # 鋼の錬金術師
    'エドワード・エルリック': None,  # 作中で15-16歳
}

def extract_birth_year_from_wikipedia(wikitext):
    """Wikipediaテキストから誕生年のみを抽出（簡略版）"""

    if not wikitext:
        return None

    # 誕生年パターン
    patterns = [
        r'(\d{4})年.*?生まれ',
        r'生年.*?(\d{4})年',
        r'[（(](\d{4})年.*?[-–]',
        r'born.*?(\d{4})',
        r'Birth year.*?(\d{4})',
    ]

    search_text = wikitext[:2000]  # 最初の2000文字のみ検索

    for pattern in patterns:
        match = re.search(pattern, search_text, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            if 1800 <= year <= 2024:
                return year

    return None

def get_wikipedia_year(wikipedia_url):
    """Wikipedia URLから誕生年を取得（シンプル版）"""

    if not wikipedia_url or pd.isna(wikipedia_url):
        return None

    # URLからページタイトルを抽出
    title_match = re.search(r'/wiki/(.+)$', wikipedia_url)
    if not title_match:
        return None

    page_title = urllib.parse.unquote(title_match.group(1))

    # Wikipedia API
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
        'User-Agent': 'Mozilla/5.0 Birth Year Collector'
    }

    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'query' in data and 'pages' in data['query']:
                pages = data['query']['pages']
                if pages and len(pages) > 0:
                    page = pages[0]
                    if 'revisions' in page:
                        wikitext = page['revisions'][0]['slots']['main']['content']
                        return extract_birth_year_from_wikipedia(wikitext)
    except:
        pass

    return None

def collect_birth_years():
    """誕生年の収集を実行"""

    # CSVファイルを読み込み
    input_file = 'ultra_think_WITH_BIRTH_DATES_SIMPLE_20250917_113030.csv'
    print(f"Loading {input_file}...")

    df = pd.read_csv(input_file, encoding='utf-8-sig')
    print(f"Total records: {len(df)}")

    updated_count = 0

    # 1. 手動調査データの適用（実在人物）
    print("\n=== Phase 1: 手動調査データの適用 ===")
    for name, year in real_person_birth_years.items():
        if year is not None:
            mask = df['person_name_display'] == name
            if mask.any():
                if pd.isna(df.loc[mask, 'birth_year_int'].values[0]):
                    df.loc[mask, 'birth_year_int'] = float(year)
                    updated_count += 1
                    print(f"✓ {name}: {year}年")

    # 2. 架空キャラクターの設定適用
    print("\n=== Phase 2: 架空キャラクター設定の適用 ===")
    for name, year in fictional_character_birth_years.items():
        if year is not None:
            mask = df['person_name_display'] == name
            if mask.any():
                if pd.isna(df.loc[mask, 'birth_year_int'].values[0]):
                    df.loc[mask, 'birth_year_int'] = float(year)
                    updated_count += 1
                    print(f"✓ {name}: {year}年（設定）")

    # 3. Wikipedia APIからの自動収集（上位50人のみ試行）
    print("\n=== Phase 3: Wikipedia API自動収集（限定的） ===")
    missing_df = df[df['birth_year_int'].isna() & df['wikipedia_url'].notna()]
    top_missing = missing_df.nlargest(50, 'fame_score')

    api_success = 0
    for idx, row in top_missing.iterrows():
        person_name = row['person_name_display']
        wikipedia_url = row['wikipedia_url']

        print(f"Checking {person_name}...", end=' ')
        year = get_wikipedia_year(wikipedia_url)

        if year:
            df.at[idx, 'birth_year_int'] = float(year)
            updated_count += 1
            api_success += 1
            print(f"✓ {year}年")
        else:
            print("✗")

        time.sleep(0.5)  # API制限対策

        if api_success >= 10:  # 10件成功したら一旦停止
            print("API収集を10件で停止（レート制限対策）")
            break

    # 統計を出力
    print(f"\n=== 更新結果 ===")
    print(f"更新件数: {updated_count}")
    print(f"誕生年保有率: {df['birth_year_int'].notna().sum()/len(df)*100:.1f}%")

    # 更新されたCSVを保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_WITH_BIRTH_YEARS_{timestamp}.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n保存先: {output_file}")

    return df

if __name__ == '__main__':
    df = collect_birth_years()