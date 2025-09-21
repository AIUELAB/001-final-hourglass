#!/usr/bin/env python3
"""
Sensational Episode Generator
センセーショナルなエピソード生成システム - 感動と共感を重視
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from enhanced_selection_algorithm import EnhancedSelectionAlgorithm
from pdca_guardian import PDCAGuardian
from fact_freshness_checker import FactFreshnessChecker


class SensationalEpisodeGenerator:
    """センセーショナルなエピソード生成システム"""

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

    def calculate_sensational_value(self, fact: Dict, person_name: str) -> Dict:
        """
        センセーショナル価値の計算

        Args:
            fact: 事実データ
            person_name: 人物名

        Returns:
            センセーショナル価値スコア詳細
        """
        scores = {
            'story_score': 0,
            'context_score': 0,
            'empathy_score': 0,
            'total_score': 0
        }

        fact_text = fact.get('fact', '')
        keywords = fact.get('keywords', [])

        # 1. ストーリー性スコア（0-10）
        story_elements = {
            'turning_point': ['転換', '初めて', '変わった', 'きっかけ', '瞬間'],
            'against_odds': ['困難', '挫折', '克服', '復活', '奇跡', '挑戦'],
            'historic_first': ['史上初', '世界初', '日本初', '最年少', '最高齢', '唯一'],
            'human_drama': ['涙', '感動', '歓喜', '絶望', '希望', '夢']
        }

        for element, terms in story_elements.items():
            for term in terms:
                if term in fact_text or any(term in k for k in keywords):
                    if element == 'turning_point':
                        scores['story_score'] += 3
                    elif element == 'against_odds':
                        scores['story_score'] += 3
                    elif element == 'historic_first':
                        scores['story_score'] += 2
                    elif element == 'human_drama':
                        scores['story_score'] += 2
                    break

        # 2. コンテキストの豊富さ（0-10）
        context_elements = {
            'background': ['当時', '時代', '背景', '状況'],
            'significance': ['意味', '重要', '歴史的', '画期的'],
            'impact': ['影響', '変えた', '開いた', '導いた'],
            'comparison': ['最', '初', '唯一', '歴代', '記録']
        }

        for element, terms in context_elements.items():
            for term in terms:
                if term in fact_text or any(term in k for k in keywords):
                    if element == 'background':
                        scores['context_score'] += 2
                    elif element == 'significance':
                        scores['context_score'] += 3
                    elif element == 'impact':
                        scores['context_score'] += 3
                    elif element == 'comparison':
                        scores['context_score'] += 2
                    break

        # 3. 共感性（0-10）
        empathy_elements = {
            'relatable': ['同じ', '誰もが', '普通の', '日常'],
            'inspiring': ['勇気', '希望', '夢', '目標', '憧れ'],
            'memorable': ['忘れられない', '記憶', '印象', '衝撃', '鮮烈']
        }

        # 年齢による共感ボーナス
        age = fact.get('age', 30)
        if 7 <= age <= 12:  # 子供時代
            scores['empathy_score'] += 2
        elif 18 <= age <= 25:  # 青春時代
            scores['empathy_score'] += 1.5
        elif 30 <= age <= 40:  # 働き盛り
            scores['empathy_score'] += 1

        for element, terms in empathy_elements.items():
            for term in terms:
                if term in fact_text or any(term in k for k in keywords):
                    if element == 'relatable':
                        scores['empathy_score'] += 3
                    elif element == 'inspiring':
                        scores['empathy_score'] += 4
                    elif element == 'memorable':
                        scores['empathy_score'] += 3
                    break

        # 総合スコア計算（最大30点を10点満点に正規化）
        scores['story_score'] = min(10, scores['story_score'])
        scores['context_score'] = min(10, scores['context_score'])
        scores['empathy_score'] = min(10, scores['empathy_score'])
        scores['total_score'] = (scores['story_score'] + scores['context_score'] + scores['empathy_score']) / 3

        return scores

    def generate_sensational_text(self, person_name: str, fact: Dict) -> str:
        """
        センセーショナルなエピソードテキスト生成

        Args:
            person_name: 人物名
            fact: 事実データ

        Returns:
            センセーショナルなエピソードテキスト
        """
        age = fact.get('age', 30)
        fact_text = fact.get('fact', '')

        # 基本構造
        base = f"あなたと同じ{age}歳のとき、{person_name}は"

        # 特別なケースの処理
        if person_name == "ヘレン・ケラー" and age == 7:
            # Water!エピソードの特別な記述
            return (f"{base}視覚・聴覚・発話に困難を抱えながらも「Water（ウォーター）」と叫びました。"
                   f"家庭教師アン・サリヴァンが井戸水を手に流し、同時に手話で\"w-a-t-e-r\"を示した瞬間、"
                   f"ヘレンの中で「感覚の体験」と「言葉（記号）」が結びつき、世界の認識が一気に開かれたのです。"
                   f"これは「概念は体験と結びついたときに深く定着する」という学習原理を示す、"
                   f"教育の歴史に残る重要な出来事でした。")

        elif person_name == "安倍晋三":
            if "在職" in fact_text and "最長" in fact_text:
                # 在職記録の特別な記述
                return (f"{base}通算在職日数3,188日で歴代最長記録を達成。"
                       f"2019年11月20日に桂太郎を超えて通算最長を更新し、"
                       f"連続在職日数も2020年8月24日に2,822日で佐藤栄作を超え歴代最長に。"
                       f"この記録は、激動の国際情勢の中で日本の舵取りを担い続けた証でした。")
            elif "総理大臣" in fact_text and age == 52:
                # 就任時の特別な記述
                return (f"{base}第90代内閣総理大臣に就任、戦後生まれ初かつ戦後最年少（52歳）の総理大臣となりました。"
                       f"小泉内閣で幹事長・官房長官を歴任し、満を持しての就任。"
                       f"「美しい国、日本」を掲げ、新しい世代のリーダーシップが始まりました。")

        # その他の人物の場合
        # コンテキストを追加
        context = self._add_context_to_fact(fact_text, fact.get('keywords', []))

        # ドラマティックな要素を強調
        dramatic = self._emphasize_dramatic_elements(context, fact.get('keywords', []))

        return f"{base}{dramatic}"

    def _add_context_to_fact(self, fact_text: str, keywords: List[str]) -> str:
        """事実にコンテキストを追加"""
        # 記録系のキーワードがある場合
        if any(k in ['史上初', '世界初', '日本初'] for k in keywords):
            if '史上初' in fact_text:
                fact_text = fact_text.replace('史上初', '前人未到の偉業となる史上初')
            elif '世界初' in fact_text:
                fact_text = fact_text.replace('世界初', '世界中が注目する世界初')
            elif '日本初' in fact_text:
                fact_text = fact_text.replace('日本初', '歴史に名を刻む日本初')

        # オリンピック関連
        if 'オリンピック' in fact_text or '五輪' in fact_text:
            if '金メダル' in fact_text:
                fact_text += "世界の頂点に立った瞬間でした。"
            elif '銀メダル' in fact_text:
                fact_text += "惜しくも頂点には届かなかったものの、その挑戦は多くの人に勇気を与えました。"

        return fact_text

    def _emphasize_dramatic_elements(self, fact_text: str, keywords: List[str]) -> str:
        """ドラマティックな要素を強調"""
        # 困難克服系
        if any(k in ['復活', '克服', '挫折'] for k in keywords):
            fact_text += "これは単なる成功ではなく、困難を乗り越えた人間の強さを示す証でした。"

        # 記録達成系
        elif any(k in ['記録', '達成', '突破'] for k in keywords):
            fact_text += "この記録は、限界に挑み続けた努力の結晶でした。"

        # 創造・革新系
        elif any(k in ['創業', '発明', '開発', '発表'] for k in keywords):
            fact_text += "この瞬間が、後の世界を大きく変える第一歩となりました。"

        return fact_text

    def select_best_sensational_fact(self, person_name: str) -> Optional[Dict]:
        """
        最もセンセーショナルな事実を選定

        Args:
            person_name: 人物名

        Returns:
            最適な事実（失敗時はNone）
        """
        if person_name not in self.database:
            return None

        person_data = self.database[person_name]
        facts = person_data.get('facts', [])

        if not facts:
            return None

        # 各事実のセンセーショナル価値を計算
        scored_facts = []
        for fact in facts:
            sensational_scores = self.calculate_sensational_value(fact, person_name)
            algorithm_score = self.selection_algorithm.calculate_fact_score(fact)

            # 総合スコア = アルゴリズムスコア × センセーショナル価値
            total_score = algorithm_score * (1 + sensational_scores['total_score'] / 10)

            scored_facts.append({
                'fact': fact,
                'sensational_scores': sensational_scores,
                'algorithm_score': algorithm_score,
                'total_score': total_score
            })

        # スコアでソート
        scored_facts.sort(key=lambda x: x['total_score'], reverse=True)

        # デバッグ出力
        print(f"\n{person_name}のセンセーショナル価値分析:")
        for i, sf in enumerate(scored_facts[:3], 1):
            fact = sf['fact']
            scores = sf['sensational_scores']
            print(f"  {i}位: {fact.get('fact', '')[:50]}...")
            print(f"    ストーリー性: {scores['story_score']:.1f}/10")
            print(f"    コンテキスト: {scores['context_score']:.1f}/10")
            print(f"    共感性: {scores['empathy_score']:.1f}/10")
            print(f"    総合スコア: {sf['total_score']:.2f}")

        return scored_facts[0]['fact'] if scored_facts else None

    def generate_episode(self, person_name: str) -> Optional[Dict]:
        """
        センセーショナルなエピソード生成

        Args:
            person_name: 人物名

        Returns:
            生成されたエピソード（失敗時はNone）
        """
        # データベースチェック
        if person_name not in self.database:
            print(f"⚠️ {person_name}のデータがデータベースに存在しません")
            return None

        person_data = self.database[person_name]

        # GROUP_エンティティの拒否
        person_id = person_data.get('person_id', '')
        if person_id.startswith('GROUP_'):
            print(f"❌ {person_name}: グループエンティティは禁止されています")
            return None

        # 最適な事実を選定
        best_fact = self.select_best_sensational_fact(person_name)

        if not best_fact:
            print(f"⚠️ {person_name}の適切な事実が選定できませんでした")
            return None

        # センセーショナルなエピソードテキスト生成
        episode_text = self.generate_sensational_text(person_name, best_fact)

        # エピソードデータ構築
        episode_data = {
            'person_id': person_data.get('person_id', f'P{str(hash(person_name))[:6]}'),
            'person_name': person_name,
            'age': best_fact.get('age', 30),
            'episode_text': episode_text,
            'confidence': best_fact.get('confidence', 1.0),
            'sources': '|'.join(best_fact.get('sources', ['verified_database'])),
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': self.selection_algorithm.calculate_fact_score(best_fact),
            'freshness_year': self.selection_algorithm._extract_year(best_fact),
            'ownership_type': best_fact.get('ownership_type', 'individual'),
            'sensational_value': self.calculate_sensational_value(best_fact, person_name)['total_score']
        }

        return episode_data

    def generate_all_episodes(self, person_list: List[str]) -> List[Dict]:
        """
        複数人物のセンセーショナルエピソード一括生成
        """
        episodes = []
        success_count = 0
        failed_persons = []

        print(f"\n🎭 {len(person_list)}人のセンセーショナルエピソード生成開始...")
        print("=" * 60)

        for person_name in person_list:
            episode = self.generate_episode(person_name)
            if episode:
                episodes.append(episode)
                success_count += 1
                print(f"✅ {person_name}: スコア {episode['algorithm_score']:.3f} "
                      f"(センセーショナル価値 {episode['sensational_value']:.1f}/10)")
            else:
                failed_persons.append(person_name)
                print(f"❌ {person_name}: 生成失敗")

        print("=" * 60)
        print(f"\n📊 生成結果:")
        print(f"   成功: {success_count}/{len(person_list)}件")
        print(f"   失敗: {len(failed_persons)}件")

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
                         'algorithm_score', 'freshness_year', 'ownership_type',
                         'sensational_value']
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()

            for episode in episodes:
                row = {k: episode.get(k, '') for k in fieldnames}
                writer.writerow(row)

        print(f"\n📄 CSV保存完了: {filename}")
        print(f"   エピソード数: {len(episodes)}件")


def main():
    """メイン処理"""
    print("=" * 60)
    print("Sensational Episode Generator - センセーショナルエピソード生成システム")
    print("=" * 60)

    generator = SensationalEpisodeGenerator()

    # 全29人のリスト
    all_persons = [
        # 既存の19人
        'イチロー', 'スティーブ・ジョブズ', 'Ado', 'さくらももこ', 'ヘレン・ケラー',
        '安倍晋三', '大谷翔平', 'HIKAKIN', '羽生善治', '宮崎駿',
        '藤井聡太', '黒澤明', '村上春樹', '北野武', '山中伸弥',
        '松田聖子', '錦織圭', '浅田真央', '吉田沙保里',
        # 追加の10人
        '孫正義', '本庶佑', '三木谷浩史', '柳井正', '羽生結弦',
        '坂本龍一', '櫻井翔', 'YOSHIKI', 'あいみょん', '小泉純一郎'
    ]

    # エピソード生成
    episodes = generator.generate_all_episodes(all_persons)

    # スコアでソート
    episodes.sort(key=lambda x: x.get('sensational_value', 0) * x.get('algorithm_score', 0), reverse=True)

    # CSV保存
    output_file = f"sensational_episodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    generator.save_to_csv(episodes, output_file)

    # サンプル表示
    if episodes:
        print("\n🎯 センセーショナルエピソードのサンプル:")
        for i, ep in enumerate(episodes[:3], 1):
            print(f"\n{i}. {ep['person_name']} ({ep['age']}歳):")
            print(f"   {ep['episode_text'][:200]}...")
            print(f"   センセーショナル価値: {ep['sensational_value']:.1f}/10")

    print("\n✨ センセーショナルエピソード生成完了！")


if __name__ == "__main__":
    main()