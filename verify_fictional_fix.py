#!/usr/bin/env python3
"""
架空キャラクター作品名修正の検証システム
"""
import pandas as pd
import json
from datetime import datetime

def verify_fictional_fixes():
    """修正結果を検証"""
    # 最新のCSVを読み込み
    csv_file = 'ultra_think_FICTIONAL_FIXED_20250828_215146.csv'
    df = pd.read_csv(csv_file)
    
    print("=" * 80)
    print("🔍 架空キャラクター作品名修正検証")
    print("=" * 80)
    
    # 1. P000199（アルミン）の確認
    p199 = df[df['person_id'] == 'P000199']
    if not p199.empty:
        row = p199.iloc[0]
        print(f"\n📌 P000199（アルミン）最終状態:")
        print(f"   person_name: {row['person_name']}")
        print(f"   person_name_display: {row['person_name_display']}")
        print(f"   person_name_ja: {row['person_name_ja']}")
        print(f"   occupation: {row['occupation']}")
        print(f"   category: {row.get('category', '')}")
        
        if '進撃の巨人' in str(row['person_name_display']):
            print("   ✅ 作品名が正しく追加されています！")
        else:
            print("   ⚠️ 作品名が追加されていません")
    
    # 2. 主要キャラクターの確認
    print("\n📌 主要キャラクター確認:")
    important_ids = ['P000075', 'P000102', 'P000535', 'P000397']
    for pid in important_ids:
        row = df[df['person_id'] == pid]
        if not row.empty:
            display = row.iloc[0]['person_name_display']
            has_work = '（' in str(display) and '）' in str(display)
            status = "✅" if has_work else "❌"
            print(f"   {pid}: {display} {status}")
    
    # 3. 架空キャラクターカテゴリ全体の統計
    fictional_mask = df['category'] == '架空の存在'
    fictional_count = fictional_mask.sum()
    
    # display名に作品名がある件数
    has_work_title = df[fictional_mask]['person_name_display'].apply(
        lambda x: '（' in str(x) and '）' in str(x)
    ).sum()
    
    print(f"\n📊 架空キャラクター統計:")
    print(f"   カテゴリ「架空の存在」: {fictional_count}件")
    print(f"   作品名付き: {has_work_title}件 ({has_work_title/fictional_count*100:.1f}%)")
    print(f"   作品名なし: {fictional_count - has_work_title}件")
    
    # 4. 作品名なしのキャラクター詳細
    no_work = df[fictional_mask & ~df['person_name_display'].apply(
        lambda x: '（' in str(x) and '）' in str(x)
    )]
    
    if len(no_work) > 0:
        print(f"\n⚠️ 作品名なしのキャラクター（最初の10件）:")
        for idx, row in no_work.head(10).iterrows():
            print(f"   {row['person_id']}: {row['person_name']} - {row['occupation']}")
    
    # 5. 修正ログの確認
    try:
        with open('fictional_character_fix_log_20250828_215146.json', 'r', encoding='utf-8') as f:
            log = json.load(f)
        print(f"\n📝 修正ログサマリー:")
        print(f"   修正成功: {log['summary']['total_fixed']}件")
        print(f"   修正失敗: {log['summary']['total_unfixed']}件")
    except:
        pass
    
    # 6. データ品質チェック
    print("\n✨ データ品質チェック:")
    
    # 重複チェック
    duplicates = df[df.duplicated('person_id')]
    print(f"   重複レコード: {len(duplicates)}件")
    
    # person_nameにアンダースコアがないか
    underscore_count = df['person_name'].apply(lambda x: '_' in str(x)).sum()
    print(f"   person_nameのアンダースコア: {underscore_count}件")
    
    # 全体の統計
    print(f"\n📈 データベース全体統計:")
    print(f"   総レコード数: {len(df)}件")
    print(f"   架空キャラクター: {fictional_count}件 ({fictional_count/len(df)*100:.1f}%)")
    
    return df

if __name__ == '__main__':
    verify_fictional_fixes()