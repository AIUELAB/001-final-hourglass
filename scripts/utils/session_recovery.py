#!/usr/bin/env python3
"""
セッション復元システム
Claude Code/Cursorクラッシュ後の復元機能

機能:
- クラッシュ検出
- セッション状態の復元
- ユーザーインターフェース
- 自動復元オプション
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
STATUS_FILE = SESSION_DIR / "STATUS.md"
LOG_FILE = SESSION_DIR / "SESSION_LOG.md"
RECOVERY_DIR = SESSION_DIR / "recovery"
SNAPSHOT_DIR = SESSION_DIR / "snapshots"

# Serena統合
sys.path.insert(0, str(Path(__file__).parent))
try:
    from serena_memory_integration import SerenaMemoryManager

    SERENA_AVAILABLE = True
except ImportError:
    SERENA_AVAILABLE = False


class SessionRecovery:
    """セッション復元クラス"""

    def __init__(self):
        self.serena = SerenaMemoryManager(PROJECT_ROOT) if SERENA_AVAILABLE else None

    def detect_crash(self) -> bool:
        """
        クラッシュを検出

        Returns:
            クラッシュが検出された場合True
        """
        # 復元ポイントの存在チェック
        recovery_file = RECOVERY_DIR / "last_stable.json"

        if not recovery_file.exists():
            return False

        # 最終更新から一定時間経過しているかチェック
        try:
            with open(recovery_file, "r", encoding="utf-8") as f:
                recovery_data = json.load(f)

            last_update = datetime.fromisoformat(recovery_data["timestamp"])
            elapsed = (datetime.now() - last_update).total_seconds()

            # 10分以上更新がない場合はクラッシュの可能性
            if elapsed > 600:
                return True

        except Exception:
            pass

        return False

    def list_recovery_points(self) -> List[Dict]:
        """
        利用可能な復元ポイントをリスト

        Returns:
            復元ポイントのリスト
        """
        recovery_points = []

        # ファイルベースの復元ポイント
        recovery_file = RECOVERY_DIR / "last_stable.json"
        if recovery_file.exists():
            try:
                with open(recovery_file, "r", encoding="utf-8") as f:
                    recovery_data = json.load(f)

                recovery_points.append(
                    {
                        "source": "file",
                        "timestamp": recovery_data["timestamp"],
                        "session_id": recovery_data["session_id"],
                        "git_commit": recovery_data.get("git_commit"),
                    }
                )
            except Exception:
                pass

        # Serenaメモリの復元ポイント
        if self.serena:
            latest_session = self.serena.load_latest_session()
            if latest_session:
                recovery_points.append(
                    {
                        "source": "serena",
                        "timestamp": latest_session.get("last_updated"),
                        "session_id": latest_session.get("session_id"),
                        "current_task": latest_session.get("current_task"),
                    }
                )

        # スナップショットからの復元ポイント
        if SNAPSHOT_DIR.exists():
            for snapshot in sorted(SNAPSHOT_DIR.glob("*.md"), reverse=True)[:5]:
                if snapshot.name != "latest.md":
                    recovery_points.append(
                        {"source": "snapshot", "timestamp": snapshot.stat().st_mtime, "file": str(snapshot.name)}
                    )

        return recovery_points

    def restore_from_file(self, recovery_file: Path) -> bool:
        """
        ファイルから復元

        Args:
            recovery_file: 復元ファイルのパス

        Returns:
            成功時True
        """
        try:
            with open(recovery_file, "r", encoding="utf-8") as f:
                recovery_data = json.load(f)

            print(f"📦 Restoring from: {recovery_file.name}")
            print(f"   Session ID: {recovery_data.get('session_id')}")
            print(f"   Timestamp: {recovery_data.get('timestamp')}")

            # STATUS.mdの確認
            if STATUS_FILE.exists():
                print("✅ STATUS.md found")
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    status_content = f.read()
                    print(f"   Preview: {status_content[:200]}...")

            # SESSION_LOG.mdの確認
            if LOG_FILE.exists():
                print("✅ SESSION_LOG.md found")
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    log_lines = f.readlines()
                    print(f"   Entries: {len([l for l in log_lines if l.startswith('##')])} sessions")

            return True

        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False

    def restore_from_serena(self) -> bool:
        """
        Serenaメモリから復元

        Returns:
            成功時True
        """
        if not self.serena:
            print("❌ Serena not available")
            return False

        try:
            latest_session = self.serena.load_latest_session()

            if not latest_session:
                print("❌ No session found in Serena memory")
                return False

            print("📦 Restoring from Serena memory")
            print(f"   Session ID: {latest_session.get('session_id')}")
            print(f"   Last updated: {latest_session.get('last_updated')}")
            print(f"   Current task: {latest_session.get('current_task', 'None')}")

            # TODO情報の表示
            todos = latest_session.get("todos")
            if todos:
                print("\n📋 TODOs:")
                for i, todo in enumerate(todos[:5], 1):
                    status = todo.get("status", "pending")
                    content = todo.get("content", "")
                    print(f"   {i}. [{status}] {content}")

            # 決定履歴の表示
            decisions = self.serena.read_memory("decisions") or []
            if decisions:
                print("\n💡 Recent decisions:")
                for decision in decisions[-3:]:
                    print(f"   - {decision.get('decision')}")

            # ブロッカーの表示
            blockers = self.serena.read_memory("blockers") or []
            active_blockers = [b for b in blockers if not b.get("resolved")]
            if active_blockers:
                print("\n⚠️ Active blockers:")
                for blocker in active_blockers:
                    print(f"   - [{blocker.get('severity')}] {blocker.get('blocker')}")

            return True

        except Exception as e:
            print(f"❌ Serena restore failed: {e}")
            return False

    def restore_from_snapshot(self, snapshot_file: Path) -> bool:
        """
        スナップショットから復元

        Args:
            snapshot_file: スナップショットファイル

        Returns:
            成功時True
        """
        try:
            with open(snapshot_file, "r", encoding="utf-8") as f:
                snapshot_content = f.read()

            print(f"📦 Restoring from snapshot: {snapshot_file.name}")
            print(f"\n{snapshot_content[:500]}...\n")

            return True

        except Exception as e:
            print(f"❌ Snapshot restore failed: {e}")
            return False

    def interactive_recovery(self):
        """対話的復元インターフェース"""
        print("=" * 60)
        print("🔄 Session Recovery System")
        print("=" * 60)

        # クラッシュ検出
        if self.detect_crash():
            print("⚠️ Potential crash detected")
        else:
            print("ℹ️ No crash detected, but recovery available")

        print()

        # 復元ポイントのリスト
        recovery_points = self.list_recovery_points()

        if not recovery_points:
            print("❌ No recovery points available")
            return

        print(f"📋 Available recovery points: {len(recovery_points)}")
        print()

        for i, point in enumerate(recovery_points, 1):
            source = point.get("source", "unknown")
            timestamp = point.get("timestamp", "unknown")

            print(f"{i}. [{source.upper()}] {timestamp}")

            if source == "file":
                print(f"   Session: {point.get('session_id')}")
                print(f"   Git: {point.get('git_commit', 'N/A')[:8]}")
            elif source == "serena":
                print(f"   Task: {point.get('current_task', 'None')}")
            elif source == "snapshot":
                print(f"   File: {point.get('file')}")

            print()

        # 復元方法の選択
        print("Select recovery method:")
        print("1. File-based recovery")
        print("2. Serena memory recovery")
        print("3. Snapshot recovery")
        print("4. View all (no restore)")
        print("0. Cancel")

        try:
            choice = input("\nEnter choice (0-4): ").strip()

            if choice == "1":
                recovery_file = RECOVERY_DIR / "last_stable.json"
                self.restore_from_file(recovery_file)

            elif choice == "2":
                self.restore_from_serena()

            elif choice == "3":
                latest_snapshot = SNAPSHOT_DIR / "latest.md"
                if latest_snapshot.exists():
                    target = latest_snapshot.resolve()
                    self.restore_from_snapshot(target)
                else:
                    print("❌ No snapshot available")

            elif choice == "4":
                # すべての情報を表示
                print("\n" + "=" * 60)
                self.restore_from_file(RECOVERY_DIR / "last_stable.json")
                print("\n" + "=" * 60)
                self.restore_from_serena()

            elif choice == "0":
                print("❌ Recovery cancelled")

            else:
                print("❌ Invalid choice")

        except KeyboardInterrupt:
            print("\n❌ Recovery cancelled")


# ===========================================
# コマンドラインインターフェース
# ===========================================


def main():
    """メイン関数"""
    recovery = SessionRecovery()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "detect":
            if recovery.detect_crash():
                print("⚠️ Crash detected")
                sys.exit(1)
            else:
                print("✅ No crash detected")
                sys.exit(0)

        elif command == "list":
            points = recovery.list_recovery_points()
            print(f"Recovery points: {len(points)}")
            for point in points:
                print(json.dumps(point, indent=2))

        elif command == "restore-file":
            recovery_file = RECOVERY_DIR / "last_stable.json"
            recovery.restore_from_file(recovery_file)

        elif command == "restore-serena":
            recovery.restore_from_serena()

        elif command == "interactive" or command == "ui":
            recovery.interactive_recovery()

        else:
            print("Usage: session_recovery.py [detect|list|restore-file|restore-serena|interactive]")
    else:
        # デフォルト: 対話的復元
        recovery.interactive_recovery()


if __name__ == "__main__":
    main()
