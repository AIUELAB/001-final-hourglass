#!/usr/bin/env python3
"""
UUUM事務所問題修正スクリプト
UUUMは事務所であり、グループではないため、括弧内表示を削除
"""

import pandas as pd
import json
from datetime import datetime
import shutil

def fix_uuum_agency_issue():
    """UUUM事務所問題を修正"""
    
    print("🏢 UUUM事務所問題修正を開始...")
    
    # UUUMに所属しているが、グループとして誤分類されている人物
    UUUM_MEMBERS = {
        'P000013': 'HIKAKIN',
        'P000104': 'はじめしゃちょー',
        'P003510': '木下ゆうか'
    }
    
    # 最新のCSVファイル（ONE OK ROCK修正済み）を使用
    csv_file = 'ultra_think_ONE_OK_ROCK_FIXED_20250829_195603.csv'
    
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
        
        # UUUM表示の修正
        for person_id, name in UUUM_MEMBERS.items():
            mask = df['person_id'] == person_id
            if mask.any():
                current_display = df.loc[mask, 'person_name_display'].values[0]
                if '(UUUM)' in str(current_display):
                    new_display = str(current_display).replace(' (UUUM)', '').strip()
                    df.loc[mask, 'person_name_display'] = new_display
                    fixed_count += 1
                    print(f"  ✅ {person_id} {name}: {current_display} → {new_display}")
        
        # youtuber_groups_database.jsonからUUUMを削除
        youtuber_groups_file = 'youtuber_groups_database.json'
        try:
            with open(youtuber_groups_file, 'r', encoding='utf-8') as f:
                youtuber_groups = json.load(f)
            
            if 'UUUM' in youtuber_groups:
                # UUUMエントリーを削除
                deleted_entry = youtuber_groups.pop('UUUM')
                
                with open(youtuber_groups_file, 'w', encoding='utf-8') as f:
                    json.dump(youtuber_groups, f, ensure_ascii=False, indent=2)
                
                print(f"\n📝 youtuber_groups_database.json修正完了:")
                print(f"  削除されたエントリー: {deleted_entry}")
        
        except FileNotFoundError:
            print(f"⚠️ {youtuber_groups_file}が見つかりません")
        
        # 新規agencies_database.jsonを作成
        agencies_db_file = 'agencies_database.json'
        agencies_db = {
            "YouTuber_agencies": {
                "UUUM": {
                    "type": "マネジメント会社",
                    "founded": "2013",
                    "founders": ["HIKAKIN", "鎌田和樹"],
                    "members": ["HIKAKIN", "はじめしゃちょー", "木下ゆうか", "東海オンエア", "フィッシャーズ"],
                    "description": "日本最大級のYouTuber事務所"
                },
                "ジェネシスワン": {
                    "type": "マネジメント会社",
                    "members": [],
                    "description": "YouTuberマネジメント事務所"
                }
            },
            "Comedy_agencies": {
                "吉本興業": {
                    "type": "芸能事務所",
                    "description": "お笑い芸人事務所"
                },
                "ホリプロ": {
                    "type": "芸能事務所",
                    "description": "総合芸能事務所"
                }
            }
        }
        
        with open(agencies_db_file, 'w', encoding='utf-8') as f:
            json.dump(agencies_db, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 新規事務所データベース作成: {agencies_db_file}")
        
        # 修正済みCSVを保存
        output_file = f'ultra_think_UUUM_FIXED_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(output_file, index=False)
        print(f"\n✅ 修正完了: {output_file}")
        print(f"📊 修正件数: {fixed_count}件")
        
        # 修正レポート作成
        report = {
            'timestamp': datetime.now().isoformat(),
            'fixed_count': fixed_count,
            'uuum_members_fixed': list(UUUM_MEMBERS.keys()),
            'agencies_database_created': agencies_db_file,
            'output_file': output_file
        }
        
        report_file = f'UUUM_FIX_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
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
    
    # UUUMが含まれる全レコードを確認
    uuum_records = df[df['person_name_display'].str.contains('UUUM', na=False)]
    
    print(f"\n📊 UUUM関連レコード: {len(uuum_records)}件")
    
    if len(uuum_records) == 0:
        print("✅ すべてのUUUM表示が削除されました！")
    else:
        print("⚠️ まだUUUM表示が残っています:")
        for _, row in uuum_records.iterrows():
            print(f"  {row['person_id']}: {row['person_name_display']}")
    
    # 正しいグループ表示の例を確認
    print("\n📊 正しいグループ表示の例:")
    
    # QuizKnockメンバー
    quizknock_members = df[df['person_name_display'].str.contains('QuizKnock', na=False)]
    if not quizknock_members.empty:
        for _, row in quizknock_members.head(2).iterrows():
            print(f"  ✅ {row['person_id']}: {row['person_name_display']} - 正しいグループ")
    
    # 東海オンエアメンバー
    tokai_members = df[df['person_name_display'].str.contains('東海オンエア', na=False)]
    if not tokai_members.empty:
        for _, row in tokai_members.head(2).iterrows():
            print(f"  ✅ {row['person_id']}: {row['person_name_display']} - 正しいグループ")

if __name__ == "__main__":
    output_file, fixed_count = fix_uuum_agency_issue()
    if output_file:
        verify_fix(output_file)