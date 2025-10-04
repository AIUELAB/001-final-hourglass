#!/usr/bin/env python3
"""
カテゴリベース候補選択器
Category-Based Candidate Selector

recognition_scoreが機能していないため、カテゴリと人物名の知名度で選定

日本の超有名人リストを活用:
- スポーツ: イチロー、大谷翔平、羽生結弦、本田圭佑等
- 経営者: 松下幸之助、本田宗一郎、稲盛和夫等
- エンタメ: 新垣結衣、綾瀬はるか、北野武等
- 政治: 安倍晋三、小泉純一郎等

Created: 2025-10-02
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import csv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TargetPerson:
    """対象人物"""
    name: str
    category: str
    priority: int  # 1=最優先, 2=優先, 3=通常


class CategoryBasedCandidateSelector:
    """カテゴリベース候補選択器"""

    # 日本の超有名人リスト（Phase 3テストで使用した人物を参考）
    FAMOUS_JAPANESE_PERSONS = [
        # スポーツ（最優先）
        TargetPerson("イチロー", "スポーツ", 1),
        TargetPerson("大谷翔平", "スポーツ", 1),
        TargetPerson("羽生結弦", "スポーツ", 1),
        TargetPerson("本田圭佑", "スポーツ", 1),
        TargetPerson("錦織圭", "スポーツ", 1),
        TargetPerson("久保建英", "スポーツ", 1),
        TargetPerson("八村塁", "スポーツ", 2),
        TargetPerson("渡辺雄太", "スポーツ", 2),
        TargetPerson("北島康介", "スポーツ", 2),
        TargetPerson("高橋尚子", "スポーツ", 2),

        # 経営者・イノベーター（最優先）
        TargetPerson("松下幸之助", "ビジネス", 1),
        TargetPerson("本田宗一郎", "ビジネス", 1),
        TargetPerson("稲盛和夫", "ビジネス", 1),
        TargetPerson("孫正義", "ビジネス", 1),
        TargetPerson("堀江貴文", "ビジネス", 1),
        TargetPerson("前澤友作", "ビジネス", 2),

        # エンタメ（優先）
        TargetPerson("新垣結衣", "エンタメ", 1),
        TargetPerson("綾瀬はるか", "エンタメ", 2),
        TargetPerson("北野武", "エンタメ", 1),
        TargetPerson("宮崎駿", "エンタメ", 1),
        TargetPerson("松本人志", "エンタメ", 2),
        TargetPerson("ダウンタウン", "エンタメ", 2),

        # 文化・芸術（優先）
        TargetPerson("村上春樹", "文化・芸術", 1),
        TargetPerson("手塚治虫", "文化・芸術", 1),
        TargetPerson("黒澤明", "文化・芸術", 1),
        TargetPerson("坂本龍一", "文化・芸術", 2),

        # 政治（通常）
        TargetPerson("安倍晋三", "政治", 2),
        TargetPerson("小泉純一郎", "政治", 2),
        TargetPerson("菅義偉", "政治", 3),
    ]

    def __init__(self, db_path: str = "episode_database.db"):
        self.db_path = db_path

    def select_from_database(self, max_candidates: int = 50) -> List[Dict]:
        """データベースから有名人を選定"""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        selected = []
        found_names = set()

        # 優先度順に選定
        for priority in [1, 2, 3]:
            if len(selected) >= max_candidates:
                break

            priority_persons = [p for p in self.FAMOUS_JAPANESE_PERSONS if p.priority == priority]

            for target in priority_persons:
                if len(selected) >= max_candidates:
                    break

                # データベースから検索（部分一致）
                query = """
                    SELECT person_id, person_name_ja, person_name_en, birth_year, category
                    FROM persons
                    WHERE person_name_ja LIKE ?
                    AND birth_year IS NOT NULL
                """
                cursor.execute(query, (f"%{target.name}%",))
                rows = cursor.fetchall()

                for row in rows:
                    person = dict(row)
                    person_name = person['person_name_ja']

                    # 重複チェック
                    if person_name not in found_names:
                        person['priority'] = target.priority
                        person['target_category'] = target.category
                        selected.append(person)
                        found_names.add(person_name)

                        logger.info(f"  選定: {person_name} (優先度: {target.priority})")

        conn.close()

        logger.info(f"✅ 選定完了: {len(selected)}名")
        return selected

    def export_to_csv(self, persons: List[Dict], output_path: str):
        """CSV出力（UTF-8 BOM）"""

        fieldnames = ['person_id', 'person_name_ja', 'birth_year', 'category', 'priority']

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for person in persons:
                writer.writerow({
                    'person_id': person['person_id'],
                    'person_name_ja': person['person_name_ja'],
                    'birth_year': person['birth_year'],
                    'category': person['category'],
                    'priority': person.get('priority', 3)
                })

        logger.info(f"💾 CSV出力: {output_path}")


def main():
    """テスト実行"""
    selector = CategoryBasedCandidateSelector()

    logger.info(f"🔍 有名人選定開始")
    persons = selector.select_from_database(max_candidates=50)

    # 統計
    logger.info(f"\n📊 選定結果:")
    logger.info(f"総数: {len(persons)}名")

    # 優先度別
    for priority in [1, 2, 3]:
        count = sum(1 for p in persons if p.get('priority') == priority)
        logger.info(f"  優先度{priority}: {count}名")

    # CSV出力
    selector.export_to_csv(persons, "famous_persons_selected.csv")

    # トップ20表示
    logger.info(f"\nトップ20:")
    for i, p in enumerate(persons[:20], 1):
        logger.info(f"  {i}. {p['person_name_ja']} ({p['birth_year']}年, {p['category']})")

    logger.info(f"\n✅ 完了")


if __name__ == "__main__":
    main()
