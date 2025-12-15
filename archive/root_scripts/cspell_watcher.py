#!/usr/bin/env python3
"""
cSpell監視・自動修正システム
新しいCSVファイルが追加された際に自動的にcSpell設定を更新する
"""

import time
import os
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from update_cspell_config import CSpellConfigUpdater

class CSpellWatcher(FileSystemEventHandler):
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.updater = CSpellConfigUpdater(project_root)
        self.last_update: float = 0.0
        self.update_cooldown = 30  # 30秒のクールダウン

    def on_created(self, event):
        if not event.is_directory and self._should_process_file(event.src_path):
            self._schedule_update()

    def on_modified(self, event):
        if not event.is_directory and self._should_process_file(event.src_path):
            self._schedule_update()

    def _should_process_file(self, file_path: str) -> bool:
        """ファイルが処理対象かどうかを判定"""
        path = Path(file_path)
        return (
            path.suffix.lower() == '.csv' and
            any(pattern in str(path) for pattern in ['deletion_results', 'deletion_backups'])
        )

    def _schedule_update(self):
        """更新をスケジュール（クールダウン付き）"""
        current_time = time.time()
        if current_time - self.last_update > self.update_cooldown:
            print(f"CSV file change detected. Updating cSpell configuration...")
            self.updater.run()
            self.last_update = current_time
        else:
            print(f"Update skipped due to cooldown period")

def main():
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = "."

    print(f"Starting cSpell watcher for {project_root}")
    print("Press Ctrl+C to stop")

    event_handler = CSpellWatcher(project_root)
    observer = Observer()
    observer.schedule(event_handler, project_root, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping cSpell watcher...")

    observer.join()

if __name__ == "__main__":
    main()
