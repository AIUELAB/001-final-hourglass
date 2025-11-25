from src.secure_config import config
#!/usr/bin/env python3
"""
シンプルなGoogle Sheetsアップローダー
容量エラーを回避して直接アップロード
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import sys

def upload_to_sheets():
    """CSVをGoogle Sheetsにアップロード"""
    try:
        print("🚀 Google Sheets アップロード開始")

        # 認証
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]

        credentials = Credentials.from_service_account_file(
            config.google_credentials_path, scopes=SCOPES
        )

        client = gspread.authorize(credentials)

        # CSVファイルを読み込み
        csv_file = "ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv"
        print(f"📂 CSVファイル読み込み中: {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"✅ データ読み込み完了: {len(df)}行 x {len(df.columns)}列")

        # NaN値を空文字列に置換
        df = df.fillna('')

        # 既存のスプレッドシートを開くか、新規作成
        sheet_title = f"Ultra_Think_DB_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # 新しいスプレッドシートを作成（別の方法）
            print("📝 新しいスプレッドシートを作成中...")
            spreadsheet = client.create(sheet_title)

            # 最初のワークシートを取得
            worksheet = spreadsheet.sheet1

            # ワークシート名を変更
            worksheet.update_title("データ")

        except Exception as e:
            print(f"⚠️ 新規作成エラー: {e}")
            print("既存のスプレッドシートを使用してください")

            # 既存のスプレッドシートIDを入力
            sheet_id = input("既存のスプレッドシートIDを入力 (空でスキップ): ").strip()
            if not sheet_id:
                return

            spreadsheet = client.open_by_key(sheet_id)
            worksheet = spreadsheet.sheet1

        print("📤 データをアップロード中...")

        # データを文字列に変換
        df = df.astype(str)

        # ヘッダーと値を準備
        header = df.columns.tolist()
        values = df.values.tolist()

        # 全データを一括アップロード
        all_data = [header] + values

        # ワークシートのサイズを調整
        worksheet.resize(rows=len(all_data), cols=len(header))

        # バッチ更新（高速）
        worksheet.update(all_data, range_name='A1')

        # フォーマット設定
        worksheet.freeze(rows=1)  # ヘッダー行を固定

        print("✅ アップロード完了！")
        print(f"🔗 スプレッドシートURL:")
        print(f"   {spreadsheet.url}")

        # URLとIDを保存
        with open("sheet_info.txt", "w") as f:
            f.write(f"URL: {spreadsheet.url}\n")
            f.write(f"ID: {spreadsheet.id}\n")
            f.write(f"Title: {spreadsheet.title}\n")

        print("\n💾 情報を sheet_info.txt に保存しました")

        return spreadsheet.url

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    url = upload_to_sheets()
    if url:
        print(f"\n✨ 成功！ブラウザでこのURLを開いてください:")
        print(url)
