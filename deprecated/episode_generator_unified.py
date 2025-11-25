#!/usr/bin/env python3
"""
Unified Episode Generator System
統一エピソード生成システム - 手動作成完全排除版
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Optional
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from enhanced_selection_algorithm import EnhancedSelectionAlgorithm
from pdca_guardian import PDCAGuardian
from fact_freshness_checker import FactFreshnessChecker


class UnifiedEpisodeGenerator:
    """統一エピソード生成システム"""

    def __init__(self):
        self.selection_algorithm = EnhancedSelectionAlgorithm()
        self.pdca_guardian = PDCAGuardian()
        self.freshness_checker = FactFreshnessChecker()
        self.database_path = "verified_facts_database_103persons.json"
        self.database = self._load_database()
        self.current_year = datetime.now().year

    def _load_database(self) -> Dict:
        """データベース読み込み"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('verified_facts', {})
        except FileNotFoundError:
            print(f"エラー: {self.database_path}が見つかりません")
            return {}

    def generate_episode(self, person_name: str) -> Optional[Dict]:
        """
        エピソード生成（データベース必須、手動作成禁止、グループ禁止）

        Args:
            person_name: 人物名

        Returns:
            生成されたエピソード（失敗時はNone）
        """
        # データベースチェック
        if person_name not in self.database:
            print(f"⚠️ {person_name}のデータがデータベースに存在しません")
            # データベースにない場合はエピソード生成を拒否
            return None

        person_data = self.database[person_name]

        # GROUP_エンティティの拒否（RULE_134）
        person_id = person_data.get('person_id', '')
        if person_id.startswith('GROUP_'):
            print(f"❌ {person_name}: グループエンティティは禁止されています (ID: {person_id})")
            print("   → 個人メンバーに分割してください")
            return None

        # 既知のグループ名チェック（RULE_135）
        known_groups = ['嵐', 'SMAP', 'TOKIO', 'V6', 'KinKi Kids', 'AKB48', 'NMB48', 'SKE48',
                       'モーニング娘。', '乃木坂46', '欅坂46', '日向坂46', 'Perfume']
        if person_name in known_groups:
            print(f"❌ {person_name}: グループ名での登録は禁止されています")
            print("   → メンバー個人を登録してください")
            return None
        facts = person_data.get('facts', [])

        if not facts:
            print(f"⚠️ {person_name}の事実データが空です")
            return None

        # 選択アルゴリズムで最適な事実を選定（人物名を渡して功績主体性を評価）
        best_fact, top_candidates = self.selection_algorithm.select_best_fact(
            facts,
            top_n=3,
            person_name=person_name  # 功績主体性評価のため
        )

        if not best_fact:
            print(f"⚠️ {person_name}の適切な事実が選定できませんでした")
            return None

        # エピソードテキスト構築
        age = best_fact.get('age', 30)
        fact_text = best_fact.get('fact', '')

        # 功績の主体性に応じたテキスト調整
        ownership_type = best_fact.get('ownership_type', 'individual')
        if ownership_type == 'participation':
            # 参加型功績の場合は適切な表現に
            if 'YMO' in fact_text and person_name == '坂本龍一':
                fact_text = fact_text.replace('結成', 'メンバーとして参加')

        episode_text = f"あなたと同じ{age}歳のとき、{person_name}は{fact_text}"

        # 句点確認
        if not episode_text.endswith('。'):
            episode_text += '。'

        # カテゴリ別の教育的文脈追加
        category = self._determine_category(person_name)
        episode_text += self._add_educational_context(category, best_fact)

        # エピソードデータ構築
        episode_data = {
            'person_id': person_data.get('person_id', f'P{str(hash(person_name))[:6]}'),
            'person_name': person_name,
            'age': age,
            'episode_text': episode_text,
            'confidence': best_fact.get('confidence', 1.0),
            'sources': '|'.join(best_fact.get('sources', ['verified_database'])),
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': self.selection_algorithm.calculate_fact_score(best_fact),
            'freshness_year': self.selection_algorithm._extract_year(best_fact),
            'ownership_type': ownership_type,  # 功績タイプを記録
            'database_sourced': True  # データベース由来フラグ
        }

        # PDCAガーディアンチェック
        person_info = {
            'person_name_display': person_name,
            'person_id': episode_data['person_id'],
            'birth_year': person_data.get('birth_year'),
            'category': category
        }

        # 完全性チェック
        violations = self.pdca_guardian.check_episode_completeness(episode_text, person_info)

        # 功績主体性チェック（新規追加）
        ownership_violations = self.pdca_guardian.check_achievement_ownership(episode_text, person_info)
        violations.extend(ownership_violations)

        # 手動作成チェック（新規追加）
        manual_violations = self.pdca_guardian.check_manual_creation(episode_data)
        violations.extend(manual_violations)

        # データ鮮度チェック
        freshness_violations = self.pdca_guardian.check_data_freshness(person_data, best_fact)
        violations.extend(freshness_violations)

        # グループエンティティチェック（新規追加 RULE_134-135）
        group_violations = self.pdca_guardian.check_group_entity_prohibition(episode_data)
        violations.extend(group_violations)

        if violations:
            print(f"⚠️ {person_name}: {len(violations)}件の警告")
            for v in violations:
                print(f"   - {v.get('type')}: {v.get('message')}")

            # クリティカルな違反がある場合は生成を中止
            critical_violations = [v for v in violations if v.get('severity') == 'critical']
            if critical_violations:
                print(f"❌ {person_name}: クリティカルな違反のため生成中止")
                return None

        return episode_data

    def _determine_category(self, person_name: str) -> str:
        """カテゴリ判定"""
        categories = {
            'スポーツ': ['イチロー', '大谷翔平', '羽生結弦', '吉田沙保里', '錦織圭', '浅田真央'],
            '政治': ['安倍晋三', '小泉純一郎', '田中角栄'],
            '文化・芸術': ['宮崎駿', '黒澤明', '村上春樹', '北野武', '坂本龍一', 'YOSHIKI'],
            '科学・技術': ['山中伸弥', '本庶佑'],
            'エンタメ': ['HIKAKIN', 'Ado', 'あいみょん', '松田聖子', '嵐'],
            '将棋': ['羽生善治', '藤井聡太'],
            '実業家': ['孫正義', '柳井正', '三木谷浩史']
        }

        for category, names in categories.items():
            if person_name in names:
                return category
        return 'その他'

    def _add_educational_context(self, category: str, fact: Dict) -> str:
        """教育的文脈の追加"""
        keywords = fact.get('keywords', [])
        context = ""

        if category == 'スポーツ':
            if any(k in keywords for k in ['史上初', '世界初', '50-50', 'ワールドシリーズ']):
                context = "この偉業は野球史上前人未到の記録であり、不可能を可能にする挑戦の象徴として世界中に勇気を与えました。"
            else:
                context = "この成果は、継続的な努力と卓越した才能の結晶であり、多くの人々に感動と勇気を与えました。"

        elif category == '政治':
            context = "この出来事は日本の歴史において重要な転換点となり、現代社会の形成に大きな影響を与えています。"

        elif category == '文化・芸術':
            context = "この作品は日本文化の新たな地平を切り開き、世界中の人々に深い影響を与え続けています。"

        elif category == '科学・技術':
            context = "この発見は科学技術の進歩に革命的な貢献をし、人類の未来を明るく照らす礎となりました。"

        elif category == '将棋':
            context = "この記録は将棋界の歴史に燦然と輝く金字塔であり、知性と創造性の極致を示しています。"

        elif category == '実業家':
            context = "このビジネスの成功は、革新的な発想と実行力の賜物であり、日本経済に大きなインパクトを与えました。"

        else:
            context = "この経験は、挑戦する勇気と創造性の重要性を示し、多くの人々にインスピレーションを与えています。"

        # キーワード強調
        if keywords and len(context) < 150:
            important_kw = keywords[0] if keywords else ""
            if important_kw:
                context += f"特に{important_kw}という点において、その功績は永遠に記憶されるでしょう。"

        return context

    def generate_all_episodes(self, person_list: List[str]) -> List[Dict]:
        """
        複数人物のエピソード一括生成

        Args:
            person_list: 人物名リスト

        Returns:
            生成されたエピソードリスト
        """
        episodes = []
        success_count = 0
        failed_persons = []

        print(f"\n📝 {len(person_list)}人のエピソード生成開始...")
        print("=" * 60)

        for person_name in person_list:
            episode = self.generate_episode(person_name)
            if episode:
                episodes.append(episode)
                success_count += 1
                print(f"✅ {person_name}: スコア {episode['algorithm_score']:.3f}")
            else:
                failed_persons.append(person_name)
                print(f"❌ {person_name}: 生成失敗（データベースなし or 品質基準未達）")

        print("=" * 60)
        print(f"\n📊 生成結果:")
        print(f"   成功: {success_count}/{len(person_list)}件")
        print(f"   失敗: {len(failed_persons)}件")

        if failed_persons:
            print(f"\n⚠️ 生成失敗した人物:")
            for name in failed_persons[:5]:  # 最初の5人のみ表示
                print(f"   - {name}")
            if len(failed_persons) > 5:
                print(f"   ... 他{len(failed_persons)-5}名")

        return episodes

    def save_to_csv(self, episodes: List[Dict], filename: str):
        """CSV保存（Excel対応）"""
        if not episodes:
            print("エピソードがありません")
            return

        # UTF-8 BOM付きで保存
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['person_id', 'person_name', 'age', 'episode_text',
                         'confidence', 'sources', 'generation_date',
                         'algorithm_score', 'freshness_year', 'ownership_type']
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()

            # ownership_typeを含まない古いエピソードにも対応
            for episode in episodes:
                row = {k: episode.get(k, '') for k in fieldnames}
                writer.writerow(row)

        print(f"\n📄 CSV保存完了: {filename}")
        print(f"   エピソード数: {len(episodes)}件")


def main():
    """メイン処理"""
    print("=" * 60)
    print("Unified Episode Generator - 統一エピソード生成システム")
    print("=" * 60)

    generator = UnifiedEpisodeGenerator()

    # 全人物リスト（29人 - 嵐を削除し櫻井翔を追加）
    all_persons = [
        # 既存の19人
        'イチロー', 'スティーブ・ジョブズ', 'Ado', 'さくらももこ', 'ヘレン・ケラー',
        '安倍晋三', '大谷翔平', 'HIKAKIN', '羽生善治', '宮崎駿',
        '藤井聡太', '黒澤明', '村上春樹', '北野武', '山中伸弥',
        '松田聖子', '錦織圭', '浅田真央', '吉田沙保里',
        # 追加の10人（嵐→櫻井翔に変更）
        '孫正義', '本庶佑', '三木谷浩史', '柳井正', '羽生結弦',
        '坂本龍一', '櫻井翔', 'YOSHIKI', 'あいみょん', '小泉純一郎'
    ]

    # エピソード生成
    episodes = generator.generate_all_episodes(all_persons)

    # スコアでソート
    episodes.sort(key=lambda x: x.get('algorithm_score', 0), reverse=True)

    # CSV保存
    output_file = f"unified_episodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    generator.save_to_csv(episodes, output_file)

    # 統計表示
    if episodes:
        print("\n🏆 スコア上位5件:")
        for i, ep in enumerate(episodes[:5], 1):
            print(f"{i}. {ep['person_name']} (スコア: {ep['algorithm_score']:.3f})")
            print(f"   {ep['episode_text'][:80]}...")

        # カテゴリ分析
        categories = {}
        for ep in episodes:
            category = generator._determine_category(ep['person_name'])
            categories[category] = categories.get(category, 0) + 1

        print("\n📂 カテゴリ分布:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"   {cat}: {count}件 ({count/len(episodes)*100:.1f}%)")

    print("\n✨ 統一システムによるエピソード生成完了！")


if __name__ == "__main__":
    main()
