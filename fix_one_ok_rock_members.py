#!/usr/bin/env python3
"""
ONE OK ROCK誤分類修正スクリプト
12名の無関係な人物を削除し、正しい4名のメンバーのみを残す
"""

import pandas as pd
import json
from datetime import datetime
import shutil

def fix_one_ok_rock_members():
    """ONE OK ROCKメンバーの誤分類を修正"""
    
    print("🚨 ONE OK ROCK誤分類修正を開始...")
    
    # 正しいONE OK ROCKメンバー（4名のみ）
    CORRECT_MEMBERS = {
        'P000025': 'Ryota',      # ベーシスト
        'P000032': 'Taka',       # ボーカル
        'P000033': 'Tomoya',     # ドラマー
        'P000034': 'Toru'        # ギタリスト
    }
    
    # 誤ってONE OK ROCKに分類された人物
    WRONG_MEMBERS = {
        'P000083': 'たかし',      # お笑い芸人
        'P002301': '原西孝幸',    # お笑い芸人
        'P002304': '原',          # お笑い芸人
        'P003179': '岡村隆史',    # お笑い芸人
        'P003237': '川田広樹',    # お笑い芸人
        'P003512': '木下隆行',    # お笑い芸人
        'P003622': '村上隆',      # 芸術家
        'P003643': '東貴博',      # お笑い芸人
        'P004455': '田﨑敬浩',    # 歌手
        'P004561': '石橋貴明',    # お笑い芸人
        'P005394': '駒場孝',      # お笑い芸人
        'P005430': '高橋恭平'     # 歌手
    }
    
    # 最新のCSVファイルを読み込み
    csv_file = 'ultra_think_FICTIONAL_FIXED_20250828_215146.csv'
    
    try:
        # バックアップ作成
        backup_file = f'backup_{csv_file}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy(csv_file, backup_file)
        print(f"✅ バックアップ作成: {backup_file}")
        
        # CSVファイル読み込み
        df = pd.read_csv(csv_file, dtype=str)
        print(f"📊 データ読み込み完了: {len(df)}件")
        
        # 修正統計
        fixed_count = 0
        
        # ONE OK ROCK誤分類の修正
        for person_id, name in WRONG_MEMBERS.items():
            mask = df['person_id'] == person_id
            if mask.any():
                # (ONE OK ROCK)を削除
                current_display = df.loc[mask, 'person_name_display'].values[0]
                if '(ONE OK ROCK)' in str(current_display):
                    new_display = str(current_display).replace(' (ONE OK ROCK)', '').strip()
                    df.loc[mask, 'person_name_display'] = new_display
                    fixed_count += 1
                    print(f"  ✅ {person_id} {name}: {current_display} → {new_display}")
        
        # groups_database.jsonの修正
        groups_db_file = 'groups_database.json'
        try:
            with open(groups_db_file, 'r', encoding='utf-8') as f:
                groups_db = json.load(f)
            
            # ONE OK ROCKメンバーリストを正しいメンバーのみに修正
            if 'ONE OK ROCK' in groups_db:
                old_members = groups_db['ONE OK ROCK']
                groups_db['ONE OK ROCK'] = ['Taka', 'Toru', 'Ryota', 'Tomoya']
                
                with open(groups_db_file, 'w', encoding='utf-8') as f:
                    json.dump(groups_db, f, ensure_ascii=False, indent=2)
                
                print(f"\n📝 groups_database.json修正完了:")
                print(f"  旧メンバー: {old_members}")
                print(f"  新メンバー: {groups_db['ONE OK ROCK']}")
        
        except FileNotFoundError:
            print(f"⚠️ {groups_db_file}が見つかりません")
        
        # 修正済みCSVを保存
        output_file = f'ultra_think_ONE_OK_ROCK_FIXED_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(output_file, index=False)
        print(f"\n✅ 修正完了: {output_file}")
        print(f"📊 修正件数: {fixed_count}件")
        
        # 修正レポート作成
        report = {
            'timestamp': datetime.now().isoformat(),
            'fixed_count': fixed_count,
            'wrong_members_removed': list(WRONG_MEMBERS.keys()),
            'correct_members_kept': list(CORRECT_MEMBERS.keys()),
            'output_file': output_file
        }
        
        report_file = f'ONE_OK_ROCK_FIX_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 レポート保存: {report_file}")
        
        return output_file, fixed_count
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return None, 0

def verify_fix(csv_file):
    """修正結果を検証"""
    print("\n🔍 修正結果を検証中...")
    
    df = pd.read_csv(csv_file, dtype=str)
    
    # ONE OK ROCKが含まれる全レコードを確認
    one_ok_rock_records = df[df['person_name_display'].str.contains('ONE OK ROCK', na=False)]
    
    print(f"\n📊 ONE OK ROCK関連レコード: {len(one_ok_rock_records)}件")
    
    correct_count = 0
    wrong_count = 0
    
    for _, row in one_ok_rock_records.iterrows():
        person_id = row['person_id']
        display_name = row['person_name_display']
        
        if person_id in ['P000025', 'P000032', 'P000033', 'P000034']:
            correct_count += 1
            print(f"  ✅ {person_id}: {display_name} - 正しいメンバー")
        else:
            wrong_count += 1
            print(f"  ❌ {person_id}: {display_name} - 誤分類（要修正）")
    
    print(f"\n📊 検証結果:")
    print(f"  正しいメンバー: {correct_count}件")
    print(f"  誤分類: {wrong_count}件")
    
    if wrong_count == 0:
        print("✅ すべての誤分類が修正されました！")
    else:
        print("⚠️ まだ誤分類が残っています")

if __name__ == "__main__":
    output_file, fixed_count = fix_one_ok_rock_members()
    if output_file:
        verify_fix(output_file)