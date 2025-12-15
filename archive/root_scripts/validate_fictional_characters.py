#!/usr/bin/env python3
"""
架空キャラクター修正検証スクリプト
Validate Fictional Character Fixes
"""

import pandas as pd
import json
from datetime import datetime

def main():
    print("="*60)
    print("架空キャラクター修正検証")
    print("="*60)

    # 修正済みデータベースを読み込み
    csv_file = 'ultra_think_FICTIONAL_FIXED_20250901_005324.csv'
    print(f"\n📂 Loading fixed database: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Total records: {len(df)}")

    # 架空キャラクターの抽出
    fictional_mask = (df['category'] == '架空の存在') | (df['occupation'] == '架空キャラクター')
    fictional_chars = df[fictional_mask].copy()
    print(f"\n🎯 Total fictional characters: {len(fictional_chars)}")

    # 検証結果の初期化
    validation_results = {
        'total_fictional': len(fictional_chars),
        'correct_format': [],
        'missing_work': [],
        'wrong_parentheses': [],
        'issues': []
    }

    # 各キャラクターの検証
    print("\n🔍 Validating all fictional characters...")

    for _, char in fictional_chars.iterrows():
        person_id = char['person_id']
        person_name = char['person_name']
        display = str(char['person_name_display'])

        # 全角括弧で作品名があるか
        if '（' in display and '）' in display:
            validation_results['correct_format'].append({
                'person_id': person_id,
                'person_name': person_name,
                'display': display
            })
        # 半角括弧（修正漏れ）
        elif '(' in display and ')' in display:
            validation_results['wrong_parentheses'].append({
                'person_id': person_id,
                'person_name': person_name,
                'display': display
            })
        # 括弧なし（作品名欠落）
        else:
            validation_results['missing_work'].append({
                'person_id': person_id,
                'person_name': person_name,
                'display': display,
                'nationality': char.get('nationality', '')
            })

    # 特定のキャラクターの詳細確認
    print("\n🎯 Checking specific characters:")

    # P000583 (Sanji)
    sanji = df[df['person_id'] == 'P000583']
    if not sanji.empty:
        s = sanji.iloc[0]
        display = s['person_name_display']
        if 'サンジ（ONE PIECE）' in display:
            print(f"  ✅ P000583 (Sanji): {display}")
        else:
            print(f"  ❌ P000583 (Sanji): {display} - Expected: サンジ（ONE PIECE）")

    # P000813 (Zoro)
    zoro = df[df['person_id'] == 'P000813']
    if not zoro.empty:
        z = zoro.iloc[0]
        display = z['person_name_display']
        if 'ゾロ（ONE PIECE）' in display or 'ロロノア・ゾロ（ONE PIECE）' in display:
            print(f"  ✅ P000813 (Zoro): {display}")
        else:
            print(f"  ❌ P000813 (Zoro): {display}")

    # P000980 (Nami)
    nami = df[df['person_id'] == 'P000980']
    if not nami.empty:
        n = nami.iloc[0]
        display = n['person_name_display']
        if '（ONE PIECE）' in display:
            print(f"  ✅ P000980 (Nami): {display}")
        else:
            print(f"  ❌ P000980 (Nami): {display} - Missing work name!")

    # P001517 (Nico Robin)
    robin = df[df['person_id'] == 'P001517']
    if not robin.empty:
        r = robin.iloc[0]
        display = r['person_name_display']
        if '（ONE PIECE）' in display:
            print(f"  ✅ P001517 (Nico Robin): {display}")
        else:
            print(f"  ❌ P001517 (Nico Robin): {display} - Missing work name!")

    # 結果サマリー
    print(f"\n📊 Validation Summary:")
    print(f"  ✅ Correct format: {len(validation_results['correct_format'])} characters")
    print(f"  ❌ Missing work name: {len(validation_results['missing_work'])} characters")
    print(f"  ⚠️ Wrong parentheses: {len(validation_results['wrong_parentheses'])} characters")

    # 問題があるキャラクターの詳細
    if validation_results['missing_work']:
        print(f"\n🚨 Characters still missing work names:")
        for char in validation_results['missing_work']:
            print(f"  {char['person_id']}: {char['person_name']} - '{char['display']}'")
            if char['nationality'] in ['北の海', 'East Blue', '偉大なる航路']:
                print(f"    → Should be ONE PIECE character")

    if validation_results['wrong_parentheses']:
        print(f"\n⚠️ Characters with wrong parentheses format:")
        for char in validation_results['wrong_parentheses']:
            print(f"  {char['person_id']}: {char['display']}")

    # 成功率の計算
    total = len(fictional_chars)
    correct = len(validation_results['correct_format'])
    success_rate = (correct / total) * 100 if total > 0 else 0

    print(f"\n📈 Success Rate: {success_rate:.1f}% ({correct}/{total})")

    # 検証レポートを保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = {
        'timestamp': datetime.now().isoformat(),
        'database_file': csv_file,
        'validation_results': validation_results,
        'success_rate': success_rate,
        'total_correct': correct,
        'total_issues': len(validation_results['missing_work']) + len(validation_results['wrong_parentheses'])
    }

    report_file = f"fictional_validation_report_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📝 Validation report saved: {report_file}")

    # 最終判定
    if success_rate >= 95:
        print("\n✅ VALIDATION PASSED! Fictional characters are properly formatted.")
        return True, csv_file
    elif success_rate >= 90:
        print("\n⚠️ VALIDATION MOSTLY PASSED with minor issues.")
        return True, csv_file
    else:
        print("\n❌ VALIDATION FAILED! Too many characters still have issues.")
        return False, csv_file

if __name__ == "__main__":
    passed, output_file = main()
    if passed:
        print(f"\n🎉 架空キャラクター表示名の修正が成功しました！")
        print(f"   Output: {output_file}")
    else:
        print(f"\n⚠️ 追加の修正が必要です。")
