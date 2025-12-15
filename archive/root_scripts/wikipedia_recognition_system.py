#!/usr/bin/env python3
"""
Wikipedia Recognition System - Phase 2
Wikipedia APIを中心とした客観的な知名度評価システム
レート制限なし、完全無料、高精度
"""

import json
import os
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import wikipediaapi
import pandas as pd
from pytrends.request import TrendReq
import logging
from pathlib import Path

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wikipedia_recognition.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WikipediaRecognitionSystem:
    """Wikipedia APIベースの知名度評価システム"""

    def __init__(self, cache_dir: str = "cache/wikipedia"):
        """
        初期化

        Args:
            cache_dir: キャッシュディレクトリ
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Wikipedia API設定
        self.wiki_wiki = wikipediaapi.Wikipedia(
            language='ja',
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent='WikipediaRecognitionSystem/1.0'
        )
        self.wiki_wiki_en = wikipediaapi.Wikipedia(
            language='en',
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent='WikipediaRecognitionSystem/1.0'
        )

        # Google Trends設定（バックアップ用）
        self.pytrends = TrendReq(hl='ja-JP', tz=540)

        # 統計情報
        self.stats = {
            'total_processed': 0,
            'wikipedia_found': 0,
            'wikipedia_not_found': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'errors': 0,
            'checkpoint_count': 0
        }

        # 品質メトリクス
        self.quality_metrics = {
            'deletion_candidates': [],
            'high_score_persons': [],
            'error_persons': [],
            'average_score': 0,
            'deletion_rate': 0
        }

        # 100人チェックポイント用
        self.checkpoint_interval = 100
        self.last_checkpoint = 0

    def get_cache_key(self, name: str) -> str:
        """キャッシュキーを生成"""
        return hashlib.md5(name.encode('utf-8')).hexdigest()

    def get_cached_data(self, name: str) -> Optional[Dict]:
        """キャッシュからデータを取得"""
        cache_key = self.get_cache_key(name)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            # キャッシュが1週間以内なら使用
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime < timedelta(days=7):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.stats['cache_hits'] += 1
                    return json.load(f)

        return None

    def save_to_cache(self, name: str, data: Dict) -> None:
        """データをキャッシュに保存"""
        cache_key = self.get_cache_key(name)
        cache_file = self.cache_dir / f"{cache_key}.json"

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def search_wikipedia(self, name: str) -> Dict[str, Any]:
        """
        Wikipedia検索を実行

        Args:
            name: 検索する人物名

        Returns:
            Wikipedia情報の辞書
        """
        # キャッシュチェック
        cached = self.get_cached_data(name)
        if cached:
            return cached

        result = {
            'found': False,
            'page_title': None,
            'summary': None,
            'page_length': 0,
            'languages': 0,
            'categories': [],
            'references': 0,
            'images': 0,
            'links': 0,
            'views': 0  # ビュー数は別途取得が必要
        }

        try:
            self.stats['api_calls'] += 1

            # Wikipedia ページを直接取得
            page = self.wiki_wiki.page(name)

            # ページが存在するかチェック
            if not page.exists():
                # 代替検索（スペースをアンダースコアに置換など）
                alt_name = name.replace(' ', '_')
                page = self.wiki_wiki.page(alt_name)

                if not page.exists():
                    self.stats['wikipedia_not_found'] += 1
                    self.save_to_cache(name, result)
                    return result

            # ページ情報を取得
            result['found'] = True
            result['page_title'] = page.title
            result['summary'] = page.summary[:500] if page.summary else ""
            result['page_length'] = len(page.text) if page.text else 0

            # カテゴリ取得
            categories = list(page.categories.keys())[:10]
            result['categories'] = categories

            # リンク数取得
            links = list(page.links.keys())
            result['links'] = len(links)

            # 言語リンク数を取得（多言語版の存在 = 国際的認知度）
            langlinks = page.langlinks
            result['languages'] = len(langlinks)

            # 英語版の存在確認
            if 'en' in langlinks:
                result['languages'] += 1  # 英語版は特に重要

            # セクション数（詳細度の指標）
            sections = page.sections
            result['references'] = len(sections) * 5  # セクション数を参照数の代替指標として使用

            # 画像の存在（簡易チェック）
            result['images'] = 5 if result['page_length'] > 5000 else 2  # ページサイズから推定

            self.stats['wikipedia_found'] += 1

            # キャッシュに保存
            self.save_to_cache(name, result)

        except Exception as e:
            logger.error(f"Wikipedia検索エラー ({name}): {str(e)}")
            self.stats['errors'] += 1
            self.save_to_cache(name, result)

        return result

    def calculate_wikipedia_score(self, wiki_data: Dict) -> float:
        """
        Wikipedia情報から知名度スコアを計算

        Args:
            wiki_data: Wikipedia検索結果

        Returns:
            知名度スコア (0-10)
        """
        if not wiki_data['found']:
            return 0.0

        score = 0.0

        # 1. ページの存在 (基礎点: 3.0)
        score += 3.0

        # 2. ページの長さ (最大2.0点)
        page_length = wiki_data['page_length']
        if page_length > 10000:
            score += 2.0
        elif page_length > 5000:
            score += 1.5
        elif page_length > 2000:
            score += 1.0
        elif page_length > 500:
            score += 0.5

        # 3. 参照数 (最大1.5点)
        references = wiki_data['references']
        if references > 50:
            score += 1.5
        elif references > 20:
            score += 1.0
        elif references > 10:
            score += 0.7
        elif references > 5:
            score += 0.4

        # 4. 多言語版の存在 (最大1.5点)
        if wiki_data['languages'] > 0:
            score += 1.5

        # 5. リンク数 (最大1.0点)
        links = wiki_data['links']
        if links > 100:
            score += 1.0
        elif links > 50:
            score += 0.7
        elif links > 20:
            score += 0.4

        # 6. 画像の存在 (最大1.0点)
        if wiki_data['images'] > 5:
            score += 1.0
        elif wiki_data['images'] > 2:
            score += 0.7
        elif wiki_data['images'] > 0:
            score += 0.4

        return min(score, 10.0)

    def get_google_trends_score(self, name: str) -> float:
        """
        Google Trendsから追加スコアを取得（オプション）

        Args:
            name: 検索する人物名

        Returns:
            トレンドスコア (0-10)
        """
        try:
            # Google Trendsは制限が厳しいので慎重に使用
            self.pytrends.build_payload([name], timeframe='today 12-m', geo='JP')
            interest = self.pytrends.interest_over_time()

            if not interest.empty and name in interest.columns:
                avg_interest = interest[name].mean()
                # 0-100のスコアを0-10に変換
                return min(avg_interest / 10, 10.0)
        except:
            pass

        return 0.0

    def evaluate_person(self, person_data: Dict) -> Dict[str, Any]:
        """
        個人の知名度を評価

        Args:
            person_data: 人物データ

        Returns:
            評価結果
        """
        name = person_data.get('person_name_display', person_data.get('person_name', ''))

        if not name:
            return {
                'person_id': person_data.get('person_id', ''),
                'name': '',
                'recognition_score': 0.0,
                'wikipedia_found': False,
                'should_delete': True,
                'reason': '名前が空'
            }

        # Wikipedia検索
        wiki_data = self.search_wikipedia(name)
        wiki_score = self.calculate_wikipedia_score(wiki_data)

        # 総合スコア計算
        recognition_score = wiki_score

        # 削除判定（スコア3.0未満は削除候補）
        should_delete = recognition_score < 3.0

        # 理由の生成
        if should_delete:
            if not wiki_data['found']:
                reason = "Wikipediaページなし"
            else:
                reason = f"知名度不足 (スコア: {recognition_score:.1f})"
        else:
            reason = f"知名度あり (スコア: {recognition_score:.1f})"

        result = {
            'person_id': person_data.get('person_id', ''),
            'name': name,
            'recognition_score': recognition_score,
            'wikipedia_found': wiki_data['found'],
            'wikipedia_page_length': wiki_data['page_length'],
            'wikipedia_references': wiki_data['references'],
            'wikipedia_languages': wiki_data['languages'],
            'should_delete': should_delete,
            'reason': reason
        }

        # 統計更新
        self.stats['total_processed'] += 1

        if should_delete:
            self.quality_metrics['deletion_candidates'].append(name)
        else:
            self.quality_metrics['high_score_persons'].append({
                'name': name,
                'score': recognition_score
            })

        return result

    def checkpoint_quality_check(self) -> Dict[str, Any]:
        """
        100人ごとの品質チェックポイント

        Returns:
            品質チェック結果
        """
        self.stats['checkpoint_count'] += 1

        # 削除率計算
        if self.stats['total_processed'] > 0:
            deletion_rate = len(self.quality_metrics['deletion_candidates']) / self.stats['total_processed']
        else:
            deletion_rate = 0

        # 平均スコア計算
        if self.quality_metrics['high_score_persons']:
            avg_score = sum(p['score'] for p in self.quality_metrics['high_score_persons']) / len(self.quality_metrics['high_score_persons'])
        else:
            avg_score = 0

        checkpoint = {
            'checkpoint_number': self.stats['checkpoint_count'],
            'total_processed': self.stats['total_processed'],
            'deletion_rate': deletion_rate,
            'average_score': avg_score,
            'wikipedia_found_rate': self.stats['wikipedia_found'] / max(self.stats['total_processed'], 1),
            'cache_hit_rate': self.stats['cache_hits'] / max(self.stats['api_calls'] + self.stats['cache_hits'], 1),
            'timestamp': datetime.now().isoformat()
        }

        # 品質チェック
        quality_issues = []

        # 削除率チェック (10-20%が正常範囲)
        if deletion_rate < 0.1:
            quality_issues.append("削除率が低すぎます（10%未満）")
        elif deletion_rate > 0.2:
            quality_issues.append("削除率が高すぎます（20%超）")

        # Wikipedia発見率チェック
        if checkpoint['wikipedia_found_rate'] < 0.3:
            quality_issues.append("Wikipedia発見率が低すぎます（30%未満）")

        checkpoint['quality_issues'] = quality_issues
        checkpoint['quality_ok'] = len(quality_issues) == 0

        # ログ出力
        logger.info(f"=== チェックポイント {self.stats['checkpoint_count']} ===")
        logger.info(f"処理済み: {self.stats['total_processed']}人")
        logger.info(f"削除率: {deletion_rate:.1%}")
        logger.info(f"平均スコア: {avg_score:.2f}")
        logger.info(f"Wikipedia発見率: {checkpoint['wikipedia_found_rate']:.1%}")

        if quality_issues:
            logger.warning(f"品質問題: {', '.join(quality_issues)}")
        else:
            logger.info("✅ 品質チェック合格")

        return checkpoint

    def process_batch(self, persons: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        バッチ処理

        Args:
            persons: 人物データのリスト

        Returns:
            (評価結果リスト, 統計情報)
        """
        results = []
        checkpoints = []

        for i, person in enumerate(persons):
            # 評価実行
            result = self.evaluate_person(person)
            results.append(result)

            # 進捗表示
            if (i + 1) % 10 == 0:
                logger.info(f"進捗: {i + 1}/{len(persons)} ({(i + 1) / len(persons) * 100:.1f}%)")

            # 100人ごとのチェックポイント
            if self.stats['total_processed'] % self.checkpoint_interval == 0 and self.stats['total_processed'] > 0:
                checkpoint = self.checkpoint_quality_check()
                checkpoints.append(checkpoint)

                # 品質問題があれば警告（ただし続行）
                if not checkpoint['quality_ok']:
                    logger.warning("品質問題が検出されましたが、処理を続行します")

            # API制限回避のための小休止（Wikipedia APIは寛容だが念のため）
            if (i + 1) % 50 == 0:
                time.sleep(1)

        # 最終統計
        final_stats = {
            'total_processed': self.stats['total_processed'],
            'wikipedia_found': self.stats['wikipedia_found'],
            'wikipedia_not_found': self.stats['wikipedia_not_found'],
            'deletion_count': len(self.quality_metrics['deletion_candidates']),
            'deletion_rate': len(self.quality_metrics['deletion_candidates']) / max(self.stats['total_processed'], 1),
            'cache_hits': self.stats['cache_hits'],
            'api_calls': self.stats['api_calls'],
            'errors': self.stats['errors'],
            'checkpoints': checkpoints
        }

        return results, final_stats


def main():
    """メイン処理"""
    print("=" * 60)
    print("Wikipedia Recognition System")
    print("客観的な知名度評価システム")
    print("=" * 60)
    print()

    # CSVファイルを検索
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        logger.error("ultra_think_*.csv ファイルが見つかりません")
        return

    # 最新のファイルを選択
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"処理対象ファイル: {latest_file}")

    # データ読み込み
    try:
        df = pd.read_csv(latest_file, encoding='utf-8-sig')
        logger.info(f"データ読み込み完了: {len(df)}件")
    except Exception as e:
        logger.error(f"CSVファイル読み込みエラー: {str(e)}")
        return

    # 必須フィールドチェック
    required_fields = ['person_name', 'person_name_display']
    missing_fields = [f for f in required_fields if f not in df.columns]
    if missing_fields:
        logger.error(f"必須フィールドが不足: {missing_fields}")
        return

    # システム初期化
    system = WikipediaRecognitionSystem()

    # テスト実行（最初の10人で動作確認）
    logger.info("=" * 40)
    logger.info("テスト実行（最初の10人）")
    logger.info("=" * 40)

    test_persons = df.head(10).to_dict('records')
    test_results, test_stats = system.process_batch(test_persons)

    # テスト結果表示
    logger.info("\n=== テスト結果 ===")
    for result in test_results:
        status = "削除" if result['should_delete'] else "保持"
        logger.info(f"{result['name']}: スコア={result['recognition_score']:.1f} -> {status}")

    logger.info(f"\n削除率: {test_stats['deletion_rate']:.1%}")

    # ユーザー確認
    print("\n" + "=" * 40)
    print("テスト実行が完了しました")
    print(f"削除率: {test_stats['deletion_rate']:.1%}")
    print("全4,701件の処理を開始しますか？")
    print("予想処理時間: 約2-3時間（API制限なし）")
    print("=" * 40)

    # 統計情報を保存
    stats_file = f"wikipedia_recognition_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(test_stats, f, ensure_ascii=False, indent=2)

    logger.info(f"統計情報を保存: {stats_file}")


if __name__ == "__main__":
    main()
