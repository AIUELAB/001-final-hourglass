#!/usr/bin/env python3
"""
改良版エピソード生成システム
3軸評価（記録・記憶・共感）と新カテゴリ対応
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path


class ImprovedEpisodeGenerator:
    """改良版エピソード生成システム"""

    def __init__(self):
        self.database_path = "verified_facts_database_103persons.json"
        self.database = self._load_database()

        self.MIN_LENGTH = 150
        self.MAX_LENGTH = 300

        # 改良版カテゴリ別テンプレート
        self.context_templates = {
            'cultural_phenomenon': [
                "この時代を象徴する出来事は、日本の文化史に新たな1ページを刻みました。",
                "社会現象となったその影響は、世代を超えて語り継がれています。",
                "時代の空気を変えた瞬間は、多くの人々の心に深く刻まれています。",
                "日本中が注目したその瞬間は、文化的転換点となりました。"
            ],
            'social_contribution': [
                "その利他的な行動は、日本社会に希望の光をもたらしました。",
                "困難な時代にあって示された勇気は、多くの人々を励まし続けています。",
                "社会への深い愛情が形となった瞬間でした。",
                "その決断は、人間の尊厳と優しさを体現するものでした。"
            ],
            'continuous_achievement': [
                "継続的な努力の結晶が、ついに歴史的な記録として結実しました。",
                "プロフェッショナリズムの極致が、新たな伝説を生みました。",
                "積み重ねた実績が、前人未到の領域へと到達しました。",
                "その一貫した姿勢は、後進への最高の教科書となりました。"
            ],
            'sports': [
                "その勇姿は多くの人々に感動と勇気を与えました。",
                "スポーツの持つ力が、国境を越えて人々を繋ぎました。",
                "限界に挑む姿勢は、後進への道標となりました。"
            ],
            'art_creation': [
                "その作品は時代を超えて愛され続けています。",
                "芸術の普遍的価値が、ここに結実しました。",
                "創造性の極致が、新たな表現の地平を開きました。"
            ],
            'science': [
                "この発見は人類の未来に希望をもたらしました。",
                "科学の進歩が、新たな可能性を切り開きました。",
                "真理への探求が、世界を変える一歩となりました。"
            ],
            'politics': [
                "この決断は日本の歴史に大きな転換点をもたらしました。",
                "政治的リーダーシップが、時代を動かした瞬間でした。",
                "国民の選択が、新たな時代の扉を開きました。"
            ],
            'business': [
                "この革新は産業界に大きなインパクトを与えました。",
                "ビジネスの新たな可能性が、ここから始まりました。",
                "起業家精神が、社会を変革する力となりました。"
            ],
            'entertainment': [
                "エンターテインメントの力が、人々に夢と希望を届けました。",
                "その才能は、多くの人々の心を豊かにしました。",
                "新しい表現が、時代の空気を変えました。"
            ],
            'award_international': [
                "世界が認めたその才能は、日本の誇りとなりました。",
                "国際的な評価が、その実力を証明しました。",
                "世界の舞台での栄誉は、新たな伝説の始まりでした。"
            ],
            'award_domestic': [
                "日本での確固たる評価が、その実力を証明しました。",
                "国内最高峰の栄誉は、長年の努力の結晶でした。",
                "この栄誉は、新たな才能の誕生を告げました。"
            ],
            'generic': [
                "この出来事は、多くの人々の記憶に刻まれています。",
                "その功績は、今も語り継がれています。",
                "時代の証人となった瞬間でした。"
            ]
        }

    def _load_database(self) -> Dict:
        """データベース読み込み"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('verified_facts', {})
        except FileNotFoundError:
            print(f"エラー: {self.database_path}が見つかりません")
            return {}

    def _categorize_content(self, fact_text: str, person_name: str, fact: Dict) -> str:
        """
        改良版カテゴライズ（3軸評価と新カテゴリ対応）
        """
        # 社会貢献カテゴリ
        if any(k in fact_text for k in ['寄付', '震災', '支援', '慈善', 'ボランティア']):
            return 'social_contribution'

        # 文化現象カテゴリ
        if any(k in fact_text for k in ['社会現象', 'ブーム', '世紀の', '全国的']):
            return 'cultural_phenomenon'

        # 継続的達成カテゴリ
        if any(k in fact_text for k in ['連続', '継続', '記録更新', '史上最長']):
            return 'continuous_achievement'

        # 既存カテゴリの判定
        if '日本アカデミー賞' in fact_text:
            return 'award_domestic'
        elif any(k in fact_text for k in ['アカデミー賞', 'Oscar', 'オスカー', 'グラミー賞',
                                          'カンヌ', 'ヴェネツィア', 'ベルリン']):
            return 'award_international'
        elif any(k in fact_text for k in ['オリンピック', '五輪', '金メダル', '銀メダル']):
            return 'sports'
        elif any(k in fact_text for k in ['発表', '公開', '出版']) and \
             any(k in fact_text for k in ['映画', '作品', '小説', '音楽']):
            return 'art_creation'
        elif any(k in fact_text for k in ['ノーベル', '研究', '発見', 'iPS']):
            return 'science'
        elif any(k in fact_text for k in ['総理', '大臣', '選挙', '政策']):
            return 'politics'
        elif any(k in fact_text for k in ['創業', '起業', '設立', '買収']):
            return 'business'
        elif any(k in fact_text for k in ['紅白', 'YouTube', 'ヒット']):
            return 'entertainment'
        else:
            return 'generic'

    def _calculate_3axis_score(self, fact: Dict) -> float:
        """
        3軸評価による総合スコア計算
        記録（20%）・記憶（40%）・共感（40%）
        """
        # 各軸のスコアを取得（デフォルト値あり）
        record_score = fact.get('importance_score', 1.0)
        memory_score = fact.get('memory_score', 0.5)
        empathy_score = fact.get('empathy_score', 0.5)

        # 重み付け計算
        total_score = (record_score * 0.2) + (memory_score * 0.4) + (empathy_score * 0.4)

        return total_score

    def _select_best_fact(self, facts: List[Dict], person_name: str) -> Optional[Dict]:
        """
        3軸評価で最適な事実を選定
        """
        if not facts:
            return None

        # 各事実の3軸スコアを計算
        scored_facts = []
        for fact in facts:
            score = self._calculate_3axis_score(fact)
            scored_facts.append((score, fact))

        # スコア順にソート
        scored_facts.sort(key=lambda x: x[0], reverse=True)

        # 最高スコアの事実を返す
        return scored_facts[0][1]

    def generate_episode(self, person_name: str) -> Optional[Dict]:
        """改良版エピソード生成"""
        if person_name not in self.database:
            print(f"⚠️ {person_name}のデータが存在しません")
            return None

        person_data = self.database[person_name]

        # GROUP_エンティティチェック
        person_id = person_data.get('person_id', '')
        if person_id.startswith('GROUP_'):
            print(f"❌ {person_name}: グループエンティティは禁止")
            return None

        facts = person_data.get('facts', [])
        if not facts:
            print(f"⚠️ {person_name}の事実データが空です")
            return None

        # 3軸評価で最適な事実を選定
        best_fact = self._select_best_fact(facts, person_name)

        if not best_fact:
            print(f"⚠️ {person_name}の適切な事実が選定できません")
            return None

        # エピソード生成
        age = best_fact.get('age', 30)
        fact_text = best_fact.get('fact', '')

        # 基本構造
        episode = f"あなたと同じ{age}歳のとき、{person_name}は{fact_text}"

        # 文末改善
        episode = self._improve_ending(episode)

        # カテゴリを判定
        category = self._categorize_content(fact_text, person_name, best_fact)

        # 文脈追加
        used_phrases = set()
        episode, used_phrases = self._add_contextual_content(
            episode, category, used_phrases
        )

        # 時代背景追加（文字数確保）
        year = self._extract_year(fact_text)
        if year >= 2020:
            episode += "困難な時代にあってなお、希望の光を灯し続けました。"
        elif year >= 2010:
            episode += "新しい時代の息吹を感じさせる快挙でした。"
        elif year >= 2000:
            episode += "21世紀の幕開けとともに、新たな伝説が生まれました。"
        elif year >= 1990:
            episode += "時代の転換点において、重要な役割を果たしました。"
        elif year >= 1980:
            episode += "日本が世界に飛躍する時代の象徴となりました。"
        else:
            episode += "その功績は時代を超えて輝き続けています。"

        # 文字数調整
        if len(episode) < self.MIN_LENGTH:
            episode, used_phrases = self._add_contextual_content(
                episode, category, used_phrases
            )

        # 長すぎる場合の調整
        if len(episode) > self.MAX_LENGTH:
            sentences = episode.split('。')
            if sentences[-1] == '':
                sentences = sentences[:-1]

            while len('。'.join(sentences) + '。') > self.MAX_LENGTH and len(sentences) > 2:
                sentences.pop()

            episode = '。'.join(sentences) + '。'

        return {
            'person_id': person_id,
            'person_name': person_name,
            'age': age,
            'episode_text': episode,
            'text_length': len(episode),
            'confidence': best_fact.get('confidence', 1.0),
            'sources': '|'.join(best_fact.get('sources', ['verified_database'])),
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '3axis_score': self._calculate_3axis_score(best_fact),
            'record_score': best_fact.get('importance_score', 1.0),
            'memory_score': best_fact.get('memory_score', 0.5),
            'empathy_score': best_fact.get('empathy_score', 0.5),
            'category': category,
            'ownership_type': best_fact.get('ownership_type', 'individual')
        }

    def _add_contextual_content(self, episode: str, category: str,
                               used_phrases: Set[str]) -> tuple[str, Set[str]]:
        """カテゴリに応じた文脈追加"""
        available_phrases = [p for p in self.context_templates.get(category, self.context_templates['generic'])
                           if p not in used_phrases]

        if available_phrases:
            chosen_phrase = available_phrases[0]
            episode += chosen_phrase
            used_phrases.add(chosen_phrase)

        return episode, used_phrases

    def _improve_ending(self, text: str) -> str:
        """名詞終わりを感動的な文末に改善"""
        endings = {
            '達成': 'という偉業を成し遂げました',
            '獲得': 'を手にすることができました',
            '受賞': 'という栄誉に輝きました',
            '優勝': 'で頂点に立ちました',
            '成功': 'させることに成功しました',
            '発表': 'を世に送り出しました',
            '創業': 'の第一歩を踏み出しました',
            '設立': 'という新たな挑戦を始めました',
            '実現': 'を実現させました',
            '就任': 'という重責を担うことになりました'
        }

        text_without_period = text.rstrip('。')
        for noun, improvement in endings.items():
            if text_without_period.endswith(noun):
                text = text_without_period[:-len(noun)] + improvement
                break

        if not text.endswith('。'):
            text += '。'

        return text

    def _extract_year(self, fact_text: str) -> int:
        """年代を抽出"""
        import re
        year_match = re.search(r'(\d{4})年', fact_text)
        if year_match:
            return int(year_match.group(1))
        return 2000

    def generate_all_episodes(self, person_list: List[str]) -> List[Dict]:
        """全員分のエピソード生成"""
        episodes = []
        success_count = 0

        print(f"\n📝 改良版エピソード生成開始（{len(person_list)}人）...")
        print("3軸評価（記録20%・記憶40%・共感40%）適用")
        print("=" * 60)

        for person_name in person_list:
            episode = self.generate_episode(person_name)
            if episode:
                episodes.append(episode)
                success_count += 1
                print(f"✅ {person_name}: {episode['text_length']}文字 [{episode['category']}] 3軸={episode['3axis_score']:.2f}")
            else:
                print(f"❌ {person_name}: 生成失敗")

        print("=" * 60)
        print(f"\n📊 生成結果:")
        print(f"   成功: {success_count}/{len(person_list)}件")

        return episodes

    def save_to_csv(self, episodes: List[Dict], filename: str):
        """CSV保存（Excel対応）"""
        if not episodes:
            print("エピソードがありません")
            return

        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['person_id', 'person_name', 'age', 'episode_text',
                         'text_length', 'category', '3axis_score',
                         'record_score', 'memory_score', 'empathy_score',
                         'confidence', 'sources', 'generation_date',
                         'ownership_type']
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()

            for episode in episodes:
                row = {k: episode.get(k, '') for k in fieldnames}
                writer.writerow(row)

        print(f"\n📄 CSV保存完了: {filename}")


def main():
    """メイン処理"""
    print("=" * 60)
    print("改良版エピソード生成システム")
    print("3軸評価と新カテゴリ対応")
    print("=" * 60)

    generator = ImprovedEpisodeGenerator()

    # 全29人のリスト
    all_persons = [
        'イチロー', 'スティーブ・ジョブズ', 'Ado', 'さくらももこ', 'ヘレン・ケラー',
        '安倍晋三', '大谷翔平', 'HIKAKIN', '羽生善治', '宮崎駿',
        '藤井聡太', '黒澤明', '村上春樹', '北野武', '山中伸弥',
        '松田聖子', '錦織圭', '浅田真央', '吉田沙保里',
        '孫正義', '本庶佑', '三木谷浩史', '柳井正', '羽生結弦',
        '坂本龍一', '櫻井翔', 'YOSHIKI', 'あいみょん', '小泉純一郎'
    ]

    # エピソード生成
    episodes = generator.generate_all_episodes(all_persons)

    # 3軸スコアでソート
    episodes.sort(key=lambda x: x.get('3axis_score', 0), reverse=True)

    # CSV保存
    output_file = f"improved_episodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    generator.save_to_csv(episodes, output_file)

    # サンプル表示
    if episodes:
        print("\n🎯 改良版エピソード上位5件:")
        for i, ep in enumerate(episodes[:5], 1):
            print(f"\n{i}. {ep['person_name']} ({ep['age']}歳) [{ep['category']}]")
            print(f"   3軸スコア: {ep['3axis_score']:.2f} (記録={ep['record_score']:.1f}, 記憶={ep['memory_score']:.2f}, 共感={ep['empathy_score']:.2f})")
            print(f"   {ep['episode_text'][:60]}...")

    print("\n✨ 改良版エピソード生成完了！")


if __name__ == "__main__":
    main()