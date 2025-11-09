#!/usr/bin/env python3
"""
3層キャッシュシステム
メモリ、Redis、SQLiteを使用した多層キャッシュによる高速化
"""

import json
import sqlite3
from src.database_utils import get_connection
import time
import hashlib
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pickle
import logging
from collections import OrderedDict
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """キャッシュエントリ"""
    key: str
    value: Any
    timestamp: float
    ttl: int
    hit_count: int = 0
    api_name: Optional[str] = None


class ThreeLayerCache:
    """3層キャッシュシステム"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        
        # Layer 1: メモリキャッシュ（LRU）
        self.memory_cache = OrderedDict()
        self.memory_max_size = self.config['layer1']['size']
        self.memory_ttl = self.config['layer1']['ttl']
        
        # Layer 2: Redis風インメモリストア（実際のRedis代替）
        self.redis_cache = {}
        self.redis_ttl = self.config['layer2']['ttl']
        
        # Layer 3: SQLite永続化
        self.sqlite_path = Path(self.config['layer3']['storage'])
        self._init_sqlite()
        
        # 統計情報
        self.stats = {
            'memory_hits': 0,
            'redis_hits': 0,
            'sqlite_hits': 0,
            'misses': 0,
            'total_requests': 0
        }
    
    def _default_config(self) -> Dict:
        """デフォルト設定"""
        return {
            'layer1': {
                'ttl': 3600,  # 1時間
                'size': 10000
            },
            'layer2': {
                'ttl': 86400,  # 24時間
                'pattern': 'similar_names'
            },
            'layer3': {
                'storage': 'cache.db',
                'retention': 30  # 30日
            }
        }
    
    def _init_sqlite(self):
        """SQLite初期化"""
        conn = get_connection(self.sqlite_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value BLOB,
                timestamp REAL,
                ttl INTEGER,
                hit_count INTEGER DEFAULT 0,
                api_name TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # インデックス作成
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON cache(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_api_name ON cache(api_name)
        ''')
        
        conn.commit()
        conn.close()
    
    def _generate_key(self, api_name: str, query: str, params: Optional[Dict] = None) -> str:
        """キャッシュキー生成"""
        key_parts = [api_name, query]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, api_name: str, query: str, params: Optional[Dict] = None) -> Tuple[Optional[Any], str]:
        """キャッシュ取得（3層チェック）"""
        key = self._generate_key(api_name, query, params)
        self.stats['total_requests'] += 1
        
        # Layer 1: メモリキャッシュ
        result = self._get_from_memory(key)
        if result is not None:
            self.stats['memory_hits'] += 1
            return result, 'memory'
        
        # Layer 2: Redis風キャッシュ
        result = self._get_from_redis(key)
        if result is not None:
            self.stats['redis_hits'] += 1
            # メモリにも保存（プロモート）
            self._set_to_memory(key, result, self.memory_ttl)
            return result, 'redis'
        
        # Layer 3: SQLite
        result = self._get_from_sqlite(key)
        if result is not None:
            self.stats['sqlite_hits'] += 1
            # 上位層にプロモート
            self._set_to_redis(key, result, self.redis_ttl)
            self._set_to_memory(key, result, self.memory_ttl)
            return result, 'sqlite'
        
        self.stats['misses'] += 1
        return None, 'miss'
    
    def set(self, api_name: str, query: str, value: Any, params: Optional[Dict] = None, ttl: Optional[int] = None):
        """キャッシュ設定（全層に保存）"""
        key = self._generate_key(api_name, query, params)
        
        # TTL決定
        if ttl is None:
            ttl = self._determine_ttl(api_name, value)
        
        # 全層に保存
        self._set_to_memory(key, value, min(ttl, self.memory_ttl))
        self._set_to_redis(key, value, min(ttl, self.redis_ttl))
        self._set_to_sqlite(key, value, ttl, api_name)
    
    def _determine_ttl(self, api_name: str, value: Any) -> int:
        """動的TTL決定"""
        # API別のTTL戦略
        ttl_strategy = {
            'Google': 86400 * 7,  # 7日（変動少ない）
            'YouTube': 86400 * 3,  # 3日（中程度の変動）
            'Twitter': 3600 * 12,  # 12時間（変動大）
            'News': 3600 * 6,     # 6時間（最新性重要）
            'Brave': 86400 * 5    # 5日
        }
        
        base_ttl = ttl_strategy.get(api_name, 86400)
        
        # 結果の質によるTTL調整
        if isinstance(value, dict):
            # 結果が多い場合は長めのTTL
            if value.get('results', 0) > 1000000:
                base_ttl *= 2
            # 結果が少ない場合は短めのTTL
            elif value.get('results', 0) < 100:
                base_ttl //= 2
        
        return base_ttl
    
    def _get_from_memory(self, key: str) -> Optional[Any]:
        """メモリキャッシュから取得"""
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            
            # TTLチェック
            if time.time() - entry['timestamp'] > entry['ttl']:
                del self.memory_cache[key]
                return None
            
            # LRU: 最後に移動
            self.memory_cache.move_to_end(key)
            entry['hit_count'] += 1
            
            return entry['value']
        return None
    
    def _set_to_memory(self, key: str, value: Any, ttl: int):
        """メモリキャッシュに設定"""
        # サイズ制限チェック
        if len(self.memory_cache) >= self.memory_max_size:
            # 最も古いエントリを削除
            self.memory_cache.popitem(last=False)
        
        self.memory_cache[key] = {
            'value': value,
            'timestamp': time.time(),
            'ttl': ttl,
            'hit_count': 0
        }
    
    def _get_from_redis(self, key: str) -> Optional[Any]:
        """Redis風キャッシュから取得"""
        if key in self.redis_cache:
            entry = self.redis_cache[key]
            
            # TTLチェック
            if time.time() - entry['timestamp'] > entry['ttl']:
                del self.redis_cache[key]
                return None
            
            entry['hit_count'] += 1
            return entry['value']
        return None
    
    def _set_to_redis(self, key: str, value: Any, ttl: int):
        """Redis風キャッシュに設定"""
        self.redis_cache[key] = {
            'value': value,
            'timestamp': time.time(),
            'ttl': ttl,
            'hit_count': 0
        }
    
    def _get_from_sqlite(self, key: str) -> Optional[Any]:
        """SQLiteから取得"""
        conn = get_connection(self.sqlite_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT value, timestamp, ttl, hit_count 
            FROM cache 
            WHERE key = ?
        ''', (key,))
        
        row = cursor.fetchone()
        
        if row:
            value_blob, timestamp, ttl, hit_count = row
            
            # TTLチェック
            if time.time() - timestamp > ttl:
                cursor.execute('DELETE FROM cache WHERE key = ?', (key,))
                conn.commit()
                conn.close()
                return None
            
            # ヒットカウント更新
            cursor.execute('''
                UPDATE cache 
                SET hit_count = hit_count + 1, updated_at = ? 
                WHERE key = ?
            ''', (datetime.now().isoformat(), key))
            
            conn.commit()
            conn.close()
            
            # デシリアライズ
            try:
                return pickle.loads(value_blob)
            except:
                return json.loads(value_blob.decode())
        
        conn.close()
        return None
    
    def _set_to_sqlite(self, key: str, value: Any, ttl: int, api_name: str):
        """SQLiteに設定"""
        conn = get_connection(self.sqlite_path)
        cursor = conn.cursor()
        
        # シリアライズ
        try:
            value_blob = pickle.dumps(value)
        except:
            value_blob = json.dumps(value).encode()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO cache 
            (key, value, timestamp, ttl, hit_count, api_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (key, value_blob, time.time(), ttl, 0, api_name, now, now))
        
        conn.commit()
        conn.close()
    
    def invalidate_pattern(self, pattern: str):
        """パターンマッチでキャッシュ無効化"""
        # メモリキャッシュ
        keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.memory_cache[key]
        
        # Redis風キャッシュ
        keys_to_delete = [k for k in self.redis_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.redis_cache[key]
        
        # SQLite
        conn = get_connection(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cache WHERE key LIKE ?', (f'%{pattern}%',))
        conn.commit()
        conn.close()
    
    def cleanup_expired(self):
        """期限切れエントリのクリーンアップ"""
        current_time = time.time()
        
        # メモリキャッシュ
        expired_keys = []
        for key, entry in self.memory_cache.items():
            if current_time - entry['timestamp'] > entry['ttl']:
                expired_keys.append(key)
        for key in expired_keys:
            del self.memory_cache[key]
        
        # Redis風キャッシュ
        expired_keys = []
        for key, entry in self.redis_cache.items():
            if current_time - entry['timestamp'] > entry['ttl']:
                expired_keys.append(key)
        for key in expired_keys:
            del self.redis_cache[key]
        
        # SQLite
        conn = get_connection(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM cache 
            WHERE timestamp + ttl < ?
        ''', (current_time,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"🧹 クリーンアップ完了: {len(expired_keys) + deleted}件削除")
    
    def get_statistics(self) -> Dict:
        """統計情報取得"""
        total_hits = self.stats['memory_hits'] + self.stats['redis_hits'] + self.stats['sqlite_hits']
        hit_rate = (total_hits / self.stats['total_requests'] * 100) if self.stats['total_requests'] > 0 else 0
        
        # SQLiteのサイズ
        sqlite_size = self.sqlite_path.stat().st_size if self.sqlite_path.exists() else 0
        
        return {
            'hit_rate': hit_rate,
            'memory_hits': self.stats['memory_hits'],
            'redis_hits': self.stats['redis_hits'],
            'sqlite_hits': self.stats['sqlite_hits'],
            'misses': self.stats['misses'],
            'total_requests': self.stats['total_requests'],
            'memory_cache_size': len(self.memory_cache),
            'redis_cache_size': len(self.redis_cache),
            'sqlite_size_mb': sqlite_size / (1024 * 1024)
        }
    
    def optimize_cache_distribution(self):
        """キャッシュ分布の最適化"""
        # SQLiteから頻繁にアクセスされるエントリを上位層にプロモート
        conn = get_connection(self.sqlite_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT key, value, ttl, api_name
            FROM cache
            WHERE hit_count > 10
            ORDER BY hit_count DESC
            LIMIT 100
        ''')
        
        for row in cursor.fetchall():
            key, value_blob, ttl, api_name = row
            try:
                value = pickle.loads(value_blob)
            except:
                value = json.loads(value_blob.decode())
            
            # 上位層にプロモート
            self._set_to_redis(key, value, min(ttl, self.redis_ttl))
            self._set_to_memory(key, value, min(ttl, self.memory_ttl))
        
        conn.close()
        logger.info("✅ キャッシュ分布最適化完了")


def demo_cache_system():
    """デモ実行"""
    cache = ThreeLayerCache()
    
    print("🔧 3層キャッシュシステム デモ")
    print("=" * 60)
    
    # テストデータ
    test_queries = [
        ("Google", "HIKAKIN", {"results": 172000000}),
        ("YouTube", "米津玄師", {"views": 500000000}),
        ("Twitter", "大谷翔平", {"mentions": 1000000}),
        ("Google", "HIKAKIN", {"results": 172000000}),  # 重複（キャッシュヒット）
    ]
    
    # キャッシュテスト
    for api_name, query, value in test_queries:
        # 取得試行
        cached_value, layer = cache.get(api_name, query)
        
        if cached_value:
            print(f"✅ キャッシュヒット ({layer}): {api_name}:{query}")
        else:
            print(f"❌ キャッシュミス: {api_name}:{query}")
            # キャッシュに保存
            cache.set(api_name, query, value)
            print(f"  → 保存完了")
    
    # 統計表示
    print("\n📊 キャッシュ統計:")
    stats = cache.get_statistics()
    for key, value in stats.items():
        if 'rate' in key:
            print(f"  {key}: {value:.1f}%")
        elif 'size' in key:
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value}")
    
    # クリーンアップ
    cache.cleanup_expired()
    
    return cache


if __name__ == "__main__":
    demo_cache_system()