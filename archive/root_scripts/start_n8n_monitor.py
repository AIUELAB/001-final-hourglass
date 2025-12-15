#!/usr/bin/env python3
"""
n8n統合システム起動スクリプト

このスクリプトは、n8n統合システムを起動します。
Dockerコンテナ監視とn8nワークフロー管理の統合UIを提供します。
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """必要な依存関係をチェック"""
    print("🔍 依存関係をチェック中...")

    required_packages = [
        'flask',
        'docker',
        'requests'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}")

    if missing_packages:
        print(f"\n❌ 不足しているパッケージ: {', '.join(missing_packages)}")
        print("以下のコマンドでインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    print("✅ すべての依存関係が満たされています")
    return True

def check_docker():
    """Dockerの状態をチェック"""
    print("\n🐳 Dockerの状態をチェック中...")

    try:
        result = subprocess.run(['docker', 'version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  ✅ Dockerが起動しています")
            return True
        else:
            print("  ❌ Dockerが起動していません")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  ❌ Dockerコマンドが見つかりません")
        return False

def check_n8n():
    """n8nの状態をチェック"""
    print("\n🔧 n8nの状態をチェック中...")

    import requests

    n8n_url = os.getenv('N8N_BASE_URL', 'http://localhost:5678')

    try:
        response = requests.get(f"{n8n_url}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ n8nが起動しています ({n8n_url})")
            return True
        else:
            print(f"  ⚠️ n8nは起動していますが、ヘルスチェックに失敗 ({response.status_code})")
            return False
    except requests.exceptions.RequestException:
        print(f"  ❌ n8nに接続できません ({n8n_url})")
        print("  n8nを起動してください:")
        print("  docker run -it --rm \\")
        print("    --name n8n \\")
        print("    -p 5678:5678 \\")
        print("    -v ~/.n8n:/home/node/.n8n \\")
        print("    n8nio/n8n")
        return False

def setup_environment():
    """環境変数を設定"""
    print("\n⚙️ 環境変数を設定中...")

    # デフォルト設定
    env_vars = {
        'N8N_BASE_URL': 'http://localhost:5678',
        'N8N_API_KEY': '',
        'FLASK_ENV': 'development',
        'FLASK_DEBUG': '1'
    }

    # .envファイルが存在する場合は読み込み
    env_file = Path('.env')
    if env_file.exists():
        print("  📁 .envファイルを読み込み中...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

    # 環境変数を設定
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
            print(f"  🔧 {key} = {value}")

    print("✅ 環境変数の設定が完了しました")

def create_directories():
    """必要なディレクトリを作成"""
    print("\n📁 ディレクトリを作成中...")

    directories = [
        'logs',
        'data',
        'temp'
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"  📁 {directory}/")

    print("✅ ディレクトリの作成が完了しました")

def start_application():
    """アプリケーションを起動"""
    print("\n🚀 アプリケーションを起動中...")

    try:
        # Flaskアプリケーションを起動
        from app import app

        print("  🌐 Webサーバーを起動中...")
        print("  📱 ブラウザで http://localhost:5000 にアクセスしてください")
        print("  ⏹️ 停止するには Ctrl+C を押してください")
        print()

        app.run(debug=True, host='0.0.0.0', port=5000)

    except ImportError as e:
        print(f"  ❌ アプリケーションのインポートに失敗: {e}")
        print("  app.pyファイルが存在することを確認してください")
        return False
    except Exception as e:
        print(f"  ❌ アプリケーションの起動に失敗: {e}")
        return False

def main():
    """メイン関数"""
    print("🚀 n8n統合システム起動スクリプト")
    print("=" * 50)

    # 依存関係チェック
    if not check_dependencies():
        sys.exit(1)

    # Dockerチェック
    if not check_docker():
        print("\n⚠️ Dockerが起動していませんが、続行します")
        print("Dockerコンテナ監視機能は利用できません")

    # n8nチェック
    if not check_n8n():
        print("\n⚠️ n8nが起動していませんが、続行します")
        print("n8nワークフロー管理機能は利用できません")

    # 環境設定
    setup_environment()

    # ディレクトリ作成
    create_directories()

    # アプリケーション起動
    if not start_application():
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ ユーザーによって中断されました")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
