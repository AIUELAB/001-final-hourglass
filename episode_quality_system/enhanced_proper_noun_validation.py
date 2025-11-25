#!/usr/bin/env python3
"""
強化版固有名詞バリデーションシステム
作品名・大会名・企業名が必須であることを厳格にチェック
"""

import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class EnhancedProperNounValidation:
    """強化版固有名詞バリデーション"""

    def __init__(self):
        """初期化"""
        self.validation_rules = self._define_validation_rules()
        self.category_mapping = self._define_category_mapping()

    def _define_category_mapping(self) -> Dict:
        """人物のカテゴリーマッピング"""
        return {
            'sports': [
                '大谷翔平', 'イチロー', '松井秀喜', '野茂英雄', '田中将大', '王貞治', '長嶋茂雄',
                '羽生結弦', '浅田真央', '荒川静香', '高橋尚子', '野口みずき', '北島康介',
                '内村航平', '室伏広治', '吉田沙保里', '伊調馨', '古賀稔彦', '吉田秀彦',
                '錦織圭', '大坂なおみ', '松山英樹', '石川遼', '渋野日向子', '宮里藍',
                '上田桃子', '平野美宇', '池江璃花子', '紀平梨花', '八村塁', '久保建英'
            ],
            'entertainment': [
                '星野源', '米津玄師', 'あいみょん', 'YOSHIKI', 'Ado', '坂本龍一', '松田聖子',
                '新海誠', '宮崎駿', '北野武', '是枝裕和', '黒澤明', '綾瀬はるか', '新垣結衣',
                '岡田准一', '渡辺謙', '福山雅治', '松本人志', '櫻井翔', '手塚治虫'
            ],
            'literature': [
                '西野亮廣', '村上春樹', '又吉直樹', '芥川龍之介', '夏目漱石', '三島由紀夫',
                '大江健三郎', '川端康成', 'さくらももこ'
            ],
            'business': [
                '孫正義', '三木谷浩史', '柳井正', '前澤友作', '堀江貴文', '藤田晋',
                '落合陽一', '松下幸之助', '盛田昭夫', '稲盛和夫', '豊田章男', 'HIKAKIN'
            ],
            'science': [
                '山中伸弥', '本庶佑', '大隅良典', '梶田隆章', '遠藤章', '満屋裕明'
            ],
            'art': [
                '草間彌生', '奈良美智', '村上隆', '横尾忠則', '安藤忠雄'
            ],
            'music': [
                '小澤征爾', '野村萬斎'
            ],
            'politics': [
                '安倍晋三', '小泉純一郎'
            ],
            'other': [
                'イモトアヤコ', 'ヘレン・ケラー', 'マザー・テレサ', 'マリー・キュリー',
                'マーティン・ルーサー・キング・ジュニア', 'アルベルト・アインシュタイン',
                'イーロン・マスク', 'ジェフ・ベゾス', 'スティーブ・ジョブズ', 'ビル・ゲイツ',
                '羽生善治', '藤井聡太', '福沢諭吉'
            ]
        }

    def _define_validation_rules(self) -> Dict:
        """カテゴリー別必須要素"""
        return {
            'sports': {
                'required_patterns': [
                    r'(五輪|オリンピック|ワールドカップ|WBC|世界選手権|全米オープン|全英オープン|マスターズ|グランプリ|アジア選手権|日本選手権|甲子園|箱根駅伝|NBA|MLB|NPB|Jリーグ|ラ・リーガ|プレミアリーグ|ツアー|グランドスラム)',
                    r'\d+[勝敗本塁打得点ゴール試合回戦メートルキロ秒分時間]'
                ],
                'error_message': '大会名・リーグ名と具体的な記録が必要'
            },
            'entertainment': {
                'required_patterns': [
                    r'「[^」]+」',  # 作品名（必須）
                    r'(視聴率|興行収入|動画再生|ダウンロード|枚|部|億円|万人)'
                ],
                'error_message': '作品名（「」付き）と数値データが必要'
            },
            'literature': {
                'required_patterns': [
                    r'「[^」]+」',  # 作品名（必須）
                    r'(出版|連載|発表|執筆|賞)'
                ],
                'error_message': '作品名（「」付き）と出版情報が必要'
            },
            'business': {
                'required_patterns': [
                    r'(株式会社|会社|楽天|ソフトバンク|ユニクロ|ZOZO|トヨタ|ソニー|パナソニック|京セラ|ライブドア|サイバーエージェント|Microsoft|Amazon|Apple)',
                    r'\d+[億万千円ドル]'
                ],
                'error_message': '企業名と金額・数値が必要'
            },
            'science': {
                'required_patterns': [
                    r'(ノーベル|iPS|PD-1|オートファジー|ニュートリノ|スタチン|HIV|細胞|遺伝子)',
                    r'(賞|発見|開発|解明)'
                ],
                'error_message': '研究内容と受賞・発見情報が必要'
            },
            'art': {
                'required_patterns': [
                    r'(「[^」]+」|展覧会|個展|美術館|ギャラリー)',
                    r'(作品|シリーズ|展示)'
                ],
                'error_message': '作品名または展覧会名が必要'
            },
            'music': {
                'required_patterns': [
                    r'(交響楽団|オーケストラ|歌劇場|五輪|「[^」]+」)',
                    r'(指揮|監督|演奏|公演)'
                ],
                'error_message': '楽団名または作品名が必要'
            }
        }

    def get_person_category(self, person_name: str) -> Optional[str]:
        """人物のカテゴリーを取得"""
        for category, persons in self.category_mapping.items():
            if person_name in persons:
                return category
        return 'other'

    def validate_episode(self, person_name: str, episode: str) -> Dict:
        """エピソードの固有名詞を検証"""

        result = {
            'person_name': person_name,
            'category': self.get_person_category(person_name),
            'is_valid': True,
            'missing_elements': [],
            'has_work_title': False,
            'has_proper_nouns': False,
            'issues': []
        }

        # テンプレート文章のチェック
        template_phrases = [
            '専門分野で重要な成果を達成した',
            '歴史的な偉業を成し遂げた',
            '具体的な記録や詳細は資料により異なる',
            'この時期の活動が後のキャリアの基礎となった',
            '業界内での評価を確立し'
        ]

        for phrase in template_phrases:
            if phrase in episode:
                result['is_valid'] = False
                result['issues'].append(f'テンプレート文章: "{phrase[:20]}..."')

        # カテゴリー別検証
        category = result['category']
        if category in self.validation_rules and category != 'other':
            rules = self.validation_rules[category]

            for pattern in rules['required_patterns']:
                if not re.search(pattern, episode):
                    result['is_valid'] = False
                    result['missing_elements'].append(rules['error_message'])
                    break

        # 作品名チェック（「」の有無）
        quoted_items = re.findall(r'「[^」]+」', episode)
        result['has_work_title'] = len(quoted_items) > 0

        # エンターテインメント・文学系は作品名必須
        if category in ['entertainment', 'literature'] and not result['has_work_title']:
            result['is_valid'] = False
            result['issues'].append('作品名（「」付き）が必須')

        # 固有名詞の総合チェック
        proper_nouns = len(quoted_items) + len(re.findall(r'[A-Z][a-z]+|[A-Z]{2,}', episode))
        result['has_proper_nouns'] = proper_nouns > 0

        return result

    def validate_all_episodes(self, csv_path: str) -> List[Dict]:
        """全エピソードを検証"""

        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        invalid_episodes = []

        for _, row in df.iterrows():
            validation = self.validate_episode(row['person_name'], row['episode'])

            if not validation['is_valid']:
                invalid_episodes.append({
                    'name': row['person_name'],
                    'category': validation['category'],
                    'issues': validation['issues'],
                    'missing': validation['missing_elements']
                })

        return invalid_episodes

def main():
    """メイン実行"""

    validator = EnhancedProperNounValidation()

    # 現在のCSVを検証
    csv_path = "/Users/admin/Documents/AIUELAB/001-final-hourglass/episode_quality_system/final_complete_episodes_20250923_190951.csv"

    print("強化版固有名詞バリデーション")
    print("="*60)

    invalid = validator.validate_all_episodes(csv_path)

    if invalid:
        print(f"\n問題のあるエピソード: {len(invalid)}件")
        print("\nカテゴリー別内訳:")

        categories = {}
        for item in invalid:
            cat = item['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item['name'])

        for cat, names in categories.items():
            print(f"  {cat}: {len(names)}件")
            for name in names[:3]:
                print(f"    - {name}")

        print("\n主な問題:")
        for item in invalid[:5]:
            print(f"  {item['name']} ({item['category']})")
            for issue in item['issues']:
                print(f"    ⚠️ {issue}")
    else:
        print("✅ すべてのエピソードが検証をパスしました")

if __name__ == "__main__":
    main()
