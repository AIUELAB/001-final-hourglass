"""
プロダクション環境設定とセキュリティ強化

本番環境での運用に必要な設定、セキュリティ対策、
パフォーマンス最適化を包括的に管理。
"""

import os
import json
import secrets
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import ssl
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import jwt
import redis
from functools import wraps
import time
import ipaddress
from collections import defaultdict
import re


@dataclass
class SecurityConfig:
    """セキュリティ設定"""

    # 暗号化
    encryption_key: str = field(default_factory=lambda: Fernet.generate_key().decode())
    jwt_secret: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # レート制限
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 1000
    rate_limit_burst_size: int = 100

    # IP制限
    ip_whitelist_enabled: bool = False
    ip_whitelist: List[str] = field(default_factory=lambda: [])
    ip_blacklist_enabled: bool = True
    ip_blacklist: List[str] = field(default_factory=lambda: [])

    # CORS設定
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["https://example.com"])
    cors_methods: List[str] = field(default_factory=lambda: ["GET", "POST"])
    cors_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Authorization"])

    # セキュリティヘッダー
    security_headers: Dict[str, str] = field(default_factory=lambda: {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    })

    # 認証設定
    api_key_header: str = "X-API-Key"
    api_key_required: bool = True
    api_keys: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 監査ログ
    audit_logging_enabled: bool = True
    audit_log_file: str = "/var/log/episode-factory/audit.log"

    # WAF設定
    waf_enabled: bool = True
    sql_injection_protection: bool = True
    xss_protection: bool = True
    path_traversal_protection: bool = True


@dataclass
class PerformanceConfig:
    """パフォーマンス設定"""

    # キャッシュ
    cache_enabled: bool = True
    cache_backend: str = "redis"  # redis, memcached, in-memory
    cache_ttl_seconds: int = 300
    cache_max_size: int = 10000

    # 接続プール
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600

    # スレッド/プロセス
    worker_processes: int = 4
    worker_threads: int = 10
    worker_connections: int = 1000

    # リクエスト処理
    request_timeout_seconds: int = 30
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    keepalive_timeout: int = 65

    # バッチ処理
    batch_size: int = 100
    batch_timeout_seconds: int = 5
    max_concurrent_batches: int = 10

    # 圧縮
    gzip_enabled: bool = True
    gzip_level: int = 6
    gzip_min_length: int = 1024

    # CDN設定
    cdn_enabled: bool = True
    cdn_url: str = "https://cdn.example.com"
    static_cache_control: str = "public, max-age=31536000"


@dataclass
class ProductionConfig:
    """プロダクション統合設定"""

    environment: str = "production"
    debug: bool = False
    testing: bool = False

    # 基本設定
    app_name: str = "episode-factory"
    version: str = "2.0.0"
    base_url: str = "https://api.episode-factory.com"

    # セキュリティ
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # パフォーマンス
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

    # ログ設定
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "/var/log/episode-factory/app.log"
    log_rotation: str = "daily"
    log_retention_days: int = 30

    # 監視設定
    monitoring_enabled: bool = True
    metrics_port: int = 9090
    health_check_path: str = "/health"
    readiness_check_path: str = "/ready"

    # データベース
    database_url: str = os.environ.get("DATABASE_URL", "")
    database_ssl_required: bool = True
    database_statement_timeout: int = 30000  # 30秒

    # Redis
    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379")
    redis_ssl: bool = True
    redis_password: Optional[str] = os.environ.get("REDIS_PASSWORD")


class SecurityManager:
    """セキュリティ管理クラス"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.cipher = Fernet(config.encryption_key.encode())
        self.rate_limiter = RateLimiter(config)
        self.ip_filter = IPFilter(config)
        self.waf = SimpleWAF(config)
        self.audit_logger = AuditLogger(config)

    def encrypt(self, data: str) -> str:
        """データ暗号化"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """データ復号化"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    def generate_api_key(self, client_name: str, permissions: List[str]) -> str:
        """APIキー生成"""
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        self.config.api_keys[key_hash] = {
            "client_name": client_name,
            "permissions": permissions,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "request_count": 0
        }

        return api_key

    def validate_api_key(self, api_key: str) -> bool:
        """APIキー検証"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        if key_hash in self.config.api_keys:
            # 使用記録更新
            self.config.api_keys[key_hash]["last_used"] = datetime.utcnow().isoformat()
            self.config.api_keys[key_hash]["request_count"] += 1
            return True

        return False

    def generate_jwt(self, payload: Dict[str, Any]) -> str:
        """JWT生成"""
        payload["exp"] = datetime.utcnow() + timedelta(
            minutes=self.config.jwt_expiration_minutes
        )
        payload["iat"] = datetime.utcnow()

        return jwt.encode(
            payload,
            self.config.jwt_secret,
            algorithm=self.config.jwt_algorithm
        )

    def validate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """JWT検証"""
        try:
            return jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )
        except jwt.ExpiredSignatureError:
            self.audit_logger.log("jwt_expired", {"token": token[:10] + "..."})
            return None
        except jwt.InvalidTokenError:
            self.audit_logger.log("jwt_invalid", {"token": token[:10] + "..."})
            return None

    def check_rate_limit(self, client_id: str) -> bool:
        """レート制限チェック"""
        return self.rate_limiter.allow(client_id)

    def check_ip_access(self, ip_address: str) -> bool:
        """IPアクセス制御"""
        return self.ip_filter.allow(ip_address)

    def sanitize_input(self, input_data: str) -> str:
        """入力サニタイズ"""
        return self.waf.sanitize(input_data)


class RateLimiter:
    """レート制限実装"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.redis_client = redis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True
        )
        self.local_cache = defaultdict(list)

    def allow(self, client_id: str) -> bool:
        """リクエスト許可判定"""
        if not self.config.rate_limit_enabled:
            return True

        key = f"rate_limit:{client_id}"
        current_time = time.time()
        window_start = current_time - 60  # 1分間のウィンドウ

        try:
            # Redis使用
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(current_time): current_time})
            pipe.zcount(key, window_start, current_time)
            pipe.expire(key, 60)
            results = pipe.execute()

            request_count = results[2]

        except Exception:
            # Redisが使えない場合はローカルキャッシュ
            self.local_cache[client_id] = [
                t for t in self.local_cache[client_id]
                if t > window_start
            ]
            self.local_cache[client_id].append(current_time)
            request_count = len(self.local_cache[client_id])

        return request_count <= self.config.rate_limit_requests_per_minute


class IPFilter:
    """IP フィルタリング"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.whitelist_networks = [
            ipaddress.ip_network(ip) for ip in config.ip_whitelist
        ]
        self.blacklist_networks = [
            ipaddress.ip_network(ip) for ip in config.ip_blacklist
        ]

    def allow(self, ip_address: str) -> bool:
        """IPアドレス許可判定"""
        try:
            ip = ipaddress.ip_address(ip_address)
        except ValueError:
            return False

        # ブラックリストチェック
        if self.config.ip_blacklist_enabled:
            for network in self.blacklist_networks:
                if ip in network:
                    return False

        # ホワイトリストチェック
        if self.config.ip_whitelist_enabled:
            for network in self.whitelist_networks:
                if ip in network:
                    return True
            return False  # ホワイトリスト有効時は明示的許可が必要

        return True


class SimpleWAF:
    """簡易WAF実装"""

    def __init__(self, config: SecurityConfig):
        self.config = config

        # 攻撃パターン定義
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|CREATE|ALTER)\b)",
            r"(--|\#|\/\*|\*\/)",
            r"(\bOR\b.*=.*)",
            r"(\bAND\b.*=.*)",
        ]

        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
        ]

        self.path_traversal_patterns = [
            r"\.\./",
            r"\.\./",
            r"%2e%2e/",
            r"%252e%252e/",
        ]

    def sanitize(self, input_data: str) -> str:
        """入力データのサニタイズ"""
        if not self.config.waf_enabled:
            return input_data

        sanitized = input_data

        # SQLインジェクション対策
        if self.config.sql_injection_protection:
            for pattern in self.sql_injection_patterns:
                if re.search(pattern, sanitized, re.IGNORECASE):
                    raise ValueError(f"Potential SQL injection detected")

        # XSS対策
        if self.config.xss_protection:
            for pattern in self.xss_patterns:
                sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

        # パストラバーサル対策
        if self.config.path_traversal_protection:
            for pattern in self.path_traversal_patterns:
                if re.search(pattern, sanitized, re.IGNORECASE):
                    raise ValueError(f"Potential path traversal detected")

        return sanitized


class AuditLogger:
    """監査ログ"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger("audit")

        if config.audit_logging_enabled:
            handler = logging.FileHandler(config.audit_log_file)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log(self, event_type: str, details: Dict[str, Any]):
        """監査イベント記録"""
        if not self.config.audit_logging_enabled:
            return

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details
        }

        self.logger.info(json.dumps(event))


class PerformanceOptimizer:
    """パフォーマンス最適化"""

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.cache = self._init_cache()

    def _init_cache(self):
        """キャッシュ初期化"""
        if not self.config.cache_enabled:
            return None

        if self.config.cache_backend == "redis":
            return redis.Redis(
                host="localhost",
                port=6379,
                decode_responses=True
            )
        else:
            return {}  # In-memory cache

    def get_from_cache(self, key: str) -> Optional[Any]:
        """キャッシュ取得"""
        if not self.config.cache_enabled:
            return None

        if isinstance(self.cache, redis.Redis):
            value = self.cache.get(key)
            if value:
                return json.loads(value)
        else:
            return self.cache.get(key)

        return None

    def set_cache(self, key: str, value: Any, ttl: Optional[int] = None):
        """キャッシュ設定"""
        if not self.config.cache_enabled:
            return

        ttl = ttl or self.config.cache_ttl_seconds

        if isinstance(self.cache, redis.Redis):
            self.cache.set(key, json.dumps(value), ex=ttl)
        else:
            self.cache[key] = value

    def clear_cache(self, pattern: Optional[str] = None):
        """キャッシュクリア"""
        if not self.config.cache_enabled:
            return

        if isinstance(self.cache, redis.Redis):
            if pattern:
                for key in self.cache.scan_iter(match=pattern):
                    self.cache.delete(key)
            else:
                self.cache.flushdb()
        else:
            if pattern:
                keys_to_delete = [k for k in self.cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.cache[key]
            else:
                self.cache.clear()


def secure_endpoint(require_auth: bool = True, rate_limit: bool = True):
    """セキュアエンドポイントデコレータ"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = kwargs.get('request') or args[1] if len(args) > 1 else None

            if not request:
                raise ValueError("Request object not found")

            # セキュリティマネージャー取得
            security = getattr(request, 'security', None)

            if not security:
                raise ValueError("Security manager not configured")

            # IP制限チェック
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if not security.check_ip_access(client_ip):
                raise PermissionError(f"IP {client_ip} not allowed")

            # レート制限チェック
            if rate_limit:
                client_id = request.headers.get('X-Client-Id', client_ip)
                if not security.check_rate_limit(client_id):
                    raise PermissionError("Rate limit exceeded")

            # 認証チェック
            if require_auth:
                api_key = request.headers.get(security.config.api_key_header)
                if not api_key or not security.validate_api_key(api_key):
                    raise PermissionError("Invalid API key")

            # 監査ログ
            security.audit_logger.log("api_access", {
                "endpoint": func.__name__,
                "client_ip": client_ip,
                "method": request.method
            })

            return func(*args, **kwargs)

        return wrapper
    return decorator


# 設定ローダー
def load_production_config() -> ProductionConfig:
    """プロダクション設定ロード"""
    config = ProductionConfig()

    # 環境変数から設定上書き
    if os.environ.get("EPISODE_FACTORY_ENV"):
        config.environment = os.environ.get("EPISODE_FACTORY_ENV")

    if os.environ.get("EPISODE_FACTORY_DEBUG"):
        config.debug = os.environ.get("EPISODE_FACTORY_DEBUG").lower() == "true"

    # セキュリティキー設定
    if os.environ.get("JWT_SECRET"):
        config.security.jwt_secret = os.environ.get("JWT_SECRET")

    if os.environ.get("ENCRYPTION_KEY"):
        config.security.encryption_key = os.environ.get("ENCRYPTION_KEY")

    return config


# 使用例
if __name__ == "__main__":
    # プロダクション設定ロード
    config = load_production_config()

    # セキュリティマネージャー初期化
    security = SecurityManager(config.security)

    # APIキー生成
    api_key = security.generate_api_key(
        client_name="frontend-app",
        permissions=["read", "write"]
    )
    print(f"Generated API Key: {api_key}")

    # データ暗号化
    sensitive_data = "This is sensitive information"
    encrypted = security.encrypt(sensitive_data)
    decrypted = security.decrypt(encrypted)
    assert sensitive_data == decrypted

    # JWT生成と検証
    token = security.generate_jwt({"user_id": 123, "role": "admin"})
    payload = security.validate_jwt(token)
    print(f"JWT Payload: {payload}")

    # パフォーマンス最適化
    optimizer = PerformanceOptimizer(config.performance)
    optimizer.set_cache("test_key", {"value": "test"})
    cached_value = optimizer.get_from_cache("test_key")
    print(f"Cached Value: {cached_value}")

    print("プロダクション設定とセキュリティシステムの初期化が完了しました")
