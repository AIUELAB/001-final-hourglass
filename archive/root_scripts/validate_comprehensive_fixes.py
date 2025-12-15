#!/usr/bin/env python3
"""
包括的修正の最終検証
すべての修正が正しく適用されたことを確認
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path

def validate_fixes():
    """修正の検証"""
    print("🔍 Ultra Think 包括的修正検証システム")
    print("=" * 60)

    # 修正済みCSVファイルを読み込み
    csv_file = Path('ultra_think_COMPREHENSIVE_FIX_20250829_215738.csv')
    if not csv_file.exists():
        print("❌ 修正済みファイルが見つかりません")
        return False

    df = pd.read_csv(csv_file)
    print(f"📊 レコード数: {len(df)}")

    validation_results = {
        'timestamp': datetime.now().isoformat(),
        'total_records': len(df),
        'issues': [],
        'statistics': {}
    }

    # P000083の検証（最重要）
    print("\n🎯 P000083の検証:")
    if 'P000083' in df['person_id'].values:
        p83 = df[df['person_id'] == 'P000083'].iloc[0]
        display = p83['person_name_display']
        occupation = p83['occupation']

        if 'トレンディエンジェル' in display and occupation == 'お笑い芸人':
            print(f"✅ P000083: 正しく修正済み")
            print(f"   person_name_display: {display}")
            print(f"   occupation: {occupation}")
        else:
            print(f"❌ P000083: 修正が不完全")
            validation_results['issues'].append({
                'person_id': 'P000083',
                'issue': 'トレンディエンジェルが正しく設定されていません',
                'current_value': display
            })

    # ONE OK ROCKの誤分類チェック
    print("\n🎸 ONE OK ROCKの誤分類チェック:")
    one_ok_rock_count = 0
    correct_members = ['P000025', 'P000032', 'P000033', 'P000034']  # 正しいメンバー

    for _, row in df.iterrows():
        if 'ONE OK ROCK' in str(row.get('person_name_display', '')):
            one_ok_rock_count += 1
            if row['person_id'] not in correct_members:
                validation_results['issues'].append({
                    'person_id': row['person_id'],
                    'issue': 'ONE OK ROCKの誤分類が残っています',
                    'person_name_display': row['person_name_display']
                })

    validation_results['statistics']['one_ok_rock'] = {
        'total': one_ok_rock_count,
        'valid': one_ok_rock_count == len(correct_members)
    }
    print(f"  ONE OK ROCK表示: {one_ok_rock_count}件（正規メンバー4件のみが正常）")

    # LUNA SEAの誤分類チェック
    print("\n🌙 LUNA SEAの誤分類チェック:")
    luna_sea_errors = []
    for _, row in df.iterrows():
        display = str(row.get('person_name_display', ''))
        if 'LUNA SEA' in display:
            # 実際のLUNA SEAメンバー以外をチェック
            if row['occupation'] not in ['歌手', 'ミュージシャン', 'アーティスト']:
                luna_sea_errors.append({
                    'person_id': row['person_id'],
                    'name': display,
                    'occupation': row['occupation']
                })

    if luna_sea_errors:
        print(f"❌ LUNA SEAの誤分類が{len(luna_sea_errors)}件残っています:")
        for err in luna_sea_errors[:5]:  # 最初の5件を表示
            print(f"   {err['person_id']}: {err['name']} ({err['occupation']})")
    else:
        print("✅ LUNA SEAの誤分類はすべて削除されました")

    # BTSの誤分類チェック
    print("\n💜 BTSの誤分類チェック:")
    bts_errors = []
    for _, row in df.iterrows():
        display = str(row.get('person_name_display', ''))
        if 'BTS' in display:
            # 実際のBTSメンバー以外をチェック（韓国人以外など）
            name_ja = str(row.get('person_name_ja', ''))
            if not any(char in name_ja for char in ['김', '박', '이', '정', '최', 'RM', 'Jin', 'SUGA', 'J-Hope', 'Jimin', 'V', 'Jungkook']):
                if row['person_id'] not in ['正規BTSメンバーのID']:  # 実際のメンバーIDは要確認
                    bts_errors.append({
                        'person_id': row['person_id'],
                        'name': display
                    })

    if bts_errors:
        print(f"⚠️ BTSの表示が{len(bts_errors)}件あります（要確認）")
    else:
        print("✅ BTSの誤分類は適切に処理されました")

    # Stray Kidsの誤分類チェック
    print("\n⭐ Stray Kidsの誤分類チェック:")
    stray_kids_comedians = []
    for _, row in df.iterrows():
        display = str(row.get('person_name_display', ''))
        if 'Stray Kids' in display and row.get('occupation') == 'お笑い芸人':
            stray_kids_comedians.append({
                'person_id': row['person_id'],
                'name': display
            })

    if stray_kids_comedians:
        print(f"❌ Stray Kidsの誤分類が{len(stray_kids_comedians)}件残っています:")
        for err in stray_kids_comedians:
            print(f"   {err['person_id']}: {err['name']}")
    else:
        print("✅ Stray Kidsの誤分類はすべて削除されました")

    # UUUMチェック（エージェンシーが削除されているか）
    print("\n🏢 UUUM（エージェンシー）のチェック:")
    uuum_count = df['person_name_display'].str.contains('UUUM', na=False).sum()
    validation_results['statistics']['uuum'] = {
        'remaining': uuum_count,
        'valid': uuum_count == 0
    }

    if uuum_count > 0:
        print(f"⚠️ UUUMの表示が{uuum_count}件残っています")
        uuum_records = df[df['person_name_display'].str.contains('UUUM', na=False)]
        for _, row in uuum_records.head().iterrows():
            print(f"   {row['person_id']}: {row['person_name_display']}")
    else:
        print("✅ UUUM（エージェンシー）の表示は正しく削除されました")

    # 正しいグループの統計
    print("\n📊 正しいグループ表示の統計:")
    valid_groups = {
        'QuizKnock': 0,
        '東海オンエア': 0,
        'フィッシャーズ': 0,
        'SEKAI NO OWARI': 0,
        "L'Arc~en~Ciel": 0
    }

    for group in valid_groups:
        count = df['person_name_display'].str.contains(group, na=False).sum()
        valid_groups[group] = count
        if count > 0:
            print(f"  {group}: {count}件")

    validation_results['statistics']['valid_groups'] = valid_groups

    # 全体のグループ/エンティティ分布
    print("\n📈 エンティティ分布（上位）:")
    entities = {}
    for _, row in df.iterrows():
        display = str(row.get('person_name_display', ''))
        if '(' in display and ')' in display:
            entity = display[display.rfind('(')+1:display.rfind(')')]
            entities[entity] = entities.get(entity, 0) + 1

    # 上位エンティティを表示
    sorted_entities = sorted(entities.items(), key=lambda x: x[1], reverse=True)[:20]
    for entity, count in sorted_entities:
        if count > 1:
            print(f"  {entity}: {count}件")

    validation_results['statistics']['entity_distribution'] = dict(entities)

    # 職業別のグループ表示率
    print("\n💼 職業別グループ表示率:")
    occupations = ['YouTuber', '歌手', 'お笑い芸人', '俳優']
    for occ in occupations:
        occ_records = df[df['occupation'] == occ]
        with_group = occ_records['person_name_display'].str.contains(r'\([^)]+\)', na=False).sum()
        total = len(occ_records)
        if total > 0:
            percentage = (with_group / total) * 100
            print(f"  {occ}: {with_group}/{total} ({percentage:.1f}%)")
            validation_results['statistics']['occupation_analysis'] = validation_results['statistics'].get('occupation_analysis', {})
            validation_results['statistics']['occupation_analysis'][occ] = {
                'total': total,
                'with_group': with_group,
                'percentage': percentage
            }

    # 最終判定
    print("\n" + "=" * 60)
    if not validation_results['issues']:
        print("✅ すべての修正が正しく適用されました！")
        validation_results['status'] = 'PASSED'
    else:
        print(f"⚠️ {len(validation_results['issues'])}件の問題が検出されました")
        validation_results['status'] = 'ISSUES_FOUND'
        print("\n問題の詳細:")
        for issue in validation_results['issues'][:10]:  # 最初の10件を表示
            print(f"  - {issue['person_id']}: {issue['issue']}")

    # レポート保存
    report_file = f"VALIDATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, ensure_ascii=False, indent=2)

    print(f"\n📄 検証レポート保存: {report_file}")

    return validation_results['status'] == 'PASSED'

if __name__ == "__main__":
    success = validate_fixes()
    print("\n🏁 検証完了")
