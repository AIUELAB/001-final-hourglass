#!/usr/bin/env python3
"""
Ultra Think 自動検証フック
CSVファイル変更時に自動的に表示名を検証・修正

作成日: 2025-08-31
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json

class AutoValidationHook:
    """ファイル変更時の自動検証フック"""
    
    def __init__(self):
        self.config_file = Path("auto_validation_config.json")
        self.load_config()
    
    def load_config(self):
        """設定を読み込み"""
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            # デフォルト設定
            self.config = {
                "enabled": True,
                "auto_validate_on_change": True,
                "auto_sync_after_validation": True,
                "validation_script": "auto_display_name_validator.py",
                "sync_script": "direct_sync.py",
                "log_file": "auto_validation_log.json"
            }
            self.save_config()
    
    def save_config(self):
        """設定を保存"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def log_action(self, action: str, details: dict):
        """アクションをログに記録"""
        log_file = Path(self.config["log_file"])
        
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
        else:
            logs = []
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        }
        
        logs.append(log_entry)
        logs = logs[-100:]  # 最新100件のみ保持
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def run_validation(self, csv_file: str) -> bool:
        """検証スクリプトを実行"""
        if not self.config.get("auto_validate_on_change", True):
            return False
        
        print(f"\n🔍 自動検証開始: {csv_file}")
        
        try:
            result = subprocess.run(
                [sys.executable, self.config["validation_script"]],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("✅ 自動検証完了")
                self.log_action("validation_success", {"file": csv_file})
                return True
            else:
                print(f"❌ 自動検証エラー: {result.stderr}")
                self.log_action("validation_error", {
                    "file": csv_file,
                    "error": result.stderr
                })
                return False
                
        except subprocess.TimeoutExpired:
            print("⚠️ 検証タイムアウト")
            self.log_action("validation_timeout", {"file": csv_file})
            return False
        except Exception as e:
            print(f"❌ 検証実行エラー: {e}")
            self.log_action("validation_exception", {
                "file": csv_file,
                "error": str(e)
            })
            return False
    
    def run_sync(self) -> bool:
        """同期スクリプトを実行"""
        if not self.config.get("auto_sync_after_validation", True):
            return False
        
        print(f"\n🔄 自動同期開始")
        
        try:
            result = subprocess.run(
                [sys.executable, self.config["sync_script"]],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print("✅ 自動同期完了")
                self.log_action("sync_success", {})
                return True
            else:
                print(f"❌ 自動同期エラー: {result.stderr}")
                self.log_action("sync_error", {"error": result.stderr})
                return False
                
        except subprocess.TimeoutExpired:
            print("⚠️ 同期タイムアウト")
            self.log_action("sync_timeout", {})
            return False
        except Exception as e:
            print(f"❌ 同期実行エラー: {e}")
            self.log_action("sync_exception", {"error": str(e)})
            return False
    
    def process_file_change(self, csv_file: str):
        """ファイル変更を処理"""
        if not self.config.get("enabled", True):
            print("⚠️ 自動検証は無効化されています")
            return
        
        print("=" * 60)
        print("🎯 Ultra Think 自動検証フック起動")
        print("=" * 60)
        
        # 検証実行
        if self.run_validation(csv_file):
            # 検証成功したら同期
            self.run_sync()
        
        print("=" * 60)
        print("✨ 自動処理完了")
        print("=" * 60)


def integrate_with_watcher():
    """auto_sync_watcher.pyと統合するための設定を追加"""
    watcher_file = Path("auto_sync_watcher.py")
    
    if not watcher_file.exists():
        print("⚠️ auto_sync_watcher.pyが見つかりません")
        return
    
    # 設定ファイルを更新
    config_file = Path("auto_sync_config.json")
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}
    
    # 検証フックを追加
    config["validation_hook"] = {
        "enabled": True,
        "script": "auto_validation_hook.py",
        "run_before_sync": True
    }
    
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("✅ auto_sync_watcher.pyとの統合設定完了")


def main():
    """メイン処理"""
    hook = AutoValidationHook()
    
    # コマンドライン引数からファイル名を取得
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        hook.process_file_change(csv_file)
    else:
        # 統合設定モード
        print("🔧 自動検証フックセットアップ")
        integrate_with_watcher()
        hook.save_config()
        print("✅ セットアップ完了")
        print("\n📝 使い方:")
        print("  python auto_validation_hook.py [CSVファイル名]")
        print("\nまたは、auto_sync_watcher.pyと統合して自動実行")


if __name__ == "__main__":
    main()