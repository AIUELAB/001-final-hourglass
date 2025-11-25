#!/usr/bin/env python3
"""
固有名詞バリデーションシステム
エピソードに必須の具体的情報（大会名、企業名、作品名等）が含まれているか検証
"""

import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Tuple

class ProperNounValidationSystem:
    """固有名詞バリデーションシステム"""

    def __init__(self):
        """初期化"""
        self.required_elements = self._define_required_elements()
        self.validation_results = []
        self.missing_info_count = 0

    def _define_required_elements(self) -> Dict:
        """必須要素の定義"""
        return {
            'sports': {
                'required': ['大会名', '記録・数値', '年月日'],
                'patterns': {
                    '大会名': r'(五輪|オリンピック|ワールドカップ|WBC|世界選手権|全米オープン|マスターズ|グランプリ|アジア選手権)',
                    '記録': r'\d+[勝敗点本m秒分]|\d+位|\d+冠',
                    '固有名詞': r'[A-Z][a-z]+|「[^」]+」|[ァ-ヴ]+[賞杯]'
                },
                'examples': {
                    '平野美宇': 'アジア選手権、中国選手（丁寧、朱雨玲、陳夢）、準々決勝・準決勝・決勝',
                    '本田宗一郎': 'マン島TTレース、125cc・250ccクラス、1961年'
                }
            },
            'business': {
                'required': ['企業名', '金額・数値', '年'],
                'patterns': {
                    '企業名': r'[株式会社|Inc\.|Corporation|Ltd\.]',
                    '金額': r'\d+[億万千]円|\d+ドル',
                    '製品名': r'「[^」]+」|[A-Z][a-z]+[A-Z]'
                }
            },
            'culture': {
                'required': ['作品名', '出版社・媒体', '数値'],
                'patterns': {
                    '作品名': r'「[^」]+」',
                    '出版社': r'(出版|新聞|雑誌|文学|ジャンプ|マガジン|りぼん)',
                    '数値': r'\d+[万部冊枚億円]'
                }
            },
            'science': {
                'required': ['研究内容', '機関名', '年'],
                'patterns': {
                    '専門用語': r'[A-Z]+[-\d]+|iPS|DNA|RNA',
                    '機関': r'(大学|研究所|学会|ノーベル)',
                    '発見': r'(発見|開発|発明|解明)'
                }
            }
        }

    def validate_episode(self, person_name: str, episode: str, category: str = None) -> Dict:
        """エピソードの固有名詞を検証"""

        validation = {
            'person_name': person_name,
            'has_proper_nouns': False,
            'missing_elements': [],
            'suggestions': [],
            'score': 0
        }

        # カテゴリー推定
        if not category:
            category = self._estimate_category(person_name, episode)

        if category in self.required_elements:
            requirements = self.required_elements[category]

            # 必須要素のチェック
            for element_type, pattern in requirements['patterns'].items():
                if not re.search(pattern, episode):
                    validation['missing_elements'].append(element_type)

            # 例がある場合は提案
            if person_name in requirements.get('examples', {}):
                validation['suggestions'].append(requirements['examples'][person_name])

        # 具体性スコア計算
        validation['score'] = self._calculate_specificity_score(episode)
        validation['has_proper_nouns'] = validation['score'] >= 60

        return validation

    def _estimate_category(self, person_name: str, episode: str) -> str:
        """人物のカテゴリーを推定"""

        # スポーツ関連キーワード
        if any(word in episode for word in ['優勝', '金メダル', '記録', '得点', 'ホームラン', '勝利']):
            return 'sports'

        # ビジネス関連
        if any(word in episode for word in ['創業', '上場', '売上', '億円', '会社', '買収']):
            return 'business'

        # 文化・芸術関連
        if any(word in episode for word in ['出版', '連載', '映画', '作品', '執筆', '公開']):
            return 'culture'

        # 科学・学術関連
        if any(word in episode for word in ['研究', '発見', '開発', 'ノーベル', '論文']):
            return 'science'

        return 'general'

    def _calculate_specificity_score(self, episode: str) -> float:
        """具体性スコアを計算"""
        score = 0

        # 固有名詞（「」内の名前）
        quoted = re.findall(r'「[^」]+」', episode)
        score += len(quoted) * 20

        # 数値
        numbers = re.findall(r'\d+[年月日勝敗点本m秒分億万千円ドル％]', episode)
        score += len(numbers) * 15

        # 固有名詞（カタカナの長い単語）
        katakana = re.findall(r'[ァ-ヴ]{4,}', episode)
        score += len(katakana) * 10

        # アルファベット（団体名、製品名など）
        alphabets = re.findall(r'[A-Z][A-Za-z]+|[A-Z]{2,}', episode)
        score += len(alphabets) * 10

        # 地名・機関名
        places = re.findall(r'(東京|大阪|ニューヨーク|パリ|ロンドン|大学|高校|会社)', episode)
        score += len(places) * 5

        return min(score, 100)

    def create_improved_episodes(self) -> Dict:
        """固有名詞が不足しているエピソードを改善"""

        improved = {
            '平野美宇': {
                'age': 17,
                'year': 2017,
                'original': '中国選手3人を破り優勝という歴史的な偉業',
                'improved': 'あなたと同じ17歳のとき、平野美宇はアジア選手権シングルスで日本人21年ぶりの優勝を達成した。準々決勝で世界ランク1位の丁寧、準決勝で同2位の朱雨玲、決勝で同5位の陳夢と中国トップ選手3人を連破。「ハリケーン平野」と呼ばれ、東京五輪への期待が高まった。この快挙により世界ランキングを8位まで上昇させ、日本卓球界に新時代をもたらした。'
            },
            '本田宗一郎': {
                'age': 55,
                'year': 1961,
                'original': '世界最高峰のオートバイレースで完全制覇',
                'improved': 'あなたと同じ55歳のとき、本田宗一郎はマン島TTレースで日本メーカー初の完全制覇を達成した。1961年6月、125ccクラスと250ccクラスの両部門で1位から5位までをホンダ車が独占。RC162型エンジンの4気筒技術で最高速度200km/hを実現。「世界のHONDA」ブランドを確立し、二輪車生産台数世界一への道を切り開いた。'
            },
            '錦織圭': {
                'age': 24,
                'year': 2014,
                'original': '全米オープンテニスで準優勝',
                'improved': 'あなたと同じ24歳のとき、錦織圭は全米オープンテニスで準優勝し、日本人男子初の4大大会決勝進出を果たした。準決勝で世界ランク1位のノバク・ジョコビッチを6-4,1-6,7-6,6-3で破る大金星。決勝ではマリン・チリッチに敗れたが、賞金145万ドルを獲得。世界ランキング5位に到達し、アジア男子テニスの新たな歴史を刻んだ。'
            },
            '羽生結弦': {
                'age': 23,
                'year': 2018,
                'improved': 'あなたと同じ23歳のとき、羽生結弦は平昌冬季五輪フィギュアスケート男子シングルで金メダルを獲得し、66年ぶりの五輪連覇を達成した。右足首負傷から4か月ぶりの実戦で、SP「バラード第1番」111.68点、FS「SEIMEI」206.17点、合計317.85点を記録。痛み止めを服用しながらの演技で、ディック・バトン以来の偉業を成し遂げた。'
            },
            '大谷翔平': {
                'age': 29,
                'year': 2023,
                'improved': 'あなたと同じ29歳のとき、大谷翔平は第5回WBC（ワールド・ベースボール・クラシック）で日本を14年ぶりの優勝に導きMVPを獲得した。投手として2勝0敗、防御率1.86、打者として打率.435、1本塁打、8打点を記録。決勝の対アメリカ戦では、最終打者のマイク・トラウトを87.5マイルのスライダーで三振に取り、「憧れるのをやめましょう」の名言を残した。'
            },
            'イチロー': {
                'age': 45,
                'year': 2019,
                'improved': 'あなたと同じ45歳のとき、イチローは東京ドームでのアスレチックス戦で現役引退を表明した。日米通算4367安打（NPB1278本、MLB3089本）、MLB史上唯一の10年連続200本安打、シーズン最多安打262本の記録保持者。引退試合には4万6451人が来場し、8回裏の守備交代時にスタンディングオベーション。「後悔などあろうはずがありません」と語った。'
            }
        }

        return improved

    def validate_all_episodes(self, csv_path: str):
        """全エピソードを検証"""

        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        print("固有名詞バリデーション結果")
        print("="*60)

        low_score_episodes = []

        for _, row in df.iterrows():
            result = self.validate_episode(
                row['person_name'],
                row['episode']
            )

            self.validation_results.append(result)

            if result['score'] < 60:
                low_score_episodes.append({
                    'name': row['person_name'],
                    'score': result['score'],
                    'missing': result['missing_elements']
                })
                self.missing_info_count += 1

        # 統計出力
        print(f"検証エピソード数: {len(df)}")
        print(f"固有名詞不足: {self.missing_info_count}件 ({self.missing_info_count/len(df)*100:.1f}%)")

        if low_score_episodes:
            print("\n固有名詞が不足している上位5件:")
            for item in sorted(low_score_episodes, key=lambda x: x['score'])[:5]:
                print(f"  - {item['name']}: スコア{item['score']}")
                if item['missing']:
                    print(f"    不足: {', '.join(item['missing'])}")

        # スコア分布
        scores = [r['score'] for r in self.validation_results]
        print(f"\n具体性スコア分布:")
        print(f"  90-100: {sum(1 for s in scores if s >= 90)}件")
        print(f"  70-89:  {sum(1 for s in scores if 70 <= s < 90)}件")
        print(f"  50-69:  {sum(1 for s in scores if 50 <= s < 70)}件")
        print(f"  0-49:   {sum(1 for s in scores if s < 50)}件")

    def generate_improvement_report(self):
        """改善レポート生成"""

        print("\n改善提案")
        print("="*60)

        improvements = self.create_improved_episodes()

        for person, data in improvements.items():
            print(f"\n【{person}】")
            print(f"  Before: {data.get('original', '(省略)')}")
            print(f"  After:  {data['improved'][:100]}...")
            print(f"  追加情報: 大会名、具体的な記録、日付")


def main():
    """メイン実行"""
    print("固有名詞バリデーションシステム")
    print("="*60)

    # システム初期化
    validator = ProperNounValidationSystem()

    # 最新のデータベースを検証
    csv_path = "objective_improved_episodes_20250923_185441.csv"
    validator.validate_all_episodes(csv_path)

    # 改善提案
    validator.generate_improvement_report()

    # 改善版エピソードの保存
    improvements = validator.create_improved_episodes()

    print("\n" + "="*60)
    print("✅ 固有名詞バリデーション完了")
    print("推奨事項:")
    print("  1. 大会名・企業名・作品名などは必ず正式名称で記載")
    print("  2. 数値・記録は具体的な単位付きで明記")
    print("  3. 年月日は可能な限り詳細に記載")
    print("  4. 人名・地名は正確に表記")


if __name__ == "__main__":
    main()
