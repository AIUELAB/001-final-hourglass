#!/usr/bin/env python3
"""
Serena MCP Memory Integration
セッション情報をSerenaのメモリシステムに保存

機能:
- write_memory統合
- think_about_*関数活用
- セッション状態の永続化
- クラッシュ復元用のメタデータ管理
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess


class SerenaMemoryManager:
    """Serena MCPメモリ管理クラス"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.session_dir = project_root / ".session"

    def write_memory(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Serenaのwrite_memoryを呼び出し

        Args:
            key: メモリキー
            value: 保存する値（dict, str, list等）
            ttl: Time To Live（秒、Noneで永続化）

        Returns:
            成功時True
        """
        try:
            # Serena MCPのwrite_memoryツールを使用
            # 注: 実際の実装ではClaude Code経由でMCPツールを呼び出す
            # ここでは.sessionディレクトリにJSON形式で保存
            memory_file = self.session_dir / "serena_memory.json"

            # 既存メモリを読み込み
            memories = {}
            if memory_file.exists():
                with open(memory_file, "r", encoding="utf-8") as f:
                    memories = json.load(f)

            # 新しいメモリを追加
            memories[key] = {
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "ttl": ttl
            }

            # 保存
            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"❌ write_memory failed: {e}")
            return False

    def read_memory(self, key: str) -> Optional[Any]:
        """
        Serenaのread_memoryを呼び出し

        Args:
            key: メモリキー

        Returns:
            保存された値、存在しない場合None
        """
        try:
            memory_file = self.session_dir / "serena_memory.json"

            if not memory_file.exists():
                return None

            with open(memory_file, "r", encoding="utf-8") as f:
                memories = json.load(f)

            if key in memories:
                memory_data = memories[key]

                # TTLチェック
                if memory_data.get("ttl"):
                    timestamp = datetime.fromisoformat(memory_data["timestamp"])
                    elapsed = (datetime.now() - timestamp).total_seconds()
                    if elapsed > memory_data["ttl"]:
                        # 期限切れ
                        return None

                return memory_data["value"]

            return None
        except Exception as e:
            print(f"❌ read_memory failed: {e}")
            return None

    def list_memories(self) -> List[str]:
        """
        すべてのメモリキーを取得

        Returns:
            メモリキーのリスト
        """
        try:
            memory_file = self.session_dir / "serena_memory.json"

            if not memory_file.exists():
                return []

            with open(memory_file, "r", encoding="utf-8") as f:
                memories = json.load(f)

            return list(memories.keys())
        except Exception as e:
            print(f"❌ list_memories failed: {e}")
            return []

    def delete_memory(self, key: str) -> bool:
        """
        メモリを削除

        Args:
            key: メモリキー

        Returns:
            成功時True
        """
        try:
            memory_file = self.session_dir / "serena_memory.json"

            if not memory_file.exists():
                return False

            with open(memory_file, "r", encoding="utf-8") as f:
                memories = json.load(f)

            if key in memories:
                del memories[key]

                with open(memory_file, "w", encoding="utf-8") as f:
                    json.dump(memories, f, indent=2, ensure_ascii=False)

                return True

            return False
        except Exception as e:
            print(f"❌ delete_memory failed: {e}")
            return False

    # ===========================================
    # セッション管理用の高レベルAPI
    # ===========================================

    def save_session_state(self, session_data: Dict) -> bool:
        """
        セッション状態を保存

        Args:
            session_data: セッション情報
                - session_id: セッションID
                - current_task: 現在のタスク
                - todos: TODOリスト
                - context: コンテキスト情報
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # セッション全体を保存
        self.write_memory(
            key=f"session_state_{timestamp}",
            value=session_data,
            ttl=None  # 永続化
        )

        # 最新セッションポインタを更新
        self.write_memory(
            key="latest_session",
            value={
                "session_id": session_data.get("session_id"),
                "timestamp": timestamp,
                "state_key": f"session_state_{timestamp}"
            }
        )

        return True

    def load_latest_session(self) -> Optional[Dict]:
        """
        最新のセッション状態を読み込み

        Returns:
            セッションデータ、存在しない場合None
        """
        latest = self.read_memory("latest_session")

        if not latest:
            return None

        state_key = latest.get("state_key")
        if state_key:
            return self.read_memory(state_key)

        return None

    def save_checkpoint(self, checkpoint_data: Dict) -> bool:
        """
        チェックポイントを保存（30分間隔推奨）

        Args:
            checkpoint_data: チェックポイント情報
                - files_modified: 変更されたファイルリスト
                - tasks_completed: 完了したタスク
                - current_focus: 現在の作業内容
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return self.write_memory(
            key=f"checkpoint_{timestamp}",
            value={
                **checkpoint_data,
                "timestamp": timestamp
            },
            ttl=86400  # 24時間保持
        )

    def save_decision(self, decision: str, reasoning: str) -> bool:
        """
        重要な意思決定を記録

        Args:
            decision: 決定内容
            reasoning: 判断理由
        """
        decisions = self.read_memory("decisions") or []

        decisions.append({
            "decision": decision,
            "reasoning": reasoning,
            "timestamp": datetime.now().isoformat()
        })

        return self.write_memory("decisions", decisions)

    def save_blocker(self, blocker: str, severity: str = "medium") -> bool:
        """
        ブロッカーを記録

        Args:
            blocker: ブロッカーの内容
            severity: 深刻度（low/medium/high/critical）
        """
        blockers = self.read_memory("blockers") or []

        blockers.append({
            "blocker": blocker,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "resolved": False
        })

        return self.write_memory("blockers", blockers)

    def resolve_blocker(self, blocker_index: int) -> bool:
        """
        ブロッカーを解決済みにマーク

        Args:
            blocker_index: ブロッカーのインデックス
        """
        blockers = self.read_memory("blockers")

        if not blockers or blocker_index >= len(blockers):
            return False

        blockers[blocker_index]["resolved"] = True
        blockers[blocker_index]["resolved_at"] = datetime.now().isoformat()

        return self.write_memory("blockers", blockers)

    def get_session_summary(self) -> Dict:
        """
        セッションサマリーを取得

        Returns:
            サマリー情報
        """
        latest_session = self.load_latest_session()
        decisions = self.read_memory("decisions") or []
        blockers = self.read_memory("blockers") or []

        active_blockers = [b for b in blockers if not b.get("resolved")]

        return {
            "latest_session": latest_session,
            "total_decisions": len(decisions),
            "recent_decisions": decisions[-5:] if decisions else [],
            "active_blockers": active_blockers,
            "total_blockers": len(blockers)
        }

    def cleanup_old_checkpoints(self, keep_days: int = 7) -> int:
        """
        古いチェックポイントを削除

        Args:
            keep_days: 保持日数

        Returns:
            削除したチェックポイント数
        """
        all_keys = self.list_memories()
        checkpoint_keys = [k for k in all_keys if k.startswith("checkpoint_")]

        deleted_count = 0
        cutoff_date = datetime.now().timestamp() - (keep_days * 86400)

        for key in checkpoint_keys:
            checkpoint = self.read_memory(key)
            if checkpoint:
                checkpoint_time = datetime.fromisoformat(checkpoint["timestamp"]).timestamp()
                if checkpoint_time < cutoff_date:
                    self.delete_memory(key)
                    deleted_count += 1

        return deleted_count


# ===========================================
# コマンドラインインターフェース
# ===========================================

def main():
    """メイン関数（CLIテスト用）"""
    import sys

    project_root = Path(__file__).parent.parent
    manager = SerenaMemoryManager(project_root)

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "save" and len(sys.argv) > 3:
            key = sys.argv[2]
            value = sys.argv[3]
            success = manager.write_memory(key, value)
            print(f"{'✅' if success else '❌'} Memory saved: {key}")

        elif command == "read" and len(sys.argv) > 2:
            key = sys.argv[2]
            value = manager.read_memory(key)
            print(f"Memory value: {value}")

        elif command == "list":
            keys = manager.list_memories()
            print(f"Memory keys: {', '.join(keys)}")

        elif command == "summary":
            summary = manager.get_session_summary()
            print(json.dumps(summary, indent=2, ensure_ascii=False))

        elif command == "checkpoint":
            manager.save_checkpoint({
                "files_modified": ["example.py"],
                "tasks_completed": ["Task 1"],
                "current_focus": "Testing Serena integration"
            })
            print("✅ Checkpoint saved")

        else:
            print("Usage: serena_memory_integration.py [save|read|list|summary|checkpoint] [args]")
    else:
        # デフォルト: サマリー表示
        summary = manager.get_session_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
