#!/usr/bin/env python3
"""
偉人伝書籍シリーズ分析システム
各出版社の偉人伝シリーズから人物リストを抽出し、データベース未登録者を特定
"""

from typing import List, Dict, Set, Tuple
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BiographySeries:
    """偉人伝シリーズのデータクラス"""
    publisher: str
    series_name: str
    target_age: str
    volume_count: int
    persons: List[Tuple[str, str, str]]  # (name, name_jp, category)

class BiographyBookDatabase:
    """主要出版社の偉人伝シリーズデータベース"""
    
    def __init__(self):
        self.series_list = []
        self._initialize_series()
    
    def _initialize_series(self):
        """各出版社のシリーズを初期化"""
        
        # 1. 角川まんが学習シリーズ まんが人物伝（27巻）
        kadokawa_series = BiographySeries(
            publisher="KADOKAWA",
            series_name="角川まんが学習シリーズ まんが人物伝",
            target_age="小学生",
            volume_count=27,
            persons=[
                # 日本の歴史人物
                ("Oda Nobunaga", "織田信長", "戦国武将"),
                ("Toyotomi Hideyoshi", "豊臣秀吉", "戦国武将"),
                ("Tokugawa Ieyasu", "徳川家康", "戦国武将"),
                ("Sanada Yukimura", "真田幸村", "戦国武将"),
                ("Takeda Shingen", "武田信玄", "戦国武将"),
                ("Uesugi Kenshin", "上杉謙信", "戦国武将"),
                ("Date Masamune", "伊達政宗", "戦国武将"),
                ("Saigo Takamori", "西郷隆盛", "幕末志士"),
                ("Sakamoto Ryoma", "坂本龍馬", "幕末志士"),
                ("Murasaki Shikibu", "紫式部", "文学者"),
                ("Tsuda Umeko", "津田梅子", "教育者"),
                ("Kitasato Shibasaburo", "北里柴三郎", "医学者"),
                ("Noguchi Hideyo", "野口英世", "医学者"),
                ("Shima Hideo", "島秀雄", "技術者"),
                # 世界の偉人
                ("Thomas Edison", "エジソン", "発明家"),
                ("Helen Keller", "ヘレン・ケラー", "社会活動家"),
                ("Florence Nightingale", "ナイチンゲール", "看護師"),
                ("Cleopatra", "クレオパトラ", "古代エジプト"),
                ("Elizabeth I", "エリザベス女王一世", "英国王室"),
                ("Marie Antoinette", "マリ・アントワネット", "フランス王室"),
                ("Ludwig van Beethoven", "ベートーベン", "作曲家"),
                ("Anne Frank", "アンネ・フランク", "ホロコースト"),
                ("Alfred Nobel", "ノーベル", "発明家"),
                ("Charles M. Schulz", "チャールズ・シュルツ", "漫画家"),
                ("Walt Disney", "ウォルト・ディズニー", "実業家"),
                ("Elizabeth Blackwell", "エリザベス・ブラックウェル", "医師"),
                ("Rachel Carson", "レイチェル・カーソン", "生物学者"),
                ("Elizabeth II", "エリザベス女王二世", "英国王室"),
                ("Alan Turing", "アラン・チューリング", "数学者"),
            ]
        )
        self.series_list.append(kadokawa_series)
        
        # 2. ポプラ社 コミック版世界の伝記（59巻以上）
        poplar_series = BiographySeries(
            publisher="ポプラ社",
            series_name="コミック版世界の伝記",
            target_age="小学生",
            volume_count=59,
            persons=[
                ("Henri Dunant", "アンリ・デュナン", "赤十字創設者"),
                ("Mother Teresa", "マザー・テレサ", "修道女"),
                ("Martin Luther King Jr.", "キング牧師", "公民権運動"),
                ("Mahatma Gandhi", "ガンディー", "独立運動"),
                ("Nelson Mandela", "ネルソン・マンデラ", "政治家"),
                ("Albert Einstein", "アインシュタイン", "物理学者"),
                ("Marie Curie", "キュリー夫人", "科学者"),
                ("Leonardo da Vinci", "レオナルド・ダ・ヴィンチ", "芸術家"),
                ("Vincent van Gogh", "ゴッホ", "画家"),
                ("Wolfgang Amadeus Mozart", "モーツァルト", "作曲家"),
                ("Johannes Gutenberg", "グーテンベルク", "発明家"),
                ("Christopher Columbus", "コロンブス", "探検家"),
                ("Marco Polo", "マルコ・ポーロ", "探検家"),
                ("Charles Darwin", "ダーウィン", "生物学者"),
                ("Isaac Newton", "ニュートン", "物理学者"),
                ("Galileo Galilei", "ガリレオ", "天文学者"),
                ("Louis Pasteur", "パスツール", "細菌学者"),
                ("Alexander Fleming", "フレミング", "医学者"),
                ("Wright Brothers", "ライト兄弟", "航空パイオニア"),
                ("Henry Ford", "ヘンリー・フォード", "実業家"),
            ]
        )
        self.series_list.append(poplar_series)
        
        # 3. 小学館版 学習まんが人物館（100巻以上）
        shogakukan_series = BiographySeries(
            publisher="小学館",
            series_name="小学館版 学習まんが人物館",
            target_age="小学生",
            volume_count=100,
            persons=[
                # 日本シリーズ
                ("Fukuzawa Yukichi", "福沢諭吉", "思想家"),
                ("Natsume Soseki", "夏目漱石", "文学者"),
                ("Higuchi Ichiyo", "樋口一葉", "文学者"),
                ("Miyazawa Kenji", "宮沢賢治", "文学者"),
                ("Tezuka Osamu", "手塚治虫", "漫画家"),
                ("Honda Soichiro", "本田宗一郎", "実業家"),
                ("Matsushita Konosuke", "松下幸之助", "実業家"),
                ("Inamori Kazuo", "稲盛和夫", "実業家"),
                ("Sugihara Chiune", "杉原千畝", "外交官"),
                ("Yukawa Hideki", "湯川秀樹", "物理学者"),
                ("Tomonaga Shinichiro", "朝永振一郎", "物理学者"),
                ("Esaki Reona", "江崎玲於奈", "物理学者"),
                # 世界シリーズ
                ("Johann Sebastian Bach", "バッハ", "作曲家"),
                ("Frederic Chopin", "ショパン", "作曲家"),
                ("Pablo Picasso", "ピカソ", "画家"),
                ("Salvador Dali", "ダリ", "画家"),
                ("Audrey Hepburn", "オードリー・ヘプバーン", "女優"),
                ("Charlie Chaplin", "チャップリン", "俳優"),
                ("Steven Jobs", "スティーブ・ジョブズ", "実業家"),
                ("Bill Gates", "ビル・ゲイツ", "実業家"),
                ("Mark Zuckerberg", "マーク・ザッカーバーグ", "実業家"),
                ("Elon Musk", "イーロン・マスク", "実業家"),
            ]
        )
        self.series_list.append(shogakukan_series)
        
        # 4. 学研 NEW日本の伝記シリーズ
        gakken_series = BiographySeries(
            publisher="学研",
            series_name="学研まんが NEW日本の伝記",
            target_age="小学生",
            volume_count=15,
            persons=[
                ("Shibusawa Eiichi", "渋沢栄一", "実業家"),
                ("Himiko", "卑弥呼", "古代日本"),
                ("Shotoku Taishi", "聖徳太子", "古代日本"),
                ("Minamoto no Yoritomo", "源頼朝", "武将"),
                ("Minamoto no Yoshitsune", "源義経", "武将"),
                ("Ashikaga Yoshimitsu", "足利義満", "室町将軍"),
                ("Oda Nobunaga", "織田信長", "戦国武将"),
                ("Tokugawa Ieyasu", "徳川家康", "戦国武将"),
                ("Katsu Kaishu", "勝海舟", "幕末"),
                ("Fukuzawa Yukichi", "福沢諭吉", "思想家"),
                ("Tsuda Umeko", "津田梅子", "教育者"),
                ("Noguchi Hideyo", "野口英世", "医学者"),
                ("Ninomiya Sontoku", "二宮尊徳", "農政家"),
                ("Ieyasu Tokugawa", "徳川家康", "戦国武将"),
                ("Murasaki Shikibu", "紫式部", "文学者"),
            ]
        )
        self.series_list.append(gakken_series)
        
        # 5. 集英社 学習まんが世界の伝記NEXT
        shueisha_series = BiographySeries(
            publisher="集英社",
            series_name="学習まんが 世界の伝記NEXT",
            target_age="小学生",
            volume_count=30,
            persons=[
                ("Coco Chanel", "ココ・シャネル", "デザイナー"),
                ("Steve Jobs", "スティーブ・ジョブズ", "実業家"),
                ("J.K. Rowling", "J.K.ローリング", "作家"),
                ("Michael Jackson", "マイケル・ジャクソン", "歌手"),
                ("The Beatles", "ビートルズ", "音楽グループ"),
                ("Albert Schweitzer", "シュバイツァー", "医師"),
                ("Howard Carter", "ハワード・カーター", "考古学者"),
                ("Jane Goodall", "ジェーン・グドール", "動物学者"),
                ("Stephen Hawking", "スティーブン・ホーキング", "物理学者"),
                ("Yuri Gagarin", "ガガーリン", "宇宙飛行士"),
                ("Neil Armstrong", "アームストロング", "宇宙飛行士"),
                ("Ernest Hemingway", "ヘミングウェイ", "作家"),
                ("Agatha Christie", "アガサ・クリスティー", "作家"),
                ("William Shakespeare", "シェイクスピア", "劇作家"),
                ("Confucius", "孔子", "思想家"),
                ("Buddha", "ブッダ", "宗教家"),
                ("Jesus Christ", "イエス・キリスト", "宗教家"),
                ("Muhammad", "ムハンマド", "宗教家"),
                ("Cleopatra", "クレオパトラ", "古代エジプト"),
                ("Alexander the Great", "アレクサンダー大王", "古代マケドニア"),
            ]
        )
        self.series_list.append(shueisha_series)
    
    def get_all_persons(self) -> Set[str]:
        """全シリーズの人物名（日本語）を取得"""
        all_persons = set()
        for series in self.series_list:
            for _, name_jp, _ in series.persons:
                all_persons.add(name_jp)
        return all_persons
    
    def get_persons_by_category(self) -> Dict[str, List[str]]:
        """カテゴリ別の人物リストを取得"""
        category_dict = {}
        for series in self.series_list:
            for _, name_jp, category in series.persons:
                if category not in category_dict:
                    category_dict[category] = []
                if name_jp not in category_dict[category]:
                    category_dict[category].append(name_jp)
        return category_dict
    
    def get_series_summary(self) -> Dict[str, Dict]:
        """各シリーズのサマリーを取得"""
        summary = {}
        for series in self.series_list:
            summary[series.series_name] = {
                "publisher": series.publisher,
                "volume_count": series.volume_count,
                "target_age": series.target_age,
                "person_count": len(series.persons),
                "categories": list(set(cat for _, _, cat in series.persons))
            }
        return summary
    
    def analyze_coverage(self) -> Dict:
        """偉人伝の網羅性を分析"""
        all_persons = self.get_all_persons()
        categories = self.get_persons_by_category()
        
        analysis = {
            "total_unique_persons": len(all_persons),
            "total_series": len(self.series_list),
            "total_volumes": sum(s.volume_count for s in self.series_list),
            "category_distribution": {
                cat: len(persons) for cat, persons in categories.items()
            },
            "top_categories": sorted(
                [(cat, len(persons)) for cat, persons in categories.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
        return analysis


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("偉人伝書籍シリーズ分析開始")
    logger.info("=" * 60)
    
    # データベース初期化
    bio_db = BiographyBookDatabase()
    
    # シリーズサマリー表示
    logger.info("\n📚 主要偉人伝シリーズ:")
    summary = bio_db.get_series_summary()
    for series_name, info in summary.items():
        logger.info(f"\n{series_name}:")
        logger.info(f"  出版社: {info['publisher']}")
        logger.info(f"  巻数: {info['volume_count']}巻")
        logger.info(f"  対象: {info['target_age']}")
        logger.info(f"  収録人物数: {info['person_count']}名")
    
    # 網羅性分析
    analysis = bio_db.analyze_coverage()
    logger.info("\n📊 網羅性分析:")
    logger.info(f"  総ユニーク人物数: {analysis['total_unique_persons']}名")
    logger.info(f"  総シリーズ数: {analysis['total_series']}シリーズ")
    logger.info(f"  総巻数: {analysis['total_volumes']}巻")
    
    logger.info("\n📈 カテゴリ別TOP10:")
    for category, count in analysis['top_categories']:
        logger.info(f"  {category}: {count}名")
    
    # 人物リスト出力
    all_persons = bio_db.get_all_persons()
    with open('biography_book_persons.txt', 'w', encoding='utf-8') as f:
        for person in sorted(all_persons):
            f.write(f"{person}\n")
    
    logger.info(f"\n✅ 人物リストを biography_book_persons.txt に出力しました")
    logger.info(f"   総人物数: {len(all_persons)}名")
    
    return bio_db


if __name__ == "__main__":
    main()