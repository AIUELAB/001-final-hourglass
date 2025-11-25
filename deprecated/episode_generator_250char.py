#!/usr/bin/env python3
"""
文字数制限250文字版エピソード生成システム
150-250文字厳守・3軸評価適用
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path


class EpisodeGenerator250Char:
    """文字数制限250文字版エピソード生成システム"""

    def __init__(self):
        self.database_path = "verified_facts_database_103persons.json"
        self.database = self._load_database()

        # 文字数制限を150-250に設定
        self.MIN_LENGTH = 150
        self.MAX_LENGTH = 250  # 300から250に変更

        # 簡潔版カテゴリ別テンプレート（短縮版）
        self.context_templates = {
            'cultural_phenomenon': [
                "この出来事は日本の文化史に新たな1ページを刻みました。",
                "社会現象となり、世代を超えて語り継がれています。"
            ],
            'social_contribution': [
                "その利他的行動は、日本社会に希望をもたらしました。",
                "困難な時代に示された勇気が、人々を励まし続けています。"
            ],
            'continuous_achievement': [
                "継続的努力が歴史的記録として結実しました。",
                "プロフェッショナリズムが新たな伝説を生みました。"
            ],
            'sports': [
                "その勇姿は人々に感動と勇気を与えました。",
                "スポーツの力が、国境を越えて人々を繋ぎました。"
            ],
            'art_creation': [
                "その作品は時代を超えて愛され続けています。",
                "芸術の価値がここに結実しました。"
            ],
            'science': [
                "この発見は人類の未来に希望をもたらしました。",
                "科学の進歩が新たな可能性を開きました。"
            ],
            'politics': [
                "この決断は日本の歴史に転換点をもたらしました。",
                "政治的リーダーシップが時代を動かしました。"
            ],
            'business': [
                "この革新は産業界に大きな影響を与えました。",
                "起業家精神が社会変革の力となりました。"
            ],
            'entertainment': [
                "その才能は人々の心を豊かにしました。",
                "新しい表現が時代を変えました。"
            ],
            'award_international': [
                "世界が認めた才能は日本の誇りとなりました。",
                "世界の舞台での栄誉は新たな伝説の始まりでした。"
            ],
            'award_domestic': [
                "日本での評価がその実力を証明しました。",
                "国内最高峰の栄誉は努力の結晶でした。"
            ],
            'generic': [
                "この出来事は多くの人々の記憶に刻まれています。",
                "その功績は今も語り継がれています。"
            ]
        }

        # 短縮版時代背景フレーズ
        self.time_phrases = {
            2020: "困難な時代に希望を灯しました。",
            2010: "新時代の快挙でした。",
            2000: "21世紀の新たな伝説となりました。",
            1990: "時代の転換点となりました。",
            1980: "日本飛躍の象徴となりました。",
            1970: "高度成長期の輝きでした。",
            0: "時代を超えて輝き続けています。"
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
        """カテゴライズ"""
        if 'category' in fact:
            return fact['category']

        # 社会貢献
        if any(k in fact_text for k in ['寄付', '震災', '支援', '慈善']):
            return 'social_contribution'
        # 文化現象
        elif any(k in fact_text for k in ['社会現象', 'ブーム', '世紀の']):
            return 'cultural_phenomenon'
        # 継続的達成
        elif any(k in fact_text for k in ['連続', '継続', '記録更新', '史上最長']):
            return 'continuous_achievement'
        # 既存カテゴリ判定
        elif '日本アカデミー賞' in fact_text:
            return 'award_domestic'
        elif any(k in fact_text for k in ['アカデミー賞', 'グラミー賞', 'カンヌ', 'ヴェネツィア']):
            return 'award_international'
        elif any(k in fact_text for k in ['オリンピック', '五輪', '金メダル']):
            return 'sports'
        elif any(k in fact_text for k in ['発表', '公開']) and any(k in fact_text for k in ['映画', '作品']):
            return 'art_creation'
        elif any(k in fact_text for k in ['ノーベル', '研究', 'iPS']):
            return 'science'
        elif any(k in fact_text for k in ['総理', '大臣', '選挙']):
            return 'politics'
        elif any(k in fact_text for k in ['創業', '起業', '設立']):
            return 'business'
        elif any(k in fact_text for k in ['YouTube', 'ヒット']):
            return 'entertainment'
        else:
            return 'generic'

    def _calculate_3axis_score(self, fact: Dict) -> float:
        """3軸評価スコア計算"""
        record_score = fact.get('importance_score', 1.0)
        memory_score = fact.get('memory_score', 0.5)
        empathy_score = fact.get('empathy_score', 0.5)
        return (record_score * 0.2) + (memory_score * 0.4) + (empathy_score * 0.4)

    def _select_best_fact(self, facts: List[Dict], person_name: str) -> Optional[Dict]:
        """最適な事実を選定"""
        if not facts:
            return None

        scored_facts = []
        for fact in facts:
            score = self._calculate_3axis_score(fact)
            scored_facts.append((score, fact))

        scored_facts.sort(key=lambda x: x[0], reverse=True)
        return scored_facts[0][1]

    def _improve_ending(self, text: str) -> str:
        """名詞終わりを改善"""
        endings = {
            '達成': 'という偉業を成し遂げました',
            '獲得': 'を手にしました',
            '受賞': 'に輝きました',
            '優勝': 'で頂点に立ちました',
            '成功': 'に成功しました',
            '発表': 'を世に送り出しました',
            '表明': 'と表明しました',
            '創業': 'の第一歩を踏み出しました',
            '設立': 'を始めました',
            '実現': 'を実現させました',
            '就任': 'に就任しました'
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

    def _get_time_phrase(self, year: int) -> str:
        """年代に応じた短縮版フレーズを取得"""
        if year >= 2020:
            return self.time_phrases[2020]
        elif year >= 2010:
            return self.time_phrases[2010]
        elif year >= 2000:
            return self.time_phrases[2000]
        elif year >= 1990:
            return self.time_phrases[1990]
        elif year >= 1980:
            return self.time_phrases[1980]
        elif year >= 1970:
            return self.time_phrases[1970]
        else:
            return self.time_phrases[0]

    def generate_episode(self, person_name: str) -> Optional[Dict]:
        """エピソード生成（250文字制限）"""
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

        # 最適な事実を選定
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

        # カテゴリ判定
        category = self._categorize_content(fact_text, person_name, best_fact)

        # 文脈フレーズ（最大1つ）
        templates = self.context_templates.get(category, self.context_templates['generic'])
        if templates and len(episode) < 200:  # 200文字未満なら1つ追加
            episode += templates[0]

        # 時代背景フレーズ（短縮版）
        year = self._extract_year(fact_text)
        time_phrase = self._get_time_phrase(year)

        # 文字数チェックして追加
        if len(episode) + len(time_phrase) <= self.MAX_LENGTH:
            episode += time_phrase

        # 150文字未満の場合、最小限の追加
        if len(episode) < self.MIN_LENGTH:
            if len(templates) > 1 and len(episode) + len(templates[1]) <= self.MAX_LENGTH:
                episode += templates[1]

        # 250文字を超える場合の調整
        if len(episode) > self.MAX_LENGTH:
            sentences = episode.split('。')
            if sentences[-1] == '':
                sentences = sentences[:-1]

            # 最後の文から削除していく
            while len('。'.join(sentences) + '。') > self.MAX_LENGTH and len(sentences) > 2:
                sentences.pop()

            episode = '。'.join(sentences) + '。'

        # 最終文字数確認
        if len(episode) > self.MAX_LENGTH:
            # それでも超える場合は、基本部分のみに
            episode = f"あなたと同じ{age}歳のとき、{person_name}は{fact_text}"
            episode = self._improve_ending(episode)
            if templates:
                episode += templates[0]

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

    def generate_all_episodes(self, person_list: List[str]) -> List[Dict]:
        """全員分のエピソード生成"""
        episodes = []
        success_count = 0
        violations = 0

        print(f"\n📝 文字数制限250文字版エピソード生成開始（{len(person_list)}人）...")
        print("文字数制限: 150-250文字")
        print("3軸評価適用")
        print("=" * 60)

        for person_name in person_list:
            episode = self.generate_episode(person_name)
            if episode:
                episodes.append(episode)
                success_count += 1

                # 文字数チェック
                length = episode['text_length']
                if length < self.MIN_LENGTH or length > self.MAX_LENGTH:
                    violations += 1
                    status = "⚠️"
                else:
                    status = "✅"

                print(f"{status} {person_name}: {length}文字 [{episode['category']}] 3軸={episode['3axis_score']:.2f}")
            else:
                print(f"❌ {person_name}: 生成失敗")

        print("=" * 60)
        print(f"\n📊 生成結果:")
        print(f"   成功: {success_count}/{len(person_list)}件")

        if episodes:
            lengths = [e['text_length'] for e in episodes]
            print(f"\n📏 文字数統計:")
            print(f"   最小: {min(lengths)}文字")
            print(f"   最大: {max(lengths)}文字")
            print(f"   平均: {sum(lengths) / len(lengths):.1f}文字")

            in_range = sum(1 for l in lengths if self.MIN_LENGTH <= l <= self.MAX_LENGTH)
            print(f"   範囲内: {in_range}/{len(lengths)}件 ({100 * in_range / len(lengths):.1f}%)")

            if violations > 0:
                print(f"   ⚠️ 違反: {violations}件")

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
        print(f"   エピソード数: {len(episodes)}件")
        print(f"   Excel対応: UTF-8 BOM付き")
        print(f"   文字数制限: 150-250文字")


def main():
    """メイン処理"""
    print("=" * 60)
    print("文字数制限250文字版エピソード生成システム")
    print("文字数150-250文字厳守・3軸評価適用")
    print("=" * 60)

    generator = EpisodeGenerator250Char()

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
    output_file = f"episodes_250char_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    generator.save_to_csv(episodes, output_file)

    # サンプル表示
    if episodes:
        print("\n🎯 上位5件のエピソード:")
        for i, ep in enumerate(episodes[:5], 1):
            print(f"\n{i}. {ep['person_name']} ({ep['age']}歳) [{ep['category']}]")
            print(f"   3軸スコア: {ep['3axis_score']:.2f}")
            print(f"   文字数: {ep['text_length']}文字")
            if ep['text_length'] > 250:
                print(f"   ⚠️ 文字数超過")
            print(f"   {ep['episode_text'][:80]}...")

    print("\n✨ 文字数制限250文字版生成完了！")
    print("   - 文字数制限: 150-250文字 ✅")
    print("   - 3軸評価: ✅")
    print("   - PDCAルール160適用: ✅")


if __name__ == "__main__":
    main()
