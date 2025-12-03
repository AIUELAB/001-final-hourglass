"""
CSVファイル監視サービス

watchdog を使用してCSVファイルの変更を監視し、
変更があった場合に登録されたコールバックを呼び出す。
"""

import os
import time
from pathlib import Path
from typing import Callable, Optional, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class CSVFileWatcher:
    """CSVファイルの変更を監視するクラス"""

    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self.observer: Optional[Observer] = None
        self.callbacks: Set[Callable] = set()
        self._last_mtime: float = 0
        self._debounce_seconds = 1.0
        self._last_event_time: float = 0

    def register_callback(self, callback: Callable):
        """変更通知のコールバックを登録"""
        self.callbacks.add(callback)

    def unregister_callback(self, callback: Callable):
        """コールバックを解除"""
        self.callbacks.discard(callback)

    def get_current_mtime(self) -> float:
        """現在のファイル更新時刻を取得"""
        try:
            return os.path.getmtime(self.csv_path)
        except OSError:
            return 0

    def start(self):
        """ファイル監視を開始"""
        if self.observer is not None:
            return

        self._last_mtime = self.get_current_mtime()

        class Handler(FileSystemEventHandler):
            def __init__(handler_self, watcher: "CSVFileWatcher"):
                handler_self.watcher = watcher

            def on_modified(handler_self, event):
                if event.is_directory:
                    return
                if Path(event.src_path).name == handler_self.watcher.csv_path.name:
                    handler_self.watcher._on_file_changed()

        self.observer = Observer()
        self.observer.schedule(Handler(self), str(self.csv_path.parent), recursive=False)
        self.observer.start()
        print(f"[File Watcher] Started: {self.csv_path}")

    def stop(self):
        """ファイル監視を停止"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            print("[File Watcher] Stopped")

    def _on_file_changed(self):
        """ファイル変更時の処理（デバウンス付き）"""
        current_time = time.time()

        if current_time - self._last_event_time < self._debounce_seconds:
            return

        new_mtime = self.get_current_mtime()
        if new_mtime > self._last_mtime:
            self._last_mtime = new_mtime
            self._last_event_time = current_time

            for callback in self.callbacks:
                try:
                    callback(new_mtime)
                except Exception as e:
                    print(f"[File Watcher] Callback error: {e}")


_watcher_instance: Optional[CSVFileWatcher] = None


def get_file_watcher(csv_path: Path) -> CSVFileWatcher:
    """ファイルウォッチャーのシングルトンインスタンスを取得"""
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = CSVFileWatcher(csv_path)
    return _watcher_instance
