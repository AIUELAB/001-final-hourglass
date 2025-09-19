#!/usr/bin/env python3
"""
実際のデータベースデータから表示用短縮名を生成
- 既存の人物データを使用
- 職業・年齢・性別に基づく適切な敬称の選択
- データベースへの反映
"""

import json
from datetime import datetime
from pathlib import Path

from japanese_name_shortener import JapaneseNameShortener, PersonInfo


class DisplayNameGenerator:
    """表示用短縮名生成クラス"""

    def __init__(self) -> None:
        self.shortener = JapaneseNameShortener()

        # 年齢推定のための職業キーワード
        self.age_indicators = {
            'child': ['小学生', '中学生', '高校生', 'student', 'child'],
            'teen': ['学生', 'teenager', 'adolescent'],
            'young_adult': ['新人', '若手', 'young', 'junior'],
            'adult': ['会社員', 'employee', 'worker', 'professional'],
            'senior': ['ベテラン', 'veteran', 'senior', 'expert']
        }

        # 性別推定のための名前パターン
        self.gender_patterns = {
            'male': ['男', '男性', 'male', 'man', 'boy'],
            'female': ['女', '女性', 'female', 'woman', 'girl']
        }

    def estimate_age_from_occupation(self, occupation: str) -> int | None:
        """
        職業から年齢を推定

        Args:
            occupation: 職業文字列

        Returns:
            推定年齢
        """
        if not occupation:
            return None

        occupation_lower = occupation.lower()

        # 年齢指標のチェック
        for age_group, indicators in self.age_indicators.items():
            for indicator in indicators:
                if indicator.lower() in occupation_lower:
                    if age_group == 'child':
                        return 12
                    elif age_group == 'teen':
                        return 18
                    elif age_group == 'young_adult':
                        return 25
                    elif age_group == 'adult':
                        return 40
                    elif age_group == 'senior':
                        return 60

        # デフォルト年齢（成人）
        return 35

    def estimate_gender_from_name(self, name: str) -> str | None:
        """
        名前から性別を推定（簡易版）

        Args:
            name: 名前

        Returns:
            推定性別
        """
        if not name:
            return None

        # 実際の実装では、より高度な性別推定が必要
        # ここでは簡易的な推定を行う
        name_lower = name.lower()

        # 職業から性別を推定
        if '女優' in name_lower or 'actress' in name_lower:
            return 'female'
        elif '俳優' in name_lower or 'actor' in name_lower:
            return 'male'

        # デフォルト（推定不能）
        return None

    def process_person_data(self, person_data: dict) -> PersonInfo:
        """
        人物データをPersonInfoオブジェクトに変換

        Args:
            person_data: 人物データの辞書

        Returns:
            PersonInfoオブジェクト
        """
        name = person_data.get('name', '')
        occupation = person_data.get('occupation', '')

        # 年齢と性別を推定
        estimated_age = self.estimate_age_from_occupation(occupation)
        estimated_gender = self.estimate_gender_from_name(name)

        return PersonInfo(
            name=name,
            occupation=occupation,
            age=estimated_age,
            gender=estimated_gender
        )

    def generate_display_names(self, input_file: str, output_file: str) -> dict:
        """
        表示用短縮名を生成

        Args:
            input_file: 入力ファイルパス
            output_file: 出力ファイルパス

        Returns:
            処理ログ
        """
        print(f"🔤 表示用短縮名の生成を開始: {input_file}")

        # JSONファイルを読み込み
        input_path = Path(input_file)
        with input_path.open(encoding='utf-8') as f:
            data = json.load(f)

        # 処理ログ
        total_entries = len(data)
        processed_entries = 0
        display_names_generated = 0
        processing_details = []

        # 各人物データを処理
        for key, person in data.items():
            try:
                # PersonInfoオブジェクトに変換
                person_info = self.process_person_data(person)

                # 短縮名を生成
                display_name = self.shortener.generate_short_name(person_info)

                # 元のデータに短縮名を追加
                person['display_name_ja'] = display_name

                # ログに記録
                processed_entries += 1
                display_names_generated += 1

                processing_details.append({
                    'id': key,
                    'original_name': person_info.name,
                    'occupation': person_info.occupation,
                    'estimated_age': person_info.age,
                    'estimated_gender': person_info.gender,
                    'display_name': display_name
                })

            except Exception as e:
                print(f"⚠️ エラー: {key} - {e}")
                # エラーが発生した場合は元の名前を使用
                person['display_name_ja'] = person.get('name', '')

        # 処理後のデータを保存
        output_path = Path(output_file)
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 処理ログを保存
        process_log = {
            'total_entries': total_entries,
            'processed_entries': processed_entries,
            'display_names_generated': display_names_generated,
            'processing_details': processing_details,
            'timestamp': datetime.now().isoformat()
        }

        log_file = output_path.parent / f"{output_path.stem}_display_names_log.json"
        with log_file.open('w', encoding='utf-8') as f:
            json.dump(process_log, f, ensure_ascii=False, indent=2)

        return process_log


def main() -> None:
    """メイン処理"""
    generator = DisplayNameGenerator()

    input_file = 'final_12410_safe_processed.json'
    output_file = 'final_12410_with_display_names.json'

    try:
        # 表示用短縮名を生成
        process_log = generator.generate_display_names(input_file, output_file)

        print(f"\n✅ 表示用短縮名の生成完了: {output_file}")
        print("📊 処理結果:")
        print(f"  総エントリ数: {process_log['total_entries']}")
        print(f"  処理されたエントリ: {process_log['processed_entries']}")
        print(f"  生成された短縮名: {process_log['display_names_generated']}")

        # 処理例を表示
        if process_log['processing_details']:
            print("\n📝 生成例（最初の10件）:")
            for detail in process_log['processing_details'][:10]:
                print(f"  {detail['original_name']} → {detail['display_name']}")
                print(f"    職業: {detail['occupation']}")
                print(f"    推定年齢: {detail['estimated_age']}歳")
                print(f"    推定性別: {detail['estimated_gender']}")
                print()

        print("🔤 これで日本語表示用の短縮名が利用可能になりました")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
