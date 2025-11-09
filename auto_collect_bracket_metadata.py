#!/usr/bin/env python3
"""
MCP自動データ収集スクリプト

目的:
1. Brave Searchで人物の所属グループ・作品情報を自動収集
2. Wikipediaで架空キャラクター判定
3. データベースに自動反映

使用MCPサーバー:
- brave-search: グループ情報検索
- context7: 作品・キャラクター情報
- fetch: Wikipedia情報取得
"""

import sqlite3
from src.database_utils import get_connection
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ================================================================================
# データクラス
# ================================================================================

@dataclass
class BracketMetadata:
    """括弧表示メタデータ"""
    entity_type: str                      # real_person / fictional_character
    group_affiliation: Optional[str]      # グループ名
    primary_work: Optional[str]           # 作品名
    show_group_in_bracket: int            # 0 or 1
    group_status: Optional[str]           # active / disbanded / hiatus
    fame_level: Optional[str]             # personal_more_famous / group_more_famous / equal
    bracket_display_text: Optional[str]   # 実際に表示するテキスト
    confidence_score: float               # 確信度 (0.0-1.0)
    data_source: str                      # データソース


# ================================================================================
# 架空キャラクター判定
# ================================================================================

class FictionalCharacterDetector:
    """架空キャラクター自動判定システム"""

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__ + '.FictionalCharacterDetector')

        # 架空キャラクターを示すキーワード
        self.fictional_keywords = {
            '架空', 'キャラクター', 'フィクション', '登場人物',
            'アニメ', '漫画', 'マンガ', 'ゲーム', '小説',
            'キャラ', '主人公', 'ヒーロー', 'ヒロイン'
        }

        # 実在人物を示すキーワード
        self.real_person_keywords = {
            '生年月日', '出身地', '卒業', '所属事務所',
            '結婚', '受賞', '活動期間', '本名'
        }

    def detect_from_wikipedia(self, person_name: str, wikipedia_text: str) -> Tuple[str, float]:
        """
        Wikipediaテキストから架空キャラクター判定

        Args:
            person_name: 人物名
            wikipedia_text: Wikipediaテキスト

        Returns:
            (entity_type, confidence_score)
        """
        if not wikipedia_text:
            return ('real_person', 0.5)  # デフォルトは実在人物

        text_lower = wikipedia_text.lower()

        # キーワードカウント
        fictional_count = sum(
            1 for keyword in self.fictional_keywords
            if keyword in text_lower
        )

        real_count = sum(
            1 for keyword in self.real_person_keywords
            if keyword in text_lower
        )

        # 判定
        if fictional_count > real_count:
            confidence = min(fictional_count / (fictional_count + real_count + 1), 0.95)
            return ('fictional_character', confidence)
        else:
            confidence = min(real_count / (fictional_count + real_count + 1), 0.95)
            return ('real_person', confidence)

    def detect_from_category(self, category: str) -> Tuple[str, float]:
        """
        カテゴリから架空キャラクター判定

        Args:
            category: カテゴリ名

        Returns:
            (entity_type, confidence_score)
        """
        if not category:
            return ('real_person', 0.5)

        if '架空' in category or 'キャラクター' in category:
            return ('fictional_character', 0.9)

        return ('real_person', 0.7)


# ================================================================================
# グループ情報収集
# ================================================================================

class GroupInfoCollector:
    """グループ情報収集システム"""

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__ + '.GroupInfoCollector')

        # カテゴリ別の検索キーワードテンプレート
        self.search_templates = {
            'お笑い芸人': '{person_name} コンビ グループ',
            'ミュージシャン': '{person_name} バンド グループ',
            'YouTuber': '{person_name} YouTuber グループ',
            'アイドル': '{person_name} アイドル グループ'
        }

    def collect_from_search(
        self,
        person_name: str,
        category: str
    ) -> Optional[BracketMetadata]:
        """
        検索結果からグループ情報を収集

        Args:
            person_name: 人物名
            category: カテゴリ

        Returns:
            BracketMetadata or None
        """
        # 検索キーワード生成
        template = self.search_templates.get(category, '{person_name} グループ')
        search_query = template.format(person_name=person_name)

        self.logger.info(f"検索クエリ: {search_query}")

        # ここでMCP brave-searchを使用（実際の実装では別途MCPクライアントを使用）
        # 今回はシミュレーション

        return None

    def parse_group_info(self, search_results: str) -> Dict:
        """
        検索結果からグループ情報を抽出

        Args:
            search_results: 検索結果テキスト

        Returns:
            グループ情報辞書
        """
        group_info = {
            'group_name': None,
            'group_status': None,
            'fame_level': None
        }

        # パターンマッチング
        # "〇〇として活動" → グループ名を抽出
        pattern_active = r'(.+?)として活動'
        match = re.search(pattern_active, search_results)
        if match:
            group_info['group_name'] = match.group(1).strip()
            group_info['group_status'] = 'active'

        # "〇〇は解散" → 解散情報
        pattern_disbanded = r'(.+?)は解散'
        match = re.search(pattern_disbanded, search_results)
        if match:
            group_info['group_status'] = 'disbanded'

        return group_info


# ================================================================================
# 自動データ収集エンジン
# ================================================================================

class AutoBracketMetadataCollector:
    """自動括弧メタデータ収集エンジン"""

    def __init__(self, db_path: str = "episode_database.db"):
        """
        初期化

        Args:
            db_path: データベースパス
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__ + '.AutoBracketMetadataCollector')

        # サブシステム初期化
        self.fictional_detector = FictionalCharacterDetector()
        self.group_collector = GroupInfoCollector()

        # 収集結果キャッシュ
        self.cache = {}

    def collect_for_person(
        self,
        person_id: str,
        person_name: str,
        category: str
    ) -> Optional[BracketMetadata]:
        """
        特定の人物のメタデータを自動収集

        Args:
            person_id: 人物ID
            person_name: 人物名
            category: カテゴリ

        Returns:
            BracketMetadata or None
        """
        self.logger.info(f"データ収集開始: {person_name} ({category})")

        # Step 1: 架空キャラクター判定
        entity_type, confidence = self.fictional_detector.detect_from_category(category)

        # Step 2: カテゴリ別の情報収集
        if entity_type == 'fictional_character':
            # 架空キャラクターの場合: 作品名収集
            return self._collect_fictional_character_metadata(person_name, category, confidence)
        else:
            # 実在人物の場合: グループ情報収集
            return self._collect_real_person_metadata(person_name, category, confidence)

    def _collect_fictional_character_metadata(
        self,
        person_name: str,
        category: str,
        confidence: float
    ) -> BracketMetadata:
        """
        架空キャラクターのメタデータ収集

        Args:
            person_name: キャラクター名
            category: カテゴリ
            confidence: 確信度

        Returns:
            BracketMetadata
        """
        # 作品名の推定（カテゴリから）
        primary_work = self._extract_work_from_category(category)

        return BracketMetadata(
            entity_type='fictional_character',
            group_affiliation=None,
            primary_work=primary_work,
            show_group_in_bracket=1 if primary_work else 0,
            group_status=None,
            fame_level=None,
            bracket_display_text=primary_work,
            confidence_score=confidence,
            data_source='category_analysis'
        )

    def _collect_real_person_metadata(
        self,
        person_name: str,
        category: str,
        confidence: float
    ) -> Optional[BracketMetadata]:
        """
        実在人物のメタデータ収集

        Args:
            person_name: 人物名
            category: カテゴリ
            confidence: 確信度

        Returns:
            BracketMetadata or None
        """
        # グループ情報収集
        group_metadata = self.group_collector.collect_from_search(person_name, category)

        if group_metadata:
            return group_metadata

        # 情報が得られなかった場合
        return BracketMetadata(
            entity_type='real_person',
            group_affiliation=None,
            primary_work=None,
            show_group_in_bracket=0,
            group_status=None,
            fame_level=None,
            bracket_display_text=None,
            confidence_score=confidence,
            data_source='no_data_found'
        )

    def _extract_work_from_category(self, category: str) -> Optional[str]:
        """
        カテゴリから作品名を抽出

        Args:
            category: カテゴリ文字列

        Returns:
            作品名 or None
        """
        # "〇〇の登場人物" パターン
        pattern = r'(.+?)の登場人物'
        match = re.search(pattern, category)
        if match:
            return match.group(1)

        return None

    def collect_batch(
        self,
        limit: int = 100,
        category_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        バッチ処理でメタデータを収集

        Args:
            limit: 処理件数上限
            category_filter: カテゴリフィルタ

        Returns:
            収集結果リスト
        """
        conn = get_connection(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 収集対象の抽出
        query = """
            SELECT person_id, person_name_ja, category
            FROM persons
            WHERE 1=1
        """

        params = []
        if category_filter:
            query += " AND category = ?"
            params.append(category_filter)

        query += " ORDER BY recognition_score DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        persons = cursor.fetchall()

        # バッチ処理
        results = []
        for i, person in enumerate(persons, 1):
            self.logger.info(f"処理中 [{i}/{len(persons)}]: {person['person_name_ja']}")

            metadata = self.collect_for_person(
                person['person_id'],
                person['person_name_ja'],
                person['category'] or ''
            )

            if metadata:
                results.append({
                    'person_id': person['person_id'],
                    'person_name': person['person_name_ja'],
                    'metadata': metadata
                })

            # レート制限対策
            time.sleep(0.5)

        conn.close()

        return results

    def save_results(self, results: List[Dict], output_path: str = "auto_collected_metadata.json"):
        """
        収集結果をJSON保存

        Args:
            results: 収集結果リスト
            output_path: 出力ファイルパス
        """
        # データクラスをdictに変換
        json_results = []
        for result in results:
            metadata = result['metadata']
            json_results.append({
                'person_id': result['person_id'],
                'person_name': result['person_name'],
                'metadata': {
                    'entity_type': metadata.entity_type,
                    'group_affiliation': metadata.group_affiliation,
                    'primary_work': metadata.primary_work,
                    'show_group_in_bracket': metadata.show_group_in_bracket,
                    'group_status': metadata.group_status,
                    'fame_level': metadata.fame_level,
                    'bracket_display_text': metadata.bracket_display_text,
                    'confidence_score': metadata.confidence_score,
                    'data_source': metadata.data_source
                }
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, ensure_ascii=False, indent=2)

        self.logger.info(f"✅ 収集結果を保存: {output_path}")


# ================================================================================
# メイン処理
# ================================================================================

def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='MCP自動データ収集')
    parser.add_argument('--db', default='episode_database.db', help='データベースパス')
    parser.add_argument('--limit', type=int, default=100, help='処理件数上限')
    parser.add_argument('--category', help='カテゴリフィルタ（お笑い芸人、ミュージシャン等）')
    parser.add_argument('--output', default='auto_collected_metadata.json', help='出力JSONパス')

    args = parser.parse_args()

    print("="*80)
    print("MCP自動データ収集スクリプト")
    print("="*80)
    print(f"データベース: {args.db}")
    print(f"処理件数上限: {args.limit}")
    print(f"カテゴリフィルタ: {args.category or '全カテゴリ'}")
    print(f"出力先: {args.output}\n")

    # 収集実行
    collector = AutoBracketMetadataCollector(args.db)
    results = collector.collect_batch(
        limit=args.limit,
        category_filter=args.category
    )

    # 結果保存
    collector.save_results(results, args.output)

    # サマリー表示
    print("\n" + "="*80)
    print("収集結果サマリー")
    print("="*80)
    print(f"総処理件数: {len(results)}")

    # entity_type別の集計
    entity_type_counts = {}
    for result in results:
        entity_type = result['metadata'].entity_type
        entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1

    print(f"\nエンティティタイプ別:")
    for entity_type, count in entity_type_counts.items():
        print(f"  - {entity_type}: {count}件")

    # 確信度の統計
    confidence_scores = [result['metadata'].confidence_score for result in results]
    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        print(f"\n平均確信度: {avg_confidence:.2f}")

    print("\n✅ 処理完了！")


if __name__ == '__main__':
    main()
