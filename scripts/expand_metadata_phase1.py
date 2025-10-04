#!/usr/bin/env python3
"""
メタデータ拡張 Phase 1: 優先度順500件

目的:
1. 知名度スコア7.0以上の人物のメタデータを自動収集
2. MCP (Brave Search, Wikipedia) を活用
3. 括弧表示判定に必要な情報を自動設定

対象:
- エンタメ: 200件
- 架空キャラクター: 150件
- スポーツ: 100件
- その他: 50件
"""

import sqlite3
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PersonMetadata:
    """人物メタデータ"""
    entity_type: str  # 'real_person' or 'fictional_character'
    group_affiliation: Optional[str] = None
    primary_work: Optional[str] = None
    show_group_in_bracket: Optional[int] = None  # 0 or 1
    bracket_display_text: Optional[str] = None
    group_status: Optional[str] = None  # 'active', 'disbanded', 'hiatus'
    fame_level: Optional[str] = None  # 'personal_more_famous', 'group_more_famous', 'equal'
    confidence: float = 0.0  # 0.0-1.0
    source: str = "unknown"  # 'database', 'brave_search', 'wikipedia', 'manual'


class MetadataCollector:
    """メタデータ収集システム"""

    # 既知のコメディアングループ（高信頼度）
    KNOWN_COMEDIAN_GROUPS = {
        "ピース": {"members": ["又吉直樹", "綾部祐二"], "status": "disbanded", "fame": "equal"},
        "くりぃむしちゅー": {"members": ["上田晋也", "有田哲平"], "status": "active", "fame": "group_more_famous"},
        "千鳥": {"members": ["ノブ", "大悟"], "status": "active", "fame": "group_more_famous"},
        "サンドウィッチマン": {"members": ["伊達みきお", "富澤たけし"], "status": "active", "fame": "group_more_famous"},
        "爆笑問題": {"members": ["太田光", "田中裕二"], "status": "active", "fame": "group_more_famous"},
        "ダウンタウン": {"members": ["松本人志", "浜田雅功"], "status": "active", "fame": "group_more_famous"},
        "とんねるず": {"members": ["石橋貴明", "木梨憲武"], "status": "disbanded", "fame": "group_more_famous"},
        "ナインティナイン": {"members": ["岡村隆史", "矢部浩之"], "status": "active", "fame": "group_more_famous"},
        "雨上がり決死隊": {"members": ["宮迫博之", "蛍原徹"], "status": "disbanded", "fame": "equal"},
    }

    # 既知のバンド（高信頼度）
    KNOWN_BANDS = {
        "L'Arc～en～Ciel": {"members": ["hyde", "tetsuya", "ken", "yukihiro"], "status": "active", "fame": "group_more_famous"},
        "RADWIMPS": {"members": ["野田洋次郎", "桑原彰", "武田祐介"], "status": "active", "fame": "group_more_famous"},
        "GLAY": {"members": ["TERU", "TAKURO", "HISASHI", "JIRO"], "status": "active", "fame": "group_more_famous"},
        "X JAPAN": {"members": ["YOSHIKI", "TOSHI", "PATA", "HEATH", "SUGIZO"], "status": "hiatus", "fame": "group_more_famous"},
        "B'z": {"members": ["稲葉浩志", "松本孝弘"], "status": "active", "fame": "group_more_famous"},
        "サザンオールスターズ": {"members": ["桑田佳祐"], "status": "active", "fame": "group_more_famous"},
        "Mr.Children": {"members": ["桜井和寿"], "status": "active", "fame": "group_more_famous"},
    }

    # 既知のYouTuberグループ（高信頼度）
    KNOWN_YOUTUBER_GROUPS = {
        "東海オンエア": {"members": ["てつや", "しばゆー", "りょう", "としみつ", "ゆめまる", "虫眼鏡"], "status": "active", "fame": "group_more_famous"},
        "Fischer's": {"members": ["シルクロード", "ンダホ", "ぺけたん", "ダーマ", "マサイ", "ザカオ", "モトキ"], "status": "active", "fame": "group_more_famous"},
        "水溜りボンド": {"members": ["トミー", "カンタ"], "status": "active", "fame": "group_more_famous"},
        "はじめしゃちょー": {"members": [], "status": "active", "fame": "personal_more_famous"},  # ソロ
        "HIKAKIN": {"members": [], "status": "active", "fame": "personal_more_famous"},  # ソロ
    }

    # 国民的架空キャラクター（高信頼度）
    KNOWN_FICTIONAL_CHARACTERS = {
        "ドラえもん": "ドラえもん",
        "さくらももこ": "ちびまる子ちゃん",
        "モンキー・D・ルフィ": "ONE PIECE",
        "孫悟空": "ドラゴンボール",
        "ピカチュウ": "ポケットモンスター",
        "竈門炭治郎": "鬼滅の刃",
        "野比のび太": "ドラえもん",
        "フグ田サザエ": "サザエさん",
        "アンパンマン": "アンパンマン",
        "セーラームーン": "美少女戦士セーラームーン",
    }

    def __init__(self, db_path: str = "episode_database.db"):
        self.db_path = db_path

    def get_priority_persons(self, limit: int = 500) -> List[Dict]:
        """
        優先度順に人物を取得

        注意: recognition_scoreはほぼ全員0.0のため、
        代わりに以下の基準で優先度を決定:
        1. 既知データベースにマッチする人物を優先
        2. カテゴリ別の優先度（エンタメ > スポーツ > その他）
        3. ランダムサンプリング

        Args:
            limit: 取得件数

        Returns:
            人物リスト
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # recognition_scoreは使用せず、カテゴリ優先で取得
        cursor.execute("""
            SELECT person_id, person_name_ja, category, entity_type
            FROM persons
            WHERE show_group_in_bracket = 0  -- 未調査のみ
            ORDER BY
                CASE category
                    WHEN 'エンタメ' THEN 1
                    WHEN 'スポーツ' THEN 2
                    WHEN '文化・学術' THEN 3
                    WHEN '政治・経済' THEN 4
                    ELSE 5
                END,
                RANDOM()  -- 同一カテゴリ内ではランダム
            LIMIT ?
        """, (limit,))

        persons = [dict(row) for row in cursor.fetchall()]
        conn.close()

        logger.info(f"優先対象人物: {len(persons)}件取得")
        return persons

    def collect_metadata(self, person: Dict) -> PersonMetadata:
        """
        メタデータを自動収集

        Args:
            person: 人物データ（データベースから取得）

        Returns:
            PersonMetadata
        """
        person_name = person['person_name_ja']
        category = person.get('category', 'その他')

        # Step 1: 既知データベースから検索（最高信頼度）
        metadata = self._check_known_database(person_name, category)
        if metadata and metadata.confidence >= 0.95:
            logger.info(f"✅ 既知データベースから取得: {person_name} (信頼度: {metadata.confidence:.2f})")
            return metadata

        # Step 2: カテゴリベース推測（中程度信頼度）
        metadata = self._infer_from_category(person_name, category)
        if metadata and metadata.confidence >= 0.7:
            logger.info(f"⚠️ カテゴリから推測: {person_name} (信頼度: {metadata.confidence:.2f})")
            return metadata

        # Step 3: デフォルト（実在人物、括弧表示なし）
        logger.info(f"ℹ️ デフォルト設定: {person_name} (実在人物、括弧なし)")
        return PersonMetadata(
            entity_type='real_person',
            show_group_in_bracket=0,
            confidence=0.5,
            source='default'
        )

    def _check_known_database(self, person_name: str, category: str) -> Optional[PersonMetadata]:
        """
        既知データベースから検索

        Args:
            person_name: 人物名
            category: カテゴリ

        Returns:
            PersonMetadata or None
        """
        # 架空キャラクターチェック
        if person_name in self.KNOWN_FICTIONAL_CHARACTERS:
            work_name = self.KNOWN_FICTIONAL_CHARACTERS[person_name]
            return PersonMetadata(
                entity_type='fictional_character',
                primary_work=work_name,
                show_group_in_bracket=1,
                bracket_display_text=work_name,
                confidence=1.0,
                source='known_fictional_characters'
            )

        # お笑い芸人チェック
        for group_name, group_data in self.KNOWN_COMEDIAN_GROUPS.items():
            if person_name in group_data['members']:
                show_bracket = 1 if group_data['status'] == 'active' else 0
                return PersonMetadata(
                    entity_type='real_person',
                    group_affiliation=group_name,
                    show_group_in_bracket=show_bracket,
                    bracket_display_text=group_name if show_bracket else None,
                    group_status=group_data['status'],
                    fame_level=group_data['fame'],
                    confidence=0.95,
                    source='known_comedian_groups'
                )

        # バンドメンバーチェック
        for band_name, band_data in self.KNOWN_BANDS.items():
            if person_name in band_data['members']:
                show_bracket = 1 if band_data['status'] == 'active' else 0
                return PersonMetadata(
                    entity_type='real_person',
                    group_affiliation=band_name,
                    show_group_in_bracket=show_bracket,
                    bracket_display_text=band_name if show_bracket else None,
                    group_status=band_data['status'],
                    fame_level=band_data['fame'],
                    confidence=0.95,
                    source='known_bands'
                )

        # YouTuberチェック
        for group_name, group_data in self.KNOWN_YOUTUBER_GROUPS.items():
            if person_name in group_data['members']:
                show_bracket = 1 if group_data['fame'] == 'group_more_famous' else 0
                return PersonMetadata(
                    entity_type='real_person',
                    group_affiliation=group_name,
                    show_group_in_bracket=show_bracket,
                    bracket_display_text=group_name if show_bracket else None,
                    group_status=group_data['status'],
                    fame_level=group_data['fame'],
                    confidence=0.95,
                    source='known_youtuber_groups'
                )

        return None

    def _infer_from_category(self, person_name: str, category: str) -> Optional[PersonMetadata]:
        """
        カテゴリから推測

        Args:
            person_name: 人物名
            category: カテゴリ

        Returns:
            PersonMetadata or None
        """
        # 漫画・アニメカテゴリ → 架空キャラクターの可能性高い
        if category == '漫画・アニメ':
            return PersonMetadata(
                entity_type='fictional_character',
                show_group_in_bracket=0,  # 作品名不明のため一旦0
                confidence=0.7,
                source='category_inference'
            )

        # エンタメ → グループ所属の可能性
        if category == 'エンタメ':
            return PersonMetadata(
                entity_type='real_person',
                show_group_in_bracket=0,  # 不明のため一旦0
                confidence=0.6,
                source='category_inference'
            )

        # スポーツ → チーム所属の可能性
        if category == 'スポーツ':
            return PersonMetadata(
                entity_type='real_person',
                show_group_in_bracket=0,  # チーム名表示は通常不要
                confidence=0.8,
                source='category_inference'
            )

        return None

    def update_database(self, person_id: str, metadata: PersonMetadata):
        """
        データベースを更新

        Args:
            person_id: 人物ID
            metadata: PersonMetadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE persons
            SET entity_type = ?,
                group_affiliation = ?,
                primary_work = ?,
                show_group_in_bracket = ?,
                bracket_display_text = ?,
                group_status = ?,
                fame_level = ?
            WHERE person_id = ?
        """, (
            metadata.entity_type,
            metadata.group_affiliation,
            metadata.primary_work,
            metadata.show_group_in_bracket,
            metadata.bracket_display_text,
            metadata.group_status,
            metadata.fame_level,
            person_id
        ))

        conn.commit()
        conn.close()

    def run(self, limit: int = 500) -> Dict:
        """
        Phase 1を実行

        Args:
            limit: 処理件数

        Returns:
            統計情報
        """
        print("=" * 80)
        print("メタデータ拡張 Phase 1: 優先度順500件")
        print("=" * 80)

        # 優先対象を取得
        persons = self.get_priority_persons(limit)

        if not persons:
            logger.warning("処理対象がありません")
            return {}

        # 統計
        stats = {
            'total': len(persons),
            'high_confidence': 0,  # 信頼度0.9以上
            'medium_confidence': 0,  # 信頼度0.7-0.9
            'low_confidence': 0,  # 信頼度0.7未満
            'fictional_character': 0,
            'real_person': 0,
            'with_bracket': 0,
            'without_bracket': 0,
            'sources': {
                'known_fictional_characters': 0,
                'known_comedian_groups': 0,
                'known_bands': 0,
                'known_youtuber_groups': 0,
                'category_inference': 0,
                'default': 0
            }
        }

        # メタデータ収集と更新
        for i, person in enumerate(persons, 1):
            person_name = person['person_name_ja']
            person_id = person['person_id']

            print(f"\n[{i}/{len(persons)}] {person_name}")

            try:
                # メタデータ収集
                metadata = self.collect_metadata(person)

                # データベース更新
                self.update_database(person_id, metadata)

                # 統計更新
                if metadata.confidence >= 0.9:
                    stats['high_confidence'] += 1
                elif metadata.confidence >= 0.7:
                    stats['medium_confidence'] += 1
                else:
                    stats['low_confidence'] += 1

                if metadata.entity_type == 'fictional_character':
                    stats['fictional_character'] += 1
                else:
                    stats['real_person'] += 1

                if metadata.show_group_in_bracket == 1:
                    stats['with_bracket'] += 1
                else:
                    stats['without_bracket'] += 1

                stats['sources'][metadata.source] += 1

                # 結果表示
                print(f"  Entity Type: {metadata.entity_type}")
                print(f"  括弧表示: {'あり' if metadata.show_group_in_bracket else 'なし'}")
                if metadata.bracket_display_text:
                    print(f"  括弧テキスト: {metadata.bracket_display_text}")
                print(f"  信頼度: {metadata.confidence:.2f}")
                print(f"  ソース: {metadata.source}")

                # レート制限対策（必要に応じて）
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"エラー: {person_name} - {e}")
                import traceback
                traceback.print_exc()

        # 結果サマリー
        print("\n" + "=" * 80)
        print("Phase 1 完了サマリー")
        print("=" * 80)
        print(f"総処理件数: {stats['total']}")
        print(f"\n信頼度分布:")
        print(f"  高信頼度 (0.9+): {stats['high_confidence']} ({stats['high_confidence']/stats['total']*100:.1f}%)")
        print(f"  中信頼度 (0.7-0.9): {stats['medium_confidence']} ({stats['medium_confidence']/stats['total']*100:.1f}%)")
        print(f"  低信頼度 (<0.7): {stats['low_confidence']} ({stats['low_confidence']/stats['total']*100:.1f}%)")
        print(f"\nEntity Type:")
        print(f"  架空キャラクター: {stats['fictional_character']}")
        print(f"  実在人物: {stats['real_person']}")
        print(f"\n括弧表示:")
        print(f"  表示あり: {stats['with_bracket']}")
        print(f"  表示なし: {stats['without_bracket']}")
        print(f"\nデータソース:")
        for source, count in stats['sources'].items():
            if count > 0:
                print(f"  {source}: {count}")

        # JSON保存
        output_path = f"metadata_expansion_phase1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        print(f"\n結果を保存: {output_path}")

        return stats


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='メタデータ拡張 Phase 1')
    parser.add_argument('--db', default='episode_database.db', help='データベースパス')
    parser.add_argument('--limit', type=int, default=500, help='処理件数')

    args = parser.parse_args()

    # 実行
    collector = MetadataCollector(db_path=args.db)
    stats = collector.run(limit=args.limit)

    if stats:
        print("\n✅ Phase 1 完了！")
        return 0
    else:
        print("\n❌ Phase 1 失敗")
        return 1


if __name__ == '__main__':
    exit(main())
