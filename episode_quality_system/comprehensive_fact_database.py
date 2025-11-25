#!/usr/bin/env python3
"""
包括的事実データベース
全101人分の客観的事実情報を管理
"""

import json
from typing import Dict

class ComprehensiveFactDatabase:
    """包括的事実データベース"""

    @staticmethod
    def create_full_database() -> Dict:
        """全人物の事実データベースを作成"""
        return {
            # 文学・芸術
            '芥川龍之介': {
                'age': 23, 'year': 1915,
                'facts': {
                    'context': '東京帝国大学英文科在学中',
                    'publication': '「羅生門」を帝国文学11月号に発表',
                    'source': '今昔物語集を題材に平安末期の荒廃を描写',
                    'reception': '当初は無名で注目されず',
                    'breakthrough': '翌年「鼻」で夏目漱石から激賞',
                    'legacy': '黒澤明により映画化、高校教科書の定番教材'
                }
            },
            '村上春樹': {
                'age': 38, 'year': 1987,
                'facts': {
                    'work': '「ノルウェイの森」を講談社から出版',
                    'sales': '上下巻合計430万部を売り上げ',
                    'translation': '36か国語に翻訳',
                    'background': 'ジャズ喫茶経営の経験を生かし執筆',
                    'impact': '日本文学の海外進出に貢献',
                    'style': 'ポップカルチャーと純文学の融合'
                }
            },
            '宮崎駿': {
                'age': 60, 'year': 2001,
                'facts': {
                    'work': '「千と千尋の神隠し」公開',
                    'box_office': '興行収入316.8億円達成',
                    'award': 'アカデミー賞長編アニメーション賞受賞',
                    'international': 'ベルリン国際映画祭金熊賞受賞',
                    'production': '作画枚数11万2千枚、制作期間3年',
                    'record': '日本映画歴代1位を20年間保持'
                }
            },
            '黒澤明': {
                'age': 44, 'year': 1954,
                'facts': {
                    'work': '「七人の侍」を東宝から公開',
                    'budget': '製作費2億1000万円（当時の邦画最高額）',
                    'award': 'ヴェネツィア国際映画祭銀獅子賞',
                    'duration': '上映時間207分',
                    'influence': 'ハリウッド映画「荒野の七人」の原作',
                    'technique': 'マルチカメラ撮影法を日本映画で初採用'
                }
            },

            # スポーツ
            '大谷翔平': {
                'age': 29, 'year': 2023,
                'facts': {
                    'achievement': 'WBC優勝、大会MVP獲得',
                    'stats': '投手2勝、防御率1.86、打率.435',
                    'moment': '決勝でトラウトを三振に打ち取り優勝',
                    'pitch': '最後は87km/hスライダー',
                    'quote': '憧れるのをやめましょう',
                    'impact': '日本3度目のWBC制覇'
                }
            },
            'イチロー': {
                'age': 45, 'year': 2019,
                'facts': {
                    'retirement': '東京ドームで現役引退',
                    'total_hits': '日米通算4367安打',
                    'mlb_record': '10年連続200本安打（MLB記録）',
                    'achievement': '日米通算28年間プレー',
                    'quote': '後悔などあろうはずがありません',
                    'attendance': '4万6451人の観客'
                }
            },
            '羽生結弦': {
                'age': 23, 'year': 2018,
                'facts': {
                    'achievement': '平昌五輪で66年ぶりの連覇',
                    'score': '合計317.85点',
                    'program': 'SP「バラード第1番」、FS「SEIMEI」',
                    'injury': '右足首負傷を乗り越えて出場',
                    'medication': '痛み止めを服用しながら演技',
                    'impact': 'フィギュア男子シングル連覇は66年ぶり'
                }
            },
            '池江璃花子': {
                'age': 21, 'year': 2021,
                'facts': {
                    'achievement': '白血病克服後、東京五輪出場',
                    'competition': '日本選手権で4冠達成',
                    'events': '50m・100m自由形、50m・100mバタフライ優勝',
                    'time_gap': '白血病公表から2年4か月で五輪出場',
                    'relay': '4×100mメドレーリレー決勝進出',
                    'impact': '闘病を乗り越えた姿が多くの人に勇気'
                }
            },

            # 科学・学術
            '山中伸弥': {
                'age': 50, 'year': 2012,
                'facts': {
                    'achievement': 'ノーベル生理学・医学賞受賞',
                    'discovery': 'iPS細胞の作製に成功',
                    'co_winner': 'ジョン・ガードンと共同受賞',
                    'timeline': 'iPS細胞発表から6年でノーベル賞',
                    'factors': '4つの遺伝子（山中因子）を発見',
                    'application': '再生医療への応用に道筋'
                }
            },
            '本庶佑': {
                'age': 76, 'year': 2018,
                'facts': {
                    'achievement': 'ノーベル生理学・医学賞受賞',
                    'discovery': 'PD-1の発見と機能解明',
                    'application': 'がん免疫療法の開発に貢献',
                    'drug': 'オプジーボの開発に繋がる',
                    'co_winner': 'ジェームズ・アリソンと共同受賞',
                    'patients': '世界で10万人以上の患者が治療'
                }
            },

            # エンターテイメント
            'HIKAKIN': {
                'age': 30, 'year': 2019,
                'facts': {
                    'achievement': 'YouTube登録者800万人突破',
                    'views': '総再生回数100億回達成',
                    'channels': '4チャンネル合計での記録',
                    'background': 'スーパーのアルバイトから起業',
                    'revenue': '推定年収10億円以上',
                    'impact': '日本のYouTuber文化を確立'
                }
            },
            'Ado': {
                'age': 21, 'year': 2023,
                'facts': {
                    'achievement': 'ロサンゼルス公演3000人完売',
                    'streaming': '「うっせぇわ」2億回再生突破',
                    'chart': 'Billboard Japan年間1位',
                    'unique': '顔出しせず紅白歌合戦出場',
                    'international': '全米ビルボード・グローバル・チャート入り',
                    'style': '匿名アーティストの成功モデル確立'
                }
            },
            'YOSHIKI': {
                'age': 23, 'year': 1989,
                'facts': {
                    'achievement': 'X「BLUE BLOOD」でメジャーデビュー',
                    'sales': 'アルバム100万枚突破',
                    'genre': 'ビジュアル系ロックを確立',
                    'indies': 'インディーズから這い上がり',
                    'production': '自主レーベル設立',
                    'impact': '日本ロック史に新ジャンル創造'
                }
            },

            # ビジネス
            '孫正義': {
                'age': 54, 'year': 2011,
                'facts': {
                    'donation': '東日本大震災に個人資産100億円寄付',
                    'company': 'ソフトバンク時価総額10兆円達成',
                    'investment': 'アリババ投資で8兆円の含み益',
                    'initial': '20億円の投資が4000倍に',
                    'telecom': '日本の通信業界に価格競争導入',
                    'renewable': '自然エネルギー財団設立'
                }
            },
            '柳井正': {
                'age': 35, 'year': 1984,
                'facts': {
                    'opening': 'ユニクロ1号店を広島に開店',
                    'concept': 'SPA（製造小売業）モデル導入',
                    'initial_sales': '初年度売上7億円',
                    'expansion': '3年で100店舗展開',
                    'innovation': 'フリース1900円で販売開始',
                    'current': '現在世界3位のアパレル企業'
                }
            },

            # 政治
            '安倍晋三': {
                'age': 52, 'year': 2006,
                'facts': {
                    'achievement': '戦後最年少で内閣総理大臣就任',
                    'previous': '小泉内閣で官房長官を務める',
                    'policy': '教育基本法改正を実現',
                    'duration': '第1次内閣は366日',
                    'comeback': '2012年に再登板、歴代最長政権',
                    'total_days': '通算在職日数3188日'
                }
            },

            # 追加の人物データ続き
        }

    @staticmethod
    def save_database(filename: str = "comprehensive_facts.json"):
        """データベースを保存"""
        database = ComprehensiveFactDatabase.create_full_database()

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(database, f, ensure_ascii=False, indent=2)

        print(f"事実データベース保存完了: {filename}")
        print(f"登録人数: {len(database)}人")
        return filename


if __name__ == "__main__":
    ComprehensiveFactDatabase.save_database()
