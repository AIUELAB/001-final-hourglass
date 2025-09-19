#!/usr/bin/env python3
"""
システム動作確認テスト

このスクリプトは、Docker & n8n統合監視システムの
基本的な動作を確認します。
"""

import os
import sys
import requests
import subprocess
from pathlib import Path

def test_docker_connection():
    """Docker接続テスト"""
    print("🐳 Docker接続テスト...")

    try:
        result = subprocess.run(['docker', 'version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  ✅ Dockerが利用可能です")
            return True
        else:
            print("  ❌ Dockerが利用できません")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  ❌ Dockerコマンドが見つかりません")
        return False

def test_n8n_connection():
    """n8n接続テスト"""
    print("\n🔧 n8n接続テスト...")

    n8n_url = os.getenv('N8N_BASE_URL', 'http://localhost:5678')

    try:
        response = requests.get(f"{n8n_url}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ n8nに接続できました ({n8n_url})")
            return True
        else:
            print(f"  ⚠️ n8nは起動していますが、ヘルスチェックに失敗 ({response.status_code})")
            return False
    except requests.exceptions.RequestException:
        print(f"  ❌ n8nに接続できません ({n8n_url})")
        print("  n8nを起動してください:")
        print("  docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n")
        return False

def test_flask_app():
    """Flaskアプリケーションテスト"""
    print("\n🌐 Flaskアプリケーションテスト...")

    try:
        # app.pyのインポートテスト
        sys.path.insert(0, str(Path.cwd()))
        from app import app

        print("  ✅ Flaskアプリケーションのインポートに成功")

        # 基本的なルートのテスト
        with app.test_client() as client:
            response = client.get('/')
            if response.status_code == 200:
                print("  ✅ メインページにアクセス可能")
            else:
                print(f"  ❌ メインページへのアクセスに失敗 ({response.status_code})")
                return False

            # APIエンドポイントのテスト
            response = client.get('/api/containers')
            if response.status_code == 200:
                print("  ✅ コンテナAPIにアクセス可能")
            else:
                print(f"  ⚠️ コンテナAPIへのアクセスに失敗 ({response.status_code})")

            response = client.get('/api/n8n/workflows')
            if response.status_code == 200:
                print("  ✅ n8nワークフローAPIにアクセス可能")
            else:
                print(f"  ⚠️ n8nワークフローAPIへのアクセスに失敗 ({response.status_code})")

        return True

    except ImportError as e:
        print(f"  ❌ Flaskアプリケーションのインポートに失敗: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Flaskアプリケーションのテストに失敗: {e}")
        return False

def test_file_structure():
    """ファイル構造テスト"""
    print("\n📁 ファイル構造テスト...")

    required_files = [
        'app.py',
        'requirements.txt',
        'templates/index.html',
        'static/css/style.css',
        'static/js/app.js'
    ]

    required_dirs = [
        'n8n_integration',
        'n8n_integration/config',
        'n8n_integration/services',
        'n8n_integration/examples'
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path}")

    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
        else:
            print(f"  ✅ {dir_path}/")

    if missing_files:
        print(f"  ❌ 不足しているファイル: {', '.join(missing_files)}")

    if missing_dirs:
        print(f"  ❌ 不足しているディレクトリ: {', '.join(missing_dirs)}")

    return len(missing_files) == 0 and len(missing_dirs) == 0

def test_dependencies():
    """依存関係テスト"""
    print("\n📦 依存関係テスト...")

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
        print(f"  ❌ 不足しているパッケージ: {', '.join(missing_packages)}")
        print("  以下のコマンドでインストールしてください:")
        print(f"  pip install {' '.join(missing_packages)}")
        return False

    return True

def main():
    """メイン関数"""
    print("🧪 Docker & n8n統合監視システム - 動作確認テスト")
    print("=" * 60)

    tests = [
        ("ファイル構造", test_file_structure),
        ("依存関係", test_dependencies),
        ("Docker接続", test_docker_connection),
        ("n8n接続", test_n8n_connection),
        ("Flaskアプリケーション", test_flask_app)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name}テストでエラーが発生: {e}")
            results.append((test_name, False))

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n結果: {passed}/{total} テストが成功")

    if passed == total:
        print("🎉 すべてのテストが成功しました！")
        print("システムを起動できます:")
        print("  python start_n8n_monitor.py")
        return True
    else:
        print("⚠️ 一部のテストが失敗しました")
        print("問題を修正してから再実行してください")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ テストが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
