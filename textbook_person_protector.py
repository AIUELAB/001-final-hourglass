#!/usr/bin/env python3
"""
教科書掲載人物保護システム
Textbook Person Protection System

小中高の教科書に掲載されている人物は
教育的重要性から削除対象外とする
"""

import json
import logging
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Subject(Enum):
    """教科目分類"""
    JAPANESE_HISTORY = "日本史"
    WORLD_HISTORY = "世界史"
    GEOGRAPHY = "地理"
    CIVICS = "公民"
    JAPANESE = "国語"
    SCIENCE = "理科"
    MATHEMATICS = "数学"
    ENGLISH = "英語"
    MUSIC = "音楽"
    ART = "美術"
    PE = "体育"
    ETHICS = "倫理"
    POLITICS_ECONOMY = "政治経済"


class Grade(Enum):
    """学年分類"""
    ELEMENTARY_LOW = "小学校低学年"  # 1-3年
    ELEMENTARY_HIGH = "小学校高学年"  # 4-6年
    JUNIOR_HIGH = "中学校"
    HIGH_SCHOOL = "高等学校"


@dataclass
class TextbookPerson:
    """教科書掲載人物データ"""
    id: str
    name: str
    name_en: Optional[str]
    subjects: List[Subject]  # 掲載教科
    grades: List[Grade]  # 掲載学年
    importance_level: int  # 重要度 (1-5: 5が最重要)
    era: Optional[str]  # 時代
    category: str  # 分野（政治家、科学者など）
    protection_reason: str


class TextbookPersonProtector:
    """
    教科書掲載人物保護システム

    文部科学省学習指導要領に基づく
    教育的重要人物の完全保護
    """

    def __init__(self):
        """初期化"""
        self.textbook_persons = self._load_textbook_database()
        self.stats = {
            'total_checked': 0,
            'textbook_found': 0,
            'protected_count': 0,
            'by_subject': {subject.value: 0 for subject in Subject},
            'by_grade': {grade.value: 0 for grade in Grade}
        }

        logger.info(f"✅ 教科書データベース初期化: {len(self.textbook_persons)}名登録")

    def _load_textbook_database(self) -> Dict[str, TextbookPerson]:
        """
        教科書掲載人物データベース
        学習指導要領必修人物＋頻出人物
        """
        database = {}

        # ===== 日本史必修人物 =====
        japanese_history_persons = [
            # 古代
            ('卑弥呼', 'Himiko', '弥生時代', 5, '女王'),
            ('聖徳太子', 'Prince Shotoku', '飛鳥時代', 5, '皇族・政治家'),
            ('中大兄皇子', 'Prince Naka no Oe', '飛鳥時代', 4, '皇族'),
            ('中臣鎌足', 'Nakatomi no Kamatari', '飛鳥時代', 4, '政治家'),
            ('聖武天皇', 'Emperor Shomu', '奈良時代', 4, '天皇'),
            ('鑑真', 'Ganjin', '奈良時代', 4, '僧侶'),
            ('行基', 'Gyoki', '奈良時代', 3, '僧侶'),

            # 平安時代
            ('桓武天皇', 'Emperor Kanmu', '平安時代', 4, '天皇'),
            ('藤原道長', 'Fujiwara no Michinaga', '平安時代', 5, '貴族・政治家'),
            ('藤原頼通', 'Fujiwara no Yorimichi', '平安時代', 3, '貴族'),
            ('紫式部', 'Murasaki Shikibu', '平安時代', 5, '作家'),
            ('清少納言', 'Sei Shonagon', '平安時代', 4, '作家'),
            ('菅原道真', 'Sugawara no Michizane', '平安時代', 4, '学者・政治家'),
            ('空海', 'Kukai', '平安時代', 4, '僧侶'),
            ('最澄', 'Saicho', '平安時代', 4, '僧侶'),

            # 鎌倉時代
            ('平清盛', 'Taira no Kiyomori', '平安末期', 4, '武士'),
            ('源頼朝', 'Minamoto no Yoritomo', '鎌倉時代', 5, '将軍'),
            ('源義経', 'Minamoto no Yoshitsune', '鎌倉時代', 4, '武将'),
            ('北条政子', 'Hojo Masako', '鎌倉時代', 4, '尼将軍'),
            ('北条時宗', 'Hojo Tokimune', '鎌倉時代', 4, '執権'),
            ('親鸞', 'Shinran', '鎌倉時代', 4, '僧侶'),
            ('日蓮', 'Nichiren', '鎌倉時代', 4, '僧侶'),
            ('法然', 'Honen', '鎌倉時代', 4, '僧侶'),
            ('道元', 'Dogen', '鎌倉時代', 3, '僧侶'),
            ('栄西', 'Eisai', '鎌倉時代', 3, '僧侶'),

            # 室町時代
            ('足利尊氏', 'Ashikaga Takauji', '室町時代', 4, '将軍'),
            ('足利義満', 'Ashikaga Yoshimitsu', '室町時代', 5, '将軍'),
            ('足利義政', 'Ashikaga Yoshimasa', '室町時代', 3, '将軍'),
            ('雪舟', 'Sesshu', '室町時代', 4, '画家'),

            # 戦国・安土桃山時代
            ('織田信長', 'Oda Nobunaga', '戦国時代', 5, '戦国大名'),
            ('豊臣秀吉', 'Toyotomi Hideyoshi', '安土桃山時代', 5, '天下人'),
            ('徳川家康', 'Tokugawa Ieyasu', '江戸時代', 5, '将軍'),
            ('武田信玄', 'Takeda Shingen', '戦国時代', 3, '戦国大名'),
            ('上杉謙信', 'Uesugi Kenshin', '戦国時代', 3, '戦国大名'),
            ('フランシスコ・ザビエル', 'Francis Xavier', '戦国時代', 4, '宣教師'),

            # 江戸時代
            ('徳川家光', 'Tokugawa Iemitsu', '江戸時代', 4, '将軍'),
            ('徳川綱吉', 'Tokugawa Tsunayoshi', '江戸時代', 3, '将軍'),
            ('徳川吉宗', 'Tokugawa Yoshimune', '江戸時代', 4, '将軍'),
            ('徳川慶喜', 'Tokugawa Yoshinobu', '江戸末期', 4, '将軍'),
            ('田沼意次', 'Tanuma Okitsugu', '江戸時代', 3, '老中'),
            ('松平定信', 'Matsudaira Sadanobu', '江戸時代', 3, '老中'),
            ('水野忠邦', 'Mizuno Tadakuni', '江戸時代', 3, '老中'),
            ('大塩平八郎', 'Oshio Heihachiro', '江戸時代', 3, '陽明学者'),
            ('伊能忠敬', 'Ino Tadataka', '江戸時代', 4, '測量家'),
            ('杉田玄白', 'Sugita Genpaku', '江戸時代', 4, '蘭学者'),
            ('前野良沢', 'Maeno Ryotaku', '江戸時代', 3, '蘭学者'),
            ('本居宣長', 'Motoori Norinaga', '江戸時代', 4, '国学者'),
            ('平賀源内', 'Hiraga Gennai', '江戸時代', 3, '発明家'),
            ('歌川広重', 'Utagawa Hiroshige', '江戸時代', 4, '浮世絵師'),
            ('葛飾北斎', 'Katsushika Hokusai', '江戸時代', 4, '浮世絵師'),
            ('近松門左衛門', 'Chikamatsu Monzaemon', '江戸時代', 3, '劇作家'),
            ('松尾芭蕉', 'Matsuo Basho', '江戸時代', 4, '俳人'),
            ('ペリー', 'Matthew Perry', '江戸末期', 5, '提督'),

            # 幕末・明治維新
            ('坂本龍馬', 'Sakamoto Ryoma', '幕末', 5, '志士'),
            ('西郷隆盛', 'Saigo Takamori', '幕末・明治', 5, '政治家'),
            ('大久保利通', 'Okubo Toshimichi', '明治', 5, '政治家'),
            ('木戸孝允', 'Kido Takayoshi', '幕末・明治', 4, '政治家'),
            ('勝海舟', 'Katsu Kaishu', '幕末', 4, '幕臣'),
            ('吉田松陰', 'Yoshida Shoin', '幕末', 4, '思想家'),
            ('高杉晋作', 'Takasugi Shinsaku', '幕末', 3, '志士'),

            # 明治時代
            ('明治天皇', 'Emperor Meiji', '明治', 5, '天皇'),
            ('伊藤博文', 'Ito Hirobumi', '明治', 5, '政治家'),
            ('大隈重信', 'Okuma Shigenobu', '明治', 4, '政治家'),
            ('板垣退助', 'Itagaki Taisuke', '明治', 4, '政治家'),
            ('福沢諭吉', 'Fukuzawa Yukichi', '明治', 5, '思想家・教育者'),
            ('渋沢栄一', 'Shibusawa Eiichi', '明治・大正', 4, '実業家'),
            ('津田梅子', 'Tsuda Umeko', '明治', 4, '教育者'),
            ('北里柴三郎', 'Kitasato Shibasaburo', '明治', 4, '医学者'),
            ('野口英世', 'Noguchi Hideyo', '明治・大正', 4, '医学者'),
            ('夏目漱石', 'Natsume Soseki', '明治・大正', 5, '作家'),
            ('森鴎外', 'Mori Ogai', '明治・大正', 4, '作家・医師'),
            ('樋口一葉', 'Higuchi Ichiyo', '明治', 4, '作家'),
            ('正岡子規', 'Masaoka Shiki', '明治', 4, '俳人'),
            ('与謝野晶子', 'Yosano Akiko', '明治・大正', 3, '歌人'),

            # 大正・昭和時代
            ('原敬', 'Hara Takashi', '大正', 3, '政治家'),
            ('犬養毅', 'Inukai Tsuyoshi', '昭和初期', 3, '政治家'),
            ('吉野作造', 'Yoshino Sakuzo', '大正', 3, '政治学者'),
            ('平塚らいてう', 'Hiratsuka Raicho', '大正・昭和', 3, '女性運動家'),
            ('市川房枝', 'Ichikawa Fusae', '昭和', 3, '女性運動家'),

            # 戦後
            ('吉田茂', 'Yoshida Shigeru', '昭和', 4, '政治家'),
            ('田中角栄', 'Tanaka Kakuei', '昭和', 3, '政治家'),
            ('佐藤栄作', 'Sato Eisaku', '昭和', 3, '政治家'),
        ]

        # 日本史人物を登録
        for i, (name, name_en, era, importance, category) in enumerate(japanese_history_persons):
            grades = self._determine_grades(importance)
            person = TextbookPerson(
                id=f'TBJ{i:04d}',
                name=name,
                name_en=name_en,
                subjects=[Subject.JAPANESE_HISTORY],
                grades=grades,
                importance_level=importance,
                era=era,
                category=category,
                protection_reason=f'日本史教科書掲載（重要度{importance}）'
            )
            database[name] = person

        # ===== 世界史必修人物 =====
        world_history_persons = [
            # 古代文明
            ('ハンムラビ', 'Hammurabi', '古代メソポタミア', 4, '王'),
            ('ツタンカーメン', 'Tutankhamun', '古代エジプト', 3, 'ファラオ'),
            ('クレオパトラ', 'Cleopatra', '古代エジプト', 4, '女王'),

            # 古代ギリシア・ローマ
            ('ソクラテス', 'Socrates', '古代ギリシア', 5, '哲学者'),
            ('プラトン', 'Plato', '古代ギリシア', 5, '哲学者'),
            ('アリストテレス', 'Aristotle', '古代ギリシア', 5, '哲学者'),
            ('アレクサンドロス大王', 'Alexander the Great', '古代マケドニア', 5, '王'),
            ('カエサル', 'Julius Caesar', '古代ローマ', 5, '政治家・軍人'),
            ('アウグストゥス', 'Augustus', '古代ローマ', 4, '皇帝'),
            ('ネロ', 'Nero', '古代ローマ', 3, '皇帝'),

            # 中国史
            ('孔子', 'Confucius', '春秋時代', 5, '思想家'),
            ('始皇帝', 'Qin Shi Huang', '秦', 5, '皇帝'),
            ('劉邦', 'Liu Bang', '漢', 4, '皇帝'),
            ('曹操', 'Cao Cao', '三国時代', 3, '武将'),
            ('諸葛亮', 'Zhuge Liang', '三国時代', 3, '軍師'),
            ('李白', 'Li Bai', '唐', 4, '詩人'),
            ('杜甫', 'Du Fu', '唐', 4, '詩人'),
            ('チンギス・ハン', 'Genghis Khan', 'モンゴル帝国', 5, '皇帝'),
            ('フビライ・ハン', 'Kublai Khan', 'モンゴル帝国', 4, '皇帝'),
            ('鄭和', 'Zheng He', '明', 3, '航海者'),
            ('孫文', 'Sun Yat-sen', '中華民国', 4, '革命家'),
            ('毛沢東', 'Mao Zedong', '中華人民共和国', 4, '政治家'),
            ('鄧小平', 'Deng Xiaoping', '中華人民共和国', 3, '政治家'),

            # イスラム世界
            ('ムハンマド', 'Muhammad', 'イスラム', 5, '預言者'),

            # 中世ヨーロッパ
            ('カール大帝', 'Charlemagne', 'フランク王国', 4, '皇帝'),
            ('ジャンヌ・ダルク', 'Joan of Arc', '中世フランス', 4, '軍人'),

            # 大航海時代
            ('コロンブス', 'Christopher Columbus', '大航海時代', 5, '探検家'),
            ('マゼラン', 'Ferdinand Magellan', '大航海時代', 4, '探検家'),
            ('バスコ・ダ・ガマ', 'Vasco da Gama', '大航海時代', 4, '探検家'),

            # ルネサンス
            ('レオナルド・ダ・ヴィンチ', 'Leonardo da Vinci', 'ルネサンス', 5, '芸術家・科学者'),
            ('ミケランジェロ', 'Michelangelo', 'ルネサンス', 5, '芸術家'),
            ('ラファエロ', 'Raphael', 'ルネサンス', 4, '画家'),
            ('ダンテ', 'Dante Alighieri', 'ルネサンス', 4, '詩人'),

            # 宗教改革
            ('ルター', 'Martin Luther', '宗教改革', 5, '宗教改革者'),
            ('カルヴァン', 'John Calvin', '宗教改革', 4, '宗教改革者'),

            # 絶対王政
            ('エリザベス1世', 'Elizabeth I', 'イギリス', 4, '女王'),
            ('ルイ14世', 'Louis XIV', 'フランス', 5, '国王'),
            ('ピョートル大帝', 'Peter the Great', 'ロシア', 4, '皇帝'),
            ('マリア・テレジア', 'Maria Theresa', 'オーストリア', 3, '女帝'),

            # 市民革命
            ('クロムウェル', 'Oliver Cromwell', 'イギリス', 4, '政治家'),
            ('ワシントン', 'George Washington', 'アメリカ', 5, '大統領'),
            ('ジェファーソン', 'Thomas Jefferson', 'アメリカ', 4, '大統領'),
            ('フランクリン', 'Benjamin Franklin', 'アメリカ', 4, '政治家・科学者'),
            ('ルソー', 'Jean-Jacques Rousseau', 'フランス', 4, '思想家'),
            ('モンテスキュー', 'Montesquieu', 'フランス', 4, '思想家'),
            ('ヴォルテール', 'Voltaire', 'フランス', 4, '思想家'),
            ('ロベスピエール', 'Robespierre', 'フランス', 4, '革命家'),
            ('ナポレオン', 'Napoleon Bonaparte', 'フランス', 5, '皇帝'),

            # 産業革命
            ('ワット', 'James Watt', 'イギリス', 4, '発明家'),
            ('スティーブンソン', 'George Stephenson', 'イギリス', 3, '技術者'),

            # 19世紀
            ('リンカーン', 'Abraham Lincoln', 'アメリカ', 5, '大統領'),
            ('ビスマルク', 'Otto von Bismarck', 'ドイツ', 4, '政治家'),
            ('ガリバルディ', 'Giuseppe Garibaldi', 'イタリア', 3, '革命家'),
            ('ヴィクトリア女王', 'Queen Victoria', 'イギリス', 4, '女王'),

            # 20世紀
            ('レーニン', 'Vladimir Lenin', 'ソ連', 4, '革命家'),
            ('スターリン', 'Joseph Stalin', 'ソ連', 4, '政治家'),
            ('ヒトラー', 'Adolf Hitler', 'ドイツ', 5, '独裁者'),
            ('ムッソリーニ', 'Benito Mussolini', 'イタリア', 3, '独裁者'),
            ('チャーチル', 'Winston Churchill', 'イギリス', 4, '政治家'),
            ('ルーズベルト', 'Franklin D. Roosevelt', 'アメリカ', 4, '大統領'),
            ('ガンディー', 'Mahatma Gandhi', 'インド', 5, '独立運動指導者'),
            ('ネルー', 'Jawaharlal Nehru', 'インド', 3, '政治家'),
            ('ホー・チ・ミン', 'Ho Chi Minh', 'ベトナム', 3, '革命家'),
            ('マンデラ', 'Nelson Mandela', '南アフリカ', 4, '政治家'),
            ('ゴルバチョフ', 'Mikhail Gorbachev', 'ソ連', 4, '政治家'),
        ]

        # 世界史人物を登録
        for i, (name, name_en, era, importance, category) in enumerate(world_history_persons):
            grades = self._determine_grades(importance)
            person = TextbookPerson(
                id=f'TBW{i:04d}',
                name=name,
                name_en=name_en,
                subjects=[Subject.WORLD_HISTORY],
                grades=grades,
                importance_level=importance,
                era=era,
                category=category,
                protection_reason=f'世界史教科書掲載（重要度{importance}）'
            )
            database[name] = person

        # ===== 理科（科学者） =====
        scientists = [
            ('ガリレオ・ガリレイ', 'Galileo Galilei', [Subject.SCIENCE], 5, '天文学者'),
            ('ニュートン', 'Isaac Newton', [Subject.SCIENCE, Subject.MATHEMATICS], 5, '物理学者'),
            ('アインシュタイン', 'Albert Einstein', [Subject.SCIENCE], 5, '物理学者'),
            ('ダーウィン', 'Charles Darwin', [Subject.SCIENCE], 5, '生物学者'),
            ('メンデル', 'Gregor Mendel', [Subject.SCIENCE], 4, '遺伝学者'),
            ('パスツール', 'Louis Pasteur', [Subject.SCIENCE], 4, '細菌学者'),
            ('キュリー夫人', 'Marie Curie', [Subject.SCIENCE], 5, '物理学者'),
            ('ノーベル', 'Alfred Nobel', [Subject.SCIENCE], 4, '化学者'),
            ('エジソン', 'Thomas Edison', [Subject.SCIENCE], 5, '発明家'),
            ('フレミング', 'Alexander Fleming', [Subject.SCIENCE], 4, '細菌学者'),
            ('湯川秀樹', 'Yukawa Hideki', [Subject.SCIENCE], 4, '物理学者'),
            ('朝永振一郎', 'Tomonaga Shinichiro', [Subject.SCIENCE], 3, '物理学者'),
            ('江崎玲於奈', 'Esaki Reona', [Subject.SCIENCE], 3, '物理学者'),
            ('利根川進', 'Tonegawa Susumu', [Subject.SCIENCE], 3, '生物学者'),
            ('山中伸弥', 'Yamanaka Shinya', [Subject.SCIENCE], 4, '医学者'),
            ('大村智', 'Omura Satoshi', [Subject.SCIENCE], 3, '化学者'),
        ]

        # 理科人物を登録
        for i, (name, name_en, subjects, importance, category) in enumerate(scientists):
            grades = self._determine_grades(importance)
            person = TextbookPerson(
                id=f'TBS{i:04d}',
                name=name,
                name_en=name_en,
                subjects=subjects,
                grades=grades,
                importance_level=importance,
                era='近現代',
                category=category,
                protection_reason=f'理科教科書掲載（重要度{importance}）'
            )
            database[name] = person

        # ===== 国語（文学者） =====
        writers = [
            # 古典
            ('紀貫之', 'Ki no Tsurayuki', 4, '歌人'),
            ('在原業平', 'Ariwara no Narihira', 3, '歌人'),
            ('小野小町', 'Ono no Komachi', 3, '歌人'),
            ('西行', 'Saigyo', 3, '歌人・僧侶'),
            ('鴨長明', 'Kamo no Chomei', 4, '随筆家'),
            ('吉田兼好', 'Yoshida Kenko', 4, '随筆家'),
            ('世阿弥', 'Zeami', 3, '能楽師'),

            # 近世
            ('井原西鶴', 'Ihara Saikaku', 4, '作家'),
            ('松尾芭蕉', 'Matsuo Basho', 5, '俳人'),
            ('与謝蕪村', 'Yosa Buson', 3, '俳人・画家'),
            ('小林一茶', 'Kobayashi Issa', 3, '俳人'),

            # 近現代
            ('夏目漱石', 'Natsume Soseki', 5, '作家'),
            ('森鴎外', 'Mori Ogai', 5, '作家'),
            ('芥川龍之介', 'Akutagawa Ryunosuke', 5, '作家'),
            ('太宰治', 'Dazai Osamu', 4, '作家'),
            ('川端康成', 'Kawabata Yasunari', 5, '作家'),
            ('三島由紀夫', 'Mishima Yukio', 4, '作家'),
            ('谷崎潤一郎', 'Tanizaki Junichiro', 4, '作家'),
            ('志賀直哉', 'Shiga Naoya', 4, '作家'),
            ('島崎藤村', 'Shimazaki Toson', 4, '作家'),
            ('石川啄木', 'Ishikawa Takuboku', 4, '歌人'),
            ('宮沢賢治', 'Miyazawa Kenji', 5, '詩人・作家'),
            ('中原中也', 'Nakahara Chuya', 3, '詩人'),
            ('高村光太郎', 'Takamura Kotaro', 3, '詩人'),
            ('萩原朔太郎', 'Hagiwara Sakutaro', 3, '詩人'),
            ('大江健三郎', 'Oe Kenzaburo', 4, '作家'),
            ('村上春樹', 'Murakami Haruki', 3, '作家'),
        ]

        # 国語人物を登録
        for i, (name, name_en, importance, category) in enumerate(writers):
            grades = self._determine_grades(importance)
            person = TextbookPerson(
                id=f'TBL{i:04d}',
                name=name,
                name_en=name_en,
                subjects=[Subject.JAPANESE],
                grades=grades,
                importance_level=importance,
                era='文学史',
                category=category,
                protection_reason=f'国語教科書掲載（重要度{importance}）'
            )
            database[name] = person

        # ===== 音楽 =====
        musicians = [
            ('バッハ', 'Johann Sebastian Bach', 5, '作曲家'),
            ('モーツァルト', 'Wolfgang Amadeus Mozart', 5, '作曲家'),
            ('ベートーヴェン', 'Ludwig van Beethoven', 5, '作曲家'),
            ('ショパン', 'Frédéric Chopin', 4, '作曲家'),
            ('シューベルト', 'Franz Schubert', 4, '作曲家'),
            ('ブラームス', 'Johannes Brahms', 3, '作曲家'),
            ('チャイコフスキー', 'Pyotr Tchaikovsky', 4, '作曲家'),
            ('ドビュッシー', 'Claude Debussy', 3, '作曲家'),
            ('滝廉太郎', 'Taki Rentaro', 4, '作曲家'),
            ('山田耕筰', 'Yamada Kosaku', 3, '作曲家'),
            ('中田喜直', 'Nakada Yoshinao', 3, '作曲家'),
        ]

        # 音楽人物を登録
        for i, (name, name_en, importance, category) in enumerate(musicians):
            grades = self._determine_grades(importance)
            person = TextbookPerson(
                id=f'TBM{i:04d}',
                name=name,
                name_en=name_en,
                subjects=[Subject.MUSIC],
                grades=grades,
                importance_level=importance,
                era='音楽史',
                category=category,
                protection_reason=f'音楽教科書掲載（重要度{importance}）'
            )
            database[name] = person

        # ===== 美術 =====
        artists = [
            ('レオナルド・ダ・ヴィンチ', 'Leonardo da Vinci', 5, '画家'),
            ('ミケランジェロ', 'Michelangelo', 5, '彫刻家・画家'),
            ('ラファエロ', 'Raphael', 4, '画家'),
            ('レンブラント', 'Rembrandt', 4, '画家'),
            ('フェルメール', 'Johannes Vermeer', 4, '画家'),
            ('ゴッホ', 'Vincent van Gogh', 5, '画家'),
            ('モネ', 'Claude Monet', 4, '画家'),
            ('ルノワール', 'Pierre-Auguste Renoir', 4, '画家'),
            ('ピカソ', 'Pablo Picasso', 5, '画家'),
            ('ダリ', 'Salvador Dalí', 3, '画家'),
            ('葛飾北斎', 'Katsushika Hokusai', 5, '浮世絵師'),
            ('歌川広重', 'Utagawa Hiroshige', 4, '浮世絵師'),
            ('雪舟', 'Sesshu', 4, '画家'),
            ('狩野永徳', 'Kano Eitoku', 3, '画家'),
            ('尾形光琳', 'Ogata Korin', 3, '画家'),
            ('横山大観', 'Yokoyama Taikan', 3, '日本画家'),
        ]

        # 美術人物を登録
        for i, (name, name_en, importance, category) in enumerate(artists):
            grades = self._determine_grades(importance)
            person = TextbookPerson(
                id=f'TBA{i:04d}',
                name=name,
                name_en=name_en,
                subjects=[Subject.ART],
                grades=grades,
                importance_level=importance,
                era='美術史',
                category=category,
                protection_reason=f'美術教科書掲載（重要度{importance}）'
            )
            database[name] = person

        # ===== 体育 =====
        athletes = [
            ('嘉納治五郎', 'Kano Jigoro', 4, '柔道創始者'),
            ('金栗四三', 'Kanakuri Shizo', 3, 'マラソン選手'),
            ('人見絹枝', 'Hitomi Kinue', 3, '陸上選手'),
            ('クーベルタン', 'Pierre de Coubertin', 4, 'オリンピック創始者'),
        ]

        # 体育人物を登録
        for i, (name, name_en, importance, category) in enumerate(athletes):
            grades = self._determine_grades(importance)
            person = TextbookPerson(
                id=f'TBP{i:04d}',
                name=name,
                name_en=name_en,
                subjects=[Subject.PE],
                grades=grades,
                importance_level=importance,
                era='スポーツ史',
                category=category,
                protection_reason=f'体育教科書掲載（重要度{importance}）'
            )
            database[name] = person

        # ===== 公民・倫理 =====
        thinkers = [
            # 西洋思想家
            ('ソクラテス', 'Socrates', 5, '哲学者'),
            ('プラトン', 'Plato', 5, '哲学者'),
            ('アリストテレス', 'Aristotle', 5, '哲学者'),
            ('デカルト', 'René Descartes', 4, '哲学者'),
            ('カント', 'Immanuel Kant', 4, '哲学者'),
            ('ヘーゲル', 'Georg Wilhelm Friedrich Hegel', 3, '哲学者'),
            ('マルクス', 'Karl Marx', 4, '思想家'),
            ('ニーチェ', 'Friedrich Nietzsche', 3, '哲学者'),
            ('フロイト', 'Sigmund Freud', 4, '心理学者'),
            ('ユング', 'Carl Jung', 3, '心理学者'),

            # 東洋思想家
            ('孔子', 'Confucius', 5, '思想家'),
            ('孟子', 'Mencius', 4, '思想家'),
            ('老子', 'Laozi', 4, '思想家'),
            ('荘子', 'Zhuangzi', 3, '思想家'),
            ('ブッダ', 'Buddha', 5, '宗教家'),

            # 経済学者
            ('アダム・スミス', 'Adam Smith', 5, '経済学者'),
            ('リカード', 'David Ricardo', 3, '経済学者'),
            ('ケインズ', 'John Maynard Keynes', 4, '経済学者'),
            ('シュンペーター', 'Joseph Schumpeter', 3, '経済学者'),
        ]

        # 公民・倫理人物を登録
        for i, (name, name_en, importance, category) in enumerate(thinkers):
            grades = [Grade.HIGH_SCHOOL]  # 主に高校で学習
            person = TextbookPerson(
                id=f'TBE{i:04d}',
                name=name,
                name_en=name_en,
                subjects=[Subject.CIVICS, Subject.ETHICS],
                grades=grades,
                importance_level=importance,
                era='思想史',
                category=category,
                protection_reason=f'公民・倫理教科書掲載（重要度{importance}）'
            )
            # 重複チェック（日本史・世界史と被る人物）
            if name not in database:
                database[name] = person

        return database

    def _determine_grades(self, importance_level: int) -> List[Grade]:
        """重要度から学年を判定"""
        if importance_level >= 5:
            # 最重要人物は全学年
            return [Grade.ELEMENTARY_LOW, Grade.ELEMENTARY_HIGH,
                   Grade.JUNIOR_HIGH, Grade.HIGH_SCHOOL]
        elif importance_level >= 4:
            # 重要人物は小学校高学年から
            return [Grade.ELEMENTARY_HIGH, Grade.JUNIOR_HIGH, Grade.HIGH_SCHOOL]
        elif importance_level >= 3:
            # 中程度は中学から
            return [Grade.JUNIOR_HIGH, Grade.HIGH_SCHOOL]
        else:
            # その他は高校のみ
            return [Grade.HIGH_SCHOOL]

    def is_textbook_person(self, name: str) -> bool:
        """教科書掲載人物かどうか判定"""
        self.stats['total_checked'] += 1
        if name in self.textbook_persons:
            self.stats['textbook_found'] += 1
            return True
        return False

    def get_protection_info(self, name: str) -> Optional[TextbookPerson]:
        """保護情報取得"""
        return self.textbook_persons.get(name)

    def should_protect(self, name: str) -> Tuple[bool, str]:
        """
        保護判定

        Returns:
            (保護すべきか, 理由)
        """
        if name in self.textbook_persons:
            person = self.textbook_persons[name]
            self.stats['protected_count'] += 1

            # 教科別カウント
            for subject in person.subjects:
                self.stats['by_subject'][subject.value] += 1

            # 学年別カウント
            for grade in person.grades:
                self.stats['by_grade'][grade.value] += 1

            return True, person.protection_reason

        return False, "教科書未掲載"

    def batch_protect(self, persons: List[Dict]) -> List[Dict]:
        """バッチ保護処理"""
        protected_persons = []

        for person in persons:
            name = person.get('name', '')

            # 教科書保護判定
            is_protected, reason = self.should_protect(name)

            # 教科書情報取得
            textbook_info = self.get_protection_info(name)

            # 結果を追加
            person_with_protection = person.copy()
            person_with_protection.update({
                'is_textbook_person': textbook_info is not None,
                'is_protected': is_protected,
                'protection_reason': reason,
                'textbook_importance': textbook_info.importance_level if textbook_info else 0,
                'textbook_subjects': [s.value for s in textbook_info.subjects] if textbook_info else [],
                'textbook_grades': [g.value for g in textbook_info.grades] if textbook_info else []
            })

            protected_persons.append(person_with_protection)

        return protected_persons

    def export_textbook_database(self, output_path: str):
        """教科書データベースをエクスポート"""
        data = []

        for name, person in self.textbook_persons.items():
            data.append({
                'id': person.id,
                'name': person.name,
                'name_en': person.name_en,
                'subjects': [s.value for s in person.subjects],
                'grades': [g.value for g in person.grades],
                'importance_level': person.importance_level,
                'era': person.era,
                'category': person.category,
                'protection_reason': person.protection_reason
            })

        # 重要度でソート
        data.sort(key=lambda x: (-x['importance_level'], x['name']))

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 教科書データベースエクスポート完了: {output_path}")

    def print_statistics(self):
        """統計情報表示"""
        print("\n" + "="*60)
        print("教科書掲載人物保護システム - 統計情報")
        print("="*60)
        print(f"データベース登録数: {len(self.textbook_persons)}名")
        print(f"チェック総数: {self.stats['total_checked']}名")
        print(f"教科書掲載検出: {self.stats['textbook_found']}名")
        print(f"保護対象数: {self.stats['protected_count']}名")

        print("\n【教科別保護数】")
        for subject, count in self.stats['by_subject'].items():
            if count > 0:
                print(f"  {subject}: {count}名")

        print("\n【学年別保護数】")
        for grade, count in self.stats['by_grade'].items():
            if count > 0:
                print(f"  {grade}: {count}名")

        print("\n【重要度別人数】")
        importance_counts = {}
        for person in self.textbook_persons.values():
            level = person.importance_level
            importance_counts[level] = importance_counts.get(level, 0) + 1

        for level in sorted(importance_counts.keys(), reverse=True):
            stars = '★' * level + '☆' * (5 - level)
            print(f"  {stars} (重要度{level}): {importance_counts[level]}名")

        print("="*60)


def main():
    """メイン実行"""
    protector = TextbookPersonProtector()

    # テストデータ
    test_persons = [
        {'name': '織田信長', 'integrated_score': 5.0},
        {'name': '豊臣秀吉', 'integrated_score': 5.0},
        {'name': '徳川家康', 'integrated_score': 5.0},
        {'name': '聖徳太子', 'integrated_score': 5.0},
        {'name': 'ナポレオン', 'integrated_score': 5.0},
        {'name': 'ニュートン', 'integrated_score': 5.0},
        {'name': '夏目漱石', 'integrated_score': 5.0},
        {'name': 'HIKAKIN', 'integrated_score': 7.5},  # 教科書未掲載
        {'name': '架空太郎', 'integrated_score': 1.0},  # 教科書未掲載
    ]

    # バッチ保護処理
    protected_persons = protector.batch_protect(test_persons)

    # 結果表示
    print("\n保護判定結果:")
    print("-" * 60)
    for person in protected_persons:
        print(f"\n名前: {person['name']}")
        print(f"  教科書掲載: {'はい' if person['is_textbook_person'] else 'いいえ'}")
        if person['is_textbook_person']:
            print(f"  重要度: {'★' * person['textbook_importance']}{'☆' * (5 - person['textbook_importance'])}")
            print(f"  掲載教科: {', '.join(person['textbook_subjects'])}")
            print(f"  学習学年: {', '.join(person['textbook_grades'])}")
        print(f"  保護対象: {'はい' if person['is_protected'] else 'いいえ'}")
        print(f"  理由: {person['protection_reason']}")

    # 統計表示
    protector.print_statistics()

    # データベースエクスポート
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"textbook_persons_database_{timestamp}.json"
    protector.export_textbook_database(output_path)

    print(f"\n✅ 完了！データベースは {output_path} に保存されました")


if __name__ == "__main__":
    main()
