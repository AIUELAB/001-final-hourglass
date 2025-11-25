#!/usr/bin/env python3
"""
拡張エピソードテンプレート
文字数不足を解消するための改善版テンプレート
"""

import random
from typing import Dict, List, Optional

class ExpandedEpisodeTemplates:
    """拡張エピソードテンプレート"""

    def __init__(self):
        # カテゴリ別拡張テンプレート（150文字以上を保証）
        self.templates = {
            'entertainment': [
                "あなたと同じ{age}歳のとき、{person}は「{work}」を発表し、{achievement}として注目を集めた。"
                "この作品は{impact1}という影響を与え、{fact1}という記録を達成。"
                "さらに{fact2}、{fact3}という実績も重ねた。",

                "{age}歳の{person}は「{work}」で{achievement}を成し遂げ、{category_title}として地位を確立。"
                "{numbers1}の成果を上げ、{impact1}。"
                "その後も{fact1}、{fact2}という業績を残している。",

                "あなたが{age}歳の頃、{person}も同じ年齢で「{work}」により{achievement}。"
                "{impact1}として評価され、{numbers1}という数字を記録。"
                "加えて{fact1}、{fact2}の功績も忘れてはならない。"
            ],

            'sports': [
                "あなたと同じ{age}歳のとき、{person}は{tournament}で{achievement}を達成し、{record}を樹立した。"
                "この快挙は{impact1}として記憶され、{fact1}という成績を残した。"
                "さらに{fact2}、{fact3}という実績も加わった。",

                "{age}歳の{person}は{tournament}において{achievement}、{record}という記録を打ち立てた。"
                "{numbers1}の成績を収め、{impact1}として評価。"
                "続けて{fact1}、{fact2}という偉業も成し遂げている。",

                "あなたが{age}歳の頃、{person}も同じ年齢で{tournament}にて{achievement}を果たした。"
                "{record}という結果を出し、{impact1}。"
                "その実績には{fact1}、{fact2}も含まれている。"
            ],

            'science': [
                "あなたと同じ{age}歳のとき、{person}は{discovery}を発表し、{field}分野で{achievement}を達成した。"
                "この研究は{impact1}という評価を受け、{publications}の論文として発表された。"
                "さらに{recognition}、{fact1}という功績も残している。",

                "{age}歳の{person}は{discovery}により{achievement}、{field}分野の発展に貢献した。"
                "{publications}の研究成果を発表し、{impact1}。"
                "また{recognition}を受賞し、{fact1}という業績も加えた。",

                "あなたが{age}歳の頃、{person}も同じ年齢で{discovery}を通じて{achievement}。"
                "{field}分野において{impact1}という影響を与え、{publications}を発表。"
                "その功績は{recognition}として認められ、{fact1}も達成した。"
            ],

            'business': [
                "あなたと同じ{age}歳のとき、{person}は{company}を創業し、{achievement}を実現した。"
                "この事業は{revenue}の売上を達成し、{impact1}という影響を業界に与えた。"
                "さらに{employees}の雇用を生み、{fact1}という実績も作った。",

                "{age}歳の{person}は{company}において{achievement}、{revenue}という成果を上げた。"
                "{impact1}としてビジネス界で評価され、{employees}を雇用。"
                "また{fact1}、{fact2}という功績も残している。",

                "あなたが{age}歳の頃、{person}も同じ年齢で{company}にて{achievement}を達成。"
                "{revenue}の売上高を記録し、{impact1}。"
                "その成果には{employees}の雇用創出、{fact1}も含まれる。"
            ],

            'literature': [
                "あなたと同じ{age}歳のとき、{person}は「{work}」を執筆し、{award}を受賞した。"
                "この作品は{impact1}という評価を得て、{sales}部の売上を記録。"
                "さらに{translations}か国語に翻訳され、{fact1}という影響も与えた。",

                "{age}歳の{person}は「{work}」により{award}、文学界で{achievement}を成し遂げた。"
                "{sales}部を売り上げ、{impact1}として評価された。"
                "また{translations}か国で翻訳出版され、{fact1}という実績も残した。",

                "あなたが{age}歳の頃、{person}も同じ年齢で「{work}」を発表し{award}。"
                "{impact1}という評価を受け、{sales}部という記録を達成。"
                "その作品は{translations}か国語に翻訳され、{fact1}も実現した。"
            ],

            'history': [
                "あなたと同じ{age}歳のとき、{person}は{event}を実行し、{achievement}を成し遂げた。"
                "この出来事は{impact1}として歴史に刻まれ、{followers}人の支持を得た。"
                "さらに{territory}を統治し、{fact1}という功績も残した。",

                "{age}歳の{person}は{event}において{achievement}、{impact1}という結果をもたらした。"
                "{followers}人の協力を得て、{territory}の支配を確立。"
                "また{fact1}、{fact2}という歴史的業績も達成している。",

                "あなたが{age}歳の頃、{person}も同じ年齢で{event}により{achievement}を実現。"
                "{impact1}として記録され、{followers}人を動かした。"
                "その功績には{territory}の統一、{fact1}も含まれている。"
            ],

            # デフォルト（その他のカテゴリ）
            'default': [
                "あなたと同じ{age}歳のとき、{person}は{achievement}を達成し、{field}分野で活躍した。"
                "この功績は{impact1}として評価され、{fact1}という成果を残した。"
                "さらに{fact2}、{fact3}という実績も重ねている。",

                "{age}歳の{person}は{achievement}により、{field}分野で{impact1}という影響を与えた。"
                "{fact1}という記録を打ち立て、{fact2}も達成。"
                "その活動は{fact3}として、今も記憶されている。"
            ]
        }

        # 接続詞のバリエーション
        self.connectors = {
            'addition': ['さらに', 'また', '加えて', 'その上', '続けて'],
            'result': ['その結果', 'これにより', 'その成果として'],
            'evaluation': ['として評価され', 'という評価を受け', 'として認められ']
        }

    def get_template(self, category: str) -> str:
        """カテゴリに応じたテンプレートを取得"""
        templates = self.templates.get(category, self.templates['default'])
        return random.choice(templates)

    def fill_template(self, template: str, data: Dict[str, str]) -> str:
        """テンプレートにデータを埋め込み"""
        result = template

        # プレースホルダーを置換
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        # 未置換のプレースホルダーを削除
        result = re.sub(r'\{[^}]+\}', '', result)

        return result

    def expand_with_connectors(self, base_text: str, additional_facts: List[str]) -> str:
        """接続詞を使って文章を拡張"""
        if not additional_facts:
            return base_text

        result = base_text

        for i, fact in enumerate(additional_facts[:2]):  # 最大2つまで追加
            if i == 0:
                connector = random.choice(self.connectors['addition'])
            else:
                connector = random.choice(self.connectors['result'])

            result += f"{connector}{fact}。"

        return result

    def ensure_minimum_length(self, episode: str, min_length: int = 130) -> str:
        """最小文字数を保証"""
        if len(episode) >= min_length:
            return episode

        # 文字数が足りない場合、追加情報を付加
        padding_phrases = [
            "この時期の活動は特に注目に値する",
            "同世代の中でも際立った成果といえる",
            "その影響は現在も続いている",
            "多くの人々に影響を与えた功績である"
        ]

        while len(episode) < min_length and padding_phrases:
            phrase = padding_phrases.pop(0)
            episode += phrase + "。"

        return episode[:250]  # 最大文字数を超えないように

import re

def test_expanded_templates():
    """拡張テンプレートのテスト"""

    templates = ExpandedEpisodeTemplates()

    test_data = {
        'entertainment': {
            'age': 27,
            'person': '松本人志',
            'work': '大日本人',
            'achievement': 'お笑い界のカリスマとして認知',
            'category_title': 'お笑い界の革新者',
            'impact1': '日本のお笑い文化に革新',
            'fact1': 'レギュラー番組10本以上',
            'fact2': '映画監督作品4本',
            'fact3': '芸歴40年以上',
            'numbers1': '視聴率20%超'
        },
        'sports': {
            'age': 29,
            'person': '大谷翔平',
            'tournament': 'WBC',
            'achievement': '日本を14年ぶりの優勝に導く',
            'record': 'MVP獲得',
            'impact1': '世界中から賞賛',
            'fact1': 'メジャーリーグで44本塁打',
            'fact2': '投手として10勝5敗',
            'fact3': 'OPS.965',
            'numbers1': '打率.435'
        }
    }

    for category, data in test_data.items():
        template = templates.get_template(category)
        episode = templates.fill_template(template, data)
        episode = templates.ensure_minimum_length(episode)

        print(f"\n【{category}】")
        print(f"文字数: {len(episode)}")
        print(f"エピソード: {episode}")

if __name__ == "__main__":
    test_expanded_templates()
