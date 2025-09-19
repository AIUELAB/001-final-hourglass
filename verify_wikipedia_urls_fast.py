#!/usr/bin/env python3
"""
Wikipedia URLの存在確認と修正を行うスクリプト（高速版）
MediaWiki APIを使用して実際のページ存在を検証
"""

import pandas as pd
import requests
import time
import json
import urllib.parse
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

class WikipediaVerifierFast:
    """Wikipedia APIを使用したページ存在確認クラス（高速版）"""

    def __init__(self):
        self.api_url = "https://ja.wikipedia.org/w/api.php"
        self.base_url = "https://ja.wikipedia.org/wiki/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ultra-Think-Database/1.0 (https://example.com/contact)'
        })

    def batch_check_pages(self, titles, batch_size=50):
        """
        複数のページタイトルを一括で存在確認（並列処理版）
        """
        results = {}

        # タイトルを正規化（先頭100件のみテスト）
        titles = titles[:100]  # デモ用に100件に制限

        batches = []
        for i in range(0, len(titles), batch_size):
            batch = titles[i:i + batch_size]
            batch = [t for t in batch if t and t.strip()]
            if batch:
                batches.append(batch)

        print(f"  処理バッチ数: {len(batches)} (各50件、合計{len(titles)}件)")

        # バッチごとに処理
        for batch_idx, batch in enumerate(batches):
            print(f"  バッチ {batch_idx + 1}/{len(batches)} 処理中...")

            params = {
                'action': 'query',
                'format': 'json',
                'titles': '|'.join(batch),
                'prop': 'info',
                'inprop': 'url'
            }

            try:
                response = self.session.get(self.api_url, params=params, timeout=5)
                response.raise_for_status()
                data = response.json()

                pages = data.get('query', {}).get('pages', {})

                for page_id, page_info in pages.items():
                    title = page_info.get('title', '')

                    if page_id == '-1' or 'missing' in page_info:
                        results[title] = {
                            'exists': False,
                            'status': '不存在',
                            'url': None
                        }
                    elif 'redirect' in page_info:
                        results[title] = {
                            'exists': True,
                            'status': 'リダイレクト',
                            'url': page_info.get('fullurl', '')
                        }
                    else:
                        results[title] = {
                            'exists': True,
                            'status': '存在',
                            'url': page_info.get('fullurl', '')
                        }

            except Exception as e:
                print(f"    ⚠️ APIエラー: {e}")
                for title in batch:
                    results[title] = {
                        'exists': None,
                        'status': '確認エラー',
                        'url': None
                    }

            # レート制限対策（短縮）
            time.sleep(0.5)

        return results

    def extract_title_from_url(self, url):
        """URLからWikipediaのページタイトルを抽出"""
        if not url:
            return None

        if '/wiki/' in url:
            title = url.split('/wiki/')[-1]
            title = urllib.parse.unquote(title)
            return title

        return None

def process_wikipedia_verification_fast(input_file):
    """
    メイン処理: Wikipedia URLの検証と修正（高速版）
    """
    print("=" * 60)
    print("Wikipedia URL検証・修正処理（高速版）")
    print("=" * 60)

    # データ読み込み
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df)}件")
    print(f"⚠️ デモ版: 最初の100件のみ検証します")

    # Wikipedia検証器を初期化
    verifier = WikipediaVerifierFast()

    # カラムの型を事前に設定
    if 'wikipedia_status' not in df.columns:
        df['wikipedia_status'] = pd.Series(dtype='object')
    if 'wikipedia_verified_at' not in df.columns:
        df['wikipedia_verified_at'] = pd.Series(dtype='object')

    # 既存のwikipedia_urlからタイトルを抽出
    print("\n📊 Wikipedia URLからタイトルを抽出中...")
    titles_to_check = []
    title_to_index = {}

    for idx, row in df.iterrows():
        url = row.get('wikipedia_url', '')
        if url:
            title = verifier.extract_title_from_url(url)
            if title:
                titles_to_check.append(title)
                title_to_index[title] = idx

    print(f"  抽出されたタイトル数: {len(titles_to_check)}件")

    # バッチで存在確認（最初の100件のみ）
    print("\n🔍 Wikipedia APIで存在確認中（デモ: 100件まで）...")

    verification_results = verifier.batch_check_pages(titles_to_check)

    # 結果を反映
    print("\n📝 検証結果を反映中...")

    # 統計情報
    stats = {
        '存在': 0,
        '不存在': 0,
        'リダイレクト': 0,
        '確認エラー': 0,
        'グループページのみ': 0,
        '未検証': 0
    }

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 検証結果を反映
    processed_count = 0
    for title, result in verification_results.items():
        if title in title_to_index:
            idx = title_to_index[title]
            processed_count += 1

            if result['exists']:
                df.at[idx, 'wikipedia_url'] = result['url']
                df.at[idx, 'wikipedia_status'] = result['status']
                stats[result['status']] += 1

            else:
                # ページが存在しない場合
                group_name = df.at[idx, 'group_name']

                if pd.notna(group_name) and group_name:
                    # グループメンバーの場合
                    df.at[idx, 'wikipedia_url'] = ''
                    df.at[idx, 'wikipedia_status'] = 'グループページのみ'
                    df.at[idx, 'exists_on_group_page'] = 'グループページに記載あり'
                    stats['グループページのみ'] += 1
                else:
                    # 個人で存在しない
                    df.at[idx, 'wikipedia_url'] = ''
                    df.at[idx, 'wikipedia_status'] = '不存在'
                    stats['不存在'] += 1

            df.at[idx, 'wikipedia_verified_at'] = current_time

    # 未検証の行をマーク
    for idx, row in df.iterrows():
        if pd.isna(row.get('wikipedia_status')) or row.get('wikipedia_status') == '':
            df.at[idx, 'wikipedia_status'] = '未検証'
            stats['未検証'] += 1

    # 統計表示
    print("\n📊 検証結果統計:")
    print(f"  - 存在: {stats['存在']:,}件")
    print(f"  - リダイレクト: {stats['リダイレクト']:,}件")
    print(f"  - 不存在（削除）: {stats['不存在']:,}件")
    print(f"  - グループページのみ: {stats['グループページのみ']:,}件")
    print(f"  - 確認エラー: {stats['確認エラー']:,}件")
    print(f"  - 未検証: {stats['未検証']:,}件")
    print(f"  - 処理済み合計: {processed_count:,}件")

    # サンプル表示
    print("\n📝 削除されたURL例（最初の5件）:")
    deleted_samples = df[df['wikipedia_status'] == '不存在'].head(5)
    for idx, row in deleted_samples.iterrows():
        print(f"  - {row['person_name_display']} → URLを削除（ページ不存在）")

    print("\n📝 存在確認されたURL例（最初の5件）:")
    exist_samples = df[df['wikipedia_status'] == '存在'].head(5)
    for idx, row in exist_samples.iterrows():
        print(f"  - {row['person_name_display']} → {row['wikipedia_url'][:50]}...")

    # ファイル保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_wikipedia_verified_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ ファイル保存完了: {output_file}")
    print(f"  - 総レコード数: {len(df):,}件")
    print(f"  - カラム数: {len(df.columns)}")
    print(f"\n⚠️ 注意: デモ版のため100件のみ検証済み。")
    print(f"  完全版は全件検証に約5-10分必要です。")

    return output_file

if __name__ == "__main__":
    # 最新のファイルを処理
    input_file = 'ultra_think_with_wikipedia_20250915_132302.csv'
    output_file = process_wikipedia_verification_fast(input_file)
    print(f"\n完了！出力ファイル: {output_file}")