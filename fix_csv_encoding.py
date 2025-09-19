#!/usr/bin/env python3
"""
CSVファイルの文字化けを修正するスクリプト
UTF-8 BOM付きで保存し、Excelで正しく開けるようにする
"""

import pandas as pd
import os
from pathlib import Path
import codecs

def fix_csv_encoding(input_file, output_file=None):
    """
    CSVファイルをUTF-8 BOM付きで再保存
    
    Args:
        input_file: 入力CSVファイルパス
        output_file: 出力CSVファイルパス（指定しない場合は_fixed.csvサフィックスを追加）
    """
    if not os.path.exists(input_file):
        print(f"エラー: ファイル {input_file} が見つかりません")
        return False
    
    if output_file is None:
        base_name = Path(input_file).stem
        output_file = f"{base_name}_fixed.csv"
    
    try:
        # CSVファイルを読み込み（UTF-8として）
        print(f"読み込み中: {input_file}")
        df = pd.read_csv(input_file, encoding='utf-8')
        
        # データの最初の数行を表示して確認
        print("\n最初の3行を確認:")
        print(df.head(3))
        
        # UTF-8 BOM付きで保存
        print(f"\n保存中: {output_file}")
        with open(output_file, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)
        
        print(f"✅ 修正完了: {output_file}")
        print("このファイルはExcelで正しく開けるはずです")
        return True
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False

def main():
    """メイン処理"""
    # 対象ファイルのリスト（deletion_resultsディレクトリ内のファイルも含む）
    target_files = [
        ("deletion_results/deletion_analysis_complete_20250902_060313.csv", "deletion_analysis_complete_20250902_060313_fixed.csv"),
        ("deletion_results/delete_candidates_20250902_060313.csv", "delete_candidates_20250902_060313_fixed.csv"),
        ("ultra_think_EPISODE_FINAL_20250901_020106.csv", None)
    ]
    
    # 存在するファイルを確認
    existing_files = []
    for file_tuple in target_files:
        input_file = file_tuple[0] if isinstance(file_tuple, tuple) else file_tuple
        output_file = file_tuple[1] if isinstance(file_tuple, tuple) and len(file_tuple) > 1 else None
        
        if os.path.exists(input_file):
            existing_files.append((input_file, output_file))
            print(f"✓ 見つかりました: {input_file}")
        else:
            print(f"✗ 見つかりません: {input_file}")
    
    if not existing_files:
        print("\n処理対象のファイルが見つかりませんでした")
    else:
        # 見つかったファイルを修正
        print(f"\n{len(existing_files)}個のファイルを修正します...")
        for input_file, output_file in existing_files:
            print(f"\n処理中: {input_file}")
            fix_csv_encoding(input_file, output_file)

if __name__ == "__main__":
    main()
