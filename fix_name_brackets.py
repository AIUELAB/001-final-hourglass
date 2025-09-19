#!/usr/bin/env python3
"""
name欄の括弧付き職業表記を修正
- 括弧内の職業情報を削除して純粋な名前にする
- 括弧内の職業情報をoccupation欄に移動（空欄の場合）
- 不適切なコンテンツをフィルタリング
"""

import json
import re
import shutil
from datetime import datetime


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
        'sex worker', 'escort', 'prostitute'
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
        'porn actress': 'actress'
    }

    return normalization_map.get(occupation, occupation)

def extract_name_and_occupation(name_with_bracket):
    """
    括弧付きの名前から、名前と職業を分離

    Args:
        name_with_bracket: "名前 (職業)" 形式の文字列

    Returns:
        (名前, 職業) のタプル
    """
    match = re.match(r'^(.+?)\s*\((.+?)\)$', name_with_bracket)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return name_with_bracket, None

def main():
    """メイン処理"""
    input_file = 'final_12410_firebase_20250822_201828.json'

    # バックアップを作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'final_12410_brackets_backup_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")

    # JSONファイルを読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 修正対象を収集
    modified_entries = []
    occupation_conflicts = []
    filtered_entries = []

    for key, person in data.items():
        if 'name' in person and '(' in person['name'] and ')' in person['name']:
            original_name = person['name']
            clean_name, bracket_occupation = extract_name_and_occupation(original_name)

            if bracket_occupation:
                # 不適切なコンテンツのチェック
                if is_inappropriate_content(bracket_occupation):
                    # 職業を正規化
                    normalized_occupation = normalize_occupation(bracket_occupation)
                    bracket_occupation = normalized_occupation
                    filtered_entries.append({
                        'id': key,
                        'original_occupation': original_name,
                        'normalized_occupation': normalized_occupation,
                        'action': 'occupation_normalized'
                    })

                current_occupation = person.get('occupation', '')

                # 名前を修正
                person['name'] = clean_name

                # occupation欄の処理
                if not current_occupation:
                    # occupation欄が空の場合は括弧内の職業を設定
                    person['occupation'] = bracket_occupation
                    modified_entries.append({
                        'id': key,
                        'original_name': original_name,
                        'new_name': clean_name,
                        'occupation_added': bracket_occupation,
                        'action': 'occupation_filled'
                    })
                else:
                    # occupation欄に既に値がある場合
                    if current_occupation != bracket_occupation:
                        # 異なる職業が記載されている場合は記録
                        occupation_conflicts.append({
                            'id': key,
                            'name': clean_name,
                            'bracket_occupation': bracket_occupation,
                            'current_occupation': current_occupation
                        })
                    modified_entries.append({
                        'id': key,
                        'original_name': original_name,
                        'new_name': clean_name,
                        'bracket_occupation': bracket_occupation,
                        'kept_occupation': current_occupation,
                        'action': 'name_only'
                    })

    # 結果を保存
    output_file = f'final_12410_brackets_fixed_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 修正ログを保存
    log_file = f'brackets_fix_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'modified_count': len(modified_entries),
            'occupation_filled_count': len([e for e in modified_entries if e['action'] == 'occupation_filled']),
            'name_only_count': len([e for e in modified_entries if e['action'] == 'name_only']),
            'occupation_conflicts': occupation_conflicts,
            'filtered_entries': filtered_entries,
            'filtered_count': len(filtered_entries),
            'modified_entries': modified_entries
        }, f, ensure_ascii=False, indent=2)

    # 結果を表示
    print("\n📊 修正結果:")
    print(f"  修正件数: {len(modified_entries)}")
    print(f"  occupation欄を埋めた: {len([e for e in modified_entries if e['action'] == 'occupation_filled'])}件")
    print(f"  名前のみ修正: {len([e for e in modified_entries if e['action'] == 'name_only'])}件")
    print(f"  職業の不一致: {len(occupation_conflicts)}件")
    print(f"  フィルタリングされた職業: {len(filtered_entries)}件")

    print(f"\n✅ 出力ファイル: {output_file}")
    print(f"✅ 修正ログ: {log_file}")

    # 修正例を表示
    print("\n📝 修正例（最初の5件）:")
    for entry in modified_entries[:5]:
        print(f"  {entry['original_name']} → {entry['new_name']}")
        if entry['action'] == 'occupation_filled':
            print(f"    occupation欄: 空 → {entry['occupation_added']}")

    # フィルタリング例を表示
    if filtered_entries:
        print("\n🔒 フィルタリング例（最初の3件）:")
        for entry in filtered_entries[:3]:
            print(f"  ID: {entry['id']}")
            print(f"    元の職業: {entry['original_occupation']}")
            print(f"    正規化後: {entry['normalized_occupation']}")

    # 職業の不一致例を表示
    if occupation_conflicts:
        print("\n⚠️ 職業の不一致例（最初の3件）:")
        for conflict in occupation_conflicts[:3]:
            print(f"  {conflict['name']}")
            print(f"    括弧内: {conflict['bracket_occupation']}")
            print(f"    occupation欄: {conflict['current_occupation']}")

    # 元のファイルを更新
    shutil.copy2(output_file, input_file)
    print(f"\n✅ 元のファイルを更新しました: {input_file}")

if __name__ == "__main__":
    main()
