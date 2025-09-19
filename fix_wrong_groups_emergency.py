#!/usr/bin/env python3
"""
緊急修正：間違ったグループ名（ONE OK ROCK、LUNA SEA等）の修正
"""
import pandas as pd
import json
from datetime import datetime

def fix_wrong_groups():
    # CSVファイルを読み込み
    df = pd.read_csv('ultra_think_FAST_VALIDATED_20250828_181901.csv')
    
    # 修正マッピング（間違ったグループ → 正しいグループ）
    wrong_group_fixes = {
        'Okamura Takashi (ONE OK ROCK)': '岡村隆史 (ナインティナイン)',
        'Nagura Jun (LUNA SEA)': '名倉潤 (ネプチューン)',
        'Takashi Koboke (ONE OK ROCK)': '小杉竜一 (ブラックマヨネーズ)',
    }
    
    # person_idとの対応を確認
    person_fixes = {
        'P003178': '岡村隆史 (ナインティナイン)',  # 岡村隆史
        'P002395': '名倉潤 (ネプチューン)',  # 名倉潤
        'P002834': '小杉竜一 (ブラックマヨネーズ)',  # 小杉竜一
        'P004136': '原田泰造 (ネプチューン)',  # 原田泰造（もし間違っていれば）
        'P004424': '堀内健 (ネプチューン)',  # 堀内健（もし間違っていれば）
        'P001970': '矢部浩之 (ナインティナイン)',  # 矢部浩之
        'P001675': '吉田敬 (ブラックマヨネーズ)',  # 吉田敬
    }
    
    fixed_count = 0
    fix_log = []
    
    # person_id ベースの修正
    for person_id, correct_display in person_fixes.items():
        if person_id in df['person_id'].values:
            idx = df[df['person_id'] == person_id].index[0]
            old_display = df.loc[idx, 'person_name_display']
            
            # ONE OK ROCKやLUNA SEAが含まれている場合のみ修正
            if 'ONE OK ROCK' in str(old_display) or 'LUNA SEA' in str(old_display):
                df.loc[idx, 'person_name_display'] = correct_display
                fixed_count += 1
                fix_log.append({
                    'person_id': person_id,
                    'old': old_display,
                    'new': correct_display
                })
    
    # person_name_display の直接マッチング修正
    for wrong_display, correct_display in wrong_group_fixes.items():
        mask = df['person_name_display'] == wrong_display
        if mask.any():
            df.loc[mask, 'person_name_display'] = correct_display
            count = mask.sum()
            fixed_count += count
            fix_log.append({
                'pattern': wrong_display,
                'replacement': correct_display,
                'count': count
            })
    
    # 修正済みファイルを保存
    output_file = 'ultra_think_WRONG_GROUPS_FIXED.csv'
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    # 修正ログを保存
    with open('wrong_groups_fix_log.json', 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'fixed_count': fixed_count,
            'fixes': fix_log
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 間違ったグループ名を{fixed_count}件修正しました")
    print(f"📁 出力ファイル: {output_file}")
    
    return df, fixed_count, fix_log

if __name__ == "__main__":
    df, count, log = fix_wrong_groups()
    
    if log:
        print("\n修正内容:")
        for fix in log:
            if 'person_id' in fix:
                print(f"  {fix['person_id']}: {fix['old']} → {fix['new']}")
            else:
                print(f"  パターン: {fix['pattern']} → {fix['replacement']} ({fix['count']}件)")