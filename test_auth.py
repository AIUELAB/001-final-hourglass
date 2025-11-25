#!/usr/bin/env python3
"""認証エンドポイントのテスト"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """ログインテスト"""
    print("=" * 50)
    print("ログインテスト (admin)")
    print("=" * 50)

    response = requests.post(
        f"{BASE_URL}/api/auth/token",
        data={"username": "admin", "password": "admin123"}
    )

    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    if response.status_code == 200:
        return response.json()["access_token"]
    return None


def test_get_user_info(token):
    """ユーザー情報取得テスト"""
    print("\n" + "=" * 50)
    print("ユーザー情報取得テスト")
    print("=" * 50)

    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_invalid_login():
    """無効な認証情報でのテスト"""
    print("\n" + "=" * 50)
    print("無効な認証情報テスト")
    print("=" * 50)

    response = requests.post(
        f"{BASE_URL}/api/auth/token",
        data={"username": "invalid", "password": "wrong"}
    )

    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_other_users():
    """他のユーザーのログインテスト"""
    users = [
        ("editor", "editor123"),
        ("viewer", "viewer123")
    ]

    for username, password in users:
        print("\n" + "=" * 50)
        print(f"ログインテスト ({username})")
        print("=" * 50)

        response = requests.post(
            f"{BASE_URL}/api/auth/token",
            data={"username": username, "password": password}
        )

        print(f"ステータスコード: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            print(f"トークン取得成功: {token_data['token_type']}")
        else:
            print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    try:
        # 1. 正常なログイン
        token = test_login()

        # 2. ユーザー情報取得
        if token:
            test_get_user_info(token)

        # 3. 無効な認証情報
        test_invalid_login()

        # 4. 他のユーザー
        test_other_users()

        print("\n" + "=" * 50)
        print("✅ すべてのテスト完了")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
