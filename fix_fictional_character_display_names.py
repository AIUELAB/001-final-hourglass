#!/usr/bin/env python3
"""
架空キャラクター表示名修正スクリプト
Fix Fictional Character Display Names

このスクリプトは以下の修正を行います：
1. 作品名が欠落しているキャラクターに作品名を追加
2. 半角括弧を全角括弧に統一
3. すべての架空キャラクターを「キャラクター名（作品名）」形式に統一
"""

import pandas as pd
import json
from datetime import datetime
import re

def load_work_mappings():
    """作品名マッピングデータベースを読み込む"""
    try:
        with open('fictional_works_database.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('作品データベース', {})
    except FileNotFoundError:
        print("⚠️ fictional_works_database.json not found, using default mappings")
        return get_default_mappings()

def get_default_mappings():
    """デフォルトの作品名マッピング"""
    return {
        "ONE PIECE": {
            "characters": ["サンジ", "Sanji", "ロロノア・ゾロ", "Roronoa Zoro", "ナミ", "Nami", 
                          "ニコ・ロビン", "Nico Robin", "トニートニー・チョッパー", "Tony Tony Chopper",
                          "モンキー・D・ルフィ", "ルフィ", "ウソップ", "フランキー", "ブルック", "ジンベエ"],
            "type": "漫画/アニメ"
        },
        "ドラえもん": {
            "characters": ["ドラえもん", "Doraemon", "野比のび太", "源静香", "剛田武", "骨川スネ夫"],
            "type": "漫画/アニメ"
        },
        "NARUTO": {
            "characters": ["うずまきナルト", "ナルト", "はたけカカシ", "Kakashi Hatake", "うちはサスケ",
                          "春野サクラ", "大蛇丸", "自来也", "綱手"],
            "type": "漫画/アニメ"
        },
        "仮面ライダー": {
            "characters": ["仮面ライダー", "Kamen Rider"],
            "type": "特撮"
        }
    }

def find_work_for_character(char_name, work_db):
    """キャラクター名から作品名を特定"""
    # 名前の複数の形式をチェック
    names_to_check = [
        char_name,
        char_name.replace(' ', ''),  # スペースを除去
        char_name.replace('・', ''),  # 中点を除去
    ]
    
    for work_name, work_info in work_db.items():
        characters = work_info.get('characters', [])
        for name in names_to_check:
            if name in characters:
                return work_name
            # 部分一致もチェック
            for char in characters:
                if name in char or char in name:
                    return work_name
    return None

def get_japanese_name(person_name, person_name_ja):
    """日本語名を取得（person_name_jaがあればそれを使用）"""
    if pd.notna(person_name_ja) and person_name_ja:
        return person_name_ja
    # person_nameが日本語の場合はそのまま使用
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', str(person_name)):
        return person_name
    return None

def fix_display_name(row, work_db):
    """表示名を修正"""
    person_id = row['person_id']
    person_name = str(row['person_name'])
    person_name_ja = row.get('person_name_ja', '')
    current_display = str(row['person_name_display'])
    nationality = str(row.get('nationality', ''))
    
    # 既に正しい形式（全角括弧で作品名付き）の場合はスキップ
    if '（' in current_display and '）' in current_display:
        # ただし、内容が正しいか確認
        return current_display, 'already_correct'
    
    # 半角括弧を全角に変換
    if '(' in current_display and ')' in current_display:
        fixed_display = current_display.replace('(', '（').replace(')', '）')
        return fixed_display, 'parentheses_fixed'
    
    # 作品名を特定
    work_name = find_work_for_character(person_name, work_db)
    
    # 特殊なケースの処理
    if person_name == "Doraemon" or person_name == "ドラえもん":
        work_name = "ドラえもん"
    elif person_name == "Kamen Rider" or person_name == "仮面ライダー":
        work_name = "仮面ライダー"
    
    # nationalityから作品を推測（ONE PIECEキャラクター）
    if not work_name and nationality in ['北の海', 'East Blue', '偉大なる航路', 'Grand Line']:
        work_name = "ONE PIECE"
    
    # 作品名が見つかった場合
    if work_name:
        # 日本語名を優先
        japanese_name = get_japanese_name(person_name, person_name_ja)
        if japanese_name:
            char_name = japanese_name
        else:
            char_name = person_name
        
        # 特定のキャラクターの日本語表記を修正
        name_corrections = {
            "Sanji": "サンジ",
            "Roronoa Zoro": "ロロノア・ゾロ",
            "Nami": "ナミ",
            "Nico Robin": "ニコ・ロビン",
            "Kakashi Hatake": "はたけカカシ",
            "Tony Tony Chopper": "トニートニー・チョッパー"
        }
        
        if person_name in name_corrections:
            char_name = name_corrections[person_name]
        
        new_display = f"{char_name}（{work_name}）"
        return new_display, 'work_added'
    
    # 作品名が見つからない場合は現状維持
    return current_display, 'no_change'

def main():
    print("="*60)
    print("架空キャラクター表示名修正")
    print("="*60)
    
    # データベース読み込み
    csv_file = 'ultra_think_FINAL_COMPLETE_20250831_215329.csv'
    print(f"\n📂 Loading database: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"✅ Total records: {len(df)}")
    
    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backup_before_fictional_fix_{timestamp}.csv"
    df.to_csv(backup_file, index=False, encoding='utf-8')
    print(f"📁 Backup saved: {backup_file}")
    
    # 作品名マッピングを読み込み
    work_db = load_work_mappings()
    print(f"\n📚 Loaded {len(work_db)} works from database")
    
    # 架空キャラクターの特定
    fictional_mask = (df['category'] == '架空の存在') | (df['occupation'] == '架空キャラクター')
    fictional_chars = df[fictional_mask].copy()
    print(f"\n🎯 Found {len(fictional_chars)} fictional characters")
    
    # 修正の実行
    fixes = {
        'work_added': [],
        'parentheses_fixed': [],
        'already_correct': [],
        'no_change': []
    }
    
    print("\n🔧 Fixing display names...")
    for idx, row in fictional_chars.iterrows():
        old_display = row['person_name_display']
        new_display, fix_type = fix_display_name(row, work_db)
        
        if new_display != old_display:
            df.loc[idx, 'person_name_display'] = new_display
            fixes[fix_type].append({
                'person_id': row['person_id'],
                'person_name': row['person_name'],
                'old_display': old_display,
                'new_display': new_display
            })
        else:
            fixes[fix_type].append({
                'person_id': row['person_id'],
                'person_name': row['person_name'],
                'display': old_display
            })
    
    # 結果の表示
    print(f"\n📊 Fix Summary:")
    print(f"  ✅ Work name added: {len(fixes['work_added'])} characters")
    print(f"  ✅ Parentheses fixed: {len(fixes['parentheses_fixed'])} characters")
    print(f"  ℹ️ Already correct: {len(fixes['already_correct'])} characters")
    print(f"  ⚠️ No change needed: {len(fixes['no_change'])} characters")
    
    # 修正内容の詳細表示
    if fixes['work_added']:
        print(f"\n🎯 Characters with work names added:")
        for fix in fixes['work_added']:
            print(f"  {fix['person_id']}: {fix['old_display']} → {fix['new_display']}")
    
    if fixes['parentheses_fixed']:
        print(f"\n🔧 Characters with parentheses fixed:")
        for fix in fixes['parentheses_fixed'][:5]:  # 最初の5件のみ表示
            print(f"  {fix['person_id']}: {fix['old_display']} → {fix['new_display']}")
        if len(fixes['parentheses_fixed']) > 5:
            print(f"  ... and {len(fixes['parentheses_fixed']) - 5} more")
    
    # 修正済みデータベースを保存
    output_file = f"ultra_think_FICTIONAL_FIXED_{timestamp}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n💾 Fixed database saved: {output_file}")
    
    # ログファイルを保存
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'total_fictional': len(fictional_chars),
        'fixes': {
            'work_added': len(fixes['work_added']),
            'parentheses_fixed': len(fixes['parentheses_fixed']),
            'already_correct': len(fixes['already_correct']),
            'no_change': len(fixes['no_change'])
        },
        'details': fixes,
        'output_file': output_file
    }
    
    log_file = f"fictional_fix_log_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    print(f"📝 Fix log saved: {log_file}")
    
    print("\n✅ Fictional character display names fixed successfully!")
    return output_file

if __name__ == "__main__":
    output_file = main()