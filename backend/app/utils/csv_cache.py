"""CSVファイルのインメモリキャッシュとETag生成"""

import csv
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class CSVCacheEntry:
    """CSVキャッシュエントリ"""

    data: List[Dict]
    mtime: float
    checksum: str
    loaded_at: datetime
    row_count: int
    file_size: int


class CSVCache:
    """CSVファイルのシングルトンインメモリキャッシュ"""

    _instance: Optional["CSVCache"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache: Dict[str, CSVCacheEntry] = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "CSVCache":
        return cls()

    def get_or_load(self, csv_path: str) -> CSVCacheEntry:
        """キャッシュからデータを取得、または再読み込み"""
        path = Path(csv_path)
        path_key = str(path.resolve())

        if not path.exists():
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

        current_mtime = os.path.getmtime(csv_path)
        current_size = os.path.getsize(csv_path)
        current_checksum = self._compute_checksum(current_size, current_mtime)

        cached = self._cache.get(path_key)
        if cached and cached.checksum == current_checksum:
            return cached

        print(f"🔄 CSVキャッシュ再読み込み: {path.name}")
        data = self._load_csv(csv_path)

        entry = CSVCacheEntry(
            data=data,
            mtime=current_mtime,
            checksum=current_checksum,
            loaded_at=datetime.now(),
            row_count=len(data),
            file_size=current_size,
        )
        self._cache[path_key] = entry
        return entry

    def get_metadata(self, csv_path: str) -> Dict:
        """ファイルメタデータのみ取得（軽量版）"""
        path = Path(csv_path)

        if not path.exists():
            return {"exists": False}

        mtime = os.path.getmtime(csv_path)
        size = os.path.getsize(csv_path)
        checksum = self._compute_checksum(size, mtime)

        path_key = str(path.resolve())
        cached = self._cache.get(path_key)
        row_count = cached.row_count if cached and cached.checksum == checksum else None

        return {
            "exists": True,
            "mtime": mtime,
            "size": size,
            "checksum": checksum,
            "row_count": row_count,
            "etag": f'W/"{checksum}"',
        }

    def invalidate(self, csv_path: str = None):
        """キャッシュを無効化"""
        if csv_path:
            path_key = str(Path(csv_path).resolve())
            self._cache.pop(path_key, None)
        else:
            self._cache.clear()

    def _compute_checksum(self, size: int, mtime: float) -> str:
        """ファイルサイズ+mtimeからチェックサムを計算"""
        return hashlib.md5(f"{size}-{mtime}".encode(), usedforsecurity=False).hexdigest()[:12]

    def _load_csv(self, csv_path: str) -> List[Dict]:
        """CSVファイルを読み込み"""
        with open(csv_path, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))


csv_cache = CSVCache.get_instance()
