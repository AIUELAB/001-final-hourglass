#!/usr/bin/env python3
"""
残りのLUNA SEA誤分類を修正
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import shutil

# 追加の修正対象
ADDITIONAL_FIXES = {
    'P005539': {'remove_group': 'LUNA SEA', 'note': 'John Frusciante - Red Hot Chili Peppers guitarist'},
    'P005546': {'remove_group': 'LUNA SEA', 'note': 'Joe Perry - Aerosmith guitarist'},
}

def main():
    print("🔧 残りのLUNA SEA誤分類を修正")
    
    # 最新のCSVファイルを検索
    csv_file = Path('ultra_think_COMPREHENSIVE_FIX_20250829_215738.csv')
    if not csv_file.exists():
        print("❌ ファイルが見つかりません")
        return
    
    # バックアップ
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backup_final_luna_fix_{timestamp}.csv"
    shutil.copy(csv_file, backup_file)
    
    # データ読み込み
    df = pd.read_csv(csv_file)
    
    # LUNA SEAを含むすべてのレコードを検索して修正
    luna_sea_count = 0
    for idx, row in df.iterrows():
        display = str(row['person_name_display'])
        if '(LUNA SEA)' in display:
            # 本物のLUNA SEAメンバーかチェック
            # 本物のメンバー: RYUICHI, SUGIZO, INORAN, J, 真矢
            real_members = ['RYUICHI', 'SUGIZO', 'INORAN', 'J', '真矢', '河村隆一']
            
            is_real_member = False
            for member in real_members:
                if member in display or member in str(row.get('person_name_ja', '')):
                    is_real_member = True
                    break
            
            if not is_real_member:
                # 誤分類なので削除
                new_display = display.replace(' (LUNA SEA)', '')
                df.loc[idx, 'person_name_display'] = new_display
                luna_sea_count += 1
                print(f"❌ {row['person_id']}: {display} → {new_display}")
    
    print(f"\n✅ {luna_sea_count}件のLUNA SEA誤分類を修正")
    
    # 保存
    output_file = f"ultra_think_FINAL_CLEAN_{timestamp}.csv"
    df.to_csv(output_file, index=False)
    print(f"💾 保存: {output_file}")
    
    return output_file

if __name__ == "__main__":
    main()