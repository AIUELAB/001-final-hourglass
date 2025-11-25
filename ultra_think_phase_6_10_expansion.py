#!/usr/bin/env python3
"""
Ultra Think Phase 6-10 Expansion - 500人規模への拡張
負荷分散とクラッシュ防止のための段階的拡張
"""

import json
import csv
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ExtendedPerson:
    person_name: str
    person_name_ja: str
    person_name_display: str
    birth_year: int
    nationality: str
    occupation: str
    main_category: str
    subcategory: str
    description: str = ""
    historical_impact: int = 8
    educational_value: int = 8
    cultural_significance: int = 9
    global_recognition: int = 7
    grade: str = "A"
    era: str = ""
    phase: int = 6

class UltraThinkPhase6to10Expander:
    """フェーズ6〜10の段階的拡張"""

    def __init__(self):
        self.collected_people: List[Dict[str, Any]] = []
        self.processed_phases = set()
        self.checkpoint_file = "ultra_think_phase_6_10_checkpoint.json"

    def get_phase_6_people(self) -> List[ExtendedPerson]:
        """フェーズ6: ルネサンス期の巨匠と文芸（60人）"""
        return [
            # ルネサンス期の画家
            ExtendedPerson("Sandro Botticelli", "サンドロ・ボッティチェッリ", "ボッティチェッリ", 1445, "イタリア", "画家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Raphael", "ラファエロ・サンティ", "ラファエロ", 1483, "イタリア", "画家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Titian", "ティツィアーノ", "ティツィアーノ", 1488, "イタリア", "画家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Donatello", "ドナテッロ", "ドナテッロ", 1386, "イタリア", "彫刻家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Giotto", "ジョット", "ジョット", 1267, "イタリア", "画家", "歴史的偉人", "フェーズ6", phase=6),

            # バロック期の芸術家
            ExtendedPerson("Caravaggio", "カラヴァッジョ", "カラヴァッジョ", 1571, "イタリア", "画家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Peter Paul Rubens", "ピーテル・パウル・ルーベンス", "ルーベンス", 1577, "フランドル", "画家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Diego Velazquez", "ディエゴ・ベラスケス", "ベラスケス", 1599, "スペイン", "画家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Gian Lorenzo Bernini", "ジャン・ロレンツォ・ベルニーニ", "ベルニーニ", 1598, "イタリア", "彫刻家", "歴史的偉人", "フェーズ6", phase=6),

            # オランダ黄金時代
            ExtendedPerson("Johannes Vermeer", "ヨハネス・フェルメール", "フェルメール", 1632, "オランダ", "画家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Frans Hals", "フランス・ハルス", "ハルス", 1582, "オランダ", "画家", "歴史的偉人", "フェーズ6", phase=6),

            # イギリス文学
            ExtendedPerson("Geoffrey Chaucer", "ジェフリー・チョーサー", "チョーサー", 1343, "イギリス", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("John Milton", "ジョン・ミルトン", "ミルトン", 1608, "イギリス", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("William Blake", "ウィリアム・ブレイク", "ブレイク", 1757, "イギリス", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Lord Byron", "バイロン卿", "バイロン", 1788, "イギリス", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Percy Shelley", "パーシー・シェリー", "シェリー", 1792, "イギリス", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("John Keats", "ジョン・キーツ", "キーツ", 1795, "イギリス", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("William Wordsworth", "ウィリアム・ワーズワース", "ワーズワース", 1770, "イギリス", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Samuel Taylor Coleridge", "サミュエル・テイラー・コールリッジ", "コールリッジ", 1772, "イギリス", "詩人", "歴史的偉人", "フェーズ6", phase=6),

            # フランス文学
            ExtendedPerson("Moliere", "モリエール", "モリエール", 1622, "フランス", "劇作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Voltaire", "ヴォルテール", "ヴォルテール", 1694, "フランス", "思想家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Jean-Jacques Rousseau", "ジャン＝ジャック・ルソー", "ルソー", 1712, "フランス", "思想家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Denis Diderot", "ドゥニ・ディドロ", "ディドロ", 1713, "フランス", "思想家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Montesquieu", "モンテスキュー", "モンテスキュー", 1689, "フランス", "思想家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Honore de Balzac", "オノレ・ド・バルザック", "バルザック", 1799, "フランス", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Alexandre Dumas", "アレクサンドル・デュマ", "デュマ", 1802, "フランス", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Emile Zola", "エミール・ゾラ", "ゾラ", 1840, "フランス", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Marcel Proust", "マルセル・プルースト", "プルースト", 1871, "フランス", "作家", "歴史的偉人", "フェーズ6", phase=6),

            # ドイツ文学・哲学
            ExtendedPerson("Friedrich Schiller", "フリードリヒ・シラー", "シラー", 1759, "ドイツ", "劇作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Heinrich Heine", "ハインリヒ・ハイネ", "ハイネ", 1797, "ドイツ", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Thomas Mann", "トーマス・マン", "トーマス・マン", 1875, "ドイツ", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Hermann Hesse", "ヘルマン・ヘッセ", "ヘッセ", 1877, "ドイツ", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Franz Kafka", "フランツ・カフカ", "カフカ", 1883, "チェコ", "作家", "歴史的偉人", "フェーズ6", phase=6),

            # ロシア文学
            ExtendedPerson("Alexander Pushkin", "アレクサンドル・プーシキン", "プーシキン", 1799, "ロシア", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Nikolai Gogol", "ニコライ・ゴーゴリ", "ゴーゴリ", 1809, "ロシア", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Ivan Turgenev", "イワン・ツルゲーネフ", "ツルゲーネフ", 1818, "ロシア", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Anton Chekhov", "アントン・チェーホフ", "チェーホフ", 1860, "ロシア", "劇作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Maxim Gorky", "マクシム・ゴーリキー", "ゴーリキー", 1868, "ロシア", "作家", "歴史的偉人", "フェーズ6", phase=6),

            # アメリカ文学
            ExtendedPerson("Edgar Allan Poe", "エドガー・アラン・ポー", "ポー", 1809, "アメリカ", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Nathaniel Hawthorne", "ナサニエル・ホーソーン", "ホーソーン", 1804, "アメリカ", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Herman Melville", "ハーマン・メルヴィル", "メルヴィル", 1819, "アメリカ", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Walt Whitman", "ウォルト・ホイットマン", "ホイットマン", 1819, "アメリカ", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Emily Dickinson", "エミリー・ディキンソン", "ディキンソン", 1830, "アメリカ", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Henry James", "ヘンリー・ジェイムズ", "ヘンリー・ジェイムズ", 1843, "アメリカ", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("F. Scott Fitzgerald", "F・スコット・フィッツジェラルド", "フィッツジェラルド", 1896, "アメリカ", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("John Steinbeck", "ジョン・スタインベック", "スタインベック", 1902, "アメリカ", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("William Faulkner", "ウィリアム・フォークナー", "フォークナー", 1897, "アメリカ", "作家", "歴史的偉人", "フェーズ6", phase=6),

            # その他の文学者
            ExtendedPerson("Miguel de Cervantes", "ミゲル・デ・セルバンテス", "セルバンテス", 1547, "スペイン", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Dante Alighieri", "ダンテ・アリギエーリ", "ダンテ", 1265, "イタリア", "詩人", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Hans Christian Andersen", "ハンス・クリスチャン・アンデルセン", "アンデルセン", 1805, "デンマーク", "童話作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Brothers Grimm", "グリム兄弟", "グリム兄弟", 1785, "ドイツ", "童話収集家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Henrik Ibsen", "ヘンリック・イプセン", "イプセン", 1828, "ノルウェー", "劇作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("August Strindberg", "アウグスト・ストリンドベリ", "ストリンドベリ", 1849, "スウェーデン", "劇作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("James Joyce", "ジェイムズ・ジョイス", "ジョイス", 1882, "アイルランド", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Jorge Luis Borges", "ホルヘ・ルイス・ボルヘス", "ボルヘス", 1899, "アルゼンチン", "作家", "歴史的偉人", "フェーズ6", phase=6),
            ExtendedPerson("Gabriel Garcia Marquez", "ガブリエル・ガルシア＝マルケス", "マルケス", 1927, "コロンビア", "作家", "歴史的偉人", "フェーズ6", phase=6),
        ]

    def get_phase_7_people(self) -> List[ExtendedPerson]:
        """フェーズ7: 探検家と発見者（50人）"""
        return [
            # 大航海時代の探検家
            ExtendedPerson("Vasco da Gama", "ヴァスコ・ダ・ガマ", "ダ・ガマ", 1469, "ポルトガル", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Ferdinand Magellan", "フェルディナンド・マゼラン", "マゼラン", 1480, "ポルトガル", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Amerigo Vespucci", "アメリゴ・ヴェスプッチ", "ヴェスプッチ", 1454, "イタリア", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("James Cook", "ジェームズ・クック", "クック", 1728, "イギリス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Francis Drake", "フランシス・ドレーク", "ドレーク", 1540, "イギリス", "航海者", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Henry Hudson", "ヘンリー・ハドソン", "ハドソン", 1565, "イギリス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("John Cabot", "ジョン・カボット", "カボット", 1450, "イタリア", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Jacques Cartier", "ジャック・カルティエ", "カルティエ", 1491, "フランス", "探検家", "歴史的偉人", "フェーズ7", phase=7),

            # 陸地探検家
            ExtendedPerson("Marco Polo", "マルコ・ポーロ", "マルコ・ポーロ", 1254, "イタリア", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Ibn Battuta", "イブン・バットゥータ", "イブン・バットゥータ", 1304, "モロッコ", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("David Livingstone", "デイヴィッド・リヴィングストン", "リヴィングストン", 1813, "イギリス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Henry Morton Stanley", "ヘンリー・モートン・スタンリー", "スタンリー", 1841, "イギリス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Alexander von Humboldt", "アレクサンダー・フォン・フンボルト", "フンボルト", 1769, "ドイツ", "博物学者", "歴史的偉人", "フェーズ7", phase=7),

            # 極地探検家
            ExtendedPerson("Roald Amundsen", "ロアール・アムンセン", "アムンセン", 1872, "ノルウェー", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Robert Falcon Scott", "ロバート・ファルコン・スコット", "スコット", 1868, "イギリス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Ernest Shackleton", "アーネスト・シャクルトン", "シャクルトン", 1874, "イギリス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Robert Peary", "ロバート・ピアリー", "ピアリー", 1856, "アメリカ", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Richard Byrd", "リチャード・バード", "バード", 1888, "アメリカ", "探検家", "歴史的偉人", "フェーズ7", phase=7),

            # 宇宙探検家
            ExtendedPerson("Yuri Gagarin", "ユーリ・ガガーリン", "ガガーリン", 1934, "ソ連", "宇宙飛行士", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Neil Armstrong", "ニール・アームストロング", "アームストロング", 1930, "アメリカ", "宇宙飛行士", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Buzz Aldrin", "バズ・オルドリン", "オルドリン", 1930, "アメリカ", "宇宙飛行士", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("John Glenn", "ジョン・グレン", "グレン", 1921, "アメリカ", "宇宙飛行士", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Alan Shepard", "アラン・シェパード", "シェパード", 1923, "アメリカ", "宇宙飛行士", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Valentina Tereshkova", "ワレンチナ・テレシコワ", "テレシコワ", 1937, "ソ連", "宇宙飛行士", "歴史的偉人", "フェーズ7", phase=7),

            # 科学的発見者
            ExtendedPerson("Gregor Mendel", "グレゴール・メンデル", "メンデル", 1822, "オーストリア", "遺伝学者", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Louis Pasteur", "ルイ・パスツール", "パスツール", 1822, "フランス", "科学者", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Robert Koch", "ロベルト・コッホ", "コッホ", 1843, "ドイツ", "細菌学者", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Alexander Fleming", "アレクサンダー・フレミング", "フレミング", 1881, "イギリス", "細菌学者", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Jonas Salk", "ジョナス・ソーク", "ソーク", 1914, "アメリカ", "医学者", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Wilhelm Roentgen", "ヴィルヘルム・レントゲン", "レントゲン", 1845, "ドイツ", "物理学者", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Henri Becquerel", "アンリ・ベクレル", "ベクレル", 1852, "フランス", "物理学者", "歴史的偉人", "フェーズ7", phase=7),

            # 考古学的発見者
            ExtendedPerson("Howard Carter", "ハワード・カーター", "カーター", 1874, "イギリス", "考古学者", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Heinrich Schliemann", "ハインリッヒ・シュリーマン", "シュリーマン", 1822, "ドイツ", "考古学者", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Arthur Evans", "アーサー・エヴァンス", "エヴァンス", 1851, "イギリス", "考古学者", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Jean-Francois Champollion", "ジャン＝フランソワ・シャンポリオン", "シャンポリオン", 1790, "フランス", "言語学者", "歴史的偉人", "フェーズ7", phase=7),

            # 海洋探検家
            ExtendedPerson("Jacques Cousteau", "ジャック＝イヴ・クストー", "クストー", 1910, "フランス", "海洋探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Thor Heyerdahl", "トール・ヘイエルダール", "ヘイエルダール", 1914, "ノルウェー", "探検家", "歴史的偉人", "フェーズ7", phase=7),

            # 山岳探検家
            ExtendedPerson("Edmund Hillary", "エドモンド・ヒラリー", "ヒラリー", 1919, "ニュージーランド", "登山家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Tenzing Norgay", "テンジン・ノルゲイ", "テンジン", 1914, "ネパール", "登山家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("George Mallory", "ジョージ・マロリー", "マロリー", 1886, "イギリス", "登山家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Reinhold Messner", "ラインホルト・メスナー", "メスナー", 1944, "イタリア", "登山家", "歴史的偉人", "フェーズ7", phase=7),

            # 女性探検家
            ExtendedPerson("Amelia Earhart", "アメリア・イアハート", "イアハート", 1897, "アメリカ", "飛行士", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Beryl Markham", "ベリル・マーカム", "マーカム", 1902, "イギリス", "飛行士", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Isabella Bird", "イザベラ・バード", "バード", 1831, "イギリス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Mary Kingsley", "メアリー・キングスリー", "キングスリー", 1862, "イギリス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Gertrude Bell", "ガートルード・ベル", "ベル", 1868, "イギリス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Freya Stark", "フレヤ・スターク", "スターク", 1893, "イギリス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
            ExtendedPerson("Alexandra David-Neel", "アレクサンドラ・ダヴィッド＝ネール", "ダヴィッド＝ネール", 1868, "フランス", "探検家", "歴史的偉人", "フェーズ7", phase=7),
        ]

    def get_phase_8_people(self) -> List[ExtendedPerson]:
        """フェーズ8: 古代〜中世の支配者と思想家（60人）"""
        return [
            # 古代エジプト
            ExtendedPerson("Ramesses II", "ラムセス2世", "ラムセス2世", -1303, "エジプト", "ファラオ", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Tutankhamun", "ツタンカーメン", "ツタンカーメン", -1341, "エジプト", "ファラオ", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Hatshepsut", "ハトシェプスト", "ハトシェプスト", -1507, "エジプト", "女王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Akhenaten", "アクエンアテン", "アクエンアテン", -1380, "エジプト", "ファラオ", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Nefertiti", "ネフェルティティ", "ネフェルティティ", -1370, "エジプト", "王妃", "歴史的偉人", "フェーズ8", phase=8),

            # 古代メソポタミア
            ExtendedPerson("Hammurabi", "ハンムラビ", "ハンムラビ", -1810, "バビロニア", "王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Nebuchadnezzar II", "ネブカドネザル2世", "ネブカドネザル", -630, "バビロニア", "王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Cyrus the Great", "キュロス大王", "キュロス", -600, "ペルシャ", "王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Darius I", "ダレイオス1世", "ダレイオス", -550, "ペルシャ", "王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Xerxes I", "クセルクセス1世", "クセルクセス", -518, "ペルシャ", "王", "歴史的偉人", "フェーズ8", phase=8),

            # 古代ギリシャ
            ExtendedPerson("Pericles", "ペリクレス", "ペリクレス", -495, "ギリシャ", "政治家", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Leonidas", "レオニダス", "レオニダス", -540, "スパルタ", "王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Themistocles", "テミストクレス", "テミストクレス", -524, "ギリシャ", "政治家", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Herodotus", "ヘロドトス", "ヘロドトス", -484, "ギリシャ", "歴史家", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Thucydides", "トゥキディデス", "トゥキディデス", -460, "ギリシャ", "歴史家", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Hippocrates", "ヒポクラテス", "ヒポクラテス", -460, "ギリシャ", "医学者", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Democritus", "デモクリトス", "デモクリトス", -460, "ギリシャ", "哲学者", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Epicurus", "エピクロス", "エピクロス", -341, "ギリシャ", "哲学者", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Diogenes", "ディオゲネス", "ディオゲネス", -412, "ギリシャ", "哲学者", "歴史的偉人", "フェーズ8", phase=8),

            # 古代ローマ
            ExtendedPerson("Cicero", "キケロ", "キケロ", -106, "ローマ", "政治家", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Marcus Aurelius", "マルクス・アウレリウス", "アウレリウス", 121, "ローマ", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Trajan", "トラヤヌス", "トラヤヌス", 53, "ローマ", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Hadrian", "ハドリアヌス", "ハドリアヌス", 76, "ローマ", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Constantine", "コンスタンティヌス", "コンスタンティヌス", 272, "ローマ", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Diocletian", "ディオクレティアヌス", "ディオクレティアヌス", 244, "ローマ", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Virgil", "ウェルギリウス", "ウェルギリウス", -70, "ローマ", "詩人", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Ovid", "オウィディウス", "オウィディウス", -43, "ローマ", "詩人", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Seneca", "セネカ", "セネカ", -4, "ローマ", "哲学者", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Pliny the Elder", "大プリニウス", "プリニウス", 23, "ローマ", "博物学者", "歴史的偉人", "フェーズ8", phase=8),

            # 中世ヨーロッパ
            ExtendedPerson("Charlemagne", "カール大帝", "カール大帝", 742, "フランク", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Alfred the Great", "アルフレッド大王", "アルフレッド", 849, "イギリス", "王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("William the Conqueror", "征服王ウィリアム", "征服王", 1028, "ノルマンディー", "王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Frederick Barbarossa", "フリードリヒ・バルバロッサ", "バルバロッサ", 1122, "神聖ローマ", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Richard the Lionheart", "獅子心王リチャード", "獅子心王", 1157, "イギリス", "王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Saint Louis", "聖王ルイ", "聖王ルイ", 1214, "フランス", "王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Edward III", "エドワード3世", "エドワード3世", 1312, "イギリス", "王", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Henry V", "ヘンリー5世", "ヘンリー5世", 1386, "イギリス", "王", "歴史的偉人", "フェーズ8", phase=8),

            # 中世イスラム
            ExtendedPerson("Muhammad", "ムハンマド", "ムハンマド", 570, "アラビア", "預言者", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Saladin", "サラディン", "サラディン", 1137, "クルド", "スルタン", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Harun al-Rashid", "ハールーン・アッ＝ラシード", "ハールーン", 763, "アッバース朝", "カリフ", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Al-Khwarizmi", "アル＝フワーリズミー", "フワーリズミー", 780, "ペルシャ", "数学者", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Ibn Sina", "イブン・スィーナー", "アヴィセンナ", 980, "ペルシャ", "医学者", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Ibn Rushd", "イブン・ルシュド", "アヴェロエス", 1126, "アンダルシア", "哲学者", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Al-Ghazali", "アル＝ガザーリー", "ガザーリー", 1058, "ペルシャ", "神学者", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Omar Khayyam", "ウマル・ハイヤーム", "ハイヤーム", 1048, "ペルシャ", "詩人", "歴史的偉人", "フェーズ8", phase=8),

            # ビザンツ帝国
            ExtendedPerson("Justinian I", "ユスティニアヌス1世", "ユスティニアヌス", 482, "ビザンツ", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Theodora", "テオドラ", "テオドラ", 500, "ビザンツ", "皇后", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Basil II", "バシレイオス2世", "バシレイオス", 958, "ビザンツ", "皇帝", "歴史的偉人", "フェーズ8", phase=8),

            # 中世アジア
            ExtendedPerson("Taizong of Tang", "唐太宗", "太宗", 598, "中国", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Wu Zetian", "武則天", "則天武后", 624, "中国", "女帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Xuanzong of Tang", "唐玄宗", "玄宗", 685, "中国", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Taizu of Song", "宋太祖", "趙匡胤", 927, "中国", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Zhu Xi", "朱熹", "朱子", 1130, "中国", "儒学者", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Wang Yangming", "王陽明", "王陽明", 1472, "中国", "思想家", "歴史的偉人", "フェーズ8", phase=8),

            # 中世インド
            ExtendedPerson("Chandragupta Maurya", "チャンドラグプタ", "チャンドラグプタ", -340, "インド", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Harsha", "ハルシャ・ヴァルダナ", "ハルシャ", 590, "インド", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Akbar", "アクバル", "アクバル", 1542, "ムガル", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
            ExtendedPerson("Shah Jahan", "シャー・ジャハーン", "シャー・ジャハーン", 1592, "ムガル", "皇帝", "歴史的偉人", "フェーズ8", phase=8),
        ]

    def get_phase_9_people(self) -> List[ExtendedPerson]:
        """フェーズ9: 産業革命と近代化の立役者（70人）"""
        return [
            # 産業革命の発明家
            ExtendedPerson("James Watt", "ジェームズ・ワット", "ワット", 1736, "イギリス", "発明家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("George Stephenson", "ジョージ・スティーブンソン", "スティーブンソン", 1781, "イギリス", "技術者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Eli Whitney", "イーライ・ホイットニー", "ホイットニー", 1765, "アメリカ", "発明家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Samuel Morse", "サミュエル・モース", "モース", 1791, "アメリカ", "発明家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Alexander Graham Bell", "アレクサンダー・グラハム・ベル", "ベル", 1847, "イギリス", "発明家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Guglielmo Marconi", "グリエルモ・マルコーニ", "マルコーニ", 1874, "イタリア", "発明家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Karl Benz", "カール・ベンツ", "ベンツ", 1844, "ドイツ", "技術者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Gottlieb Daimler", "ゴットリープ・ダイムラー", "ダイムラー", 1834, "ドイツ", "技術者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Rudolf Diesel", "ルドルフ・ディーゼル", "ディーゼル", 1858, "ドイツ", "技術者", "歴史的偉人", "フェーズ9", phase=9),

            # 実業家・産業資本家
            ExtendedPerson("Andrew Carnegie", "アンドリュー・カーネギー", "カーネギー", 1835, "アメリカ", "実業家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("John D. Rockefeller", "ジョン・D・ロックフェラー", "ロックフェラー", 1839, "アメリカ", "実業家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("J.P. Morgan", "J・P・モルガン", "モルガン", 1837, "アメリカ", "銀行家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Cornelius Vanderbilt", "コーネリアス・ヴァンダービルト", "ヴァンダービルト", 1794, "アメリカ", "実業家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Henry Ford", "ヘンリー・フォード", "フォード", 1863, "アメリカ", "実業家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Alfred Krupp", "アルフレート・クルップ", "クルップ", 1812, "ドイツ", "実業家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Cecil Rhodes", "セシル・ローズ", "ローズ", 1853, "イギリス", "実業家", "歴史的偉人", "フェーズ9", phase=9),

            # 社会改革者
            ExtendedPerson("Robert Owen", "ロバート・オウエン", "オウエン", 1771, "イギリス", "社会改革者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Karl Marx", "カール・マルクス", "マルクス", 1818, "ドイツ", "思想家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Friedrich Engels", "フリードリヒ・エンゲルス", "エンゲルス", 1820, "ドイツ", "思想家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Vladimir Lenin", "ウラジーミル・レーニン", "レーニン", 1870, "ロシア", "革命家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Leon Trotsky", "レフ・トロツキー", "トロツキー", 1879, "ロシア", "革命家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Joseph Stalin", "ヨシフ・スターリン", "スターリン", 1878, "ジョージア", "政治家", "歴史的偉人", "フェーズ9", phase=9),

            # 近代政治家
            ExtendedPerson("Abraham Lincoln", "エイブラハム・リンカーン", "リンカーン", 1809, "アメリカ", "大統領", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Ulysses S. Grant", "ユリシーズ・グラント", "グラント", 1822, "アメリカ", "大統領", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("William Gladstone", "ウィリアム・グラッドストン", "グラッドストン", 1809, "イギリス", "首相", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Benjamin Disraeli", "ベンジャミン・ディズレーリ", "ディズレーリ", 1804, "イギリス", "首相", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Giuseppe Mazzini", "ジュゼッペ・マッツィーニ", "マッツィーニ", 1805, "イタリア", "革命家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Camillo Cavour", "カミッロ・カヴール", "カヴール", 1810, "イタリア", "政治家", "歴史的偉人", "フェーズ9", phase=9),

            # 軍事指導者
            ExtendedPerson("Horatio Nelson", "ホレーショ・ネルソン", "ネルソン", 1758, "イギリス", "提督", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Duke of Wellington", "ウェリントン公爵", "ウェリントン", 1769, "イギリス", "将軍", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Robert E. Lee", "ロバート・E・リー", "リー将軍", 1807, "アメリカ", "将軍", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Stonewall Jackson", "ストーンウォール・ジャクソン", "ジャクソン", 1824, "アメリカ", "将軍", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Helmuth von Moltke", "ヘルムート・フォン・モルトケ", "モルトケ", 1800, "ドイツ", "将軍", "歴史的偉人", "フェーズ9", phase=9),

            # 科学者・医学者
            ExtendedPerson("Michael Faraday", "マイケル・ファラデー", "ファラデー", 1791, "イギリス", "物理学者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("James Clerk Maxwell", "ジェームズ・クラーク・マクスウェル", "マクスウェル", 1831, "イギリス", "物理学者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Lord Kelvin", "ケルヴィン卿", "ケルヴィン", 1824, "イギリス", "物理学者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Dmitri Mendeleev", "ドミトリ・メンデレーエフ", "メンデレーエフ", 1834, "ロシア", "化学者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Joseph Lister", "ジョゼフ・リスター", "リスター", 1827, "イギリス", "医学者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Ignaz Semmelweis", "イグナーツ・ゼンメルワイス", "ゼンメルワイス", 1818, "ハンガリー", "医学者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Wilhelm Wundt", "ヴィルヘルム・ヴント", "ヴント", 1832, "ドイツ", "心理学者", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Ivan Pavlov", "イワン・パブロフ", "パブロフ", 1849, "ロシア", "生理学者", "歴史的偉人", "フェーズ9", phase=9),

            # 女性先駆者
            ExtendedPerson("Mary Wollstonecraft", "メアリ・ウルストンクラフト", "ウルストンクラフト", 1759, "イギリス", "女性解放運動家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Harriet Tubman", "ハリエット・タブマン", "タブマン", 1822, "アメリカ", "奴隷解放運動家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Sojourner Truth", "ソジャーナ・トゥルース", "トゥルース", 1797, "アメリカ", "活動家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Elizabeth Cady Stanton", "エリザベス・キャディ・スタントン", "スタントン", 1815, "アメリカ", "女性参政権運動家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Emmeline Pankhurst", "エメリン・パンクハースト", "パンクハースト", 1858, "イギリス", "女性参政権運動家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Jane Addams", "ジェーン・アダムズ", "アダムズ", 1860, "アメリカ", "社会事業家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Ida B. Wells", "アイダ・B・ウェルズ", "ウェルズ", 1862, "アメリカ", "ジャーナリスト", "歴史的偉人", "フェーズ9", phase=9),

            # 芸術家・音楽家
            ExtendedPerson("Franz Schubert", "フランツ・シューベルト", "シューベルト", 1797, "オーストリア", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Felix Mendelssohn", "フェリックス・メンデルスゾーン", "メンデルスゾーン", 1809, "ドイツ", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Robert Schumann", "ロベルト・シューマン", "シューマン", 1810, "ドイツ", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Franz Liszt", "フランツ・リスト", "リスト", 1811, "ハンガリー", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Richard Wagner", "リヒャルト・ワーグナー", "ワーグナー", 1813, "ドイツ", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Giuseppe Verdi", "ジュゼッペ・ヴェルディ", "ヴェルディ", 1813, "イタリア", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Johannes Brahms", "ヨハネス・ブラームス", "ブラームス", 1833, "ドイツ", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Pyotr Tchaikovsky", "ピョートル・チャイコフスキー", "チャイコフスキー", 1840, "ロシア", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Antonin Dvorak", "アントニン・ドヴォルザーク", "ドヴォルザーク", 1841, "チェコ", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Edvard Grieg", "エドヴァルド・グリーグ", "グリーグ", 1843, "ノルウェー", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Gustav Mahler", "グスタフ・マーラー", "マーラー", 1860, "オーストリア", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Claude Debussy", "クロード・ドビュッシー", "ドビュッシー", 1862, "フランス", "作曲家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Maurice Ravel", "モーリス・ラヴェル", "ラヴェル", 1875, "フランス", "作曲家", "歴史的偉人", "フェーズ9", phase=9),

            # 印象派画家
            ExtendedPerson("Edouard Manet", "エドゥアール・マネ", "マネ", 1832, "フランス", "画家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Edgar Degas", "エドガー・ドガ", "ドガ", 1834, "フランス", "画家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Paul Cezanne", "ポール・セザンヌ", "セザンヌ", 1839, "フランス", "画家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Auguste Rodin", "オーギュスト・ロダン", "ロダン", 1840, "フランス", "彫刻家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Pierre-Auguste Renoir", "ピエール＝オーギュスト・ルノワール", "ルノワール", 1841, "フランス", "画家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Paul Gauguin", "ポール・ゴーギャン", "ゴーギャン", 1848, "フランス", "画家", "歴史的偉人", "フェーズ9", phase=9),
            ExtendedPerson("Henri de Toulouse-Lautrec", "アンリ・ド・トゥールーズ＝ロートレック", "ロートレック", 1864, "フランス", "画家", "歴史的偉人", "フェーズ9", phase=9),
        ]

    def get_phase_10_people(self) -> List[ExtendedPerson]:
        """フェーズ10: 20世紀の変革者と現代の先駆者（60人）"""
        return [
            # 20世紀の政治指導者
            ExtendedPerson("Woodrow Wilson", "ウッドロウ・ウィルソン", "ウィルソン", 1856, "アメリカ", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Harry S. Truman", "ハリー・S・トルーマン", "トルーマン", 1884, "アメリカ", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Dwight D. Eisenhower", "ドワイト・D・アイゼンハワー", "アイゼンハワー", 1890, "アメリカ", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Lyndon B. Johnson", "リンドン・ジョンソン", "LBJ", 1908, "アメリカ", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Richard Nixon", "リチャード・ニクソン", "ニクソン", 1913, "アメリカ", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Jimmy Carter", "ジミー・カーター", "カーター", 1924, "アメリカ", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Bill Clinton", "ビル・クリントン", "クリントン", 1946, "アメリカ", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Barack Obama", "バラク・オバマ", "オバマ", 1961, "アメリカ", "大統領", "歴史的偉人", "フェーズ10", phase=10),

            # ヨーロッパの指導者
            ExtendedPerson("David Lloyd George", "デビッド・ロイド・ジョージ", "ロイド・ジョージ", 1863, "イギリス", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Clement Attlee", "クレメント・アトリー", "アトリー", 1883, "イギリス", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Harold Wilson", "ハロルド・ウィルソン", "ウィルソン", 1916, "イギリス", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Tony Blair", "トニー・ブレア", "ブレア", 1953, "イギリス", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Georges Clemenceau", "ジョルジュ・クレマンソー", "クレマンソー", 1841, "フランス", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Francois Mitterrand", "フランソワ・ミッテラン", "ミッテラン", 1916, "フランス", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Jacques Chirac", "ジャック・シラク", "シラク", 1932, "フランス", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Konrad Adenauer", "コンラート・アデナウアー", "アデナウアー", 1876, "ドイツ", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Willy Brandt", "ヴィリー・ブラント", "ブラント", 1913, "ドイツ", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Helmut Schmidt", "ヘルムート・シュミット", "シュミット", 1918, "ドイツ", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Helmut Kohl", "ヘルムート・コール", "コール", 1930, "ドイツ", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Angela Merkel", "アンゲラ・メルケル", "メルケル", 1954, "ドイツ", "首相", "歴史的偉人", "フェーズ10", phase=10),

            # 世界の指導者
            ExtendedPerson("Mikhail Gorbachev", "ミハイル・ゴルバチョフ", "ゴルバチョフ", 1931, "ソ連", "書記長", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Boris Yeltsin", "ボリス・エリツィン", "エリツィン", 1931, "ロシア", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Vladimir Putin", "ウラジーミル・プーチン", "プーチン", 1952, "ロシア", "大統領", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Jiang Zemin", "江沢民", "江沢民", 1926, "中国", "国家主席", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Hu Jintao", "胡錦濤", "胡錦濤", 1942, "中国", "国家主席", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Xi Jinping", "習近平", "習近平", 1953, "中国", "国家主席", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Shinzo Abe", "安倍晋三", "安倍晋三", 1954, "日本", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Narendra Modi", "ナレンドラ・モディ", "モディ", 1950, "インド", "首相", "歴史的偉人", "フェーズ10", phase=10),

            # 平和活動家
            ExtendedPerson("Albert Schweitzer", "アルベルト・シュヴァイツァー", "シュヴァイツァー", 1875, "フランス", "医師", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Ralph Bunche", "ラルフ・バンチ", "バンチ", 1904, "アメリカ", "外交官", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Dag Hammarskjold", "ダグ・ハマーショルド", "ハマーショルド", 1905, "スウェーデン", "国連事務総長", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Lester B. Pearson", "レスター・B・ピアソン", "ピアソン", 1897, "カナダ", "首相", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Wangari Maathai", "ワンガリ・マータイ", "マータイ", 1940, "ケニア", "環境活動家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Muhammad Yunus", "ムハマド・ユヌス", "ユヌス", 1940, "バングラデシュ", "経済学者", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Liu Xiaobo", "劉暁波", "劉暁波", 1955, "中国", "人権活動家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Malala Yousafzai", "マララ・ユスフザイ", "マララ", 1997, "パキスタン", "活動家", "歴史的偉人", "フェーズ10", phase=10),

            # 現代の科学者
            ExtendedPerson("Enrico Fermi", "エンリコ・フェルミ", "フェルミ", 1901, "イタリア", "物理学者", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("J. Robert Oppenheimer", "ロバート・オッペンハイマー", "オッペンハイマー", 1904, "アメリカ", "物理学者", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Edward Teller", "エドワード・テラー", "テラー", 1908, "ハンガリー", "物理学者", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Murray Gell-Mann", "マレー・ゲルマン", "ゲルマン", 1929, "アメリカ", "物理学者", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Kip Thorne", "キップ・ソーン", "ソーン", 1940, "アメリカ", "物理学者", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Roger Penrose", "ロジャー・ペンローズ", "ペンローズ", 1931, "イギリス", "物理学者", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Edward Witten", "エドワード・ウィッテン", "ウィッテン", 1951, "アメリカ", "物理学者", "歴史的偉人", "フェーズ10", phase=10),

            # 現代芸術家・建築家
            ExtendedPerson("Pablo Picasso", "パブロ・ピカソ", "ピカソ", 1881, "スペイン", "画家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Henri Matisse", "アンリ・マティス", "マティス", 1869, "フランス", "画家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Salvador Dali", "サルバドール・ダリ", "ダリ", 1904, "スペイン", "画家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Jackson Pollock", "ジャクソン・ポロック", "ポロック", 1912, "アメリカ", "画家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Andy Warhol", "アンディ・ウォーホル", "ウォーホル", 1928, "アメリカ", "芸術家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Frank Lloyd Wright", "フランク・ロイド・ライト", "ライト", 1867, "アメリカ", "建築家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Le Corbusier", "ル・コルビュジエ", "コルビュジエ", 1887, "スイス", "建築家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Ludwig Mies van der Rohe", "ミース・ファン・デル・ローエ", "ミース", 1886, "ドイツ", "建築家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("I.M. Pei", "イオ・ミン・ペイ", "ペイ", 1917, "中国", "建築家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Zaha Hadid", "ザハ・ハディド", "ハディド", 1950, "イラク", "建築家", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Tadao Ando", "安藤忠雄", "安藤忠雄", 1941, "日本", "建築家", "歴史的偉人", "フェーズ10", phase=10),

            # その他の現代の先駆者
            ExtendedPerson("Coco Chanel", "ココ・シャネル", "シャネル", 1883, "フランス", "デザイナー", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Christian Dior", "クリスチャン・ディオール", "ディオール", 1905, "フランス", "デザイナー", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Yves Saint Laurent", "イヴ・サンローラン", "サンローラン", 1936, "フランス", "デザイナー", "歴史的偉人", "フェーズ10", phase=10),
            ExtendedPerson("Giorgio Armani", "ジョルジオ・アルマーニ", "アルマーニ", 1934, "イタリア", "デザイナー", "歴史的偉人", "フェーズ10", phase=10),
        ]

    def load_checkpoint(self):
        """チェックポイントの読み込み"""
        try:
            if Path(self.checkpoint_file).exists():
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_phases = set(data.get('processed_phases', []))
                    self.collected_people = data.get('collected_people', [])
                    logger.info(f"チェックポイント読み込み完了: {len(self.processed_phases)}フェーズ処理済み")
        except Exception as e:
            logger.error(f"チェックポイント読み込み失敗: {e}")

    def save_checkpoint(self):
        """チェックポイントの保存"""
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'processed_phases': list(self.processed_phases),
                    'collected_people': self.collected_people
                }, f, ensure_ascii=False, indent=2)
            logger.info("チェックポイント保存完了")
        except Exception as e:
            logger.error(f"チェックポイント保存失敗: {e}")

    def process_phase(self, phase_num: int, people_getter):
        """フェーズの処理（負荷分散）"""
        if phase_num in self.processed_phases:
            logger.info(f"フェーズ{phase_num}は処理済みです")
            return

        logger.info(f"フェーズ{phase_num}の処理を開始...")
        people = people_getter()

        # 10人ずつのバッチで処理
        batch_size = 10
        for i in range(0, len(people), batch_size):
            batch = people[i:i+batch_size]
            logger.info(f"バッチ処理中: {i+1}-{min(i+batch_size, len(people))}/{len(people)}")

            for person in batch:
                person_dict = asdict(person)
                self.collected_people.append(person_dict)

            # API負荷対策
            time.sleep(1)

        self.processed_phases.add(phase_num)
        self.save_checkpoint()
        logger.info(f"フェーズ{phase_num}完了: {len(people)}人追加")

    def save_phase_data(self, phase_num: int, people: List[ExtendedPerson]):
        """フェーズごとのデータ保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # CSV保存
        csv_file = f"ultra_think_phase_{phase_num}_{timestamp}.csv"
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            if people:
                fieldnames = list(asdict(people[0]).keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for person in people:
                    writer.writerow(asdict(person))

        # JSON保存
        json_file = f"ultra_think_phase_{phase_num}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(p) for p in people], f, ensure_ascii=False, indent=2)

        logger.info(f"フェーズ{phase_num}データ保存: {csv_file}, {json_file}")

    def run_expansion(self):
        """フェーズ6〜10の拡張実行"""
        self.load_checkpoint()

        phases = [
            (6, self.get_phase_6_people),
            (7, self.get_phase_7_people),
            (8, self.get_phase_8_people),
            (9, self.get_phase_9_people),
            (10, self.get_phase_10_people),
        ]

        for phase_num, getter in phases:
            try:
                self.process_phase(phase_num, getter)
                # フェーズ間の休憩
                time.sleep(3)
            except Exception as e:
                logger.error(f"フェーズ{phase_num}でエラー: {e}")
                # エラーでも継続
                continue

        # 最終データ保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_csv = f"ultra_think_phase_6_10_complete_{timestamp}.csv"
        final_json = f"ultra_think_phase_6_10_complete_{timestamp}.json"

        # 全フィールドを収集
        all_fields = set()
        for person in self.collected_people:
            all_fields.update(person.keys())

        # CSV保存
        with open(final_csv, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = sorted(list(all_fields))
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for person in self.collected_people:
                writer.writerow(person)

        # JSON保存
        with open(final_json, 'w', encoding='utf-8') as f:
            json.dump(self.collected_people, f, ensure_ascii=False, indent=2)

        logger.info(f"""
        ========================================
        フェーズ6〜10拡張完了！
        ========================================
        総人数: {len(self.collected_people)}人
        処理フェーズ: {sorted(list(self.processed_phases))}
        出力ファイル:
        - {final_csv}
        - {final_json}
        ========================================
        """)

        return self.collected_people

def main():
    """メイン実行"""
    logger.info("""
    ========================================
    Ultra Think Phase 6-10 Expansion
    500人規模への段階的拡張開始
    ========================================
    """)

    expander = UltraThinkPhase6to10Expander()
    people = expander.run_expansion()

    logger.info(f"✅ 拡張完了: {len(people)}人のデータを収集")

if __name__ == "__main__":
    main()
