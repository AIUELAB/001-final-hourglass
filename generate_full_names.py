#!/usr/bin/env python3
"""
person_name_ja用のフルネーム表記生成
- 敬称なしのフルネーム表記
- 客観性と一貫性を重視
- データベースへの反映
"""

import json
from datetime import datetime
from typing import Any

from objective_name_shortener import ObjectiveNameShortener, PersonInfo


class FullNameGenerator:
    """フルネーム表記生成クラス"""

    def __init__(self):
        self.shortener = ObjectiveNameShortener()

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

        return PersonInfo(
            name=name,
            occupation=occupation
        )

    def generate_full_names(self, input_file: str, output_file: str) -> dict[str, Any]:
        """
        フルネーム表記を生成

        Args:
            input_file: 入力ファイルパス
            output_file: 出力ファイルパス
        """
        print(f"🔤 person_name_ja用フルネーム表記の生成を開始: {input_file}")

        # JSONファイルを読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 処理ログ
        total_entries = len(data)
        processed_entries = 0
        full_names_generated = 0
        processing_details = []

        # 各人物データを処理
        for key, person in data.items():
            try:
                # PersonInfoオブジェクトに変換
                person_info = self.process_person_data(person)

                # フルネーム表記を生成（defaultパターン）
                full_name = self.shortener.generate_objective_name(person_info, 'default')

                # 元のデータにperson_name_jaを追加
                person['person_name_ja'] = full_name

                # ログに記録
                processed_entries += 1
                full_names_generated += 1

                processing_details.append({
                    'id': key,
                    'original_name': person_info.name,
                    'occupation': person_info.occupation,
                    'person_name_ja': full_name
                })

            except Exception as e:
                print(f"⚠️ エラー: {key} - {e}")
                # エラーが発生した場合は元の名前を使用
                person['person_name_ja'] = person.get('name', '')

        # 処理後のデータを保存
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 処理ログを保存
        process_log = {
            'total_entries': total_entries,
            'processed_entries': processed_entries,
            'full_names_generated': full_names_generated,
            'processing_details': processing_details,
            'timestamp': datetime.now().isoformat()
        }

        log_file = output_file.replace('.json', '_full_names_log.json')
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(process_log, f, ensure_ascii=False, indent=2)

        return process_log

def main():
    """メイン処理"""
    generator = FullNameGenerator()

    input_file = 'final_12410_safe_processed.json'
    output_file = 'final_12410_with_person_name_ja.json'

    try:
        # フルネーム表記を生成
        process_log = generator.generate_full_names(input_file, output_file)

        print(f"\n✅ person_name_ja用フルネーム表記の生成完了: {output_file}")
        print("📊 処理結果:")
        print(f"  総エントリ数: {process_log['total_entries']}")
        print(f"  処理されたエントリ: {process_log['processed_entries']}")
        print(f"  生成されたフルネーム: {process_log['full_names_generated']}")

        # 処理例を表示
        if process_log['processing_details']:
            print("\n📝 生成例（最初の10件）:")
            for detail in process_log['processing_details'][:10]:
                print(f"  {detail['original_name']} → {detail['person_name_ja']}")
                print(f"    職業: {detail['occupation']}")
                print()

        print("🔤 person_name_jaフィールドが正常に生成されました")
        print("🎯 敬称なしのフルネーム表記で客観性を確保")
        print("📋 データベースの一貫性と完全性を重視")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
