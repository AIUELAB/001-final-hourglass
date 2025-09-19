#!/usr/bin/env python3
"""
中点（・）で区切られた名前の処理を修正
現代の人物（特に映画監督、俳優など）はフルネーム維持
"""

import csv
import json
import shutil
from datetime import datetime

# 歴史的巨匠（短縮可能）
HISTORICAL_MASTERS = {
    # 映画界の巨匠（故人のみ）
    '黒澤明': '黒澤',
    'クロサワ・アキラ': '黒澤',
    '小津安二郎': '小津',
    'アルフレッド・ヒッチコック': 'ヒッチコック',
    'スタンリー・キューブリック': 'キューブリック',
    
    # 音楽界（クラシック）
    'ヴォルフガング・アマデウス・モーツァルト': 'モーツァルト',
    'ルートヴィヒ・ヴァン・ベートーヴェン': 'ベートーヴェン',
    'ヨハン・セバスチャン・バッハ': 'バッハ',
    'フレデリック・ショパン': 'ショパン',
    
    # 美術界
    'レオナルド・ダ・ヴィンチ': 'ダ・ヴィンチ',
    'パブロ・ピカソ': 'ピカソ',
    'フィンセント・ファン・ゴッホ': 'ゴッホ',
    'ミケランジェロ・ブオナローティ': 'ミケランジェロ',
    
    # 科学界
    'アルベルト・アインシュタイン': 'アインシュタイン',
    'アイザック・ニュートン': 'ニュートン',
    'ガリレオ・ガリレイ': 'ガリレオ',
    
    # 古代の人物
    'ガイウス・ノルバヌス・ソレクス': 'ソレクス',
    'ユリウス・カエサル': 'カエサル',
}

# 現代の映画監督（フルネーム必須）
MODERN_DIRECTORS = [
    'クリストファー・ノーラン',
    'スティーヴン・スピルバーグ',
    'マーティン・スコセッシ',
    'クエンティン・タランティーノ',
    'デヴィッド・フィンチャー',
    'ウェス・アンダーソン',
    'ポール・トーマス・アンダーソン',
    'ダーレン・アロノフスキー',
    'ギレルモ・デル・トロ',
    'ジェームズ・キャメロン',
    'ティム・バートン',
    'コーエン兄弟',
    'リドリー・スコット',
    'デニス・ヴィルヌーヴ',
    'タイカ・ワイティティ',
]

# 現代の俳優（フルネーム必須）
MODERN_ACTORS = [
    'ニール・パトリック・ハリス',
    'ブラッド・ピット',
    'レオナルド・ディカプリオ',
    'トム・ハンクス',
    'メリル・ストリープ',
    'ロバート・ダウニー・Jr',
    'スカーレット・ヨハンソン',
    'ベネディクト・カンバーバッチ',
]

def should_keep_fullname(person_data):
    """フルネームを維持すべきか判定"""
    name = person_data.get('person_name', '')
    name_ja = person_data.get('person_name_ja', '')
    birth_date = person_data.get('birth_date', '')
    death_date = person_data.get('death_date', '')
    occupation = person_data.get('occupation', '')
    category = person_data.get('main_category', '')
    subcategory = person_data.get('subcategory', '')
    
    # 現代の映画監督・俳優
    if name in MODERN_DIRECTORS or name_ja in MODERN_DIRECTORS:
        return True
    if name in MODERN_ACTORS or name_ja in MODERN_ACTORS:
        return True
    
    # 映画監督カテゴリーで1900年以降生まれ
    if subcategory == '映画監督' or '映画監督' in occupation:
        if birth_date:
            try:
                birth_year = int(birth_date.split('-')[0])
                if birth_year >= 1900:
                    return True
            except:
                pass
    
    # 存命中の人物（death_dateが空）
    if birth_date and not death_date:
        try:
            birth_year = int(birth_date.split('-')[0])
            # 1940年以降生まれで存命なら現代人
            if birth_year >= 1940:
                return True
        except:
            pass
    
    # エンターテインメント系の現代人
    if category == 'エンターテインメント' and not death_date:
        return True
    
    return False

def fix_display_name(person_data):
    """表示名を修正"""
    name = person_data.get('person_name', '')
    name_ja = person_data.get('person_name_ja', '')
    current_display = person_data.get('person_name_display', '')
    
    # 歴史的巨匠は短縮可能
    if name_ja in HISTORICAL_MASTERS:
        return HISTORICAL_MASTERS[name_ja]
    if name in HISTORICAL_MASTERS:
        return HISTORICAL_MASTERS[name]
    
    # フルネーム維持が必要な人物
    if should_keep_fullname(person_data):
        # 中点で区切られた名前で、現在短縮されている場合
        if '・' in name_ja and len(current_display) < len(name_ja):
            return name_ja
        if '・' in name and len(current_display) < len(name):
            return name_ja if name_ja else name
    
    # お笑いコンビ形式は維持
    comedy_duos = ['中川家', 'サンドウィッチマン', 'フットボールアワー']
    if any(duo in name_ja for duo in comedy_duos) and '・' in name_ja:
        return name_ja
    
    # 特定の修正が必要な人物
    if current_display == 'ノーラン' and 'クリストファー' in name_ja:
        return 'クリストファー・ノーラン'
    if current_display == 'ハリス' and 'ニール' in name_ja:
        return 'ニール・パトリック・ハリス'
    if current_display == 'リチャードソン' and 'トニー' in name_ja:
        return 'トニー・リチャードソン'
    if current_display == 'イロナ' and 'シュターッレル' in name_ja:
        return 'シュターッレル・イロナ'
    
    # その他の中点名前で短すぎる場合
    if '・' in name_ja and len(current_display) <= 5:
        # 歴史的人物でなければフルネーム
        if should_keep_fullname(person_data):
            return name_ja
    
    return current_display

def main():
    """メイン処理"""
    print("=" * 60)
    print("中点名前の表示名修正")
    print("=" * 60)
    
    input_file = 'final_12410_firebase_20250822_201828.json'
    
    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_midpoint_fix_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")
    
    # JSON読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 修正処理
    fix_count = 0
    fix_log = []
    
    for key, person in data.items():
        old_display = person.get('person_name_display', '')
        new_display = fix_display_name(person)
        
        if old_display != new_display:
            fix_log.append({
                'id': key,
                'person_name': person.get('person_name', ''),
                'person_name_ja': person.get('person_name_ja', ''),
                'old_display': old_display,
                'new_display': new_display,
                'category': person.get('subcategory', ''),
                'birth': person.get('birth_date', '')
            })
            person['person_name_display'] = new_display
            fix_count += 1
    
    # 結果を保存
    output_file = f'midpoint_fixed_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ログ保存
    log_file = f'midpoint_fix_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'fix_count': fix_count,
            'timestamp': timestamp,
            'samples': fix_log[:100]
        }, f, ensure_ascii=False, indent=2)
    
    # 元のファイルを更新
    shutil.copy2(output_file, input_file)
    
    print("\n📊 処理結果:")
    print(f"  修正件数: {fix_count}件")
    
    # 主要な修正例を表示
    print("\n📝 主な修正例:")
    important_fixes = [
        f for f in fix_log 
        if any(name in f['old_display'] for name in ['ノーラン', 'ハリス', 'リチャードソン', 'イロナ'])
    ]
    for i, fix in enumerate(important_fixes[:10], 1):
        print(f"{i}. {fix['id']}: {fix['old_display']} → {fix['new_display']} ({fix['category']})")
    
    # CSV出力
    print("\n📊 CSV出力中...")
    csv_filename = f'midpoint_fixed_{timestamp}.csv'
    
    headers = [
        'id', 'person_name', 'person_name_ja', 'person_name_display', 'grade',
        'birth_date', 'death_date', 'nationality', 'occupation',
        'main_category', 'subcategory', 'description'
    ]
    
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for key, person in data.items():
            row = {
                'id': person.get('id', key),
                'person_name': person.get('person_name', ''),
                'person_name_ja': person.get('person_name_ja', ''),
                'person_name_display': person.get('person_name_display', ''),
                'grade': person.get('grade', ''),
                'birth_date': person.get('birth_date', ''),
                'death_date': person.get('death_date', ''),
                'nationality': person.get('nationality', ''),
                'occupation': person.get('occupation', ''),
                'main_category': person.get('main_category', ''),
                'subcategory': person.get('subcategory', ''),
                'description': person.get('description', '')
            }
            writer.writerow(row)
    
    print(f"✅ CSV出力完了: {csv_filename}")
    
    return fix_count

if __name__ == "__main__":
    main()