#!/usr/bin/env python3
"""
Authentication and Authorization Middleware
Phase 4 - Security Enhancement
"""

import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from aiohttp import web
from functools import wraps
import asyncio
import logging
from collections import defaultdict
import time
import json
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class RateLimiter:
    """レート制限機能"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_limit: int = 100,
        default_window: int = 60
    ):
        self.redis_url = redis_url
        self.default_limit = default_limit
        self.default_window = default_window
        self.redis_client = None
        self.local_cache = defaultdict(list)  # Fallback for Redis failure

    async def connect(self):
        """Redis接続"""
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Rate limiter connected to Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed, using local cache: {e}")
            self.redis_client = None

    async def is_allowed(
        self,
        identifier: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> tuple[bool, Dict[str, Any]]:
        """レート制限チェック"""
        limit = limit or self.default_limit
        window = window or self.default_window

        if self.redis_client:
            return await self._check_redis(identifier, limit, window)
        else:
            return self._check_local(identifier, limit, window)

    async def _check_redis(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> tuple[bool, Dict[str, Any]]:
        """Redisベースのレート制限チェック"""
        try:
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            window_start = current_time - window

            # Remove old entries
            await self.redis_client.zremrangebyscore(key, 0, window_start)

            # Count current requests
            request_count = await self.redis_client.zcard(key)

            if request_count < limit:
                # Add new request
                await self.redis_client.zadd(key, {str(current_time): current_time})
                await self.redis_client.expire(key, window)

                return True, {
                    'allowed': True,
                    'limit': limit,
                    'remaining': limit - request_count - 1,
                    'reset': current_time + window
                }
            else:
                return False, {
                    'allowed': False,
                    'limit': limit,
                    'remaining': 0,
                    'reset': current_time + window,
                    'retry_after': window
                }

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fallback to local
            return self._check_local(identifier, limit, window)

    def _check_local(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> tuple[bool, Dict[str, Any]]:
        """ローカルキャッシュベースのレート制限チェック"""
        current_time = time.time()
        window_start = current_time - window

        # Clean old entries
        self.local_cache[identifier] = [
            t for t in self.local_cache[identifier]
            if t > window_start
        ]

        request_count = len(self.local_cache[identifier])

        if request_count < limit:
            self.local_cache[identifier].append(current_time)
            return True, {
                'allowed': True,
                'limit': limit,
                'remaining': limit - request_count - 1,
                'reset': int(current_time + window)
            }
        else:
            return False, {
                'allowed': False,
                'limit': limit,
                'remaining': 0,
                'reset': int(current_time + window),
                'retry_after': window
            }

class JWTAuth:
    """JWT認証機能"""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        token_expiry: int = 3600
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry = token_expiry

    def generate_token(
        self,
        user_id: str,
        roles: List[str] = None,
        additional_claims: Dict[str, Any] = None
    ) -> str:
        """JWTトークン生成"""
        payload = {
            'user_id': user_id,
            'roles': roles or [],
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(seconds=self.token_expiry),
            'jti': secrets.token_urlsafe(16)  # JWT ID for revocation
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """JWTトークン検証"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def refresh_token(self, token: str) -> Optional[str]:
        """トークンリフレッシュ"""
        payload = self.verify_token(token)
        if payload:
            # Remove old timestamps
            payload.pop('iat', None)
            payload.pop('exp', None)
            payload.pop('jti', None)

            # Generate new token
            return self.generate_token(
                payload['user_id'],
                payload.get('roles'),
                {k: v for k, v in payload.items()
                 if k not in ['user_id', 'roles']}
            )
        return None

class AuthMiddleware:
    """認証ミドルウェア"""

    def __init__(
        self,
        jwt_auth: JWTAuth,
        rate_limiter: RateLimiter,
        whitelist_paths: List[str] = None
    ):
        self.jwt_auth = jwt_auth
        self.rate_limiter = rate_limiter
        self.whitelist_paths = whitelist_paths or ['/health', '/metrics']

    @web.middleware
    async def middleware(self, request: web.Request, handler):
        """認証ミドルウェアハンドラ"""
        path = request.path

        # ホワイトリストパスはスキップ
        if any(path.startswith(p) for p in self.whitelist_paths):
            return await handler(request)

        # レート制限チェック
        client_ip = request.headers.get('X-Forwarded-For',
                                       request.remote or 'unknown')
        allowed, rate_info = await self.rate_limiter.is_allowed(client_ip)

        if not allowed:
            return web.json_response(
                {
                    'error': 'Rate limit exceeded',
                    'retry_after': rate_info['retry_after']
                },
                status=429,
                headers={
                    'X-RateLimit-Limit': str(rate_info['limit']),
                    'X-RateLimit-Remaining': '0',
                    'X-RateLimit-Reset': str(rate_info['reset']),
                    'Retry-After': str(rate_info['retry_after'])
                }
            )

        # JWT認証チェック
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return web.json_response(
                {'error': 'Missing or invalid authorization header'},
                status=401
            )

        token = auth_header.replace('Bearer ', '')
        payload = self.jwt_auth.verify_token(token)

        if not payload:
            return web.json_response(
                {'error': 'Invalid or expired token'},
                status=401
            )

        # ユーザー情報をリクエストに追加
        request['user'] = payload

        # ハンドラー実行
        response = await handler(request)

        # レート制限ヘッダー追加
        response.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
        response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
        response.headers['X-RateLimit-Reset'] = str(rate_info['reset'])

        return response

def require_roles(*required_roles):
    """ロールベースアクセス制御デコレータ"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            user = request.get('user', {})
            user_roles = set(user.get('roles', []))
            required = set(required_roles)

            if not required.intersection(user_roles):
                return web.json_response(
                    {
                        'error': 'Insufficient privileges',
                        'required_roles': list(required_roles)
                    },
                    status=403
                )

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

class SecurityHeaders:
    """セキュリティヘッダーミドルウェア"""

    @web.middleware
    async def middleware(self, request: web.Request, handler):
        """セキュリティヘッダー追加"""
        response = await handler(request)

        # セキュリティヘッダー
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response

async def create_secure_app() -> web.Application:
    """セキュアなアプリケーション作成"""
    import os

    # 環境変数から設定読み込み
    jwt_secret = os.getenv('JWT_SECRET_KEY', 'change-this-secret')
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    rate_limit = int(os.getenv('API_RATE_LIMIT', '100'))
    rate_window = int(os.getenv('API_RATE_LIMIT_PERIOD', '60'))

    # コンポーネント初期化
    jwt_auth = JWTAuth(secret_key=jwt_secret)
    rate_limiter = RateLimiter(
        redis_url=redis_url,
        default_limit=rate_limit,
        default_window=rate_window
    )

    await rate_limiter.connect()

    # ミドルウェア作成
    auth_middleware = AuthMiddleware(jwt_auth, rate_limiter)
    security_headers = SecurityHeaders()

    # アプリケーション作成
    app = web.Application(
        middlewares=[
            security_headers.middleware,
            auth_middleware.middleware
        ]
    )

    # 認証エンドポイント追加
    async def login(request):
        """ログインエンドポイント"""
        data = await request.json()
        username = data.get('username')
        password = data.get('password')

        # TODO: 実際のユーザー認証ロジック
        if username == 'admin' and password == 'password':
            token = jwt_auth.generate_token(
                user_id='admin',
                roles=['admin', 'user']
            )
            return web.json_response({'token': token})

        return web.json_response(
            {'error': 'Invalid credentials'},
            status=401
        )

    async def refresh(request):
        """トークンリフレッシュエンドポイント"""
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            new_token = jwt_auth.refresh_token(token)
            if new_token:
                return web.json_response({'token': new_token})

        return web.json_response(
            {'error': 'Invalid token'},
            status=401
        )

    app.router.add_post('/auth/login', login)
    app.router.add_post('/auth/refresh', refresh)

    return app

if __name__ == "__main__":
    # テスト実行
    async def main():
        app = await create_secure_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8080)
        await site.start()

        print("="*60)
        print("🔒 Security Middleware Test Server")
        print("="*60)
        print("Server running on http://localhost:8080")
        print("Login endpoint: POST /auth/login")
        print("Refresh endpoint: POST /auth/refresh")

        while True:
            await asyncio.sleep(3600)

    asyncio.run(main())