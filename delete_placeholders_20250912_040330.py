#!/usr/bin/env python3
"""
プレースホルダーデータ削除スクリプト
生成日時: 2025-09-12 04:03:30
削除対象: 27件
"""

import pandas as pd
from datetime import datetime

# 削除対象ID
deletion_ids = ['P030063', 'P002921', 'P030062', 'P030065', 'P030001', 'P030066', 'P030010', 'P030008', 'P002916', 'P030009', 'P002918', 'P002922', 'P030067', 'P030064', 'P030003', 'P030004', 'P002919', 'P002915', 'P030007', 'P002920']  # 最初の20件

# データ読み込み
df = pd.read_csv('ultra_think_MASSIVE_CLEANED_20250912_035645.csv')

# バックアップ作成
backup_file = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
df.to_csv(backup_file, index=False, encoding='utf-8-sig')

# 削除実行
df_cleaned = df[~df["person_id"].isin(deletion_ids)]

# 保存
output_file = f'ultra_think_FINAL_CLEAN_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
df_cleaned.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"削除前: {len(df)}件")
print(f"削除後: {len(df_cleaned)}件")
print(f"削除数: {len(df) - len(df_cleaned)}件")