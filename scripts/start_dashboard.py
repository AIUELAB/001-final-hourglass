#!/usr/bin/env python3
"""
エピソードメインデータベース ダッシュボード起動スクリプト

使用方法:
    python scripts/start_dashboard.py          # v7を起動（デフォルト）
    python scripts/start_dashboard.py --v6     # v6を起動
    python scripts/start_dashboard.py --port 8888  # ポート指定
    python scripts/start_dashboard.py --no-open    # ブラウザを開かない
"""

import argparse
import http.server
import os
import socketserver
import subprocess
import sys
import webbrowser
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
PRESERVED_DIR = PROJECT_ROOT / "preserved"

# ダッシュボードファイル
DASHBOARDS = {
    "v7": "episode_database_dashboard_v7.html",
    "v6": "episode_database_dashboard_v6.html",
    "v5": "episode_database_dashboard_v5.html",
}

DEFAULT_PORT = 8080
DEFAULT_VERSION = "v7"


def check_port_in_use(port: int) -> bool:
    """ポートが使用中か確認"""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def kill_process_on_port(port: int):
    """指定ポートのプロセスを終了"""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                subprocess.run(["kill", "-9", pid], capture_output=True)
            print(f"  ポート {port} のプロセスを終了しました")
    except Exception:
        pass


def start_server(port: int, version: str, open_browser: bool = True):
    """HTTPサーバーを起動"""
    dashboard_file = DASHBOARDS.get(version)
    if not dashboard_file:
        print(f"❌ バージョン '{version}' は存在しません")
        print(f"   利用可能: {', '.join(DASHBOARDS.keys())}")
        sys.exit(1)

    dashboard_path = PRESERVED_DIR / dashboard_file
    if not dashboard_path.exists():
        print(f"❌ ダッシュボードファイルが見つかりません: {dashboard_path}")
        sys.exit(1)

    # ポートが使用中なら解放
    if check_port_in_use(port):
        print(f"⚠️  ポート {port} は使用中です。解放します...")
        kill_process_on_port(port)
        import time

        time.sleep(1)

    print("=" * 60)
    print(f"📊 エピソードメインデータベース ダッシュボード {version.upper()}")
    print("=" * 60)
    print()
    print(f"  ファイル: {dashboard_file}")
    print(f"  ポート: {port}")
    print(f"  URL: http://localhost:{port}/{dashboard_file}")
    print()
    print("  終了するには Ctrl+C を押してください")
    print("=" * 60)
    print()

    # ディレクトリ変更
    os.chdir(PRESERVED_DIR)

    # ブラウザを開く
    if open_browser:
        url = f"http://localhost:{port}/{dashboard_file}"
        webbrowser.open(url)

    # サーバー起動
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✅ サーバーを停止しました")


def main():
    parser = argparse.ArgumentParser(description="エピソードメインデータベース ダッシュボード起動")
    parser.add_argument("--v7", action="store_true", default=True, help="v7ダッシュボードを起動（デフォルト）")
    parser.add_argument("--v6", action="store_true", help="v6ダッシュボードを起動")
    parser.add_argument("--v5", action="store_true", help="v5ダッシュボードを起動")
    parser.add_argument(
        "--port", "-p", type=int, default=DEFAULT_PORT, help=f"ポート番号（デフォルト: {DEFAULT_PORT}）"
    )
    parser.add_argument("--no-open", action="store_true", help="ブラウザを自動で開かない")

    args = parser.parse_args()

    # バージョン決定
    if args.v6:
        version = "v6"
    elif args.v5:
        version = "v5"
    else:
        version = "v7"

    start_server(args.port, version, not args.no_open)


if __name__ == "__main__":
    main()
