#!/usr/bin/env python3
"""
歴史的人物保護・修正スクリプト
Protect and Fix Historical Figures Script

このスクリプトは、有名な歴史的人物を保護し、
誤って削除対象になった人物のデータを修正します。
"""

import pandas as pd
import json
from datetime import datetime

# 拡張版: 有名な歴史的人物のリスト（保護対象）
FAMOUS_HISTORICAL_FIGURES = {
    # 哲学者・思想家
    'カント': {'name_en': 'Immanuel Kant', 'occupation': '哲学者', 'nationality': 'ドイツ', 'recognition': 50},
    'ガンジー': {'name_en': 'Mahatma Gandhi', 'occupation': '独立運動指導者', 'nationality': 'インド', 'recognition': 55},
    'ガンディー': {'name_en': 'Mahatma Gandhi', 'occupation': '独立運動指導者', 'nationality': 'インド', 'recognition': 55},
    
    # 文学・芸術
    'ゲーテ': {'name_en': 'Johann Wolfgang von Goethe', 'occupation': '詩人・作家', 'nationality': 'ドイツ', 'recognition': 50},
    'シェイクスピア': {'name_en': 'William Shakespeare', 'occupation': '劇作家', 'nationality': 'イギリス', 'recognition': 60},
    'セルバンテス': {'name_en': 'Miguel de Cervantes', 'occupation': '作家', 'nationality': 'スペイン', 'recognition': 45},
    'チャールズ・ディケンズ': {'name_en': 'Charles Dickens', 'occupation': '作家', 'nationality': 'イギリス', 'recognition': 45},
    'レンブラント': {'name_en': 'Rembrandt van Rijn', 'occupation': '画家', 'nationality': 'オランダ', 'recognition': 50},
    'ワーグナー': {'name_en': 'Richard Wagner', 'occupation': '作曲家', 'nationality': 'ドイツ', 'recognition': 45},
    'ポール・ゴーギャン': {'name_en': 'Paul Gauguin', 'occupation': '画家', 'nationality': 'フランス', 'recognition': 45},
    
    # 科学者・発明家
    'パスツール': {'name_en': 'Louis Pasteur', 'occupation': '科学者', 'nationality': 'フランス', 'recognition': 50},
    'ファーブル': {'name_en': 'Jean-Henri Fabre', 'occupation': '昆虫学者', 'nationality': 'フランス', 'recognition': 40},
    'フレミング': {'name_en': 'Alexander Fleming', 'occupation': '細菌学者', 'nationality': 'イギリス', 'recognition': 45},
    'ライト兄弟': {'name_en': 'Wright Brothers', 'occupation': '発明家・航空技術者', 'nationality': 'アメリカ', 'recognition': 50},
    '平賀源内': {'name_en': 'Hiraga Gennai', 'occupation': '発明家', 'nationality': '日本', 'recognition': 40},
    
    # 実業家・経済人
    'ジョブズ': {'name_en': 'Steve Jobs', 'occupation': '実業家', 'nationality': 'アメリカ', 'recognition': 55},
    '本田宗一郎': {'name_en': 'Soichiro Honda', 'occupation': '実業家', 'nationality': '日本', 'recognition': 45},
    'ロックフェラー': {'name_en': 'John D. Rockefeller', 'occupation': '実業家', 'nationality': 'アメリカ', 'recognition': 45},
    
    # 歴史上の人物
    'チンギス・ハーン': {'name_en': 'Genghis Khan', 'occupation': '皇帝', 'nationality': 'モンゴル', 'recognition': 50},
    'ムーミン': {'name_en': 'Moomin', 'occupation': '架空キャラクター', 'nationality': 'フィンランド', 'recognition': 40},
    '在原業平': {'name_en': 'Ariwara no Narihira', 'occupation': '歌人', 'nationality': '日本', 'recognition': 40},
    '一休宗純': {'name_en': 'Ikkyu Sojun', 'occupation': '僧侶', 'nationality': '日本', 'recognition': 40},
    '松尾芭蕉': {'name_en': 'Matsuo Basho', 'occupation': '俳人', 'nationality': '日本', 'recognition': 45},
    '杉原千畝': {'name_en': 'Chiune Sugihara', 'occupation': '外交官', 'nationality': '日本', 'recognition': 40},
    
    # スポーツ選手
    'モハメド・アリ': {'name_en': 'Muhammad Ali', 'occupation': 'ボクサー', 'nationality': 'アメリカ', 'recognition': 50},
    'ビリー・ジーン・キング': {'name_en': 'Billie Jean King', 'occupation': 'テニス選手', 'nationality': 'アメリカ', 'recognition': 40},
    'フローレンス・ジョイナー': {'name_en': 'Florence Griffith Joyner', 'occupation': '陸上選手', 'nationality': 'アメリカ', 'recognition': 40},
    'マーガレット・コート': {'name_en': 'Margaret Court', 'occupation': 'テニス選手', 'nationality': 'オーストラリア', 'recognition': 40},
    
    # 公民権活動家・政治家
    'ローザ・パークス': {'name_en': 'Rosa Parks', 'occupation': '公民権活動家', 'nationality': 'アメリカ', 'recognition': 45},
    'マンデラ': {'name_en': 'Nelson Mandela', 'occupation': '政治家・人権活動家', 'nationality': '南アフリカ', 'recognition': 55},
    'ブッカー・T・ワシントン': {'name_en': 'Booker T. Washington', 'occupation': '教育者・公民権運動家', 'nationality': 'アメリカ', 'recognition': 40},
    
    # その他の有名人
    'Helen Keller': {'name_ja': 'ヘレン・ケラー', 'occupation': '作家・教育者', 'nationality': 'アメリカ', 'recognition': 50},
    'ヘレン・ケラー': {'name_en': 'Helen Keller', 'occupation': '作家・教育者', 'nationality': 'アメリカ', 'recognition': 50},
    'ロケット': {'name_en': 'George Stephenson', 'occupation': '技術者', 'nationality': 'イギリス', 'recognition': 40}
}

def fix_all_historical_figures(df):
    """
    すべての歴史的人物のデータを修正
    """
    fixed_count = 0
    fix_log = []
    
    for idx, row in df.iterrows():
        person_name = str(row.get('person_name', ''))
        person_name_display = str(row.get('person_name_display', ''))
        
        # 名前のマッチング（person_nameまたはperson_name_displayで確認）
        matched_figure = None
        for figure, info in FAMOUS_HISTORICAL_FIGURES.items():
            if figure in person_name or figure in person_name_display or \
               person_name in figure or \
               (info.get('name_en') and info['name_en'] == person_name) or \
               (info.get('name_ja') and info['name_ja'] == person_name_display):
                matched_figure = figure
                break
        
        if matched_figure:
            info = FAMOUS_HISTORICAL_FIGURES[matched_figure]
            changes = []
            
            # occupationが不明の場合は修正
            if row['occupation'] == '不明' or pd.isna(row['occupation']):
                old_occupation = row['occupation']
                df.loc[idx, 'occupation'] = info['occupation']
                changes.append(f"occupation: {old_occupation} → {info['occupation']}")
            
            # nationalityが不明の場合は修正
            if row['nationality'] == '不明' or pd.isna(row['nationality']):
                old_nationality = row['nationality']
                df.loc[idx, 'nationality'] = info['nationality']
                changes.append(f"nationality: {old_nationality} → {info['nationality']}")
            
            # recognitionが低い場合は修正
            if row.get('name_recognition', 0) < 40:
                old_recognition = row.get('name_recognition', 0)
                df.loc[idx, 'name_recognition'] = info['recognition']
                changes.append(f"recognition: {old_recognition} → {info['recognition']}")
            
            if changes:
                fixed_count += 1
                fix_log.append({
                    'person_id': row['person_id'],
                    'person_name': person_name,
                    'person_name_display': person_name_display,
                    'changes': changes
                })
    
    return df, fixed_count, fix_log

def identify_true_placeholders(row):
    """
    真のプレースホルダーかどうか判定（改善版）
    """
    person_name = str(row.get('person_name', ''))
    person_name_display = str(row.get('person_name_display', ''))
    
    # 有名な歴史的人物は絶対に保護
    for figure in FAMOUS_HISTORICAL_FIGURES:
        if figure in person_name or figure in person_name_display:
            return False, 'Famous historical figure'
    
    # 明確なプレースホルダーパターン
    placeholder_patterns = [
        '田中太郎', '山田花子', 'テスト太郎', 'テスト花子',
        'Test User', 'Sample Name', 'Dummy', 'Person\\d+',
        'User\\d+', 'Character\\d+', '名前\\d+', '人物\\d+',
        '仮名', '名無し', 'Unknown', 'Placeholder', 'Example'
    ]
    
    for pattern in placeholder_patterns:
        if pattern in person_name or pattern in person_name_display:
            return True, f'Placeholder pattern: {pattern}'
    
    # 単一文字の名前（ただしLUNA SEAのJは除外）
    if len(person_name.strip()) == 1 and 'LUNA SEA' not in person_name_display:
        if not person_name.strip() in ['J']:  # J (LUNA SEA)は保護
            return True, 'Single character name'
    
    # 完全に空の名前
    if (pd.isna(person_name) or person_name.strip() == '') and \
       (pd.isna(person_name_display) or person_name_display.strip() == ''):
        return True, 'Empty name fields'
    
    # 数字だけの名前
    if person_name.strip().isdigit():
        return True, 'Numeric name only'
    
    return False, 'Not a placeholder'

def main():
    print("="*60)
    print("歴史的人物保護・修正スクリプト")
    print("Protect and Fix Historical Figures")
    print("="*60)
    
    # データベース読み込み
    csv_file = 'ultra_think_FICTIONAL_COMPLETE_20250901_005521.csv'
    print(f"\n📂 Loading database: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Total records: {len(df)}")
    
    # まず有名な歴史的人物のデータを修正
    print("\n🔧 Fixing ALL historical figures data...")
    df, fixed_count, fix_log = fix_all_historical_figures(df)
    print(f"✅ Fixed {fixed_count} historical figures")
    
    if fix_log:
        print("\n📝 Fixed entries:")
        for fix in fix_log[:10]:
            print(f"  {fix['person_id']}: {fix['person_name_display']}")
            for change in fix['changes']:
                print(f"    {change}")
        if len(fix_log) > 10:
            print(f"  ... and {len(fix_log) - 10} more")
    
    # 真のプレースホルダーを特定
    print("\n🔍 Identifying true placeholders...")
    
    true_placeholders = []
    protected_count = 0
    
    for idx, row in df.iterrows():
        is_placeholder, reason = identify_true_placeholders(row)
        
        if is_placeholder:
            true_placeholders.append({
                'person_id': row['person_id'],
                'person_name': row.get('person_name', ''),
                'person_name_display': row.get('person_name_display', ''),
                'occupation': row.get('occupation', ''),
                'recognition': row.get('name_recognition', 0),
                'reason': reason
            })
        elif reason == 'Famous historical figure':
            protected_count += 1
    
    print(f"\n📊 Results:")
    print(f"  True placeholders found: {len(true_placeholders)}")
    print(f"  Historical figures fixed: {fixed_count}")
    print(f"  Historical figures protected: {protected_count}")
    
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
    fixed_csv = f"ultra_think_PROTECTED_FIXED_{timestamp}.csv"
    df.to_csv(fixed_csv, index=False, encoding='utf-8')
    print(f"\n💾 Fixed and protected database saved: {fixed_csv}")
    
    # プレースホルダーリストを保存
    placeholder_report = {
        'timestamp': datetime.now().isoformat(),
        'total_placeholders': len(true_placeholders),
        'historical_figures_fixed': fixed_count,
        'historical_figures_protected': protected_count,
        'placeholder_ids': [p['person_id'] for p in true_placeholders],
        'placeholders': true_placeholders,
        'fix_log': fix_log
    }
    
    report_file = f"final_placeholders_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(placeholder_report, f, ensure_ascii=False, indent=2)
    print(f"📝 Final placeholder report saved: {report_file}")
    
    print("\n✅ Historical figure protection completed!")
    print(f"   True placeholders for deletion: {len(true_placeholders)} records")
    print(f"   Historical figures preserved and fixed: {fixed_count} records")
    print(f"   Total protected: {protected_count} records")
    
    return df, true_placeholders

if __name__ == "__main__":
    df, placeholders = main()