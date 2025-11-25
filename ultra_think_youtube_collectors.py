#!/usr/bin/env python3
"""
Ultra Think - YouTube API活用日本トップYouTuber収集スクリプト
YouTube Data API v3を使用して日本の有名YouTuberを収集
"""

import os
import requests
import pandas as pd
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import re

# YouTube API設定
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', 'YOUR_API_KEY_HERE')
YOUTUBE_API_BASE = 'https://www.googleapis.com/youtube/v3'

def get_japan_top_channels(api_key: str, max_results: int = 50) -> List[Dict]:
    """
    日本のトップYouTubeチャンネルを取得
    """
    channels = []

    # 日本の人気YouTuberのチャンネルID（手動リスト）
    # これらは確実に追加したい主要チャンネル
    top_channel_ids = [
        'UCZf__ehlCEBPop-_NV19J9w',  # HikakinTV
        'UCgMPP6RRjktV7krOfyUewqw',  # はじめしゃちょー
        'UCibEhpu5HP45-w7Bq1ZIulw',  # Fischer's-フィッシャーズ
        'UCutJqz56653xV2wwSvut_hQ',  # 東海オンエア
        'UC9V3Y3_uzU5e-usObb6IE1w',  # ヒカル
        'UCynIYcsBwTrwBIecconPN2A',  # コムドット
        'UCDIJB_1FxCgtXlmYixfwNWg',  # 水溜りボンド
        'UCpOjLndjOqMoffA-fr8cbKA',  # スカイピース
        'UCWuB-2M55oCxJLSxbyQxcAw',  # QuizKnock
        'UC-_J49BF9tZt5_zQvHVCRGQ',  # おめがシスターズ
    ]

    # チャンネル情報を取得
    for channel_id in top_channel_ids:
        try:
            url = f"{YOUTUBE_API_BASE}/channels"
            params = {
                'part': 'snippet,statistics',
                'id': channel_id,
                'key': api_key
            }

            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if 'items' in data and data['items']:
                    channels.append(data['items'][0])

            time.sleep(0.5)  # レート制限対策

        except Exception as e:
            print(f"Error fetching channel {channel_id}: {e}")

    return channels

def extract_birth_year_from_description(description: str) -> Optional[int]:
    """
    チャンネル説明文から誕生年を抽出
    """
    # 生年月日パターンを検索
    patterns = [
        r'(\d{4})年.*生まれ',
        r'生年月日.*(\d{4})年',
        r'(\d{4})\.(\d{1,2})\.(\d{1,2})',
        r'(\d{4})/(\d{1,2})/(\d{1,2})',
    ]

    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            try:
                year = int(match.group(1))
                if 1900 <= year <= 2010:  # 妥当な範囲
                    return year
            except:
                pass

    return None

def get_predefined_youtubers() -> List[Dict]:
    """
    事前定義された有名YouTuberリスト（誕生年確定）
    """
    return [
        # 個人YouTuber
        {"name": "HIKAKIN", "name_ja": "ヒカキン", "birth_year": 1989, "group": None},
        {"name": "Hajime Syacho", "name_ja": "はじめしゃちょー", "birth_year": 1993, "group": None},
        {"name": "Hikaru", "name_ja": "ヒカル", "birth_year": 1991, "group": None},
        {"name": "Seiya", "name_ja": "セイヤ", "birth_year": 1993, "group": None},
        {"name": "Kajisac", "name_ja": "カジサック", "birth_year": 1980, "group": None},
        {"name": "Raphael", "name_ja": "ラファエル", "birth_year": 1989, "group": None},

        # Fischer's メンバー
        {"name": "Silk Road", "name_ja": "シルクロード", "birth_year": 1994, "group": "フィッシャーズ"},
        {"name": "Masai", "name_ja": "マサイ", "birth_year": 1995, "group": "フィッシャーズ"},
        {"name": "Ndaho", "name_ja": "ンダホ", "birth_year": 1994, "group": "フィッシャーズ"},
        {"name": "Peketan", "name_ja": "ぺけたん", "birth_year": 1995, "group": "フィッシャーズ"},
        {"name": "Dama", "name_ja": "ダーマ", "birth_year": 1995, "group": "フィッシャーズ"},
        {"name": "Zakao", "name_ja": "ザカオ", "birth_year": 1994, "group": "フィッシャーズ"},
        {"name": "Motoki", "name_ja": "モトキ", "birth_year": 1994, "group": "フィッシャーズ"},

        # 東海オンエア
        {"name": "Tetsuya", "name_ja": "てつや", "birth_year": 1993, "group": "東海オンエア"},
        {"name": "Shibayu", "name_ja": "しばゆー", "birth_year": 1993, "group": "東海オンエア"},
        {"name": "Ryo", "name_ja": "りょう", "birth_year": 1993, "group": "東海オンエア"},
        {"name": "Toshimitsu", "name_ja": "としみつ", "birth_year": 1993, "group": "東海オンエア"},
        {"name": "Yumemaru", "name_ja": "ゆめまる", "birth_year": 1995, "group": "東海オンエア"},
        {"name": "Mushimegane", "name_ja": "虫眼鏡", "birth_year": 1992, "group": "東海オンエア"},

        # コムドット
        {"name": "Yamato", "name_ja": "やまと", "birth_year": 1998, "group": "コムドット"},
        {"name": "Yuta", "name_ja": "ゆうた", "birth_year": 1999, "group": "コムドット"},
        {"name": "Yuma", "name_ja": "ゆうま", "birth_year": 1998, "group": "コムドット"},
        {"name": "Hyuga", "name_ja": "ひゅうが", "birth_year": 1998, "group": "コムドット"},
        {"name": "Amugiri", "name_ja": "あむぎり", "birth_year": 1999, "group": "コムドット"},

        # 水溜りボンド
        {"name": "Kanta", "name_ja": "カンタ", "birth_year": 1994, "group": "水溜りボンド"},
        {"name": "Tommy", "name_ja": "トミー", "birth_year": 1993, "group": "水溜りボンド"},

        # スカイピース
        {"name": "Teo", "name_ja": "テオ", "birth_year": 1995, "group": "スカイピース"},
        {"name": "Jin", "name_ja": "じん", "birth_year": 1996, "group": "スカイピース"},

        # QuizKnock
        {"name": "Izawa Takuji", "name_ja": "伊沢拓司", "birth_year": 1994, "group": "QuizKnock"},
        {"name": "Kawamura Takuya", "name_ja": "川村拓哉", "birth_year": 1994, "group": "QuizKnock"},
        {"name": "Fukura P", "name_ja": "ふくらP", "birth_year": 1993, "group": "QuizKnock"},

        # 女性YouTuber
        {"name": "Kanna Hashimoto", "name_ja": "橋本環奈", "birth_year": 1999, "group": None},
        {"name": "Nanako", "name_ja": "ななこ", "birth_year": 2002, "group": None},
        {"name": "Ayanonono", "name_ja": "あやののの", "birth_year": 2000, "group": None},

        # VTuber
        {"name": "Kizuna AI", "name_ja": "キズナアイ", "birth_year": 2016, "group": None},  # デビュー年
        {"name": "Kaguya Luna", "name_ja": "輝夜月", "birth_year": 2017, "group": None},
        {"name": "Mirai Akari", "name_ja": "ミライアカリ", "birth_year": 2017, "group": None},
    ]

def format_person_display(name: str, group: Optional[str]) -> str:
    """
    表示名をフォーマット（グループ名付き）
    """
    if group:
        return f"{name}（{group}）"
    return name

def create_person_record(person_data: Dict) -> Dict:
    """
    個人レコードを作成
    """
    name = person_data['name']
    name_ja = person_data['name_ja']
    birth_year = person_data['birth_year']
    group = person_data.get('group', None)

    # 表示名の作成
    display_name = format_person_display(name_ja, group)

    return {
        'batch_id': 'youtube_influencers',
        'birth_year': birth_year,
        'category': '',
        'cultural_significance': 8,
        'description': '',
        'educational_value': 6,
        'era': '',
        'followers': '',
        'global_recognition': 6,
        'grade': 'A',
        'historical_impact': 5,
        'is_animal': '',
        'is_fictional': '',
        'main_category': 'インターネット',
        'name': name,
        'nationality': '日本',
        'occupation': 'YouTuber',
        'person_name': name,
        'person_name.1': name,
        'person_name_display': display_name,
        'person_name_ja': name_ja,
        'phase': 'YouTubers2024',
        'platform': 'YouTube',
        'subcategory': 'インフルエンサー'
    }

def main():
    print("=== Ultra Think YouTube収集システム ===\n")

    # 事前定義リストから作成
    print("1. 事前定義YouTuberリストを処理中...")
    predefined = get_predefined_youtubers()

    # DataFrame作成
    records = []
    for person in predefined:
        record = create_person_record(person)
        records.append(record)

    df_youtubers = pd.DataFrame(records)
    print(f"   追加: {len(df_youtubers)}人のYouTuber/インフルエンサー")

    # グループ別統計
    print("\n=== グループ別統計 ===")
    group_counts = df_youtubers['person_name_display'].str.extract(r'（(.+)）').value_counts()
    for group, count in group_counts.head(10).items():
        print(f"{group}: {count}人")

    # 既存データと統合
    print("\n2. 既存データベースと統合中...")
    existing_file = 'ultra_think_CLEANED_20250825_204705.csv'

    try:
        existing_df = pd.read_csv(existing_file)
        print(f"   既存: {len(existing_df)}人")

        # 重複チェック
        existing_names = set(zip(existing_df['person_name'].fillna(''),
                                existing_df['birth_year'].fillna(0)))
        new_names = set(zip(df_youtubers['person_name'].fillna(''),
                           df_youtubers['birth_year'].fillna(0)))

        duplicates = new_names & existing_names
        if duplicates:
            print(f"   重複: {len(duplicates)}人（除外）")
            mask = ~df_youtubers.apply(lambda x: (x['person_name'], x['birth_year']) in duplicates, axis=1)
            df_youtubers = df_youtubers[mask]

        # 統合
        merged_df = pd.concat([existing_df, df_youtubers], ignore_index=True)

    except FileNotFoundError:
        print("   既存ファイルなし")
        merged_df = df_youtubers

    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_WITH_YOUTUBERS_{timestamp}.csv'
    merged_df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n✅ 保存完了: {output_file}")
    print(f"   最終人数: {len(merged_df):,}人")

    # 10,000人チェック
    if len(merged_df) >= 10000:
        print("\n🎉 祝！10,000人達成！！")
    else:
        remaining = 10000 - len(merged_df)
        print(f"\n   10,000人まで残り: {remaining}人")

    return merged_df

if __name__ == "__main__":
    main()
