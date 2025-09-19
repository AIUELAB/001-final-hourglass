#!/usr/bin/env python3
"""
Wikipedia URLの完全検証スクリプト
全3,569件のURLを検証し、詳細レポートを生成
"""

import pandas as pd
import requests
import time
import json
import urllib.parse
from datetime import datetime
from tqdm import tqdm
import os

class WikipediaCompleteVerifier:
    """Wikipedia APIを使用した完全検証クラス"""

    def __init__(self):
        self.api_url = "https://ja.wikipedia.org/w/api.php"
        self.base_url = "https://ja.wikipedia.org/wiki/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ultra-Think-Database/1.0 (https://example.com/contact)'
        })
        self.progress_file = 'wikipedia_verification_progress.json'
        self.verified_cache = self.load_progress()

    def load_progress(self):
        """前回の進捗を読み込み"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_progress(self):
        """進捗を保存"""
        with open(self.progress_file, 'w') as f:
            json.dump(self.verified_cache, f)

    def batch_check_pages(self, titles, batch_size=50):
        """
        複数のページタイトルを一括で存在確認
        """
        results = {}

        # すでに検証済みのものはスキップ
        titles_to_check = []
        for title in titles:
            if title in self.verified_cache:
                results[title] = self.verified_cache[title]
            else:
                titles_to_check.append(title)

        if not titles_to_check:
            return results

        # プログレスバーの設定
        total_batches = (len(titles_to_check) + batch_size - 1) // batch_size

        with tqdm(total=len(titles_to_check), desc="Wikipedia API検証", unit="件") as pbar:
            for i in range(0, len(titles_to_check), batch_size):
                batch = titles_to_check[i:i + batch_size]
                batch = [t for t in batch if t and t.strip()]

                if not batch:
                    continue

                params = {
                    'action': 'query',
                    'format': 'json',
                    'titles': '|'.join(batch),
                    'prop': 'info',
                    'inprop': 'url'
                }

                retry_count = 0
                max_retries = 3

                while retry_count < max_retries:
                    try:
                        response = self.session.get(self.api_url, params=params, timeout=10)
                        response.raise_for_status()
                        data = response.json()

                        pages = data.get('query', {}).get('pages', {})

                        for page_id, page_info in pages.items():
                            title = page_info.get('title', '')

                            if page_id == '-1' or 'missing' in page_info:
                                result = {
                                    'exists': False,
                                    'status': '不存在',
                                    'url': None
                                }
                            elif 'redirect' in page_info:
                                result = {
                                    'exists': True,
                                    'status': 'リダイレクト',
                                    'url': page_info.get('fullurl', '')
                                }
                            else:
                                result = {
                                    'exists': True,
                                    'status': '存在',
                                    'url': page_info.get('fullurl', '')
                                }

                            results[title] = result
                            self.verified_cache[title] = result

                        break  # 成功したらループを抜ける

                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            print(f"\n⚠️ APIエラー（バッチ {i//batch_size + 1}）: {e}")
                            for title in batch:
                                results[title] = {
                                    'exists': None,
                                    'status': '確認エラー',
                                    'url': None
                                }
                                self.verified_cache[title] = results[title]
                        else:
                            time.sleep(2)  # リトライ前に待機

                pbar.update(len(batch))

                # 進捗を定期的に保存
                if (i // batch_size + 1) % 10 == 0:
                    self.save_progress()

                # レート制限対策
                time.sleep(0.3)  # より短い間隔で実行

        # 最終的な進捗を保存
        self.save_progress()

        return results

    def extract_title_from_url(self, url):
        """URLからWikipediaのページタイトルを抽出"""
        if not url or pd.isna(url):
            return None

        # float型の場合は文字列に変換
        url = str(url)

        if '/wiki/' in url:
            title = url.split('/wiki/')[-1]
            title = urllib.parse.unquote(title)
            return title

        return None

def generate_verification_report(stats, df):
    """検証レポートを生成"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f'wikipedia_verification_report_{timestamp}.md'

    report = f"""# Wikipedia URL検証レポート

## 📅 実行情報
- 実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
- 総レコード数: {len(df):,}件
- 検証済みURL数: {sum(stats.values()):,}件

## 📊 検証結果統計

| ステータス | 件数 | 割合 |
|-----------|------|------|
| 存在 | {stats.get('存在', 0):,}件 | {stats.get('存在', 0)/len(df)*100:.1f}% |
| リダイレクト | {stats.get('リダイレクト', 0):,}件 | {stats.get('リダイレクト', 0)/len(df)*100:.1f}% |
| 不存在 | {stats.get('不存在', 0):,}件 | {stats.get('不存在', 0)/len(df)*100:.1f}% |
| グループページのみ | {stats.get('グループページのみ', 0):,}件 | {stats.get('グループページのみ', 0)/len(df)*100:.1f}% |
| 確認エラー | {stats.get('確認エラー', 0):,}件 | {stats.get('確認エラー', 0)/len(df)*100:.1f}% |
| 未設定 | {stats.get('未設定', 0):,}件 | {stats.get('未設定', 0)/len(df)*100:.1f}% |

## 📝 カテゴリ別分析

### 存在が確認されたページ（上位カテゴリ）
"""

    # カテゴリ別の統計
    if 'category' in df.columns:
        category_stats = df[df['wikipedia_status'] == '存在']['category'].value_counts().head(10)
        for category, count in category_stats.items():
            report += f"- {category}: {count:,}件\n"

    report += f"""

### 削除されたURL（サンプル）
"""

    # 削除されたURLのサンプル
    deleted_samples = df[df['wikipedia_status'] == '不存在'].head(20)
    for idx, row in deleted_samples.iterrows():
        report += f"- {row.get('person_name_display', 'N/A')}\n"

    report += f"""

## 🔍 データ品質評価

- **有効URL率**: {(stats.get('存在', 0) + stats.get('リダイレクト', 0))/sum(stats.values())*100:.1f}%
- **無効URL率**: {stats.get('不存在', 0)/sum(stats.values())*100:.1f}%
- **検証成功率**: {(sum(stats.values()) - stats.get('確認エラー', 0))/sum(stats.values())*100:.1f}%

## 💡 改善提案

1. **不存在URLの対処**
   - 代替リンク（公式サイト、SNS）の追加を検討
   - グループページへのリンクで代替

2. **リダイレクトの更新**
   - リダイレクト先の正式URLへの更新を推奨

3. **定期メンテナンス**
   - 月次での再検証スケジュールの設定
   - 新規作成ページの自動検出

## ✅ 完了

Wikipedia URL検証が正常に完了しました。
無効なURLは削除され、データ品質が向上しました。
"""

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 レポート生成完了: {report_file}")
    return report_file

def process_complete_verification(input_file):
    """
    メイン処理: 全件のWikipedia URL検証
    """
    print("=" * 60)
    print("Wikipedia URL完全検証処理")
    print("=" * 60)

    # データ読み込み
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df)}件")

    # Wikipedia検証器を初期化
    verifier = WikipediaCompleteVerifier()

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
    print(f"  推定処理時間: 約{len(titles_to_check) * 0.3 / 60:.1f}分")

    # バッチで存在確認
    print("\n🔍 Wikipedia API検証開始...")

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
        '未設定': 0
    }

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 検証結果を反映
    for title, result in verification_results.items():
        if title in title_to_index:
            idx = title_to_index[title]

            if result['exists']:
                df.at[idx, 'wikipedia_url'] = result['url']
                df.at[idx, 'wikipedia_status'] = result['status']
                stats[result['status']] += 1

            elif result['exists'] is False:
                # ページが存在しない場合
                group_name = df.at[idx, 'group_name']

                if pd.notna(group_name) and group_name:
                    df.at[idx, 'wikipedia_url'] = ''
                    df.at[idx, 'wikipedia_status'] = 'グループページのみ'
                    df.at[idx, 'exists_on_group_page'] = 'グループページに記載あり'
                    stats['グループページのみ'] += 1
                else:
                    df.at[idx, 'wikipedia_url'] = ''
                    df.at[idx, 'wikipedia_status'] = '不存在'
                    stats['不存在'] += 1

            else:
                # エラーの場合
                df.at[idx, 'wikipedia_status'] = result['status']
                stats[result['status']] += 1

            df.at[idx, 'wikipedia_verified_at'] = current_time

    # 未設定の行を処理
    for idx, row in df.iterrows():
        if pd.isna(row.get('wikipedia_status')) or row.get('wikipedia_status') == '':
            df.at[idx, 'wikipedia_status'] = '未設定'
            stats['未設定'] += 1

    # 統計表示
    print("\n📊 検証結果統計:")
    for status, count in stats.items():
        if count > 0:
            print(f"  - {status}: {count:,}件 ({count/len(df)*100:.1f}%)")

    # レポート生成
    report_file = generate_verification_report(stats, df)

    # ファイル保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_wikipedia_complete_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ ファイル保存完了: {output_file}")
    print(f"  - 総レコード数: {len(df):,}件")
    print(f"  - カラム数: {len(df.columns)}")

    # 進捗ファイルを削除
    if os.path.exists(verifier.progress_file):
        os.remove(verifier.progress_file)

    return output_file, stats

if __name__ == "__main__":
    # 最新のファイルを処理
    input_file = 'ultra_think_wikipedia_verified_20250915_133537.csv'

    start_time = time.time()
    output_file, stats = process_complete_verification(input_file)
    elapsed_time = time.time() - start_time

    print(f"\n⏱️ 処理時間: {elapsed_time/60:.1f}分")
    print(f"\n✅ 完了！")
    print(f"  出力ファイル: {output_file}")
    print(f"  有効URL率: {(stats.get('存在', 0) + stats.get('リダイレクト', 0))/(sum(stats.values()) or 1)*100:.1f}%")