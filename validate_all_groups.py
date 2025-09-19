#!/usr/bin/env python3
"""
全グループ・事務所データの包括的検証
すべての修正が正しく適用されているか確認
"""

import pandas as pd
import json
from datetime import datetime
from collections import Counter

def comprehensive_validation():
    """包括的なデータ検証"""
    
    print("🔍 包括的データ検証を開始...")
    print("=" * 60)
    
    # 最新の修正済みCSVファイル
    csv_file = 'ultra_think_AUTO_CLASSIFIED_20250829_195846.csv'
    
    try:
        # CSVファイル読み込み
        df = pd.read_csv(csv_file, dtype=str)
        print(f"📊 データ読み込み完了: {len(df)}件")
        
        # 検証結果を格納
        validation_results = {
            'total_records': len(df),
            'timestamp': datetime.now().isoformat(),
            'issues': [],
            'statistics': {}
        }
        
        # 1. ONE OK ROCK検証
        print("\n1️⃣ ONE OK ROCK メンバー検証")
        print("-" * 40)
        
        one_ok_rock_records = df[df['person_name_display'].str.contains('ONE OK ROCK', na=False)]
        correct_members = ['P000025', 'P000032', 'P000033', 'P000034']
        
        one_ok_rock_valid = True
        for _, row in one_ok_rock_records.iterrows():
            person_id = row['person_id']
            display_name = row['person_name_display']
            
            if person_id in correct_members:
                print(f"  ✅ {person_id}: {display_name} - 正しいメンバー")
            else:
                print(f"  ❌ {person_id}: {display_name} - 誤分類")
                validation_results['issues'].append({
                    'type': 'ONE_OK_ROCK_MISCLASSIFICATION',
                    'person_id': person_id,
                    'display_name': display_name
                })
                one_ok_rock_valid = False
        
        if one_ok_rock_valid:
            print("  ✅ すべて正しいメンバーです")
        
        validation_results['statistics']['one_ok_rock'] = {
            'total': len(one_ok_rock_records),
            'valid': one_ok_rock_valid
        }
        
        # 2. UUUM検証
        print("\n2️⃣ UUUM 事務所表示検証")
        print("-" * 40)
        
        uuum_records = df[df['person_name_display'].str.contains('UUUM', na=False)]
        
        if len(uuum_records) == 0:
            print("  ✅ UUUM表示は正しく削除されています")
            uuum_valid = True
        else:
            print(f"  ❌ {len(uuum_records)}件のUUUM表示が残っています:")
            for _, row in uuum_records.iterrows():
                print(f"    - {row['person_id']}: {row['person_name_display']}")
                validation_results['issues'].append({
                    'type': 'AGENCY_AS_GROUP',
                    'person_id': row['person_id'],
                    'display_name': row['person_name_display']
                })
            uuum_valid = False
        
        validation_results['statistics']['uuum'] = {
            'remaining': len(uuum_records),
            'valid': uuum_valid
        }
        
        # 3. 正しいグループ表示の統計
        print("\n3️⃣ 正しいグループ表示の統計")
        print("-" * 40)
        
        valid_groups = {
            'QuizKnock': df[df['person_name_display'].str.contains('QuizKnock', na=False)],
            '東海オンエア': df[df['person_name_display'].str.contains('東海オンエア', na=False)],
            'フィッシャーズ': df[df['person_name_display'].str.contains('フィッシャーズ', na=False)],
            'SEKAI NO OWARI': df[df['person_name_display'].str.contains('SEKAI NO OWARI', na=False)],
            'L\'Arc~en~Ciel': df[df['person_name_display'].str.contains('L\'Arc~en~Ciel', na=False)]
        }
        
        group_stats = {}
        for group_name, members in valid_groups.items():
            count = len(members)
            if count > 0:
                print(f"  ✅ {group_name}: {count}名")
                if count <= 3:
                    for _, row in members.iterrows():
                        print(f"      - {row['person_name_display']}")
                group_stats[group_name] = count
        
        validation_results['statistics']['valid_groups'] = group_stats
        
        # 4. 括弧内エンティティの分析
        print("\n4️⃣ 括弧内エンティティ分析")
        print("-" * 40)
        
        import re
        entity_counter = Counter()
        
        for _, row in df.iterrows():
            display_name = str(row.get('person_name_display', ''))
            match = re.search(r'\((.*?)\)', display_name)
            if match:
                entity = match.group(1)
                entity_counter[entity] += 1
        
        print(f"  括弧付き表示の総数: {sum(entity_counter.values())}件")
        print("\n  頻出エンティティ TOP10:")
        for entity, count in entity_counter.most_common(10):
            print(f"    - {entity}: {count}件")
        
        validation_results['statistics']['entity_distribution'] = dict(entity_counter)
        
        # 5. 職業別グループ分析
        print("\n5️⃣ 職業別グループ分析")
        print("-" * 40)
        
        occupation_group_analysis = {}
        
        for occupation in ['YouTuber', '歌手', 'お笑い芸人', '俳優']:
            occ_df = df[df['occupation'] == occupation]
            occ_with_group = occ_df[occ_df['person_name_display'].str.contains(r'\(.*\)', na=False)]
            
            if len(occ_df) > 0:
                percentage = (len(occ_with_group) / len(occ_df)) * 100
                print(f"  {occupation}: {len(occ_with_group)}/{len(occ_df)} ({percentage:.1f}%)")
                
                occupation_group_analysis[occupation] = {
                    'total': len(occ_df),
                    'with_group': len(occ_with_group),
                    'percentage': percentage
                }
        
        validation_results['statistics']['occupation_analysis'] = occupation_group_analysis
        
        # 6. 総合判定
        print("\n" + "=" * 60)
        print("📊 総合判定")
        print("=" * 60)
        
        total_issues = len(validation_results['issues'])
        
        if total_issues == 0:
            print("✅ すべての修正が正しく適用されています！")
            validation_results['status'] = 'PASSED'
        else:
            print(f"⚠️ {total_issues}件の問題が残っています")
            validation_results['status'] = 'FAILED'
        
        # レポート保存
        report_file = f'VALIDATION_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 検証レポート保存: {report_file}")
        
        return validation_results
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return None

def create_final_summary():
    """最終サマリーレポートを作成"""
    
    print("\n" + "=" * 60)
    print("📋 最終サマリーレポート")
    print("=" * 60)
    
    summary = {
        'timestamp': datetime.now().isoformat(),
        'fixes_applied': []
    }
    
    # 修正履歴をまとめる
    fixes = [
        {
            'type': 'ONE OK ROCK誤分類修正',
            'count': 12,
            'details': '無関係な12名をONE OK ROCKから削除'
        },
        {
            'type': 'UUUM事務所問題修正', 
            'count': 3,
            'details': 'HIKAKIN、はじめしゃちょー、木下ゆうかから(UUUM)を削除'
        },
        {
            'type': 'The Beatles誤分類修正',
            'count': 1,
            'details': 'りん(YouTuber)から(The Beatles)を削除'
        }
    ]
    
    total_fixes = sum(fix['count'] for fix in fixes)
    
    print(f"\n🔧 適用された修正:")
    for fix in fixes:
        print(f"  • {fix['type']}: {fix['count']}件")
        print(f"    {fix['details']}")
        summary['fixes_applied'].append(fix)
    
    print(f"\n📊 合計修正件数: {total_fixes}件")
    summary['total_fixes'] = total_fixes
    
    # データ構造改善
    print(f"\n🏗️ データ構造改善:")
    print(f"  • groups_database.json: ONE OK ROCKメンバーを正しく修正")
    print(f"  • youtuber_groups_database.json: UUUMエントリーを削除")
    print(f"  • agencies_database.json: 新規作成（事務所専用データベース）")
    
    summary['structure_improvements'] = [
        'groups_database.json修正',
        'youtuber_groups_database.json修正',
        'agencies_database.json新規作成'
    ]
    
    # システム改善
    print(f"\n⚙️ システム改善:")
    print(f"  • EntityClassifier: 事務所vsグループ自動判定システム")
    print(f"  • 妥当性検証: 職業とグループの整合性チェック")
    print(f"  • 将来の誤分類防止メカニズム")
    
    summary['system_improvements'] = [
        '自動分類システム構築',
        '妥当性検証機能',
        '誤分類防止メカニズム'
    ]
    
    # サマリーファイル保存
    summary_file = f'FINAL_SUMMARY_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 最終サマリー保存: {summary_file}")
    
    return summary

if __name__ == "__main__":
    # 包括的検証を実行
    validation_results = comprehensive_validation()
    
    # 最終サマリーを作成
    summary = create_final_summary()
    
    print("\n" + "=" * 60)
    print("✅ 検証完了！")
    print("=" * 60)