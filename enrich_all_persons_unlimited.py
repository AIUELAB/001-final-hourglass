#!/usr/bin/env python3
"""
全員分のoccupation/descriptionを充実させるスクリプト（API制限なし）
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

class UnlimitedPersonEnricher:
    """API制限なしで人物詳細情報を充実させるクラス"""

    def __init__(self):
        """初期化"""
        self.multi_api = MultiAPIRecognitionSystem()
        self.wiki_system = WikipediaRecognitionSystemV2()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.enriched = 0
        self.max_workers = 20  # API制限なし設定

        # カテゴリと職業のマッピング（改善版）
        self.category_occupation_map = {
            'スポーツ': ['野球選手', 'サッカー選手', 'ボクサー', '力士', 'テニス選手', 'ゴルファー',
                        'フィギュアスケート選手', '水泳選手', '陸上選手', 'バスケットボール選手',
                        'バレーボール選手', 'ラグビー選手', '卓球選手', 'バドミントン選手', '体操選手',
                        'レスリング選手', '柔道家', '空手家', '剣道家', 'プロレスラー', '総合格闘家',
                        'スキー選手', 'スノーボード選手', '自転車選手', 'モータースポーツ選手'],

            'エンタメ': ['俳優', '女優', '歌手', 'アイドル', 'タレント', '芸人', 'お笑い芸人',
                        'モデル', 'グラビアアイドル', 'アナウンサー', 'MC', '司会者', 'YouTuber',
                        'TikToker', 'インフルエンサー', 'VTuber', 'ミュージシャン', 'バンド',
                        'DJ', '音楽プロデューサー', '演出家', '声優', 'ナレーター', 'ラジオパーソナリティ',
                        'ダンサー', '振付師', 'マジシャン', 'パフォーマー'],

            '文化・芸術': ['作家', '小説家', '詩人', '画家', '彫刻家', '写真家', '建築家',
                          'デザイナー', 'イラストレーター', '漫画家', 'アニメーター', '映画監督',
                          '脚本家', '作曲家', '指揮者', '演奏家', 'ピアニスト', 'バイオリニスト',
                          '書道家', '陶芸家', '華道家', '茶道家', '料理研究家', 'ファッションデザイナー',
                          'グラフィックデザイナー', 'プロダクトデザイナー'],

            '歴史': ['天皇', '将軍', '武将', '大名', '侍', '幕末の志士', '軍人', '提督', '元帥',
                    '革命家', '探検家', '冒険家', '宣教師', '僧侶', '神官'],

            '科学・技術': ['科学者', '研究者', '数学者', '物理学者', '化学者', '生物学者',
                          '医学者', '医師', 'ノーベル賞受賞者', '発明家', 'エンジニア',
                          'プログラマー', '宇宙飛行士', 'AI研究者', '情報工学者', '機械工学者',
                          '建設技術者', '環境学者', '天文学者'],

            'ビジネス': ['実業家', '起業家', '経営者', 'CEO', '社長', '会長', '創業者',
                        '投資家', 'ベンチャーキャピタリスト', 'コンサルタント', '銀行家',
                        'ファンドマネージャー', '不動産開発者', 'IT企業経営者'],

            '政治': ['政治家', '首相', '総理大臣', '大臣', '知事', '市長', '議員', '大統領',
                    '外交官', '官僚', '国連職員', '裁判官', '検察官', '弁護士'],

            '宗教・思想': ['宗教家', '僧侶', '神父', '牧師', '哲学者', '思想家', '教育者', '活動家',
                          '社会運動家', '環境活動家', '人権活動家', 'NGO代表'],

            '犯罪・事件': ['犯罪者', '事件関係者', 'テロリスト', '詐欺師', 'ハッカー', '内部告発者']
        }

        logger.info("="*60)
        logger.info("🚀 全員分の詳細情報充実処理開始（API制限なし）")
        logger.info("="*60)
        logger.info(f"並列処理数: {self.max_workers}")

    def get_comprehensive_details(self, name: str):
        """包括的な詳細情報を取得"""
        try:
            # Multi-APIで包括的な情報取得
            score, details = self.multi_api.calculate_comprehensive_score(
                name=name,
                occupation='',
                description='',
                min_score=0
            )

            occupation = ''
            description = ''
            category = 'その他'

            # Wikipedia情報を優先
            if details.get('wikipedia', {}).get('found'):
                wiki_summary = details['wikipedia'].get('summary', '')
                wiki_categories = details['wikipedia'].get('categories', [])

                occupation = self.extract_occupation_from_text(wiki_summary)
                description = self.generate_description(wiki_summary)
                category = self.determine_category(occupation, wiki_summary, wiki_categories)

            # Web検索情報で補完
            elif details.get('web_search', {}).get('results'):
                web_results = details['web_search']['results']
                if web_results:
                    first_result = web_results[0]
                    snippet = first_result.get('snippet', '')

                    occupation = self.extract_occupation_from_text(snippet)
                    description = self.generate_description(snippet)
                    category = self.determine_category(occupation, snippet, [])

            return {
                'occupation': occupation,
                'description': description,
                'category': category,
                'recognition_score': score,
                'sources': list(details.keys())
            }

        except Exception as e:
            logger.debug(f"詳細取得エラー: {name} - {e}")
            return None

    def extract_occupation_from_text(self, text: str) -> str:
        """テキストから職業を抽出（改善版）"""
        if not text:
            return ''

        # 職業パターン（より包括的）
        occupation_patterns = [
            r'は、.*?の([^。、]+(?:選手|家|者|員|官|師|士|手|人|長|手))(?:[。、]|である|であった)',
            r'は、([^。、]+(?:選手|家|者|員|官|師|士|手|人))として',
            r'日本の([^。、]+(?:選手|家|者|員|官|師|士|手|人))(?:[。、]|である)',
            r'([^。、]+(?:選手|家|者|員|官|師|士|手|人))として活動',
            r'職業は([^。、]+)',
            r'は([^。、]+)を務め',
        ]

        for pattern in occupation_patterns:
            match = re.search(pattern, text)
            if match:
                occupation = match.group(1)
                # クリーンアップ
                occupation = occupation.replace('である', '').replace('であった', '')
                occupation = occupation.replace('日本の', '').strip()

                # 複数の職業がある場合は最初のものを取得
                if '・' in occupation:
                    occupation = occupation.split('・')[0]
                if '、' in occupation:
                    occupation = occupation.split('、')[0]

                return occupation.strip()

        # キーワードベースの抽出
        for category, occupations in self.category_occupation_map.items():
            for occ in occupations:
                if occ in text:
                    return occ

        return ''

    def generate_description(self, text: str) -> str:
        """テキストから説明を生成（改善版）"""
        if not text:
            return ''

        # HTMLタグを除去
        text = re.sub(r'<[^>]+>', '', text)

        # 最初の文を取得
        sentences = text.split('。')
        if sentences:
            first_sentence = sentences[0] + '。'

            # 不要な部分を削除
            first_sentence = re.sub(r'\([^)]*\)', '', first_sentence)  # 括弧内を削除
            first_sentence = re.sub(r'\[[^\]]*\]', '', first_sentence)  # 角括弧内を削除
            first_sentence = re.sub(r'\s+', ' ', first_sentence)  # 連続する空白を1つに

            # 150文字以内に制限
            if len(first_sentence) > 150:
                first_sentence = first_sentence[:147] + '...'

            return first_sentence.strip()

        return text[:150] if len(text) > 150 else text

    def determine_category(self, occupation: str, text: str, wiki_categories: list) -> str:
        """カテゴリを判定（改善版）"""
        occupation_lower = occupation.lower()
        text_lower = text.lower()
        categories_str = ' '.join(wiki_categories).lower()

        # 職業からの判定（優先度高）
        for category, occupations in self.category_occupation_map.items():
            for occ in occupations:
                if occ in occupation_lower:
                    return category

        # テキスト内容からの判定
        category_scores = {}
        for category, occupations in self.category_occupation_map.items():
            score = 0
            for occ in occupations:
                if occ in text_lower:
                    score += 2
                if occ in categories_str:
                    score += 1
            if score > 0:
                category_scores[category] = score

        # 最高スコアのカテゴリを返す
        if category_scores:
            return max(category_scores, key=category_scores.get)

        # Wikipediaカテゴリから判定
        category_keywords = {
            'スポーツ': ['スポーツ', '選手', 'オリンピック', 'メダリスト', '競技', 'プロ'],
            'エンタメ': ['俳優', '女優', '歌手', 'タレント', '芸能', 'アイドル', '音楽', '映画', 'テレビ'],
            '文化・芸術': ['作家', '画家', '芸術', '文学', '美術', '音楽家', '作品', '展覧会'],
            '歴史': ['歴史', '武将', '大名', '天皇', '将軍', '戦国', '江戸', '明治'],
            '科学・技術': ['科学', '研究', '学者', 'ノーベル賞', '大学', '教授', '博士'],
            'ビジネス': ['実業', '経営', '企業', '創業', 'ビジネス', '会社', '社長'],
            '政治': ['政治', '議員', '大臣', '知事', '選挙', '政党', '内閣'],
            '宗教・思想': ['宗教', '思想', '哲学', '活動家', '運動', 'NGO'],
            '犯罪・事件': ['犯罪', '事件', '逮捕', '容疑', '裁判']
        }

        category_scores = {}
        for category, keywords in category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 2
                if keyword in categories_str:
                    score += 1
            if score > 0:
                category_scores[category] = score

        if category_scores:
            return max(category_scores, key=category_scores.get)

        return 'その他'

    def process_person(self, idx, row):
        """1人分を処理"""
        try:
            name = row.get('person_name_ja', row.get('name', ''))
            current_occupation = row.get('occupation', '')
            current_description = row.get('description', '')
            current_category = row.get('category', 'その他')

            # すでに十分な情報がある場合は軽微な改善のみ
            if current_occupation and current_description and current_category != 'その他':
                # カテゴリの再確認のみ
                if current_category == 'その他':
                    details = self.get_comprehensive_details(name)
                    if details and details['category'] != 'その他':
                        return idx, {'category': details['category']}
                return idx, None

            # 包括的な情報を取得
            details = self.get_comprehensive_details(name)

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

                # スコアが向上した場合は更新
                if 'recognition_score' in row and details['recognition_score'] > row['recognition_score']:
                    updates['recognition_score'] = details['recognition_score']

                if updates:
                    return idx, updates

            return idx, None

        except Exception as e:
            logger.error(f"エラー: {row.get('person_name_ja', '')} - {e}")
            return idx, None

    def enrich_database(self):
        """データベース全体を充実"""
        # 最新のデータベースを読み込み
        db_file = "DATABASE_FINAL_LATEST.csv"
        if not Path(db_file).exists():
            # 他のデータベースファイルを探す
            import glob
            db_files = glob.glob("DATABASE_FINAL_*.csv")
            if not db_files:
                db_files = glob.glob("database_*.csv")
            if db_files:
                db_file = sorted(db_files)[-1]
            else:
                logger.error("データベースファイルが見つかりません")
                return None

        logger.info(f"データベース読み込み: {db_file}")
        self.df = pd.read_csv(db_file, encoding='utf-8-sig')

        logger.info(f"レコード数: {len(self.df)}")

        # 優先度順にソート（情報が不足している人を優先）
        priority_indices = []

        for idx, row in self.df.iterrows():
            occupation = row.get('occupation', '')
            description = row.get('description', '')
            category = row.get('category', 'その他')

            # 優先度を計算
            priority = 0
            if pd.isna(occupation) or occupation == '':
                priority += 3
            if pd.isna(description) or description == '':
                priority += 3
            if category == 'その他':
                priority += 2

            if priority > 0:
                priority_indices.append((idx, row, priority))

        # 優先度でソート
        priority_indices.sort(key=lambda x: x[2], reverse=True)

        logger.info(f"充実対象: {len(priority_indices)}件")

        # 並列処理で充実
        logger.info(f"\n📊 並列処理開始（{self.max_workers}並列）")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}

            # タスクを投入
            for idx, row, _ in priority_indices:
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

                if processed % 100 == 0:
                    logger.info(f"  処理済み: {processed}/{len(priority_indices)} (充実: {self.enriched})")

        logger.info(f"✅ 処理完了: {processed}件 (充実: {self.enriched}件)")

        return self.df

    def save_results(self):
        """結果を保存"""
        output_file = f"database_fully_enriched_{self.timestamp}.csv"
        self.df.to_csv(output_file, index=False, encoding='utf-8-sig')

        logger.info(f"\n💾 出力ファイル: {output_file}")

        # 統計情報
        logger.info("\n📊 充実後の統計:")

        # occupation充実率
        occupation_filled = (self.df['occupation'].notna() & (self.df['occupation'] != '')).sum()
        occupation_rate = (occupation_filled / len(self.df)) * 100
        logger.info(f"  occupation充実率: {occupation_rate:.1f}% ({occupation_filled}/{len(self.df)})")

        # description充実率
        description_filled = (self.df['description'].notna() & (self.df['description'] != '')).sum()
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
    enricher = UnlimitedPersonEnricher()

    # データベース充実
    df = enricher.enrich_database()

    if df is not None:
        # 結果を保存
        output_file = enricher.save_results()

        logger.info("\n" + "="*60)
        logger.info("✅ 全員分の詳細情報充実処理完了")
        logger.info("="*60)
        logger.info(f"充実件数: {enricher.enriched}")
        logger.info(f"出力ファイル: {output_file}")

if __name__ == "__main__":
    main()
