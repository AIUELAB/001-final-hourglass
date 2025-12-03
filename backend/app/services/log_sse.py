"""
ログ専用 Server-Sent Events マネージャー

Phase 2: バックエンドログ収集システム

ログエントリのリアルタイム配信を担当。
レベル/セッションIDフィルタリング機能付き。
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, List, Optional, Set


@dataclass
class LogSSEClient:
    """ログSSEクライアント情報"""

    client_id: str
    queue: asyncio.Queue
    connected_at: float = field(default_factory=time.time)
    # フィルタリング条件
    level_filter: Optional[Set[str]] = None  # 監視するレベル（None=全て）
    session_filter: Optional[str] = None  # 監視するセッションID


class LogSSEManager:
    """ログSSE接続を管理するクラス"""

    def __init__(self):
        self.clients: Dict[str, LogSSEClient] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 30

    async def connect(
        self,
        level_filter: Optional[List[str]] = None,
        session_filter: Optional[str] = None,
    ) -> LogSSEClient:
        """
        新しいクライアント接続を作成

        Args:
            level_filter: 監視するレベルのリスト（例: ["error", "warn"]）
            session_filter: 監視するセッションID

        Returns:
            LogSSEClient インスタンス
        """
        client_id = str(uuid.uuid4())
        client = LogSSEClient(
            client_id=client_id,
            queue=asyncio.Queue(),
            level_filter=set(level_filter) if level_filter else None,
            session_filter=session_filter,
        )
        self.clients[client_id] = client
        print(
            f"[LogSSE] Client connected: {client_id} "
            f"(levels={level_filter}, session={session_filter}, total={len(self.clients)})"
        )
        return client

    def disconnect(self, client_id: str):
        """クライアント接続を解除"""
        if client_id in self.clients:
            del self.clients[client_id]
            print(f"[LogSSE] Client disconnected: {client_id} " f"(remaining: {len(self.clients)})")

    def _should_send(self, client: LogSSEClient, log_entry: dict) -> bool:
        """
        クライアントにログを送信すべきか判定

        Args:
            client: 対象クライアント
            log_entry: ログエントリデータ

        Returns:
            送信すべき場合True
        """
        # レベルフィルタ
        if client.level_filter:
            entry_level = log_entry.get("level", "log")
            if entry_level not in client.level_filter:
                return False

        # セッションフィルタ
        if client.session_filter:
            entry_session = log_entry.get("session_id") or log_entry.get("sessionId")
            if entry_session != client.session_filter:
                return False

        return True

    async def broadcast_log(self, log_entry: dict):
        """
        ログエントリをフィルタリングしながらブロードキャスト

        Args:
            log_entry: ログエントリデータ
        """
        message = {"event": "log", "data": log_entry}

        disconnected = []
        for client_id, client in self.clients.items():
            try:
                if self._should_send(client, log_entry):
                    await client.queue.put(message)
            except Exception as e:
                print(f"[LogSSE] Broadcast failed for {client_id}: {e}")
                disconnected.append(client_id)

        for client_id in disconnected:
            self.disconnect(client_id)

    async def broadcast_batch(self, log_entries: List[dict]):
        """
        複数のログエントリを一括ブロードキャスト

        Args:
            log_entries: ログエントリのリスト
        """
        for entry in log_entries:
            await self.broadcast_log(entry)

    async def broadcast_operation(self, operation: dict, event_type: str = "operation"):
        """
        操作イベントをブロードキャスト

        Args:
            operation: 操作データ
            event_type: イベントタイプ（operation_start / operation_end）
        """
        message = {"event": event_type, "data": operation}

        disconnected = []
        for client_id, client in self.clients.items():
            try:
                # セッションフィルタがある場合はチェック
                if client.session_filter:
                    op_session = operation.get("session_id") or operation.get("sessionId")
                    if op_session != client.session_filter:
                        continue
                await client.queue.put(message)
            except Exception as e:
                print(f"[LogSSE] Operation broadcast failed for {client_id}: {e}")
                disconnected.append(client_id)

        for client_id in disconnected:
            self.disconnect(client_id)

    async def event_generator(self, client: LogSSEClient) -> AsyncGenerator[str, None]:
        """
        SSEイベントジェネレーター

        Args:
            client: クライアント情報

        Yields:
            SSE形式の文字列
        """
        try:
            while True:
                try:
                    message = await asyncio.wait_for(client.queue.get(), timeout=self._heartbeat_interval + 5)
                    yield self.format_sse(event=message["event"], data=message["data"])
                except asyncio.TimeoutError:
                    # タイムアウト時はハートビート送信
                    yield self.format_sse(
                        event="heartbeat",
                        data={
                            "timestamp": time.time(),
                            "client_id": client.client_id,
                        },
                    )
        except asyncio.CancelledError:
            pass

    def format_sse(self, event: str, data: dict) -> str:
        """
        SSE形式にフォーマット

        Args:
            event: イベント名
            data: データ辞書

        Returns:
            SSE形式文字列
        """
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def start_heartbeat(self):
        """ハートビートタスクを開始"""
        if self._heartbeat_task is not None:
            return

        async def heartbeat_loop():
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                if self.clients:
                    message = {"event": "heartbeat", "data": {"timestamp": time.time()}}
                    for client_id, client in list(self.clients.items()):
                        try:
                            await client.queue.put(message)
                        except Exception:
                            self.disconnect(client_id)

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
        print("[LogSSE] Heartbeat started")

    async def stop_heartbeat(self):
        """ハートビートタスクを停止"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            print("[LogSSE] Heartbeat stopped")

    def get_client_count(self) -> int:
        """接続中のクライアント数を取得"""
        return len(self.clients)

    def get_client_info(self) -> List[dict]:
        """接続中のクライアント情報を取得"""
        return [
            {
                "client_id": client.client_id,
                "connected_at": client.connected_at,
                "level_filter": list(client.level_filter) if client.level_filter else None,
                "session_filter": client.session_filter,
            }
            for client in self.clients.values()
        ]


# グローバルインスタンス
log_sse_manager = LogSSEManager()
