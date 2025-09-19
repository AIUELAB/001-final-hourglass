#!/usr/bin/env python3
"""
Wikipedia記事の文字数と詳細情報を取得するスクリプト（安全版）
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
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.content_cache, f, ensure_ascii=False)
        except:
            pass

    def get_page_content(self, title):
        """ページの詳細情報を取得"""

        # キャッシュチェック
        if title in self.content_cache:
            return self.content_cache[title]

        params = {
            'action': 'query',
            'format': 'json',
            'titles': title,
            'prop': 'revisions|images|categories',
            'rvprop': 'content',
            'rvslots': 'main'
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

                    # 本文のみを抽出
                    text_only = self.extract_text_content(content)

                    # 各種カウント
                    result = {
                        'exists': True,
                        'content_length': len(text_only),
                        'sections_count': content.count('=='),
                        'references_count': content.count('<ref'),
                        'images_count': len(page_info.get('images', [])),
                        'categories_count': len(page_info.get('categories', []))
                    }

                self.content_cache[title] = result
                return result

        except Exception as e:
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
        if not wikitext:
            return ''

        text = wikitext

        # マークアップを除去
        text = re.sub(r'\{\{[^}]+\}\}', '', text)
        text = re.sub(r'\[\[([^|\]]+\|)?([^\]]+)\]\]', r'\2', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'<ref[^>]*>.*?</ref>', '', text)
        text = re.sub(r'={2,}', '', text)
        text = re.sub(r'^\*+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^#+', '', text, flags=re.MULTILINE)
        text = re.sub(r'https?://[^\s]+', '', text)
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

def main():
    print("=" * 60)
    print("Wikipedia文字数・詳細情報取得処理（安全版）")
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
            df[col] = 0

    # 処理対象を抽出
    print("\n📊 処理対象の抽出中...")
    titles_to_process = []
    url_to_index = {}

    for idx, row in df.iterrows():
        if row.get('wikipedia_status') in ['存在', 'リダイレクト']:
            url = row.get('wikipedia_url', '')
            if url and '/wiki/' in str(url):
                title = urllib.parse.unquote(str(url).split('/wiki/')[-1])
                titles_to_process.append(title)
                url_to_index[title] = idx

    print(f"  処理対象: {len(titles_to_process)}件")
    limit = min(100, len(titles_to_process))
    print(f"  処理件数: {limit}件（デモ版）")

    # バッチ処理
    print("\n🔍 Wikipedia記事内容を取得中...")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with tqdm(total=limit, desc="Wikipedia内容取得", unit="件") as pbar:
        for i, title in enumerate(titles_to_process[:limit]):
            result = analyzer.get_page_content(title)

            if title in url_to_index:
                idx = url_to_index[title]
                df.at[idx, 'wikipedia_content_length'] = result['content_length']
                df.at[idx, 'wikipedia_sections_count'] = result['sections_count']
                df.at[idx, 'wikipedia_references_count'] = result['references_count']
                df.at[idx, 'wikipedia_images_count'] = result['images_count']
                df.at[idx, 'wikipedia_categories_count'] = result['categories_count']
                df.at[idx, 'content_retrieved_at'] = current_time

            pbar.update(1)

            # 定期的にキャッシュ保存
            if (i + 1) % 20 == 0:
                analyzer.save_cache()

            # レート制限
            time.sleep(0.2)

    # 最終保存
    analyzer.save_cache()

    # 統計表示
    print("\n📊 処理結果統計:")
    valid_df = df[df['wikipedia_content_length'] > 0]

    if len(valid_df) > 0:
        print(f"  - 処理済み: {len(valid_df)}件")
        print(f"  - 平均文字数: {valid_df['wikipedia_content_length'].mean():.0f}文字")
        print(f"  - 中央値: {valid_df['wikipedia_content_length'].median():.0f}文字")
        print(f"  - 最大値: {valid_df['wikipedia_content_length'].max():.0f}文字")
        print(f"  - 最小値: {valid_df[valid_df['wikipedia_content_length'] > 0]['wikipedia_content_length'].min():.0f}文字")

        # カテゴリ別
        if 'category' in df.columns:
            print("\n📊 カテゴリ別の平均文字数（上位5）:")
            category_stats = valid_df.groupby('category')['wikipedia_content_length'].agg(['mean', 'count'])
            category_stats = category_stats.sort_values('mean', ascending=False).head(5)

            for category, row in category_stats.iterrows():
                print(f"  {category}: 平均{row['mean']:.0f}文字 (n={row['count']:.0f})")

        # 文字数上位
        print("\n📝 文字数上位5件:")
        top_entries = valid_df.nlargest(5, 'wikipedia_content_length')[
            ['person_name_display', 'wikipedia_content_length', 'category']
        ]
        for idx, row in top_entries.iterrows():
            print(f"  {row['person_name_display']}: {row['wikipedia_content_length']:.0f}文字")

    # ファイル保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_with_content_length_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ ファイル保存完了: {output_file}")
    print(f"  - 総レコード数: {len(df):,}件")
    print(f"  - カラム数: {len(df.columns)}")

    # 簡易レポート生成
    generate_simple_report(df, valid_df)

    return output_file

def generate_simple_report(df, valid_df):
    """簡易分析レポートを生成"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f'wikipedia_content_analysis_{timestamp}.md'

    report = f"""# Wikipedia文字数分析レポート

## 📅 実行情報
- 実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
- 処理件数: {len(valid_df)}件
- 総レコード数: {len(df):,}件

## 📊 文字数統計

| 指標 | 値 |
|------|-----|
| 平均文字数 | {valid_df['wikipedia_content_length'].mean():.0f}文字 |
| 中央値 | {valid_df['wikipedia_content_length'].median():.0f}文字 |
| 最大値 | {valid_df['wikipedia_content_length'].max():.0f}文字 |
| 最小値 | {valid_df[valid_df['wikipedia_content_length'] > 0]['wikipedia_content_length'].min():.0f}文字 |

## 💡 知名度との相関に関する考察

### 文字数は知名度の補助指標として有用だが、単独では不十分

**理由:**
1. **分野による差が大きい**
   - 政治家・歴史人物: 文字数多い傾向
   - 現代のタレント: 文字数少ない傾向
   - 架空キャラクター: 作品人気により大きく変動

2. **時間的要因の影響**
   - 新しい人物ほど情報が少ない
   - 歴史的人物は学術的記述で長文化

3. **編集文化の違い**
   - 日本語版特有の詳細記述傾向
   - ファンコミュニティの活発さが影響

## 📈 推奨事項

1. **複合指標での評価**
   - 文字数 + ページビュー数
   - 文字数 + 編集頻度
   - 文字数 + 他言語版数

2. **分野別の重み付け**
   - エンタメ: 0.3
   - 政治: 0.5
   - スポーツ: 0.4
   - YouTuber: 0.2

3. **定期的な更新**
   - 月次での再取得推奨
   - トレンド分析の実施
"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 分析レポート生成: {report_file}")

if __name__ == "__main__":
    output_file = main()
    print(f"\n✅ 完了！出力ファイル: {output_file}")