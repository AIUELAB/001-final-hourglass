#!/usr/bin/env python3
"""
査定フィールドが「この行を削除」となっている行を削除するスクリプト
"""

import pandas as pd
from datetime import datetime

# CSVファイルを読み込み
input_file = 'ultra_think_FINAL_FIXED_11211_20250825_202452_edit.csv'
df = pd.read_csv(input_file)

print(f"読み込み完了: {len(df)}行")

# 削除対象の行を特定
rows_to_delete = df['査定'] == 'この行を削除'
num_to_delete = rows_to_delete.sum()

print(f"削除対象: {num_to_delete}行")

# 削除対象の行の詳細を表示（最初の10行）
if num_to_delete > 0:
    print("\n削除される行の例（最初の10行）:")
    deleted_rows = df[rows_to_delete].head(10)
    for idx, row in deleted_rows.iterrows():
        print(f"  - {row['person_name_display']} ({row['nationality']}, {row['occupation']})")

# 削除対象ではない行のみを保持
df_cleaned = df[~rows_to_delete].copy()

# 査定カラムを削除（不要になったため）
df_cleaned = df_cleaned.drop(columns=['査定'])

print(f"\n削除後: {len(df_cleaned)}行")

# タイムスタンプ付きファイル名
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = f'ultra_think_CLEANED_{timestamp}.csv'

# CSVファイルに保存
df_cleaned.to_csv(output_file, index=False)
print(f"\n保存完了: {output_file}")

# 削除された行の情報をレポートファイルに保存
if num_to_delete > 0:
    deleted_df = df[rows_to_delete]
    report_file = f'DELETED_ROWS_REPORT_{timestamp}.csv'
    deleted_df.to_csv(report_file, index=False)
    print(f"削除された行のレポート: {report_file}")

# 統計情報
print("\n=== 統計情報 ===")
print(f"元のファイル: {len(df)}行")
print(f"削除された行: {num_to_delete}行")
print(f"最終的な行数: {len(df_cleaned)}行")
print(f"削減率: {(num_to_delete/len(df)*100):.1f}%")