#!/usr/bin/env python3
"""
破損データと不適切なコンテンツのクリーンアップ
- 破損した名前の検出・修正
- 不適切なコンテンツのフィルタリング
- Claude API使用時のポリシー違反を防ぐ
"""

import json
import re
import shutil
from datetime import datetime

# 定数定義
FILTERED_PLACEHOLDER = '[フィルタリング済み]'
CORRUPTED_NAME_PLACEHOLDER = '[名前不明]'

def is_corrupted_name(name: str) -> bool:
    """
    名前が破損しているかどうかを判定

    Args:
        name: チェック対象の名前

    Returns:
        破損している場合True
    """
    if not name:
        return True

    # 破損パターン
    corrupted_patterns = [
        r'^[^\w\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+$',  # 特殊文字のみ
        r'^[()\[\]{}\.\s]+$',  # 括弧や記号のみ
        r'^[a-zA-Z]{1,2}$',  # 1-2文字の英字のみ
        r'^[0-9]+$',  # 数字のみ
        r'^[^\w\s]+$',  # 文字や空白以外のみ
    ]

    for pattern in corrupted_patterns:
        if re.match(pattern, name):
            return True

    return False

def is_inappropriate_content(text: str) -> bool:
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

    # 不適切な職業カテゴリ
    inappropriate_occupations = [
        'ポルノ俳優', 'ポルノ女優', 'AV俳優', 'AV女優',
        'adult film actor', 'adult film actress', 'porn actor', 'porn actress',
        'sex worker', 'escort', 'prostitute', 'pornstar'
    ]

    # 不適切な名前パターン
    inappropriate_patterns = [
        r'fuck', r'shit', r'porn', r'sex', r'xxx',
        r'アダルト', r'エロ', r'ポルノ'
    ]

    # 不適切な職業のチェック
    for occupation in inappropriate_occupations:
        if occupation.lower() in text_lower:
            return True

    # 不適切な名前パターンのチェック
    for pattern in inappropriate_patterns:
        if re.search(pattern, text_lower):
            return True

    return False

def normalize_occupation(occupation: str) -> str:
    """
    職業を正規化（不適切な表現を適切な表現に変更）

    Args:
        occupation: 元の職業

    Returns:
        正規化された職業
    """
    normalization_map = {
        'ポルノ俳優': '俳優',
        'ポルノ女優': '女優',
        'AV俳優': '俳優',
        'AV女優': '女優',
        'adult film actor': 'actor',
        'adult film actress': 'actress',
        'porn actor': 'actor',
        'porn actress': 'actress',
        'pornstar': 'actor'
    }

    return normalization_map.get(occupation, occupation)

def cleanup_person_data(person: dict) -> tuple[dict, list[str]]:
    """
    人物データをクリーンアップ

    Args:
        person: 人物データの辞書

    Returns:
        (クリーンアップ後のデータ, クリーンアップされた項目のリスト)
    """
    cleaned_person = person.copy()
    cleaned_items = []

    # 名前のクリーンアップ
    if 'name' in cleaned_person:
        name = cleaned_person['name']

        # 破損した名前の処理
        if is_corrupted_name(name):
            cleaned_person['name'] = CORRUPTED_NAME_PLACEHOLDER
            cleaned_items.append('name (corrupted)')

        # 不適切なコンテンツの処理
        elif is_inappropriate_content(name):
            cleaned_person['name'] = FILTERED_PLACEHOLDER
            cleaned_items.append('name (inappropriate)')

    # 職業のクリーンアップ
    if 'occupation' in cleaned_person:
        occupation = cleaned_person['occupation']

        if is_inappropriate_content(occupation):
            # 職業を正規化
            normalized = normalize_occupation(occupation)
            if normalized != occupation:
                cleaned_person['occupation'] = normalized
                cleaned_items.append('occupation (normalized)')
            else:
                cleaned_person['occupation'] = FILTERED_PLACEHOLDER
                cleaned_items.append('occupation')

    # 説明文のクリーンアップ
    if 'description' in cleaned_person:
        description = cleaned_person['description']

        if is_inappropriate_content(description):
            cleaned_person['description'] = FILTERED_PLACEHOLDER
            cleaned_items.append('description')

    return cleaned_person, cleaned_items

def main():
    """メイン処理"""
    input_file = 'final_12410_firebase_20250822_201828.json'

    # バックアップを作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'final_12410_cleanup_backup_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")

    # JSONファイルを読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📊 データ件数: {len(data)}")

    # クリーンアップ対象を収集
    cleaned_entries = []
    corrupted_names = []
    inappropriate_content = []

    for key, person in data.items():
        cleaned_person, cleaned_items = cleanup_person_data(person)

        if cleaned_items:
            cleaned_entries.append({
                'id': key,
                'cleaned_fields': cleaned_items
            })

            # 破損した名前の記録
            if any('corrupted' in item for item in cleaned_items):
                corrupted_names.append(key)

            # 不適切なコンテンツの記録
            if any('inappropriate' in item or 'normalized' in item for item in cleaned_items):
                inappropriate_content.append(key)

        data[key] = cleaned_person

    # 結果を保存
    output_file = f'final_12410_cleaned_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # クリーンアップログを保存
    log_file = f'cleanup_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_entries': len(data),
            'cleaned_entries': len(cleaned_entries),
            'corrupted_names': len(corrupted_names),
            'inappropriate_content': len(inappropriate_content),
            'cleaned_entries_detail': cleaned_entries,
            'corrupted_names_list': corrupted_names,
            'inappropriate_content_list': inappropriate_content,
            'timestamp': timestamp
        }, f, ensure_ascii=False, indent=2)

    # 結果を表示
    print("\n🔧 クリーンアップ結果:")
    print(f"  クリーンアップされたエントリ: {len(cleaned_entries)}件")
    print(f"  破損した名前: {len(corrupted_names)}件")
    print(f"  不適切なコンテンツ: {len(inappropriate_content)}件")

    print(f"\n✅ 出力ファイル: {output_file}")
    print(f"✅ クリーンアップログ: {log_file}")

    # 破損した名前の例を表示
    if corrupted_names:
        print("\n⚠️ 破損した名前の例（最初の5件）:")
        for key in corrupted_names[:5]:
            person = data[key]
            print(f"  ID: {key}")
            print(f"    名前: {person.get('name', 'N/A')}")
            print(f"    職業: {person.get('occupation', 'N/A')}")

    # 不適切なコンテンツの例を表示
    if inappropriate_content:
        print("\n🔒 不適切なコンテンツの例（最初の5件）:")
        for key in inappropriate_content[:5]:
            person = data[key]
            print(f"  ID: {key}")
            print(f"    名前: {person.get('name', 'N/A')}")
            print(f"    職業: {person.get('occupation', 'N/A')}")

    # 元のファイルを更新
    shutil.copy2(output_file, input_file)
    print(f"\n✅ 元のファイルを更新しました: {input_file}")

if __name__ == "__main__":
    main()
