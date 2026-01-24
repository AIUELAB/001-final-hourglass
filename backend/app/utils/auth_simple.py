"""認証ユーティリティ（簡易版）

開発環境用の簡易認証システム
本番環境では適切なパスワードハッシュ化を実装すること
"""

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
_secret_key = os.getenv("JWT_SECRET_KEY")
if not _secret_key:
    raise ValueError(
        "JWT_SECRET_KEY environment variable is required. "
        'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
    )
SECRET_KEY: str = _secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


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
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
