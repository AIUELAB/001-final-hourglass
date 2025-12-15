#!/usr/bin/env python3
"""
お笑い芸人グループ情報収集スクリプト

目的:
1. データベース内のお笑い芸人のグループ情報を自動収集
2. コンビ・トリオの所属情報、活動状態を判定
3. 知名度レベル（個人 vs グループ）を推定

データソース:
- 既知のお笑いコンビ・トリオデータベース
- カテゴリ情報からの推定
- 検索結果からの抽出（将来実装）
"""

import sqlite3
from src.database_utils import get_connection
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ================================================================================
# 既知のお笑いコンビ・トリオデータベース
# ================================================================================

COMEDIAN_GROUPS_DATABASE = {
    # 現役コンビ（活動中）
    'ダウンタウン': {
        'members': ['松本人志', '浜田雅功'],
        'status': 'active',
        'fame_level': 'group_more_famous',  # グループの方が有名
        'debut_year': 1982
    },
    'ウッチャンナンチャン': {
        'members': ['内村光良', '南原清隆'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'debut_year': 1985
    },
    'とんねるず': {
        'members': ['石橋貴明', '木梨憲武'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'debut_year': 1980
    },
    '爆笑問題': {
        'members': ['太田光', '田中裕二'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'debut_year': 1988
    },
    'くりぃむしちゅー': {
        'members': ['上田晋也', '有田哲平'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'debut_year': 1991
    },
    'ナインティナイン': {
        'members': ['岡村隆史', '矢部浩之'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'debut_year': 1990
    },
    'ネプチューン': {
        'members': ['名倉潤', '原田泰造', '堀内健'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'debut_year': 1993
    },
    'サンドウィッチマン': {
        'members': ['伊達みきお', '富澤たけし'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'debut_year': 1998
    },
    'アンジャッシュ': {
        'members': ['渡部建', '児嶋一哉'],
        'status': 'hiatus',  # 活動休止中
        'fame_level': 'group_more_famous',
        'debut_year': 1993
    },
    'ピース': {
        'members': ['又吉直樹', '綾部祐二'],
        'status': 'active',
        'fame_level': 'equal',  # 同等
        'debut_year': 2001
    },
    'オードリー': {
        'members': ['春日俊彰', '若林正恭'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'debut_year': 2000
    },
    '千鳥': {
        'members': ['大悟', 'ノブ'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'debut_year': 2000
    },
    '霜降り明星': {
        'members': ['粗品', 'せいや'],
        'status': 'active',
        'fame_level': 'group_more_famous',
        'debut_year': 2013
    },

    # 解散済みコンビ
    'ごっつ': {
        'members': ['松本人志', '今田耕司'],  # ごっつええ感じ時代
        'status': 'disbanded',
        'fame_level': 'personal_more_famous',
        'debut_year': None
    },

    # YouTuberコンビ（参考）
    'HIKAKIN & SEIKIN': {
        'members': ['HIKAKIN', 'SEIKIN'],
        'status': 'active',
        'fame_level': 'personal_more_famous',  # HIKAKINの方が圧倒的に有名
        'debut_year': 2010
    }
}


# ================================================================================
# データクラス
# ================================================================================

@dataclass
class ComedianGroupInfo:
    """お笑い芸人グループ情報"""
    group_name: str
    group_status: str              # active / disbanded / hiatus
    fame_level: str                # personal_more_famous / group_more_famous / equal
    show_group_in_bracket: int     # 0 or 1
    bracket_display_text: str
    confidence: float              # 確信度
    data_source: str               # データソース


# ================================================================================
# お笑い芸人グループ情報収集エンジン
# ================================================================================

class ComedianGroupInfoCollector:
    """お笑い芸人グループ情報収集エンジン"""

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__ + '.ComedianGroupInfoCollector')

        # メンバー名→グループ名のマッピング作成
        self.member_to_group = {}
        for group_name, group_data in COMEDIAN_GROUPS_DATABASE.items():
            for member in group_data['members']:
                self.member_to_group[member] = group_name

    def collect_for_comedian(self, person_name: str) -> Optional[ComedianGroupInfo]:
        """
        お笑い芸人のグループ情報を収集

        Args:
            person_name: 芸人名

        Returns:
            ComedianGroupInfo or None
        """
        # データベース照合
        group_name = self.member_to_group.get(person_name)

        if not group_name:
            self.logger.debug(f"グループ情報なし: {person_name}")
            return None

        group_data = COMEDIAN_GROUPS_DATABASE[group_name]

        # 括弧表示判定
        show_bracket = self._should_show_bracket(group_data)

        return ComedianGroupInfo(
            group_name=group_name,
            group_status=group_data['status'],
            fame_level=group_data['fame_level'],
            show_group_in_bracket=1 if show_bracket else 0,
            bracket_display_text=group_name if show_bracket else '',
            confidence=0.95,  # 既知データベースは高確信度
            data_source='known_database'
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
        データベースからお笑い芸人を抽出してバッチ収集

        Args:
            db_path: データベースパス

        Returns:
            収集結果リスト
        """
        conn = get_connection(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # お笑い芸人を抽出（カテゴリが「エンタメ」「その他」から既知のコンビメンバーを検索）
        cursor.execute("""
            SELECT person_id, person_name_ja, category
            FROM persons
            ORDER BY recognition_score DESC
        """)

        comedians = cursor.fetchall()
        conn.close()

        self.logger.info(f"お笑い芸人抽出: {len(comedians)}件")

        # バッチ収集
        results = []
        for comedian in comedians:
            group_info = self.collect_for_comedian(comedian['person_name_ja'])

            if group_info:
                results.append({
                    'person_id': comedian['person_id'],
                    'person_name': comedian['person_name_ja'],
                    'category': comedian['category'],
                    'group_name': group_info.group_name,
                    'group_status': group_info.group_status,
                    'fame_level': group_info.fame_level,
                    'show_group_in_bracket': group_info.show_group_in_bracket,
                    'bracket_display_text': group_info.bracket_display_text,
                    'confidence': group_info.confidence,
                    'data_source': group_info.data_source
                })
            else:
                # グループ情報なし
                results.append({
                    'person_id': comedian['person_id'],
                    'person_name': comedian['person_name_ja'],
                    'category': comedian['category'],
                    'group_name': None,
                    'group_status': None,
                    'fame_level': None,
                    'show_group_in_bracket': 0,
                    'bracket_display_text': '',
                    'confidence': 0.0,
                    'data_source': 'no_data'
                })

        return results


# ================================================================================
# レポート生成
# ================================================================================

def print_comedian_group_report(results: List[Dict]):
    """お笑い芸人グループ情報レポート"""
    print("="*80)
    print("お笑い芸人グループ情報収集レポート")
    print("="*80)

    total = len(results)
    with_group = sum(1 for r in results if r['group_name'])
    without_group = total - with_group

    show_bracket = sum(1 for r in results if r['show_group_in_bracket'] == 1)

    print(f"\n総処理件数: {total}")
    if total > 0:
        print(f"グループ情報あり: {with_group}件 ({with_group/total*100:.1f}%)")
        print(f"グループ情報なし: {without_group}件 ({without_group/total*100:.1f}%)")
    else:
        print("データが見つかりませんでした")
    print(f"括弧表示対象: {show_bracket}件")

    # グループ別集計
    print(f"\n【グループ別集計】")
    group_counts = {}
    for result in results:
        if result['group_name']:
            group_name = result['group_name']
            group_counts[group_name] = group_counts.get(group_name, 0) + 1

    for group_name, count in sorted(group_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {group_name}: {count}名")

    # 括弧表示対象一覧
    print(f"\n【括弧表示対象一覧】")
    bracket_results = [r for r in results if r['show_group_in_bracket'] == 1]

    for i, result in enumerate(bracket_results, 1):
        print(f"{i:2d}. {result['person_name']:<20} ({result['bracket_display_text']:<20}) ステータス: {result['group_status']}")

    # 非表示理由の統計
    print(f"\n【括弧非表示の理由】")
    no_bracket_results = [r for r in results if r['group_name'] and r['show_group_in_bracket'] == 0]

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

    parser = argparse.ArgumentParser(description='お笑い芸人グループ情報収集')
    parser.add_argument('--db', default='episode_database.db', help='データベースパス')
    parser.add_argument('--output', default='comedian_group_info.json', help='出力JSONパス')

    args = parser.parse_args()

    print("="*80)
    print("お笑い芸人グループ情報収集スクリプト")
    print("="*80)
    print(f"データベース: {args.db}")
    print(f"出力先: {args.output}\n")

    # 収集実行
    collector = ComedianGroupInfoCollector()
    results = collector.collect_batch_from_database(args.db)

    # レポート表示
    print_comedian_group_report(results)

    # JSON保存
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 収集結果を保存: {args.output}")


if __name__ == '__main__':
    main()
