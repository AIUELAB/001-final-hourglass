#!/usr/bin/env python3
"""
架空キャラクター自動判定システム（強化版）

目的:
1. 複数の判定基準を組み合わせて高精度判定
2. 有名作品データベースとの照合
3. 確信度スコアリング

判定基準:
- カテゴリ情報
- 人物名パターン（・、＝等の特殊文字）
- Wikipedia情報
- 既知の作品データベース
"""

import sqlite3
import logging
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ================================================================================
# データクラス
# ================================================================================

class EntityType(Enum):
    """エンティティタイプ"""
    REAL_PERSON = "real_person"
    FICTIONAL_CHARACTER = "fictional_character"
    UNCERTAIN = "uncertain"


@dataclass
class ClassificationResult:
    """判定結果"""
    entity_type: EntityType
    confidence: float              # 0.0 - 1.0
    primary_work: Optional[str]    # 作品名
    reasoning: str                 # 判定理由
    evidence: List[str]            # 証拠リスト


# ================================================================================
# 有名作品データベース
# ================================================================================

FAMOUS_WORKS_DATABASE = {
    # 少年漫画・アニメ
    'ONE PIECE': [
        'モンキー・D・ルフィ', 'ロロノア・ゾロ', 'ナミ', 'ウソップ', 'サンジ',
        'トニートニー・チョッパー', 'ニコ・ロビン', 'フランキー', 'ブルック'
    ],
    'ドラゴンボール': [
        '孫悟空', 'ベジータ', 'ピッコロ', 'クリリン', 'ブルマ',
        'トランクス', '孫悟飯', 'フリーザ', 'セル', '魔人ブウ'
    ],
    'NARUTO': [
        'うずまきナルト', 'うちはサスケ', 'はたけカカシ', '春野サクラ',
        'うちはイタチ', '日向ネジ', '我愛羅', 'うちはマダラ'
    ],
    '鬼滅の刃': [
        '竈門炭治郎', '竈門禰豆子', '我妻善逸', '嘴平伊之助',
        '冨岡義勇', '胡蝶しのぶ', '煉獄杏寿郎', '時透無一郎'
    ],
    '呪術廻戦': [
        '虎杖悠仁', '伏黒恵', '釘崎野薔薇', '五条悟', '七海建人'
    ],
    '進撃の巨人': [
        'エレン・イェーガー', 'ミカサ・アッカーマン', 'アルミン・アルレルト',
        'リヴァイ', 'エルヴィン・スミス'
    ],

    # 少女漫画・アニメ
    '美少女戦士セーラームーン': [
        '月野うさぎ', '水野亜美', '火野レイ', '木野まこと', '愛野美奈子'
    ],
    'ちびまる子ちゃん': [
        'さくらももこ', 'さくらひろし', 'さくらすみれ'
    ],

    # ジブリ作品
    'となりのトトロ': ['トトロ', 'サツキ', 'メイ'],
    '千と千尋の神隠し': ['千尋', 'ハク', '湯婆婆', '釜爺'],
    '魔女の宅急便': ['キキ', 'ジジ', 'トンボ'],

    # ゲーム
    'ポケットモンスター': ['サトシ', 'ピカチュウ', 'ミュウツー'],
    'ドラゴンクエスト': ['勇者', 'スライム'],
    'ファイナルファンタジー': ['クラウド', 'ティファ', 'セフィロス'],
    'スーパーマリオ': ['マリオ', 'ルイージ', 'ピーチ姫', 'クッパ'],

    # 国民的キャラクター
    'ドラえもん': ['ドラえもん', 'のび太', 'しずかちゃん', 'ジャイアン', 'スネ夫'],
    'アンパンマン': ['アンパンマン', 'バイキンマン', 'ドキンちゃん', 'しょくぱんまん'],
    'サザエさん': ['サザエ', 'カツオ', 'ワカメ', 'マスオ', '波平', 'フネ', 'タラちゃん'],

    # 特撮
    'ウルトラマン': ['ウルトラマン', 'ゼットン', 'バルタン星人'],
    '仮面ライダー': ['仮面ライダー1号', '仮面ライダー2号'],

    # ディズニー
    'ディズニー': ['ミッキーマウス', 'ミニーマウス', 'ドナルドダック', 'グーフィー']
}


# ================================================================================
# 架空キャラクター判定エンジン
# ================================================================================

class FictionalCharacterClassifier:
    """架空キャラクター判定エンジン"""

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__ + '.FictionalCharacterClassifier')

        # 作品名→キャラクター名のマッピング
        self.character_to_work = {}
        for work, characters in FAMOUS_WORKS_DATABASE.items():
            for character in characters:
                self.character_to_work[character] = work

    def classify(
        self,
        person_name: str,
        category: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ClassificationResult:
        """
        総合判定

        Args:
            person_name: 人物名
            category: カテゴリ
            metadata: 追加メタデータ

        Returns:
            ClassificationResult
        """
        evidence = []
        confidence_scores = []

        # 判定1: 有名作品データベース照合
        work_match = self._check_famous_works_database(person_name)
        if work_match:
            evidence.append(f"有名作品データベースに登録: {work_match}")
            confidence_scores.append(0.95)
            return ClassificationResult(
                entity_type=EntityType.FICTIONAL_CHARACTER,
                confidence=0.95,
                primary_work=work_match,
                reasoning="有名作品データベースに登録されている",
                evidence=evidence
            )

        # 判定2: カテゴリ判定
        category_result = self._check_category(category)
        if category_result:
            entity_type, conf, work = category_result
            evidence.append(f"カテゴリ判定: {category}")
            confidence_scores.append(conf)

            if conf > 0.8:
                return ClassificationResult(
                    entity_type=entity_type,
                    confidence=conf,
                    primary_work=work,
                    reasoning=f"カテゴリから判定: {category}",
                    evidence=evidence
                )

        # 判定3: 人物名パターン分析
        name_pattern_result = self._check_name_pattern(person_name)
        if name_pattern_result:
            entity_type, conf, reason = name_pattern_result
            evidence.append(f"名前パターン: {reason}")
            confidence_scores.append(conf)

        # 総合判定
        if not confidence_scores:
            # デフォルトは実在人物
            return ClassificationResult(
                entity_type=EntityType.REAL_PERSON,
                confidence=0.6,
                primary_work=None,
                reasoning="判定基準に該当せず、実在人物として扱う",
                evidence=["デフォルト判定"]
            )

        avg_confidence = sum(confidence_scores) / len(confidence_scores)

        if avg_confidence > 0.7:
            return ClassificationResult(
                entity_type=EntityType.FICTIONAL_CHARACTER,
                confidence=avg_confidence,
                primary_work=None,
                reasoning="複数の判定基準から架空キャラクターと判定",
                evidence=evidence
            )
        else:
            return ClassificationResult(
                entity_type=EntityType.REAL_PERSON,
                confidence=1.0 - avg_confidence,
                primary_work=None,
                reasoning="実在人物と判定",
                evidence=evidence
            )

    def _check_famous_works_database(self, person_name: str) -> Optional[str]:
        """
        有名作品データベース照合

        Args:
            person_name: 人物名

        Returns:
            作品名 or None
        """
        return self.character_to_work.get(person_name)

    def _check_category(self, category: Optional[str]) -> Optional[Tuple[EntityType, float, Optional[str]]]:
        """
        カテゴリから判定

        Args:
            category: カテゴリ名

        Returns:
            (EntityType, confidence, work_name) or None
        """
        if not category:
            return None

        category_lower = category.lower()

        # 架空キャラクターを示すキーワード
        fictional_keywords = [
            '架空', 'キャラクター', 'フィクション', '登場人物'
        ]

        for keyword in fictional_keywords:
            if keyword in category_lower:
                # "〇〇の登場人物" から作品名を抽出
                work_name = self._extract_work_from_category(category)
                return (EntityType.FICTIONAL_CHARACTER, 0.9, work_name)

        # アニメ・漫画・ゲーム関連
        media_keywords = [
            'アニメ', '漫画', 'マンガ', 'ゲーム', '小説'
        ]

        for keyword in media_keywords:
            if keyword in category_lower:
                work_name = self._extract_work_from_category(category)
                return (EntityType.FICTIONAL_CHARACTER, 0.8, work_name)

        return None

    def _extract_work_from_category(self, category: str) -> Optional[str]:
        """
        カテゴリから作品名を抽出

        Args:
            category: カテゴリ文字列

        Returns:
            作品名 or None
        """
        # "〇〇の登場人物"
        pattern1 = r'(.+?)の登場人物'
        match = re.search(pattern1, category)
        if match:
            return match.group(1)

        # "〇〇(アニメ)", "〇〇(漫画)"
        pattern2 = r'(.+?)\((?:アニメ|漫画|ゲーム|小説)\)'
        match = re.search(pattern2, category)
        if match:
            return match.group(1)

        return None

    def _check_name_pattern(self, person_name: str) -> Optional[Tuple[EntityType, float, str]]:
        """
        名前パターンから判定

        Args:
            person_name: 人物名

        Returns:
            (EntityType, confidence, reason) or None
        """
        # 架空キャラクターに多い特徴
        # 1. 中黒（・）を含む（実在人物ではまれ）
        if '・' in person_name and not self._is_foreign_name(person_name):
            return (EntityType.FICTIONAL_CHARACTER, 0.7, "中黒（・）を含む")

        # 2. カタカナのみ（実在人物ではまれ）
        if self._is_all_katakana(person_name):
            return (EntityType.FICTIONAL_CHARACTER, 0.6, "カタカナのみ")

        # 3. 特殊文字（＝、☆等）を含む
        special_chars = ['＝', '☆', '★', '♪', '♡']
        if any(char in person_name for char in special_chars):
            return (EntityType.FICTIONAL_CHARACTER, 0.8, "特殊文字を含む")

        return None

    def _is_foreign_name(self, name: str) -> bool:
        """外国人名判定"""
        # 簡易的な判定（英字を含むかどうか）
        return bool(re.search(r'[A-Za-z]', name))

    def _is_all_katakana(self, name: str) -> bool:
        """カタカナのみ判定"""
        # カタカナと中黒のみで構成されているか
        pattern = r'^[ァ-ヴー・]+$'
        return bool(re.match(pattern, name))


# ================================================================================
# バッチ処理
# ================================================================================

def classify_batch_from_database(
    db_path: str = "episode_database.db",
    limit: int = 100
) -> List[Dict]:
    """
    データベースから人物を取得してバッチ判定

    Args:
        db_path: データベースパス
        limit: 処理件数上限

    Returns:
        判定結果リスト
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # データ取得
    cursor.execute("""
        SELECT person_id, person_name_ja, category
        FROM persons
        ORDER BY recognition_score DESC
        LIMIT ?
    """, (limit,))

    persons = cursor.fetchall()
    conn.close()

    # 判定実行
    classifier = FictionalCharacterClassifier()
    results = []

    for person in persons:
        result = classifier.classify(
            person['person_name_ja'],
            person['category']
        )

        results.append({
            'person_id': person['person_id'],
            'person_name': person['person_name_ja'],
            'category': person['category'],
            'entity_type': result.entity_type.value,
            'confidence': result.confidence,
            'primary_work': result.primary_work,
            'reasoning': result.reasoning,
            'evidence': result.evidence
        })

    return results


def print_classification_report(results: List[Dict]):
    """判定結果レポート表示"""
    print("="*80)
    print("架空キャラクター判定レポート")
    print("="*80)

    # 統計
    total = len(results)
    fictional_count = sum(1 for r in results if r['entity_type'] == 'fictional_character')
    real_count = sum(1 for r in results if r['entity_type'] == 'real_person')

    print(f"\n総処理件数: {total}")
    print(f"架空キャラクター: {fictional_count}件 ({fictional_count/total*100:.1f}%)")
    print(f"実在人物: {real_count}件 ({real_count/total*100:.1f}%)")

    # 架空キャラクターリスト
    print(f"\n【架空キャラクター一覧】")
    fictional_results = [r for r in results if r['entity_type'] == 'fictional_character']

    for i, result in enumerate(fictional_results[:20], 1):  # 上位20件
        work_info = f"({result['primary_work']})" if result['primary_work'] else ""
        print(f"{i:2d}. {result['person_name']:<20} {work_info:<30} 確信度: {result['confidence']:.2f}")

    if len(fictional_results) > 20:
        print(f"... 他 {len(fictional_results) - 20}件")


# ================================================================================
# メイン処理
# ================================================================================

def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='架空キャラクター自動判定')
    parser.add_argument('--db', default='episode_database.db', help='データベースパス')
    parser.add_argument('--limit', type=int, default=100, help='処理件数上限')

    args = parser.parse_args()

    print("="*80)
    print("架空キャラクター自動判定システム")
    print("="*80)
    print(f"データベース: {args.db}")
    print(f"処理件数: {args.limit}\n")

    # バッチ判定実行
    results = classify_batch_from_database(args.db, args.limit)

    # レポート表示
    print_classification_report(results)

    # JSON保存
    import json
    output_path = "fictional_character_classification.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 判定結果を保存: {output_path}")


if __name__ == '__main__':
    main()
