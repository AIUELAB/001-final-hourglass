#!/usr/bin/env python3
"""
Wikipedia全件存在確認とスコア0設定
person_name + occupation + nationalityで検索し、
Wikipedia未掲載者はname_recognition = 0に設定
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import requests
import time
import logging
from pathlib import Path
import shutil

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'wikipedia_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WikipediaValidator:
    """Wikipedia存在確認クラス"""

    def __init__(self):
        self.base_url = "https://ja.wikipedia.org/w/api.php"
        self.cache = {}  # 検索結果のキャッシュ
        self.stats = {
            'total': 0,
            'found': 0,
            'not_found': 0,
            'errors': 0,
            'score_zero': 0
        }

        # 既知の有名人（テスト用）
        self.known_persons = {
            'HIKAKIN': True,
            '米津玄師': True,
            '大谷翔平': True,
            'リーチマイケル': True,
            '香川真司': True
        }

    def search_wikipedia(self, person_name, occupation=None, nationality=None):
        """Wikipedia検索"""
        # キャッシュチェック
        cache_key = f"{person_name}|{occupation}|{nationality}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # 検索クエリの構築（複数パターン）
            queries = []

            # パターン1: フルコンテキスト検索
            if occupation and nationality and str(nationality) != 'nan':
                queries.append(f"{person_name} {occupation} {nationality}")

            # パターン2: 名前＋職業
            if occupation and str(occupation) != 'nan':
                queries.append(f"{person_name} {occupation}")

            # パターン3: 名前のみ
            queries.append(person_name)

            # 各パターンで検索
            for query in queries:
                params = {
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': query,
                    'srlimit': 5,
                    'srprop': 'snippet|titlesnippet'
                }

                response = requests.get(self.base_url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('query', {}).get('search', [])

                    # 結果の確認
                    for result in results:
                        title = result.get('title', '')
                        snippet = result.get('snippet', '')

                        # 人名が含まれているか確認
                        name_parts = person_name.replace(' ', '')
                        if (person_name in title or
                            name_parts in title or
                            person_name in snippet):
                            self.cache[cache_key] = True
                            return True

                time.sleep(0.1)  # API制限対策

            # 見つからない場合
            self.cache[cache_key] = False
            return False

        except Exception as e:
            logger.warning(f"Wikipedia検索エラー: {person_name} - {e}")
            return None

    def validate_person(self, row):
        """個人の検証"""
        person_id = row['person_id']
        person_name = row['person_name']
        occupation = row.get('occupation', '')
        nationality = row.get('nationality', '')
        current_score = row['name_recognition']

        # 既知の有名人チェック
        if person_name in self.known_persons:
            return current_score  # スコア維持

        # Wikipedia検索
        exists = self.search_wikipedia(person_name, occupation, nationality)

        if exists is True:
            self.stats['found'] += 1
            return current_score  # スコア維持
        elif exists is False:
            self.stats['not_found'] += 1
            self.stats['score_zero'] += 1
            logger.info(f"  ❌ {person_id}: {person_name} ({occupation}) → スコア0")
            return 0.0  # スコアを0に設定
        else:
            self.stats['errors'] += 1
            return current_score  # エラー時は維持

    def process_database(self, df):
        """データベース全体の処理"""
        logger.info("=" * 60)
        logger.info("📊 Wikipedia全件確認開始")
        logger.info("=" * 60)

        self.stats['total'] = len(df)

        # プログレスバー風の表示
        batch_size = 100
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]

            for idx, row in batch.iterrows():
                new_score = self.validate_person(row)
                df.at[idx, 'name_recognition'] = new_score

            # 進捗表示
            progress = min((i + batch_size) / len(df) * 100, 100)
            logger.info(f"進捗: {progress:.1f}% ({min(i+batch_size, len(df))}/{len(df)})")

            # 中間統計
            if (i + batch_size) % 500 == 0:
                logger.info(f"  見つかった: {self.stats['found']}件")
                logger.info(f"  見つからない: {self.stats['not_found']}件")
                logger.info(f"  スコア0設定: {self.stats['score_zero']}件")

        return df

    def generate_report(self):
        """検証レポート生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.stats,
            'accuracy_rate': (self.stats['found'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0,
            'placeholder_rate': (self.stats['not_found'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0,
            'error_rate': (self.stats['errors'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        }

        report_file = f"wikipedia_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"📝 レポート保存: {report_file}")
        return report


def backup_database(csv_file):
    """データベースのバックアップ"""
    backup_file = f"backup_{csv_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(csv_file, backup_file)
    logger.info(f"💾 バックアップ作成: {backup_file}")
    return backup_file


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 Wikipedia全件存在確認開始")
    logger.info("=" * 60)

    # データ読み込み
    csv_file = "ultra_think_CLEANED_20250911_192323.csv"
    logger.info(f"📂 データ読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    original_count = len(df)
    logger.info(f"📊 総レコード数: {original_count}件")

    # バックアップ作成
    backup_file = backup_database(csv_file)

    # Wikipedia検証
    validator = WikipediaValidator()
    df = validator.process_database(df)

    # スコア0のレコードを除外（オプション）
    score_zero = df[df['name_recognition'] == 0]
    logger.info(f"\n📊 スコア0設定: {len(score_zero)}件")

    # サンプル表示
    if len(score_zero) > 0:
        logger.info("\nスコア0の例（最初の10件）:")
        for _, row in score_zero.head(10).iterrows():
            logger.info(f"  {row['person_id']}: {row['person_name']} ({row['occupation']})")

    # 修正後のデータ保存
    output_file = f"ultra_think_WIKIPEDIA_VALIDATED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"💾 検証済みデータ保存: {output_file}")

    # レポート生成
    report = validator.generate_report()

    # 最終サマリー
    logger.info("=" * 60)
    logger.info("📊 Wikipedia検証完了")
    logger.info("=" * 60)
    logger.info(f"  総検証数: {validator.stats['total']}件")
    logger.info(f"  Wikipedia掲載: {validator.stats['found']}件 ({validator.stats['found']/validator.stats['total']*100:.1f}%)")
    logger.info(f"  Wikipedia未掲載: {validator.stats['not_found']}件 ({validator.stats['not_found']/validator.stats['total']*100:.1f}%)")
    logger.info(f"  スコア0設定: {validator.stats['score_zero']}件")
    logger.info(f"  エラー: {validator.stats['errors']}件")

    return output_file, report


if __name__ == "__main__":
    # テストモード（最初の100件のみ）
    import sys
    if '--test' in sys.argv:
        logger.info("⚠️ テストモード: 最初の100件のみ処理")
        df = pd.read_csv("ultra_think_CLEANED_20250911_192323.csv").head(100)
        validator = WikipediaValidator()
        df = validator.process_database(df)
        df.to_csv("test_wikipedia_validation.csv", index=False, encoding='utf-8-sig')
        print("\n✅ テスト完了")
    else:
        output_file, report = main()
        print(f"\n✅ 処理完了")
        print(f"📁 出力ファイル: {output_file}")
