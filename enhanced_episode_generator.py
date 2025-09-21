#!/usr/bin/env python3
"""
Enhanced Episode Generator - 150-300文字の豊かなエピソード生成
味気ない名詞終わりを避け、感動的な文末で締めくくる
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


class EnhancedEpisodeGenerator:
    """拡張エピソード生成システム（150-300文字）"""

    def __init__(self):
        self.selection_algorithm = EnhancedSelectionAlgorithm()
        self.pdca_guardian = PDCAGuardian()
        self.freshness_checker = FactFreshnessChecker()
        self.database_path = "verified_facts_database_103persons.json"
        self.database = self._load_database()
        self.current_year = datetime.now().year

        # 文字数制限
        self.MIN_LENGTH = 150
        self.MAX_LENGTH = 300

    def _load_database(self) -> Dict:
        """データベース読み込み"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('verified_facts', {})
        except FileNotFoundError:
            print(f"エラー: {self.database_path}が見つかりません")
            return {}

    def _improve_ending(self, text: str) -> str:
        """
        名詞で終わる味気ない文末を改善

        Args:
            text: 元のテキスト

        Returns:
            改善された文末のテキスト
        """
        # 味気ない名詞終わりのパターン
        boring_endings = [
            '達成', '獲得', '受賞', '優勝', '成功', '発表', '創業', '設立',
            '記録', '更新', '突破', '登板', '就任', '当選', '完成', '出版'
        ]

        # 改善用の文末表現
        emotional_endings = {
            '達成': 'という偉業を成し遂げました',
            '獲得': 'を手にすることができました',
            '受賞': 'という栄誉に輝きました',
            '優勝': 'で頂点に立ちました',
            '成功': 'させることに成功しました',
            '発表': 'を世界に向けて発表しました',
            '創業': 'の第一歩を踏み出しました',
            '設立': 'という新たな挑戦を始めました',
            '記録': 'という歴史的な記録を打ち立てました',
            '更新': 'という新記録を樹立しました',
            '突破': 'の大台を突破しました',
            '登板': 'として新たな歴史を刻み始めました',
            '就任': 'という重責を担うことになりました',
            '当選': 'という民意を受け止めました',
            '完成': 'を世に送り出しました',
            '出版': 'を世に問いました'
        }

        # 文末をチェック
        for boring_end in boring_endings:
            if text.endswith(boring_end) or text.endswith(boring_end + '。'):
                # 句点を削除
                if text.endswith('。'):
                    text = text[:-1]

                # 文末を改善
                for key, value in emotional_endings.items():
                    if text.endswith(key):
                        # 名詞を動詞化して感動的に
                        text = text[:-len(key)] + value
                        break

                # 句点を追加
                if not text.endswith('。'):
                    text += '。'
                break

        return text

    def generate_enhanced_episode(self, person_name: str, fact: Dict) -> str:
        """
        150-300文字の拡張エピソード生成

        Args:
            person_name: 人物名
            fact: 事実データ

        Returns:
            拡張されたエピソード文（150-300文字）
        """
        age = fact.get('age', 30)
        fact_text = fact.get('fact', '')
        keywords = fact.get('keywords', [])

        # 基本構造
        base = f"あなたと同じ{age}歳のとき、{person_name}は"

        # ヘレン・ケラーの特別処理（200文字以上）
        if person_name == "ヘレン・ケラー" and age == 7:
            return (f"{base}視覚・聴覚・発話に困難を抱えながらも、「Water（ウォーター）」と初めて発声しました。"
                   f"家庭教師アン・サリヴァンが井戸水を手に流しながら、手話で\"w-a-t-e-r\"を繰り返し示した瞬間、"
                   f"ヘレンの中で「物」と「言葉」が結びつきました。"
                   f"それまで暗闇の中にいた少女に、言葉という光が差し込んだのです。"
                   f"この瞬間は、人間の学習における「理解」の本質を示す、教育史上最も感動的な出来事として今も語り継がれています。")

        # 安倍晋三の特別処理
        elif person_name == "安倍晋三":
            if "在職" in fact_text and "最長" in fact_text:
                return (f"{base}通算在職日数3,188日という歴代最長記録を樹立しました。"
                       f"2019年11月20日に桂太郎の記録を塗り替え、連続在職日数も2,822日で佐藤栄作を超えました。"
                       f"激動の国際情勢の中、日本の舵取りを担い続けた8年余り。"
                       f"アベノミクス、地球儀を俯瞰する外交、そして令和への改元。"
                       f"その功績は賛否両論ありながらも、日本の政治史に大きな足跡を残したことは誰もが認めるところでしょう。")
            elif age == 52:
                return (f"{base}第90代内閣総理大臣に就任し、戦後生まれ初、そして戦後最年少（52歳）の総理大臣となりました。"
                       f"小泉内閣で幹事長・官房長官を歴任し、満を持しての就任。"
                       f"「美しい国、日本」を掲げ、新しい世代のリーダーシップが始まりました。"
                       f"この瞬間、日本の政治は新たな時代への扉を開いたのです。")

        # 大谷翔平の特別処理
        elif person_name == "大谷翔平" and "50-50" in str(keywords):
            return (f"{base}MLB史上誰も成し遂げられなかった「50本塁打50盗塁」を達成しました。"
                   f"最終的には54本塁打、59盗塁という驚異的な数字を記録。"
                   f"さらにドジャースのワールドシリーズ初優勝にも貢献しました。"
                   f"投打の二刀流で世界を驚かせ続けた男が、また新たな伝説を作り上げたのです。"
                   f"この偉業は、野球の常識を覆し続ける大谷の挑戦の象徴として、永遠に語り継がれることでしょう。")

        # その他の人物の拡張処理
        else:
            # 基本のエピソード
            episode = f"{base}{fact_text}"

            # 文脈を追加（50-100文字追加）
            if 'オリンピック' in fact_text or '五輪' in fact_text:
                if '金メダル' in fact_text:
                    episode += "4年に一度の大舞台で世界の頂点に立った瞬間、日本中が歓喜に包まれました。"
                elif '銀メダル' in fact_text:
                    episode += "惜しくも頂点には届かなかったものの、その勇姿は多くの人々に感動と勇気を与えました。"

            elif any(k in fact_text for k in ['史上初', '世界初', '日本初']):
                episode += "前人未到の領域に足を踏み入れたこの瞬間は、歴史に新たな1ページを刻みました。"

            elif '記録' in fact_text:
                episode += "長い間破られることのなかった記録を更新したこの偉業は、努力の結晶として輝き続けています。"

            elif any(k in fact_text for k in ['受賞', '賞']):
                episode += "この栄誉は、長年の努力と献身的な取り組みが認められた証であり、後進への道標となりました。"

            elif any(k in fact_text for k in ['創業', '設立', '開発']):
                episode += "この挑戦は、後の世界を大きく変える第一歩となり、イノベーションの歴史に名を刻みました。"

            # 年代による追加コンテキスト
            year = self.selection_algorithm._extract_year(fact)
            if year >= 2020:
                episode += f"コロナ禍という困難な時代にあってなお、希望の光を灯し続けました。"
            elif year >= 2010:
                episode += f"SNS時代の到来とともに、その偉業は瞬く間に世界中に広がりました。"
            elif year >= 2000:
                episode += f"21世紀の幕開けとともに、新たな時代を切り開く挑戦でした。"
            elif year >= 1990:
                episode += f"バブル後の困難な時代に、日本に勇気と希望を与えました。"

            # 文末を改善
            episode = self._improve_ending(episode)

            # 文字数調整（150-300文字）
            if len(episode) < self.MIN_LENGTH:
                # 追加の感動要素
                if person_name in ['浅田真央', '羽生結弦', '錦織圭']:
                    episode += "その姿は、夢を追い続ける全ての人々への励ましとなっています。"
                elif person_name in ['山中伸弥', '本庶佑']:
                    episode += "この研究成果は、人類の未来に希望をもたらす光となりました。"
                else:
                    episode += "この瞬間は、挑戦することの素晴らしさを私たちに教えてくれます。"

            # 文字数が多すぎる場合はトリミング
            if len(episode) > self.MAX_LENGTH:
                # 最後の句点で区切って調整
                sentences = episode.split('。')
                while len('。'.join(sentences)) > self.MAX_LENGTH and len(sentences) > 2:
                    sentences.pop()
                episode = '。'.join(sentences) + '。'

            return episode

    def generate_episode(self, person_name: str) -> Optional[Dict]:
        """
        エピソード生成

        Args:
            person_name: 人物名

        Returns:
            生成されたエピソード（失敗時はNone）
        """
        if person_name not in self.database:
            print(f"⚠️ {person_name}のデータがデータベースに存在しません")
            return None

        person_data = self.database[person_name]

        # GROUP_エンティティの拒否
        person_id = person_data.get('person_id', '')
        if person_id.startswith('GROUP_'):
            print(f"❌ {person_name}: グループエンティティは禁止されています")
            return None

        facts = person_data.get('facts', [])
        if not facts:
            print(f"⚠️ {person_name}の事実データが空です")
            return None

        # 最適な事実を選定
        best_fact, _ = self.selection_algorithm.select_best_fact(
            facts,
            top_n=3,
            person_name=person_name
        )

        if not best_fact:
            print(f"⚠️ {person_name}の適切な事実が選定できませんでした")
            return None

        # 拡張エピソード生成（150-300文字）
        episode_text = self.generate_enhanced_episode(person_name, best_fact)

        # 文字数チェック
        text_length = len(episode_text)
        if text_length < self.MIN_LENGTH or text_length > self.MAX_LENGTH:
            print(f"⚠️ {person_name}: 文字数違反 ({text_length}文字)")

        # エピソードデータ構築
        episode_data = {
            'person_id': person_data.get('person_id', f'P{str(hash(person_name))[:6]}'),
            'person_name': person_name,
            'age': best_fact.get('age', 30),
            'episode_text': episode_text,
            'text_length': text_length,
            'confidence': best_fact.get('confidence', 1.0),
            'sources': '|'.join(best_fact.get('sources', ['verified_database'])),
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': self.selection_algorithm.calculate_fact_score(best_fact),
            'freshness_year': self.selection_algorithm._extract_year(best_fact),
            'ownership_type': best_fact.get('ownership_type', 'individual')
        }

        return episode_data

    def generate_all_episodes(self, person_list: List[str]) -> List[Dict]:
        """
        複数人物のエピソード一括生成
        """
        episodes = []
        success_count = 0
        failed_persons = []
        length_violations = []

        print(f"\n📝 {len(person_list)}人の拡張エピソード生成開始（150-300文字）...")
        print("=" * 60)

        for person_name in person_list:
            episode = self.generate_episode(person_name)
            if episode:
                episodes.append(episode)
                success_count += 1
                length = episode['text_length']

                if self.MIN_LENGTH <= length <= self.MAX_LENGTH:
                    print(f"✅ {person_name}: {length}文字")
                else:
                    length_violations.append((person_name, length))
                    print(f"⚠️ {person_name}: {length}文字 (違反)")
            else:
                failed_persons.append(person_name)
                print(f"❌ {person_name}: 生成失敗")

        print("=" * 60)
        print(f"\n📊 生成結果:")
        print(f"   成功: {success_count}/{len(person_list)}件")
        print(f"   失敗: {len(failed_persons)}件")
        print(f"   文字数違反: {len(length_violations)}件")

        if length_violations:
            print(f"\n⚠️ 文字数違反:")
            for name, length in length_violations[:5]:
                print(f"   - {name}: {length}文字")

        return episodes

    def save_to_csv(self, episodes: List[Dict], filename: str):
        """CSV保存（Excel対応）"""
        if not episodes:
            print("エピソードがありません")
            return

        # UTF-8 BOM付きで保存
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['person_id', 'person_name', 'age', 'episode_text',
                         'text_length', 'confidence', 'sources', 'generation_date',
                         'algorithm_score', 'freshness_year', 'ownership_type']
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
    print("Enhanced Episode Generator - 拡張エピソード生成システム")
    print("150-300文字の豊かなエピソード")
    print("=" * 60)

    generator = EnhancedEpisodeGenerator()

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
    episodes.sort(key=lambda x: x.get('algorithm_score', 0), reverse=True)

    # CSV保存
    output_file = f"enhanced_episodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    generator.save_to_csv(episodes, output_file)

    # サンプル表示
    if episodes:
        print("\n🎯 拡張エピソードのサンプル:")
        for i, ep in enumerate(episodes[:3], 1):
            print(f"\n{i}. {ep['person_name']} ({ep['age']}歳) - {ep['text_length']}文字:")
            print(f"   {ep['episode_text']}")

    print("\n✨ 拡張エピソード生成完了！")


if __name__ == "__main__":
    main()