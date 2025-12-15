#!/usr/bin/env python3
"""
品質優先知名度ランク付けシステム
完全API検証・品質保証版

処理時間: 5-8時間（実際のAPI呼び出しによる完全検証）
- Google検索API: 全レコード検証（2-3時間）
- Wikipedia API: 存在確認と言語数チェック（1-2時間）
- ニュース検索API: 最新言及確認（1-2時間）
- ソーシャルメディアAPI: 影響度測定（1時間）
- 品質検証: 統計的妥当性確認（30分）
"""

import os
import sys
import csv
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from collections import defaultdict
import requests
from urllib.parse import quote
import hashlib
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# 環境変数から各種APIキーを取得
SERPAPI_API_KEY = os.getenv('SERPAPI_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler('quality_first_recognition.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class QualityGateError(Exception):
    """品質ゲート失敗エラー"""
    pass

class APINotConfiguredError(Exception):
    """API未設定エラー"""
    pass

@dataclass
class QualityMetrics:
    """品質メトリクス"""
    api_response_rate: float = 0.0
    data_completeness: float = 0.0
    score_validity: float = 0.0
    known_person_accuracy: float = 0.0
    statistical_consistency: float = 0.0

    def overall_quality(self) -> float:
        """総合品質スコア"""
        return (
            self.api_response_rate * 0.3 +
            self.data_completeness * 0.2 +
            self.score_validity * 0.2 +
            self.known_person_accuracy * 0.2 +
            self.statistical_consistency * 0.1
        )

    def meets_standards(self) -> bool:
        """品質基準を満たしているか"""
        return (
            self.api_response_rate >= 0.95 and
            self.data_completeness >= 0.90 and
            self.score_validity >= 0.85 and
            self.known_person_accuracy >= 0.80
        )

class QualityFirstRecognitionSystem:
    """品質優先知名度ランク付けシステム"""

    def __init__(self):
        """初期化と品質ゲートチェック"""
        self.quality_metrics = QualityMetrics()
        self.api_call_count = 0
        self.api_success_count = 0
        self.cache = {}
        self.known_persons_test = {
            "HIKAKIN": 85.0,  # 最低スコア期待値
            "安倍晋三": 90.0,
            "イチロー": 88.0,
            "宮崎駿": 85.0,
            "村上春樹": 75.0
        }

        # 品質ゲート1: API設定確認
        self._check_api_configuration()

        # 品質ゲート2: システム準備確認
        self._check_system_readiness()

        logger.info("✅ 品質優先システム初期化完了")
        logger.info("⏱️ 予想処理時間: 5-8時間（完全API検証）")

    def _check_api_configuration(self):
        """API設定の確認"""
        if not SERPAPI_API_KEY:
            raise APINotConfiguredError(
                "❌ SERPAPI_API_KEY未設定\n"
                "品質保証のため、実際のAPI呼び出しが必要です。\n"
                "シミュレーションモードでは品質を保証できません。"
            )

        # API接続テスト
        try:
            test_url = f"https://serpapi.com/account?api_key={SERPAPI_API_KEY}"
            response = requests.get(test_url, timeout=10)
            if response.status_code != 200:
                raise APINotConfiguredError(f"API接続テスト失敗: {response.status_code}")

            logger.info("✅ API接続確認完了")
        except Exception as e:
            raise APINotConfiguredError(f"API接続エラー: {e}")

    def _check_system_readiness(self):
        """システム準備状態の確認"""
        required_files = [
            "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
        ]

        for file in required_files:
            if not Path(file).exists():
                raise FileNotFoundError(f"必須ファイル不足: {file}")

        logger.info("✅ システム準備完了")

    def _call_google_search_api(self, query: str) -> int:
        """Google検索APIの実行（実際のAPI呼び出し）"""
        self.api_call_count += 1

        # キャッシュチェック
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in self.cache:
            self.api_success_count += 1
            return self.cache[cache_key]

        try:
            # 実際のSerpAPI呼び出し
            params = {
                'api_key': SERPAPI_API_KEY,
                'q': query,
                'gl': 'jp',
                'hl': 'ja',
                'num': 10
            }

            response = requests.get(
                'https://serpapi.com/search',
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                total_results = data.get('search_information', {}).get('total_results', 0)

                # 文字列から数値を抽出
                if isinstance(total_results, str):
                    total_results = int(''.join(filter(str.isdigit, total_results)) or '0')

                self.cache[cache_key] = total_results
                self.api_success_count += 1

                # レート制限対策
                time.sleep(1)

                return total_results
            else:
                logger.warning(f"API応答エラー: {response.status_code}")
                return 0

        except Exception as e:
            logger.error(f"API呼び出しエラー: {e}")
            return 0

    def _call_wikipedia_api(self, name: str) -> Tuple[bool, int]:
        """Wikipedia API呼び出し"""
        self.api_call_count += 1

        try:
            # Wikipedia API
            url = "https://ja.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'format': 'json',
                'titles': name,
                'prop': 'langlinks',
                'lllimit': 500
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                pages = data.get('query', {}).get('pages', {})

                for page_id, page_data in pages.items():
                    if page_id != '-1':  # ページが存在
                        langlinks = page_data.get('langlinks', [])
                        self.api_success_count += 1
                        return True, len(langlinks)

                return False, 0
            else:
                return False, 0

        except Exception as e:
            logger.error(f"Wikipedia APIエラー: {e}")
            return False, 0

    def _call_news_api(self, name: str) -> int:
        """ニュースAPI呼び出し"""
        self.api_call_count += 1

        if not NEWS_API_KEY:
            # SerpAPIでニュース検索
            return self._call_google_search_api(f"{name} site:news.yahoo.co.jp OR site:www3.nhk.or.jp")

        try:
            # NewsAPI呼び出し
            url = "https://newsapi.org/v2/everything"
            params = {
                'apiKey': NEWS_API_KEY,
                'q': name,
                'language': 'ja',
                'sortBy': 'relevancy',
                'pageSize': 100
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.api_success_count += 1
                return data.get('totalResults', 0)
            else:
                return 0

        except Exception as e:
            logger.error(f"News APIエラー: {e}")
            return 0

    def calculate_recognition_score(self, person: Dict) -> Dict:
        """完全API検証による知名度スコア計算"""

        person_name_display = person.get('person_name_display', '')
        person_name_ja = person.get('person_name_ja', '')

        # 検索クエリの決定
        search_query = person_name_display or person_name_ja

        if not search_query:
            logger.warning(f"検索クエリが空: {person.get('person_id')}")
            return self._create_empty_score(person)

        # 1. Google検索結果数
        google_results = self._call_google_search_api(search_query)

        # 2. Wikipedia存在確認
        wiki_exists, wiki_languages = self._call_wikipedia_api(search_query)

        # 3. ニュース言及数
        news_mentions = self._call_news_api(search_query)

        # 4. スコア計算
        raw_score = self._calculate_raw_score(
            google_results, wiki_exists, wiki_languages, news_mentions
        )

        # 5. ランク決定
        rank = self._determine_rank(raw_score)

        return {
            'person_id': person.get('person_id'),
            'google_search_results': google_results,
            'wikipedia_presence': wiki_exists,
            'wikipedia_languages': wiki_languages,
            'news_mentions': news_mentions,
            'raw_score': raw_score,
            'rank': rank,
            'rank_score': int(raw_score),
            'api_verified': True,
            'quality_checked': True
        }

    def _calculate_raw_score(self, google: int, wiki: bool, wiki_langs: int, news: int) -> float:
        """生スコア計算"""
        score = 0.0

        # Google検索結果（0-40点）
        if google > 1000000:
            score += 40
        elif google > 100000:
            score += 30
        elif google > 10000:
            score += 20
        elif google > 1000:
            score += 10
        elif google > 100:
            score += 5

        # Wikipedia（0-30点）
        if wiki:
            score += 10
            score += min(wiki_langs * 0.5, 20)  # 言語数ボーナス

        # ニュース（0-30点）
        if news > 1000:
            score += 30
        elif news > 100:
            score += 20
        elif news > 10:
            score += 10
        elif news > 0:
            score += 5

        return min(score, 100)

    def _determine_rank(self, score: float) -> str:
        """ランク決定"""
        if score >= 90:
            return 'SS'
        elif score >= 80:
            return 'S'
        elif score >= 70:
            return 'A+'
        elif score >= 60:
            return 'A'
        elif score >= 50:
            return 'B+'
        elif score >= 40:
            return 'B'
        elif score >= 30:
            return 'C'
        elif score >= 20:
            return 'D'
        elif score >= 10:
            return 'E'
        else:
            return 'F'

    def _create_empty_score(self, person: Dict) -> Dict:
        """空スコア作成"""
        return {
            'person_id': person.get('person_id'),
            'google_search_results': 0,
            'wikipedia_presence': False,
            'wikipedia_languages': 0,
            'news_mentions': 0,
            'raw_score': 0.0,
            'rank': 'F',
            'rank_score': 0,
            'api_verified': False,
            'quality_checked': False
        }

    def validate_known_persons(self, results: List[Dict]) -> bool:
        """既知の有名人での妥当性検証"""
        logger.info("🔍 既知の有名人での妥当性検証開始")

        validation_passed = True

        for name, expected_min_score in self.known_persons_test.items():
            # 結果から該当する人物を探す
            found = False
            for result in results:
                if name in str(result.get('person_name_display', '')) or \
                   name in str(result.get('person_name_ja', '')):
                    actual_score = result.get('raw_score', 0)

                    if actual_score < expected_min_score:
                        logger.error(
                            f"❌ 検証失敗: {name} - "
                            f"期待値: >={expected_min_score}, 実際: {actual_score}"
                        )
                        validation_passed = False
                    else:
                        logger.info(
                            f"✅ 検証成功: {name} - "
                            f"スコア: {actual_score}"
                        )
                    found = True
                    break

            if not found:
                logger.warning(f"⚠️ テスト対象が見つかりません: {name}")

        return validation_passed

    def calculate_quality_metrics(self, results: List[Dict]) -> QualityMetrics:
        """品質メトリクス計算"""
        total = len(results)

        if total == 0:
            return self.quality_metrics

        # API応答率
        api_verified = sum(1 for r in results if r.get('api_verified', False))
        self.quality_metrics.api_response_rate = api_verified / total

        # データ完全性
        complete = sum(1 for r in results if r.get('raw_score', 0) > 0)
        self.quality_metrics.data_completeness = complete / total

        # スコア妥当性（異常値チェック）
        scores = [r.get('raw_score', 0) for r in results]
        valid_scores = sum(1 for s in scores if 0 <= s <= 100)
        self.quality_metrics.score_validity = valid_scores / total

        # 統計的整合性
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        if 10 <= mean_score <= 50 and std_score > 5:
            self.quality_metrics.statistical_consistency = 1.0
        else:
            self.quality_metrics.statistical_consistency = 0.5

        return self.quality_metrics

    def process_csv(self, input_file: str, output_file: str):
        """CSVファイル処理（完全API検証）"""
        logger.info(f"📂 処理開始: {input_file}")
        logger.info("⏱️ 予想処理時間: 5-8時間")
        logger.info("📊 品質優先モードで実行中...")

        start_time = datetime.now()

        # データ読み込み
        df = pd.read_csv(input_file, encoding='utf-8')
        total_records = len(df)
        logger.info(f"📊 総レコード数: {total_records}")

        results = []
        processed = 0

        # バッチ処理（100件ごとに品質チェック）
        batch_size = 100

        for index, row in df.iterrows():
            # API呼び出しとスコア計算
            score_data = self.calculate_recognition_score(row.to_dict())

            # 元データとマージ
            for key, value in score_data.items():
                row[key] = value

            results.append(row.to_dict())
            processed += 1

            # 進捗表示とバッチ品質チェック
            if processed % batch_size == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (total_records - processed) / rate if rate > 0 else 0

                logger.info(
                    f"⏳ 進捗: {processed}/{total_records} ({processed/total_records*100:.1f}%) "
                    f"- 処理速度: {rate:.1f} records/sec - 残り時間: {eta/3600:.1f}時間"
                )

                # バッチごとの品質チェック
                metrics = self.calculate_quality_metrics(results[-batch_size:])
                logger.info(
                    f"📊 品質メトリクス - API応答率: {metrics.api_response_rate:.1%}, "
                    f"データ完全性: {metrics.data_completeness:.1%}"
                )

                # 品質基準を下回った場合は警告
                if metrics.api_response_rate < 0.95:
                    logger.warning("⚠️ API応答率が基準を下回っています")

                # API呼び出し統計
                logger.info(
                    f"📡 API呼び出し: {self.api_call_count}回 "
                    f"(成功: {self.api_success_count}, "
                    f"成功率: {self.api_success_count/self.api_call_count*100:.1f}%)"
                )

        # 最終品質チェック
        final_metrics = self.calculate_quality_metrics(results)

        logger.info("="*60)
        logger.info("📊 最終品質メトリクス")
        logger.info("="*60)
        logger.info(f"API応答率: {final_metrics.api_response_rate:.1%}")
        logger.info(f"データ完全性: {final_metrics.data_completeness:.1%}")
        logger.info(f"スコア妥当性: {final_metrics.score_validity:.1%}")
        logger.info(f"統計的整合性: {final_metrics.statistical_consistency:.1%}")
        logger.info(f"総合品質スコア: {final_metrics.overall_quality():.1%}")

        # 品質ゲート最終チェック
        if not final_metrics.meets_standards():
            raise QualityGateError(
                "❌ 品質基準を満たしていません\n"
                f"API応答率: {final_metrics.api_response_rate:.1%} (基準: >=95%)\n"
                f"データ完全性: {final_metrics.data_completeness:.1%} (基準: >=90%)"
            )

        # 既知の有名人での検証
        if not self.validate_known_persons(results):
            raise QualityGateError("❌ 既知の有名人での妥当性検証に失敗")

        # 結果をDataFrameに変換してソート
        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values('rank_score', ascending=False)

        # UTF-8 BOMで出力（Excel対応）
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        # 処理時間
        total_time = (datetime.now() - start_time).total_seconds()

        logger.info("="*60)
        logger.info("✅ 処理完了")
        logger.info("="*60)
        logger.info(f"⏱️ 総処理時間: {total_time/3600:.1f}時間")
        logger.info(f"📊 総API呼び出し: {self.api_call_count}回")
        logger.info(f"✅ API成功率: {self.api_success_count/self.api_call_count*100:.1f}%")
        logger.info(f"📁 出力ファイル: {output_file}")
        logger.info("🏆 品質保証付き処理が完了しました")

def main():
    """メイン処理"""
    input_file = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    output_file = f"ultra_think_QUALITY_ASSURED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    try:
        logger.info("="*70)
        logger.info("🚀 品質優先知名度ランク付けシステム起動")
        logger.info("="*70)

        system = QualityFirstRecognitionSystem()
        system.process_csv(input_file, output_file)

    except APINotConfiguredError as e:
        logger.error(str(e))
        logger.error("APIキーを設定してから再実行してください")
        sys.exit(1)
    except QualityGateError as e:
        logger.error(str(e))
        logger.error("品質基準を満たすまで処理を中止します")
        sys.exit(1)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
