#!/usr/bin/env python3
"""
Ultra Think Mass Collector
1万人以上の有名人データを段階的に収集
日本人の大半が知っている人物を中心に
"""

import csv
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
import time


class UltraThinkMassCollector:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.existing_file = "ultra_think_ultimate_1211_20250825_163049.csv"
        self.output_csv = f"ultra_think_extended_{self.timestamp}.csv"
        self.output_json = f"ultra_think_extended_{self.timestamp}.json"
        self.report_file = f"COLLECTION_REPORT_{self.timestamp}.md"

        # 既存データを読み込み
        self.existing_data = self.load_existing_data()
        self.existing_names = {r.get('person_name', '') for r in self.existing_data}

        # 収集データ
        self.new_data = []

        # 統計
        self.stats = {
            'phase1_anime': 0,
            'phase2_comedy': 0,
            'phase3_idol': 0,
            'phase4_actor': 0,
            'phase5_sports': 0,
            'phase6_foreign': 0,
            'phase7_youtuber': 0,
            'phase8_others': 0,
            'duplicates_skipped': 0,
            'total_collected': 0
        }

    def load_existing_data(self) -> List[Dict]:
        """既存データを読み込み"""
        with open(self.existing_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            return list(reader)

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
            'batch_id': f'phase_{self.timestamp}',
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
            'phase': f'MassCollection_{self.timestamp}',
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

    def phase1_anime_manga_characters(self):
        """Phase 1: アニメ・漫画キャラクター収集"""
        print("\n📺 Phase 1: アニメ・漫画キャラクター収集開始...")

        characters = [
            # ドラえもん
            ("Doraemon", "ドラえもん", "ドラえもん", 1969, "日本", "ロボット", True),
            ("Nobita Nobi", "野比のび太", "のび太", 1964, "日本", "小学生", True),
            ("Shizuka Minamoto", "源静香", "しずかちゃん", 1964, "日本", "小学生", True),
            ("Takeshi Goda", "剛田武", "ジャイアン", 1964, "日本", "小学生", True),
            ("Suneo Honekawa", "骨川スネ夫", "スネ夫", 1964, "日本", "小学生", True),

            # ポケモン
            ("Pikachu", "ピカチュウ", "ピカチュウ", 1996, "カントー地方", "ポケモン", True),
            ("Satoshi", "サトシ", "サトシ", 1997, "日本", "ポケモントレーナー", True),

            # ドラゴンボール
            ("Son Goku", "孫悟空", "孫悟空", 1984, "サイヤ星", "戦士", True),
            ("Vegeta", "ベジータ", "ベジータ", 1988, "サイヤ星", "王子", True),
            ("Frieza", "フリーザ", "フリーザ", 1990, "不明", "宇宙の帝王", True),
            ("Piccolo", "ピッコロ", "ピッコロ", 1988, "ナメック星", "戦士", True),
            ("Krillin", "クリリン", "クリリン", 1985, "地球", "武道家", True),
            ("Gohan", "孫悟飯", "孫悟飯", 1989, "地球", "戦士", True),

            # ワンピース
            ("Monkey D. Luffy", "モンキー・D・ルフィ", "ルフィ", 1997, "東の海", "海賊", True),
            ("Roronoa Zoro", "ロロノア・ゾロ", "ゾロ", 1997, "東の海", "剣士", True),
            ("Sanji", "サンジ", "サンジ", 1997, "北の海", "コック", True),
            ("Nami", "ナミ", "ナミ", 1997, "東の海", "航海士", True),
            ("Nico Robin", "ニコ・ロビン", "ロビン", 2000, "西の海", "考古学者", True),
            ("Tony Tony Chopper", "トニートニー・チョッパー", "チョッパー", 2000, "グランドライン", "医者", True),

            # 鬼滅の刃
            ("Tanjiro Kamado", "竈門炭治郎", "炭治郎", 2016, "日本", "鬼殺隊", True),
            ("Nezuko Kamado", "竈門禰豆子", "禰豆子", 2016, "日本", "鬼", True),
            ("Zenitsu Agatsuma", "我妻善逸", "善逸", 2016, "日本", "鬼殺隊", True),
            ("Inosuke Hashibira", "嘴平伊之助", "伊之助", 2016, "日本", "鬼殺隊", True),
            ("Giyu Tomioka", "冨岡義勇", "冨岡義勇", 2016, "日本", "水柱", True),
            ("Shinobu Kocho", "胡蝶しのぶ", "胡蝶しのぶ", 2016, "日本", "蟲柱", True),

            # 呪術廻戦
            ("Yuji Itadori", "虎杖悠仁", "虎杖悠仁", 2018, "日本", "呪術師", True),
            ("Megumi Fushiguro", "伏黒恵", "伏黒恵", 2018, "日本", "呪術師", True),
            ("Nobara Kugisaki", "釘崎野薔薇", "釘崎野薔薇", 2018, "日本", "呪術師", True),
            ("Satoru Gojo", "五条悟", "五条悟", 2018, "日本", "特級呪術師", True),
            ("Ryomen Sukuna", "両面宿儺", "宿儺", 2018, "日本", "呪いの王", True),

            # 進撃の巨人
            ("Eren Yeager", "エレン・イェーガー", "エレン", 2009, "パラディ島", "兵士", True),
            ("Mikasa Ackerman", "ミカサ・アッカーマン", "ミカサ", 2009, "パラディ島", "兵士", True),
            ("Armin Arlert", "アルミン・アルレルト", "アルミン", 2009, "パラディ島", "兵士", True),
            ("Levi Ackerman", "リヴァイ・アッカーマン", "リヴァイ兵長", 2009, "パラディ島", "兵士長", True),

            # NARUTO
            ("Naruto Uzumaki", "うずまきナルト", "ナルト", 1999, "木ノ葉隠れ", "忍者", True),
            ("Sasuke Uchiha", "うちはサスケ", "サスケ", 1999, "木ノ葉隠れ", "忍者", True),
            ("Sakura Haruno", "春野サクラ", "サクラ", 1999, "木ノ葉隠れ", "忍者", True),
            ("Kakashi Hatake", "はたけカカシ", "カカシ先生", 1999, "木ノ葉隠れ", "上忍", True),

            # スラムダンク
            ("Hanamichi Sakuragi", "桜木花道", "桜木花道", 1990, "日本", "バスケ選手", True),
            ("Kaede Rukawa", "流川楓", "流川楓", 1990, "日本", "バスケ選手", True),
            ("Takenori Akagi", "赤木剛憲", "ゴリ", 1990, "日本", "バスケ選手", True),

            # 名探偵コナン
            ("Conan Edogawa", "江戸川コナン", "コナン", 1994, "日本", "探偵", True),
            ("Shinichi Kudo", "工藤新一", "新一", 1994, "日本", "高校生探偵", True),
            ("Ran Mouri", "毛利蘭", "蘭", 1994, "日本", "高校生", True),
            ("Kogoro Mouri", "毛利小五郎", "小五郎", 1994, "日本", "探偵", True),

            # エヴァンゲリオン
            ("Shinji Ikari", "碇シンジ", "シンジ", 1995, "日本", "エヴァパイロット", True),
            ("Rei Ayanami", "綾波レイ", "綾波レイ", 1995, "日本", "エヴァパイロット", True),
            ("Asuka Langley", "惣流・アスカ・ラングレー", "アスカ", 1995, "ドイツ", "エヴァパイロット", True),

            # クレヨンしんちゃん
            ("Shinnosuke Nohara", "野原しんのすけ", "しんちゃん", 1992, "日本", "幼稚園児", True),
            ("Misae Nohara", "野原みさえ", "みさえ", 1992, "日本", "主婦", True),
            ("Hiroshi Nohara", "野原ひろし", "ひろし", 1992, "日本", "サラリーマン", True),

            # サザエさん
            ("Sazae Fuguta", "フグ田サザエ", "サザエさん", 1946, "日本", "主婦", True),
            ("Masuo Fuguta", "フグ田マスオ", "マスオさん", 1946, "日本", "サラリーマン", True),
            ("Katsuo Isono", "磯野カツオ", "カツオ", 1946, "日本", "小学生", True),
            ("Wakame Isono", "磯野ワカメ", "ワカメ", 1946, "日本", "小学生", True),
            ("Tara Fuguta", "フグ田タラオ", "タラちゃん", 1946, "日本", "幼児", True),

            # ちびまる子ちゃん
            ("Maruko Sakura", "さくらももこ", "まる子", 1986, "日本", "小学生", True),
            ("Tomozou Sakura", "さくら友蔵", "友蔵", 1986, "日本", "祖父", True),

            # アンパンマン
            ("Anpanman", "アンパンマン", "アンパンマン", 1973, "日本", "ヒーロー", True),
            ("Baikinman", "ばいきんまん", "ばいきんまん", 1973, "バイキン星", "悪役", True),
            ("Dokinchan", "ドキンちゃん", "ドキンちゃん", 1973, "バイキン星", "悪役", True),
            ("Currypanman", "カレーパンマン", "カレーパンマン", 1973, "日本", "ヒーロー", True),
            ("Shokupanman", "しょくぱんまん", "しょくぱんまん", 1973, "日本", "ヒーロー", True),
        ]

        for char_data in characters:
            person_name, person_name_ja, display, birth_year, nationality, occupation, is_fictional = char_data
            self.add_person(
                person_name=person_name,
                person_name_ja=person_name_ja,
                person_name_display=display,
                birth_year=birth_year,
                nationality=nationality,
                occupation=occupation,
                category="架空の存在",
                is_fictional=is_fictional
            )
            self.stats['phase1_anime'] += 1

        print(f"  ✓ Phase 1完了: {self.stats['phase1_anime']}件収集")

    def phase2_comedy_groups(self):
        """Phase 2: お笑い芸人グループメンバー収集"""
        print("\n😂 Phase 2: お笑い芸人グループメンバー収集開始...")

        comedians = [
            # さまぁ〜ず（既存データで確認済み、スキップ）

            # ナインティナイン
            ("Takashi Okamura", "岡村隆史", "岡村隆史", 1970, "日本", "お笑い芸人", "ナインティナイン"),
            ("Hiroyuki Yabe", "矢部浩之", "矢部浩之", 1971, "日本", "お笑い芸人", "ナインティナイン"),

            # とんねるず
            ("Takaaki Ishibashi", "石橋貴明", "石橋貴明", 1961, "日本", "お笑い芸人", "とんねるず"),
            ("Noritake Kinashi", "木梨憲武", "木梨憲武", 1962, "日本", "お笑い芸人", "とんねるず"),

            # ダウンタウン（既存データで確認済み、一部スキップ）
            ("Masatoshi Hamada", "浜田雅功", "浜田雅功", 1963, "日本", "お笑い芸人", "ダウンタウン"),

            # ウッチャンナンチャン
            ("Teruyoshi Uchimura", "内村光良", "内村光良", 1964, "日本", "お笑い芸人", "ウッチャンナンチャン"),
            ("Kiyotaka Nanbara", "南原清隆", "南原清隆", 1965, "日本", "お笑い芸人", "ウッチャンナンチャン"),

            # 爆笑問題
            ("Hikari Ota", "太田光", "太田光", 1965, "日本", "お笑い芸人", "爆笑問題"),
            ("Yuji Tanaka", "田中裕二", "田中裕二", 1965, "日本", "お笑い芸人", "爆笑問題"),

            # 千鳥
            ("Daigo", "大悟", "大悟", 1980, "日本", "お笑い芸人", "千鳥"),
            ("Nobu", "ノブ", "ノブ", 1979, "日本", "お笑い芸人", "千鳥"),

            # 霜降り明星
            ("Seiya", "せいや", "せいや", 1992, "日本", "お笑い芸人", "霜降り明星"),
            ("Soshina", "粗品", "粗品", 1993, "日本", "お笑い芸人", "霜降り明星"),

            # かまいたち
            ("Ryuichi Hamaie", "濱家隆一", "濱家隆一", 1983, "日本", "お笑い芸人", "かまいたち"),
            ("Kenji Yamauchi", "山内健司", "山内健司", 1981, "日本", "お笑い芸人", "かまいたち"),

            # オードリー
            ("Toshiaki Kasuga", "春日俊彰", "春日俊彰", 1979, "日本", "お笑い芸人", "オードリー"),
            ("Masayasu Wakabayashi", "若林正恭", "若林正恭", 1978, "日本", "お笑い芸人", "オードリー"),

            # 中川家
            ("Tsuyoshi Nakagawa", "中川剛", "剛", 1970, "日本", "お笑い芸人", "中川家"),
            ("Reiji Nakagawa", "中川礼二", "礼二", 1972, "日本", "お笑い芸人", "中川家"),

            # NON STYLE
            ("Akira Ishida", "石田明", "石田明", 1980, "日本", "お笑い芸人", "NON STYLE"),
            ("Yuki Inoue", "井上裕介", "井上裕介", 1980, "日本", "お笑い芸人", "NON STYLE"),

            # ブラックマヨネーズ
            ("Ryuji Yoshida", "吉田敬", "吉田敬", 1973, "日本", "お笑い芸人", "ブラックマヨネーズ"),
            ("Takashi Koboke", "小杉竜一", "小杉竜一", 1973, "日本", "お笑い芸人", "ブラックマヨネーズ"),

            # 麒麟
            ("Hiroshi Tamura", "田村裕", "田村裕", 1979, "日本", "お笑い芸人", "麒麟"),
            ("Akira Kawashima", "川島明", "川島明", 1979, "日本", "お笑い芸人", "麒麟"),

            # ミルクボーイ
            ("Takashi Komaba", "駒場孝", "駒場孝", 1986, "日本", "お笑い芸人", "ミルクボーイ"),
            ("Keigo Utsumi", "内海崇", "内海崇", 1985, "日本", "お笑い芸人", "ミルクボーイ"),
        ]

        for comedian_data in comedians:
            person_name, person_name_ja, display, birth_year, nationality, occupation, group_name = comedian_data
            self.add_person(
                person_name=person_name,
                person_name_ja=person_name_ja,
                person_name_display=display,
                birth_year=birth_year,
                nationality=nationality,
                occupation=occupation,
                category="現代のイノベーター",
                group_name=group_name
            )
            self.stats['phase2_comedy'] += 1

        print(f"  ✓ Phase 2完了: {self.stats['phase2_comedy']}件収集")

    def phase3_idol_music_groups(self):
        """Phase 3: アイドル・音楽グループメンバー収集"""
        print("\n🎵 Phase 3: アイドル・音楽グループメンバー収集開始...")

        idols = [
            # 嵐
            ("Satoshi Ohno", "大野智", "大野智", 1980, "日本", "アイドル", "嵐"),
            ("Sho Sakurai", "櫻井翔", "櫻井翔", 1982, "日本", "アイドル", "嵐"),
            ("Masaki Aiba", "相葉雅紀", "相葉雅紀", 1982, "日本", "アイドル", "嵐"),
            ("Kazunari Ninomiya", "二宮和也", "二宮和也", 1983, "日本", "アイドル", "嵐"),
            ("Jun Matsumoto", "松本潤", "松本潤", 1983, "日本", "アイドル", "嵐"),

            # King & Prince
            ("Sho Hirano", "平野紫耀", "平野紫耀", 1997, "日本", "アイドル", "King & Prince"),
            ("Ren Nagase", "永瀬廉", "永瀬廉", 1999, "日本", "アイドル", "King & Prince"),
            ("Kaito Takahashi", "高橋海人", "高橋海人", 1999, "日本", "アイドル", "King & Prince"),

            # Snow Man
            ("Hikaru Iwamoto", "岩本照", "岩本照", 1993, "日本", "アイドル", "Snow Man"),
            ("Tatsuya Fukasawa", "深澤辰哉", "深澤辰哉", 1992, "日本", "アイドル", "Snow Man"),
            ("Ryota Miyadate", "宮舘涼太", "宮舘涼太", 1993, "日本", "アイドル", "Snow Man"),
            ("Ryohei Abe", "阿部亮平", "阿部亮平", 1993, "日本", "アイドル", "Snow Man"),
            ("Koji Mukai", "向井康二", "向井康二", 1994, "日本", "アイドル", "Snow Man"),
            ("Daisuke Sakuma", "佐久間大介", "佐久間大介", 1992, "日本", "アイドル", "Snow Man"),
            ("Shota Watanabe", "渡辺翔太", "渡辺翔太", 1992, "日本", "アイドル", "Snow Man"),
            ("Ren Meguro", "目黒蓮", "目黒蓮", 1997, "日本", "アイドル", "Snow Man"),
            ("Raul", "ラウール", "ラウール", 2003, "日本", "アイドル", "Snow Man"),

            # AKB48（歴代センター）
            ("Atsuko Maeda", "前田敦子", "前田敦子", 1991, "日本", "元アイドル", "元AKB48"),
            ("Yuko Oshima", "大島優子", "大島優子", 1988, "日本", "元アイドル", "元AKB48"),
            ("Mariko Shinoda", "篠田麻里子", "篠田麻里子", 1986, "日本", "元アイドル", "元AKB48"),
            ("Minami Takahashi", "高橋みなみ", "高橋みなみ", 1991, "日本", "元アイドル", "元AKB48"),
            ("Haruna Kojima", "小嶋陽菜", "小嶋陽菜", 1988, "日本", "元アイドル", "元AKB48"),
            ("Rino Sashihara", "指原莉乃", "指原莉乃", 1992, "日本", "元アイドル", "元HKT48"),
            ("Jurina Matsui", "松井珠理奈", "松井珠理奈", 1997, "日本", "元アイドル", "元SKE48"),
            ("Sakura Miyawaki", "宮脇咲良", "宮脇咲良", 1998, "日本", "アイドル", "LE SSERAFIM"),

            # 乃木坂46
            ("Mai Shiraishi", "白石麻衣", "白石麻衣", 1992, "日本", "元アイドル", "元乃木坂46"),
            ("Nanase Nishino", "西野七瀬", "西野七瀬", 1994, "日本", "元アイドル", "元乃木坂46"),
            ("Asuka Saito", "齋藤飛鳥", "齋藤飛鳥", 1998, "日本", "元アイドル", "元乃木坂46"),
            ("Erika Ikuta", "生田絵梨花", "生田絵梨花", 1997, "日本", "元アイドル", "元乃木坂46"),
            ("Minami Hoshino", "星野みなみ", "星野みなみ", 1998, "日本", "元アイドル", "元乃木坂46"),

            # 日向坂46
            ("Nao Kosaka", "小坂菜緒", "小坂菜緒", 2002, "日本", "アイドル", "日向坂46"),
            ("Kyoko Saito", "齊藤京子", "齊藤京子", 1997, "日本", "アイドル", "日向坂46"),

            # TWICE（日本人メンバー）
            ("Momo Hirai", "平井もも", "モモ", 1996, "日本", "アイドル", "TWICE"),
            ("Sana Minatozaki", "湊崎紗夏", "サナ", 1996, "日本", "アイドル", "TWICE"),
            ("Mina Myoui", "名井南", "ミナ", 1997, "日本", "アイドル", "TWICE"),

            # NiziU
            ("Mako", "山口真子", "マコ", 2001, "日本", "アイドル", "NiziU"),
            ("Rio", "花橋梨緒", "リオ", 2002, "日本", "アイドル", "NiziU"),
            ("Maya", "勝村摩耶", "マヤ", 2002, "日本", "アイドル", "NiziU"),
            ("Riku", "大江梨久", "リク", 2002, "日本", "アイドル", "NiziU"),

            # EXILE
            ("Hiro", "五十嵐広行", "HIRO", 1969, "日本", "ダンサー", "EXILE"),
            ("Atsushi", "佐藤篤志", "ATSUSHI", 1980, "日本", "歌手", "EXILE"),
            ("Takahiro", "田﨑敬浩", "TAKAHIRO", 1984, "日本", "歌手", "EXILE"),
            ("Akira", "黒澤良平", "AKIRA", 1981, "日本", "ダンサー", "EXILE"),

            # 三代目 J SOUL BROTHERS
            ("Ryuji Imaichi", "今市隆二", "今市隆二", 1986, "日本", "歌手", "三代目 J SOUL BROTHERS"),
            ("Hiroomi Tosaka", "登坂広臣", "登坂広臣", 1987, "日本", "歌手", "三代目 J SOUL BROTHERS"),
            ("Naoto", "片寄涼太", "NAOTO", 1983, "日本", "ダンサー", "三代目 J SOUL BROTHERS"),

            # Mr.Children
            ("Kazutoshi Sakurai", "桜井和寿", "桜井和寿", 1970, "日本", "ミュージシャン", "Mr.Children"),
            ("Kenichi Tahara", "田原健一", "田原健一", 1969, "日本", "ミュージシャン", "Mr.Children"),
            ("Hideya Suzuki", "鈴木英哉", "鈴木英哉", 1969, "日本", "ミュージシャン", "Mr.Children"),
            ("Masashi Nakagawa", "中川雅史", "中川雅史", 1969, "日本", "ミュージシャン", "Mr.Children"),
        ]

        for idol_data in idols:
            person_name, person_name_ja, display, birth_year, nationality, occupation, group_name = idol_data
            self.add_person(
                person_name=person_name,
                person_name_ja=person_name_ja,
                person_name_display=display,
                birth_year=birth_year,
                nationality=nationality,
                occupation=occupation,
                category="現代のイノベーター",
                group_name=group_name
            )
            self.stats['phase3_idol'] += 1

        print(f"  ✓ Phase 3完了: {self.stats['phase3_idol']}件収集")

    def collect_all(self):
        """全フェーズのデータを収集"""
        print("=" * 60)
        print("🚀 Ultra Think Mass Collection 開始")
        print("=" * 60)

        # Phase 1: アニメ・漫画キャラクター
        self.phase1_anime_manga_characters()

        # Phase 2: お笑い芸人グループ
        self.phase2_comedy_groups()

        # Phase 3: アイドル・音楽グループ
        self.phase3_idol_music_groups()

        # TODO: 追加フェーズ
        # self.phase4_actors_actresses()
        # self.phase5_sports_athletes()
        # self.phase6_foreign_celebrities()
        # self.phase7_youtubers_tiktokers()
        # self.phase8_others()

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
        report = f"""# Ultra Think Mass Collection Report

## 実行日時
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 収集結果

### フェーズ別収集数
- Phase 1 (アニメ・漫画): {self.stats['phase1_anime']}件
- Phase 2 (お笑い芸人): {self.stats['phase2_comedy']}件
- Phase 3 (アイドル・音楽): {self.stats['phase3_idol']}件
- Phase 4 (俳優・女優): {self.stats['phase4_actor']}件
- Phase 5 (スポーツ): {self.stats['phase5_sports']}件
- Phase 6 (海外有名人): {self.stats['phase6_foreign']}件
- Phase 7 (YouTuber): {self.stats['phase7_youtuber']}件
- Phase 8 (その他): {self.stats['phase8_others']}件

### 統計
- 新規収集: {self.stats['total_collected']}件
- 重複スキップ: {self.stats['duplicates_skipped']}件
- 既存データ: {len(self.existing_data)}件
- 最終総数: {len(self.existing_data) + self.stats['total_collected']}件

### 出力ファイル
- CSV: {self.output_csv}
- JSON: {self.output_json}
"""

        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📝 レポート生成: {self.report_file}")


def main():
    collector = UltraThinkMassCollector()
    collector.collect_all()
    collector.save_data()
    collector.generate_report()


if __name__ == "__main__":
    main()
