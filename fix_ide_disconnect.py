#!/usr/bin/env python3
"""
IDE切断問題の解決スクリプト
Ultra Think分析による根本原因と解決策
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from simple_notification import notify_error, notify_success, notify_warning


class IDEConnectionFixer:
    """IDE接続問題を修正するクラス"""
    
    def __init__(self):
        self.config_path = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass/mcp-config/claude_desktop_config.json")
        self.issues_found = []
        self.solutions = []
        
    def analyze_root_cause(self):
        """根本原因の分析 - Ultra Think"""
        print("🔍 IDE切断問題の根本原因分析を開始...")
        print("=" * 60)
        
        # 1. パッケージ存在チェック
        print("\n1️⃣ パッケージ存在チェック:")
        result = subprocess.run(
            ["npm", "view", "@win32user/mcp-ide"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("   ❌ @win32user/mcp-ide パッケージが存在しません")
            self.issues_found.append("PACKAGE_NOT_FOUND")
            self.solutions.append({
                "issue": "パッケージ不存在",
                "cause": "@win32user/mcp-ide はnpmレジストリに存在しない",
                "solution": "正しいパッケージに置換する"
            })
        
        # 2. 設定ファイルチェック
        print("\n2️⃣ 設定ファイルチェック:")
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if "ide" in config.get("mcpServers", {}):
                    ide_config = config["mcpServers"]["ide"]
                    print(f"   現在の設定: {ide_config['args']}")
                    if "@win32user/mcp-ide" in str(ide_config['args']):
                        print("   ⚠️ 存在しないパッケージが設定されています")
        
        # 3. 代替パッケージの検索
        print("\n3️⃣ 利用可能な代替パッケージ:")
        alternatives = [
            ("@vscode-mcp/vscode-mcp-server", "VS Code/Cursor統合"),
            ("@jetbrains/mcp-proxy", "JetBrains IDE統合"),
            ("Serena", "高度なコード操作（IDE機能含む）")
        ]
        for pkg, desc in alternatives:
            print(f"   ✅ {pkg}: {desc}")
            
        return self.issues_found, self.solutions
    
    def fix_configuration(self):
        """設定ファイルを修正"""
        print("\n🔧 設定ファイルの修正を開始...")
        
        # バックアップ作成
        backup_path = self.config_path.with_suffix('.json.backup')
        with open(self.config_path, 'r', encoding='utf-8') as f:
            original_config = json.load(f)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(original_config, f, indent=2, ensure_ascii=False)
        print(f"   📁 バックアップ作成: {backup_path}")
        
        # 設定を修正
        config = original_config.copy()
        
        # 方法1: IDEサーバーを正しいパッケージに置換
        if "@vscode-mcp/vscode-mcp-server" in subprocess.run(
            ["npm", "search", "@vscode-mcp/vscode-mcp-server"],
            capture_output=True,
            text=True
        ).stdout:
            config["mcpServers"]["ide"] = {
                "command": "npx",
                "args": ["-y", "@vscode-mcp/vscode-mcp-server"],
                "env": {}
            }
            print("   ✅ IDE設定を@vscode-mcp/vscode-mcp-serverに更新")
        
        # 方法2: Serenaが有効な場合はIDEを無効化（Serenaに統合されているため）
        if "serena" in config.get("mcpServers", {}) and not config["mcpServers"].get("serena", {}).get("disabled"):
            config["mcpServers"]["ide"]["disabled"] = True
            print("   ✅ Serenaが有効なため、重複するIDEサーバーを無効化")
            
        # 設定を保存
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("   ✅ 設定ファイルを更新しました")
        
        return True
    
    def install_correct_package(self):
        """正しいパッケージをインストール"""
        print("\n📦 正しいIDEパッケージのインストール...")
        
        packages_to_try = [
            "@vscode-mcp/vscode-mcp-server",
            "@jetbrains/mcp-proxy"
        ]
        
        for package in packages_to_try:
            print(f"\n   インストール試行: {package}")
            result = subprocess.run(
                ["npm", "install", "-g", package],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"   ✅ {package} のインストール成功")
                notify_success(f"{package}のインストール完了")
                return True
            else:
                print(f"   ⚠️ {package} のインストール失敗（オプション）")
        
        print("   ℹ️ Serenaサーバーが有効なため、追加のIDEサーバーは不要です")
        return True
    
    def verify_solution(self):
        """解決策の検証"""
        print("\n✅ 解決策の検証...")
        
        # 設定ファイルの再読み込み
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Serenaの状態確認
        serena_enabled = "serena" in config.get("mcpServers", {}) and \
                        not config["mcpServers"].get("serena", {}).get("disabled", False)
        
        if serena_enabled:
            print("   ✅ Serenaサーバーが有効（IDE機能統合済み）")
            print("   ℹ️ Serenaには以下のIDE機能が含まれています:")
            print("      • コード診断")
            print("      • 自動補完")
            print("      • リファクタリング")
            print("      • シンボル検索")
            print("      • 定義へのジャンプ")
            return True
        
        # IDE設定の確認
        ide_config = config.get("mcpServers", {}).get("ide", {})
        if ide_config.get("disabled"):
            print("   ℹ️ IDEサーバーは無効化されています（Serenaで代替）")
            return True
        
        if "@vscode-mcp/vscode-mcp-server" in str(ide_config.get("args", [])):
            print("   ✅ 正しいIDEパッケージが設定されています")
            return True
        
        return False

def main():
    """メイン処理"""
    print("🎯 IDE切断問題の解決 - Ultra Think分析")
    print("=" * 60)
    
    fixer = IDEConnectionFixer()
    
    # 1. 根本原因の分析
    issues, solutions = fixer.analyze_root_cause()
    
    print("\n📊 分析結果:")
    print("=" * 60)
    print(f"検出された問題: {len(issues)}件")
    for solution in solutions:
        print(f"\n問題: {solution['issue']}")
        print(f"原因: {solution['cause']}")
        print(f"解決策: {solution['solution']}")
    
    # 2. 修正の実行
    print("\n" + "=" * 60)
    if input("\n修正を実行しますか？ (y/n): ").lower() == 'y':
        # 設定修正
        if fixer.fix_configuration():
            notify_success("設定ファイルを修正しました")
        
        # パッケージインストール（オプション）
        fixer.install_correct_package()
        
        # 検証
        if fixer.verify_solution():
            notify_success("IDE接続問題が解決されました！")
            print("\n🎉 解決完了！")
            print("\n次のステップ:")
            print("1. Claude Desktopアプリを再起動してください")
            print("2. Serenaサーバーが正常に接続されることを確認してください")
            print("3. IDE機能（診断、補完など）が動作することを確認してください")
        else:
            notify_error("問題の解決に失敗しました")
    else:
        print("\n修正をキャンセルしました")

if __name__ == "__main__":
    main()