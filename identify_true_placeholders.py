#!/usr/bin/env python3
"""
真のプレースホルダー特定スクリプト
Identify True Placeholders Script

このスクリプトは、本当に削除すべきプレースホルダーを特定し、
誤って削除対象になった有名人を保護します。
"""

import pandas as pd
import json
from datetime import datetime
import re

# 有名な歴史的人物のリスト（保護対象）
FAMOUS_HISTORICAL_FIGURES = {
    'カント': {'name_en': 'Immanuel Kant', 'occupation': '哲学者', 'nationality': 'ドイツ'},
    'ガンジー': {'name_en': 'Mahatma Gandhi', 'occupation': '独立運動指導者', 'nationality': 'インド'},
    'ガンディー': {'name_en': 'Mahatma Gandhi', 'occupation': '独立運動指導者', 'nationality': 'インド'},
    'ゲーテ': {'name_en': 'Johann Wolfgang von Goethe', 'occupation': '詩人・作家', 'nationality': 'ドイツ'},
    'シェイクスピア': {'name_en': 'William Shakespeare', 'occupation': '劇作家', 'nationality': 'イギリス'},
    'ジョブズ': {'name_en': 'Steve Jobs', 'occupation': '実業家', 'nationality': 'アメリカ'},
    'セルバンテス': {'name_en': 'Miguel de Cervantes', 'occupation': '作家', 'nationality': 'スペイン'},
    'チンギス・ハーン': {'name_en': 'Genghis Khan', 'occupation': '皇帝', 'nationality': 'モンゴル'},
    'チャールズ・ディケンズ': {'name_en': 'Charles Dickens', 'occupation': '作家', 'nationality': 'イギリス'},
    'パスツール': {'name_en': 'Louis Pasteur', 'occupation': '科学者', 'nationality': 'フランス'},
    'ビリー・ジーン・キング': {'name_en': 'Billie Jean King', 'occupation': 'テニス選手', 'nationality': 'アメリカ'},
    'ファーブル': {'name_en': 'Jean-Henri Fabre', 'occupation': '昆虫学者', 'nationality': 'フランス'},
    'フローレンス・ジョイナー': {'name_en': 'Florence Griffith Joyner', 'occupation': '陸上選手', 'nationality': 'アメリカ'},
    'ポール・ゴーギャン': {'name_en': 'Paul Gauguin', 'occupation': '画家', 'nationality': 'フランス'},
    'マーガレット・コート': {'name_en': 'Margaret Court', 'occupation': 'テニス選手', 'nationality': 'オーストラリア'},
    'ムーミン': {'name_en': 'Moomin', 'occupation': '架空キャラクター', 'nationality': 'フィンランド'},
    'モハメド・アリ': {'name_en': 'Muhammad Ali', 'occupation': 'ボクサー', 'nationality': 'アメリカ'},
    'ローザ・パークス': {'name_en': 'Rosa Parks', 'occupation': '公民権活動家', 'nationality': 'アメリカ'},
    'ロケット': {'name_en': 'George Stephenson', 'occupation': '技術者', 'nationality': 'イギリス'},
    '一休宗純': {'name_en': 'Ikkyu Sojun', 'occupation': '僧侶', 'nationality': '日本'},
    '平賀源内': {'name_en': 'Hiraga Gennai', 'occupation': '発明家', 'nationality': '日本'},
    '本田宗一郎': {'name_en': 'Soichiro Honda', 'occupation': '実業家', 'nationality': '日本'},
    '杉原千畝': {'name_en': 'Chiune Sugihara', 'occupation': '外交官', 'nationality': '日本'},
    '松尾芭蕉': {'name_en': 'Matsuo Basho', 'occupation': '俳人', 'nationality': '日本'}
}

# 明確なプレースホルダーパターン
PLACEHOLDER_PATTERNS = [
    r'^田中太郎',
    r'^山田花子',
    r'^テスト太郎',
    r'^テスト花子',
    r'^Test\s*User',
    r'^Sample\s*Name',
    r'^Dummy',
    r'^Person\s*\d+',
    r'^User\s*\d+',
    r'^Character\s*\d+',
    r'^名前\d+',
    r'^人物\d+',
    r'^仮名',
    r'^名無し',
    r'^Unknown',
    r'^Placeholder',
    r'^Example'
]

def is_true_placeholder(row):
    """
    真のプレースホルダーかどうか判定
    """
    person_name = str(row.get('person_name', ''))
    person_name_display = str(row.get('person_name_display', ''))
    
    # 有名な歴史的人物は保護
    for figure in FAMOUS_HISTORICAL_FIGURES:
        if figure in person_name or figure in person_name_display:
            return False, 'Famous historical figure'
    
    # プレースホルダーパターンチェック
    for pattern in PLACEHOLDER_PATTERNS:
        if re.match(pattern, person_name, re.IGNORECASE) or \
           re.match(pattern, person_name_display, re.IGNORECASE):
            return True, 'Placeholder pattern detected'
    
    # 完全に空の名前
    if (pd.isna(person_name) or person_name.strip() == '') and \
       (pd.isna(person_name_display) or person_name_display.strip() == ''):
        return True, 'Empty name fields'
    
    # 単純すぎる名前（1文字だけ、数字だけなど）
    if len(person_name.strip()) == 1 and not re.match(r'[あ-んア-ン一-龥]', person_name):
        return True, 'Single character name'
    
    if re.match(r'^\d+$', person_name):
        return True, 'Numeric name'
    
    return False, 'Not a placeholder'

def fix_historical_figures(df):
    """
    有名な歴史的人物のデータを修正
    """
    fixed_count = 0
    fix_log = []
    
    for idx, row in df.iterrows():
        person_name = str(row.get('person_name', ''))
        person_name_display = str(row.get('person_name_display', ''))
        
        for figure, info in FAMOUS_HISTORICAL_FIGURES.items():
            if figure in person_name or figure in person_name_display:
                # occupationが不明の場合は修正
                if row['occupation'] == '不明' or pd.isna(row['occupation']):
                    old_occupation = row['occupation']
                    df.loc[idx, 'occupation'] = info['occupation']
                    
                    # nationalityも修正
                    if row['nationality'] == '不明' or pd.isna(row['nationality']):
                        old_nationality = row['nationality']
                        df.loc[idx, 'nationality'] = info['nationality']
                    
                    fixed_count += 1
                    fix_log.append({
                        'person_id': row['person_id'],
                        'person_name': person_name,
                        'old_occupation': old_occupation,
                        'new_occupation': info['occupation'],
                        'new_nationality': info['nationality']
                    })
                break
    
    return df, fixed_count, fix_log

def main():
    print("="*60)
    print("真のプレースホルダー特定")
    print("Identify True Placeholders")
    print("="*60)
    
    # データベース読み込み
    csv_file = 'ultra_think_FICTIONAL_COMPLETE_20250901_005521.csv'
    print(f"\n📂 Loading database: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Total records: {len(df)}")
    
    # まず有名な歴史的人物のデータを修正
    print("\n🔧 Fixing historical figures data...")
    df, fixed_count, fix_log = fix_historical_figures(df)
    print(f"✅ Fixed {fixed_count} historical figures")
    
    if fix_log:
        print("\n📝 Fixed entries:")
        for fix in fix_log[:5]:
            print(f"  {fix['person_id']}: {fix['person_name']}")
            print(f"    Occupation: {fix['old_occupation']} → {fix['new_occupation']}")
        if len(fix_log) > 5:
            print(f"  ... and {len(fix_log) - 5} more")
    
    # 真のプレースホルダーを特定
    print("\n🔍 Identifying true placeholders...")
    
    true_placeholders = []
    protected_entries = []
    
    for idx, row in df.iterrows():
        is_placeholder, reason = is_true_placeholder(row)
        
        if is_placeholder:
            true_placeholders.append({
                'person_id': row['person_id'],
                'person_name': row.get('person_name', ''),
                'person_name_display': row.get('person_name_display', ''),
                'occupation': row.get('occupation', ''),
                'recognition': row.get('name_recognition', 0),
                'reason': reason
            })
        elif row.get('occupation') == '不明' and row.get('name_recognition', 0) < 40:
            # occupationが不明で低認識度だが、有名人でない場合は要確認
            if reason != 'Famous historical figure':
                # 本当に不明な人物の可能性
                true_placeholders.append({
                    'person_id': row['person_id'],
                    'person_name': row.get('person_name', ''),
                    'person_name_display': row.get('person_name_display', ''),
                    'occupation': row.get('occupation', ''),
                    'recognition': row.get('name_recognition', 0),
                    'reason': 'Unknown person with no clear identity'
                })
    
    print(f"\n📊 Results:")
    print(f"  True placeholders found: {len(true_placeholders)}")
    print(f"  Historical figures fixed: {fixed_count}")
    
    # プレースホルダーの詳細表示
    if true_placeholders:
        print("\n🚨 True placeholders to delete:")
        for item in true_placeholders[:10]:
            print(f"  {item['person_id']}: {item['person_name']} - {item['reason']}")
        if len(true_placeholders) > 10:
            print(f"  ... and {len(true_placeholders) - 10} more")
    
    # 修正済みデータベースを保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # データ修正を保存
    if fixed_count > 0:
        fixed_csv = f"ultra_think_HISTORICAL_FIXED_{timestamp}.csv"
        df.to_csv(fixed_csv, index=False, encoding='utf-8')
        print(f"\n💾 Fixed database saved: {fixed_csv}")
    
    # プレースホルダーリストを保存
    placeholder_report = {
        'timestamp': datetime.now().isoformat(),
        'total_placeholders': len(true_placeholders),
        'historical_figures_fixed': fixed_count,
        'placeholder_ids': [p['person_id'] for p in true_placeholders],
        'placeholders': true_placeholders,
        'fix_log': fix_log
    }
    
    report_file = f"true_placeholders_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(placeholder_report, f, ensure_ascii=False, indent=2)
    print(f"📝 Placeholder report saved: {report_file}")
    
    print("\n✅ True placeholder identification completed!")
    print(f"   Recommended deletions: {len(true_placeholders)} records")
    print(f"   Historical figures preserved and fixed: {fixed_count} records")
    
    return df, true_placeholders

if __name__ == "__main__":
    df, placeholders = main()