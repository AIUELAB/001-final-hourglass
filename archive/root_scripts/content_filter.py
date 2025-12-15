#!/usr/bin/env python3
"""
コンテンツフィルタリング機能
- 不適切な職業やコンテンツを検出・フィルタリング
- Claude API使用時のポリシー違反を防ぐ
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 定数定義
FILTERED_PLACEHOLDER = '[フィルタリング済み]'

class ContentFilter:
    """コンテンツフィルタリングクラス"""

    def __init__(self):
        # 不適切な職業カテゴリ
        self.inappropriate_occupations = {
            'adult_entertainment': [
                'ポルノ俳優', 'ポルノ女優', 'AV俳優', 'AV女優',
                'adult film actor', 'adult film actress', 'porn actor', 'porn actress',
                'sex worker', 'escort', 'prostitute'
            ],
            'illegal_activities': [
                '犯罪者', 'テロリスト', '麻薬密売人', '詐欺師',
                'criminal', 'terrorist', 'drug dealer', 'fraudster'
            ],
            'controversial': [
                '極右活動家', '極左活動家', '過激派',
                'extremist', 'radical', 'militant'
            ]
        }

        # 不適切な名前パターン
        self.inappropriate_name_patterns = [
            r'fuck', r'shit', r'porn', r'sex', r'xxx',
            r'アダルト', r'エロ', r'ポルノ'
        ]

        # 職業の正規化マッピング
        self.occupation_normalization = {
            'ポルノ俳優': '俳優',
            'ポルノ女優': '女優',
            'AV俳優': '俳優',
            'AV女優': '女優',
            'adult film actor': 'actor',
            'adult film actress': 'actress',
            'porn actor': 'actor',
            'porn actress': 'actress'
        }

    def is_inappropriate_content(self, text: str) -> bool:
        """
        テキストが不適切なコンテンツかどうかを判定

        Args:
            text: チェック対象のテキスト

        Returns:
            不適切なコンテンツの場合True
        """
        if not text:
            return False

        text_lower = text.lower()

        # 不適切な職業のチェック
        for _, occupations in self.inappropriate_occupations.items():
            for occupation in occupations:
                if occupation.lower() in text_lower:
                    return True

        # 不適切な名前パターンのチェック
        for pattern in self.inappropriate_name_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def filter_person_data(self, person: Dict) -> Tuple[Dict, List[str]]:
        """
        人物データをフィルタリング

        Args:
            person: 人物データの辞書

        Returns:
            (フィルタリング後のデータ, フィルタリングされた項目のリスト)
        """
        filtered_person = person.copy()
        filtered_items = []

        # 名前のフィルタリング
        if 'name' in filtered_person:
            if self.is_inappropriate_content(filtered_person['name']):
                filtered_person['name'] = FILTERED_PLACEHOLDER
                filtered_items.append('name')

        # 職業のフィルタリング
        if 'occupation' in filtered_person:
            if self.is_inappropriate_content(filtered_person['occupation']):
                # 職業を正規化
                normalized = self.normalize_occupation(filtered_person['occupation'])
                if normalized:
                    filtered_person['occupation'] = normalized
                    filtered_items.append('occupation (normalized)')
                else:
                    filtered_person['occupation'] = FILTERED_PLACEHOLDER
                    filtered_items.append('occupation')

        # 説明文のフィルタリング
        if 'description' in filtered_person:
            if self.is_inappropriate_content(filtered_person['description']):
                filtered_person['description'] = FILTERED_PLACEHOLDER
                filtered_items.append('description')

        return filtered_person, filtered_items

    def normalize_occupation(self, occupation: str) -> Optional[str]:
        """
        職業を正規化

        Args:
            occupation: 元の職業

        Returns:
            正規化された職業、またはNone
        """
        return self.occupation_normalization.get(occupation)

    def filter_dataset(self, data: Dict) -> Tuple[Dict, Dict]:
        """
        データセット全体をフィルタリング

        Args:
            data: 元のデータセット

        Returns:
            (フィルタリング後のデータ, フィルタリングログ)
        """
        filtered_data = {}
        filter_log: Dict[str, Any] = {
            'total_entries': len(data),
            'filtered_entries': 0,
            'filtered_items': [],
            'timestamp': datetime.now().isoformat()
        }

        for key, person in data.items():
            filtered_person, filtered_items = self.filter_person_data(person)

            if filtered_items:
                filter_log['filtered_entries'] += 1
                filter_log['filtered_items'].append({
                    'id': key,
                    'filtered_fields': filtered_items
                })

            filtered_data[key] = filtered_person

        return filtered_data, filter_log

    def create_safe_dataset(self, input_file: str, output_file: str) -> Dict:
        """
        安全なデータセットを作成

        Args:
            input_file: 入力ファイルパス
            output_file: 出力ファイルパス

        Returns:
            フィルタリングログ
        """
        # JSONファイルを読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # フィルタリング実行
        filtered_data, filter_log = self.filter_dataset(data)

        # フィルタリング後のデータを保存
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=2)

        # フィルタリングログを保存
        log_file = output_file.replace('.json', '_filter_log.json')
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(filter_log, f, ensure_ascii=False, indent=2)

        return filter_log

def main():
    """メイン処理"""
    filter_tool = ContentFilter()

    input_file = 'final_12410_firebase_20250822_201828.json'
    output_file = 'final_12410_filtered_safe.json'

    print("🔒 コンテンツフィルタリングを開始します...")

    try:
        filter_log = filter_tool.create_safe_dataset(input_file, output_file)

        print(f"✅ フィルタリング完了: {output_file}")
        print("📊 フィルタリング結果:")
        print(f"  総エントリ数: {filter_log['total_entries']}")
        print(f"  フィルタリングされたエントリ: {filter_log['filtered_entries']}")
        print(f"  フィルタリングされた項目: {len(filter_log['filtered_items'])}")

        if filter_log['filtered_items']:
            print("\n📝 フィルタリング例（最初の5件）:")
            for item in filter_log['filtered_items'][:5]:
                print(f"  ID: {item['id']}")
                print(f"    フィルタリングされた項目: {', '.join(item['filtered_fields'])}")

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
