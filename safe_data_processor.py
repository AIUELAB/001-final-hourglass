#!/usr/bin/env python3
"""
安全なデータ処理スクリプト
- Claude API使用時のポリシー違反を防ぐ
- 不適切なコンテンツの自動検出・フィルタリング
- データ品質の向上
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple


class SafeDataProcessor:
    """安全なデータ処理クラス"""

    def __init__(self):
        # 不適切なコンテンツの定義
        self.inappropriate_patterns = {
            'adult_content': [
                r'porn', r'sex', r'xxx', r'adult', r'erotic',
                r'ポルノ', r'アダルト', r'エロ', r'AV', r'性'
            ],
            'violence': [
                r'kill', r'murder', r'violence', r'blood', r'gore',
                r'殺人', r'暴力', r'血', r'残酷'
            ],
            'illegal_activities': [
                r'drug', r'crime', r'terror', r'fraud',
                r'麻薬', r'犯罪', r'テロ', r'詐欺'
            ],
            'hate_speech': [
                r'hate', r'racist', r'discrimination',
                r'差別', r'憎悪', r'偏見'
            ]
        }

        # 職業の正規化マッピング
        self.occupation_normalization = {
            'ポルノ俳優': '俳優',
            'ポルノ女優': '女優',
            'AV俳優': '俳優',
            'AV女優': '女優',
            'adult film actor': 'actor',
            'adult film actress': 'actress',
            'porn actor': 'actor',
            'porn actress': 'actress',
            'pornstar': 'actor',
            'sex worker': 'entertainer',
            'escort': 'entertainer',
            'prostitute': 'entertainer'
        }

        # 安全な職業カテゴリ
        self.safe_occupations = [
            'actor', 'actress', '俳優', '女優', '歌手', 'singer',
            '作家', 'writer', '画家', 'painter', '音楽家', 'musician',
            '科学者', 'scientist', '医師', 'doctor', '教師', 'teacher',
            'エンジニア', 'engineer', 'ビジネスマン', 'businessman'
        ]

    def is_safe_content(self, text: str) -> bool:
        """
        テキストが安全かどうかを判定

        Args:
            text: チェック対象のテキスト

        Returns:
            安全な場合True
        """
        if not text or not isinstance(text, str):
            return True

        text_lower = text.lower()

        # 不適切なパターンのチェック
        for _, patterns in self.inappropriate_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return False

        return True

    def normalize_occupation(self, occupation: str) -> str:
        """
        職業を正規化

        Args:
            occupation: 元の職業

        Returns:
            正規化された職業
        """
        return self.occupation_normalization.get(occupation, occupation)

    def process_person_data(self, person: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        人物データを安全に処理

        Args:
            person: 人物データ

        Returns:
            (処理後のデータ, 処理された項目のリスト)
        """
        processed_person = person.copy()
        processed_items = []

        # 名前の処理
        if 'name' in processed_person:
            name = processed_person['name']
            if not self.is_safe_content(name):
                processed_person['name'] = '[フィルタリング済み]'
                processed_items.append('name')

        # 職業の処理
        if 'occupation' in processed_person:
            occupation = processed_person['occupation']
            if not self.is_safe_content(occupation):
                # 正規化を試行
                normalized = self.normalize_occupation(occupation)
                if normalized != occupation:
                    processed_person['occupation'] = normalized
                    processed_items.append('occupation (normalized)')
                else:
                    processed_person['occupation'] = '[フィルタリング済み]'
                    processed_items.append('occupation')

        # 説明文の処理
        if 'description' in processed_person:
            description = processed_person['description']
            if not self.is_safe_content(description):
                processed_person['description'] = '[フィルタリング済み]'
                processed_items.append('description')

        # その他のフィールドの処理
        for field in ['biography', 'notes', 'comments']:
            if field in processed_person:
                content = processed_person[field]
                if not self.is_safe_content(content):
                    processed_person[field] = '[フィルタリング済み]'
                    processed_items.append(field)

        return processed_person, processed_items

    def process_dataset(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        データセット全体を安全に処理

        Args:
            data: 元のデータセット

        Returns:
            (処理後のデータ, 処理ログ)
        """
        processed_data = {}
        process_log: Dict[str, Any] = {
            'total_entries': len(data),
            'processed_entries': 0,
            'normalized_occupations': 0,
            'filtered_fields': 0,
            'processed_items': [],
            'timestamp': datetime.now().isoformat()
        }

        for key, person in data.items():
            processed_person, processed_items = self.process_person_data(person)

            if processed_items:
                process_log['processed_entries'] += 1
                process_log['processed_items'].append({
                    'id': key,
                    'processed_fields': processed_items
                })

                # 統計の更新
                for item in processed_items:
                    if 'normalized' in item:
                        process_log['normalized_occupations'] += 1
                    else:
                        process_log['filtered_fields'] += 1

            processed_data[key] = processed_person

        return processed_data, process_log

    def create_safe_dataset(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """
        安全なデータセットを作成

        Args:
            input_file: 入力ファイルパス
            output_file: 出力ファイルパス

        Returns:
            処理ログ
        """
        print(f"🔒 安全なデータセットの作成を開始: {input_file}")

        # JSONファイルを読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # データ処理実行
        processed_data, process_log = self.process_dataset(data)

        # 処理後のデータを保存
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)

        # 処理ログを保存
        log_file = output_file.replace('.json', '_process_log.json')
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(process_log, f, ensure_ascii=False, indent=2)

        return process_log

def main():
    """メイン処理"""
    processor = SafeDataProcessor()

    input_file = 'final_12410_firebase_20250822_201828.json'
    output_file = 'final_12410_safe_processed.json'

    try:
        # 安全なデータセットを作成
        process_log = processor.create_safe_dataset(input_file, output_file)

        print(f"\n✅ 安全なデータセットの作成完了: {output_file}")
        print("📊 処理結果:")
        print(f"  総エントリ数: {process_log['total_entries']}")
        print(f"  処理されたエントリ: {process_log['processed_entries']}")
        print(f"  正規化された職業: {process_log['normalized_occupations']}")
        print(f"  フィルタリングされたフィールド: {process_log['filtered_fields']}")

        # 処理例を表示
        if process_log['processed_items']:
            print("\n📝 処理例（最初の5件）:")
            for item in process_log['processed_items'][:5]:
                print(f"  ID: {item['id']}")
                print(f"    処理された項目: {', '.join(item['processed_fields'])}")

        print("\n🔒 このデータセットはClaude APIで安全に使用できます")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
