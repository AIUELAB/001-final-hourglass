#!/usr/bin/env python3
"""
Ultra Think 自動較正機能付き人物追加システム
Auto-Calibrated Person Addition System

人物追加時に自動的にname_recognitionを較正し、
適切なスコアを設定するインテリジェントシステム
"""

import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib
from ultra_think_japanese_recognition_calibrator import JapaneseRecognitionCalibrator

class AutoCalibratedPersonAdder:
    """自動較正機能付き人物追加システム"""

    def __init__(self, database_path: str = None):
        """
        初期化

        Args:
            database_path: 既存データベースのパス（オプション）
        """
        # 較正システムを初期化
        self.calibrator = JapaneseRecognitionCalibrator()

        # 既存データベースを読み込む
        self.database_path = database_path
        self.existing_persons = []
        self.person_index = {}  # 高速検索用インデックス

        if database_path and os.path.exists(database_path):
            self.load_existing_database(database_path)

        # カテゴリ定義
        self.valid_categories = [
            'エンタメ', 'スポーツ', '学術・科学', 'ビジネス', '政治',
            '歴史上の人物', '文化・芸術', 'テクノロジー', 'その他'
        ]

        # 次のperson_idを決定
        self.next_person_id = self._get_next_person_id()

    def load_existing_database(self, filepath: str):
        """既存データベースを読み込む"""
        print(f"📂 既存データベース読み込み中: {filepath}")

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            self.existing_persons = list(reader)

        # インデックスを構築
        for person in self.existing_persons:
            key = self._create_person_key(person)
            self.person_index[key] = person

        print(f"  ✅ {len(self.existing_persons)}名のデータを読み込みました")

    def _get_next_person_id(self) -> int:
        """次のperson_idを取得"""
        if not self.existing_persons:
            return 1

        max_id = 0
        for person in self.existing_persons:
            person_id = person.get('person_id', 'P0')
            if person_id.startswith('P'):
                try:
                    id_num = int(person_id[1:])
                    max_id = max(max_id, id_num)
                except:
                    pass

        return max_id + 1

    def _create_person_key(self, person: Dict) -> str:
        """人物の一意キーを作成（重複チェック用）"""
        name = person.get('person_name', '').lower()
        birth_year = person.get('birth_year', '')
        return f"{name}_{birth_year}"

    def add_person(self,
                   person_name: str,
                   person_name_ja: str = None,
                   person_name_display: str = None,
                   category: str = 'その他',
                   nationality: str = '不明',
                   occupation: str = '',
                   birth_year: int = None,
                   additional_data: Dict = None) -> Dict:
        """
        単一の人物を追加（自動較正付き）

        Args:
            person_name: 人物名（英語/原語）
            person_name_ja: 日本語名
            person_name_display: 表示名
            category: カテゴリ
            nationality: 国籍
            occupation: 職業
            birth_year: 生年
            additional_data: 追加データ

        Returns:
            追加された人物データ（較正済み）
        """
        # 基本データを構築
        person_data = self._create_person_data(
            person_name, person_name_ja, person_name_display,
            category, nationality, occupation, birth_year,
            additional_data
        )

        # 重複チェック
        if self._is_duplicate(person_data):
            print(f"⚠️  重複: {person_name} は既に存在します")
            return None

        # 自動較正を実行
        calibrated_score = self.calibrator.calibrate_score(person_data)
        person_data['name_recognition'] = calibrated_score

        # メタデータを追加
        person_data['recognition_metadata'] = self._create_recognition_metadata(
            person_data, calibrated_score
        )

        # データベースに追加
        self.existing_persons.append(person_data)
        key = self._create_person_key(person_data)
        self.person_index[key] = person_data

        print(f"✅ 追加: {person_name_ja or person_name} (知名度: {calibrated_score}点)")

        return person_data

    def add_persons_batch(self, persons_list: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        複数の人物を一括追加（自動較正付き）

        Args:
            persons_list: 人物データのリスト

        Returns:
            (成功リスト, 失敗リスト)
        """
        added = []
        failed = []

        print(f"\n🔄 バッチ処理開始: {len(persons_list)}名")

        for person_input in persons_list:
            try:
                result = self.add_person(
                    person_name=person_input.get('person_name'),
                    person_name_ja=person_input.get('person_name_ja'),
                    person_name_display=person_input.get('person_name_display'),
                    category=person_input.get('category', 'その他'),
                    nationality=person_input.get('nationality', '不明'),
                    occupation=person_input.get('occupation', ''),
                    birth_year=person_input.get('birth_year'),
                    additional_data=person_input.get('additional_data')
                )

                if result:
                    added.append(result)
                else:
                    failed.append(person_input)

            except Exception as e:
                print(f"❌ エラー: {person_input.get('person_name')} - {str(e)}")
                failed.append(person_input)

        print(f"\n📊 バッチ処理完了:")
        print(f"  成功: {len(added)}名")
        print(f"  失敗/重複: {len(failed)}名")

        return added, failed

    def _create_person_data(self, person_name, person_name_ja, person_name_display,
                           category, nationality, occupation, birth_year,
                           additional_data) -> Dict:
        """人物データを構築"""
        # person_name_jaが未設定の場合
        if not person_name_ja:
            person_name_ja = person_name

        # person_name_displayが未設定の場合
        if not person_name_display:
            person_name_display = person_name_ja

        # カテゴリの検証
        if category not in self.valid_categories:
            category = 'その他'

        # person_idを生成
        person_id = f"P{self.next_person_id:06d}"
        self.next_person_id += 1

        # episode_idとhashを生成
        timestamp = datetime.now()
        episode_id = f"EP_{timestamp.strftime('%Y%m%d_%H%M%S')}_{self._generate_hash()[:6]}"
        episode_hash = hashlib.md5(f"{person_name}_{timestamp}".encode()).hexdigest()

        # 基本データ
        data = {
            'accuracy_score': 85,
            'age': '',
            'age_months': '',
            'category': category,
            'created_at': timestamp.isoformat(),
            'episode_date': '',
            'episode_hash': episode_hash,
            'episode_id': episode_id,
            'episode_text': '',
            'episode_title': '',
            'episode_type': '',
            'episode_year': '',
            'era': self._determine_era(birth_year),
            'extended_data': json.dumps(additional_data or {}, ensure_ascii=False),
            'impact_score': 85,
            'is_published': 'true',
            'name_recognition': 50,  # 較正前の仮値
            'nationality': nationality,
            'occupation': occupation,
            'person_id': person_id,
            'person_name': person_name,
            'person_name_display': person_name_display,
            'person_name_ja': person_name_ja,
            'recognition_metadata': '{}',
            'source': 'Auto-Added'
        }

        # birth_yearがある場合は追加
        if birth_year:
            data['birth_year'] = str(birth_year)

        return data

    def _generate_hash(self) -> str:
        """ランダムハッシュを生成"""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    def _determine_era(self, birth_year) -> str:
        """生年から時代を判定"""
        if not birth_year:
            return ''

        if birth_year >= 2000:
            return '現代'
        elif birth_year >= 1900:
            return '20世紀'
        elif birth_year >= 1800:
            return '19世紀'
        elif birth_year >= 1700:
            return '18世紀'
        elif birth_year >= 1600:
            return '17世紀'
        else:
            return '古代'

    def _is_duplicate(self, person_data: Dict) -> bool:
        """重複チェック"""
        key = self._create_person_key(person_data)
        return key in self.person_index

    def _create_recognition_metadata(self, person_data: Dict, calibrated_score: int) -> str:
        """認識メタデータを作成"""
        metadata = {
            'calibrated_at': datetime.now().isoformat(),
            'calibrated_score': calibrated_score,
            'auto_calibrated': True,
            'calibration_version': '1.0',
            'category': person_data['category'],
            'nationality': person_data['nationality']
        }

        # 日本人の場合は追加情報
        if person_data['nationality'] == '日本':
            metadata['japan_priority'] = True

        return json.dumps(metadata, ensure_ascii=False)

    def save_database(self, output_path: str = None):
        """データベースを保存"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"ultra_think_database_{timestamp}.csv"

        if not self.existing_persons:
            print("⚠️  保存するデータがありません")
            return

        # ヘッダーを取得
        headers = list(self.existing_persons[0].keys())

        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(self.existing_persons)

        print(f"💾 データベースを保存しました: {output_path}")
        print(f"   総人数: {len(self.existing_persons)}名")

    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        stats = {
            'total_persons': len(self.existing_persons),
            'categories': {},
            'nationalities': {},
            'score_distribution': {
                '90-100': 0, '80-89': 0, '70-79': 0,
                '60-69': 0, '50-59': 0, '40-49': 0,
                '30-39': 0, '1-29': 0
            }
        }

        for person in self.existing_persons:
            # カテゴリ別
            cat = person.get('category', 'その他')
            stats['categories'][cat] = stats['categories'].get(cat, 0) + 1

            # 国籍別
            nat = person.get('nationality', '不明')
            stats['nationalities'][nat] = stats['nationalities'].get(nat, 0) + 1

            # スコア分布
            score = int(person.get('name_recognition', 50))
            if score >= 90:
                stats['score_distribution']['90-100'] += 1
            elif score >= 80:
                stats['score_distribution']['80-89'] += 1
            elif score >= 70:
                stats['score_distribution']['70-79'] += 1
            elif score >= 60:
                stats['score_distribution']['60-69'] += 1
            elif score >= 50:
                stats['score_distribution']['50-59'] += 1
            elif score >= 40:
                stats['score_distribution']['40-49'] += 1
            elif score >= 30:
                stats['score_distribution']['30-39'] += 1
            else:
                stats['score_distribution']['1-29'] += 1

        return stats


# 使用例とテスト機能
def example_usage():
    """使用例"""
    print("🎌 Ultra Think 自動較正機能付き人物追加システム")
    print("=" * 60)

    # 既存データベースを指定してシステムを初期化
    existing_db = "ultra_think_calibrated_20250827_132748.csv"
    if not os.path.exists(existing_db):
        existing_db = None

    adder = AutoCalibratedPersonAdder(existing_db)

    # 単一人物の追加例
    print("\n【単一人物追加のテスト】")
    new_person = adder.add_person(
        person_name="Shinsaku Takasugi",
        person_name_ja="高杉晋作",
        person_name_display="高杉晋作",
        category="歴史上の人物",
        nationality="日本",
        occupation="幕末の志士",
        birth_year=1839
    )

    if new_person:
        print(f"  → 知名度スコア: {new_person['name_recognition']}点")

    # バッチ追加例
    print("\n【バッチ追加のテスト】")
    batch_persons = [
        {
            'person_name': 'Ryoma Sakamoto',
            'person_name_ja': '坂本龍馬',
            'category': '歴史上の人物',
            'nationality': '日本',
            'occupation': '幕末の志士',
            'birth_year': 1836
        },
        {
            'person_name': 'Soseki Natsume',
            'person_name_ja': '夏目漱石',
            'category': '文化・芸術',
            'nationality': '日本',
            'occupation': '作家',
            'birth_year': 1867
        },
        {
            'person_name': 'Hideyo Noguchi',
            'person_name_ja': '野口英世',
            'category': '学術・科学',
            'nationality': '日本',
            'occupation': '細菌学者',
            'birth_year': 1876
        }
    ]

    added, failed = adder.add_persons_batch(batch_persons)

    # 統計情報を表示
    print("\n📊 現在のデータベース統計:")
    stats = adder.get_statistics()
    print(f"  総人数: {stats['total_persons']}名")
    print(f"  カテゴリ数: {len(stats['categories'])}種類")
    print(f"  国籍数: {len(stats['nationalities'])}ヶ国")

    # データベースを保存
    adder.save_database()

if __name__ == "__main__":
    example_usage()
