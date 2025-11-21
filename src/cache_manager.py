#!/usr/bin/env python3
"""
キャッシュ管理システム
Google Sheetsとブラウザのキャッシュを完全にクリアし、常に最新データを表示

作成日: 2025-08-31
Ultra Think Mode対応
"""

import hashlib
import json
import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional


class CacheManager:
    """
    マルチレイヤーキャッシュ管理システム
    - メモリキャッシュ
    - ファイルキャッシュ
    - APIキャッシュ
    - ブラウザキャッシュ
    """

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.memory_cache: Dict[str, Any] = {}
        self.cache_metadata: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)

        # キャッシュディレクトリ作成
        self.cache_dir.mkdir(exist_ok=True)
        (self.cache_dir / "memory").mkdir(exist_ok=True)
        (self.cache_dir / "files").mkdir(exist_ok=True)
        (self.cache_dir / "metadata").mkdir(exist_ok=True)

        # 設定
        self.ttl_seconds = 300  # 5分のTTL
        self.force_clear_on_update = True
        self.browser_cache_buster = True

        self.logger.info("✅ CacheManager初期化完了")

    def purge_all_cache(self) -> bool:
        """すべてのキャッシュを完全削除"""
        try:
            # メモリキャッシュクリア
            self.memory_cache.clear()
            self.cache_metadata.clear()

            # ファイルキャッシュクリア
            if self.cache_dir.exists():
                for cache_type in ["memory", "files", "metadata"]:
                    cache_path = self.cache_dir / cache_type
                    if cache_path.exists():
                        for file in cache_path.glob("*"):
                            if file.is_file():
                                file.unlink()
                            elif file.is_dir():
                                shutil.rmtree(file)

            self.logger.info("🗑️  全キャッシュを完全削除しました")
            return True

        except Exception as e:
            self.logger.error(f"❌ キャッシュ削除エラー: {e}")
            return False

    def purge_old_data(self, timestamp_threshold: datetime) -> int:
        """指定タイムスタンプ以前のデータを完全削除"""
        deleted_count = 0

        # メモリキャッシュから古いデータ削除
        keys_to_delete = []
        for key, metadata in self.cache_metadata.items():
            if metadata.get("timestamp"):
                cache_time = datetime.fromisoformat(metadata["timestamp"])
                if cache_time < timestamp_threshold:
                    keys_to_delete.append(key)

        for key in keys_to_delete:
            if key in self.memory_cache:
                del self.memory_cache[key]
            if key in self.cache_metadata:
                del self.cache_metadata[key]
            deleted_count += 1

        # ファイルキャッシュから古いデータ削除
        for cache_file in (self.cache_dir / "files").glob("*.json"):
            if cache_file.stat().st_mtime < timestamp_threshold.timestamp():
                cache_file.unlink()
                deleted_count += 1

        self.logger.info(f"🗑️  {deleted_count}件の古いキャッシュを削除")
        return deleted_count

    def invalidate_all_cache(self) -> None:
        """全キャッシュを強制無効化"""
        # タイムスタンプを過去に設定して無効化
        past_time = (datetime.now() - timedelta(days=365)).isoformat()

        for key in self.cache_metadata:
            self.cache_metadata[key]["timestamp"] = past_time
            self.cache_metadata[key]["valid"] = False

        self.logger.info("⚠️  全キャッシュを無効化しました")

    def atomic_cache_update(self, key: str, data: Any, version: str) -> bool:
        """トランザクション型キャッシュ更新"""
        try:
            # 古いキャッシュをバックアップ
            old_data = self.memory_cache.get(key)
            old_metadata = self.cache_metadata.get(key, {}).copy()

            # 新しいデータのハッシュ計算
            data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
            data_hash = hashlib.sha256(data_str.encode()).hexdigest()

            # メタデータ作成
            new_metadata = {
                "timestamp": datetime.now().isoformat(),
                "version": version,
                "hash": data_hash,
                "valid": True,
                "size": len(data_str),
            }

            # アトミック更新
            self.memory_cache[key] = data
            self.cache_metadata[key] = new_metadata

            # ファイルキャッシュに永続化
            cache_file = self.cache_dir / "files" / f"{key}.json"
            temp_file = cache_file.with_suffix(".tmp")

            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump({"data": data, "metadata": new_metadata}, f, ensure_ascii=False, indent=2)

            # アトミックなファイル置換
            temp_file.replace(cache_file)

            self.logger.info(f"✅ キャッシュ更新成功: {key} (v{version})")
            return True

        except Exception as e:
            # ロールバック
            if old_data is not None:
                self.memory_cache[key] = old_data
                self.cache_metadata[key] = old_metadata

            self.logger.error(f"❌ キャッシュ更新失敗: {e}")
            return False

    def get_cache(self, key: str) -> Optional[Any]:
        """キャッシュ取得（TTLチェック付き）"""
        # メモリキャッシュチェック
        if key in self.memory_cache:
            metadata = self.cache_metadata.get(key, {})

            # TTLチェック
            if metadata.get("timestamp"):
                cache_time = datetime.fromisoformat(metadata["timestamp"])
                if (datetime.now() - cache_time).total_seconds() < self.ttl_seconds:
                    if metadata.get("valid", False):
                        return self.memory_cache[key]

        # ファイルキャッシュチェック
        cache_file = self.cache_dir / "files" / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)

                metadata = cache_data.get("metadata", {})
                if metadata.get("timestamp"):
                    cache_time = datetime.fromisoformat(metadata["timestamp"])
                    if (datetime.now() - cache_time).total_seconds() < self.ttl_seconds:
                        if metadata.get("valid", False):
                            # メモリキャッシュに復元
                            self.memory_cache[key] = cache_data["data"]
                            self.cache_metadata[key] = metadata
                            return cache_data["data"]
            except Exception as e:
                self.logger.warning(f"キャッシュ読み込みエラー: {e}")

        return None

    def generate_cache_buster_url(self, base_url: str, version: str = None) -> str:
        """ブラウザキャッシュ回避用のURL生成"""
        timestamp = int(time.time())

        # バージョンハッシュ生成（セキュリティ用途ではないためMD5使用）
        if version:
            version_hash = hashlib.md5(version.encode(), usedforsecurity=False).hexdigest()[:8]
        else:
            version_hash = hashlib.md5(str(timestamp).encode(), usedforsecurity=False).hexdigest()[:8]

        # URLパラメータ追加
        separator = "&" if "?" in base_url else "?"
        cache_buster_params = f"v={timestamp}&hash={version_hash}&nocache=1"

        return f"{base_url}{separator}{cache_buster_params}"

    def clear_google_sheets_cache(self) -> Dict[str, Any]:
        """Google Sheets APIキャッシュクリア用ヘッダー生成"""
        return {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "If-None-Match": "*",  # 強制更新
            "X-Cache-Bypass": "1",
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計情報取得"""
        memory_size = sum(len(json.dumps(v, default=str)) for v in self.memory_cache.values())

        file_count = len(list((self.cache_dir / "files").glob("*.json")))
        file_size = sum(f.stat().st_size for f in (self.cache_dir / "files").glob("*.json"))

        valid_count = sum(1 for m in self.cache_metadata.values() if m.get("valid", False))

        return {
            "memory_cache": {"count": len(self.memory_cache), "size_bytes": memory_size, "valid_count": valid_count},
            "file_cache": {"count": file_count, "size_bytes": file_size},
            "ttl_seconds": self.ttl_seconds,
            "force_clear_on_update": self.force_clear_on_update,
        }

    def cleanup_expired(self) -> int:
        """期限切れキャッシュの自動クリーンアップ"""
        threshold = datetime.now() - timedelta(seconds=self.ttl_seconds)
        return self.purge_old_data(threshold)

    def force_browser_refresh_script(self) -> str:
        """ブラウザ強制リフレッシュ用JavaScript生成"""
        return """
        // 強制リフレッシュスクリプト
        (function() {
            // キャッシュクリア
            if ('caches' in window) {
                caches.keys().then(names => {
                    names.forEach(name => caches.delete(name));
                });
            }

            // ハード再読み込み
            window.location.reload(true);

            // 代替方法（より強力）
            const url = new URL(window.location.href);
            url.searchParams.set('_t', Date.now());
            url.searchParams.set('nocache', '1');
            window.location.href = url.toString();
        })();
        """


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)

    cache_mgr = CacheManager()

    # テストデータ
    test_data = {"name": "カジサック", "display": "カジサック"}

    # キャッシュ更新
    cache_mgr.atomic_cache_update("test_key", test_data, "v1.0.0")

    # キャッシュ取得
    cached = cache_mgr.get_cache("test_key")
    print(f"キャッシュデータ: {cached}")

    # 統計表示
    stats = cache_mgr.get_cache_stats()
    print(f"キャッシュ統計: {json.dumps(stats, indent=2)}")

    # URL生成テスト
    url = cache_mgr.generate_cache_buster_url("https://docs.google.com/spreadsheets/d/xxx/edit", "v1.0.0")
    print(f"キャッシュ回避URL: {url}")
