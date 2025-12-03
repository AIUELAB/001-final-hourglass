"""
Server-Sent Events マネージャー

複数クライアントへのブロードキャスト、
ハートビート送信、接続管理を担当。
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, Optional


@dataclass
class SSEClient:
    """SSEクライアント情報"""

    client_id: str
    queue: asyncio.Queue
    connected_at: float = field(default_factory=time.time)


class SSEManager:
    """SSE接続を管理するクラス"""

    def __init__(self):
        self.clients: Dict[str, SSEClient] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 30

    async def connect(self) -> SSEClient:
        """新しいクライアント接続を作成"""
        client_id = str(uuid.uuid4())
        client = SSEClient(client_id=client_id, queue=asyncio.Queue())
        self.clients[client_id] = client
        print(f"[SSE] Client connected: {client_id} (total: {len(self.clients)})")
        return client

    def disconnect(self, client_id: str):
        """クライアント接続を解除"""
        if client_id in self.clients:
            del self.clients[client_id]
            print(f"[SSE] Client disconnected: {client_id} (remaining: {len(self.clients)})")

    async def broadcast(self, event_type: str, data: dict):
        """すべてのクライアントにイベントを送信"""
        message = {"event": event_type, "data": data}

        disconnected = []
        for client_id, client in self.clients.items():
            try:
                await client.queue.put(message)
            except Exception as e:
                print(f"[SSE] Broadcast failed for {client_id}: {e}")
                disconnected.append(client_id)

        for client_id in disconnected:
            self.disconnect(client_id)

    async def event_generator(self, client: SSEClient) -> AsyncGenerator[str, None]:
        """SSEイベントジェネレーター"""
        try:
            while True:
                try:
                    message = await asyncio.wait_for(client.queue.get(), timeout=self._heartbeat_interval + 5)
                    yield self.format_sse(event=message["event"], data=message["data"])
                except asyncio.TimeoutError:
                    yield self.format_sse(event="heartbeat", data={"timestamp": time.time()})
        except asyncio.CancelledError:
            pass

    def format_sse(self, event: str, data: dict) -> str:
        """SSE形式にフォーマット"""
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def start_heartbeat(self):
        """ハートビートタスクを開始"""
        if self._heartbeat_task is not None:
            return

        async def heartbeat_loop():
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                if self.clients:
                    await self.broadcast("heartbeat", {"timestamp": time.time()})

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
        print("[SSE] Heartbeat started")

    async def stop_heartbeat(self):
        """ハートビートタスクを停止"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            print("[SSE] Heartbeat stopped")


sse_manager = SSEManager()
