#!/usr/bin/env python3
"""
Wikipedia URLの存在確認と修正を行うスクリプト
MediaWiki APIを使用して実際のページ存在を検証
"""

import pandas as pd
import requests
import time
import json
import urllib.parse
from datetime import datetime
import re

class WikipediaVerifier:
    """Wikipedia APIを使用したページ存在確認クラス"""

    def __init__(self):
        self.api_url = "https://ja.wikipedia.org/w/api.php"
        self.base_url = "https://ja.wikipedia.org/wiki/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ultra-Think-Database/1.0 (https://example.com/contact)'
        })
        self.cache = {}  # 検証結果のキャッシュ

    def batch_check_pages(self, titles, batch_size=50):
        """
        複数のページタイトルを一括で存在確認

        Args:
            titles: ページタイトルのリスト
            batch_size: 一度に確認するページ数（最大50）

        Returns:
            dict: タイトル -> 存在状態のマッピング
        """
        results = {}

        # バッチ処理
        for i in range(0, len(titles), batch_size):
            batch = titles[i:i + batch_size]

            # 空のタイトルをスキップ
            batch = [t for t in batch if t and t.strip()]

            if not batch:
                continue

            # APIパラメータ
            params = {
                'action': 'query',
                'format': 'json',
                'titles': '|'.join(batch),
                'prop': 'info',
                'inprop': 'url'
            }

            try:
                response = self.session.get(self.api_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                # 結果の解析
                pages = data.get('query', {}).get('pages', {})

                for page_id, page_info in pages.items():
                    title = page_info.get('title', '')

                    if page_id == '-1' or 'missing' in page_info:
                        # ページが存在しない
                        results[title] = {
                            'exists': False,
                            'status': '不存在',
                            'url': None
                        }
                    elif 'redirect' in page_info:
                        # リダイレクトページ
                        results[title] = {
                            'exists': True,
                            'status': 'リダイレクト',
                            'url': page_info.get('fullurl', '')
                        }
                    else:
                        # ページが存在
                        results[title] = {
                            'exists': True,
                            'status': '存在',
                            'url': page_info.get('fullurl', '')
                        }

            except Exception as e:
                print(f"  ⚠️ APIエラー（バッチ {i//batch_size + 1}）: {e}")
                # エラー時は不明として処理
                for title in batch:
                    results[title] = {
                        'exists': None,
                        'status': '確認エラー',
                        'url': None
                    }

            # レート制限対策
            time.sleep(1)

        return results

    def check_group_page_mention(self, person_name, group_name):
        """
        グループのWikipediaページに個人が記載されているか確認

        Args:
            person_name: 個人名
            group_name: グループ名

        Returns:
            bool: 記載があればTrue
        """
        if not group_name:
            return False

        # グループページの内容を取得
        params = {
            'action': 'query',
            'format': 'json',
            'titles': group_name,
            'prop': 'revisions',
            'rvprop': 'content',
            'rvslots': 'main'
        }

        try:
            response = self.session.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            pages = data.get('query', {}).get('pages', {})

            for page_id, page_info in pages.items():
                if page_id != '-1' and 'revisions' in page_info:
                    # ページ内容を取得
                    content = page_info['revisions'][0]['slots']['main'].get('*', '')

                    # 個人名が含まれているか確認
                    if person_name in content:
                        return True

        except Exception as e:
            print(f"    グループページ確認エラー: {e}")

        return False

    def extract_title_from_url(self, url):
        """URLからWikipediaのページタイトルを抽出"""
        if not url:
            return None

        # URLからタイトル部分を抽出
        if '/wiki/' in url:
            title = url.split('/wiki/')[-1]
            # URLデコード
            title = urllib.parse.unquote(title)
            return title

        return None

def process_wikipedia_verification(input_file):
    """
    メイン処理: Wikipedia URLの検証と修正

    Args:
        input_file: 入力CSVファイル名

    Returns:
        output_file: 出力CSVファイル名
    """
    print("=" * 60)
    print("Wikipedia URL検証・修正処理")
    print("=" * 60)

    # データ読み込み
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df)}件")

    # Wikipedia検証器を初期化
    verifier = WikipediaVerifier()

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

    # バッチで存在確認
    print("\n🔍 Wikipedia APIで存在確認中...")
    print(f"  バッチ数: {(len(titles_to_check) + 49) // 50}")

    verification_results = verifier.batch_check_pages(titles_to_check)

    # 新しいカラムを追加
    if 'wikipedia_status' not in df.columns:
        # wikipedia_urlの次に追加
        columns = list(df.columns)
        url_index = columns.index('wikipedia_url')
        new_columns = (columns[:url_index + 1] +
                      ['wikipedia_status', 'wikipedia_verified_at'] +
                      columns[url_index + 1:])
        df = df.reindex(columns=new_columns)

    # 結果を反映
    print("\n📝 検証結果を反映中...")

    # 統計情報
    stats = {
        '存在': 0,
        '不存在': 0,
        'リダイレクト': 0,
        '確認エラー': 0,
        'グループページのみ': 0
    }

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for title, result in verification_results.items():
        if title in title_to_index:
            idx = title_to_index[title]

            if result['exists']:
                # ページが存在する場合
                df.at[idx, 'wikipedia_url'] = result['url']
                df.at[idx, 'wikipedia_status'] = result['status']
                stats[result['status']] += 1

            else:
                # ページが存在しない場合
                # グループページを確認
                person_name = df.at[idx, 'person_name']
                group_name = df.at[idx, 'group_name']

                if group_name and verifier.check_group_page_mention(person_name, group_name):
                    # グループページに記載あり
                    df.at[idx, 'wikipedia_url'] = ''  # 個人ページはなし
                    df.at[idx, 'wikipedia_status'] = 'グループページのみ'
                    df.at[idx, 'exists_on_group_page'] = 'グループページに記載あり'
                    stats['グループページのみ'] += 1
                else:
                    # 完全に存在しない
                    df.at[idx, 'wikipedia_url'] = ''  # URLを削除
                    df.at[idx, 'wikipedia_status'] = '不存在'
                    stats['不存在'] += 1

            df.at[idx, 'wikipedia_verified_at'] = current_time

    # URLがない行の処理
    empty_url_count = 0
    for idx, row in df.iterrows():
        if pd.isna(row.get('wikipedia_url')) or row.get('wikipedia_url') == '':
            if pd.isna(row.get('wikipedia_status')):
                df.at[idx, 'wikipedia_status'] = '未設定'
                empty_url_count += 1

    # 統計表示
    print("\n📊 検証結果統計:")
    print(f"  - 存在: {stats['存在']:,}件")
    print(f"  - リダイレクト: {stats['リダイレクト']:,}件")
    print(f"  - 不存在（削除）: {stats['不存在']:,}件")
    print(f"  - グループページのみ: {stats['グループページのみ']:,}件")
    print(f"  - 確認エラー: {stats['確認エラー']:,}件")
    print(f"  - 未設定: {empty_url_count:,}件")

    # サンプル表示
    print("\n📝 削除されたURL例（最初の10件）:")
    deleted_samples = df[df['wikipedia_status'] == '不存在'].head(10)
    for idx, row in deleted_samples.iterrows():
        print(f"  - {row['person_name_display']} → URLを削除（ページ不存在）")

    # ファイル保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_wikipedia_verified_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ ファイル保存完了: {output_file}")
    print(f"  - 総レコード数: {len(df):,}件")
    print(f"  - カラム数: {len(df.columns)}")

    return output_file

if __name__ == "__main__":
    # 最新のファイルを処理
    input_file = 'ultra_think_with_wikipedia_20250915_132302.csv'
    output_file = process_wikipedia_verification(input_file)
    print(f"\n完了！出力ファイル: {output_file}")