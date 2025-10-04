#!/usr/bin/env python3
"""
バンド・YouTuber情報収集スクリプト

目的:
1. データベース内のミュージシャン（バンドメンバー）のグループ情報を自動収集
2. YouTuberのグループ情報を自動収集
3. 活動状態、知名度レベルを判定

データソース:
- 既知のバンド・YouTuberグループデータベース
- カテゴリ情報からの推定
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ================================================================================
# 既知のバンド・YouTuberグループデータベース
# ================================================================================

BAND_GROUPS_DATABASE = {
    # ロックバンド（現役）
    'ONE OK ROCK': {
        'members': ['Taka', 'Toru', 'Ryota', 'Tomoya'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'genre': 'rock',
        'debut_year': 2005
    },
    'RADWIMPS': {
        'members': ['野田洋次郎', '桑原彰', '武田祐介'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'genre': 'rock',
        'debut_year': 2001
    },
    'back number': {
        'members': ['清水依与吏', '小島和也', '栗原寿'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'genre': 'rock',
        'debut_year': 2004
    },
    'Official髭男dism': {
        'members': ['藤原聡', '小笹大輔', '楢﨑誠', '松浦匡希'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'genre': 'rock',
        'debut_year': 2012
    },

    # 解散バンド（有名）
    'X JAPAN': {
        'members': ['YOSHIKI', 'TOSHI', 'PATA', 'HEATH', 'HIDE'],
        'status': 'disbanded',
        'fame_level': 'personal_more_famous',  # YOSHIKIの個人知名度が高い
        'genre': 'rock',
        'debut_year': 1982
    },
    'LUNA SEA': {
        'members': ['RYUICHI', 'SUGIZO', 'INORAN', 'J', '真矢'],
        'status': 'active',  # 再結成
        'fame_level': 'group_more_famous',
        'genre': 'rock',
        'debut_year': 1989
    },
    'L\'Arc～en～Ciel': {
        'members': ['hyde', 'tetsuya', 'ken', 'yukihiro'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'genre': 'rock',
        'debut_year': 1991
    },
    'GLAY': {
        'members': ['TERU', 'TAKURO', 'HISASHI', 'JIRO'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'genre': 'rock',
        'debut_year': 1988
    },

    # アイドルグループ
    '嵐': {
        'members': ['大野智', '櫻井翔', '相葉雅紀', '二宮和也', '松本潤'],
        'status': 'hiatus',  # 活動休止中
        'fame_level': 'group_more_famous',
        'genre': 'idol',
        'debut_year': 1999
    },
    'SMAP': {
        'members': ['中居正広', '木村拓哉', '稲垣吾郎', '草彅剛', '香取慎吾'],
        'status': 'disbanded',
        'fame_level': 'personal_more_famous',  # 木村拓哉等個人が有名
        'genre': 'idol',
        'debut_year': 1988
    },

    # K-POPグループ
    'BTS': {
        'members': ['RM', 'ジン', 'SUGA', 'J-HOPE', 'ジミン', 'V', 'ジョングク'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'genre': 'kpop',
        'debut_year': 2013
    },
    'BLACKPINK': {
        'members': ['ジス', 'ジェニー', 'ロゼ', 'リサ'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'genre': 'kpop',
        'debut_year': 2016
    }
}

YOUTUBER_GROUPS_DATABASE = {
    # YouTuberグループ
    'HIKAKIN & SEIKIN': {
        'members': ['HIKAKIN', 'SEIKIN'],
        'status': 'active',
        'fame_level': 'personal_more_famous',  # HIKAKINの個人チャンネルが圧倒的
        'channel_type': 'variety',
        'debut_year': 2010
    },
    'Fischer\'s': {
        'members': ['シルクロード', 'ンダホ', 'ぺけたん', 'ダーマ', 'マサイ', 'モトキ', 'ザカオ'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'channel_type': 'variety',
        'debut_year': 2012
    },
    '東海オンエア': {
        'members': ['てつや', 'しばゆー', 'りょう', 'としみつ', 'ゆめまる', '虫眼鏡'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'channel_type': 'variety',
        'debut_year': 2013
    },
    'はじめしゃちょー&もやし': {
        'members': ['はじめしゃちょー', 'もやし'],
        'status': 'active',
        'fame_level': 'personal_more_famous',  # はじめしゃちょーの個人が圧倒的
        'channel_type': 'variety',
        'debut_year': 2012
    }
}


# ================================================================================
# データクラス
# ================================================================================

@dataclass
class BandYouTuberGroupInfo:
    """バンド・YouTuberグループ情報"""
    group_name: str
    group_status: str              # active / disbanded / hiatus
    fame_level: str                # personal_more_famous / group_more_famous / equal
    show_group_in_bracket: int     # 0 or 1
    bracket_display_text: str
    confidence: float              # 確信度
    data_source: str               # データソース
    group_type: str                # band / youtuber


# ================================================================================
# バンド・YouTuber情報収集エンジン
# ================================================================================

class BandYouTuberInfoCollector:
    """バンド・YouTuber情報収集エンジン"""

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__ + '.BandYouTuberInfoCollector')

        # メンバー名→グループ名のマッピング作成
        self.member_to_band = {}
        for group_name, group_data in BAND_GROUPS_DATABASE.items():
            for member in group_data['members']:
                self.member_to_band[member] = group_name

        self.member_to_youtuber = {}
        for group_name, group_data in YOUTUBER_GROUPS_DATABASE.items():
            for member in group_data['members']:
                self.member_to_youtuber[member] = group_name

    def collect_for_musician(self, person_name: str) -> Optional[BandYouTuberGroupInfo]:
        """
        ミュージシャンのバンド情報を収集

        Args:
            person_name: ミュージシャン名

        Returns:
            BandYouTuberGroupInfo or None
        """
        group_name = self.member_to_band.get(person_name)

        if not group_name:
            return None

        group_data = BAND_GROUPS_DATABASE[group_name]
        show_bracket = self._should_show_bracket(group_data)

        return BandYouTuberGroupInfo(
            group_name=group_name,
            group_status=group_data['status'],
            fame_level=group_data['fame_level'],
            show_group_in_bracket=1 if show_bracket else 0,
            bracket_display_text=group_name if show_bracket else '',
            confidence=0.95,
            data_source='known_database',
            group_type='band'
        )

    def collect_for_youtuber(self, person_name: str) -> Optional[BandYouTuberGroupInfo]:
        """
        YouTuberのグループ情報を収集

        Args:
            person_name: YouTuber名

        Returns:
            BandYouTuberGroupInfo or None
        """
        group_name = self.member_to_youtuber.get(person_name)

        if not group_name:
            return None

        group_data = YOUTUBER_GROUPS_DATABASE[group_name]
        show_bracket = self._should_show_bracket(group_data)

        return BandYouTuberGroupInfo(
            group_name=group_name,
            group_status=group_data['status'],
            fame_level=group_data['fame_level'],
            show_group_in_bracket=1 if show_bracket else 0,
            bracket_display_text=group_name if show_bracket else '',
            confidence=0.95,
            data_source='known_database',
            group_type='youtuber'
        )

    def _should_show_bracket(self, group_data: Dict) -> bool:
        """
        括弧表示判定

        Args:
            group_data: グループデータ

        Returns:
            表示するかどうか
        """
        # Rule 1: 解散済み・活動休止中は表示しない
        if group_data['status'] in ['disbanded', 'hiatus']:
            return False

        # Rule 2: 本人の方が有名な場合は表示しない
        if group_data['fame_level'] == 'personal_more_famous':
            return False

        # Rule 3: 活動中かつグループが有名 or 同等 → 表示
        if group_data['status'] == 'active':
            if group_data['fame_level'] in ['group_more_famous', 'equal']:
                return True

        return False

    def collect_batch_from_database(
        self,
        db_path: str = "episode_database.db"
    ) -> List[Dict]:
        """
        データベースからミュージシャン・YouTuberを抽出してバッチ収集

        Args:
            db_path: データベースパス

        Returns:
            収集結果リスト
        """
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 全データ取得
        cursor.execute("""
            SELECT person_id, person_name_ja, category
            FROM persons
            ORDER BY recognition_score DESC
        """)

        persons = cursor.fetchall()
        conn.close()

        self.logger.info(f"全人物数: {len(persons)}件")

        # バッチ収集
        results = []
        for person in persons:
            person_name = person['person_name_ja']

            # ミュージシャン判定
            group_info = self.collect_for_musician(person_name)
            if group_info:
                results.append({
                    'person_id': person['person_id'],
                    'person_name': person_name,
                    'category': person['category'],
                    'group_name': group_info.group_name,
                    'group_status': group_info.group_status,
                    'fame_level': group_info.fame_level,
                    'show_group_in_bracket': group_info.show_group_in_bracket,
                    'bracket_display_text': group_info.bracket_display_text,
                    'confidence': group_info.confidence,
                    'data_source': group_info.data_source,
                    'group_type': group_info.group_type
                })
                continue

            # YouTuber判定
            group_info = self.collect_for_youtuber(person_name)
            if group_info:
                results.append({
                    'person_id': person['person_id'],
                    'person_name': person_name,
                    'category': person['category'],
                    'group_name': group_info.group_name,
                    'group_status': group_info.group_status,
                    'fame_level': group_info.fame_level,
                    'show_group_in_bracket': group_info.show_group_in_bracket,
                    'bracket_display_text': group_info.bracket_display_text,
                    'confidence': group_info.confidence,
                    'data_source': group_info.data_source,
                    'group_type': group_info.group_type
                })

        return results


# ================================================================================
# レポート生成
# ================================================================================

def print_band_youtuber_report(results: List[Dict]):
    """バンド・YouTuber情報レポート"""
    print("="*80)
    print("バンド・YouTuber情報収集レポート")
    print("="*80)

    total = len(results)
    band_count = sum(1 for r in results if r['group_type'] == 'band')
    youtuber_count = sum(1 for r in results if r['group_type'] == 'youtuber')
    show_bracket = sum(1 for r in results if r['show_group_in_bracket'] == 1)

    print(f"\n総処理件数: {total}")
    print(f"バンドメンバー: {band_count}件")
    print(f"YouTuberグループ: {youtuber_count}件")
    print(f"括弧表示対象: {show_bracket}件")

    # グループ別集計
    print(f"\n【グループ別集計】")
    group_counts = {}
    for result in results:
        group_name = result['group_name']
        group_counts[group_name] = group_counts.get(group_name, 0) + 1

    for group_name, count in sorted(group_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {group_name}: {count}名")

    # 括弧表示対象一覧
    print(f"\n【括弧表示対象一覧】")
    bracket_results = [r for r in results if r['show_group_in_bracket'] == 1]

    for i, result in enumerate(bracket_results, 1):
        group_type_label = "バンド" if result['group_type'] == 'band' else "YouTuber"
        print(f"{i:2d}. {result['person_name']:<20} ({result['bracket_display_text']:<25}) [{group_type_label}]")

    # 非表示理由の統計
    print(f"\n【括弧非表示の理由】")
    no_bracket_results = [r for r in results if r['show_group_in_bracket'] == 0]

    disbanded_count = sum(1 for r in no_bracket_results if r['group_status'] == 'disbanded')
    hiatus_count = sum(1 for r in no_bracket_results if r['group_status'] == 'hiatus')
    personal_famous_count = sum(1 for r in no_bracket_results if r['fame_level'] == 'personal_more_famous')

    print(f"  解散済み: {disbanded_count}件")
    print(f"  活動休止: {hiatus_count}件")
    print(f"  本人の方が有名: {personal_famous_count}件")


# ================================================================================
# メイン処理
# ================================================================================

def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='バンド・YouTuber情報収集')
    parser.add_argument('--db', default='episode_database.db', help='データベースパス')
    parser.add_argument('--output', default='band_youtuber_info.json', help='出力JSONパス')

    args = parser.parse_args()

    print("="*80)
    print("バンド・YouTuber情報収集スクリプト")
    print("="*80)
    print(f"データベース: {args.db}")
    print(f"出力先: {args.output}\n")

    # 収集実行
    collector = BandYouTuberInfoCollector()
    results = collector.collect_batch_from_database(args.db)

    # レポート表示
    print_band_youtuber_report(results)

    # JSON保存
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 収集結果を保存: {args.output}")


if __name__ == '__main__':
    main()
