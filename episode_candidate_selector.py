#!/usr/bin/env python3
"""
エピソード候補選択システム
Episode Candidate Selector

UnifiedDataCollectionGatewayとSmartIterationEngineを連携させ、
有名人データベースから最適なエピソード生成候補を選定する

機能:
1. データベースから候補人物を抽出
2. CharacterTypeClassifierで架空キャラクターを除外
3. 知名度スコアと年齢分散でランキング
4. SmartIterationEngineへの最適な入力データを生成

Created: 2025-10-02
"""

import sqlite3
from src.database_utils import get_connection
import json
import csv
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# プロジェクト内モジュール
try:
    from character_type_classifier import CharacterTypeClassifier, CharacterType
except ImportError:
    logger.warning("CharacterTypeClassifier not available, using basic filtering")
    CharacterTypeClassifier = None
    CharacterType = None

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EpisodeCandidate:
    """エピソード候補データ"""
    person_id: str
    person_name: str
    person_name_ja: str
    birth_year: int
    category: str
    recognition_score: float
    entity_type: str

    # エピソード生成用の年齢リスト
    target_ages: List[int]

    # 優先度スコア（知名度、カテゴリ多様性、年齢分散を考慮）
    priority_score: float

    # メタデータ
    metadata: Dict = None


class EpisodeCandidateSelector:
    """エピソード候補選択システム"""

    def __init__(
        self,
        db_path: str = "episode_database.db",
        min_recognition_score: float = 5.0,
        min_birth_year: int = 1800,
        max_candidates: int = 100
    ):
        """
        初期化

        Args:
            db_path: エピソードデータベースパス
            min_recognition_score: 最小知名度スコア
            min_birth_year: 最小生年
            max_candidates: 最大候補数
        """
        self.db_path = db_path
        self.min_recognition_score = min_recognition_score
        self.min_birth_year = min_birth_year
        self.max_candidates = max_candidates

        # システムコンポーネント初期化
        self.classifier = CharacterTypeClassifier() if CharacterTypeClassifier else None

        logger.info(f"エピソード候補選択システム初期化完了")
        logger.info(f"  DB: {db_path}")
        logger.info(f"  最小知名度: {min_recognition_score}")
        logger.info(f"  最大候補数: {max_candidates}")

    def select_candidates(
        self,
        categories: Optional[List[str]] = None,
        exclude_fictional: bool = True,
        age_range: Tuple[int, int] = (20, 70)
    ) -> List[EpisodeCandidate]:
        """
        データベースから候補を選定

        Args:
            categories: カテゴリフィルター（Noneなら全カテゴリ）
            exclude_fictional: 架空キャラクター除外
            age_range: 生成対象年齢範囲

        Returns:
            エピソード候補リスト（優先度順）
        """
        logger.info(f"🔍 候補選定開始")

        # 1. データベースクエリ
        persons = self._query_database(categories)
        logger.info(f"  データベース抽出: {len(persons)}名")

        # 2. 架空キャラクター除外
        if exclude_fictional:
            persons = self._filter_fictional_characters(persons)
            logger.info(f"  架空キャラクター除外後: {len(persons)}名")

        # 3. エピソード候補データ生成
        candidates = []
        for person in persons:
            candidate = self._create_candidate(person, age_range)
            if candidate:
                candidates.append(candidate)

        logger.info(f"  候補生成完了: {len(candidates)}名")

        # 4. 優先度計算とソート
        candidates = self._calculate_priority(candidates)
        candidates = sorted(candidates, key=lambda c: c.priority_score, reverse=True)

        # 5. 最大候補数に制限
        candidates = candidates[:self.max_candidates]

        logger.info(f"✅ 最終候補: {len(candidates)}名")

        return candidates

    def _query_database(self, categories: Optional[List[str]] = None) -> List[Dict]:
        """データベースクエリ"""
        conn = get_connection(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # クエリ構築
        query = """
            SELECT
                person_id,
                person_name_ja,
                person_name_en,
                birth_year,
                category,
                recognition_score,
                metadata
            FROM persons
            WHERE
                birth_year IS NOT NULL
                AND birth_year >= ?
                AND recognition_score >= ?
        """

        params = [self.min_birth_year, self.min_recognition_score]

        # カテゴリフィルター
        if categories:
            placeholders = ','.join(['?' for _ in categories])
            query += f" AND category IN ({placeholders})"
            params.extend(categories)

        query += " ORDER BY recognition_score DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # 辞書に変換
        persons = [dict(row) for row in rows]
        return persons

    def _filter_fictional_characters(self, persons: List[Dict]) -> List[Dict]:
        """架空キャラクターを除外"""
        if not self.classifier:
            # Classifierがない場合は全て通過
            logger.warning("CharacterTypeClassifier無効、フィルタリングスキップ")
            for person in persons:
                person['entity_type'] = 'real_person'
            return persons

        filtered = []

        for person in persons:
            # CharacterTypeClassifierで判定
            classification = self.classifier.classify(
                person['person_name_ja'] or person['person_name_en']
            )

            # 実在人物のみ保持
            if classification.character_type in [
                CharacterType.REAL_PERSON,
                CharacterType.HISTORICAL_FIGURE
            ]:
                person['entity_type'] = classification.character_type.value
                filtered.append(person)
            else:
                logger.debug(f"  除外: {person['person_name_ja']} ({classification.character_type.value})")

        return filtered

    def _create_candidate(
        self,
        person: Dict,
        age_range: Tuple[int, int]
    ) -> Optional[EpisodeCandidate]:
        """エピソード候補データを生成"""
        try:
            # 現在年を計算
            current_year = datetime.now().year
            age_now = current_year - person['birth_year']

            # 対象年齢リストを生成
            min_age, max_age = age_range
            target_ages = []

            # 20歳代～60歳代で5歳刻み
            for age in range(min_age, min(max_age, age_now) + 1, 5):
                if min_age <= age <= max_age:
                    target_ages.append(age)

            # 年齢が範囲外なら候補から除外
            if not target_ages:
                return None

            # メタデータ解析
            metadata = {}
            if person.get('metadata'):
                try:
                    metadata = json.loads(person['metadata'])
                except:
                    pass

            candidate = EpisodeCandidate(
                person_id=person['person_id'],
                person_name=person['person_name_en'] or person['person_name_ja'],
                person_name_ja=person['person_name_ja'],
                birth_year=person['birth_year'],
                category=person['category'],
                recognition_score=person['recognition_score'],
                entity_type=person.get('entity_type', 'real_person'),
                target_ages=target_ages,
                priority_score=0.0,  # 後で計算
                metadata=metadata
            )

            return candidate

        except Exception as e:
            logger.warning(f"候補生成エラー: {person.get('person_name_ja')}: {e}")
            return None

    def _calculate_priority(self, candidates: List[EpisodeCandidate]) -> List[EpisodeCandidate]:
        """優先度スコアを計算"""

        # カテゴリ分布を計算（カテゴリ多様性ボーナス）
        category_counts = {}
        for c in candidates:
            category_counts[c.category] = category_counts.get(c.category, 0) + 1

        for candidate in candidates:
            # ベーススコア: 知名度スコア (0-10)
            base_score = candidate.recognition_score

            # カテゴリ多様性ボーナス（少ないカテゴリほど高い）
            category_bonus = 10.0 / max(1, category_counts[candidate.category])

            # 年齢分散ボーナス（多くの年齢でエピソード生成可能）
            age_diversity_bonus = len(candidate.target_ages) * 0.5

            # 総合優先度
            candidate.priority_score = (
                base_score * 1.0 +
                category_bonus * 0.3 +
                age_diversity_bonus * 0.2
            )

        return candidates

    def export_to_csv(
        self,
        candidates: List[EpisodeCandidate],
        output_path: str = "episode_candidates.csv"
    ):
        """候補リストをCSV出力（UTF-8 BOM）"""

        fieldnames = [
            'person_id',
            'person_name',
            'person_name_ja',
            'birth_year',
            'category',
            'recognition_score',
            'entity_type',
            'target_ages',
            'priority_score'
        ]

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for candidate in candidates:
                row = {
                    'person_id': candidate.person_id,
                    'person_name': candidate.person_name,
                    'person_name_ja': candidate.person_name_ja,
                    'birth_year': candidate.birth_year,
                    'category': candidate.category,
                    'recognition_score': candidate.recognition_score,
                    'entity_type': candidate.entity_type,
                    'target_ages': ','.join(map(str, candidate.target_ages)),
                    'priority_score': f"{candidate.priority_score:.2f}"
                }
                writer.writerow(row)

        logger.info(f"💾 CSV出力: {output_path}")

    def generate_episode_batch_input(
        self,
        candidates: List[EpisodeCandidate],
        episodes_per_person: int = 2
    ) -> List[Dict]:
        """
        SmartIterationEngine用のバッチ入力を生成

        Args:
            candidates: エピソード候補リスト
            episodes_per_person: 1人あたりのエピソード数

        Returns:
            SmartIterationEngine.generate_episode()用の入力リスト
        """
        batch_input = []

        for candidate in candidates:
            # 各人物について、target_agesから最大episodes_per_person個選択
            selected_ages = candidate.target_ages[:episodes_per_person]

            for age in selected_ages:
                batch_input.append({
                    'person_name': candidate.person_name_ja,
                    'age': age,
                    'category': candidate.category,
                    'person_id': candidate.person_id,
                    'birth_year': candidate.birth_year,
                    'recognition_score': candidate.recognition_score
                })

        logger.info(f"📋 バッチ入力生成: {len(batch_input)}エピソード")

        return batch_input


def main():
    """テスト実行"""
    import argparse

    parser = argparse.ArgumentParser(description="Episode Candidate Selector")
    parser.add_argument('--count', type=int, default=50, help='候補数')
    parser.add_argument('--min-score', type=float, default=6.0, help='最小知名度')
    parser.add_argument('--output', default='episode_candidates.csv', help='出力CSV')
    parser.add_argument('--categories', nargs='+', help='カテゴリフィルター')

    args = parser.parse_args()

    # 候補選定
    selector = EpisodeCandidateSelector(
        min_recognition_score=args.min_score,
        max_candidates=args.count
    )

    candidates = selector.select_candidates(
        categories=args.categories,
        exclude_fictional=True,
        age_range=(20, 70)
    )

    # 統計表示
    print(f"\n{'='*60}")
    print(f"📊 エピソード候補選定結果")
    print(f"{'='*60}")
    print(f"総候補数: {len(candidates)}")

    # カテゴリ分布
    category_dist = {}
    for c in candidates:
        category_dist[c.category] = category_dist.get(c.category, 0) + 1

    print(f"\nカテゴリ分布:")
    for cat, count in sorted(category_dist.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {cat}: {count}名")

    # トップ10
    print(f"\nトップ10候補:")
    for i, c in enumerate(candidates[:10], 1):
        print(f"  {i}. {c.person_name_ja} ({c.birth_year}年, {c.category}) - スコア: {c.priority_score:.2f}")

    # CSV出力
    selector.export_to_csv(candidates, args.output)

    # バッチ入力生成（サンプル）
    batch_input = selector.generate_episode_batch_input(candidates[:10], episodes_per_person=2)
    print(f"\n📋 バッチ入力サンプル（最初の5件）:")
    for item in batch_input[:5]:
        print(f"  {item['person_name']} ({item['age']}歳, {item['category']})")

    print(f"\n✅ 完了")


if __name__ == "__main__":
    main()
