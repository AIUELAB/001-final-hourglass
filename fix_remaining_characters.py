#!/usr/bin/env python3
"""
残り2体のONE PIECEキャラクターを修正
Fix remaining 2 ONE PIECE characters
"""

import pandas as pd
import json
from datetime import datetime

def main():
    print("="*60)
    print("残りのキャラクター修正")
    print("="*60)
    
    # データベース読み込み
    csv_file = 'ultra_think_FICTIONAL_FIXED_20250901_005324.csv'
    print(f"\n📂 Loading database: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8')
    
    # バックアップ
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backup_before_final_fix_{timestamp}.csv"
    df.to_csv(backup_file, index=False, encoding='utf-8')
    print(f"📁 Backup saved: {backup_file}")
    
    fixes = []
    
    # P000980 (Nami)を修正
    nami_mask = df['person_id'] == 'P000980'
    if nami_mask.any():
        old_display = df.loc[nami_mask, 'person_name_display'].iloc[0]
        new_display = 'ナミ（ONE PIECE）'
        df.loc[nami_mask, 'person_name_display'] = new_display
        fixes.append({
            'person_id': 'P000980',
            'old': old_display,
            'new': new_display
        })
        print(f"✅ Fixed P000980: {old_display} → {new_display}")
    
    # P001517 (Nico Robin)を修正
    robin_mask = df['person_id'] == 'P001517'
    if robin_mask.any():
        old_display = df.loc[robin_mask, 'person_name_display'].iloc[0]
        new_display = 'ニコ・ロビン（ONE PIECE）'
        df.loc[robin_mask, 'person_name_display'] = new_display
        fixes.append({
            'person_id': 'P001517',
            'old': old_display,
            'new': new_display
        })
        print(f"✅ Fixed P001517: {old_display} → {new_display}")
    
    # 保存
    output_file = f"ultra_think_FICTIONAL_COMPLETE_{timestamp}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n💾 Final database saved: {output_file}")
    
    # ログ保存
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'fixes': fixes,
        'output_file': output_file
    }
    
    log_file = f"final_fictional_fix_log_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    print(f"📝 Log saved: {log_file}")
    
    print("\n✅ All fictional characters fixed!")
    return output_file

if __name__ == "__main__":
    output = main()