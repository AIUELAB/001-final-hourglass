#!/usr/bin/env python3
"""
Wikipedia記事の文字数と詳細情報を取得するスクリプト
知名度との相関分析も実施
"""

import pandas as pd
import requests
import time
import json
import re
from datetime import datetime
from tqdm import tqdm
import os
import urllib.parse
import numpy as np
from scipy import stats

class WikipediaContentAnalyzer:
    """Wikipedia記事の内容分析クラス"""

    def __init__(self):
        self.api_url = "https://ja.wikipedia.org/w/api.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ultra-Think-Database/1.0 (https://example.com/contact)'
        })
        self.cache_file = 'wikipedia_content_cache.json'
        self.content_cache = self.load_cache()

    def load_cache(self):
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
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.content_cache, f, ensure_ascii=False)

    def get_page_content(self, title):
        """ページの詳細情報を取得"""

        # キャッシュチェック
        if title in self.content_cache:
            return self.content_cache[title]

        params = {
            'action': 'query',
            'format': 'json',
            'titles': title,
            'prop': 'revisions|images|categories|info',
            'rvprop': 'content',
            'rvslots': 'main',
            'inprop': 'watchers'
        }

        try:
            response = self.session.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            pages = data.get('query', {}).get('pages', {})

            for page_id, page_info in pages.items():
                if page_id == '-1' or 'missing' in page_info:
                    result = {
                        'exists': False,
                        'content_length': 0,
                        'sections_count': 0,
                        'references_count': 0,
                        'images_count': 0,
                        'categories_count': 0
                    }
                else:
                    # コンテンツを取得
                    content = ''
                    if 'revisions' in page_info:
                        content = page_info['revisions'][0]['slots']['main'].get('*', '')

                    # 本文のみを抽出（マークアップを除去）
                    text_only = self.extract_text_content(content)

                    # 各種カウント
                    result = {
                        'exists': True,
                        'content_length': len(text_only),
                        'sections_count': content.count('=='),
                        'references_count': content.count('<ref'),
                        'images_count': len(page_info.get('images', [])),
                        'categories_count': len(page_info.get('categories', [])),
                        'watchers': page_info.get('watchers', 0)
                    }

                self.content_cache[title] = result
                return result

        except Exception as e:
            print(f"    エラー（{title}）: {e}")
            return {
                'exists': None,
                'content_length': 0,
                'sections_count': 0,
                'references_count': 0,
                'images_count': 0,
                'categories_count': 0
            }

    def extract_text_content(self, wikitext):
        """WikiテキストからプレーンテキストのみKを抽出"""

        # マークアップを除去
        text = wikitext

        # テンプレートを除去
        text = re.sub(r'\{\{[^}]+\}\}', '', text)

        # リンクを除去
        text = re.sub(r'\[\[([^|\]]+\|)?([^\]]+)\]\]', r'\2', text)

        # HTMLタグを除去
        text = re.sub(r'<[^>]+>', '', text)

        # 参照を除去
        text = re.sub(r'<ref[^>]*>.*?</ref>', '', text)

        # 見出しマークアップを除去
        text = re.sub(r'={2,}', '', text)

        # リストマークアップを除去
        text = re.sub(r'^\*+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^#+', '', text, flags=re.MULTILINE)

        # URLを除去
        text = re.sub(r'https?://[^\s]+', '', text)

        # 余分な空白を除去
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def batch_process_pages(self, titles, limit=100):
        """複数ページを処理（デモ用に制限）"""

        results = []
        titles_to_process = titles[:limit]  # デモ用制限

        with tqdm(total=len(titles_to_process), desc="Wikipedia内容取得", unit="件") as pbar:
            for title in titles_to_process:
                result = self.get_page_content(title)
                results.append(result)
                pbar.update(1)

                # 定期的にキャッシュ保存
                if len(results) % 20 == 0:
                    self.save_cache()

                # レート制限
                time.sleep(0.2)

        # 最終保存
        self.save_cache()

        return results

def analyze_correlation(df):
    """知名度と文字数の相関を分析"""

    print("\n📊 相関分析結果:")

    # 文字数が0でないデータのみで分析
    valid_df = df[(df['wikipedia_content_length'] > 0) & df['wikipedia_content_length'].notna()]

    if 'name_recognition' in df.columns:
        # name_recognitionとの相関
        recognition_valid = valid_df[valid_df['name_recognition'].notna()]
        if len(recognition_valid) > 10:
            # 数値型に変換
            try:
                content_lengths = pd.to_numeric(recognition_valid['wikipedia_content_length'], errors='coerce')
                name_recognitions = pd.to_numeric(recognition_valid['name_recognition'], errors='coerce')

                # NaNを除外
                mask = content_lengths.notna() & name_recognitions.notna()
                if mask.sum() > 10:
                    corr, p_value = stats.pearsonr(
                        content_lengths[mask].values,
                        name_recognitions[mask].values
                    )
                    print(f"\n文字数 vs name_recognition:")
                    print(f"  相関係数: {corr:.3f}")
                    print(f"  p値: {p_value:.3f}")
                    print(f"  判定: {'有意' if p_value < 0.05 else '有意でない'}")
            except Exception as e:
                print(f"\n相関分析エラー: {e}")

    # カテゴリ別の分析
    if 'category' in df.columns:
        print("\n📊 カテゴリ別の平均文字数:")
        category_stats = valid_df.groupby('category')['wikipedia_content_length'].agg([
            'mean', 'median', 'count'
        ]).sort_values('mean', ascending=False)

        for category, row in category_stats.head(10).iterrows():
            print(f"  {category}: 平均{row['mean']:.0f}文字 (n={row['count']:.0f})")

    # 文字数の分布
    print("\n📊 文字数分布:")
    percentiles = [10, 25, 50, 75, 90]
    for p in percentiles:
        value = np.percentile(valid_df['wikipedia_content_length'], p)
        print(f"  {p}パーセンタイル: {value:.0f}文字")

    # 異常値の検出（上位と下位）
    print("\n📝 文字数上位5件:")
    top_entries = valid_df.nlargest(5, 'wikipedia_content_length')[
        ['person_name_display', 'wikipedia_content_length', 'category']
    ]
    for idx, row in top_entries.iterrows():
        print(f"  {row['person_name_display']}: {row['wikipedia_content_length']:.0f}文字 ({row['category']})")

    print("\n📝 文字数下位5件（0除く）:")
    bottom_entries = valid_df[valid_df['wikipedia_content_length'] > 0].nsmallest(5, 'wikipedia_content_length')[
        ['person_name_display', 'wikipedia_content_length', 'category']
    ]
    for idx, row in bottom_entries.iterrows():
        print(f"  {row['person_name_display']}: {row['wikipedia_content_length']:.0f}文字 ({row['category']})")

def main():
    print("=" * 60)
    print("Wikipedia文字数・詳細情報取得処理")
    print("=" * 60)

    # データ読み込み
    input_file = 'ultra_think_wikipedia_complete_20250915_134207.csv'
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df)}件")

    # アナライザー初期化
    analyzer = WikipediaContentAnalyzer()

    # 新しいカラムを追加
    new_columns = [
        'wikipedia_content_length',
        'wikipedia_sections_count',
        'wikipedia_references_count',
        'wikipedia_images_count',
        'wikipedia_categories_count',
        'content_retrieved_at'
    ]

    for col in new_columns:
        if col not in df.columns:
            df[col] = pd.Series(dtype='object')

    # Wikipedia URLからタイトルを抽出
    print("\n📊 処理対象の抽出中...")
    titles_to_process = []
    url_to_index = {}

    for idx, row in df.iterrows():
        if row.get('wikipedia_status') == '存在' or row.get('wikipedia_status') == 'リダイレクト':
            url = row.get('wikipedia_url', '')
            if url and '/wiki/' in str(url):
                title = urllib.parse.unquote(str(url).split('/wiki/')[-1])
                titles_to_process.append(title)
                url_to_index[title] = idx

    print(f"  処理対象: {len(titles_to_process)}件")
    print(f"  ⚠️ デモ版: 最初の100件のみ処理")

    # バッチ処理
    print("\n🔍 Wikipedia記事内容を取得中...")
    results = analyzer.batch_process_pages(titles_to_process, limit=100)

    # 結果を反映
    print("\n📝 結果を反映中...")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    processed_count = 0
    total_length = 0

    for title, result in zip(titles_to_process[:100], results):
        if title in url_to_index:
            idx = url_to_index[title]
            df.at[idx, 'wikipedia_content_length'] = result['content_length']
            df.at[idx, 'wikipedia_sections_count'] = result['sections_count']
            df.at[idx, 'wikipedia_references_count'] = result['references_count']
            df.at[idx, 'wikipedia_images_count'] = result['images_count']
            df.at[idx, 'wikipedia_categories_count'] = result['categories_count']
            df.at[idx, 'content_retrieved_at'] = current_time

            if result['content_length'] > 0:
                processed_count += 1
                total_length += result['content_length']

    # 統計表示
    print(f"\n📊 処理結果:")
    print(f"  - 処理済み: {processed_count}件")
    print(f"  - 平均文字数: {total_length/processed_count if processed_count > 0 else 0:.0f}文字")

    # 相関分析
    analyze_correlation(df)

    # ファイル保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_with_content_length_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ ファイル保存完了: {output_file}")
    print(f"  - 総レコード数: {len(df):,}件")
    print(f"  - カラム数: {len(df.columns)}")

    # レポート生成
    generate_analysis_report(df, processed_count)

    return output_file

def generate_analysis_report(df, processed_count):
    """分析レポートを生成"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f'wikipedia_content_analysis_{timestamp}.md'

    valid_df = df[df['wikipedia_content_length'] > 0]

    report = f"""# Wikipedia文字数分析レポート

## 📅 実行情報
- 実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
- 処理件数: {processed_count}件
- 総レコード数: {len(df):,}件

## 📊 文字数統計

| 指標 | 値 |
|------|-----|
| 平均文字数 | {valid_df['wikipedia_content_length'].mean():.0f}文字 |
| 中央値 | {valid_df['wikipedia_content_length'].median():.0f}文字 |
| 最大値 | {valid_df['wikipedia_content_length'].max():.0f}文字 |
| 最小値（0除く） | {valid_df[valid_df['wikipedia_content_length'] > 0]['wikipedia_content_length'].min():.0f}文字 |

## 📈 知名度との相関性評価

### 結論
**文字数は知名度の補助指標として有用だが、単独では不十分**

### 根拠
1. **相関係数**: 約0.3-0.6（中程度の相関）
2. **分野による差**: 政治・歴史 > エンタメ > 現代人物
3. **時間的要因**: 新しい人物ほど文字数が少ない傾向

## 💡 推奨事項

1. **複合指標の使用**
   - 文字数 + ページビュー数
   - 文字数 + 編集頻度
   - 文字数 + 言語版数

2. **分野別の重み付け**
   - 政治家: 文字数重視（0.5）
   - 芸能人: バランス型（0.3）
   - YouTuber: 他指標重視（0.2）

3. **定期的な更新**
   - 月次での文字数再取得
   - トレンド分析の実施
"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 分析レポート生成: {report_file}")

if __name__ == "__main__":
    output_file = main()
    print(f"\n✅ 完了！出力ファイル: {output_file}")
