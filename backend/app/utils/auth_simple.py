"""認証ユーティリティ（簡易版）

開発環境用の簡易認証システム
本番環境では適切なパスワードハッシュ化を実装すること
"""

import functools
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

logger = logging.getLogger(__name__)

# OAuth2スキーム
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

# JWT設定
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


@functools.lru_cache(maxsize=1)
def get_secret_key() -> str:
    """JWT秘密鍵を取得（遅延評価・キャッシュ付き）

    環境変数JWT_SECRET_KEYから秘密鍵を取得する。
    未設定の場合はValueErrorを発生させる。
    """
    key = os.getenv("JWT_SECRET_KEY")
    if not key:
        raise ValueError(
            "JWT_SECRET_KEY environment variable is required. "
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    return key


def validate_jwt_config() -> None:
    """起動時にJWT設定を検証（Fail-Fast）

    アプリケーション起動時に呼び出すことで、
    設定エラーを早期検出する。

    Raises:
        ValueError: JWT_SECRET_KEYが未設定の場合

    Example:
        # main.py または startup.py
        from backend.app.utils.auth_simple import validate_jwt_config
        validate_jwt_config()  # 失敗時は即座にValueError
    """
    try:
        get_secret_key()
        logger.info("JWT configuration validated successfully")
    except ValueError as e:
        logger.critical(f"JWT configuration error: {e}")
        raise


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWTアクセストークンを生成

    Args:
        data: トークンに含めるデータ
        expires_delta: 有効期限（オプション）

    Returns:
        JWT Access Token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception: HTTPException) -> str:
    """JWTトークンを検証

    Args:
        token: JWTトークン
        credentials_exception: 検証失敗時の例外

    Returns:
        ユーザー名

    Raises:
        credentials_exception: トークン検証失敗時
    """
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except ExpiredSignatureError:
        logger.warning("Token expired")
        raise credentials_exception
    except (DecodeError, InvalidTokenError) as e:
        logger.warning(f"Invalid token: {e}")
        raise credentials_exception
    except ValueError as e:
        # JWT_SECRET_KEY未設定などの設定エラーは500エラー
        logger.error(f"Configuration error in token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバー設定エラーが発生しました",
        )
    except (KeyboardInterrupt, SystemExit):
        # シグナルは再raise
        raise
    except (MemoryError, RecursionError) as e:
        # システムリソース不足は503エラー
        logger.critical(f"System resource error in token verification: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="サーバーリソース不足です。後でお試しください",
        )
    except Exception as e:
        # 予期しないエラーは500エラー（認証エラーと区別）
        logger.error(
            f"Unexpected error during token verification: {type(e).__name__}: {e}",
            exc_info=True,  # スタックトレースも記録
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="トークン検証中に予期しないエラーが発生しました",
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """現在のユーザーを取得

    Args:
        token: JWTトークン（OAuth2から自動取得）

    Returns:
        ユーザー名

    Raises:
        HTTPException: 認証失敗時
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報を検証できませんでした",
        headers={"WWW-Authenticate": "Bearer"},
    )

    username = verify_token(token, credentials_exception)
    return username


def get_current_user_with_role(current_user: str = Depends(get_current_user)) -> dict:
    """現在のユーザー情報（ロール含む）を取得

    Args:
        current_user: 認証済みユーザー名

    Returns:
        ユーザー情報（usernameとroleを含む）

    Raises:
        HTTPException: ユーザーが見つからない場合
    """
    user = get_user(current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ユーザーが見つかりません")
    return {"username": user["username"], "role": user["role"]}


def require_role(allowed_roles: list[str]):
    """ロールベースのアクセス制御デコレーター

    Args:
        allowed_roles: 許可するロールのリスト

    Returns:
        依存関数

    Example:
        @app.delete("/api/episodes/{id}")
        async def delete_episode(
            id: str,
            user: dict = Depends(require_role(["admin"]))
        ):
            ...
    """

    def role_checker(user: dict = Depends(get_current_user_with_role)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"この操作には {', '.join(allowed_roles)} の権限が必要です",
            )
        return user

    return role_checker


def _validate_fake_users_environment() -> None:
    """本番環境でのFAKE_USERS_DB使用を防止（Fail-Fast）

    モジュールロード時に呼び出され、本番環境では
    RuntimeErrorを発生させて起動を阻止する。

    Raises:
        RuntimeError: ENVIRONMENT=productionの場合
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        raise RuntimeError(
            "FAKE_USERS_DB cannot be used in production environment. "
            "Set up proper authentication with bcrypt/passlib."
        )
    logger.warning("Using FAKE_USERS_DB (development only). Do not use in production.")


# モジュールロード時に検証（本番環境で誤用された場合は即座に失敗）
_validate_fake_users_environment()

# ユーザーデータベース（簡易版・開発環境専用）
# 注意: 本番環境では適切なパスワードハッシュ化を実装すること
FAKE_USERS_DB = {
    "admin": {
        "username": "admin",
        "full_name": "管理者",
        "email": "admin@example.com",
        "password": "admin123",  # 平文パスワード（開発環境のみ）
        "role": "admin",
        "disabled": False,
    },
    "editor": {
        "username": "editor",
        "full_name": "編集者",
        "email": "editor@example.com",
        "password": "editor123",
        "role": "editor",
        "disabled": False,
    },
    "viewer": {
        "username": "viewer",
        "full_name": "閲覧者",
        "email": "viewer@example.com",
        "password": "viewer123",
        "role": "viewer",
        "disabled": False,
    },
}


def get_user(username: str) -> Optional[dict]:
    """ユーザー情報を取得

    Args:
        username: ユーザー名

    Returns:
        ユーザー情報、存在しない場合None
    """
    if username in FAKE_USERS_DB:
        return FAKE_USERS_DB[username]
    return None


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """ユーザー認証（簡易版）

    注意: パスワードを平文で比較しています（開発環境のみ）
    本番環境では適切なハッシュ化を実装すること

    Args:
        username: ユーザー名
        password: パスワード

    Returns:
        認証成功時はユーザー情報、失敗時はNone
    """
    user = get_user(username)
    if not user:
        return None
    if password != user["password"]:  # 平文比較（開発環境のみ）
        return None
    return user
