#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI協調分析システム稼働状況チェック
Claude CodeとCodex MCPサーバーの協議システムの状態を確認
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path


def check_codex_server_status():
    """Codex MCPサーバーの稼働状況を確認"""
    print("=" * 60)
    print("🔍 Codex MCPサーバー状態確認")
    print("=" * 60)

    # プロセス確認
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )

        codex_processes = [
            line for line in result.stdout.split('\n')
            if 'codex' in line.lower() and 'grep' not in line
        ]

        if codex_processes:
            print("✅ Codex関連プロセスが見つかりました:")
            for proc in codex_processes[:3]:  # 最初の3つを表示
                parts = proc.split()
                if len(parts) > 10:
                    cmd = ' '.join(parts[10:])[:100]
                    print(f"  - PID {parts[1]}: {cmd}...")
        else:
            print("❌ Codexプロセスが見つかりません")

    except Exception as e:
        print(f"❌ プロセス確認エラー: {e}")

    # ポート確認（8765）
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8765))
        sock.close()

        if result == 0:
            print("✅ ポート8765がリッスン状態です")
        else:
            print("❌ ポート8765に接続できません")

    except Exception as e:
        print(f"❌ ポート確認エラー: {e}")

    # ログファイル確認
    log_file = Path("codex_server.log")
    if log_file.exists():
        # 最終更新時刻
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        print(f"📝 ログファイル最終更新: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

        # 最新のログエントリ
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    print(f"  最新エントリ: {last_line[:100]}...")
        except Exception as e:
            print(f"  ログ読み取りエラー: {e}")
    else:
        print("❌ ログファイルが見つかりません")

    return codex_processes


def check_startup_config():
    """起動設定を確認"""
    print("\n" + "=" * 60)
    print("⚙️ 起動設定確認")
    print("=" * 60)

    config_file = Path("startup_config.json")

    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Codex設定があるか確認
        has_codex = False

        if 'codex_settings' in config:
            print("✅ Codex設定セクションが存在します")
            has_codex = True
            settings = config['codex_settings']
            print(f"  - 自動起動: {settings.get('auto_start', False)}")
            print(f"  - ポート: {settings.get('port', 'N/A')}")
        else:
            print("❌ Codex設定セクションが存在しません")

        # Serena設定
        if 'serena_settings' in config:
            print("\n✅ Serena設定セクションが存在します")
            settings = config['serena_settings']
            print(f"  - 自動起動: {settings.get('auto_start_serena', False)}")
            print(f"  - ポート: {settings.get('serena_port', 'N/A')}")

        return has_codex
    else:
        print("❌ startup_config.jsonが見つかりません")
        return False


def check_collaboration_files():
    """AI協調システムファイルの確認"""
    print("\n" + "=" * 60)
    print("📁 AI協調システムファイル")
    print("=" * 60)

    files = [
        "claude_codex_collaboration.py",
        "codex_mcp_server.py",
        "codex_double_check.py"
    ]

    found_files = []
    for filename in files:
        file_path = Path(filename)
        if file_path.exists():
            size = file_path.stat().st_size
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            print(f"✅ {filename}")
            print(f"   - サイズ: {size:,} bytes")
            print(f"   - 更新日時: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            found_files.append(filename)
        else:
            print(f"❌ {filename} - 見つかりません")

    return found_files


def check_cache_and_results():
    """キャッシュと実行結果の確認"""
    print("\n" + "=" * 60)
    print("💾 キャッシュと実行結果")
    print("=" * 60)

    # キャッシュディレクトリ
    cache_dir = Path(".collaboration_cache")
    if cache_dir.exists():
        cache_files = list(cache_dir.glob("*"))
        print(f"✅ キャッシュディレクトリ: {len(cache_files)}ファイル")
    else:
        print("❌ キャッシュディレクトリが存在しません")

    # 検証結果ファイル
    verification_files = list(Path(".").glob("codex_verification_report_*.json"))
    if verification_files:
        print(f"✅ 検証レポート: {len(verification_files)}件")
        # 最新のレポート
        latest = max(verification_files, key=lambda p: p.stat().st_mtime)
        mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        print(f"   最新: {latest.name} ({mtime.strftime('%Y-%m-%d %H:%M')})")
    else:
        print("❌ 検証レポートが見つかりません")


def generate_status_report():
    """稼働状況レポート生成"""
    print("\n" + "=" * 60)
    print("📊 AI協調分析システム稼働状況サマリー")
    print("=" * 60)

    status = {
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }

    # Codexサーバー
    codex_procs = check_codex_server_status()
    status["components"]["codex_server"] = {
        "running": len(codex_procs) > 0,
        "process_count": len(codex_procs)
    }

    # 起動設定
    has_config = check_startup_config()
    status["components"]["startup_config"] = {
        "configured": has_config
    }

    # ファイル
    files = check_collaboration_files()
    status["components"]["files"] = {
        "found": len(files),
        "list": files
    }

    # キャッシュ
    check_cache_and_results()

    # 総合判定
    print("\n" + "=" * 60)
    print("🎯 総合判定")
    print("=" * 60)

    if codex_procs and has_config:
        print("✅ AI協調分析システムは完全に稼働中です")
        status["overall"] = "FULLY_OPERATIONAL"
    elif codex_procs:
        print("⚠️ Codexサーバーは動作中ですが、自動起動設定がありません")
        status["overall"] = "PARTIALLY_OPERATIONAL"
    elif files:
        print("⚠️ システムファイルは存在しますが、サーバーが停止しています")
        status["overall"] = "STOPPED"
    else:
        print("❌ AI協調分析システムは設定されていません")
        status["overall"] = "NOT_CONFIGURED"

    # レポート保存
    report_file = f"ai_collaboration_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print(f"\n📁 レポート保存: {report_file}")

    return status


def main():
    """メイン処理"""
    print("AI協調分析システム稼働状況チェック")
    print("実行時刻:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()

    status = generate_status_report()

    # 推奨事項
    print("\n" + "=" * 60)
    print("💡 推奨事項")
    print("=" * 60)

    if status["overall"] == "NOT_CONFIGURED":
        print("1. Codex MCPサーバーをインストール:")
        print("   codex mcp install")
        print("2. startup_config.jsonにCodex設定を追加")
        print("3. 起動フックスクリプトを更新")

    elif status["overall"] == "STOPPED":
        print("1. Codex MCPサーバーを起動:")
        print("   python3 codex_mcp_server.py")
        print("2. 自動起動設定を追加")

    elif status["overall"] == "PARTIALLY_OPERATIONAL":
        print("1. startup_config.jsonにCodex自動起動設定を追加")
        print("2. 起動フックスクリプトを更新")

    else:
        print("✅ システムは正常に稼働しています")

    return 0


if __name__ == "__main__":
    sys.exit(main())
