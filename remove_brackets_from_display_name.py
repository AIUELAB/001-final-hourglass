#!/usr/bin/env python3
"""
person_name_displayから括弧を削除するスクリプト
元のデータはperson_name_display_originalカラムにバックアップ
"""

import pandas as pd
import re
from datetime import datetime
import json

def remove_brackets(text):
    """
    文字列から括弧とその中身を削除
    全角括弧（）と半角括弧()の両方に対応
    """
    if pd.isna(text):
        return text

    # 全角括弧を削除
    text = re.sub(r'（[^）]*）', '', text)
    # 半角括弧を削除
    text = re.sub(r'\([^)]*\)', '', text)
    # 前後の空白を削除
    return text.strip()

def check_duplicates_after_removal(df, cleaned_names):
    """括弧削除後の重複をチェック"""

    # 重複チェック用のデータフレーム作成
    check_df = pd.DataFrame({
        'original': df['person_name_display'],
        'cleaned': cleaned_names,
        'person_id': df['person_id'],
        'occupation': df['occupation'],
        'group_name': df['group_name']
    })

    # 重複を見つける
    duplicated_cleaned = check_df[check_df.duplicated(subset=['cleaned'], keep=False)]

    if len(duplicated_cleaned) > 0:
        # 重複グループを作成
        duplicate_groups = duplicated_cleaned.groupby('cleaned').apply(
            lambda x: x[['original', 'person_id', 'occupation', 'group_name']].to_dict('records')
        ).to_dict()

        return duplicate_groups

    return {}

def check_short_names(df, cleaned_names):
    """短い名前（1-2文字）をチェック"""

    short_names = []
    for idx, (original, cleaned) in enumerate(zip(df['person_name_display'], cleaned_names)):
        if pd.notna(cleaned) and len(cleaned) <= 2:
            # 括弧が削除されたケースのみ
            if original != cleaned:
                short_names.append({
                    'index': idx,
                    'original': original,
                    'cleaned': cleaned,
                    'person_id': df.iloc[idx]['person_id'],
                    'group_name': df.iloc[idx]['group_name']
                })

    return short_names

def main():
    print("=" * 60)
    print("person_name_display 括弧削除処理")
    print("=" * 60)

    # CSVファイルを読み込み
    input_file = 'ultra_think_with_groups_20250915_130035.csv'
    df = pd.read_csv(input_file)
    print(f"✅ データ読み込み完了: {len(df)}件")

    # 括弧を含む名前の数を確認
    with_brackets = df[df['person_name_display'].str.contains(r'[（(]', na=False, regex=True)]
    print(f"📊 括弧付き名前: {len(with_brackets)}件")

    # person_name_display_originalカラムを追加（バックアップ）
    # group_nameの後に挿入
    columns = list(df.columns)
    group_name_index = columns.index('group_name')
    new_columns = (columns[:group_name_index + 1] +
                  ['person_name_display_original'] +
                  columns[group_name_index + 1:])

    # person_name_displayを複製してバックアップ
    df['person_name_display_original'] = df['person_name_display'].copy()

    # データフレームを再構成
    df = df[new_columns]
    print(f"✅ バックアップカラム追加（person_name_display_original）")

    # 括弧削除処理
    cleaned_names = df['person_name_display'].apply(remove_brackets)

    # 問題チェック
    print("\n📋 データ検証:")

    # 1. 重複チェック
    duplicates = check_duplicates_after_removal(df, cleaned_names)
    if duplicates:
        print(f"\n⚠️ 括弧削除後に重複する名前: {len(duplicates)}グループ")
        for cleaned_name, records in list(duplicates.items())[:5]:
            print(f"\n  '{cleaned_name}':")
            for record in records:
                print(f"    - {record['original']} (ID: {record['person_id']}, グループ: {record['group_name']})")
    else:
        print("✅ 重複なし")

    # 2. 短い名前チェック
    short_names = check_short_names(df, cleaned_names)
    if short_names:
        print(f"\n⚠️ 短い名前（1-2文字）: {len(short_names)}件")
        for item in short_names[:10]:
            print(f"  {item['original']} → {item['cleaned']} (グループ: {item['group_name']})")
    else:
        print("✅ 短い名前の問題なし")

    # cleaned_namesを適用
    df['person_name_display'] = cleaned_names
    print(f"\n✅ 括弧削除完了: {len(with_brackets)}件処理")

    # 統計情報
    print("\n📊 処理結果:")
    print(f"  - 総レコード数: {len(df):,}件")
    print(f"  - 括弧削除: {len(with_brackets):,}件")
    print(f"  - 変更なし: {len(df) - len(with_brackets):,}件")

    # 処理例を表示
    print("\n📝 処理例（最初の5件）:")
    for idx, row in with_brackets.head(5).iterrows():
        original = df.loc[idx, 'person_name_display_original']
        cleaned = df.loc[idx, 'person_name_display']
        group = df.loc[idx, 'group_name']
        print(f"  {original} → {cleaned} (group_name: {group})")

    # 新しいファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_cleaned_names_{timestamp}.csv'

    # UTF-8 BOM付きで保存
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ ファイル保存完了: {output_file}")
    print(f"  - カラム数: {len(df.columns)}")
    print(f"  - person_name_display_originalカラム位置: {new_columns.index('person_name_display_original') + 1}番目（H列）")

    return output_file

if __name__ == "__main__":
    output_file = main()
    print(f"\n完了！出力ファイル: {output_file}")