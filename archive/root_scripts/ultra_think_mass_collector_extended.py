#!/usr/bin/env python3
"""
Ultra Think Mass Collector Extended
1万人以上の有名人データを大規模収集
全フェーズ実装版
"""

import csv
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
import time


class UltraThinkMassCollectorExtended:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 前回の収集結果を使用
        self.existing_file = "ultra_think_extended_20250825_164753.csv"
        if not os.path.exists(self.existing_file):
            self.existing_file = "ultra_think_ultimate_1211_20250825_163049.csv"

        self.output_csv = f"ultra_think_massive_{self.timestamp}.csv"
        self.output_json = f"ultra_think_massive_{self.timestamp}.json"
        self.report_file = f"MASSIVE_COLLECTION_REPORT_{self.timestamp}.md"

        # 既存データを読み込み
        self.existing_data = self.load_existing_data()
        self.existing_names = {r.get('person_name', '') for r in self.existing_data}

        # 収集データ
        self.new_data = []

        # 統計
        self.stats = {
            'phase4_actor': 0,
            'phase5_sports': 0,
            'phase6_foreign': 0,
            'phase7_youtuber': 0,
            'phase8_historical': 0,
            'phase9_others': 0,
            'duplicates_skipped': 0,
            'total_collected': 0
        }

    def load_existing_data(self) -> List[Dict]:
        """既存データを読み込み"""
        try:
            with open(self.existing_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except:
            return []

    def create_person_record(self,
                           person_name: str,
                           person_name_ja: str,
                           person_name_display: str,
                           birth_year: int,
                           nationality: str = "",
                           occupation: str = "",
                           category: str = "",
                           is_fictional: bool = False,
                           is_animal: bool = False,
                           group_name: Optional[str] = None) -> Dict:
        """人物レコードを作成"""

        # グループメンバーの場合、表示名を調整
        if group_name:
            person_name_display = f"{person_name_ja}（{group_name}）"

        return {
            'batch_id': f'extended_{self.timestamp}',
            'birth_year': str(birth_year) if birth_year else '',
            'category': category,
            'cultural_significance': '',
            'description': '',
            'educational_value': '',
            'era': '現代' if birth_year >= 1900 else '近代',
            'followers': '',
            'global_recognition': '',
            'grade': '',
            'historical_impact': '',
            'is_animal': str(is_animal).upper(),
            'is_fictional': str(is_fictional).upper(),
            'main_category': category,
            'name': person_name_ja,
            'nationality': nationality,
            'occupation': occupation,
            'person_name': person_name,
            'person_name_display': person_name_display,
            'person_name_ja': person_name_ja,
            'phase': f'ExtendedCollection_{self.timestamp}',
            'platform': '',
            'subcategory': ''
        }

    def add_person(self, **kwargs) -> bool:
        """人物を追加（重複チェック付き）"""
        person_name = kwargs.get('person_name', '')

        # 重複チェック
        if person_name in self.existing_names:
            self.stats['duplicates_skipped'] += 1
            return False

        # レコード作成
        record = self.create_person_record(**kwargs)
        self.new_data.append(record)
        self.existing_names.add(person_name)
        self.stats['total_collected'] += 1

        # プログレス表示
        if self.stats['total_collected'] % 100 == 0:
            print(f"  収集済み: {self.stats['total_collected']}件")

        return True

    def phase4_actors_actresses(self):
        """Phase 4: 俳優・女優収集"""
        print("\n🎭 Phase 4: 俳優・女優収集開始...")

        actors = [
            # 日本の女優
            ("Yui Aragaki", "新垣結衣", "新垣結衣", 1988, "日本", "女優"),
            ("Satomi Ishihara", "石原さとみ", "石原さとみ", 1986, "日本", "女優"),
            ("Haruka Ayase", "綾瀬はるか", "綾瀬はるか", 1985, "日本", "女優"),
            ("Keiko Kitagawa", "北川景子", "北川景子", 1986, "日本", "女優"),
            ("Masami Nagasawa", "長澤まさみ", "長澤まさみ", 1987, "日本", "女優"),
            ("Suzu Hirose", "広瀬すず", "広瀬すず", 1998, "日本", "女優"),
            ("Alice Hirose", "広瀬アリス", "広瀬アリス", 1994, "日本", "女優"),
            ("Kanna Hashimoto", "橋本環奈", "橋本環奈", 1999, "日本", "女優"),
            ("Kasumi Arimura", "有村架純", "有村架純", 1993, "日本", "女優"),
            ("Mitsuki Takahata", "高畑充希", "高畑充希", 1991, "日本", "女優"),
            ("Nana Komatsu", "小松菜奈", "小松菜奈", 1996, "日本", "女優"),
            ("Minami Hamabe", "浜辺美波", "浜辺美波", 2000, "日本", "女優"),
            ("Mei Nagano", "永野芽郁", "永野芽郁", 1999, "日本", "女優"),
            ("Tao Tsuchiya", "土屋太鳳", "土屋太鳳", 1995, "日本", "女優"),
            ("Yuriko Yoshitaka", "吉高由里子", "吉高由里子", 1988, "日本", "女優"),
            ("Erika Toda", "戸田恵梨香", "戸田恵梨香", 1988, "日本", "女優"),
            ("Mirei Kiritani", "桐谷美玲", "桐谷美玲", 1989, "日本", "女優"),
            ("Emi Takei", "武井咲", "武井咲", 1993, "日本", "女優"),
            ("Nanao", "菜々緒", "菜々緒", 1988, "日本", "女優"),
            ("Yuko Takeuchi", "竹内結子", "竹内結子", 1980, "日本", "女優"),

            # 日本の男優（追加）
            ("Takeru Satoh", "佐藤健", "佐藤健", 1989, "日本", "俳優"),
            ("Ryunosuke Kamiki", "神木隆之介", "神木隆之介", 1993, "日本", "俳優"),
            ("Ryo Takeuchi", "竹内涼真", "竹内涼真", 1993, "日本", "俳優"),
            ("Ryu Yokohama", "横浜流星", "横浜流星", 1996, "日本", "俳優"),
            ("Tomoya Nakamura", "中村倫也", "中村倫也", 1986, "日本", "俳優"),
            ("Kento Nakajima", "中島健人", "中島健人", 1994, "日本", "俳優"),
            ("Taishi Nakagawa", "中川大志", "中川大志", 1998, "日本", "俳優"),
            ("Sota Fukushi", "福士蒼汰", "福士蒼汰", 1993, "日本", "俳優"),
            ("Mackenyu", "新田真剣佑", "真剣佑", 1996, "日本", "俳優"),
            ("Takumi Kitamura", "北村匠海", "北村匠海", 1997, "日本", "俳優"),
            ("Yuki Yamada", "山田裕貴", "山田裕貴", 1990, "日本", "俳優"),
            ("Shinnosuke Mitsushima", "満島真之介", "満島真之介", 1989, "日本", "俳優"),
            ("Ryo Narita", "成田凌", "成田凌", 1993, "日本", "俳優"),
            ("Shun Oguri", "小栗旬", "小栗旬", 1982, "日本", "俳優"),
            ("Tsuyoshi Kusanagi", "草なぎ剛", "草なぎ剛", 1974, "日本", "俳優"),
            ("Satoshi Tsumabuki", "妻夫木聡", "妻夫木聡", 1980, "日本", "俳優"),
            ("Hiroshi Abe", "阿部寛", "阿部寛", 1964, "日本", "俳優"),
            ("Toshiyuki Nishida", "西田敏行", "西田敏行", 1947, "日本", "俳優"),
            ("Ken Watanabe", "渡辺謙", "渡辺謙", 1959, "日本", "俳優"),
            ("Koji Yakusho", "役所広司", "役所広司", 1956, "日本", "俳優"),

            # ベテラン女優
            ("Sayuri Yoshinaga", "吉永小百合", "吉永小百合", 1945, "日本", "女優"),
            ("Yoshiko Mita", "三田佳子", "三田佳子", 1941, "日本", "女優"),
            ("Hitomi Kuroki", "黒木瞳", "黒木瞳", 1960, "日本", "女優"),
            ("Ryoko Yonekura", "米倉涼子", "米倉涼子", 1975, "日本", "女優"),
            ("Yukie Nakama", "仲間由紀恵", "仲間由紀恵", 1979, "日本", "女優"),
            ("Kyoko Fukada", "深田恭子", "深田恭子", 1982, "日本", "女優"),
            ("Maki Horikita", "堀北真希", "堀北真希", 1988, "日本", "元女優"),
            ("Yuko Oshima", "大島優子", "大島優子", 1988, "日本", "女優"),
            ("Kou Shibasaki", "柴咲コウ", "柴咲コウ", 1981, "日本", "女優"),
            ("Mao Inoue", "井上真央", "井上真央", 1987, "日本", "女優"),
        ]

        for actor_data in actors:
            person_name, person_name_ja, display, birth_year, nationality, occupation = actor_data
            if self.add_person(
                person_name=person_name,
                person_name_ja=person_name_ja,
                person_name_display=display,
                birth_year=birth_year,
                nationality=nationality,
                occupation=occupation,
                category="現代のイノベーター"
            ):
                self.stats['phase4_actor'] += 1

        print(f"  ✓ Phase 4完了: {self.stats['phase4_actor']}件収集")

    def phase5_sports_athletes(self):
        """Phase 5: スポーツ選手収集"""
        print("\n⚽ Phase 5: スポーツ選手収集開始...")

        athletes = [
            # 野球レジェンド
            ("Sadaharu Oh", "王貞治", "王貞治", 1940, "日本", "元野球選手"),
            ("Shigeo Nagashima", "長嶋茂雄", "長嶋茂雄", 1936, "日本", "元野球選手"),
            ("Hideo Nomo", "野茂英雄", "野茂英雄", 1968, "日本", "元野球選手"),
            ("Daisuke Matsuzaka", "松坂大輔", "松坂大輔", 1980, "日本", "元野球選手"),
            ("Koji Uehara", "上原浩治", "上原浩治", 1975, "日本", "元野球選手"),
            ("Hisashi Iwakuma", "岩隈久志", "岩隈久志", 1981, "日本", "元野球選手"),
            ("Hiroki Kuroda", "黒田博樹", "黒田博樹", 1975, "日本", "元野球選手"),
            ("Kenta Maeda", "前田健太", "前田健太", 1988, "日本", "野球選手"),
            ("Yoshinobu Yamamoto", "山本由伸", "山本由伸", 1998, "日本", "野球選手"),
            ("Roki Sasaki", "佐々木朗希", "佐々木朗希", 2001, "日本", "野球選手"),
            ("Munetaka Murakami", "村上宗隆", "村上宗隆", 2000, "日本", "野球選手"),
            ("Tomoya Mori", "森友哉", "森友哉", 1995, "日本", "野球選手"),
            ("Yuki Yanagita", "柳田悠岐", "柳田悠岐", 1988, "日本", "野球選手"),
            ("Masataka Yoshida", "吉田正尚", "吉田正尚", 1993, "日本", "野球選手"),

            # サッカー
            ("Hidetoshi Nakata", "中田英寿", "中田英寿", 1977, "日本", "元サッカー選手"),
            ("Keisuke Honda", "本田圭佑", "本田圭佑", 1986, "日本", "元サッカー選手"),
            ("Shinji Kagawa", "香川真司", "香川真司", 1989, "日本", "サッカー選手"),
            ("Yuto Nagatomo", "長友佑都", "長友佑都", 1986, "日本", "サッカー選手"),
            ("Maya Yoshida", "吉田麻也", "吉田麻也", 1988, "日本", "サッカー選手"),
            ("Makoto Hasebe", "長谷部誠", "長谷部誠", 1984, "日本", "元サッカー選手"),
            ("Shinji Okazaki", "岡崎慎司", "岡崎慎司", 1986, "日本", "元サッカー選手"),
            ("Takumi Minamino", "南野拓実", "南野拓実", 1995, "日本", "サッカー選手"),
            ("Takehiro Tomiyasu", "冨安健洋", "冨安健洋", 1998, "日本", "サッカー選手"),
            ("Kaoru Mitoma", "三笘薫", "三笘薫", 1997, "日本", "サッカー選手"),
            ("Daichi Kamada", "鎌田大地", "鎌田大地", 1996, "日本", "サッカー選手"),
            ("Wataru Endo", "遠藤航", "遠藤航", 1993, "日本", "サッカー選手"),
            ("Ao Tanaka", "田中碧", "田中碧", 1998, "日本", "サッカー選手"),
            ("Ritsu Doan", "堂安律", "堂安律", 1998, "日本", "サッカー選手"),
            ("Junya Ito", "伊東純也", "伊東純也", 1993, "日本", "サッカー選手"),

            # テニス
            ("Kimiko Date", "伊達公子", "伊達公子", 1970, "日本", "元テニス選手"),
            ("Ai Sugiyama", "杉山愛", "杉山愛", 1975, "日本", "元テニス選手"),

            # フィギュアスケート（追加）
            ("Mao Asada", "浅田真央", "浅田真央", 1990, "日本", "元フィギュアスケート選手"),
            ("Yuna Kim", "キム・ヨナ", "キム・ヨナ", 1990, "韓国", "元フィギュアスケート選手"),
            ("Miki Ando", "安藤美姫", "安藤美姫", 1987, "日本", "元フィギュアスケート選手"),
            ("Shizuka Arakawa", "荒川静香", "荒川静香", 1981, "日本", "元フィギュアスケート選手"),
            ("Midori Ito", "伊藤みどり", "伊藤みどり", 1969, "日本", "元フィギュアスケート選手"),
            ("Daisuke Takahashi", "高橋大輔", "高橋大輔", 1986, "日本", "フィギュアスケート選手"),
            ("Nathan Chen", "ネイサン・チェン", "ネイサン・チェン", 1999, "アメリカ", "フィギュアスケート選手"),

            # 水泳
            ("Kosuke Kitajima", "北島康介", "北島康介", 1982, "日本", "元水泳選手"),
            ("Daiya Seto", "瀬戸大也", "瀬戸大也", 1994, "日本", "水泳選手"),
            ("Rikako Ikee", "池江璃花子", "池江璃花子", 2000, "日本", "水泳選手"),

            # 体操
            ("Kohei Uchimura", "内村航平", "内村航平", 1989, "日本", "体操選手"),
            ("Kenzo Shirai", "白井健三", "白井健三", 1996, "日本", "元体操選手"),
            ("Daiki Hashimoto", "橋本大輝", "橋本大輝", 2001, "日本", "体操選手"),

            # 柔道
            ("Yasuhiro Yamashita", "山下泰裕", "山下泰裕", 1957, "日本", "元柔道選手"),
            ("Tadahiro Nomura", "野村忠宏", "野村忠宏", 1974, "日本", "元柔道選手"),
            ("Ryoko Tani", "谷亮子", "谷亮子", 1975, "日本", "元柔道選手"),
            ("Kaori Matsumoto", "松本薫", "松本薫", 1987, "日本", "元柔道選手"),
            ("Uta Abe", "阿部詩", "阿部詩", 2000, "日本", "柔道選手"),
            ("Hifumi Abe", "阿部一二三", "阿部一二三", 1997, "日本", "柔道選手"),

            # レスリング
            ("Saori Yoshida", "吉田沙保里", "吉田沙保里", 1982, "日本", "元レスリング選手"),
            ("Kaori Icho", "伊調馨", "伊調馨", 1984, "日本", "元レスリング選手"),
            ("Risako Kawai", "川井梨紗子", "川井梨紗子", 1994, "日本", "レスリング選手"),
            ("Yukako Kawai", "川井友香子", "川井友香子", 1997, "日本", "レスリング選手"),

            # ボクシング
            ("Naoya Inoue", "井上尚弥", "井上尚弥", 1993, "日本", "ボクシング選手"),
            ("Kazuto Ioka", "井岡一翔", "井岡一翔", 1989, "日本", "ボクシング選手"),
            ("Ryota Murata", "村田諒太", "村田諒太", 1986, "日本", "元ボクシング選手"),

            # バスケットボール
            ("Rui Hachimura", "八村塁", "八村塁", 1998, "日本", "バスケットボール選手"),
            ("Yuta Watanabe", "渡邊雄太", "渡邊雄太", 1994, "日本", "バスケットボール選手"),

            # ゴルフ
            ("Hideki Matsuyama", "松山英樹", "松山英樹", 1992, "日本", "ゴルフ選手"),
            ("Hinako Shibuno", "渋野日向子", "渋野日向子", 1998, "日本", "ゴルフ選手"),

            # 陸上
            ("Yoshihide Kiryu", "桐生祥秀", "桐生祥秀", 1995, "日本", "陸上選手"),
            ("Shuhei Tada", "多田修平", "多田修平", 1996, "日本", "陸上選手"),
            ("Ryuji Miura", "三浦龍司", "三浦龍司", 2002, "日本", "陸上選手"),
        ]

        for athlete_data in athletes:
            person_name, person_name_ja, display, birth_year, nationality, occupation = athlete_data
            if self.add_person(
                person_name=person_name,
                person_name_ja=person_name_ja,
                person_name_display=display,
                birth_year=birth_year,
                nationality=nationality,
                occupation=occupation,
                category="現代のイノベーター"
            ):
                self.stats['phase5_sports'] += 1

        print(f"  ✓ Phase 5完了: {self.stats['phase5_sports']}件収集")

    def phase6_foreign_celebrities(self):
        """Phase 6: 海外有名人収集"""
        print("\n🌍 Phase 6: 海外有名人収集開始...")

        celebrities = [
            # ハリウッド俳優
            ("Tom Cruise", "トム・クルーズ", "トム・クルーズ", 1962, "アメリカ", "俳優"),
            ("Brad Pitt", "ブラッド・ピット", "ブラッド・ピット", 1963, "アメリカ", "俳優"),
            ("Leonardo DiCaprio", "レオナルド・ディカプリオ", "レオナルド・ディカプリオ", 1974, "アメリカ", "俳優"),
            ("Johnny Depp", "ジョニー・デップ", "ジョニー・デップ", 1963, "アメリカ", "俳優"),
            ("Will Smith", "ウィル・スミス", "ウィル・スミス", 1968, "アメリカ", "俳優"),
            ("Robert Downey Jr.", "ロバート・ダウニー・Jr.", "ロバート・ダウニー・Jr.", 1965, "アメリカ", "俳優"),
            ("Chris Evans", "クリス・エヴァンス", "クリス・エヴァンス", 1981, "アメリカ", "俳優"),
            ("Chris Hemsworth", "クリス・ヘムズワース", "クリス・ヘムズワース", 1983, "オーストラリア", "俳優"),
            ("Ryan Reynolds", "ライアン・レイノルズ", "ライアン・レイノルズ", 1976, "カナダ", "俳優"),
            ("Tom Holland", "トム・ホランド", "トム・ホランド", 1996, "イギリス", "俳優"),

            # ハリウッド女優
            ("Scarlett Johansson", "スカーレット・ヨハンソン", "スカーレット・ヨハンソン", 1984, "アメリカ", "女優"),
            ("Emma Watson", "エマ・ワトソン", "エマ・ワトソン", 1990, "イギリス", "女優"),
            ("Anne Hathaway", "アン・ハサウェイ", "アン・ハサウェイ", 1982, "アメリカ", "女優"),
            ("Jennifer Lawrence", "ジェニファー・ローレンス", "ジェニファー・ローレンス", 1990, "アメリカ", "女優"),
            ("Emma Stone", "エマ・ストーン", "エマ・ストーン", 1988, "アメリカ", "女優"),
            ("Angelina Jolie", "アンジェリーナ・ジョリー", "アンジェリーナ・ジョリー", 1975, "アメリカ", "女優"),
            ("Gal Gadot", "ガル・ガドット", "ガル・ガドット", 1985, "イスラエル", "女優"),
            ("Margot Robbie", "マーゴット・ロビー", "マーゴット・ロビー", 1990, "オーストラリア", "女優"),
            ("Zendaya", "ゼンデイヤ", "ゼンデイヤ", 1996, "アメリカ", "女優"),

            # サッカー選手
            ("Lionel Messi", "リオネル・メッシ", "メッシ", 1987, "アルゼンチン", "サッカー選手"),
            ("Cristiano Ronaldo", "クリスティアーノ・ロナウド", "ロナウド", 1985, "ポルトガル", "サッカー選手"),
            ("Neymar Jr.", "ネイマール", "ネイマール", 1992, "ブラジル", "サッカー選手"),
            ("Kylian Mbappe", "キリアン・エムバペ", "エムバペ", 1998, "フランス", "サッカー選手"),
            ("Erling Haaland", "アーリング・ハーランド", "ハーランド", 2000, "ノルウェー", "サッカー選手"),
            ("Kevin De Bruyne", "ケヴィン・デ・ブライネ", "デ・ブライネ", 1991, "ベルギー", "サッカー選手"),
            ("Mohamed Salah", "モハメド・サラー", "サラー", 1992, "エジプト", "サッカー選手"),
            ("Robert Lewandowski", "ロベルト・レヴァンドフスキ", "レヴァンドフスキ", 1988, "ポーランド", "サッカー選手"),
            ("Karim Benzema", "カリム・ベンゼマ", "ベンゼマ", 1987, "フランス", "サッカー選手"),
            ("Luka Modric", "ルカ・モドリッチ", "モドリッチ", 1985, "クロアチア", "サッカー選手"),

            # バスケットボール選手
            ("LeBron James", "レブロン・ジェームズ", "レブロン", 1984, "アメリカ", "バスケットボール選手"),
            ("Stephen Curry", "ステフィン・カリー", "カリー", 1988, "アメリカ", "バスケットボール選手"),
            ("Kevin Durant", "ケビン・デュラント", "デュラント", 1988, "アメリカ", "バスケットボール選手"),
            ("Giannis Antetokounmpo", "ヤニス・アデトクンボ", "ヤニス", 1994, "ギリシャ", "バスケットボール選手"),
            ("Nikola Jokic", "ニコラ・ヨキッチ", "ヨキッチ", 1995, "セルビア", "バスケットボール選手"),
            ("Luka Doncic", "ルカ・ドンチッチ", "ドンチッチ", 1999, "スロベニア", "バスケットボール選手"),

            # テニス選手
            ("Roger Federer", "ロジャー・フェデラー", "フェデラー", 1981, "スイス", "元テニス選手"),
            ("Rafael Nadal", "ラファエル・ナダル", "ナダル", 1986, "スペイン", "テニス選手"),
            ("Novak Djokovic", "ノバク・ジョコビッチ", "ジョコビッチ", 1987, "セルビア", "テニス選手"),
            ("Serena Williams", "セリーナ・ウィリアムズ", "セリーナ", 1981, "アメリカ", "元テニス選手"),

            # 音楽アーティスト
            ("Taylor Swift", "テイラー・スウィフト", "テイラー・スウィフト", 1989, "アメリカ", "歌手"),
            ("Ariana Grande", "アリアナ・グランデ", "アリアナ・グランデ", 1993, "アメリカ", "歌手"),
            ("Billie Eilish", "ビリー・アイリッシュ", "ビリー・アイリッシュ", 2001, "アメリカ", "歌手"),
            ("Ed Sheeran", "エド・シーラン", "エド・シーラン", 1991, "イギリス", "歌手"),
            ("Bruno Mars", "ブルーノ・マーズ", "ブルーノ・マーズ", 1985, "アメリカ", "歌手"),
            ("Justin Bieber", "ジャスティン・ビーバー", "ジャスティン・ビーバー", 1994, "カナダ", "歌手"),
            ("Drake", "ドレイク", "ドレイク", 1986, "カナダ", "ラッパー"),
            ("Eminem", "エミネム", "エミネム", 1972, "アメリカ", "ラッパー"),
            ("Kanye West", "カニエ・ウェスト", "カニエ・ウェスト", 1977, "アメリカ", "ラッパー"),
            ("Beyonce", "ビヨンセ", "ビヨンセ", 1981, "アメリカ", "歌手"),
            ("Rihanna", "リアーナ", "リアーナ", 1988, "バルバドス", "歌手"),
            ("Lady Gaga", "レディー・ガガ", "レディー・ガガ", 1986, "アメリカ", "歌手"),
            ("Adele", "アデル", "アデル", 1988, "イギリス", "歌手"),
            ("Dua Lipa", "デュア・リパ", "デュア・リパ", 1995, "イギリス", "歌手"),
            ("The Weeknd", "ザ・ウィークエンド", "ザ・ウィークエンド", 1990, "カナダ", "歌手"),
            ("Post Malone", "ポスト・マローン", "ポスト・マローン", 1995, "アメリカ", "歌手"),

            # K-POP（追加）
            ("IU", "アイユー", "IU", 1993, "韓国", "歌手"),
            ("G-Dragon", "G-DRAGON", "G-DRAGON", 1988, "韓国", "歌手"),
            ("Psy", "サイ", "PSY", 1977, "韓国", "歌手"),
        ]

        for celeb_data in celebrities:
            person_name, person_name_ja, display, birth_year, nationality, occupation = celeb_data
            if self.add_person(
                person_name=person_name,
                person_name_ja=person_name_ja,
                person_name_display=display,
                birth_year=birth_year,
                nationality=nationality,
                occupation=occupation,
                category="現代のイノベーター"
            ):
                self.stats['phase6_foreign'] += 1

        print(f"  ✓ Phase 6完了: {self.stats['phase6_foreign']}件収集")

    def phase7_youtubers_streamers(self):
        """Phase 7: YouTuber・配信者収集"""
        print("\n📹 Phase 7: YouTuber・配信者収集開始...")

        youtubers = [
            # コムドット
            ("Yamato", "やまと", "やまと（コムドット）", 1998, "日本", "YouTuber", "コムドット"),
            ("Yuta", "ゆうた", "ゆうた（コムドット）", 1999, "日本", "YouTuber", "コムドット"),
            ("Yuma", "ゆうま", "ゆうま（コムドット）", 1998, "日本", "YouTuber", "コムドット"),
            ("Hyuga", "ひゅうが", "ひゅうが（コムドット）", 1998, "日本", "YouTuber", "コムドット"),
            ("Amugiri", "あむぎり", "あむぎり（コムドット）", 1999, "日本", "YouTuber", "コムドット"),

            # スカイピース
            ("Teo", "テオくん", "テオくん（スカイピース）", 1995, "日本", "YouTuber", "スカイピース"),
            ("Ini", "☆イニ☆", "☆イニ☆（スカイピース）", 1995, "日本", "YouTuber", "スカイピース"),

            # 平成フラミンゴ
            ("NICO", "にこ", "にこ（平成フラミンゴ）", 1992, "日本", "YouTuber", "平成フラミンゴ"),
            ("RIHO", "りほ", "りほ（平成フラミンゴ）", 1994, "日本", "YouTuber", "平成フラミンゴ"),

            # カジサック
            ("Kajisac", "カジサック", "カジサック", 1980, "日本", "YouTuber"),

            # ヒカル
            ("Hikaru", "ヒカル", "ヒカル", 1991, "日本", "YouTuber"),

            # ラファエル
            ("Raphael", "ラファエル", "ラファエル", 1989, "日本", "YouTuber"),

            # てんちむ
            ("Tenchim", "てんちむ", "てんちむ", 1993, "日本", "YouTuber"),

            # ゆきりぬ
            ("Yukirinu", "ゆきりぬ", "ゆきりぬ", 1996, "日本", "YouTuber"),

            # エミリン
            ("Emirin", "エミリン", "エミリン", 1993, "日本", "YouTuber"),

            # 朝倉未来
            ("Mikuru Asakura", "朝倉未来", "朝倉未来", 1992, "日本", "YouTuber"),

            # 朝倉海
            ("Kai Asakura", "朝倉海", "朝倉海", 1993, "日本", "YouTuber"),

            # ヴァンゆん
            ("Vanyu", "ヴァンビ", "ヴァンビ（ヴァンゆん）", 1995, "日本", "YouTuber", "ヴァンゆん"),
            ("Yun", "ゆん", "ゆん（ヴァンゆん）", 1996, "日本", "YouTuber", "ヴァンゆん"),

            # ばんばんざい
            ("Ryuga", "りゅうが", "りゅうが（ばんばんざい）", 1999, "日本", "YouTuber", "ばんばんざい"),
            ("Miyuu", "みゆ", "みゆ（ばんばんざい）", 1999, "日本", "YouTuber", "ばんばんざい"),
            ("Ginjiro", "ぎんじろう", "ぎんじろう（ばんばんざい）", 1999, "日本", "YouTuber", "ばんばんざい"),

            # パパラピーズ
            ("Tanukana", "タヌカナ", "タヌカナ（パパラピーズ）", 1995, "日本", "YouTuber", "パパラピーズ"),
            ("Jukiya", "じゅきや", "じゅきや（パパラピーズ）", 1995, "日本", "YouTuber", "パパラピーズ"),

            # なこなこチャンネル
            ("Nagomi", "なごみ", "なごみ（なこなこ）", 2000, "日本", "YouTuber", "なこなこチャンネル"),
            ("Koki", "こーくん", "こーくん（なこなこ）", 2000, "日本", "YouTuber", "なこなこチャンネル"),

            # 夕闇に誘いし漆黒の天使達
            ("Yami", "やみ", "やみ（夕闇）", 1995, "日本", "YouTuber", "夕闇に誘いし漆黒の天使達"),
            ("Kuro", "くろ", "くろ（夕闇）", 1995, "日本", "YouTuber", "夕闇に誘いし漆黒の天使達"),

            # きりたんぽ
            ("Kiritanpo", "きりたんぽ", "きりたんぽ", 1993, "日本", "YouTuber"),

            # けみお
            ("Kemio", "けみお", "けみお", 1995, "日本", "YouTuber"),

            # ゆうこす
            ("Yukos", "ゆうこす", "ゆうこす", 1994, "日本", "YouTuber"),

            # ねお
            ("Neo", "ねお", "ねお", 2001, "日本", "YouTuber"),

            # みきぽん
            ("Mikipon", "みきぽん", "みきぽん", 1992, "日本", "YouTuber"),

            # さぁや
            ("Saaya", "さぁや", "さぁや", 1995, "日本", "YouTuber"),

            # あやなん
            ("Ayanan", "あやなん", "あやなん", 1993, "日本", "YouTuber"),

            # しばなん
            ("Shibanan", "しばなん", "しばなん", 1993, "日本", "YouTuber"),
        ]

        for youtuber_data in youtubers:
            if len(youtuber_data) == 7:  # グループメンバー
                person_name, person_name_ja, display, birth_year, nationality, occupation, group_name = youtuber_data
                if self.add_person(
                    person_name=person_name,
                    person_name_ja=person_name_ja,
                    person_name_display=display,
                    birth_year=birth_year,
                    nationality=nationality,
                    occupation=occupation,
                    category="現代のイノベーター",
                    group_name=group_name
                ):
                    self.stats['phase7_youtuber'] += 1
            else:  # ソロ
                person_name, person_name_ja, display, birth_year, nationality, occupation = youtuber_data
                if self.add_person(
                    person_name=person_name,
                    person_name_ja=person_name_ja,
                    person_name_display=display,
                    birth_year=birth_year,
                    nationality=nationality,
                    occupation=occupation,
                    category="現代のイノベーター"
                ):
                    self.stats['phase7_youtuber'] += 1

        print(f"  ✓ Phase 7完了: {self.stats['phase7_youtuber']}件収集")

    def phase8_historical_figures(self):
        """Phase 8: 歴史上の人物（追加）収集"""
        print("\n📚 Phase 8: 歴史上の人物（追加）収集開始...")

        historical = [
            # 日本の戦国武将（追加）
            ("Mitsuhide Akechi", "明智光秀", "明智光秀", 1528, "日本", "武将"),
            ("Kenshin Uesugi", "上杉謙信", "上杉謙信", 1530, "日本", "武将"),
            ("Shingen Takeda", "武田信玄", "武田信玄", 1521, "日本", "武将"),
            ("Motonari Mori", "毛利元就", "毛利元就", 1497, "日本", "武将"),
            ("Yoshimoto Imagawa", "今川義元", "今川義元", 1519, "日本", "武将"),
            ("Kiyomasa Kato", "加藤清正", "加藤清正", 1562, "日本", "武将"),
            ("Masanori Fukushima", "福島正則", "福島正則", 1561, "日本", "武将"),
            ("Yukimura Sanada", "真田幸村", "真田幸村", 1567, "日本", "武将"),
            ("Kanetsugu Naoe", "直江兼続", "直江兼続", 1560, "日本", "武将"),
            ("Yoshihiro Shimazu", "島津義弘", "島津義弘", 1535, "日本", "武将"),

            # 幕末の志士（追加）
            ("Takamori Saigo", "西郷隆盛", "西郷隆盛", 1828, "日本", "政治家"),
            ("Toshimichi Okubo", "大久保利通", "大久保利通", 1830, "日本", "政治家"),
            ("Takayoshi Kido", "木戸孝允", "木戸孝允", 1833, "日本", "政治家"),
            ("Shinsaku Takasugi", "高杉晋作", "高杉晋作", 1839, "日本", "志士"),
            ("Isami Kondo", "近藤勇", "近藤勇", 1834, "日本", "新選組局長"),
            ("Toshizo Hijikata", "土方歳三", "土方歳三", 1835, "日本", "新選組副長"),
            ("Soji Okita", "沖田総司", "沖田総司", 1842, "日本", "新選組隊士"),
            ("Kaishu Katsu", "勝海舟", "勝海舟", 1823, "日本", "政治家"),
            ("Shoin Yoshida", "吉田松陰", "吉田松陰", 1830, "日本", "思想家"),

            # 日本の文化人（追加）
            ("Hokusai Katsushika", "葛飾北斎", "葛飾北斎", 1760, "日本", "浮世絵師"),
            ("Hiroshige Utagawa", "歌川広重", "歌川広重", 1797, "日本", "浮世絵師"),
            ("Sharaku Toshusai", "東洲斎写楽", "写楽", 1763, "日本", "浮世絵師"),
            ("Basho Matsuo", "松尾芭蕉", "松尾芭蕉", 1644, "日本", "俳人"),
            ("Rikyu Sen", "千利休", "千利休", 1522, "日本", "茶人"),
            ("Chikamatsu Monzaemon", "近松門左衛門", "近松門左衛門", 1653, "日本", "劇作家"),

            # 世界の歴史的人物（追加）
            ("George Washington", "ジョージ・ワシントン", "ジョージ・ワシントン", 1732, "アメリカ", "初代大統領"),
            ("Benjamin Franklin", "ベンジャミン・フランクリン", "ベンジャミン・フランクリン", 1706, "アメリカ", "政治家"),
            ("Thomas Jefferson", "トーマス・ジェファーソン", "トーマス・ジェファーソン", 1743, "アメリカ", "大統領"),
            ("Theodore Roosevelt", "セオドア・ルーズベルト", "セオドア・ルーズベルト", 1858, "アメリカ", "大統領"),
            ("Franklin Roosevelt", "フランクリン・ルーズベルト", "フランクリン・ルーズベルト", 1882, "アメリカ", "大統領"),
            ("John F. Kennedy", "ジョン・F・ケネディ", "JFK", 1917, "アメリカ", "大統領"),
            ("Martin Luther King Jr.", "マーティン・ルーサー・キング・Jr.", "キング牧師", 1929, "アメリカ", "公民権運動指導者"),
            ("Malcolm X", "マルコムX", "マルコムX", 1925, "アメリカ", "公民権運動活動家"),
            ("Che Guevara", "チェ・ゲバラ", "チェ・ゲバラ", 1928, "アルゼンチン", "革命家"),
            ("Fidel Castro", "フィデル・カストロ", "カストロ", 1926, "キューバ", "革命家"),
            ("Vladimir Lenin", "ウラジーミル・レーニン", "レーニン", 1870, "ロシア", "革命家"),
            ("Joseph Stalin", "ヨシフ・スターリン", "スターリン", 1878, "ソ連", "指導者"),
            ("Adolf Hitler", "アドルフ・ヒトラー", "ヒトラー", 1889, "ドイツ", "独裁者"),
            ("Benito Mussolini", "ベニート・ムッソリーニ", "ムッソリーニ", 1883, "イタリア", "独裁者"),
            ("Mao Zedong", "毛沢東", "毛沢東", 1893, "中国", "政治家"),
            ("Deng Xiaoping", "鄧小平", "鄧小平", 1904, "中国", "政治家"),
            ("Ho Chi Minh", "ホー・チ・ミン", "ホー・チ・ミン", 1890, "ベトナム", "革命家"),

            # 科学者・発明家（追加）
            ("Galileo Galilei", "ガリレオ・ガリレイ", "ガリレオ", 1564, "イタリア", "天文学者"),
            ("Johannes Kepler", "ヨハネス・ケプラー", "ケプラー", 1571, "ドイツ", "天文学者"),
            ("Nicolaus Copernicus", "ニコラウス・コペルニクス", "コペルニクス", 1473, "ポーランド", "天文学者"),
            ("Michael Faraday", "マイケル・ファラデー", "ファラデー", 1791, "イギリス", "物理学者"),
            ("James Clerk Maxwell", "ジェームズ・クラーク・マクスウェル", "マクスウェル", 1831, "イギリス", "物理学者"),
            ("Nikola Tesla", "ニコラ・テスラ", "テスラ", 1856, "セルビア", "発明家"),
            ("Alexander Fleming", "アレクサンダー・フレミング", "フレミング", 1881, "イギリス", "細菌学者"),
            ("Louis Pasteur", "ルイ・パスツール", "パスツール", 1822, "フランス", "細菌学者"),
            ("Gregor Mendel", "グレゴール・メンデル", "メンデル", 1822, "オーストリア", "遺伝学者"),
            ("James Watson", "ジェームズ・ワトソン", "ワトソン", 1928, "アメリカ", "分子生物学者"),
            ("Francis Crick", "フランシス・クリック", "クリック", 1916, "イギリス", "分子生物学者"),
            ("Stephen Hawking", "スティーヴン・ホーキング", "ホーキング", 1942, "イギリス", "物理学者"),
        ]

        for hist_data in historical:
            person_name, person_name_ja, display, birth_year, nationality, occupation = hist_data
            if self.add_person(
                person_name=person_name,
                person_name_ja=person_name_ja,
                person_name_display=display,
                birth_year=birth_year,
                nationality=nationality,
                occupation=occupation,
                category="歴史的偉人"
            ):
                self.stats['phase8_historical'] += 1

        print(f"  ✓ Phase 8完了: {self.stats['phase8_historical']}件収集")

    def phase9_others(self):
        """Phase 9: その他有名人収集"""
        print("\n🌟 Phase 9: その他有名人収集開始...")

        others = [
            # 有名な動物
            ("Hachiko", "ハチ公", "ハチ公", 1923, "日本", "忠犬", False, True),
            ("Tama", "たま", "たま（駅長猫）", 1999, "日本", "駅長猫", False, True),
            ("Wasao", "わさお", "わさお", 2008, "日本", "秋田犬", False, True),
            ("Shabani", "シャバーニ", "シャバーニ", 1996, "オランダ", "ゴリラ", False, True),
            ("Shan Shan", "シャンシャン", "シャンシャン", 2017, "日本", "パンダ", False, True),
            ("Rascal", "ラスカル", "ラスカル", 1977, "アメリカ", "アライグマ", True, True),

            # 競走馬（追加）
            ("Orfevre", "オルフェーヴル", "オルフェーヴル", 2008, "日本", "競走馬", False, True),
            ("Deep Impact", "ディープインパクト", "ディープインパクト", 2002, "日本", "競走馬", False, True),
            ("Kitasan Black", "キタサンブラック", "キタサンブラック", 2012, "日本", "競走馬", False, True),
            ("Almond Eye", "アーモンドアイ", "アーモンドアイ", 2015, "日本", "競走馬", False, True),
            ("Oguri Cap", "オグリキャップ", "オグリキャップ", 1985, "日本", "競走馬", False, True),
            ("Narita Brian", "ナリタブライアン", "ナリタブライアン", 1991, "日本", "競走馬", False, True),
            ("Silence Suzuka", "サイレンススズカ", "サイレンススズカ", 1994, "日本", "競走馬", False, True),
            ("Tokai Teio", "トウカイテイオー", "トウカイテイオー", 1988, "日本", "競走馬", False, True),
            ("Mejiro McQueen", "メジロマックイーン", "メジロマックイーン", 1987, "日本", "競走馬", False, True),
            ("Special Week", "スペシャルウィーク", "スペシャルウィーク", 1995, "日本", "競走馬", False, True),

            # 実業家（追加）
            ("Elon Musk", "イーロン・マスク", "イーロン・マスク", 1971, "南アフリカ", "実業家"),
            ("Jeff Bezos", "ジェフ・ベゾス", "ジェフ・ベゾス", 1964, "アメリカ", "実業家"),
            ("Bill Gates", "ビル・ゲイツ", "ビル・ゲイツ", 1955, "アメリカ", "実業家"),
            ("Mark Zuckerberg", "マーク・ザッカーバーグ", "ザッカーバーグ", 1984, "アメリカ", "実業家"),
            ("Warren Buffett", "ウォーレン・バフェット", "バフェット", 1930, "アメリカ", "投資家"),
            ("Steve Jobs", "スティーブ・ジョブズ", "ジョブズ", 1955, "アメリカ", "実業家"),
            ("Larry Page", "ラリー・ペイジ", "ラリー・ペイジ", 1973, "アメリカ", "実業家"),
            ("Sergey Brin", "セルゲイ・ブリン", "セルゲイ・ブリン", 1973, "ロシア", "実業家"),
            ("Jack Ma", "ジャック・マー", "ジャック・マー", 1964, "中国", "実業家"),
            ("Masayoshi Son", "孫正義", "孫正義", 1957, "日本", "実業家"),
            ("Tadashi Yanai", "柳井正", "柳井正", 1949, "日本", "実業家"),
            ("Hiroshi Mikitani", "三木谷浩史", "三木谷浩史", 1965, "日本", "実業家"),

            # ファッションデザイナー
            ("Coco Chanel", "ココ・シャネル", "ココ・シャネル", 1883, "フランス", "デザイナー"),
            ("Christian Dior", "クリスチャン・ディオール", "ディオール", 1905, "フランス", "デザイナー"),
            ("Yves Saint Laurent", "イヴ・サンローラン", "サンローラン", 1936, "フランス", "デザイナー"),
            ("Giorgio Armani", "ジョルジオ・アルマーニ", "アルマーニ", 1934, "イタリア", "デザイナー"),
            ("Gianni Versace", "ジャンニ・ヴェルサーチ", "ヴェルサーチ", 1946, "イタリア", "デザイナー"),
            ("Karl Lagerfeld", "カール・ラガーフェルド", "カール・ラガーフェルド", 1933, "ドイツ", "デザイナー"),
            ("Rei Kawakubo", "川久保玲", "川久保玲", 1942, "日本", "デザイナー"),
            ("Yohji Yamamoto", "山本耀司", "山本耀司", 1943, "日本", "デザイナー"),
            ("Kenzo Takada", "高田賢三", "ケンゾー", 1939, "日本", "デザイナー"),
            ("Issey Miyake", "三宅一生", "三宅一生", 1938, "日本", "デザイナー"),

            # 映画監督
            ("Steven Spielberg", "スティーヴン・スピルバーグ", "スピルバーグ", 1946, "アメリカ", "映画監督"),
            ("George Lucas", "ジョージ・ルーカス", "ジョージ・ルーカス", 1944, "アメリカ", "映画監督"),
            ("James Cameron", "ジェームズ・キャメロン", "キャメロン", 1954, "カナダ", "映画監督"),
            ("Christopher Nolan", "クリストファー・ノーラン", "ノーラン", 1970, "イギリス", "映画監督"),
            ("Quentin Tarantino", "クエンティン・タランティーノ", "タランティーノ", 1963, "アメリカ", "映画監督"),
            ("Martin Scorsese", "マーティン・スコセッシ", "スコセッシ", 1942, "アメリカ", "映画監督"),
            ("Francis Ford Coppola", "フランシス・フォード・コッポラ", "コッポラ", 1939, "アメリカ", "映画監督"),
            ("Stanley Kubrick", "スタンリー・キューブリック", "キューブリック", 1928, "アメリカ", "映画監督"),
            ("Alfred Hitchcock", "アルフレッド・ヒッチコック", "ヒッチコック", 1899, "イギリス", "映画監督"),
            ("Akira Kurosawa", "黒澤明", "黒澤明", 1910, "日本", "映画監督"),
            ("Hayao Miyazaki", "宮崎駿", "宮崎駿", 1941, "日本", "アニメ監督"),
            ("Makoto Shinkai", "新海誠", "新海誠", 1973, "日本", "アニメ監督"),
            ("Mamoru Hosoda", "細田守", "細田守", 1967, "日本", "アニメ監督"),
            ("Hideaki Anno", "庵野秀明", "庵野秀明", 1960, "日本", "アニメ監督"),
        ]

        for other_data in others:
            if len(other_data) == 8:  # 動物
                person_name, person_name_ja, display, birth_year, nationality, occupation, is_fictional, is_animal = other_data
                if self.add_person(
                    person_name=person_name,
                    person_name_ja=person_name_ja,
                    person_name_display=display,
                    birth_year=birth_year,
                    nationality=nationality,
                    occupation=occupation,
                    category="動物" if is_animal and not is_fictional else "架空の存在" if is_fictional else "現代のイノベーター",
                    is_fictional=is_fictional,
                    is_animal=is_animal
                ):
                    self.stats['phase9_others'] += 1
            else:  # 人物
                person_name, person_name_ja, display, birth_year, nationality, occupation = other_data
                if self.add_person(
                    person_name=person_name,
                    person_name_ja=person_name_ja,
                    person_name_display=display,
                    birth_year=birth_year,
                    nationality=nationality,
                    occupation=occupation,
                    category="現代のイノベーター"
                ):
                    self.stats['phase9_others'] += 1

        print(f"  ✓ Phase 9完了: {self.stats['phase9_others']}件収集")

    def collect_all(self):
        """全フェーズのデータを収集"""
        print("=" * 60)
        print("🚀 Ultra Think Massive Collection 開始")
        print("=" * 60)

        # Phase 4: 俳優・女優
        self.phase4_actors_actresses()

        # Phase 5: スポーツ選手
        self.phase5_sports_athletes()

        # Phase 6: 海外有名人
        self.phase6_foreign_celebrities()

        # Phase 7: YouTuber・配信者
        self.phase7_youtubers_streamers()

        # Phase 8: 歴史上の人物
        self.phase8_historical_figures()

        # Phase 9: その他
        self.phase9_others()

        print(f"\n✅ 収集完了")
        print(f"  総収集数: {self.stats['total_collected']}件")
        print(f"  重複スキップ: {self.stats['duplicates_skipped']}件")

    def save_data(self):
        """データを保存"""
        # 既存データと新規データを結合
        all_data = self.existing_data + self.new_data

        # CSV保存
        with open(self.output_csv, 'w', encoding='utf-8-sig', newline='') as f:
            if all_data:
                writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                writer.writeheader()
                writer.writerows(all_data)

        # JSON保存
        with open(self.output_json, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 保存完了:")
        print(f"  - CSV: {self.output_csv}")
        print(f"  - JSON: {self.output_json}")
        print(f"  - 総レコード数: {len(all_data)}件")

    def generate_report(self):
        """収集レポートを生成"""
        report = f"""# Ultra Think Massive Collection Report

## 実行日時
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 収集結果

### フェーズ別収集数
- Phase 4 (俳優・女優): {self.stats['phase4_actor']}件
- Phase 5 (スポーツ): {self.stats['phase5_sports']}件
- Phase 6 (海外有名人): {self.stats['phase6_foreign']}件
- Phase 7 (YouTuber): {self.stats['phase7_youtuber']}件
- Phase 8 (歴史上の人物): {self.stats['phase8_historical']}件
- Phase 9 (その他): {self.stats['phase9_others']}件

### 統計
- 新規収集: {self.stats['total_collected']}件
- 重複スキップ: {self.stats['duplicates_skipped']}件
- 既存データ: {len(self.existing_data)}件
- 最終総数: {len(self.existing_data) + self.stats['total_collected']}件

### 目標達成状況
- 目標: 11,211件以上
- 現在: {len(self.existing_data) + self.stats['total_collected']}件
- 達成率: {((len(self.existing_data) + self.stats['total_collected']) / 11211 * 100):.1f}%

### 出力ファイル
- CSV: {self.output_csv}
- JSON: {self.output_json}

## カテゴリ別内訳
- 俳優・女優: 日本の人気俳優・女優を中心に収集
- スポーツ選手: 野球、サッカー、テニス、フィギュアスケート等
- 海外有名人: ハリウッドスター、サッカー選手、音楽アーティスト
- YouTuber: コムドット、スカイピース等の人気YouTuber
- 歴史上の人物: 戦国武将、幕末の志士、世界の偉人
- その他: 動物、競走馬、実業家、デザイナー、映画監督
"""

        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📝 レポート生成: {self.report_file}")


def main():
    collector = UltraThinkMassCollectorExtended()
    collector.collect_all()
    collector.save_data()
    collector.generate_report()


if __name__ == "__main__":
    main()
