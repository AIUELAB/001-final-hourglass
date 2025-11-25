from src.secure_config import config
#!/usr/bin/env python3
"""
既存のGoogle Sheetsにデータをアップロード
手動で作成したスプレッドシートを使用
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import sys
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

def upload_to_existing_sheet(spreadsheet_id=None):
    """既存のGoogle Sheetsにアップロード"""
    try:
        console.print("[bold blue]📊 Ultra Think Database → Google Sheets アップローダー[/bold blue]\n")

        if not spreadsheet_id:
            console.print("[yellow]事前準備:[/yellow]")
            console.print("1. Google Sheetsを開く: https://sheets.google.com")
            console.print("2. 「+」ボタンで新しいスプレッドシートを作成")
            console.print("3. URLから以下の形式でIDをコピー:")
            console.print("   https://docs.google.com/spreadsheets/d/[bold cyan]【ここがID】[/bold cyan]/edit")
            console.print()

            spreadsheet_id = input("スプレッドシートIDを入力: ").strip()

            if not spreadsheet_id:
                console.print("[red]IDが入力されていません[/red]")
                return None

        # 認証
        console.print("\n[blue]認証中...[/blue]")
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
        console.print(f"\n[blue]CSVファイル読み込み中: {csv_file}[/blue]")

        df = pd.read_csv(csv_file, encoding='utf-8')
        console.print(f"[green]✅ データ読み込み完了: {len(df)}行 x {len(df.columns)}列[/green]")

        # NaN値を空文字列に置換
        df = df.fillna('')

        # データを文字列に変換
        df = df.astype(str)

        # スプレッドシートを開く
        console.print(f"\n[blue]スプレッドシートに接続中...[/blue]")
        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
            console.print(f"[green]✅ スプレッドシート「{spreadsheet.title}」に接続成功[/green]")
        except Exception as e:
            console.print(f"[red]❌ スプレッドシートを開けません: {e}[/red]")
            console.print("[yellow]ヒント: スプレッドシートの共有設定を確認してください[/yellow]")
            return None

        # 最初のワークシートを取得
        worksheet = spreadsheet.sheet1
        worksheet.update_title("Ultra_Think_Data")

        # データ準備
        header = df.columns.tolist()
        values = df.values.tolist()
        all_data = [header] + values

        # ワークシートのサイズを調整
        console.print(f"\n[blue]ワークシートサイズ調整中...[/blue]")
        worksheet.resize(rows=len(all_data), cols=len(header))

        # プログレスバーでアップロード
        console.print(f"\n[blue]データアップロード中...[/blue]")

        # バッチサイズ
        batch_size = 1000
        total_rows = len(all_data)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:

            upload_task = progress.add_task("アップロード中...", total=total_rows)

            for i in range(0, total_rows, batch_size):
                end_idx = min(i + batch_size, total_rows)
                batch_data = all_data[i:end_idx]

                # バッチデータをアップロード
                start_cell = f'A{i+1}'
                worksheet.update(batch_data, range_name=start_cell)

                progress.update(upload_task, advance=len(batch_data))

        # フォーマット設定
        console.print(f"\n[blue]フォーマット設定中...[/blue]")
        worksheet.freeze(rows=1)  # ヘッダー行を固定

        # 完了
        console.print(f"\n[green]✨ アップロード完了！[/green]")
        console.print(f"\n[bold cyan]📊 スプレッドシートURL:[/bold cyan]")
        console.print(f"[link]{spreadsheet.url}[/link]")

        # 情報を保存
        with open("sheet_info.txt", "w") as f:
            f.write(f"URL: {spreadsheet.url}\n")
            f.write(f"ID: {spreadsheet.id}\n")
            f.write(f"Title: {spreadsheet.title}\n")
            f.write(f"Updated: {datetime.now().isoformat()}\n")

        console.print(f"\n[green]💾 接続情報を sheet_info.txt に保存しました[/green]")

        # 使用方法を表示
        console.print("\n[bold yellow]📝 次のステップ:[/bold yellow]")
        console.print("1. 上記URLをブラウザで開く")
        console.print("2. データの編集・フィルタリング・ソートが可能")
        console.print("3. 変更は自動保存されます")
        console.print("\n[yellow]ヒント: データ → フィルタを作成 で問題のある行を抽出できます[/yellow]")

        return spreadsheet.url

    except Exception as e:
        console.print(f"[red]❌ エラー: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # コマンドライン引数でIDを受け取ることも可能
    import sys
    sheet_id = sys.argv[1] if len(sys.argv) > 1 else None

    url = upload_to_existing_sheet(sheet_id)

    if url:
        console.print(f"\n[green]✅ 成功！ブラウザでURLを開いてデータを確認してください[/green]")
