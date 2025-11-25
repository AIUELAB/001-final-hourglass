#!/usr/bin/env python3
"""
Ultra Think 直接同期スクリプト
gspreadを使用したシンプルで確実な同期
"""

import os
import sys
import json
import pandas as pd
import gspread
from pathlib import Path
from datetime import datetime
from google.oauth2.service_account import Credentials
import webbrowser
import time


def main():
    """メイン実行"""
    print("=" * 60)
    print("🚀 Ultra Think 直接同期システム")
    print("=" * 60)

    # 1. 最新のCSVファイルを検索
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        print("❌ ultra_think_*.csv ファイルが見つかりません")
        return 1

    latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
    print(f"\n📄 対象ファイル: {latest_csv.name}")

    # 2. データ読み込み
    print("\n📊 データ読み込み中...")
    try:
        df = pd.read_csv(latest_csv)
        print(f"✅ データ読み込み完了: {len(df)}行")

        # NaN値を空文字列に変換
        df = df.fillna('')

    except Exception as e:
        print(f"❌ データ読み込みエラー: {e}")
        return 1

    # 3. Google Sheets接続
    print("\n☁️ Google Sheetsに接続中...")
    try:
        # 認証情報
        credentials_path = "key/credentials.json"
        if not Path(credentials_path).exists():
            print("❌ 認証ファイルが見つかりません")
            return 1

        # スコープ設定
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        # 認証
        creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
        client = gspread.authorize(creds)

        print("✅ Google Sheets接続成功")

    except Exception as e:
        print(f"❌ Google Sheets接続エラー: {e}")
        return 1

    # 4. スプレッドシートを開く
    spreadsheet_id = "1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps"
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        sheet = spreadsheet.sheet1  # 最初のシート

        print(f"✅ スプレッドシート接続: {spreadsheet.title}")

    except Exception as e:
        print(f"❌ スプレッドシート接続エラー: {e}")
        return 1

    # 5. シートをクリアして新しいデータを書き込み
    print("\n🔄 データ同期中...")
    try:
        # 既存データをクリア
        sheet.clear()
        print("   既存データをクリア")

        # 必要に応じてシートをリサイズ
        sheet.resize(rows=len(df) + 1, cols=len(df.columns))
        print(f"   シートサイズ調整: {len(df) + 1}行 × {len(df.columns)}列")

        # ヘッダーを設定
        headers = df.columns.tolist()
        sheet.update('A1', [headers])
        print("   ヘッダー設定完了")

        # データを設定（バッチ更新）
        values = df.values.tolist()

        # データを分割して送信（1000行ずつ）
        batch_size = 1000
        total_batches = (len(values) + batch_size - 1) // batch_size

        for i in range(0, len(values), batch_size):
            batch = values[i:i+batch_size]
            start_row = i + 2  # ヘッダー行の次から
            end_row = min(i + batch_size + 1, len(values) + 1)

            range_str = f'A{start_row}:{chr(65 + len(headers) - 1)}{end_row}'
            sheet.update(range_str, batch)

            current_batch = (i // batch_size) + 1
            print(f"   バッチ {current_batch}/{total_batches} 完了 ({len(batch)}行)")

            # レート制限対策
            time.sleep(1)

        print("✅ データ同期完了！")

    except Exception as e:
        print(f"❌ データ同期エラー: {e}")
        return 1

    # 6. スプレッドシート名を更新
    print("\n📝 スプレッドシート名を更新中...")
    try:
        new_name = latest_csv.stem.replace('_', ' ').replace('ultra think', 'Ultra Think')
        spreadsheet.update_title(new_name)
        print(f"✅ スプレッドシート名更新: {new_name}")

    except Exception as e:
        print(f"⚠️ スプレッドシート名更新エラー: {e}")

    # 7. フォーマット設定
    print("\n🎨 フォーマット設定中...")
    try:
        # ヘッダー行を太字に
        sheet.format('A1:Z1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.8},
            'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
        })
        print("✅ フォーマット設定完了")

    except Exception as e:
        print(f"⚠️ フォーマット設定エラー: {e}")

    # 8. ブラウザで開く
    print("\n🌐 ブラウザで開いています...")
    try:
        # キャッシュバスター付きURL
        timestamp = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}?v={timestamp}&nocache=1"
        webbrowser.open(url)
        print("✅ ブラウザで開きました")

    except Exception as e:
        print(f"⚠️ ブラウザ起動エラー: {e}")

    # 9. 成功音を再生（macOS）
    os.system("afplay /System/Library/Sounds/Glass.aiff 2>/dev/null &")

    # 10. サマリー表示
    print("\n" + "=" * 60)
    print("🎉 同期が正常に完了しました！")
    print("=" * 60)
    print(f"✅ 同期行数: {len(df)}行")
    print(f"✅ 同期列数: {len(df.columns)}列")
    print(f"✅ スプレッドシート: {new_name}")
    print(f"✅ URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print("=" * 60)

    # ログ記録
    sync_log = {
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "rows": len(df),
        "columns": len(df.columns),
        "file": latest_csv.name,
        "method": "direct_sync"
    }

    log_file = Path("sync_log.json")
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(sync_log)
    logs = logs[-10:]  # 最新10件のみ保持

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠️ ユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
