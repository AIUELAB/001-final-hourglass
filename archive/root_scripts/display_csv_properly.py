#!/usr/bin/env python3
"""
CSVファイルを正しく表示するためのスクリプト
文字化けを防ぎ、見やすい形式で表示します
"""

import pandas as pd
import sys
from pathlib import Path

def display_csv(file_path, num_rows=20):
    """
    CSVファイルを適切なエンコーディングで読み込み、表示する

    Args:
        file_path: CSVファイルのパス
        num_rows: 表示する行数
    """
    try:
        # UTF-8で読み込み
        df = pd.read_csv(file_path, encoding='utf-8')

        print(f"📊 ファイル: {Path(file_path).name}")
        print(f"✅ 正常に読み込みました")
        print(f"📈 総レコード数: {len(df):,}")
        print(f"📋 カラム数: {len(df.columns)}")
        print("=" * 100)

        # データの概要を表示
        print("\n【データ概要】")
        print("-" * 100)

        # 主要カラムの情報
        main_cols = ['person_id', 'person_name', 'person_name_ja', 'person_name_display',
                     'nationality', 'occupation', 'category', 'name_recognition']

        available_cols = [col for col in main_cols if col in df.columns]

        # 最初のN行を表示
        print(f"\n【最初の{num_rows}件のデータ】")
        print("-" * 100)

        # pandas の表示オプションを設定
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 50)
        pd.set_option('display.unicode.east_asian_width', True)

        # データを表示
        display_df = df[available_cols].head(num_rows)

        # 各行を見やすく表示
        for idx, row in display_df.iterrows():
            print(f"\n📌 レコード {idx + 1}:")
            for col in available_cols:
                value = row[col]
                if pd.notna(value):
                    print(f"  {col:20}: {value}")

        # 統計情報
        print("\n" + "=" * 100)
        print("【統計情報】")
        print("-" * 100)

        if 'nationality' in df.columns:
            print("\n国籍別カウント（上位10）:")
            print(df['nationality'].value_counts().head(10).to_string())

        if 'category' in df.columns:
            print("\n\nカテゴリ別カウント:")
            print(df['category'].value_counts().to_string())

        if 'occupation' in df.columns:
            print("\n\n職業別カウント（上位10）:")
            print(df['occupation'].value_counts().head(10).to_string())

        return df

    except UnicodeDecodeError:
        print("❌ UTF-8での読み込みに失敗しました")
        print("別のエンコーディングを試しています...")

        # 他のエンコーディングを試す
        encodings = ['shift-jis', 'cp932', 'euc-jp', 'iso-2022-jp']
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"✅ {encoding}で読み込み成功")
                return df
            except:
                continue

        print("❌ すべてのエンコーディングで失敗しました")
        return None

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return None


def export_to_excel(df, output_path):
    """
    DataFrameをExcelファイルとして保存（文字化け対策済み）
    """
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='データ', index=False)
        print(f"✅ Excelファイルを保存しました: {output_path}")
    except Exception as e:
        print(f"❌ Excel保存エラー: {e}")


if __name__ == "__main__":
    # ファイルパス
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_CLEAN_NO_PLACEHOLDERS_20250827_124619.csv"

    # CSVファイルを表示
    df = display_csv(csv_file, num_rows=30)

    # 必要に応じてExcelファイルとして保存
    if df is not None and len(sys.argv) > 1 and sys.argv[1] == '--excel':
        excel_path = csv_file.replace('.csv', '_readable.xlsx')
        export_to_excel(df, excel_path)
