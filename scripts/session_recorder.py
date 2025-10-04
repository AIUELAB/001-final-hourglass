#!/usr/bin/env python3
"""
セッション記録システム
Claude Code/Cursorのクラッシュ対策のための自動記録

機能:
- リアルタイムセッション記録
- STATUS.md自動更新
- SESSION_LOG.md会話履歴記録
- スナップショット作成
- Serena MCP統合（メモリシステム）
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import fcntl
import hashlib
import sys

# Serena統合モジュールをインポート
sys.path.insert(0, str(Path(__file__).parent))
try:
    from serena_memory_integration import SerenaMemoryManager
    SERENA_AVAILABLE = True
except ImportError:
    SERENA_AVAILABLE = False

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
STATUS_FILE = SESSION_DIR / "STATUS.md"
LOG_FILE = SESSION_DIR / "SESSION_LOG.md"
SNAPSHOT_DIR = SESSION_DIR / "snapshots"
RECOVERY_DIR = SESSION_DIR / "recovery"


class SessionRecorder:
    """セッション記録管理クラス"""

    def __init__(self):
        self.session_id = self._generate_session_id()
        self.ensure_directories()

        # Serena統合
        if SERENA_AVAILABLE:
            self.serena = SerenaMemoryManager(PROJECT_ROOT)
        else:
            self.serena = None

    def _generate_session_id(self) -> str:
        """セッションIDを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}"

    def ensure_directories(self):
        """必要なディレクトリを作成"""
        SESSION_DIR.mkdir(exist_ok=True)
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        RECOVERY_DIR.mkdir(exist_ok=True)

    def _file_lock(self, file_path: Path):
        """ファイルロックを取得（競合防止）"""
        lock_file = file_path.with_suffix(".lock")
        return open(lock_file, "w")

    def record_prompt(self, prompt: str, metadata: Optional[Dict] = None):
        """
        ユーザープロンプトを記録

        Args:
            prompt: ユーザーのプロンプト
            metadata: 追加メタデータ
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # SESSION_LOG.mdに追記
        lock = self._file_lock(LOG_FILE)
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n## {timestamp}\n")
                f.write(f"**User**: {prompt}\n\n")

                if metadata:
                    f.write("**Metadata**:\n")
                    f.write(f"```json\n{json.dumps(metadata, indent=2, ensure_ascii=False)}\n```\n\n")

        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()

        # STATUS.md更新
        self.update_status(last_prompt=prompt)

        # Serenaメモリに保存
        if self.serena:
            self.serena.write_memory(
                key=f"prompt_{timestamp.replace(' ', '_').replace(':', '')}",
                value={
                    "prompt": prompt,
                    "timestamp": timestamp,
                    "metadata": metadata
                },
                ttl=86400  # 24時間保持
            )

    def record_response(self, response: str, metadata: Optional[Dict] = None):
        """
        アシスタント応答を記録

        Args:
            response: アシスタントの応答
            metadata: 追加メタデータ
        """
        lock = self._file_lock(LOG_FILE)
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

            with open(LOG_FILE, "a", encoding="utf-8") as f:
                # 応答が長い場合は省略
                if len(response) > 500:
                    response_summary = response[:500] + f"\n\n[...省略 ({len(response)} 文字)]"
                else:
                    response_summary = response

                f.write(f"**Assistant**: {response_summary}\n\n")

                if metadata:
                    f.write("**Metadata**:\n")
                    f.write(f"```json\n{json.dumps(metadata, indent=2, ensure_ascii=False)}\n```\n\n")

        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()

        # Serenaメモリに保存
        if self.serena:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.serena.write_memory(
                key=f"response_{timestamp}",
                value={
                    "response": response[:500],  # 最初の500文字のみ
                    "full_length": len(response),
                    "timestamp": timestamp,
                    "metadata": metadata
                },
                ttl=86400  # 24時間保持
            )

    def update_status(
        self,
        current_task: Optional[str] = None,
        last_prompt: Optional[str] = None,
        context: Optional[Dict] = None,
        todos: Optional[List[Dict]] = None,
    ):
        """
        STATUS.mdを更新

        Args:
            current_task: 現在のタスク
            last_prompt: 最後のプロンプト
            context: コンテキスト情報
            todos: TODOリスト
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 既存のSTATUS.mdを読み込み（存在する場合）
        existing_data = self._read_status()

        # 更新
        if current_task is not None:
            existing_data["current_task"] = current_task
        if last_prompt is not None:
            existing_data["last_prompt"] = last_prompt
        if context is not None:
            existing_data["context"] = {**existing_data.get("context", {}), **context}
        if todos is not None:
            existing_data["todos"] = todos

        existing_data["last_updated"] = timestamp
        existing_data["session_id"] = self.session_id

        # STATUS.mdに書き込み
        lock = self._file_lock(STATUS_FILE)
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                f.write("# セッションステータス\n\n")
                f.write(f"**最終更新**: {existing_data['last_updated']}\n")
                f.write(f"**セッションID**: {existing_data['session_id']}\n\n")

                # 現在のタスク
                f.write("## 現在のタスク\n\n")
                if existing_data.get("current_task"):
                    f.write(f"{existing_data['current_task']}\n\n")
                else:
                    f.write("_なし_\n\n")

                # TODOリスト
                if existing_data.get("todos"):
                    f.write("## TODOリスト\n\n")
                    for todo in existing_data["todos"]:
                        status_icon = "✅" if todo.get("status") == "completed" else "⏳" if todo.get("status") == "in_progress" else "⬜"
                        f.write(f"- {status_icon} {todo.get('content', '')}\n")
                    f.write("\n")

                # 進行中の会話
                f.write("## 進行中の会話\n\n")
                if existing_data.get("last_prompt"):
                    f.write(f"- 最後のプロンプト: {existing_data['last_prompt'][:100]}...\n\n")

                # コンテキスト
                if existing_data.get("context"):
                    f.write("## コンテキスト\n\n")
                    for key, value in existing_data["context"].items():
                        f.write(f"- **{key}**: {value}\n")
                    f.write("\n")

                # メモ
                f.write("## メモ\n\n")
                f.write("_クラッシュ時にはこのファイルから復元できます_\n\n")

        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()

        # Serenaメモリに保存（セッション状態）
        if self.serena:
            self.serena.save_session_state({
                "session_id": existing_data.get("session_id"),
                "current_task": existing_data.get("current_task"),
                "last_prompt": existing_data.get("last_prompt"),
                "context": existing_data.get("context"),
                "todos": existing_data.get("todos"),
                "last_updated": existing_data.get("last_updated")
            })

    def _read_status(self) -> Dict:
        """既存のSTATUS.mdからデータを読み込み"""
        if not STATUS_FILE.exists():
            return {}

        # 簡易的なパーサー（Markdownから情報抽出）
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                content = f.read()

            # 基本的なフィールドのみ抽出
            data = {}

            # セッションIDを抽出
            if "**セッションID**:" in content:
                session_id_line = [line for line in content.split("\n") if "**セッションID**:" in line]
                if session_id_line:
                    data["session_id"] = session_id_line[0].split(":", 1)[1].strip()

            return data
        except Exception:
            return {}

    def create_snapshot(self, snapshot_name: Optional[str] = None):
        """
        現在のセッション状態のスナップショットを作成

        Args:
            snapshot_name: スナップショット名（省略時は自動生成）
        """
        if snapshot_name is None:
            snapshot_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        snapshot_file = SNAPSHOT_DIR / f"{snapshot_name}.md"

        with open(snapshot_file, "w", encoding="utf-8") as f:
            f.write(f"# セッションスナップショット: {snapshot_name}\n\n")
            f.write(f"**作成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # STATUS.mdの内容をコピー
            if STATUS_FILE.exists():
                f.write("## ステータス\n\n")
                with open(STATUS_FILE, "r", encoding="utf-8") as status_f:
                    f.write(status_f.read())
                f.write("\n\n")

            # 最新のSESSION_LOGから抜粋
            if LOG_FILE.exists():
                f.write("## 最新のログ（最後の5エントリ）\n\n")
                with open(LOG_FILE, "r", encoding="utf-8") as log_f:
                    lines = log_f.readlines()
                    # 最後の100行を取得
                    recent_lines = lines[-100:] if len(lines) > 100 else lines
                    f.write("".join(recent_lines))

        # latest.mdへのシンボリックリンク更新
        latest_link = SNAPSHOT_DIR / "latest.md"
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(snapshot_file.name)

        return snapshot_file

    def save_recovery_point(self):
        """復元ポイントを保存"""
        recovery_data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "status_file": str(STATUS_FILE),
            "log_file": str(LOG_FILE),
            "git_commit": self._get_git_commit(),
            "working_directory": str(PROJECT_ROOT),
        }

        recovery_file = RECOVERY_DIR / "last_stable.json"
        with open(recovery_file, "w", encoding="utf-8") as f:
            json.dump(recovery_data, f, indent=2, ensure_ascii=False)

        # Serenaメモリにも保存
        if self.serena:
            self.serena.write_memory(
                key="last_recovery_point",
                value=recovery_data,
                ttl=None  # 永続化
            )

            # チェックポイントとしても保存
            self.serena.save_checkpoint({
                "files_modified": [],  # 実際には追跡する
                "tasks_completed": [],
                "current_focus": "Recovery point saved",
                "git_commit": recovery_data["git_commit"]
            })

    def _get_git_commit(self) -> Optional[str]:
        """現在のGitコミットハッシュを取得"""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None


# ===================================
# コマンドラインインターフェース
# ===================================

def main():
    """メイン関数（CLIテスト用）"""
    import sys

    recorder = SessionRecorder()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "prompt" and len(sys.argv) > 2:
            prompt_text = " ".join(sys.argv[2:])
            recorder.record_prompt(prompt_text)
            print(f"✅ Prompt recorded: {prompt_text[:50]}...")

        elif command == "response" and len(sys.argv) > 2:
            response_text = " ".join(sys.argv[2:])
            recorder.record_response(response_text)
            print(f"✅ Response recorded: {response_text[:50]}...")

        elif command == "snapshot":
            snapshot_file = recorder.create_snapshot()
            print(f"✅ Snapshot created: {snapshot_file}")

        elif command == "recovery":
            recorder.save_recovery_point()
            print("✅ Recovery point saved")

        else:
            print("Usage: session_recorder.py [prompt|response|snapshot|recovery] [text]")
    else:
        # デフォルト: ステータス更新のみ
        recorder.update_status(
            context={
                "project": "001-final-hourglass",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        print("✅ Session status updated")


if __name__ == "__main__":
    main()
