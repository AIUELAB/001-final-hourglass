#!/usr/bin/env python3
"""
最適化版同期システムのテストスクリプト
設定ファイルと依存関係をチェックして動作確認
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def test_dependencies():
    """依存関係のテスト"""
    print("🔍 依存関係チェック中...")
    
    missing_packages = []
    
    try:
        import pandas
        print("✅ pandas")
    except ImportError:
        missing_packages.append("pandas")
    
    try:
        import gspread
        print("✅ gspread")
    except ImportError:
        missing_packages.append("gspread")
    
    try:
        from google.oauth2.service_account import Credentials
        print("✅ google-auth")
    except ImportError:
        missing_packages.append("google-auth")
    
    try:
        from rich.console import Console
        print("✅ rich")
    except ImportError:
        missing_packages.append("rich")
    
    try:
        import concurrent.futures
        print("✅ concurrent.futures (標準ライブラリ)")
    except ImportError:
        missing_packages.append("concurrent.futures")
    
    try:
        from watchdog.observers import Observer
        print("✅ watchdog")
    except ImportError:
        print("⚠️ watchdog (オプション)")
        missing_packages.append("watchdog")
    
    if missing_packages:
        print(f"\n❌ 不足パッケージ: {', '.join(missing_packages)}")
        print("インストール: pip install " + " ".join(missing_packages))
        return False
    else:
        print("\n✅ 全ての依存関係が満たされています")
        return True

def test_config_files():
    """設定ファイルのテスト"""
    print("\n📋 設定ファイルチェック中...")
    
    # sheets_config.json
    config_path = Path('sheets_config.json')
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            required_keys = ['spreadsheet_id', 'auto_sync_enabled']
            missing_keys = [key for key in required_keys if key not in config]
            
            if missing_keys:
                print(f"⚠️ sheets_config.json - 不足キー: {missing_keys}")
            else:
                print("✅ sheets_config.json")
                
        except json.JSONDecodeError:
            print("❌ sheets_config.json - JSON形式エラー")
            return False
    else:
        print("❌ sheets_config.json が見つかりません")
        return False
    
    # startup_config.json
    startup_config_path = Path('startup_config.json')
    if startup_config_path.exists():
        try:
            with open(startup_config_path, 'r', encoding='utf-8') as f:
                startup_config = json.load(f)
            
            required_sections = ['startup_settings', 'performance_settings']
            missing_sections = [section for section in required_sections if section not in startup_config]
            
            if missing_sections:
                print(f"⚠️ startup_config.json - 不足セクション: {missing_sections}")
            else:
                print("✅ startup_config.json")
                
        except json.JSONDecodeError:
            print("❌ startup_config.json - JSON形式エラー")
            return False
    else:
        print("❌ startup_config.json が見つかりません")
        return False
    
    return True

def test_credentials():
    """Google認証ファイルのテスト"""
    print("\n🔐 認証ファイルチェック中...")
    
    creds_path = Path('/Users/admin/Documents/AIUELAB/001-final-hourglass/key/credentials.json')
    if creds_path.exists():
        try:
            with open(creds_path, 'r') as f:
                creds = json.load(f)
            
            required_keys = ['type', 'project_id', 'client_email', 'private_key']
            missing_keys = [key for key in required_keys if key not in creds]
            
            if missing_keys:
                print(f"⚠️ credentials.json - 不足キー: {missing_keys}")
                return False
            else:
                print("✅ Google認証ファイル")
                return True
                
        except json.JSONDecodeError:
            print("❌ credentials.json - JSON形式エラー")
            return False
    else:
        print("❌ credentials.jsonが見つかりません")
        print(f"   期待パス: {creds_path}")
        return False

def test_csv_files():
    """CSVファイルのテスト"""
    print("\n📁 CSVファイルチェック中...")
    
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    
    if not csv_files:
        print("⚠️ ultra_think_*.csvファイルが見つかりません")
        return False
    
    # 最新ファイルを検出
    latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    file_size_mb = latest_file.stat().st_size / (1024 * 1024)
    mod_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
    
    print(f"✅ 最新CSVファイル: {latest_file.name}")
    print(f"   サイズ: {file_size_mb:.2f} MB")
    print(f"   更新日時: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # CSVの構造をチェック
    try:
        import pandas as pd
        df = pd.read_csv(latest_file)
        print(f"   データサイズ: {len(df)}行 × {len(df.columns)}列")
        
        # 重要な列の存在チェック
        important_columns = ['person_id', 'person_name_ja', 'person_name_en']
        existing_columns = [col for col in important_columns if col in df.columns]
        print(f"   重要列: {len(existing_columns)}/{len(important_columns)} 存在")
        
        return True
        
    except Exception as e:
        print(f"❌ CSVファイル読み込みエラー: {e}")
        return False

def test_system_requirements():
    """システム要件のテスト"""
    print("\n🖥️ システム要件チェック中...")
    
    # Python バージョン
    python_version = sys.version_info
    print(f"🐍 Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("❌ Python 3.8以上が必要です")
        return False
    
    # macOS チェック
    if sys.platform == 'darwin':
        print("✅ macOS環境（音声通知対応）")
        
        # 音声ファイルのチェック
        sound_files = [
            '/System/Library/Sounds/Glass.aiff',
            '/System/Library/Sounds/Sosumi.aiff'
        ]
        
        for sound_file in sound_files:
            if Path(sound_file).exists():
                print(f"✅ {Path(sound_file).name}")
            else:
                print(f"⚠️ {Path(sound_file).name} が見つかりません")
    else:
        print(f"ℹ️ {sys.platform}環境（音声通知は制限される可能性があります）")
    
    return True

def run_dry_run_test():
    """ドライランテスト"""
    print("\n🚀 ドライランテスト実行中...")
    
    try:
        # 設定を読み込み
        with open('sheets_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        with open('startup_config.json', 'r', encoding='utf-8') as f:
            startup_config = json.load(f)
        
        # パフォーマンス設定を表示
        perf_settings = startup_config.get('performance_settings', {})
        print(f"⚡ 並列ワーカー数: {perf_settings.get('max_parallel_workers', 10)}")
        print(f"📦 バッチサイズ: {perf_settings.get('batch_processing_size', 1000)}")
        print(f"🔄 リトライ回数: {perf_settings.get('retry_attempts', 3)}")
        
        # ブラウザ設定を表示
        browser_settings = startup_config.get('browser_settings', {})
        auto_open = startup_config.get('startup_settings', {}).get('auto_open_browser', False)
        print(f"🌐 ブラウザ自動起動: {'有効' if auto_open else '無効'}")
        
        # 音声通知設定を表示
        audio_settings = startup_config.get('notification_settings', {}).get('audio_notifications', {})
        audio_enabled = audio_settings.get('enabled', False)
        print(f"🔊 音声通知: {'有効' if audio_enabled else '無効'}")
        
        if audio_enabled:
            success_sound = audio_settings.get('sync_complete_sound', 'なし')
            error_sound = audio_settings.get('error_sound', 'なし')
            print(f"   成功音: {Path(success_sound).name if success_sound != 'なし' else 'なし'}")
            print(f"   エラー音: {Path(error_sound).name if error_sound != 'なし' else 'なし'}")
        
        print("✅ ドライランテスト完了")
        return True
        
    except Exception as e:
        print(f"❌ ドライランテストエラー: {e}")
        return False

def main():
    """メイン関数"""
    print("🔬 Ultra Think 最適化同期システム - テストスイート")
    print("=" * 60)
    
    tests = [
        ("依存関係", test_dependencies),
        ("設定ファイル", test_config_files),
        ("認証ファイル", test_credentials),
        ("CSVファイル", test_csv_files),
        ("システム要件", test_system_requirements),
        ("ドライラン", run_dry_run_test)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}テスト中にエラー: {e}")
            results.append((test_name, False))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 結果: {passed}/{total} テスト通過")
    
    if passed == total:
        print("\n🎉 全テストが通過しました！")
        print("   python auto_startup_sync_optimized.py で実行してください")
        return True
    else:
        print(f"\n⚠️ {total - passed}件のテストが失敗しました")
        print("   上記エラーを修正してから実行してください")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)