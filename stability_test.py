#!/usr/bin/env python3
"""
MCP管理システム - 5分間安定性テスト
"""

import time
import subprocess
import datetime
import os
import psutil

class StabilityTester:
    def __init__(self, duration=300, check_interval=30):
        self.duration = duration  # 5分
        self.check_interval = check_interval  # 30秒ごと
        self.log_file = f"stability_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        # カウンター
        self.total_checks = 0
        self.serena_failures = 0
        self.codex_failures = 0
        self.memory_failures = 0
        self.sequential_failures = 0

    def log(self, message):
        """ログ出力"""
        print(message)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')

    def check_process(self, pattern):
        """プロセスチェック"""
        try:
            result = subprocess.run(['pgrep', '-f', pattern],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def check_port(self, port):
        """ポートチェック"""
        try:
            result = subprocess.run(['lsof', '-i', f':{port}'],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def check_servers(self):
        """サーバー状態チェック"""
        self.total_checks += 1
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')

        self.log(f"\n[{timestamp}] チェック #{self.total_checks}")
        self.log("-" * 40)

        # Serena
        if self.check_process("serena-mcp-server"):
            self.log("  ✅ Serena: 稼働中")
        else:
            self.log("  ❌ Serena: 停止")
            self.serena_failures += 1

        # Codex
        if self.check_process("codex_mcp_server"):
            self.log("  ✅ Codex: 稼働中")
        else:
            self.log("  ❌ Codex: 停止")
            self.codex_failures += 1

        # Memory
        if self.check_process("@modelcontextprotocol/server-memory"):
            self.log("  ✅ Memory: 稼働中")
        else:
            self.log("  ⚠️ Memory: 停止（NPXサーバー）")
            self.memory_failures += 1

        # Sequential
        if self.check_process("@modelcontextprotocol/server-sequential-thinking"):
            self.log("  ✅ Sequential: 稼働中")
        else:
            self.log("  ⚠️ Sequential: 停止（NPXサーバー）")
            self.sequential_failures += 1

        # ポート状態
        self.log("\n  ポート状態:")
        if self.check_port(8000):
            self.log("    • Port 8000 (Serena): ✅ 使用中")
        else:
            self.log("    • Port 8000 (Serena): ⚠️ 未使用")

        if self.check_port(8765):
            self.log("    • Port 8765 (Codex): ✅ 使用中")
        else:
            self.log("    • Port 8765 (Codex): ⚠️ 未使用")

    def run(self):
        """テスト実行"""
        self.log("=" * 48)
        self.log("📊 MCP管理システム - 5分間安定性テスト")
        self.log("=" * 48)
        self.log(f"\n📅 開始時刻: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"⏱️ テスト時間: {self.duration//60}分間")
        self.log(f"🔄 チェック間隔: {self.check_interval}秒")
        self.log(f"📝 ログファイル: {self.log_file}\n")

        start_time = time.time()

        self.log("🔄 安定性テスト開始...")
        self.log("=" * 40)

        while True:
            elapsed = time.time() - start_time
            if elapsed >= self.duration:
                break

            remaining = self.duration - elapsed
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)

            self.check_servers()
            self.log(f"\n  ⏳ 残り時間: {minutes}分{seconds}秒")

            # 次のチェックまで待機
            time.sleep(self.check_interval)

        # 最終レポート
        self.generate_report()

    def generate_report(self):
        """最終レポート生成"""
        self.log("\n" + "=" * 40)
        self.log("📊 安定性テスト結果")
        self.log("=" * 40)
        self.log(f"\n📅 終了時刻: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"⏱️ テスト時間: {self.duration//60}分間")
        self.log(f"🔍 総チェック回数: {self.total_checks}\n")

        self.log("📈 稼働率統計:")

        if self.total_checks > 0:
            serena_uptime = int(100 * (self.total_checks - self.serena_failures) / self.total_checks)
            codex_uptime = int(100 * (self.total_checks - self.codex_failures) / self.total_checks)
            memory_uptime = int(100 * (self.total_checks - self.memory_failures) / self.total_checks)
            sequential_uptime = int(100 * (self.total_checks - self.sequential_failures) / self.total_checks)

            self.log(f"  • Serena: {serena_uptime}% (失敗: {self.serena_failures}/{self.total_checks})")
            self.log(f"  • Codex: {codex_uptime}% (失敗: {self.codex_failures}/{self.total_checks})")
            self.log(f"  • Memory: {memory_uptime}% (失敗: {self.memory_failures}/{self.total_checks})")
            self.log(f"  • Sequential: {sequential_uptime}% (失敗: {self.sequential_failures}/{self.total_checks})")

        # 総合評価
        total_failures = self.serena_failures + self.codex_failures
        if total_failures == 0:
            self.log("\n✅ 結果: 主要サーバー安定 - Serena/Codexが5分間正常稼働")
        else:
            self.log(f"\n⚠️ 結果: 一部不安定 - 主要サーバー失敗{total_failures}回")

        self.log(f"\n📝 詳細ログは {self.log_file} に保存されました")
        self.log("=" * 40)

if __name__ == "__main__":
    tester = StabilityTester(duration=300, check_interval=30)  # 5分間、30秒間隔
    tester.run()