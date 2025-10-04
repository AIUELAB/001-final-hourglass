#!/usr/bin/env python3
"""
Phase 1: パイロット対象人物選定スクリプト

15-20人の多様な人物を選定し、エピソード生成のパイロット運用を開始します。

選定基準:
1. 多様性の確保（各カテゴリから代表的人物）
2. 知名度レベルの分散（超有名〜やや低いまで）
3. データ品質の確保（Wikipedia記事あり、birth_year確定）
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class PilotPersonSelector:
    """パイロット対象人物選定クラス"""

    def __init__(self, db_path: str = "episode_database.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_category_distribution(self) -> Dict[str, int]:
        """カテゴリ別人物数を取得"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM persons
            WHERE person_id NOT IN (SELECT DISTINCT person_id FROM episodes)
            GROUP BY category
            ORDER BY count DESC
        """)
        return {row['category']: row['count'] for row in cursor.fetchall()}

    def select_diverse_sample(self) -> List[Dict[str, Any]]:
        """
        多様性を確保したサンプル選定

        各カテゴリから代表的人物を選定：
        - スポーツ: 2-3人
        - エンタメ: 2-3人
        - 政治: 1-2人
        - 文化・芸術: 1-2人
        - 科学・技術: 1-2人
        - 歴史: 1-2人
        - 架空キャラクター: 1人（いれば）
        - その他: 2-3人
        """
        cursor = self.conn.cursor()

        # カテゴリ別選定数
        category_targets = {
            'スポーツ': 3,
            'エンタメ': 3,
            '政治': 2,
            '文化・芸術': 2,
            '学術・科学': 1,
            'テクノロジー': 1,
            '歴史': 2,
            '架空の存在': 1,
            'その他': 2,
        }

        selected_persons = []

        for category, target_count in category_targets.items():
            # 知名度レベルを分散させるため、異なるスコア帯から選定
            # 超有名（9.0以上）、有名（7.0-9.0）、一般的（5.0-7.0）、やや低い（5.0未満）

            query = """
                SELECT
                    person_id,
                    person_name_ja,
                    person_name_en,
                    category,
                    recognition_score,
                    birth_year,
                    entity_type
                FROM persons
                WHERE category = ?
                  AND person_id NOT IN (SELECT DISTINCT person_id FROM episodes)
                  AND birth_year IS NOT NULL
                ORDER BY recognition_score DESC
                LIMIT ?
            """

            cursor.execute(query, (category, target_count))
            rows = cursor.fetchall()

            for row in rows:
                selected_persons.append({
                    'person_id': row['person_id'],
                    'person_name_ja': row['person_name_ja'],
                    'person_name_en': row['person_name_en'],
                    'category': row['category'],
                    'recognition_score': row['recognition_score'],
                    'birth_year': row['birth_year'],
                    'entity_type': row['entity_type'],
                })

        return selected_persons

    def add_recognition_score_diversity(self, current_selection: List[Dict]) -> List[Dict]:
        """
        知名度スコアの多様性を追加

        現在の選定リストに加えて、異なる知名度レベルの人物を追加
        """
        cursor = self.conn.cursor()

        # スコア帯別の追加人数
        score_ranges = [
            (9.0, 10.0, 2),   # 超有名
            (7.0, 9.0, 2),    # 有名
            (5.0, 7.0, 2),    # 一般的
            (0.0, 5.0, 2),    # やや低い
        ]

        # 既存の選定IDを除外
        existing_ids = [p['person_id'] for p in current_selection]

        additional_persons = []

        for min_score, max_score, count in score_ranges:
            query = """
                SELECT
                    person_id,
                    person_name_ja,
                    person_name_en,
                    category,
                    recognition_score,
                    birth_year,
                    entity_type
                FROM persons
                WHERE person_id NOT IN (SELECT DISTINCT person_id FROM episodes)
                  AND person_id NOT IN ({placeholders})
                  AND recognition_score >= ?
                  AND recognition_score < ?
                  AND birth_year IS NOT NULL
                ORDER BY RANDOM()
                LIMIT ?
            """.format(placeholders=','.join('?' * len(existing_ids)))

            cursor.execute(query, existing_ids + [min_score, max_score, count])
            rows = cursor.fetchall()

            for row in rows:
                person = {
                    'person_id': row['person_id'],
                    'person_name_ja': row['person_name_ja'],
                    'person_name_en': row['person_name_en'],
                    'category': row['category'],
                    'recognition_score': row['recognition_score'],
                    'birth_year': row['birth_year'],
                    'entity_type': row['entity_type'],
                }
                additional_persons.append(person)
                existing_ids.append(person['person_id'])

        return additional_persons

    def validate_selection(self, persons: List[Dict]) -> Dict[str, Any]:
        """選定結果の検証"""
        validation = {
            'total_count': len(persons),
            'category_distribution': {},
            'score_distribution': {
                'super_famous': 0,  # 9.0以上
                'famous': 0,         # 7.0-9.0
                'general': 0,        # 5.0-7.0
                'lower': 0,          # 5.0未満
            },
            'entity_type_distribution': {},
            'has_birth_year': 0,
            'missing_birth_year': 0,
        }

        for person in persons:
            # カテゴリ分布
            category = person['category']
            validation['category_distribution'][category] = \
                validation['category_distribution'].get(category, 0) + 1

            # スコア分布
            score = person['recognition_score'] or 0.0
            if score >= 9.0:
                validation['score_distribution']['super_famous'] += 1
            elif score >= 7.0:
                validation['score_distribution']['famous'] += 1
            elif score >= 5.0:
                validation['score_distribution']['general'] += 1
            else:
                validation['score_distribution']['lower'] += 1

            # エンティティタイプ分布
            entity_type = person['entity_type']
            validation['entity_type_distribution'][entity_type] = \
                validation['entity_type_distribution'].get(entity_type, 0) + 1

            # 生年確認
            if person['birth_year']:
                validation['has_birth_year'] += 1
            else:
                validation['missing_birth_year'] += 1

        return validation

    def save_selection(self, persons: List[Dict], output_path: str = "phase1_pilot_persons.json"):
        """選定結果を保存"""
        output = {
            'metadata': {
                'phase': 'Phase 1 - Pilot',
                'created_at': datetime.now().isoformat(),
                'total_count': len(persons),
                'target_range': '15-20 persons',
            },
            'validation': self.validate_selection(persons),
            'persons': persons,
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ 選定結果を保存: {output_path}")
        return output

    def print_summary(self, selection_output: Dict):
        """選定サマリーを表示"""
        metadata = selection_output['metadata']
        validation = selection_output['validation']
        persons = selection_output['persons']

        print("\n" + "=" * 60)
        print("  Phase 1: パイロット対象人物選定結果")
        print("=" * 60)
        print(f"\n📊 総選定数: {metadata['total_count']}人")

        print(f"\n📂 カテゴリ別分布:")
        for category, count in validation['category_distribution'].items():
            print(f"   - {category}: {count}人")

        print(f"\n⭐ 知名度レベル分布:")
        print(f"   - 超有名（9.0以上）: {validation['score_distribution']['super_famous']}人")
        print(f"   - 有名（7.0-9.0）: {validation['score_distribution']['famous']}人")
        print(f"   - 一般的（5.0-7.0）: {validation['score_distribution']['general']}人")
        print(f"   - やや低い（5.0未満）: {validation['score_distribution']['lower']}人")

        print(f"\n🏷️ エンティティタイプ分布:")
        for entity_type, count in validation['entity_type_distribution'].items():
            print(f"   - {entity_type}: {count}人")

        print(f"\n📅 生年データ:")
        print(f"   - 生年確定: {validation['has_birth_year']}人")
        print(f"   - 生年不明: {validation['missing_birth_year']}人")

        print(f"\n👥 選定された人物リスト:")
        for i, person in enumerate(persons, 1):
            print(f"   {i:2d}. {person['person_name_ja']:<20} "
                  f"（{person['category']:<15} / スコア: {person['recognition_score']:.1f}）")

        print("\n" + "=" * 60)
        print("  次のステップ:")
        print("=" * 60)
        print("  1. 選定結果を確認")
        print("  2. エピソード生成エンジンの準備")
        print("  3. 最初のエピソード生成開始")
        print("=" * 60 + "\n")

    def close(self):
        """データベース接続を閉じる"""
        self.conn.close()


def main():
    """メイン処理"""
    print("=" * 60)
    print("  Phase 1: パイロット対象人物選定")
    print("=" * 60)
    print()

    # 選定クラス初期化
    selector = PilotPersonSelector()

    # Step 1: カテゴリ分布確認
    print("📊 カテゴリ別人物数:")
    category_dist = selector.get_category_distribution()
    for category, count in list(category_dist.items())[:10]:
        print(f"   - {category}: {count}人")
    print()

    # Step 2: 多様性を確保したサンプル選定
    print("🔍 多様性を確保したサンプル選定中...")
    diverse_sample = selector.select_diverse_sample()
    print(f"   ✅ 初期選定: {len(diverse_sample)}人")

    # Step 3: 知名度スコアの多様性追加
    print("⭐ 知名度レベルの多様性を追加中...")
    additional = selector.add_recognition_score_diversity(diverse_sample)
    print(f"   ✅ 追加選定: {len(additional)}人")

    # Step 4: 結合
    all_selected = diverse_sample + additional
    print(f"   ✅ 合計選定: {len(all_selected)}人")

    # Step 5: 目標範囲内に調整（15-20人）
    if len(all_selected) > 20:
        print(f"   ⚠️ 選定数が20人を超過。上位20人に絞り込みます。")
        # 知名度スコア順にソート
        all_selected.sort(key=lambda x: x['recognition_score'] or 0, reverse=True)
        all_selected = all_selected[:20]
    elif len(all_selected) < 15:
        print(f"   ⚠️ 選定数が15人未満。追加選定が必要です。")

    # Step 6: 検証
    print("\n🔍 選定結果の検証中...")
    validation = selector.validate_selection(all_selected)

    # Step 7: 保存
    output = selector.save_selection(all_selected)

    # Step 8: サマリー表示
    selector.print_summary(output)

    # クリーンアップ
    selector.close()

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
