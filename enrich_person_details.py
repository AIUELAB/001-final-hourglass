#!/usr/bin/env python3
"""
人物の詳細情報を充実させるスクリプト
occupation, description, categoryを適切に設定
"""

import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

sys.path.append(str(Path(__file__).parent))
from multi_api_recognition_system import MultiAPIRecognitionSystem
from wikipedia_recognition_system_v2 import WikipediaRecognitionSystemV2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API制限解除設定を読み込み
try:
    with open('api_unlimited_config.json', 'r') as f:
        config = json.load(f)
except:
    config = {"api_settings": {"max_parallel": 10}}

class PersonDetailsEnricher:
    """人物詳細情報充実クラス"""

    def __init__(self, database_file: str):
        """初期化"""
        self.database_file = database_file
        self.df = pd.read_csv(database_file, encoding='utf-8-sig')
        self.multi_api = MultiAPIRecognitionSystem()
        self.wiki_system = WikipediaRecognitionSystemV2()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.enriched = 0
        self.max_workers = min(10, config.get('api_settings', {}).get('max_parallel', 10))

        # カテゴリと職業のマッピング
        self.category_occupation_map = {
            'スポーツ': ['野球選手', 'サッカー選手', 'ボクサー', '力士', 'テニス選手', 'ゴルファー',
                        'フィギュアスケート選手', '水泳選手', '陸上選手', 'バスケットボール選手',
                        'バレーボール選手', 'ラグビー選手', '卓球選手', 'バドミントン選手', '体操選手',
                        'レスリング選手', '柔道家', '空手家', '剣道家', 'プロレスラー', '総合格闘家'],

            'エンタメ': ['俳優', '女優', '歌手', 'アイドル', 'タレント', '芸人', 'お笑い芸人',
                        'モデル', 'グラビアアイドル', 'アナウンサー', 'MC', '司会者', 'YouTuber',
                        'TikToker', 'インフルエンサー', 'VTuber', 'ミュージシャン', 'バンド',
                        'DJ', '音楽プロデューサー', '演出家', '声優', 'ナレーター'],

            '文化・芸術': ['作家', '小説家', '詩人', '画家', '彫刻家', '写真家', '建築家',
                          'デザイナー', 'イラストレーター', '漫画家', 'アニメーター', '映画監督',
                          '脚本家', '作曲家', '指揮者', '演奏家', 'ピアニスト', 'バイオリニスト',
                          '書道家', '陶芸家', '華道家', '茶道家'],

            '歴史': ['天皇', '将軍', '武将', '大名', '侍', '幕末の志士', '軍人', '提督', '元帥'],

            '科学・技術': ['科学者', '研究者', '数学者', '物理学者', '化学者', '生物学者',
                          '医学者', '医師', 'ノーベル賞受賞者', '発明家', 'エンジニア',
                          'プログラマー', '宇宙飛行士', 'AI研究者'],

            'ビジネス': ['実業家', '起業家', '経営者', 'CEO', '社長', '会長', '創業者',
                        '投資家', 'ベンチャーキャピタリスト'],

            '政治': ['政治家', '首相', '総理大臣', '大臣', '知事', '市長', '議員', '大統領'],

            '宗教・思想': ['宗教家', '僧侶', '神父', '牧師', '哲学者', '思想家', '教育者', '活動家'],

            '犯罪・事件': ['犯罪者', '事件関係者']
        }

        logger.info("="*60)
        logger.info("📊 人物詳細情報充実処理開始")
        logger.info("="*60)
        logger.info(f"データベース: {database_file}")
        logger.info(f"レコード数: {len(self.df)}")
        logger.info(f"並列処理数: {self.max_workers}")

    def get_person_details_from_wikipedia(self, name: str):
        """Wikipediaから詳細情報を取得"""
        try:
            # WikipediaAPIで情報取得
            score, details = self.wiki_system.calculate_wikipedia_score(name)

            if details and details.get('found'):
                page_summary = details.get('summary', '')
                page_categories = details.get('categories', [])

                # 職業を抽出
                occupation = self.extract_occupation_from_text(page_summary)

                # 説明を生成
                description = self.generate_description(page_summary)

                # カテゴリを判定
                category = self.determine_category(occupation, page_summary, page_categories)

                return {
                    'occupation': occupation,
                    'description': description,
                    'category': category,
                    'wikipedia_summary': page_summary[:500]  # 最初の500文字
                }
        except Exception as e:
            logger.debug(f"Wikipedia取得エラー: {name} - {e}")

        return None

    def extract_occupation_from_text(self, text: str) -> str:
        """テキストから職業を抽出"""
        # 職業パターン
        occupation_patterns = [
            r'は、.*?の([^。、]+(?:選手|家|者|員|官|師|士|手|人|長))(?:[。、]|である|であった)',
            r'日本の([^。、]+(?:選手|家|者|員|官|師|士|手|人))(?:[。、]|である)',
            r'([^。、]+(?:選手|家|者|員|官|師|士|手|人))として',
        ]

        for pattern in occupation_patterns:
            match = re.search(pattern, text)
            if match:
                occupation = match.group(1)
                # クリーンアップ
                occupation = occupation.replace('である', '').replace('であった', '').strip()
                return occupation

        return ''

    def generate_description(self, text: str) -> str:
        """テキストから説明を生成"""
        if not text:
            return ''

        # 最初の文を取得
        sentences = text.split('。')
        if sentences:
            first_sentence = sentences[0] + '。'
            # 不要な部分を削除
            first_sentence = re.sub(r'\([^)]*\)', '', first_sentence)  # 括弧内を削除
            first_sentence = re.sub(r'\[[^\]]*\]', '', first_sentence)  # 角括弧内を削除

            # 100文字以内に制限
            if len(first_sentence) > 100:
                first_sentence = first_sentence[:97] + '...'

            return first_sentence.strip()

        return text[:100] if len(text) > 100 else text

    def determine_category(self, occupation: str, text: str, wiki_categories: list) -> str:
        """カテゴリを判定"""
        occupation_lower = occupation.lower()
        text_lower = text.lower()
        categories_str = ' '.join(wiki_categories).lower()

        # カテゴリマップから判定
        for category, occupations in self.category_occupation_map.items():
            for occ in occupations:
                if occ in occupation_lower or occ in text_lower:
                    return category

        # Wikipediaカテゴリから判定
        category_keywords = {
            'スポーツ': ['スポーツ', '選手', 'オリンピック', 'メダリスト'],
            'エンタメ': ['俳優', '女優', '歌手', 'タレント', '芸能', 'アイドル'],
            '文化・芸術': ['作家', '画家', '芸術', '文学', '美術', '音楽家'],
            '歴史': ['歴史', '武将', '大名', '天皇', '将軍'],
            '科学・技術': ['科学', '研究', '学者', 'ノーベル賞'],
            'ビジネス': ['実業', '経営', '企業', '創業'],
            '政治': ['政治', '議員', '大臣', '知事'],
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in categories_str:
                    return category

        return 'その他'

    def process_person(self, idx, row):
        """1人分を処理"""
        try:
            name = row.get('person_name_ja', row.get('name', ''))
            current_occupation = row.get('occupation', '')
            current_description = row.get('description', '')
            current_category = row.get('category', 'その他')

            # すでに十分な情報がある場合はスキップ
            if current_occupation and current_description and current_category != 'その他':
                return idx, None

            # Wikipedia情報を取得
            details = self.get_person_details_from_wikipedia(name)

            if details:
                updates = {}

                # occupationが空の場合は更新
                if not current_occupation and details['occupation']:
                    updates['occupation'] = details['occupation']

                # descriptionが空の場合は更新
                if not current_description and details['description']:
                    updates['description'] = details['description']

                # categoryが「その他」の場合は更新
                if current_category == 'その他' and details['category'] != 'その他':
                    updates['category'] = details['category']

                if updates:
                    return idx, updates

            # Wikipediaで見つからない場合は名前から推測
            if current_category == 'その他':
                # 名前パターンから推測
                if any(pattern in name for pattern in ['選手', 'プロ', 'チャンピオン']):
                    return idx, {'category': 'スポーツ'}
                elif any(pattern in name for pattern in ['歌手', '俳優', 'タレント', 'アイドル']):
                    return idx, {'category': 'エンタメ'}
                elif any(pattern in name for pattern in ['作家', '画家', '監督']):
                    return idx, {'category': '文化・芸術'}
                elif any(pattern in name for pattern in ['社長', 'CEO', '創業者']):
                    return idx, {'category': 'ビジネス'}
                elif any(pattern in name for pattern in ['大臣', '知事', '議員']):
                    return idx, {'category': '政治'}

            return idx, None

        except Exception as e:
            logger.error(f"エラー: {row.get('person_name_ja', '')} - {e}")
            return idx, None

    def enrich_all_parallel(self):
        """全員を並列処理で充実"""
        logger.info("\n📊 並列処理で詳細情報を充実")

        # occupationが空またはcategoryが「その他」の人物を優先
        priority_indices = []
        normal_indices = []

        for idx, row in self.df.iterrows():
            occupation = row.get('occupation', '')
            category = row.get('category', 'その他')

            if pd.isna(occupation) or occupation == '' or category == 'その他':
                priority_indices.append((idx, row))
            else:
                normal_indices.append((idx, row))

        all_indices = priority_indices + normal_indices
        logger.info(f"  優先処理: {len(priority_indices)}件")
        logger.info(f"  通常処理: {len(normal_indices)}件")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}

            # タスクを投入（最初の1000件に制限）
            for idx, row in all_indices[:1000]:
                future = executor.submit(self.process_person, idx, row.to_dict())
                futures[future] = idx

            # 結果を収集
            processed = 0
            for future in as_completed(futures):
                idx, updates = future.result()

                if updates:
                    for key, value in updates.items():
                        self.df.at[idx, key] = value
                    self.enriched += 1

                processed += 1

                if processed % 50 == 0:
                    logger.info(f"  処理済み: {processed}/{min(1000, len(all_indices))} (充実: {self.enriched})")

        logger.info(f"✅ 処理完了: {processed}件 (充実: {self.enriched}件)")

    def save_results(self):
        """結果を保存"""
        output_file = f"database_enriched_{self.timestamp}.csv"
        self.df.to_csv(output_file, index=False, encoding='utf-8-sig')

        logger.info(f"\n💾 出力ファイル: {output_file}")

        # 統計情報
        logger.info("\n📊 充実後の統計:")

        # occupation充実率
        occupation_filled = self.df['occupation'].notna().sum()
        occupation_rate = (occupation_filled / len(self.df)) * 100
        logger.info(f"  occupation充実率: {occupation_rate:.1f}% ({occupation_filled}/{len(self.df)})")

        # description充実率
        description_filled = self.df['description'].notna().sum()
        description_rate = (description_filled / len(self.df)) * 100
        logger.info(f"  description充実率: {description_rate:.1f}% ({description_filled}/{len(self.df)})")

        # カテゴリ分布
        category_counts = self.df['category'].value_counts()
        logger.info("\n  カテゴリ分布:")
        for cat, count in category_counts.head(10).items():
            percentage = (count / len(self.df)) * 100
            logger.info(f"    {cat}: {count}名 ({percentage:.1f}%)")

        # その他の割合
        others_count = category_counts.get('その他', 0)
        others_rate = (others_count / len(self.df)) * 100
        logger.info(f"\n  「その他」の割合: {others_rate:.1f}%")

        return output_file

def main():
    """メイン処理"""
    import glob

    # 最新のデータベースを取得
    db_files = glob.glob("database_category_improved_*.csv")
    if not db_files:
        db_files = glob.glob("database_episode_format_*.csv")
    if not db_files:
        db_files = glob.glob("database_*.csv")

    if not db_files:
        logger.error("データベースファイルが見つかりません")
        return

    latest_db = sorted(db_files)[-1]
    logger.info(f"対象ファイル: {latest_db}")

    # 処理実行
    enricher = PersonDetailsEnricher(latest_db)
    enricher.enrich_all_parallel()
    output_file = enricher.save_results()

    logger.info("\n" + "="*60)
    logger.info("✅ 詳細情報充実処理完了")
    logger.info("="*60)
    logger.info(f"充実件数: {enricher.enriched}")

if __name__ == "__main__":
    main()
