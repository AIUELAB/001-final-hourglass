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
from src.database_utils import get_db_connection
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import csv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# Rule 201インポート（オプション）
try:
    from rules.rule_201_episode_selection_criteria import Rule201EpisodeSelectionCriteria
    RULE_201_AVAILABLE = True
except ImportError:
    RULE_201_AVAILABLE = False
    logger.warning("Rule 201が利用できません。優先度評価機能は無効化されます。")


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

    def __init__(self, db_path: str = "episode_database.db", enable_priority_scoring: bool = True):
        self.db_path = db_path
        self.excluded_persons: set = set()  # 除外する人物名のセット
        self.enable_priority_scoring = enable_priority_scoring and RULE_201_AVAILABLE

        # Rule 201初期化（優先度評価用）
        if self.enable_priority_scoring:
            self.priority_gate = Rule201EpisodeSelectionCriteria()
            logger.info("✅ Rule 201による優先度評価を有効化しました")
        else:
            self.priority_gate = None
            if enable_priority_scoring and not RULE_201_AVAILABLE:
                logger.warning("⚠️ Rule 201が利用できないため、優先度評価は無効化されました")

    def load_excluded_persons_from_csv(self, csv_path: str):
        """
        既存データベースから除外人物リストを読み込み

        Args:
            csv_path: 既存エピソードデータベースのCSVパス
        """
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    person_name = row.get('人物名', '')
                    if person_name:
                        self.excluded_persons.add(person_name)

            logger.info(f"✅ 除外リスト読み込み完了: {len(self.excluded_persons)}件")
        except FileNotFoundError:
            logger.warning(f"⚠️ 除外リストファイルが見つかりません: {csv_path}")
        except Exception as e:
            logger.error(f"❌ 除外リスト読み込みエラー: {e}")

    def add_excluded_person(self, person_name: str):
        """除外リストに人物を追加"""
        self.excluded_persons.add(person_name)

    def add_excluded_persons(self, person_names: List[str]):
        """除外リストに複数人物を追加"""
        self.excluded_persons.update(person_names)

    def clear_excluded_persons(self):
        """除外リストをクリア"""
        self.excluded_persons.clear()

    def select_from_database(self, max_candidates: int = 50) -> List[Dict]:
        """データベースから有名人を選定"""

        with get_db_connection(self.db_path) as conn:
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

                        # 除外リストチェック
                        if person_name in self.excluded_persons:
                            logger.debug(f"  除外: {person_name} (除外リストに存在)")
                            continue

                        # 重複チェック
                        if person_name not in found_names:
                            person['priority'] = target.priority
                            person['target_category'] = target.category
                            selected.append(person)
                            found_names.add(person_name)

                            logger.info(f"  選定: {person_name} (優先度: {target.priority})")

        logger.info(f"✅ 選定完了: {len(selected)}名")
        return selected

    def select_with_priority(self, max_candidates: int = 130, target_tier1_ratio: float = 0.4) -> List[Dict]:
        """
        優先度ベースの候補選定（Rule 201統合版）

        Args:
            max_candidates: 選定する候補数
            target_tier1_ratio: Tier 1の目標比率（デフォルト40%）

        Returns:
            優先度順にソートされた候補リスト
        """
        # まず全候補を取得（多めに）
        all_candidates = self.select_from_database(max_candidates=max_candidates * 3)

        if not self.enable_priority_scoring or not all_candidates:
            # Rule 201が無効の場合は通常の選定結果をそのまま返す
            return all_candidates[:max_candidates]

        logger.info(f"\n🎯 Rule 201による優先度評価を開始")

        # 各候補の優先度を評価
        tier1_candidates = []
        tier2_candidates = []
        tier3_candidates = []

        for candidate in all_candidates:
            # Rule 201で評価
            tier, score, details = self.priority_gate.evaluate_priority({
                'description': f"{candidate.get('category', '')} 分野の著名人",
                'person_name': candidate.get('person_name_ja', ''),
                'category': candidate.get('category', ''),
                'priority': candidate.get('priority', 3)
            })

            # 候補に優先度情報を追加
            candidate['tier'] = tier
            candidate['priority_score'] = score
            candidate['tier_details'] = details

            # Tier別に分類
            if tier == 1:
                tier1_candidates.append(candidate)
            elif tier == 2:
                tier2_candidates.append(candidate)
            else:
                tier3_candidates.append(candidate)

        # 各Tierをスコア順にソート
        tier1_candidates.sort(key=lambda x: x['priority_score'], reverse=True)
        tier2_candidates.sort(key=lambda x: x['priority_score'], reverse=True)
        tier3_candidates.sort(key=lambda x: x['priority_score'], reverse=True)

        # 目標Tier比率に基づいて選定
        target_tier1 = int(max_candidates * target_tier1_ratio)
        target_tier2 = int(max_candidates * 0.35)
        target_tier3 = max_candidates - target_tier1 - target_tier2

        selected = []
        selected.extend(tier1_candidates[:target_tier1])

        remaining = max_candidates - len(selected)
        if remaining > 0:
            selected.extend(tier2_candidates[:min(target_tier2, remaining)])

        remaining = max_candidates - len(selected)
        if remaining > 0:
            selected.extend(tier3_candidates[:min(target_tier3, remaining)])

        # 不足分は残りのTier 1/2から補充
        remaining = max_candidates - len(selected)
        if remaining > 0:
            extra_tier1 = tier1_candidates[target_tier1:]
            extra_tier2 = tier2_candidates[target_tier2:]
            extra = extra_tier1 + extra_tier2
            extra.sort(key=lambda x: x['priority_score'], reverse=True)
            selected.extend(extra[:remaining])

        # 統計情報を表示
        final_tier1 = sum(1 for c in selected if c['tier'] == 1)
        final_tier2 = sum(1 for c in selected if c['tier'] == 2)
        final_tier3 = sum(1 for c in selected if c['tier'] == 3)

        logger.info(f"\n📊 優先度ベース選定結果:")
        logger.info(f"   総数: {len(selected)}名")
        logger.info(f"   Tier 1: {final_tier1}名 ({final_tier1/len(selected)*100:.1f}%) - 目標≥40%")
        logger.info(f"   Tier 2: {final_tier2}名 ({final_tier2/len(selected)*100:.1f}%) - 目標≥35%")
        logger.info(f"   Tier 3: {final_tier3}名 ({final_tier3/len(selected)*100:.1f}%) - 目標≤25%")

        return selected[:max_candidates]

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
