#!/usr/bin/env python3
"""
Ultra Think Safe Collector Extended
Phase 2-5の実装（エンタメ、スポーツ、国際、特殊カテゴリ）
エラー防止型段階的収集システム
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional
import os
import time


class SafeCollectorExtended:
    """拡張版エラー防止型収集システム"""

    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Phase 1の結果を基に続行
        self.base_file = "ultra_think_safe_20250825_171135.csv"
        self.checkpoint_dir = "checkpoints"
        self.output_csv = f"ultra_think_extended_{self.timestamp}.csv"
        self.output_json = f"ultra_think_extended_{self.timestamp}.json"
        self.report_file = f"EXTENDED_COLLECTION_REPORT_{self.timestamp}.md"

        # 統計情報
        self.stats = {
            'initial_count': 0,
            'added_count': 0,
            'duplicate_count': 0,
            'error_count': 0,
            'fixed_count': 0,
            'validation_passes': 0,
            'validation_failures': 0,
            'phase_results': {}
        }

        # 既存データ
        self.existing_data = []
        self.existing_names = set()
        self.existing_display = set()

        # 収集データ
        self.new_data = []

        # バッチサイズ
        self.batch_size = 100

        # チェックポイントディレクトリ作成
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def load_existing_data(self) -> bool:
        """既存データを読み込み"""
        try:
            print(f"📂 既存データ読み込み中: {self.base_file}")

            with open(self.base_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.existing_data = list(reader)

            self.stats['initial_count'] = len(self.existing_data)

            # 重複チェック用セット作成
            for record in self.existing_data:
                person_name = record.get('person_name', '').strip()
                person_name_display = record.get('person_name_display', '').strip()

                if person_name:
                    self.existing_names.add(person_name.lower())
                if person_name_display:
                    self.existing_display.add(person_name_display)

            print(f"✅ {len(self.existing_data)}件の既存データ読み込み完了")
            print(f"   - 既存person_name: {len(self.existing_names)}件")
            print(f"   - 既存person_name_display: {len(self.existing_display)}件")

            return True

        except Exception as e:
            print(f"❌ データ読み込みエラー: {e}")
            return False

    def validate_record(self, record: Dict) -> Tuple[bool, List[str]]:
        """レコードの検証"""
        errors = []

        # 必須フィールドチェック
        if not record.get('person_name', '').strip():
            errors.append("person_name is empty")

        if not record.get('person_name_display', '').strip():
            errors.append("person_name_display is empty")

        # birth_year検証（存在する場合）
        birth_year = record.get('birth_year', '')
        if birth_year:
            try:
                year = int(birth_year)
                if year < -3000 or year > 2025:
                    errors.append(f"Invalid birth_year: {year}")
            except:
                errors.append(f"birth_year is not a number: {birth_year}")

        # 重複チェック
        person_name = record.get('person_name', '').strip()
        person_name_display = record.get('person_name_display', '').strip()

        if person_name.lower() in self.existing_names:
            errors.append(f"Duplicate person_name: {person_name}")

        if person_name_display in self.existing_display:
            errors.append(f"Duplicate person_name_display: {person_name_display}")

        # パターンチェック（問題のあるパターン）
        if re.match(r'^.+_\d{3,4}$', person_name_display):
            errors.append(f"Invalid pattern (occupation_number): {person_name_display}")

        if '_Person_' in person_name:
            errors.append(f"Invalid pattern (_Person_): {person_name}")

        return len(errors) == 0, errors

    def validate_batch(self, batch: List[Dict]) -> Tuple[bool, Dict]:
        """バッチ単位の検証"""
        print(f"\n🔍 バッチ検証中（{len(batch)}件）...")

        validation_result = {
            'total': len(batch),
            'passed': 0,
            'failed': 0,
            'errors': []
        }

        for i, record in enumerate(batch):
            is_valid, errors = self.validate_record(record)

            if is_valid:
                validation_result['passed'] += 1
            else:
                validation_result['failed'] += 1
                validation_result['errors'].append({
                    'index': i,
                    'person_name': record.get('person_name', ''),
                    'errors': errors
                })

        # 結果表示
        print(f"   ✅ 合格: {validation_result['passed']}件")
        print(f"   ❌ 不合格: {validation_result['failed']}件")

        if validation_result['failed'] > 0:
            print(f"   ⚠️ エラー詳細:")
            for error_info in validation_result['errors'][:5]:  # 最初の5件表示
                print(f"      - {error_info['person_name']}: {', '.join(error_info['errors'])}")

        return validation_result['failed'] == 0, validation_result

    def fix_batch_errors(self, batch: List[Dict], validation_result: Dict) -> List[Dict]:
        """バッチのエラーを修正"""
        print(f"\n🔧 エラー修正中...")

        fixed_batch = []
        fixed_count = 0

        for i, record in enumerate(batch):
            # エラーがあるレコードを探す
            error_info = None
            for err in validation_result['errors']:
                if err['index'] == i:
                    error_info = err
                    break

            if error_info:
                # 重複エラーはスキップ（修正不可）
                has_duplicate = any('Duplicate' in e for e in error_info['errors'])
                if has_duplicate:
                    self.stats['duplicate_count'] += 1
                    self.stats['error_count'] += 1
                    continue

                # その他のエラーも基本的にスキップ
                self.stats['error_count'] += 1
            else:
                # エラーなしのレコード
                fixed_batch.append(record)

        print(f"   ✅ {len(fixed_batch)}件処理完了")
        print(f"   ⚠️ {len(batch) - len(fixed_batch)}件スキップ")

        return fixed_batch

    def save_checkpoint(self, phase_name: str, data: List[Dict]):
        """チェックポイント保存"""
        checkpoint_file = os.path.join(
            self.checkpoint_dir,
            f"checkpoint_{phase_name}_{self.timestamp}.json"
        )

        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 チェックポイント保存: {checkpoint_file}")

    def create_person_record(self,
                           person_name: str,
                           person_name_ja: str,
                           person_name_display: str,
                           birth_year: Optional[int] = None,
                           occupation: str = "",
                           nationality: str = "日本",
                           category: str = "",
                           subcategory: str = "",
                           group_name: str = "",
                           is_fictional: bool = False,
                           is_animal: bool = False,
                           phase: str = "SafeCollection") -> Dict:
        """人物レコード作成"""

        # グループメンバーの場合の表示名調整
        if group_name:
            person_name_display = f"{person_name_ja}（{group_name}）"

        record = {
            'batch_id': f'safe_{phase.lower()}',
            'birth_year': str(birth_year) if birth_year else '',
            'category': category,
            'cultural_significance': '',
            'description': '',
            'educational_value': '',
            'era': '',
            'followers': '',
            'global_recognition': '',
            'grade': 'A',
            'historical_impact': '',
            'is_animal': 'true' if is_animal else '',
            'is_fictional': 'true' if is_fictional else '',
            'main_category': category,
            'name': person_name,
            'nationality': nationality,
            'occupation': occupation,
            'person_name': person_name,
            'person_name_display': person_name_display,
            'person_name_ja': person_name_ja,
            'phase': phase,
            'platform': '',
            'subcategory': subcategory
        }

        return record

    def collect_phase2_kpop_bands(self) -> List[Dict]:
        """Phase 2-1: K-POP・日本のバンド（800件）"""
        print("\n🎵 Phase 2-1: K-POP・バンド収集中...")

        data = []

        # K-POPグループ（メンバー個別）
        kpop_groups = [
            # Stray Kids
            ("Bang Chan", "バンチャン", "バンチャン", 1997, "歌手", "Stray Kids", "オーストラリア"),
            ("Lee Know", "リノ", "リノ", 1998, "歌手", "Stray Kids", "韓国"),
            ("Changbin", "チャンビン", "チャンビン", 1999, "歌手", "Stray Kids", "韓国"),
            ("Hyunjin", "ヒョンジン", "ヒョンジン", 2000, "歌手", "Stray Kids", "韓国"),
            ("Han", "ハン", "ハン", 2000, "歌手", "Stray Kids", "韓国"),
            ("Felix", "フィリックス", "フィリックス", 2000, "歌手", "Stray Kids", "オーストラリア"),
            ("Seungmin", "スンミン", "スンミン", 2000, "歌手", "Stray Kids", "韓国"),
            ("I.N", "アイエン", "アイエン", 2001, "歌手", "Stray Kids", "韓国"),

            # SEVENTEEN
            ("S.Coups", "エスクプス", "エスクプス", 1995, "歌手", "SEVENTEEN", "韓国"),
            ("Jeonghan", "ジョンハン", "ジョンハン", 1995, "歌手", "SEVENTEEN", "韓国"),
            ("Joshua", "ジョシュア", "ジョシュア", 1995, "歌手", "SEVENTEEN", "アメリカ"),
            ("Jun", "ジュン", "ジュン", 1996, "歌手", "SEVENTEEN", "中国"),
            ("Hoshi", "ホシ", "ホシ", 1996, "歌手", "SEVENTEEN", "韓国"),
            ("Wonwoo", "ウォヌ", "ウォヌ", 1996, "歌手", "SEVENTEEN", "韓国"),
            ("Woozi", "ウジ", "ウジ", 1996, "歌手", "SEVENTEEN", "韓国"),
            ("DK", "ドギョム", "ドギョム", 1997, "歌手", "SEVENTEEN", "韓国"),
            ("Mingyu", "ミンギュ", "ミンギュ", 1997, "歌手", "SEVENTEEN", "韓国"),
            ("The8", "ディエイト", "ディエイト", 1997, "歌手", "SEVENTEEN", "中国"),
            ("Seungkwan", "スングァン", "スングァン", 1998, "歌手", "SEVENTEEN", "韓国"),
            ("Vernon", "バーノン", "バーノン", 1998, "歌手", "SEVENTEEN", "アメリカ"),
            ("Dino", "ディノ", "ディノ", 1999, "歌手", "SEVENTEEN", "韓国"),

            # TWICE
            ("Nayeon", "ナヨン", "ナヨン", 1995, "歌手", "TWICE", "韓国"),
            ("Jeongyeon", "ジョンヨン", "ジョンヨン", 1996, "歌手", "TWICE", "韓国"),
            ("Momo", "モモ", "モモ", 1996, "歌手", "TWICE", "日本"),
            ("Sana", "サナ", "サナ", 1996, "歌手", "TWICE", "日本"),
            ("Jihyo", "ジヒョ", "ジヒョ", 1997, "歌手", "TWICE", "韓国"),
            ("Mina", "ミナ", "ミナ", 1997, "歌手", "TWICE", "日本"),
            ("Dahyun", "ダヒョン", "ダヒョン", 1998, "歌手", "TWICE", "韓国"),
            ("Chaeyoung", "チェヨン", "チェヨン", 1999, "歌手", "TWICE", "韓国"),
            ("Tzuyu", "ツウィ", "ツウィ", 1999, "歌手", "TWICE", "台湾"),

            # ENHYPEN
            ("Heeseung", "ヒスン", "ヒスン", 2001, "歌手", "ENHYPEN", "韓国"),
            ("Jay", "ジェイ", "ジェイ", 2002, "歌手", "ENHYPEN", "アメリカ"),
            ("Jake", "ジェイク", "ジェイク", 2002, "歌手", "ENHYPEN", "オーストラリア"),
            ("Sunghoon", "ソンフン", "ソンフン", 2002, "歌手", "ENHYPEN", "韓国"),
            ("Sunoo", "ソヌ", "ソヌ", 2003, "歌手", "ENHYPEN", "韓国"),
            ("Jungwon", "ジョンウォン", "ジョンウォン", 2004, "歌手", "ENHYPEN", "韓国"),
            ("Ni-ki", "ニキ", "ニキ", 2005, "歌手", "ENHYPEN", "日本"),

            # NCT DREAM
            ("Mark", "マーク", "マーク", 1999, "歌手", "NCT DREAM", "カナダ"),
            ("Renjun", "ロンジュン", "ロンジュン", 2000, "歌手", "NCT DREAM", "中国"),
            ("Jeno", "ジェノ", "ジェノ", 2000, "歌手", "NCT DREAM", "韓国"),
            ("Haechan", "ヘチャン", "ヘチャン", 2000, "歌手", "NCT DREAM", "韓国"),
            ("Jaemin", "ジェミン", "ジェミン", 2000, "歌手", "NCT DREAM", "韓国"),
            ("Chenle", "チョンロ", "チョンロ", 2001, "歌手", "NCT DREAM", "中国"),
            ("Jisung", "ジソン", "ジソン", 2002, "歌手", "NCT DREAM", "韓国"),

            # BLACKPINK
            ("Jisoo", "ジス", "ジス", 1995, "歌手", "BLACKPINK", "韓国"),
            ("Jennie", "ジェニー", "ジェニー", 1996, "歌手", "BLACKPINK", "韓国"),
            ("Rose", "ロゼ", "ロゼ", 1997, "歌手", "BLACKPINK", "ニュージーランド"),
            ("Lisa", "リサ", "リサ", 1997, "歌手", "BLACKPINK", "タイ"),

            # ITZY
            ("Yeji", "イェジ", "イェジ", 2000, "歌手", "ITZY", "韓国"),
            ("Lia", "リア", "リア", 2000, "歌手", "ITZY", "韓国"),
            ("Ryujin", "リュジン", "リュジン", 2001, "歌手", "ITZY", "韓国"),
            ("Chaeryeong", "チェリョン", "チェリョン", 2001, "歌手", "ITZY", "韓国"),
            ("Yuna", "ユナ", "ユナ", 2003, "歌手", "ITZY", "韓国"),

            # aespa
            ("Karina", "カリナ", "カリナ", 2000, "歌手", "aespa", "韓国"),
            ("Giselle", "ジゼル", "ジゼル", 2000, "歌手", "aespa", "日本"),
            ("Winter", "ウィンター", "ウィンター", 2001, "歌手", "aespa", "韓国"),
            ("Ningning", "ニンニン", "ニンニン", 2002, "歌手", "aespa", "中国"),

            # TXT
            ("Yeonjun", "ヨンジュン", "ヨンジュン", 1999, "歌手", "TXT", "韓国"),
            ("Soobin", "スビン", "スビン", 2000, "歌手", "TXT", "韓国"),
            ("Beomgyu", "ボムギュ", "ボムギュ", 2001, "歌手", "TXT", "韓国"),
            ("Taehyun", "テヒョン", "テヒョン", 2002, "歌手", "TXT", "韓国"),
            ("Huening Kai", "ヒュニンカイ", "ヒュニンカイ", 2002, "歌手", "TXT", "アメリカ"),

            # ATEEZ
            ("Hongjoong", "ホンジュン", "ホンジュン", 1998, "歌手", "ATEEZ", "韓国"),
            ("Seonghwa", "ソンファ", "ソンファ", 1998, "歌手", "ATEEZ", "韓国"),
            ("Yunho", "ユンホ", "ユンホ", 1999, "歌手", "ATEEZ", "韓国"),
            ("Yeosang", "ヨサン", "ヨサン", 1999, "歌手", "ATEEZ", "韓国"),
            ("San", "サン", "サン", 1999, "歌手", "ATEEZ", "韓国"),
            ("Mingi", "ミンギ", "ミンギ", 1999, "歌手", "ATEEZ", "韓国"),
            ("Wooyoung", "ウヨン", "ウヨン", 1999, "歌手", "ATEEZ", "韓国"),
            ("Jongho", "ジョンホ", "ジョンホ", 2000, "歌手", "ATEEZ", "韓国"),
        ]

        # 日本のバンド
        japanese_bands = [
            # King & Prince
            ("Ren Nagase", "永瀬廉", "永瀬廉", 1999, "歌手", "King & Prince", "日本"),
            ("Kaito Takahashi", "高橋海人", "高橋海人", 1999, "歌手", "King & Prince", "日本"),
            ("Yuta Kishi", "岸優太", "岸優太", 1995, "歌手", "King & Prince", "日本"),
            ("Yuta Jinguji", "神宮寺勇太", "神宮寺勇太", 1997, "歌手", "King & Prince", "日本"),
            ("Sho Hirano", "平野紫耀", "平野紫耀", 1997, "歌手", "King & Prince", "日本"),

            # Snow Man
            ("Koji Mukai", "向井康二", "向井康二", 1994, "歌手", "Snow Man", "日本"),
            ("Tatsuya Fukasawa", "深澤辰哉", "深澤辰哉", 1992, "歌手", "Snow Man", "日本"),
            ("Shota Watanabe", "渡辺翔太", "渡辺翔太", 1992, "歌手", "Snow Man", "日本"),
            ("Ryohei Abe", "阿部亮平", "阿部亮平", 1993, "歌手", "Snow Man", "日本"),
            ("Daisuke Sakuma", "佐久間大介", "佐久間大介", 1992, "歌手", "Snow Man", "日本"),
            ("Ren Meguro", "目黒蓮", "目黒蓮", 1997, "歌手", "Snow Man", "日本"),
            ("Hikaru Iwamoto", "岩本照", "岩本照", 1993, "歌手", "Snow Man", "日本"),
            ("Ryota Miyadate", "宮舘涼太", "宮舘涼太", 1993, "歌手", "Snow Man", "日本"),
            ("Raul", "ラウール", "ラウール", 2003, "歌手", "Snow Man", "日本"),

            # SixTONES
            ("Jesse", "ジェシー", "ジェシー", 1996, "歌手", "SixTONES", "日本"),
            ("Hokuto Matsumura", "松村北斗", "松村北斗", 1995, "歌手", "SixTONES", "日本"),
            ("Taiga Kyomoto", "京本大我", "京本大我", 1994, "歌手", "SixTONES", "日本"),
            ("Yugo Kochi", "髙地優吾", "髙地優吾", 1994, "歌手", "SixTONES", "日本"),
            ("Juri Tanaka", "田中樹", "田中樹", 1995, "歌手", "SixTONES", "日本"),
            ("Shintaro Morimoto", "森本慎太郎", "森本慎太郎", 1997, "歌手", "SixTONES", "日本"),

            # なにわ男子
            ("Shunsuke Michieda", "道枝駿佑", "道枝駿佑", 2002, "歌手", "なにわ男子", "日本"),
            ("Kyohei Takahashi", "高橋恭平", "高橋恭平", 2000, "歌手", "なにわ男子", "日本"),
            ("Ryusei Onishi", "大西流星", "大西流星", 2001, "歌手", "なにわ男子", "日本"),
            ("Daigo Nishihata", "西畑大吾", "西畑大吾", 1997, "歌手", "なにわ男子", "日本"),
            ("Kento Nagao", "長尾謙杜", "長尾謙杜", 2002, "歌手", "なにわ男子", "日本"),
            ("Joichiro Fujiwara", "藤原丈一郎", "藤原丈一郎", 1996, "歌手", "なにわ男子", "日本"),
            ("Ryuta Ohashi", "大橋和也", "大橋和也", 1997, "歌手", "なにわ男子", "日本"),

            # YOASOBI
            ("Ayase", "Ayase", "Ayase", 1994, "音楽プロデューサー", "YOASOBI", "日本"),
            ("Ikura", "ikura", "ikura", 2000, "歌手", "YOASOBI", "日本"),

            # Official髭男dism
            ("Satoshi Fujihara", "藤原聡", "藤原聡", 1991, "歌手", "Official髭男dism", "日本"),
            ("Daisuke Ozasa", "小笹大輔", "小笹大輔", 1994, "ギタリスト", "Official髭男dism", "日本"),
            ("Makoto Narazaki", "楢崎誠", "楢崎誠", 1989, "ベーシスト", "Official髭男dism", "日本"),
            ("Tomohiro Matsuurura", "松浦匡希", "松浦匡希", 1993, "ドラマー", "Official髭男dism", "日本"),

            # Mrs. GREEN APPLE
            ("Motoki Omori", "大森元貴", "大森元貴", 1996, "歌手", "Mrs. GREEN APPLE", "日本"),
            ("Hiroto Wakai", "若井滉斗", "若井滉斗", 1996, "ギタリスト", "Mrs. GREEN APPLE", "日本"),
            ("Ryoka Fujisawa", "藤澤涼架", "藤澤涼架", 1993, "キーボーディスト", "Mrs. GREEN APPLE", "日本"),

            # King Gnu
            ("Daiki Tsuneta", "常田大希", "常田大希", 1992, "歌手", "King Gnu", "日本"),
            ("Satoru Iguchi", "井口理", "井口理", 1993, "歌手", "King Gnu", "日本"),
            ("Yu Seki", "関口祐", "関口祐", 1992, "ベーシスト", "King Gnu", "日本"),
            ("Kazuki Arai", "新井和輝", "新井和輝", 1992, "ベーシスト", "King Gnu", "日本"),

            # back number
            ("Iyori Shimizu", "清水依与吏", "清水依与吏", 1984, "歌手", "back number", "日本"),
            ("Kazuya Kojima", "小島和也", "小島和也", 1984, "ベーシスト", "back number", "日本"),
            ("Hisashi Kurihara", "栗原寿", "栗原寿", 1985, "ドラマー", "back number", "日本"),

            # ONE OK ROCK
            ("Takahiro Moriuchi", "森内貴寛", "Taka", 1988, "歌手", "ONE OK ROCK", "日本"),
            ("Toru Yamashita", "山下亨", "Toru", 1988, "ギタリスト", "ONE OK ROCK", "日本"),
            ("Ryota Kohama", "小浜良太", "Ryota", 1989, "ベーシスト", "ONE OK ROCK", "日本"),
            ("Tomoya Kanki", "神吉智也", "Tomoya", 1987, "ドラマー", "ONE OK ROCK", "日本"),

            # RADWIMPS
            ("Yojiro Noda", "野田洋次郎", "野田洋次郎", 1985, "歌手", "RADWIMPS", "日本"),
            ("Akira Kuwahara", "桑原彰", "桑原彰", 1985, "ギタリスト", "RADWIMPS", "日本"),
            ("Yusuke Takeda", "武田祐介", "武田祐介", 1985, "ベーシスト", "RADWIMPS", "日本"),
            ("Satoshi Yamaguchi", "山口智史", "山口智史", 1985, "ドラマー", "RADWIMPS", "日本"),

            # BUMP OF CHICKEN
            ("Motoo Fujiwara", "藤原基央", "藤原基央", 1979, "歌手", "BUMP OF CHICKEN", "日本"),
            ("Hiroaki Masukawa", "増川弘明", "増川弘明", 1979, "ギタリスト", "BUMP OF CHICKEN", "日本"),
            ("Yoshifumi Naoi", "直井由文", "直井由文", 1979, "ベーシスト", "BUMP OF CHICKEN", "日本"),
            ("Hideo Masu", "升秀夫", "升秀夫", 1979, "ドラマー", "BUMP OF CHICKEN", "日本"),
        ]

        # データ作成
        for person in kpop_groups + japanese_bands:
            if len(person) >= 6:
                name, display, ja, year, occ, group = person[:6]
                nationality = person[6] if len(person) > 6 else "日本"

                record = self.create_person_record(
                    person_name=name,
                    person_name_ja=ja,
                    person_name_display=display,
                    birth_year=year,
                    occupation=occ,
                    nationality=nationality,
                    category="エンタメ",
                    subcategory="音楽",
                    group_name=group,
                    phase="Phase2-1"
                )
                data.append(record)

        return data

    def collect_phase2_voice_actors_youtubers(self) -> List[Dict]:
        """Phase 2-2: 声優・YouTuber（1,200件）"""
        print("\n🎙️ Phase 2-2: 声優・YouTuber収集中...")

        data = []

        # 人気声優（男性）
        male_voice_actors = [
            ("Yuki Kaji", "梶裕貴", "梶裕貴", 1985, "声優"),
            ("Yoshitsugu Matsuoka", "松岡禎丞", "松岡禎丞", 1986, "声優"),
            ("Nobuhiko Okamoto", "岡本信彦", "岡本信彦", 1986, "声優"),
            ("Daisuke Ono", "小野大輔", "小野大輔", 1978, "声優"),
            ("Takahiro Sakurai", "櫻井孝宏", "櫻井孝宏", 1974, "声優"),
            ("Jun Fukuyama", "福山潤", "福山潤", 1978, "声優"),
            ("Hiroshi Kamiya", "神谷浩史", "神谷浩史", 1975, "声優"),
            ("Tomokazu Sugita", "杉田智和", "杉田智和", 1980, "声優"),
            ("Yuichi Nakamura", "中村悠一", "中村悠一", 1980, "声優"),
            ("Tatsuhisa Suzuki", "鈴木達央", "鈴木達央", 1983, "声優"),
            ("Kenichi Suzumura", "鈴村健一", "鈴村健一", 1974, "声優"),
            ("Shinichiro Miki", "三木眞一郎", "三木眞一郎", 1968, "声優"),
            ("Akira Ishida", "石田彰", "石田彰", 1967, "声優"),
            ("Koichi Yamadera", "山寺宏一", "山寺宏一", 1961, "声優"),
            ("Noriaki Sugiyama", "杉山紀彰", "杉山紀彰", 1974, "声優"),
            ("Showtaro Morikubo", "森久保祥太郎", "森久保祥太郎", 1974, "声優"),
            ("Toshiyuki Morikawa", "森川智之", "森川智之", 1967, "声優"),
            ("Ryohei Kimura", "木村良平", "木村良平", 1984, "声優"),
            ("Kensho Ono", "小野賢章", "小野賢章", 1989, "声優"),
            ("Soma Saito", "斉藤壮馬", "斉藤壮馬", 1991, "声優"),
            ("Yuma Uchida", "内田雄馬", "内田雄馬", 1992, "声優"),
            ("Kaito Ishikawa", "石川界人", "石川界人", 1993, "声優"),
            ("Shunsuke Takeuchi", "武内駿輔", "武内駿輔", 1997, "声優"),
            ("Gakuto Kajiwara", "梶原岳人", "梶原岳人", 1994, "声優"),
            ("Shun Horie", "堀江瞬", "堀江瞬", 1993, "声優"),
        ]

        # 人気声優（女性）
        female_voice_actors = [
            ("Kana Hanazawa", "花澤香菜", "花澤香菜", 1989, "声優"),
            ("Aoi Yuki", "悠木碧", "悠木碧", 1992, "声優"),
            ("Inori Minase", "水瀬いのり", "水瀬いのり", 1995, "声優"),
            ("Saori Hayami", "早見沙織", "早見沙織", 1991, "声優"),
            ("Ayane Sakura", "佐倉綾音", "佐倉綾音", 1994, "声優"),
            ("Nao Toyama", "東山奈央", "東山奈央", 1992, "声優"),
            ("Rie Takahashi", "高橋李依", "高橋李依", 1994, "声優"),
            ("Ai Kayano", "茅野愛衣", "茅野愛衣", 1987, "声優"),
            ("Maaya Uchida", "内田真礼", "内田真礼", 1989, "声優"),
            ("Yoshino Nanjo", "南條愛乃", "南條愛乃", 1984, "声優"),
            ("Ayana Taketatsu", "竹達彩奈", "竹達彩奈", 1989, "声優"),
            ("Yui Horie", "堀江由衣", "堀江由衣", 1976, "声優"),
            ("Yukari Tamura", "田村ゆかり", "田村ゆかり", 1976, "声優"),
            ("Nana Mizuki", "水樹奈々", "水樹奈々", 1980, "声優"),
            ("Miyuki Sawashiro", "沢城みゆき", "沢城みゆき", 1985, "声優"),
            ("Rie Kugimiya", "釘宮理恵", "釘宮理恵", 1979, "声優"),
            ("Marina Inoue", "井上麻里奈", "井上麻里奈", 1985, "声優"),
            ("Yoko Hikasa", "日笠陽子", "日笠陽子", 1985, "声優"),
            ("Sumire Uesaka", "上坂すみれ", "上坂すみれ", 1991, "声優"),
            ("Akari Kito", "鬼頭明里", "鬼頭明里", 1994, "声優"),
            ("Miku Ito", "伊藤美来", "伊藤美来", 1996, "声優"),
            ("Yui Ogura", "小倉唯", "小倉唯", 1995, "声優"),
            ("Kaori Ishihara", "石原夏織", "石原夏織", 1993, "声優"),
            ("Sora Amamiya", "雨宮天", "雨宮天", 1993, "声優"),
            ("Reina Ueda", "上田麗奈", "上田麗奈", 1994, "声優"),
        ]

        # YouTuber（日本）
        youtubers = [
            ("Hikakin", "ヒカキン", "ヒカキン", 1989, "YouTuber"),
            ("Hajime Syacho", "はじめしゃちょー", "はじめしゃちょー", 1993, "YouTuber"),
            ("Fischer's", "フィッシャーズ", "フィッシャーズ", 1994, "YouTuber"),
            ("Tokai On Air", "東海オンエア", "東海オンエア", 1993, "YouTuber"),
            ("Seikin", "セイキン", "セイキン", 1987, "YouTuber"),
            ("Kimagure Cook", "きまぐれクック", "きまぐれクック", 1991, "YouTuber"),
            ("Yuka Kinoshita", "木下ゆうか", "木下ゆうか", 1985, "YouTuber"),
            ("Mizutamari Bond", "水溜りボンド", "水溜りボンド", 1993, "YouTuber"),
            ("Kiwami Japan", "圧倒的不審者の極み", "圧倒的不審者の極み", 1992, "YouTuber"),
            ("QuizKnock", "QuizKnock", "QuizKnock", 1994, "YouTuber"),
            ("Kokoro Kusano", "草野心平", "草野心平", 1988, "YouTuber"),
            ("Fuwa-chan", "フワちゃん", "フワちゃん", 1993, "YouTuber"),
            ("Eguchinn", "江口拓也", "エガちゃん", 1990, "YouTuber"),
            ("Kemio", "けみお", "けみお", 1995, "YouTuber"),
            ("Yusuke", "ゆうすけ", "コムドット・ゆうすけ", 1998, "YouTuber"),
            ("Yukio", "佐藤優樹", "スカイピース", 1995, "YouTuber"),
            ("Teo", "テオ", "スカイピース", 1995, "YouTuber"),
            ("Nakamachi JP", "中町JP", "中町JP", 1997, "YouTuber"),
            ("Poki", "ポッキー", "ポッキー", 1995, "YouTuber"),
            ("Raphael", "ラファエル", "ラファエル", 1989, "YouTuber"),
            ("Hikakin Games", "ヒカキンゲームズ", "ヒカキンゲームズ", 1989, "YouTuber"),
            ("Retoruto", "レトルト", "レトルト", 1990, "YouTuber"),
            ("Kiyo", "キヨ", "キヨ", 1993, "YouTuber"),
            ("Ushizawa", "牛沢", "牛沢", 1990, "YouTuber"),
            ("Gatchman", "ガッチマン", "ガッチマン", 1988, "YouTuber"),
        ]

        # VTuber
        vtubers = [
            ("Kizuna AI", "キズナアイ", "キズナアイ", 2016, "VTuber"),
            ("Gawr Gura", "がうる・ぐら", "がうる・ぐら", 2020, "VTuber"),
            ("Minato Aqua", "湊あくあ", "湊あくあ", 2018, "VTuber"),
            ("Usada Pekora", "兎田ぺこら", "兎田ぺこら", 2019, "VTuber"),
            ("Hoshimachi Suisei", "星街すいせい", "星街すいせい", 2018, "VTuber"),
            ("Sakura Miko", "さくらみこ", "さくらみこ", 2018, "VTuber"),
            ("Shirakami Fubuki", "白上フブキ", "白上フブキ", 2018, "VTuber"),
            ("Inugami Korone", "戌神ころね", "戌神ころね", 2019, "VTuber"),
            ("Nekomata Okayu", "猫又おかゆ", "猫又おかゆ", 2019, "VTuber"),
            ("Houshou Marine", "宝鐘マリン", "宝鐘マリン", 2019, "VTuber"),
            ("Shirogane Noel", "白銀ノエル", "白銀ノエル", 2019, "VTuber"),
            ("Kiryu Coco", "桐生ココ", "桐生ココ", 2019, "VTuber"),
            ("Tsunomaki Watame", "角巻わため", "角巻わため", 2019, "VTuber"),
            ("Tokoyami Towa", "常闇トワ", "常闇トワ", 2020, "VTuber"),
            ("Momosuzu Nene", "桃鈴ねね", "桃鈴ねね", 2020, "VTuber"),
            ("Yukihana Lamy", "雪花ラミィ", "雪花ラミィ", 2020, "VTuber"),
            ("Oozora Subaru", "大空スバル", "大空スバル", 2018, "VTuber"),
            ("Murasaki Shion", "紫咲シオン", "紫咲シオン", 2018, "VTuber"),
            ("Nakiri Ayame", "百鬼あやめ", "百鬼あやめ", 2018, "VTuber"),
            ("Yuzuki Choco", "癒月ちょこ", "癒月ちょこ", 2018, "VTuber"),
            ("Tsukino Mito", "月ノ美兎", "月ノ美兎", 2018, "VTuber"),
            ("Honma Himawari", "本間ひまわり", "本間ひまわり", 2018, "VTuber"),
            ("Sasaki Saku", "笹木咲", "笹木咲", 2018, "VTuber"),
            ("Shiina Yuika", "椎名唯華", "椎名唯華", 2018, "VTuber"),
            ("Ange Katrina", "アンジュ・カトリーナ", "アンジュ・カトリーナ", 2019, "VTuber"),
        ]

        # データ作成
        for person in male_voice_actors + female_voice_actors + youtubers + vtubers:
            if len(person) == 5:
                name, display, ja, year, occ = person
                record = self.create_person_record(
                    person_name=name,
                    person_name_ja=ja,
                    person_name_display=display,
                    birth_year=year,
                    occupation=occ,
                    category="エンタメ",
                    subcategory="声優・配信" if occ in ["声優", "VTuber"] else "YouTube",
                    phase="Phase2-2"
                )
                data.append(record)

        return data

    def collect_phase3_sports(self) -> List[Dict]:
        """Phase 3: スポーツ選手（2,000件）"""
        print("\n⚾ Phase 3: スポーツ選手収集中...")

        data = []

        # プロ野球選手（現役主要選手）
        baseball_players = [
            # 読売ジャイアンツ
            ("Hayato Sakamoto", "坂本勇人", "坂本勇人", 1988, "野球選手"),
            ("Yoshihiro Maru", "丸佳浩", "丸佳浩", 1989, "野球選手"),
            ("Kazuma Okamoto", "岡本和真", "岡本和真", 1996, "野球選手"),
            ("Tomoyuki Sugano", "菅野智之", "菅野智之", 1989, "野球選手"),

            # 阪神タイガース
            ("Yusuke Oyama", "大山悠輔", "大山悠輔", 1994, "野球選手"),
            ("Teruaki Sato", "佐藤輝明", "佐藤輝明", 1999, "野球選手"),
            ("Koji Chikamoto", "近本光司", "近本光司", 1994, "野球選手"),
            ("Shintaro Fujinami", "藤浪晋太郎", "藤浪晋太郎", 1994, "野球選手"),

            # 中日ドラゴンズ
            ("Yota Kyoda", "京田陽太", "京田陽太", 1994, "野球選手"),
            ("Dayan Viciedo", "ダヤン・ビシエド", "ビシエド", 1989, "野球選手"),
            ("Hiroto Takahashi", "高橋宏斗", "高橋宏斗", 2002, "野球選手"),

            # 横浜DeNAベイスターズ
            ("Toshiro Miyazaki", "宮﨑敏郎", "宮﨑敏郎", 1988, "野球選手"),
            ("Keita Sano", "佐野恵太", "佐野恵太", 1994, "野球選手"),
            ("Neftali Soto", "ネフタリ・ソト", "ソト", 1989, "野球選手"),
            ("Taiga Kamichatani", "上茶谷大河", "上茶谷大河", 1996, "野球選手"),

            # 広島東洋カープ
            ("Ryosuke Kikuchi", "菊池涼介", "菊池涼介", 1990, "野球選手"),
            ("Seiya Suzuki", "鈴木誠也", "鈴木誠也", 1994, "野球選手"),
            ("Ryoma Nishikawa", "西川龍馬", "西川龍馬", 1994, "野球選手"),

            # 東京ヤクルトスワローズ
            ("Tetsuto Yamada", "山田哲人", "山田哲人", 1992, "野球選手"),
            ("Munetaka Murakami", "村上宗隆", "村上宗隆", 2000, "野球選手"),
            ("Norichika Aoki", "青木宣親", "青木宣親", 1982, "野球選手"),

            # 福岡ソフトバンクホークス
            ("Yuki Yanagita", "柳田悠岐", "柳田悠岐", 1988, "野球選手"),
            ("Kenta Imamiya", "今宮健太", "今宮健太", 1991, "野球選手"),
            ("Ukyo Shuto", "周東佑京", "周東佑京", 1996, "野球選手"),
            ("Kodai Senga", "千賀滉大", "千賀滉大", 1993, "野球選手"),

            # 千葉ロッテマリーンズ
            ("Takashi Ogino", "荻野貴司", "荻野貴司", 1985, "野球選手"),
            ("Shogo Nakamura", "中村奨吾", "中村奨吾", 1992, "野球選手"),
            ("Roki Sasaki", "佐々木朗希", "佐々木朗希", 2001, "野球選手"),

            # 埼玉西武ライオンズ
            ("Hotaka Yamakawa", "山川穂高", "山川穂高", 1991, "野球選手"),
            ("Sosuke Genda", "源田壮亮", "源田壮亮", 1993, "野球選手"),
            ("Takeya Nakamura", "中村剛也", "中村剛也", 1983, "野球選手"),

            # 東北楽天ゴールデンイーグルス
            ("Hideto Asamura", "浅村栄斗", "浅村栄斗", 1990, "野球選手"),
            ("Hiroaki Shimauchi", "島内宏明", "島内宏明", 1990, "野球選手"),
            ("Masahiro Tanaka", "田中将大", "田中将大", 1988, "野球選手"),

            # 北海道日本ハムファイターズ
            ("Kotaro Kiyomiya", "清宮幸太郎", "清宮幸太郎", 1999, "野球選手"),
            ("Chusei Mannami", "万波中正", "万波中正", 2000, "野球選手"),
            ("Go Matsumoto", "松本剛", "松本剛", 1993, "野球選手"),

            # オリックス・バファローズ
            ("Masataka Yoshida", "吉田正尚", "吉田正尚", 1993, "野球選手"),
            ("Yutaro Sugimoto", "杉本裕太郎", "杉本裕太郎", 1991, "野球選手"),
            ("Yoshinobu Yamamoto", "山本由伸", "山本由伸", 1998, "野球選手"),
        ]

        # サッカー選手
        soccer_players = [
            # 日本代表主要選手
            ("Takumi Minamino", "南野拓実", "南野拓実", 1995, "サッカー選手"),
            ("Takehiro Tomiyasu", "冨安健洋", "冨安健洋", 1998, "サッカー選手"),
            ("Wataru Endo", "遠藤航", "遠藤航", 1993, "サッカー選手"),
            ("Daichi Kamada", "鎌田大地", "鎌田大地", 1996, "サッカー選手"),
            ("Junya Ito", "伊東純也", "伊東純也", 1993, "サッカー選手"),
            ("Kaoru Mitoma", "三笘薫", "三笘薫", 1997, "サッカー選手"),
            ("Takefusa Kubo", "久保建英", "久保建英", 2001, "サッカー選手"),
            ("Ritsu Doan", "堂安律", "堂安律", 1998, "サッカー選手"),
            ("Yuya Osako", "大迫勇也", "大迫勇也", 1990, "サッカー選手"),
            ("Shogo Taniguchi", "谷口彰悟", "谷口彰悟", 1991, "サッカー選手"),
            ("Ko Itakura", "板倉滉", "板倉滉", 1997, "サッカー選手"),
            ("Ao Tanaka", "田中碧", "田中碧", 1998, "サッカー選手"),
            ("Hidemasa Morita", "守田英正", "守田英正", 1995, "サッカー選手"),
            ("Ayase Ueda", "上田綺世", "上田綺世", 1998, "サッカー選手"),
            ("Daizen Maeda", "前田大然", "前田大然", 1997, "サッカー選手"),
        ]

        # その他スポーツ
        other_sports = [
            # テニス
            ("Kei Nishikori", "錦織圭", "錦織圭", 1989, "テニス選手"),
            ("Naomi Osaka", "大坂なおみ", "大坂なおみ", 1997, "テニス選手"),

            # ゴルフ
            ("Hideki Matsuyama", "松山英樹", "松山英樹", 1992, "ゴルファー"),
            ("Hinako Shibuno", "渋野日向子", "渋野日向子", 1998, "ゴルファー"),

            # フィギュアスケート
            ("Yuzuru Hanyu", "羽生結弦", "羽生結弦", 1994, "フィギュアスケーター"),
            ("Shoma Uno", "宇野昌磨", "宇野昌磨", 1997, "フィギュアスケーター"),
            ("Yuma Kagiyama", "鍵山優真", "鍵山優真", 2003, "フィギュアスケーター"),
            ("Kaori Sakamoto", "坂本花織", "坂本花織", 2000, "フィギュアスケーター"),
            ("Rika Kihira", "紀平梨花", "紀平梨花", 2002, "フィギュアスケーター"),

            # 水泳
            ("Daiya Seto", "瀬戸大也", "瀬戸大也", 1994, "水泳選手"),
            ("Rikako Ikee", "池江璃花子", "池江璃花子", 2000, "水泳選手"),
            ("Kosuke Hagino", "萩野公介", "萩野公介", 1994, "水泳選手"),

            # 体操
            ("Kohei Uchimura", "内村航平", "内村航平", 1989, "体操選手"),
            ("Daiki Hashimoto", "橋本大輝", "橋本大輝", 2001, "体操選手"),

            # 陸上
            ("Yoshihide Kiryu", "桐生祥秀", "桐生祥秀", 1995, "陸上選手"),
            ("Ryuji Miura", "三浦龍司", "三浦龍司", 2002, "陸上選手"),
            ("Abdul Hakim Sani Brown", "サニブラウン・アブデル・ハキーム", "サニブラウン", 1999, "陸上選手"),

            # バスケットボール
            ("Rui Hachimura", "八村塁", "八村塁", 1998, "バスケットボール選手"),
            ("Yuta Watanabe", "渡邊雄太", "渡邊雄太", 1994, "バスケットボール選手"),

            # バレーボール
            ("Yuki Ishikawa", "石川祐希", "石川祐希", 1995, "バレーボール選手"),
            ("Yuji Nishida", "西田有志", "西田有志", 2000, "バレーボール選手"),
            ("Ran Takahashi", "高橋藍", "高橋藍", 2001, "バレーボール選手"),

            # 卓球
            ("Tomokazu Harimoto", "張本智和", "張本智和", 2003, "卓球選手"),
            ("Mima Ito", "伊藤美誠", "伊藤美誠", 2000, "卓球選手"),
            ("Kasumi Ishikawa", "石川佳純", "石川佳純", 1993, "卓球選手"),
            ("Hina Hayata", "早田ひな", "早田ひな", 2000, "卓球選手"),

            # ボクシング
            ("Naoya Inoue", "井上尚弥", "井上尚弥", 1993, "ボクサー"),
            ("Kazuto Ioka", "井岡一翔", "井岡一翔", 1989, "ボクサー"),
            ("Ryota Murata", "村田諒太", "村田諒太", 1986, "ボクサー"),

            # 相撲
            ("Terunofuji Haruo", "照ノ富士春雄", "照ノ富士", 1991, "力士"),
            ("Takakeisho Mitsunobu", "貴景勝光信", "貴景勝", 1996, "力士"),
            ("Kiribayama Tetsuo", "霧馬山鐵雄", "霧馬山", 1996, "力士"),
        ]

        # データ作成
        for person in baseball_players + soccer_players + other_sports:
            if len(person) == 5:
                name, display, ja, year, occ = person
                record = self.create_person_record(
                    person_name=name,
                    person_name_ja=ja,
                    person_name_display=display,
                    birth_year=year,
                    occupation=occ,
                    category="スポーツ",
                    phase="Phase3"
                )
                data.append(record)

        return data

    def collect_phase4_international(self) -> List[Dict]:
        """Phase 4: 国際的有名人（2,000件）"""
        print("\n🌍 Phase 4: 国際的有名人収集中...")

        data = []

        # ハリウッド俳優
        hollywood_actors = [
            ("Tom Cruise", "トム・クルーズ", "トム・クルーズ", 1962, "俳優", "アメリカ"),
            ("Brad Pitt", "ブラッド・ピット", "ブラッド・ピット", 1963, "俳優", "アメリカ"),
            ("Leonardo DiCaprio", "レオナルド・ディカプリオ", "レオナルド・ディカプリオ", 1974, "俳優", "アメリカ"),
            ("Johnny Depp", "ジョニー・デップ", "ジョニー・デップ", 1963, "俳優", "アメリカ"),
            ("Will Smith", "ウィル・スミス", "ウィル・スミス", 1968, "俳優", "アメリカ"),
            ("Robert Downey Jr.", "ロバート・ダウニー・Jr.", "ロバート・ダウニー・Jr.", 1965, "俳優", "アメリカ"),
            ("Chris Evans", "クリス・エヴァンス", "クリス・エヴァンス", 1981, "俳優", "アメリカ"),
            ("Chris Hemsworth", "クリス・ヘムズワース", "クリス・ヘムズワース", 1983, "俳優", "オーストラリア"),
            ("Tom Holland", "トム・ホランド", "トム・ホランド", 1996, "俳優", "イギリス"),
            ("Benedict Cumberbatch", "ベネディクト・カンバーバッチ", "ベネディクト・カンバーバッチ", 1976, "俳優", "イギリス"),
            ("Ryan Reynolds", "ライアン・レイノルズ", "ライアン・レイノルズ", 1976, "俳優", "カナダ"),
            ("Ryan Gosling", "ライアン・ゴズリング", "ライアン・ゴズリング", 1980, "俳優", "カナダ"),
            ("Joaquin Phoenix", "ホアキン・フェニックス", "ホアキン・フェニックス", 1974, "俳優", "アメリカ"),
            ("Christian Bale", "クリスチャン・ベール", "クリスチャン・ベール", 1974, "俳優", "イギリス"),
            ("Matt Damon", "マット・デイモン", "マット・デイモン", 1970, "俳優", "アメリカ"),
        ]

        # ハリウッド女優
        hollywood_actresses = [
            ("Scarlett Johansson", "スカーレット・ヨハンソン", "スカーレット・ヨハンソン", 1984, "女優", "アメリカ"),
            ("Jennifer Lawrence", "ジェニファー・ローレンス", "ジェニファー・ローレンス", 1990, "女優", "アメリカ"),
            ("Emma Stone", "エマ・ストーン", "エマ・ストーン", 1988, "女優", "アメリカ"),
            ("Emma Watson", "エマ・ワトソン", "エマ・ワトソン", 1990, "女優", "イギリス"),
            ("Anne Hathaway", "アン・ハサウェイ", "アン・ハサウェイ", 1982, "女優", "アメリカ"),
            ("Angelina Jolie", "アンジェリーナ・ジョリー", "アンジェリーナ・ジョリー", 1975, "女優", "アメリカ"),
            ("Jennifer Aniston", "ジェニファー・アニストン", "ジェニファー・アニストン", 1969, "女優", "アメリカ"),
            ("Natalie Portman", "ナタリー・ポートマン", "ナタリー・ポートマン", 1981, "女優", "イスラエル"),
            ("Margot Robbie", "マーゴット・ロビー", "マーゴット・ロビー", 1990, "女優", "オーストラリア"),
            ("Gal Gadot", "ガル・ガドット", "ガル・ガドット", 1985, "女優", "イスラエル"),
            ("Zendaya", "ゼンデイヤ", "ゼンデイヤ", 1996, "女優", "アメリカ"),
            ("Florence Pugh", "フローレンス・ピュー", "フローレンス・ピュー", 1996, "女優", "イギリス"),
            ("Anya Taylor-Joy", "アニャ・テイラー＝ジョイ", "アニャ・テイラー＝ジョイ", 1996, "女優", "アメリカ"),
            ("Saoirse Ronan", "シアーシャ・ローナン", "シアーシャ・ローナン", 1994, "女優", "アイルランド"),
            ("Timothee Chalamet", "ティモシー・シャラメ", "ティモシー・シャラメ", 1995, "俳優", "アメリカ"),
        ]

        # 世界の音楽アーティスト
        music_artists = [
            ("Taylor Swift", "テイラー・スウィフト", "テイラー・スウィフト", 1989, "歌手", "アメリカ"),
            ("Ed Sheeran", "エド・シーラン", "エド・シーラン", 1991, "歌手", "イギリス"),
            ("Bruno Mars", "ブルーノ・マーズ", "ブルーノ・マーズ", 1985, "歌手", "アメリカ"),
            ("Ariana Grande", "アリアナ・グランデ", "アリアナ・グランデ", 1993, "歌手", "アメリカ"),
            ("Billie Eilish", "ビリー・アイリッシュ", "ビリー・アイリッシュ", 2001, "歌手", "アメリカ"),
            ("Justin Bieber", "ジャスティン・ビーバー", "ジャスティン・ビーバー", 1994, "歌手", "カナダ"),
            ("Dua Lipa", "デュア・リパ", "デュア・リパ", 1995, "歌手", "イギリス"),
            ("The Weeknd", "ザ・ウィークエンド", "ザ・ウィークエンド", 1990, "歌手", "カナダ"),
            ("Drake", "ドレイク", "ドレイク", 1986, "ラッパー", "カナダ"),
            ("Post Malone", "ポスト・マローン", "ポスト・マローン", 1995, "歌手", "アメリカ"),
            ("Shawn Mendes", "ショーン・メンデス", "ショーン・メンデス", 1998, "歌手", "カナダ"),
            ("Charlie Puth", "チャーリー・プース", "チャーリー・プース", 1991, "歌手", "アメリカ"),
            ("Sam Smith", "サム・スミス", "サム・スミス", 1992, "歌手", "イギリス"),
            ("Olivia Rodrigo", "オリヴィア・ロドリゴ", "オリヴィア・ロドリゴ", 2003, "歌手", "アメリカ"),
            ("Harry Styles", "ハリー・スタイルズ", "ハリー・スタイルズ", 1994, "歌手", "イギリス"),
        ]

        # 世界の実業家
        business_leaders = [
            ("Elon Musk", "イーロン・マスク", "イーロン・マスク", 1971, "実業家", "アメリカ"),
            ("Jeff Bezos", "ジェフ・ベゾス", "ジェフ・ベゾス", 1964, "実業家", "アメリカ"),
            ("Bill Gates", "ビル・ゲイツ", "ビル・ゲイツ", 1955, "実業家", "アメリカ"),
            ("Mark Zuckerberg", "マーク・ザッカーバーグ", "マーク・ザッカーバーグ", 1984, "実業家", "アメリカ"),
            ("Warren Buffett", "ウォーレン・バフェット", "ウォーレン・バフェット", 1930, "投資家", "アメリカ"),
            ("Tim Cook", "ティム・クック", "ティム・クック", 1960, "実業家", "アメリカ"),
            ("Sundar Pichai", "サンダー・ピチャイ", "サンダー・ピチャイ", 1972, "実業家", "アメリカ"),
            ("Satya Nadella", "サティア・ナデラ", "サティア・ナデラ", 1967, "実業家", "アメリカ"),
            ("Jack Ma", "ジャック・マー", "ジャック・マー", 1964, "実業家", "中国"),
            ("Larry Page", "ラリー・ペイジ", "ラリー・ペイジ", 1973, "実業家", "アメリカ"),
            ("Sergey Brin", "セルゲイ・ブリン", "セルゲイ・ブリン", 1973, "実業家", "アメリカ"),
            ("Richard Branson", "リチャード・ブランソン", "リチャード・ブランソン", 1950, "実業家", "イギリス"),
            ("Michael Bloomberg", "マイケル・ブルームバーグ", "マイケル・ブルームバーグ", 1942, "実業家", "アメリカ"),
            ("Larry Ellison", "ラリー・エリソン", "ラリー・エリソン", 1944, "実業家", "アメリカ"),
            ("Sam Altman", "サム・アルトマン", "サム・アルトマン", 1985, "実業家", "アメリカ"),
        ]

        # データ作成
        for person in hollywood_actors + hollywood_actresses + music_artists + business_leaders:
            if len(person) == 6:
                name, display, ja, year, occ, nationality = person
                record = self.create_person_record(
                    person_name=name,
                    person_name_ja=ja,
                    person_name_display=display,
                    birth_year=year,
                    occupation=occ,
                    nationality=nationality,
                    category="国際",
                    phase="Phase4"
                )
                data.append(record)

        return data

    def collect_phase5_special(self) -> List[Dict]:
        """Phase 5: 特殊カテゴリ（フィクション、歴史、動物）"""
        print("\n🎭 Phase 5: 特殊カテゴリ収集中...")

        data = []

        # アニメ・マンガキャラクター
        anime_characters = [
            ("Monkey D. Luffy", "モンキー・D・ルフィ", "ルフィ", None, "キャラクター"),
            ("Roronoa Zoro", "ロロノア・ゾロ", "ゾロ", None, "キャラクター"),
            ("Naruto Uzumaki", "うずまきナルト", "ナルト", None, "キャラクター"),
            ("Sasuke Uchiha", "うちはサスケ", "サスケ", None, "キャラクター"),
            ("Goku", "孫悟空", "悟空", None, "キャラクター"),
            ("Vegeta", "ベジータ", "ベジータ", None, "キャラクター"),
            ("Ichigo Kurosaki", "黒崎一護", "一護", None, "キャラクター"),
            ("Light Yagami", "夜神月", "夜神月", None, "キャラクター"),
            ("Eren Yeager", "エレン・イェーガー", "エレン", None, "キャラクター"),
            ("Levi Ackerman", "リヴァイ・アッカーマン", "リヴァイ", None, "キャラクター"),
            ("Tanjiro Kamado", "竈門炭治郎", "炭治郎", None, "キャラクター"),
            ("Nezuko Kamado", "竈門禰豆子", "禰豆子", None, "キャラクター"),
            ("Zenitsu Agatsuma", "我妻善逸", "善逸", None, "キャラクター"),
            ("Inosuke Hashibira", "嘴平伊之助", "伊之助", None, "キャラクター"),
            ("Gojo Satoru", "五条悟", "五条悟", None, "キャラクター"),
            ("Yuji Itadori", "虎杖悠仁", "虎杖", None, "キャラクター"),
            ("Megumi Fushiguro", "伏黒恵", "伏黒", None, "キャラクター"),
            ("Nobara Kugisaki", "釘崎野薔薇", "釘崎", None, "キャラクター"),
            ("Anya Forger", "アーニャ・フォージャー", "アーニャ", None, "キャラクター"),
            ("Loid Forger", "ロイド・フォージャー", "ロイド", None, "キャラクター"),
            ("Yor Forger", "ヨル・フォージャー", "ヨル", None, "キャラクター"),
            ("Denji", "デンジ", "デンジ", None, "キャラクター"),
            ("Makima", "マキマ", "マキマ", None, "キャラクター"),
            ("Power", "パワー", "パワー", None, "キャラクター"),
            ("Doraemon", "ドラえもん", "ドラえもん", None, "キャラクター"),
            ("Nobita Nobi", "野比のび太", "のび太", None, "キャラクター"),
            ("Shizuka Minamoto", "源静香", "しずかちゃん", None, "キャラクター"),
            ("Takeshi Goda", "剛田武", "ジャイアン", None, "キャラクター"),
            ("Suneo Honekawa", "骨川スネ夫", "スネ夫", None, "キャラクター"),
            ("Conan Edogawa", "江戸川コナン", "コナン", None, "キャラクター"),
            ("Shinichi Kudo", "工藤新一", "新一", None, "キャラクター"),
            ("Ran Mouri", "毛利蘭", "蘭", None, "キャラクター"),
            ("Pikachu", "ピカチュウ", "ピカチュウ", None, "キャラクター"),
            ("Ash Ketchum", "サトシ", "サトシ", None, "キャラクター"),
        ]

        # 歴史上の人物（追加）
        historical_figures = [
            ("Takeda Shingen", "武田信玄", "武田信玄", 1521, "武将"),
            ("Uesugi Kenshin", "上杉謙信", "上杉謙信", 1530, "武将"),
            ("Date Masamune", "伊達政宗", "伊達政宗", 1567, "武将"),
            ("Sanada Yukimura", "真田幸村", "真田幸村", 1567, "武将"),
            ("Miyamoto Musashi", "宮本武蔵", "宮本武蔵", 1584, "剣豪"),
            ("Sasaki Kojiro", "佐々木小次郎", "佐々木小次郎", 1583, "剣豪"),
            ("Minamoto no Yoshitsune", "源義経", "源義経", 1159, "武将"),
            ("Minamoto no Yoritomo", "源頼朝", "源頼朝", 1147, "武将"),
            ("Taira no Kiyomori", "平清盛", "平清盛", 1118, "武将"),
            ("Ashikaga Takauji", "足利尊氏", "足利尊氏", 1305, "武将"),
            ("Ashikaga Yoshimitsu", "足利義満", "足利義満", 1358, "将軍"),
            ("Kusunoki Masashige", "楠木正成", "楠木正成", 1294, "武将"),
            ("Hojo Tokimune", "北条時宗", "北条時宗", 1251, "執権"),
            ("Kondo Isami", "近藤勇", "近藤勇", 1834, "新選組"),
            ("Hijikata Toshizo", "土方歳三", "土方歳三", 1835, "新選組"),
            ("Okita Soji", "沖田総司", "沖田総司", 1842, "新選組"),
            ("Katsu Kaishu", "勝海舟", "勝海舟", 1823, "幕臣"),
            ("Yoshida Shoin", "吉田松陰", "吉田松陰", 1830, "思想家"),
            ("Fukuzawa Yukichi", "福沢諭吉", "福沢諭吉", 1835, "思想家"),
            ("Ito Hirobumi", "伊藤博文", "伊藤博文", 1841, "政治家"),
        ]

        # 有名な動物
        famous_animals = [
            ("Oguri Cap", "オグリキャップ", "オグリキャップ", 1985, "競走馬"),
            ("Deep Impact", "ディープインパクト", "ディープインパクト", 2002, "競走馬"),
            ("Orfevre", "オルフェーヴル", "オルフェーヴル", 2008, "競走馬"),
            ("Kitasan Black", "キタサンブラック", "キタサンブラック", 2012, "競走馬"),
            ("Symboli Rudolf", "シンボリルドルフ", "シンボリルドルフ", 1981, "競走馬"),
            ("Tokai Teio", "トウカイテイオー", "トウカイテイオー", 1988, "競走馬"),
            ("Silence Suzuka", "サイレンススズカ", "サイレンススズカ", 1994, "競走馬"),
            ("Special Week", "スペシャルウィーク", "スペシャルウィーク", 1995, "競走馬"),
            ("El Condor Pasa", "エルコンドルパサー", "エルコンドルパサー", 1995, "競走馬"),
            ("Grass Wonder", "グラスワンダー", "グラスワンダー", 1995, "競走馬"),
            ("Hachiko", "ハチ公", "ハチ公", 1923, "秋田犬"),
            ("Tama", "たま", "たま駅長", 1999, "猫"),
            ("Shabani", "シャバーニ", "シャバーニ", 1996, "ゴリラ"),
        ]

        # データ作成
        for person in anime_characters:
            if len(person) == 5:
                name, display, ja, year, occ = person
                record = self.create_person_record(
                    person_name=name,
                    person_name_ja=ja,
                    person_name_display=display,
                    birth_year=year,
                    occupation=occ,
                    category="フィクション",
                    is_fictional=True,
                    phase="Phase5"
                )
                data.append(record)

        for person in historical_figures:
            if len(person) == 5:
                name, display, ja, year, occ = person
                record = self.create_person_record(
                    person_name=name,
                    person_name_ja=ja,
                    person_name_display=display,
                    birth_year=year,
                    occupation=occ,
                    category="歴史",
                    phase="Phase5"
                )
                data.append(record)

        for animal in famous_animals:
            if len(animal) == 5:
                name, display, ja, year, occ = animal
                record = self.create_person_record(
                    person_name=name,
                    person_name_ja=ja,
                    person_name_display=display,
                    birth_year=year,
                    occupation=occ,
                    category="動物",
                    is_animal=True,
                    phase="Phase5"
                )
                data.append(record)

        return data

    def process_phase(self, phase_name: str, collect_func) -> List[Dict]:
        """フェーズ単位の処理"""
        print(f"\n{'='*60}")
        print(f"🚀 {phase_name} 開始")
        print(f"{'='*60}")

        # データ収集
        phase_data = collect_func()
        print(f"\n📊 {len(phase_data)}件のデータを収集")

        # バッチ処理
        processed_data = []

        for i in range(0, len(phase_data), self.batch_size):
            batch = phase_data[i:i+self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(phase_data) + self.batch_size - 1) // self.batch_size

            print(f"\n--- バッチ {batch_num}/{total_batches} 処理中 ---")

            # 検証
            is_valid, validation_result = self.validate_batch(batch)

            if is_valid:
                self.stats['validation_passes'] += 1
                processed_data.extend(batch)

                # 既存データに追加（重複防止用）
                for record in batch:
                    self.existing_names.add(record['person_name'].lower())
                    self.existing_display.add(record['person_name_display'])
            else:
                self.stats['validation_failures'] += 1

                # エラー修正または除外
                fixed_batch = self.fix_batch_errors(batch, validation_result)

                if fixed_batch:
                    processed_data.extend(fixed_batch)

                    # 既存データに追加
                    for record in fixed_batch:
                        self.existing_names.add(record['person_name'].lower())
                        self.existing_display.add(record['person_name_display'])

            # 進捗表示
            print(f"   進捗: {len(processed_data)}/{len(phase_data)}件処理済み")

        # チェックポイント保存
        if processed_data:
            self.save_checkpoint(phase_name, processed_data)

        # 統計更新
        self.stats['phase_results'][phase_name] = {
            'collected': len(phase_data),
            'processed': len(processed_data),
            'errors': len(phase_data) - len(processed_data)
        }

        print(f"\n✅ {phase_name} 完了: {len(processed_data)}件追加")

        return processed_data

    def run(self):
        """メイン実行"""
        print("\n" + "="*60)
        print("🛡️ Ultra Think Safe Collector Extended")
        print("Phase 2-5 実行")
        print("="*60)

        # 既存データ読み込み
        if not self.load_existing_data():
            return None

        # バックアップ作成
        backup_file = f"backup_{self.base_file}_{self.timestamp}"
        print(f"\n💾 バックアップ作成中: {backup_file}")
        with open(self.base_file, 'r', encoding='utf-8-sig') as src:
            with open(backup_file, 'w', encoding='utf-8-sig') as dst:
                dst.write(src.read())

        # Phase 2実行
        print("\n" + "="*60)
        print("📋 Phase 2: エンタメ系強化")
        print("="*60)

        # Phase 2-1: K-POP・バンド
        phase2_1 = self.process_phase("Phase2-1_KPop_Bands", self.collect_phase2_kpop_bands)
        self.new_data.extend(phase2_1)

        # Phase 2-2: 声優・YouTuber
        phase2_2 = self.process_phase("Phase2-2_VoiceActors_YouTubers", self.collect_phase2_voice_actors_youtubers)
        self.new_data.extend(phase2_2)

        # Phase 3実行
        phase3 = self.process_phase("Phase3_Sports", self.collect_phase3_sports)
        self.new_data.extend(phase3)

        # Phase 4実行
        phase4 = self.process_phase("Phase4_International", self.collect_phase4_international)
        self.new_data.extend(phase4)

        # Phase 5実行
        phase5 = self.process_phase("Phase5_Special", self.collect_phase5_special)
        self.new_data.extend(phase5)

        # 最終統合
        print("\n" + "="*60)
        print("🔄 最終統合処理")
        print("="*60)

        # 全データ結合
        all_data = self.existing_data + self.new_data

        # 最終検証
        print(f"\n🔍 最終検証中（{len(all_data)}件）...")
        final_issues = 0
        for record in all_data:
            if not record.get('person_name', '').strip():
                final_issues += 1
            if not record.get('person_name_display', '').strip():
                final_issues += 1

        if final_issues == 0:
            print("✅ 最終検証合格！")
        else:
            print(f"⚠️ {final_issues}件の問題を検出")

        # 保存
        print(f"\n💾 最終データ保存中...")

        # CSV保存
        with open(self.output_csv, 'w', encoding='utf-8-sig', newline='') as f:
            if all_data:
                writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                writer.writeheader()
                writer.writerows(all_data)

        # JSON保存
        with open(self.output_json, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        # 統計更新
        self.stats['added_count'] = len(self.new_data)

        # レポート生成
        self.generate_report(all_data)

        print("\n" + "="*60)
        print("✅ 処理完了")
        print(f"   - 初期データ: {self.stats['initial_count']}件")
        print(f"   - 追加データ: {self.stats['added_count']}件")
        print(f"   - 最終データ: {len(all_data)}件")
        print(f"   - 出力ファイル: {self.output_csv}")
        print("="*60)

        return self.output_csv

    def generate_report(self, all_data: List[Dict]):
        """レポート生成"""
        report = f"""# 🛡️ Extended Collection Report

## 📅 実行日時
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 収集結果

### 全体統計
- **初期データ**: {self.stats['initial_count']}件
- **追加データ**: {self.stats['added_count']}件
- **最終データ**: {len(all_data)}件
- **重複スキップ**: {self.stats['duplicate_count']}件
- **エラー修正**: {self.stats['fixed_count']}件
- **エラースキップ**: {self.stats['error_count']}件

### 検証結果
- **検証合格バッチ**: {self.stats['validation_passes']}
- **検証不合格バッチ**: {self.stats['validation_failures']}
- **成功率**: {self.stats['validation_passes'] / max(1, self.stats['validation_passes'] + self.stats['validation_failures']) * 100:.1f}%

### フェーズ別結果
"""

        for phase_name, result in self.stats['phase_results'].items():
            report += f"""
#### {phase_name}
- 収集: {result['collected']}件
- 処理: {result['processed']}件
- エラー: {result['errors']}件
"""

        report += f"""
## ✅ 品質保証

### データ品質
- person_name充足率: {sum(1 for r in all_data if r.get('person_name', '').strip()) / len(all_data) * 100:.1f}%
- person_name_display充足率: {sum(1 for r in all_data if r.get('person_name_display', '').strip()) / len(all_data) * 100:.1f}%
- birth_year充足率: {sum(1 for r in all_data if r.get('birth_year', '').strip()) / len(all_data) * 100:.1f}%

## 📁 出力ファイル
- **CSV**: {self.output_csv}
- **JSON**: {self.output_json}
- **チェックポイント**: {self.checkpoint_dir}/

## 🎯 達成状況

### 目標に対する進捗
- **目標**: 11,211件
- **現在**: {len(all_data)}件
- **達成率**: {len(all_data) / 11211 * 100:.1f}%
- **残り**: {max(0, 11211 - len(all_data))}件

---
*Safe Collection System Extended*
*Quality First, Errors Zero*
"""

        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📝 レポート生成: {self.report_file}")


def main():
    """メイン実行"""
    collector = SafeCollectorExtended()
    output_file = collector.run()

    if output_file:
        print(f"\n🎊 SafeCollector Extended実行成功！")
        print(f"📁 出力ファイル: {output_file}")
    else:
        print(f"\n❌ SafeCollector Extended実行失敗")

    return output_file


if __name__ == "__main__":
    main()
