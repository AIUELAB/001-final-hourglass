#!/usr/bin/env python3
"""
Google検索結果数を取得するスクリプト
優先度の高い1000件を実測定し、残りを統計的に推定
"""

import pandas as pd
import numpy as np
import asyncio
import random
import json
import re
import time
from datetime import datetime
from tqdm import tqdm
import os
from playwright.async_api import async_playwright
from typing import Dict, List, Optional, Tuple
import pickle
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

class GoogleSearchCounter:
    """Google検索結果数を取得するクラス"""

    def __init__(self):
        self.cache_file = 'google_search_cache.json'
        self.search_cache = self.load_cache()
        self.session_file = 'search_session.pkl'
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]

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
        """セッション情報を保存（中断/再開用）"""
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

        # 各指標を正規化（0-1の範囲）
        df = df.copy()

        # name_recognitionスコア（欠損値は0として扱う）
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

        # Wikipedia文字数スコア（対数正規化）
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

        # グループメンバーの場合はスコアを少し上げる
        if 'group_name' in df.columns:
            df.loc[df['group_name'].notna() & (df['group_name'] != ''), 'priority_score'] *= 1.1

        # スコアを0-100の範囲に正規化
        df['priority_score'] = df['priority_score'] * 100

        return df

    def create_search_query(self, row: pd.Series) -> str:
        """最適な検索クエリを生成"""
        queries = []

        # 基本の名前（必須）
        name = str(row.get('person_name_display', ''))
        if not name:
            name = str(row.get('person_name', ''))

        # 完全一致検索
        query = f'"{name}"'

        # 職業を追加（精度向上）
        occupation = row.get('occupation', '')
        if occupation and str(occupation) != 'nan':
            query += f' {occupation}'

        # グループ名を追加（該当する場合）
        group = row.get('group_name', '')
        if group and str(group) != 'nan':
            query += f' "{group}"'

        return query

    async def search_with_playwright(self, query: str, browser) -> Optional[int]:
        """Playwrightで検索結果数を取得"""

        # キャッシュチェック
        if query in self.search_cache:
            return self.search_cache[query]

        try:
            # 新しいページを作成
            page = await browser.new_page()

            # ランダムなUser-Agent設定
            await page.set_extra_http_headers({
                'User-Agent': random.choice(self.user_agents)
            })

            # Google検索
            await page.goto('https://www.google.com/search?q=' + query.replace(' ', '+'))

            # 結果数を取得
            result_stats = await page.query_selector('#result-stats')
            if result_stats:
                text = await result_stats.inner_text()

                # 数値を抽出
                # "約 1,230,000 件" or "About 1,230,000 results"
                match = re.search(r'[\d,]+', text.replace(',', ''))
                if match:
                    count = int(match.group().replace(',', ''))
                    self.search_cache[query] = count
                    await page.close()
                    return count

            await page.close()
            return 0

        except Exception as e:
            print(f"\n検索エラー（{query[:30]}...）: {e}")
            if 'page' in locals():
                await page.close()
            return None

    async def batch_search(self, df: pd.DataFrame, limit: int = 1000) -> pd.DataFrame:
        """バッチで検索を実行"""

        # セッション復元チェック
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
        df_to_search = df_sorted.iloc[start_idx:limit]

        print(f"\n🔍 Google検索結果数を取得中（{len(df_to_search)}件）...")
        print("  ※ レート制限のため3-5秒間隔で実行")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            with tqdm(total=len(df_to_search), initial=start_idx, desc="検索実行") as pbar:
                for idx, row in df_to_search.iterrows():
                    query = self.create_search_query(row)

                    # 検索実行
                    count = await self.search_with_playwright(query, browser)

                    if count is not None:
                        results[idx] = {
                            'query': query,
                            'count': count,
                            'timestamp': datetime.now().isoformat()
                        }

                    pbar.update(1)

                    # 定期的に保存
                    if len(results) % 20 == 0:
                        self.save_cache()
                        self.save_session({
                            'completed': start_idx + len(results),
                            'total': limit,
                            'results': results
                        })

                    # レート制限
                    await asyncio.sleep(random.uniform(3, 5))

            await browser.close()

        # 最終保存
        self.save_cache()

        # 結果を反映
        df['google_search_count'] = 0
        df['search_query'] = ''
        df['search_timestamp'] = ''

        for idx, data in results.items():
            if idx in df.index:
                df.at[idx, 'google_search_count'] = data['count']
                df.at[idx, 'search_query'] = data['query']
                df.at[idx, 'search_timestamp'] = data['timestamp']

        return df

    def build_prediction_model(self, df: pd.DataFrame) -> Tuple[RandomForestRegressor, LabelEncoder]:
        """予測モデルを構築"""
        print("\n🤖 統計的予測モデルを構築中...")

        # 訓練データの準備（検索結果がある行のみ）
        train_df = df[df['google_search_count'] > 0].copy()

        if len(train_df) < 100:
            print("  ⚠️ 訓練データ不足（最低100件必要）")
            return None, None

        # 特徴量の準備
        features = []

        # 数値特徴量
        if 'name_recognition' in df.columns:
            train_df['name_recognition_num'] = pd.to_numeric(train_df['name_recognition'], errors='coerce').fillna(0)
            features.append('name_recognition_num')

        if 'wikipedia_content_length' in df.columns:
            train_df['content_length_log'] = np.log1p(pd.to_numeric(train_df['wikipedia_content_length'], errors='coerce').fillna(0))
            features.append('content_length_log')

        if 'wikipedia_sections_count' in df.columns:
            train_df['sections_count'] = pd.to_numeric(train_df['wikipedia_sections_count'], errors='coerce').fillna(0)
            features.append('sections_count')

        # カテゴリ特徴量
        le_category = LabelEncoder()
        if 'category' in df.columns:
            train_df['category_encoded'] = le_category.fit_transform(train_df['category'].fillna('その他'))
            features.append('category_encoded')

        # グループメンバーフラグ
        if 'group_name' in df.columns:
            train_df['has_group'] = (train_df['group_name'].notna() & (train_df['group_name'] != '')).astype(int)
            features.append('has_group')

        # Wikipedia存在フラグ
        if 'wikipedia_status' in df.columns:
            train_df['has_wikipedia'] = (train_df['wikipedia_status'] == '存在').astype(int)
            features.append('has_wikipedia')

        # 訓練データとテストデータに分割
        X = train_df[features]
        y = np.log1p(train_df['google_search_count'])  # 対数変換

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # モデル訓練
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        model.fit(X_train, y_train)

        # 評価
        score = model.score(X_test, y_test)
        print(f"  📊 モデル精度（R²スコア）: {score:.3f}")

        return model, le_category, features

    def predict_search_counts(self, df: pd.DataFrame, model, le_category, features: List[str]) -> pd.DataFrame:
        """検索結果数を予測"""
        print("\n📈 残りのレコードの検索結果数を予測中...")

        # 予測対象の抽出
        predict_df = df[df['google_search_count'] == 0].copy()

        if len(predict_df) == 0:
            return df

        # 特徴量の準備
        if 'name_recognition' in features:
            predict_df['name_recognition_num'] = pd.to_numeric(predict_df['name_recognition'], errors='coerce').fillna(0)

        if 'content_length_log' in features:
            predict_df['content_length_log'] = np.log1p(pd.to_numeric(predict_df['wikipedia_content_length'], errors='coerce').fillna(0))

        if 'sections_count' in features:
            predict_df['sections_count'] = pd.to_numeric(predict_df['wikipedia_sections_count'], errors='coerce').fillna(0)

        if 'category_encoded' in features:
            # 未知のカテゴリは'その他'として扱う
            predict_df['category_filled'] = predict_df['category'].fillna('その他')
            predict_df['category_encoded'] = predict_df['category_filled'].apply(
                lambda x: le_category.transform([x])[0] if x in le_category.classes_ else le_category.transform(['その他'])[0]
            )

        if 'has_group' in features:
            predict_df['has_group'] = (predict_df['group_name'].notna() & (predict_df['group_name'] != '')).astype(int)

        if 'has_wikipedia' in features:
            predict_df['has_wikipedia'] = (predict_df['wikipedia_status'] == '存在').astype(int)

        # 予測実行
        X_predict = predict_df[features]
        y_pred_log = model.predict(X_predict)
        y_pred = np.expm1(y_pred_log).astype(int)  # 対数逆変換

        # 結果を反映
        for idx, pred_count in zip(predict_df.index, y_pred):
            df.at[idx, 'google_search_count'] = pred_count
            df.at[idx, 'search_query'] = f"[推定] {df.at[idx, 'person_name_display']}"
            df.at[idx, 'is_predicted'] = True

        print(f"  ✅ {len(predict_df)}件の予測完了")

        return df

async def main():
    print("=" * 60)
    print("Google検索結果数取得処理")
    print("=" * 60)

    # データ読み込み
    input_file = 'ultra_think_with_content_length_20250915_135623.csv'

    if not os.path.exists(input_file):
        print(f"❌ ファイルが見つかりません: {input_file}")
        return

    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df)}件")

    # 検索カウンター初期化
    counter = GoogleSearchCounter()

    # 優先度スコア計算
    df = counter.calculate_priority_score(df)

    # 優先度統計
    print("\n📊 優先度スコア統計:")
    print(f"  最高スコア: {df['priority_score'].max():.1f}")
    print(f"  平均スコア: {df['priority_score'].mean():.1f}")
    print(f"  中央値: {df['priority_score'].median():.1f}")

    # 上位サンプル表示
    print("\n🏆 優先度上位5件:")
    top_5 = df.nlargest(5, 'priority_score')[['person_name_display', 'category', 'priority_score']]
    for idx, row in top_5.iterrows():
        print(f"  {row['person_name_display']}: {row['priority_score']:.1f}点 ({row['category']})")

    # 新しいカラムを追加
    if 'google_search_count' not in df.columns:
        df['google_search_count'] = 0
    if 'search_query' not in df.columns:
        df['search_query'] = ''
    if 'search_timestamp' not in df.columns:
        df['search_timestamp'] = ''
    if 'is_predicted' not in df.columns:
        df['is_predicted'] = False

    # バッチ検索実行（上位1000件）
    print("\n" + "=" * 60)
    print("Phase 1: 実検索実行（上位1000件）")
    print("=" * 60)

    df = await counter.batch_search(df, limit=1000)

    # 実検索結果の統計
    searched_df = df[df['google_search_count'] > 0]
    print(f"\n✅ 実検索完了: {len(searched_df)}件")

    if len(searched_df) > 0:
        print("\n📊 実検索結果統計:")
        print(f"  最大: {searched_df['google_search_count'].max():,}件")
        print(f"  平均: {searched_df['google_search_count'].mean():,.0f}件")
        print(f"  中央値: {searched_df['google_search_count'].median():,.0f}件")

        # 検索結果上位5件
        print("\n🔍 検索結果上位5件:")
        top_searches = searched_df.nlargest(5, 'google_search_count')[
            ['person_name_display', 'google_search_count', 'category']
        ]
        for idx, row in top_searches.iterrows():
            print(f"  {row['person_name_display']}: {row['google_search_count']:,}件 ({row['category']})")

    # 統計的予測
    print("\n" + "=" * 60)
    print("Phase 2: 統計的予測（残りのレコード）")
    print("=" * 60)

    if len(searched_df) >= 100:
        model, le_category, features = counter.build_prediction_model(df)

        if model:
            df = counter.predict_search_counts(df, model, le_category, features)

            # 予測結果の統計
            predicted_df = df[df['is_predicted'] == True]
            print(f"\n📊 予測結果統計（{len(predicted_df)}件）:")
            print(f"  最大: {predicted_df['google_search_count'].max():,}件")
            print(f"  平均: {predicted_df['google_search_count'].mean():,.0f}件")
            print(f"  中央値: {predicted_df['google_search_count'].median():,.0f}件")
    else:
        print("  ⚠️ 訓練データ不足のため予測をスキップ")

    # 最終統計
    print("\n" + "=" * 60)
    print("📊 最終結果統計")
    print("=" * 60)

    valid_df = df[df['google_search_count'] > 0]
    print(f"  総処理件数: {len(valid_df)}件")
    print(f"  実測定: {len(df[df['is_predicted'] == False])}件")
    print(f"  予測: {len(df[df['is_predicted'] == True])}件")

    # カテゴリ別平均
    if len(valid_df) > 0:
        print("\n📊 カテゴリ別平均検索結果数:")
        category_stats = valid_df.groupby('category')['google_search_count'].agg(['mean', 'count'])
        category_stats = category_stats.sort_values('mean', ascending=False).head(10)

        for category, row in category_stats.iterrows():
            print(f"  {category}: {row['mean']:,.0f}件 (n={int(row['count'])})")

    # ファイル保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_with_google_counts_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ ファイル保存完了: {output_file}")
    print(f"  - 総レコード数: {len(df):,}件")
    print(f"  - カラム数: {len(df.columns)}")

    # レポート生成
    generate_analysis_report(df, len(searched_df), len(predicted_df))

    # セッション削除
    if os.path.exists(counter.session_file):
        os.remove(counter.session_file)

    return output_file

def generate_analysis_report(df: pd.DataFrame, searched_count: int, predicted_count: int):
    """分析レポートを生成"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f'google_search_analysis_{timestamp}.md'

    valid_df = df[df['google_search_count'] > 0]

    # 相関分析
    correlation = 0
    if 'name_recognition' in df.columns and len(valid_df) > 10:
        recognition_values = pd.to_numeric(valid_df['name_recognition'], errors='coerce')
        search_values = valid_df['google_search_count']

        mask = recognition_values.notna()
        if mask.sum() > 10:
            correlation = recognition_values[mask].corr(search_values[mask])

    report = f"""# Google検索結果数分析レポート

## 📅 実行情報
- 実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
- 総レコード数: {len(df):,}件
- 実測定件数: {searched_count}件
- 予測件数: {predicted_count}件

## 📊 検索結果統計

| 指標 | 値 |
|------|-----|
| 最大検索結果数 | {valid_df['google_search_count'].max():,}件 |
| 平均検索結果数 | {valid_df['google_search_count'].mean():,.0f}件 |
| 中央値 | {valid_df['google_search_count'].median():,.0f}件 |
| 知名度との相関 | {correlation:.3f} |

## 💡 知名度指標としての評価

### Google検索結果数の有効性
- **相関係数**: {correlation:.3f}（{"強い相関" if abs(correlation) > 0.7 else "中程度の相関" if abs(correlation) > 0.4 else "弱い相関"}）
- **実用性**: 高い（リアルタイムの関心度を反映）
- **更新頻度**: 日々変動（トレンドに敏感）

## 📈 推奨活用方法

1. **複合指標の構築**
   - Google検索結果数 × 0.3
   - Wikipedia文字数 × 0.3
   - name_recognition × 0.4

2. **カテゴリ別重み付け**
   - 現代人物: Google重視（0.5）
   - 歴史人物: Wikipedia重視（0.5）
   - エンタメ: 両方均等（0.5/0.5）

3. **定期更新**
   - 月次でGoogle検索結果を再取得
   - トレンド分析の実施
"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 分析レポート生成: {report_file}")

if __name__ == "__main__":
    output_file = asyncio.run(main())
    if output_file:
        print(f"\n✅ 処理完了！")
        print(f"📁 出力ファイル: {output_file}")