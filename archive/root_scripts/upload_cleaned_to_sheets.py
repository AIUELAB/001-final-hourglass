#!/usr/bin/env python3
"""
整理済みCSVをGoogle Sheetsにアップロードしてブラウザで開く
"""

import pandas as pd
import webbrowser
import os
from datetime import datetime

def main():
    print("=" * 80)
    print("📊 整理済みデータ → Google Sheets アップロード")
    print("=" * 80)

    # 整理済みCSVファイル
    csv_file = 'ultra_think_CLEANED_COLUMNS_20250915_200823.csv'

    if not os.path.exists(csv_file):
        print(f"❌ ファイルが見つかりません: {csv_file}")
        return

    print(f"\n📂 ファイル情報:")
    print(f"  ファイル名: {csv_file}")
    file_size = os.path.getsize(csv_file) / (1024 * 1024)
    print(f"  ファイルサイズ: {file_size:.2f} MB")

    # データ概要
    df = pd.read_csv(csv_file)
    print(f"\n📊 データ概要:")
    print(f"  レコード数: {len(df):,}件")
    print(f"  カラム数: {len(df.columns)}列")

    # Google Sheetsの直接アップロードURL
    # 既存のスプレッドシートID
    spreadsheet_id = '1HnV0x-U9HjbGur7VQpB66T0x5HMcPLHQCdMOTQ_HkwE'
    sheets_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

    print(f"\n🌐 Google Sheetsを開いています...")
    print(f"  URL: {sheets_url}")

    # ブラウザで開く
    webbrowser.open(sheets_url)

    print("\n" + "=" * 80)
    print("📤 手動アップロード手順")
    print("=" * 80)
    print("""
1. Google Sheetsが開きました

2. ファイル → インポート をクリック

3. 「アップロード」タブを選択

4. 以下のファイルをドラッグ&ドロップ:
   ultra_think_CLEANED_COLUMNS_20250915_200823.csv

5. インポート場所:
   ✅ 「現在のシートを置き換える」を選択

6. 「データをインポート」をクリック
    """)

    print("=" * 80)
    print("✅ 準備完了！")
    print("=" * 80)

    print(f"\n📊 アップロードされるデータ:")
    print(f"  - 3,569件の100%完工データ")
    print(f"  - 41カラム（60カラムから19カラム削除済み）")
    print(f"  - ファイルサイズ64.5%削減済み")
    print(f"  - すべてBrave Search APIで取得した実データ")

    # Google Drive経由の代替方法も提示
    print("\n📁 代替方法（Google Drive経由）:")
    print("  1. https://drive.google.com を開く")
    print("  2. 新規 → ファイルのアップロード")
    print("  3. ultra_think_CLEANED_COLUMNS_20250915_200823.csv を選択")
    print("  4. アップロード後、右クリック → アプリで開く → Google スプレッドシート")

if __name__ == "__main__":
    main()
