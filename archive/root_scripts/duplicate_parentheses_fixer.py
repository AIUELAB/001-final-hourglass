#!/usr/bin/env python3
"""
重複括弧修正スクリプト
P000399（カジサック）のような "名前 (名前)" パターンを修正

作成日: 2025-08-30
問題: person_name_displayフィールドで名前が括弧内で重複している
解決策: 重複パターンを検出して修正
"""

import pandas as pd
import re
from datetime import datetime
import json
from pathlib import Path

def detect_duplicate_parentheses(df):
    """重複括弧パターンを検出"""
    duplicates = []
    pattern = re.compile(r'^([^(]+)\s*\(\1\)$')

    for idx, row in df.iterrows():
        display_name = str(row.get('person_name_display', ''))
        if pd.notna(display_name) and display_name:
            match = pattern.match(display_name.strip())
            if match:
                duplicates.append({
                    'index': idx,
                    'person_id': row.get('person_id', ''),
                    'person_name': row.get('person_name', ''),
                    'person_name_ja': row.get('person_name_ja', ''),
                    'current_display': display_name,
                    'base_name': match.group(1).strip(),
                    'fixed_display': match.group(1).strip()
                })

    return duplicates

def fix_duplicate_parentheses(df, duplicates):
    """重複括弧を修正"""
    fixed_count = 0
    fix_log = []

    for dup in duplicates:
        idx = dup['index']
        old_value = df.at[idx, 'person_name_display']
        new_value = dup['fixed_display']

        df.at[idx, 'person_name_display'] = new_value
        fixed_count += 1

        fix_log.append({
            'person_id': dup['person_id'],
            'before': old_value,
            'after': new_value,
            'timestamp': datetime.now().isoformat()
        })

        print(f"✅ 修正: {dup['person_id']} - '{old_value}' → '{new_value}'")

    return df, fixed_count, fix_log

def detect_other_issues(df):
    """その他の問題パターンを検出"""
    issues = {
        'double_parentheses': [],  # ((名前)) パターン
        'empty_parentheses': [],   # 名前 () パターン
        'nested_parentheses': [],  # 名前 ((内容)) パターン
        'multiple_parentheses': []  # 名前 (A) (B) パターン
    }

    for idx, row in df.iterrows():
        display_name = str(row.get('person_name_display', ''))
        if pd.notna(display_name) and display_name:
            person_id = row.get('person_id', '')

            # 二重括弧
            if '((' in display_name or '))' in display_name:
                issues['double_parentheses'].append({
                    'person_id': person_id,
                    'display_name': display_name
                })

            # 空括弧
            if '()' in display_name:
                issues['empty_parentheses'].append({
                    'person_id': person_id,
                    'display_name': display_name
                })

            # 複数括弧
            paren_count = display_name.count('(')
            if paren_count > 1:
                issues['multiple_parentheses'].append({
                    'person_id': person_id,
                    'display_name': display_name,
                    'count': paren_count
                })

    return issues

def main():
    """メイン処理"""
    print("=" * 60)
    print("🔧 重複括弧修正スクリプト開始")
    print("=" * 60)

    # CSVファイルの読み込み
    csv_file = 'ultra_think_FINAL_CLEAN_20250829_220113.csv'
    print(f"\n📂 ファイル読み込み: {csv_file}")

    df = pd.read_csv(csv_file)
    print(f"✅ 読み込み完了: {len(df)}件のレコード")

    # 重複括弧の検出
    print("\n🔍 重複括弧パターンの検出中...")
    duplicates = detect_duplicate_parentheses(df)

    if duplicates:
        print(f"\n⚠️  {len(duplicates)}件の重複括弧パターンを発見:")
        for dup in duplicates:
            print(f"  - {dup['person_id']}: '{dup['current_display']}'")

        # 修正実行
        print("\n🛠️  修正を実行中...")
        df, fixed_count, fix_log = fix_duplicate_parentheses(df, duplicates)

        # 修正結果を保存
        output_file = f'ultra_think_DUPLICATE_FIXED_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(output_file, index=False)
        print(f"\n💾 修正済みファイル保存: {output_file}")

        # ログファイル保存
        log_file = f'duplicate_fix_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_records': len(df),
                    'duplicates_found': len(duplicates),
                    'duplicates_fixed': fixed_count,
                    'timestamp': datetime.now().isoformat()
                },
                'fixes': fix_log
            }, f, ensure_ascii=False, indent=2)
        print(f"📝 修正ログ保存: {log_file}")
    else:
        print("✅ 重複括弧パターンは見つかりませんでした")

    # その他の問題検出
    print("\n🔍 その他の問題パターンを検出中...")
    issues = detect_other_issues(df)

    issue_count = sum(len(v) for v in issues.values())
    if issue_count > 0:
        print(f"\n⚠️  {issue_count}件のその他の問題を発見:")
        for issue_type, items in issues.items():
            if items:
                print(f"  - {issue_type}: {len(items)}件")
                for item in items[:3]:  # 最初の3件を表示
                    print(f"    • {item['person_id']}: {item['display_name']}")
                if len(items) > 3:
                    print(f"    ... 他 {len(items) - 3}件")

    print("\n" + "=" * 60)
    print("✅ 重複括弧修正スクリプト完了")
    print("=" * 60)

    # 修正サマリー
    if duplicates:
        print("\n📊 修正サマリー:")
        print(f"  - 検出された重複: {len(duplicates)}件")
        print(f"  - 修正完了: {fixed_count}件")
        print(f"  - 出力ファイル: {output_file}")

        # 最も重要な修正を表示
        if any(d['person_id'] == 'P000399' for d in duplicates):
            print("\n🎯 P000399（カジサック）の修正: 完了 ✅")

if __name__ == "__main__":
    main()
