#!/usr/bin/env python3
"""
Final Episode Generator with New System
新システムを使用した最終版エピソード生成
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Optional
import sys
from pathlib import Path

# モジュールのインポート
sys.path.append(str(Path(__file__).parent))
from enhanced_selection_algorithm import EnhancedSelectionAlgorithm
from pdca_guardian import PDCAGuardian
from fact_freshness_checker import FactFreshnessChecker


class FinalEpisodeGenerator:
    """最終版エピソード生成器"""

    def __init__(self):
        self.selection_algorithm = EnhancedSelectionAlgorithm()
        self.pdca_guardian = PDCAGuardian()
        self.freshness_checker = FactFreshnessChecker()
        self.database_path = "verified_facts_database_103persons.json"
        self.database = self._load_database()

    def _load_database(self) -> Dict:
        """データベース読み込み"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('verified_facts', {})
        except FileNotFoundError:
            print(f"警告: {self.database_path}が見つかりません")
            return {}

    def generate_improved_episode(self, person_name: str, person_data: Dict) -> Optional[Dict]:
        """
        改善版エピソード生成（新アルゴリズム使用）
        """
        facts = person_data.get('facts', [])
        if not facts:
            return None

        # 新アルゴリズムで最適な事実を選定
        best_fact, top_candidates = self.selection_algorithm.select_best_fact(facts, top_n=3)

        if not best_fact:
            return None

        # エピソードテキスト構築
        age = best_fact.get('age', 30)
        fact_text = best_fact.get('fact', '')

        episode_text = f"あなたと同じ{age}歳のとき、{person_name}は{fact_text}"

        # 句点確認
        if not episode_text.endswith('。'):
            episode_text += '。'

        # カテゴリ別の教育的文脈追加
        category = self._determine_category(person_name)
        episode_text += self._add_educational_context(category, best_fact)

        # PDCAガーディアンチェック
        person_info = {
            'person_name_display': person_name,
            'person_id': person_data.get('person_id', f'P{person_name[:3].upper()}'),
            'birth_year': person_data.get('birth_year'),
            'category': category
        }

        violations = self.pdca_guardian.check_episode_completeness(episode_text, person_info)

        # データ鮮度チェック（新機能）
        freshness_violations = self.pdca_guardian.check_data_freshness(person_data, best_fact)
        violations.extend(freshness_violations)

        if violations:
            print(f"⚠️ {person_name}: {len(violations)}件の警告")
            for v in violations:
                print(f"   - {v.get('type')}: {v.get('message')}")

        return {
            'person_id': person_data.get('person_id', f'P{str(hash(person_name))[:6]}'),
            'person_name': person_name,
            'age': age,
            'episode_text': episode_text,
            'confidence': best_fact.get('confidence', 1.0),
            'sources': '|'.join(best_fact.get('sources', ['verified_database'])),
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': self.selection_algorithm.calculate_fact_score(best_fact),
            'freshness_year': self.selection_algorithm._extract_year(best_fact)
        }

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

    def refresh_existing_episodes(self) -> List[Dict]:
        """
        既存15エピソードのブラッシュアップ
        """
        existing_persons = [
            'イチロー', 'スティーブ・ジョブズ', 'Ado', 'さくらももこ', 'ヘレン・ケラー',
            '安倍晋三', '大谷翔平', 'HIKAKIN', '羽生善治', '宮崎駿',
            '藤井聡太', '黒澤明', '村上春樹', '北野武'
        ]

        refreshed_episodes = []

        print("\n📝 既存エピソードのブラッシュアップ開始...")
        for person_name in existing_persons:
            if person_name in self.database:
                episode = self.generate_improved_episode(person_name, self.database[person_name])
                if episode:
                    refreshed_episodes.append(episode)
                    print(f"✅ {person_name}: スコア {episode['algorithm_score']:.3f}")
                else:
                    print(f"❌ {person_name}: 生成失敗")
            else:
                # データベースにない場合は手動作成
                if person_name == 'スティーブ・ジョブズ':
                    episode = {
                        'person_id': 'P003',
                        'person_name': person_name,
                        'age': 52,
                        'episode_text': 'あなたと同じ52歳のとき、スティーブ・ジョブズは2007年に初代iPhoneを発表し、「電話を再発明する」と宣言しました。このイノベーションはモバイルコンピューティングの概念を根本から覆し、人類のコミュニケーション方法を永遠に変えました。特にタッチスクリーン革命という点において、その功績は永遠に記憶されるでしょう。',
                        'confidence': 1.0,
                        'sources': 'Apple発表会記録|Wikipedia',
                        'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'algorithm_score': 2.1,
                        'freshness_year': 2007
                    }
                    refreshed_episodes.append(episode)
                elif person_name == 'ヘレン・ケラー':
                    episode = {
                        'person_id': 'P001',
                        'person_name': person_name,
                        'age': 7,
                        'episode_text': 'あなたと同じ7歳のとき、ヘレン・ケラーは視覚・聴覚・発話に困難を抱えながらも「Water!」と叫びました。家庭教師アン・サリヴァンが井戸水を手に流しながら手話で「w-a-t-e-r」を綴った瞬間、ヘレンの中で感覚と言語が結びつき、世界の認識が劇的に開かれました。これは「概念は体験と結びついたときに深く定着する」という学習原理を示す、教育史上最も重要な瞬間の一つです。',
                        'confidence': 1.0,
                        'sources': '伝記複数|Wikipedia|自伝',
                        'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'algorithm_score': 1.8,
                        'freshness_year': 1887
                    }
                    refreshed_episodes.append(episode)

        return refreshed_episodes

    def generate_new_episodes(self, count: int = 10) -> List[Dict]:
        """
        新規10エピソードの生成
        """
        # 未使用の人物を選定
        new_persons = [
            '孫正義', '山中伸弥', '松田聖子', '三木谷浩史', '柳井正',
            '錦織圭', '浅田真央', '羽生結弦', '吉田沙保里', '本庶佑'
        ]

        new_episodes = []

        print("\n🆕 新規エピソード生成開始...")
        for person_name in new_persons[:count]:
            if person_name in self.database:
                episode = self.generate_improved_episode(person_name, self.database[person_name])
                if episode:
                    new_episodes.append(episode)
                    print(f"✅ {person_name}: スコア {episode['algorithm_score']:.3f}")
                else:
                    # データがない場合は手動で追加
                    print(f"⚠️ {person_name}: データ不足、手動作成")
                    episode = self._create_manual_episode(person_name)
                    if episode:
                        new_episodes.append(episode)

        return new_episodes

    def _create_manual_episode(self, person_name: str) -> Optional[Dict]:
        """手動エピソード作成（データ不足時）"""
        manual_episodes = {
            '孫正義': {
                'age': 39,
                'text': '1996年、Yahoo! JAPANを設立し、日本のインターネット革命を牽引',
                'year': 1996
            },
            '山中伸弥': {
                'age': 44,
                'text': '2006年、iPS細胞の作製に成功し、再生医療の扉を開いた',
                'year': 2006
            },
            '松田聖子': {
                'age': 18,
                'text': '1980年、「裸足の季節」でデビューし、アイドル界の頂点へ',
                'year': 1980
            }
        }

        if person_name in manual_episodes:
            data = manual_episodes[person_name]
            episode_text = f"あなたと同じ{data['age']}歳のとき、{person_name}は{data['text']}。"

            category = self._determine_category(person_name)
            episode_text += self._add_educational_context(category, {'keywords': []})

            return {
                'person_id': f'P{str(hash(person_name))[:6]}',
                'person_name': person_name,
                'age': data['age'],
                'episode_text': episode_text,
                'confidence': 0.9,
                'sources': 'manual_entry|Wikipedia',
                'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'algorithm_score': 1.5,
                'freshness_year': data['year']
            }

        return None

    def save_to_csv(self, episodes: List[Dict], filename: str):
        """CSV保存（Excel対応）"""
        if not episodes:
            print("エピソードがありません")
            return

        # UTF-8 BOM付きで保存
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['person_id', 'person_name', 'age', 'episode_text',
                         'confidence', 'sources', 'generation_date',
                         'algorithm_score', 'freshness_year']
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(episodes)

        print(f"\n📄 CSV保存完了: {filename}")
        print(f"   エピソード数: {len(episodes)}件")


def main():
    """メイン処理"""
    print("=" * 60)
    print("Final Episode Generator - 最終版エピソード生成")
    print("=" * 60)

    generator = FinalEpisodeGenerator()

    # 既存エピソードのブラッシュアップ
    refreshed = generator.refresh_existing_episodes()

    # 新規エピソード生成
    new_episodes = generator.generate_new_episodes(10)

    # 全エピソードを統合
    all_episodes = refreshed + new_episodes

    # スコアでソート（高い順）
    all_episodes.sort(key=lambda x: x.get('algorithm_score', 0), reverse=True)

    # CSV保存
    output_file = f"final_episodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    generator.save_to_csv(all_episodes, output_file)

    # 統計表示
    print("\n📊 生成統計:")
    print(f"   ブラッシュアップ: {len(refreshed)}件")
    print(f"   新規生成: {len(new_episodes)}件")
    print(f"   合計: {len(all_episodes)}件")

    # 上位5件表示
    print("\n🏆 スコア上位5件:")
    for i, ep in enumerate(all_episodes[:5], 1):
        print(f"{i}. {ep['person_name']} (スコア: {ep['algorithm_score']:.3f})")
        print(f"   {ep['episode_text'][:80]}...")

    # 鮮度分析
    current_year = datetime.now().year
    fresh_count = sum(1 for ep in all_episodes
                     if ep.get('freshness_year', 0) >= current_year - 2)

    print(f"\n📈 データ鮮度:")
    print(f"   2年以内のデータ: {fresh_count}/{len(all_episodes)}件")
    print(f"   鮮度率: {(fresh_count/len(all_episodes)*100):.1f}%")

    print("\n✨ 最終版エピソード生成完了！")


if __name__ == "__main__":
    main()
