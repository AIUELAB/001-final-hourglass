#!/usr/bin/env python3
"""
「嵐」グループ問題修正スクリプト
P003218「嵐」を個人からグループに修正し、メンバーを個別追加
"""

import pandas as pd
import json
from datetime import datetime
import shutil

def fix_arashi_group_issue():
    """嵐のグループ問題を修正"""
    print("="*60)
    print("🔧 「嵐」グループ問題修正")
    print("="*60)
    
    # バックアップ作成
    csv_file = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    backup_file = f"backup_{csv_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(csv_file, backup_file)
    print(f"📦 バックアップ作成: {backup_file}")
    
    # データ読み込み
    df = pd.read_csv(csv_file)
    print(f"📂 データ読み込み: {len(df)}件")
    
    # 嵐のレコードを確認
    arashi_record = df[df['person_id'] == 'P003218']
    if not arashi_record.empty:
        print("\n🎯 現在の「嵐」レコード:")
        print(f"  person_id: {arashi_record.iloc[0]['person_id']}")
        print(f"  person_name: {arashi_record.iloc[0]['person_name']}")
        print(f"  occupation: {arashi_record.iloc[0]['occupation']}")
        
        # entity_typeをgroupに変更
        df.loc[df['person_id'] == 'P003218', 'entity_type'] = 'group'
        df.loc[df['person_id'] == 'P003218', 'occupation'] = 'アイドルグループ'
        
        # extended_dataを更新してグループ情報を追加
        extended_data = json.loads(arashi_record.iloc[0]['extended_data'] or '{}')
        extended_data['entity_type'] = 'group'
        extended_data['group_members'] = [
            '大野智', '櫻井翔', '相葉雅紀', '二宮和也', '松本潤'
        ]
        extended_data['active_period'] = '1999-2020'
        extended_data['note'] = '2020年12月31日活動休止'
        df.loc[df['person_id'] == 'P003218', 'extended_data'] = json.dumps(extended_data, ensure_ascii=False)
        
        print("\n✅ 「嵐」をグループとして修正完了")
    
    # 嵐のメンバーを個別に追加
    arashi_members = [
        {
            'person_id': 'P003218_001',
            'person_name': '大野智',
            'person_name_ja': '大野智',
            'person_name_display': '大野智',
            'entity_type': 'person',
            'occupation': '歌手・俳優・タレント',
            'nationality': '日本',
            'category': 'エンタメ',
            'final_score': 7.5,
            'accuracy_score': 80,
            'impact_score': 75,
            'is_published': True,
            'created_at': datetime.now().isoformat(),
            'source': 'Arashi Member Fix',
            'extended_data': json.dumps({
                'group_id': 'P003218',
                'group_name': '嵐',
                'birth_date': '1980-11-26',
                'is_fictional': 'FALSE'
            }, ensure_ascii=False)
        },
        {
            'person_id': 'P003218_002',
            'person_name': '櫻井翔',
            'person_name_ja': '櫻井翔',
            'person_name_display': '櫻井翔',
            'entity_type': 'person',
            'occupation': '歌手・俳優・タレント・ニュースキャスター',
            'nationality': '日本',
            'category': 'エンタメ',
            'final_score': 8.0,
            'accuracy_score': 85,
            'impact_score': 80,
            'is_published': True,
            'created_at': datetime.now().isoformat(),
            'source': 'Arashi Member Fix',
            'extended_data': json.dumps({
                'group_id': 'P003218',
                'group_name': '嵐',
                'birth_date': '1982-01-25',
                'is_fictional': 'FALSE'
            }, ensure_ascii=False)
        },
        {
            'person_id': 'P003218_003',
            'person_name': '相葉雅紀',
            'person_name_ja': '相葉雅紀',
            'person_name_display': '相葉雅紀',
            'entity_type': 'person',
            'occupation': '歌手・俳優・タレント',
            'nationality': '日本',
            'category': 'エンタメ',
            'final_score': 7.0,
            'accuracy_score': 75,
            'impact_score': 70,
            'is_published': True,
            'created_at': datetime.now().isoformat(),
            'source': 'Arashi Member Fix',
            'extended_data': json.dumps({
                'group_id': 'P003218',
                'group_name': '嵐',
                'birth_date': '1982-12-24',
                'is_fictional': 'FALSE'
            }, ensure_ascii=False)
        },
        {
            'person_id': 'P003218_004',
            'person_name': '二宮和也',
            'person_name_ja': '二宮和也',
            'person_name_display': '二宮和也',
            'entity_type': 'person',
            'occupation': '歌手・俳優・タレント',
            'nationality': '日本',
            'category': 'エンタメ',
            'final_score': 7.5,
            'accuracy_score': 80,
            'impact_score': 75,
            'is_published': True,
            'created_at': datetime.now().isoformat(),
            'source': 'Arashi Member Fix',
            'extended_data': json.dumps({
                'group_id': 'P003218',
                'group_name': '嵐',
                'birth_date': '1983-06-17',
                'is_fictional': 'FALSE'
            }, ensure_ascii=False)
        },
        {
            'person_id': 'P003218_005',
            'person_name': '松本潤',
            'person_name_ja': '松本潤',
            'person_name_display': '松本潤',
            'entity_type': 'person',
            'occupation': '歌手・俳優・タレント',
            'nationality': '日本',
            'category': 'エンタメ',
            'final_score': 7.5,
            'accuracy_score': 80,
            'impact_score': 75,
            'is_published': True,
            'created_at': datetime.now().isoformat(),
            'source': 'Arashi Member Fix',
            'extended_data': json.dumps({
                'group_id': 'P003218',
                'group_name': '嵐',
                'birth_date': '1983-08-30',
                'is_fictional': 'FALSE'
            }, ensure_ascii=False)
        }
    ]
    
    # 既存メンバーチェック
    existing_member_ids = df[df['person_id'].str.startswith('P003218_')]['person_id'].tolist()
    if existing_member_ids:
        print(f"\n⚠️ 既存メンバーレコード検出: {existing_member_ids}")
        df = df[~df['person_id'].str.startswith('P003218_')]
        print(f"  → 既存メンバーレコード削除")
    
    # メンバー追加
    print("\n📝 嵐メンバー追加:")
    for member in arashi_members:
        # 既存のカラムに合わせてデータを準備
        new_row = {col: '' for col in df.columns}
        for key, value in member.items():
            if key in df.columns:
                new_row[key] = value
        
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        print(f"  ✅ {member['person_name']} (ID: {member['person_id']})")
    
    # 保存
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 修正データ保存: {csv_file}")
    print(f"📊 総レコード数: {len(df)}件")
    
    # 検証
    print("\n🔍 修正結果検証:")
    arashi_group = df[df['person_id'] == 'P003218']
    if not arashi_group.empty:
        print(f"  グループ「嵐」: entity_type={arashi_group.iloc[0].get('entity_type', 'N/A')}")
    
    members = df[df['person_id'].str.startswith('P003218_')]
    print(f"  メンバー数: {len(members)}名")
    for _, member in members.iterrows():
        print(f"    - {member['person_name']}: score={member.get('final_score', 'N/A')}")
    
    return True

if __name__ == "__main__":
    success = fix_arashi_group_issue()
    if success:
        print("\n✅ 修正完了")
    else:
        print("\n❌ 修正失敗")