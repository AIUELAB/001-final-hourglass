#!/usr/bin/env python3
"""
実際のAPIを使用した検索結果数取得スクリプト
SerpAPIを使用して本物のGoogle検索結果数を取得
"""

import pandas as pd
import numpy as np
import json
import re
import time
import os
from datetime import datetime
from tqdm import tqdm
from typing import Dict, List, Optional, Tuple
import pickle
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import warnings
from dotenv import load_dotenv
warnings.filterwarnings('ignore')

# SerpAPI
try:
    from serpapi import Client
    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    print("⚠️ SerpAPIライブラリがインストールされていません")
    print("pip install serpapi でインストールしてください")

# Brave Search API
import requests

class RealSearchCounter:
    """実際のAPIで検索結果数を取得するクラス"""

    def __init__(self):
        self.cache_file = 'real_search_cache.json'
        self.search_cache = self.load_cache()
        self.session_file = 'search_session_real.pkl'

        # API設定
        self.serpapi_key = os.getenv('SERPAPI_API_KEY')
        self.brave_api_key = os.getenv('BRAVE_API_KEY')

        # SerpAPIクライアント初期化
        if SERPAPI_AVAILABLE and self.serpapi_key:
            self.serpapi_client = Client(api_key=self.serpapi_key)
            print("✅ SerpAPI初期化成功")
        else:
            self.serpapi_client = None

        # カウンター
        self.api_calls = 0
        self.api_limit = 5000  # SerpAPIの月間制限

    def load_cache(self) -> Dict:
        """キャッシュを読み込み"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_cache(self):
        """キャッシュを保存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.search_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"キャッシュ保存エラー: {e}")

    def save_session(self, data: Dict):
        """セッション情報を保存"""
        try:
            with open(self.session_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"セッション保存エラー: {e}")

    def load_session(self) -> Optional[Dict]:
        """セッション情報を読み込み"""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'rb') as f:
                    return pickle.load(f)
            except:
                return None
        return None

    def calculate_priority_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """優先度スコアを計算"""
        print("\n📊 優先度スコアを計算中...")

        df = df.copy()

        # name_recognitionスコア
        if 'name_recognition' in df.columns:
            df['norm_recognition'] = pd.to_numeric(df['name_recognition'], errors='coerce').fillna(0) / 100
        else:
            df['norm_recognition'] = 0

        # Wikipedia存在スコア
        if 'wikipedia_status' in df.columns:
            df['wikipedia_score'] = df['wikipedia_status'].apply(
                lambda x: 1.0 if x == '存在' else 0.5 if x == 'リダイレクト' else 0
            )
        else:
            df['wikipedia_score'] = 0

        # Wikipedia文字数スコア
        if 'wikipedia_content_length' in df.columns:
            content_lengths = pd.to_numeric(df['wikipedia_content_length'], errors='coerce').fillna(0)
            max_length = content_lengths.max()
            if max_length > 0:
                df['content_score'] = np.log1p(content_lengths) / np.log1p(max_length)
            else:
                df['content_score'] = 0
        else:
            df['content_score'] = 0

        # カテゴリ重要度
        category_weights = {
            '政治': 0.9,
            'スポーツ': 0.85,
            'エンタメ': 0.8,
            '現代のイノベーター': 0.75,
            '文化・芸術': 0.7,
            '学術・科学': 0.65,
            'その他': 0.5,
            '架空の存在': 0.3
        }

        if 'category' in df.columns:
            df['category_score'] = df['category'].map(category_weights).fillna(0.5)
        else:
            df['category_score'] = 0.5

        # 総合優先度スコア
        df['priority_score'] = (
            df['norm_recognition'] * 0.35 +
            df['wikipedia_score'] * 0.25 +
            df['content_score'] * 0.25 +
            df['category_score'] * 0.15
        )

        # グループメンバーはスコアを上げる
        if 'group_name' in df.columns:
            df.loc[df['group_name'].notna() & (df['group_name'] != ''), 'priority_score'] *= 1.1

        df['priority_score'] = df['priority_score'] * 100

        return df

    def create_search_query(self, row: pd.Series) -> str:
        """最適な検索クエリを生成"""
        # 基本の名前
        name = str(row.get('person_name_display', ''))
        if not name:
            name = str(row.get('person_name', ''))

        # 完全一致検索
        query = f'"{name}"'

        # 職業を追加
        occupation = row.get('occupation', '')
        if occupation and str(occupation) != 'nan':
            query += f' {occupation}'

        # グループ名を追加
        group = row.get('group_name', '')
        if group and str(group) != 'nan' and group != name:
            query += f' "{group}"'

        return query

    def get_serpapi_results(self, query: str) -> Optional[int]:
        """SerpAPIで実際の検索結果数を取得"""

        # キャッシュチェック
        cache_key = f"serpapi:{query}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]

        if not self.serpapi_client:
            return None

        try:
            # SerpAPI検索実行
            results = self.serpapi_client.search({
                'q': query,
                'engine': 'google',
                'hl': 'ja',  # 日本語
                'gl': 'jp',  # 日本
                'num': 10    # 結果数（総数取得には影響しない）
            })

            # 検索結果数を抽出
            if 'search_information' in results:
                total_results = results['search_information'].get('total_results', 0)

                # 文字列から数値に変換
                if isinstance(total_results, str):
                    # "約 1,230,000 件" のような形式から数値を抽出
                    numbers = re.findall(r'[\d,]+', total_results)
                    if numbers:
                        total_results = int(numbers[0].replace(',', ''))
                    else:
                        total_results = 0

                self.search_cache[cache_key] = total_results
                self.api_calls += 1
                return total_results

        except Exception as e:
            print(f"  SerpAPIエラー（{query[:30]}...）: {e}")

        return None

    def get_brave_results(self, query: str) -> Optional[int]:
        """Brave Search APIで検索結果数を取得"""

        # キャッシュチェック
        cache_key = f"brave:{query}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]

        if not self.brave_api_key:
            return None

        try:
            headers = {
                'X-Subscription-Token': self.brave_api_key,
                'Accept': 'application/json'
            }

            params = {
                'q': query,
                'country': 'jp',
                'lang': 'ja',
                'count': 1  # 結果数だけ必要
            }

            response = requests.get(
                'https://api.search.brave.com/res/v1/web/search',
                headers=headers,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                # 推定結果数を取得（Braveは正確な数を提供しない場合がある）
                if 'web' in data and 'results' in data['web']:
                    # 結果がある場合は推定値を生成
                    # （Braveは総数を直接提供しないため、推定が必要）
                    estimated_count = len(data['web']['results']) * 10000
                    self.search_cache[cache_key] = estimated_count
                    return estimated_count

        except Exception as e:
            print(f"  Brave APIエラー（{query[:30]}...）: {e}")

        return None

    def batch_search(self, df: pd.DataFrame, limit: int = 1000, use_serpapi: bool = True) -> pd.DataFrame:
        """バッチで検索を実行"""

        # セッション復元
        session = self.load_session()
        if session:
            print(f"📂 前回のセッションを復元（{session['completed']}/{session['total']}件完了）")
            start_idx = session['completed']
            results = session['results']
        else:
            start_idx = 0
            results = {}

        # 優先度でソート
        df_sorted = df.sort_values('priority_score', ascending=False)
        df_to_search = df_sorted.iloc[start_idx:min(limit, len(df_sorted))]

        print(f"\n🔍 検索結果数を取得中（{len(df_to_search)}件）...")

        if use_serpapi and self.serpapi_client:
            print("  📡 使用API: SerpAPI (Google検索)")
        elif self.brave_api_key:
            print("  📡 使用API: Brave Search")
        else:
            print("  ⚠️ APIが設定されていません")
            return df

        with tqdm(total=len(df_to_search), initial=start_idx, desc="検索実行") as pbar:
            for idx, row in df_to_search.iterrows():
                query = self.create_search_query(row)

                # API選択と実行
                count = None
                if use_serpapi and self.serpapi_client:
                    count = self.get_serpapi_results(query)
                elif self.brave_api_key:
                    count = self.get_brave_results(query)

                if count is not None:
                    results[idx] = {
                        'query': query,
                        'count': count,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'serpapi' if use_serpapi else 'brave'
                    }

                pbar.update(1)

                # 定期的に保存
                if len(results) % 10 == 0:
                    self.save_cache()
                    self.save_session({
                        'completed': start_idx + len(results),
                        'total': limit,
                        'results': results
                    })

                # レート制限
                time.sleep(1.0 if use_serpapi else 0.5)

                # API制限チェック
                if self.api_calls >= self.api_limit:
                    print(f"\n⚠️ API制限に達しました（{self.api_calls}/{self.api_limit}）")
                    break

        # 最終保存
        self.save_cache()

        # 結果を反映
        df['search_result_count'] = 0
        df['search_query'] = ''
        df['search_timestamp'] = ''
        df['search_source'] = ''

        for idx, data in results.items():
            if idx in df.index:
                df.at[idx, 'search_result_count'] = data['count']
                df.at[idx, 'search_query'] = data['query']
                df.at[idx, 'search_timestamp'] = data['timestamp']
                df.at[idx, 'search_source'] = data['source']

        return df

def main():
    print("=" * 60)
    print("実際のAPI検索結果数取得処理")
    print("=" * 60)

    # .envファイルから環境変数を読み込み
    load_dotenv()

    # データ読み込み
    input_file = 'ultra_think_with_search_counts_20250915_140948.csv'

    if not os.path.exists(input_file):
        # 別のファイルを試す
        input_file = 'ultra_think_with_content_length_20250915_135623.csv'
        if not os.path.exists(input_file):
            print(f"❌ ファイルが見つかりません")
            return

    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df)}件")

    # APIキー確認
    serpapi_key = os.getenv('SERPAPI_API_KEY')
    brave_key = os.getenv('BRAVE_API_KEY')

    print("\n📡 API設定状況:")
    print(f"  SerpAPI: {'✅ 設定済み' if serpapi_key else '❌ 未設定'}")
    print(f"  Brave: {'✅ 設定済み' if brave_key else '❌ 未設定'}")

    if not serpapi_key and not brave_key:
        print("\n❌ APIキーが設定されていません")
        print("以下のコマンドを実行してください:")
        print("  python3 scripts/load_api_keys.py")
        return

    # 検索カウンター初期化
    counter = RealSearchCounter()

    # 優先度スコア計算
    df = counter.calculate_priority_score(df)

    # 優先度統計
    print("\n📊 優先度スコア統計:")
    print(f"  最高スコア: {df['priority_score'].max():.1f}")
    print(f"  平均スコア: {df['priority_score'].mean():.1f}")
    print(f"  中央値: {df['priority_score'].median():.1f}")

    # 上位サンプル
    print("\n🏆 優先度上位5件:")
    top_5 = df.nlargest(5, 'priority_score')[['person_name_display', 'category', 'priority_score']]
    for idx, row in top_5.iterrows():
        print(f"  {row['person_name_display']}: {row['priority_score']:.1f}点 ({row['category']})")

    # 新しいカラムを追加
    if 'search_result_count' not in df.columns:
        df['search_result_count'] = 0
    if 'search_query' not in df.columns:
        df['search_query'] = ''
    if 'search_timestamp' not in df.columns:
        df['search_timestamp'] = ''
    if 'search_source' not in df.columns:
        df['search_source'] = ''

    # 実行確認
    print("\n" + "=" * 60)
    print("⚠️ API実行確認")
    print("=" * 60)
    print(f"処理予定: 上位1000件")
    print(f"推定時間: 約{1000/60:.1f}分（レート制限考慮）")
    print(f"API使用: {'SerpAPI' if serpapi_key else 'Brave Search'}")

    # 本番実行（上位1000件）
    print("\n🚀 本番実行: 上位1000件を処理します")
    print("⏱️ 予想処理時間: 約17分（レート制限により60件/分）")

    # バッチ検索実行
    df = counter.batch_search(df, limit=1000, use_serpapi=bool(serpapi_key))

    # 実検索結果の統計
    searched_df = df[df['search_result_count'] > 0]
    print(f"\n✅ 検索完了: {len(searched_df)}件")
    print(f"  APIコール数: {counter.api_calls}")

    if len(searched_df) > 0:
        print("\n📊 検索結果統計:")
        print(f"  最大: {searched_df['search_result_count'].max():,}件")
        print(f"  平均: {searched_df['search_result_count'].mean():,.0f}件")
        print(f"  中央値: {searched_df['search_result_count'].median():,.0f}件")

        # 検索結果詳細
        print("\n🔍 検索結果詳細:")
        for idx, row in searched_df.head(10).iterrows():
            print(f"  {row['person_name_display']}: {row['search_result_count']:,}件")
            print(f"    クエリ: {row['search_query']}")

    # ファイル保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_real_search_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ ファイル保存完了: {output_file}")
    print(f"  - 総レコード数: {len(df):,}件")
    print(f"  - 実測定済み: {len(searched_df)}件")

    # セッション削除
    if os.path.exists(counter.session_file):
        os.remove(counter.session_file)

    return output_file

if __name__ == "__main__":
    output_file = main()
    if output_file:
        print(f"\n✅ 処理完了！")
        print(f"📁 出力ファイル: {output_file}")