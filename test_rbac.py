#!/usr/bin/env python3
"""ロールベースアクセス制御（RBAC）のテスト"""

import requests
import json

BASE_URL = "http://localhost:8000"


def get_token(username: str, password: str) -> str:
    """ログインしてトークンを取得"""
    response = requests.post(
        f"{BASE_URL}/api/auth/token",
        data={"username": username, "password": password}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


def test_read_access():
    """読取アクセステスト（全員可能）"""
    print("=" * 60)
    print("読取アクセステスト")
    print("=" * 60)

    # 認証なしでGET
    response = requests.get(f"{BASE_URL}/api/episodes?page=1&page_size=5")
    print(f"\n[認証なし] GET /api/episodes")
    print(f"  ステータス: {response.status_code}")
    if response.status_code == 200:
        print(f"  ✅ 読取成功: {response.json()['total']}件")
    else:
        print(f"  ❌ 失敗: {response.text}")


def test_create_access():
    """作成アクセステスト"""
    print("\n" + "=" * 60)
    print("作成アクセステスト（admin, editorのみ）")
    print("=" * 60)

    test_data = {
        "person_name": "テスト太郎",
        "age": "25",
        "episode_text": "テストエピソード",
        "category": "テスト",
        "person_type": "REAL"
    }

    # viewer でPOST（失敗すべき）
    viewer_token = get_token("viewer", "viewer123")
    print("\n[viewer] POST /api/episodes")
    response = requests.post(
        f"{BASE_URL}/api/episodes",
        json=test_data,
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    print(f"  ステータス: {response.status_code}")
    if response.status_code == 403:
        print(f"  ✅ 期待通りアクセス拒否")
    else:
        print(f"  ❌ 予期しない結果: {response.text[:100]}")

    # editor でPOST（成功すべき）
    editor_token = get_token("editor", "editor123")
    print("\n[editor] POST /api/episodes")
    response = requests.post(
        f"{BASE_URL}/api/episodes",
        json=test_data,
        headers={"Authorization": f"Bearer {editor_token}"}
    )
    print(f"  ステータス: {response.status_code}")
    if response.status_code == 201:
        created_id = response.json()["person_id"]
        print(f"  ✅ 作成成功: person_id={created_id}")
        return created_id
    else:
        print(f"  ❌ 失敗: {response.text[:100]}")
        return None


def test_update_access(person_id: str):
    """更新アクセステスト"""
    if not person_id:
        print("\n⏭️  更新テストをスキップ（作成済みIDなし）")
        return

    print("\n" + "=" * 60)
    print("更新アクセステスト（admin, editorのみ）")
    print("=" * 60)

    update_data = {
        "episode_text": "更新されたエピソード"
    }

    # viewer でPUT（失敗すべき）
    viewer_token = get_token("viewer", "viewer123")
    print(f"\n[viewer] PUT /api/episodes/{person_id}")
    response = requests.put(
        f"{BASE_URL}/api/episodes/{person_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    print(f"  ステータス: {response.status_code}")
    if response.status_code == 403:
        print(f"  ✅ 期待通りアクセス拒否")
    else:
        print(f"  ❌ 予期しない結果")

    # editor でPUT（成功すべき）
    editor_token = get_token("editor", "editor123")
    print(f"\n[editor] PUT /api/episodes/{person_id}")
    response = requests.put(
        f"{BASE_URL}/api/episodes/{person_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {editor_token}"}
    )
    print(f"  ステータス: {response.status_code}")
    if response.status_code == 200:
        print(f"  ✅ 更新成功")
    else:
        print(f"  ❌ 失敗: {response.text[:100]}")


def test_delete_access(person_id: str):
    """削除アクセステスト"""
    if not person_id:
        print("\n⏭️  削除テストをスキップ（作成済みIDなし）")
        return

    print("\n" + "=" * 60)
    print("削除アクセステスト（adminのみ）")
    print("=" * 60)

    # viewer でDELETE（失敗すべき）
    viewer_token = get_token("viewer", "viewer123")
    print(f"\n[viewer] DELETE /api/episodes/{person_id}")
    response = requests.delete(
        f"{BASE_URL}/api/episodes/{person_id}",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    print(f"  ステータス: {response.status_code}")
    if response.status_code == 403:
        print(f"  ✅ 期待通りアクセス拒否")
    else:
        print(f"  ❌ 予期しない結果")

    # editor でDELETE（失敗すべき）
    editor_token = get_token("editor", "editor123")
    print(f"\n[editor] DELETE /api/episodes/{person_id}")
    response = requests.delete(
        f"{BASE_URL}/api/episodes/{person_id}",
        headers={"Authorization": f"Bearer {editor_token}"}
    )
    print(f"  ステータス: {response.status_code}")
    if response.status_code == 403:
        print(f"  ✅ 期待通りアクセス拒否")
    else:
        print(f"  ❌ 予期しない結果")

    # admin でDELETE（成功すべき）
    admin_token = get_token("admin", "admin123")
    print(f"\n[admin] DELETE /api/episodes/{person_id}")
    response = requests.delete(
        f"{BASE_URL}/api/episodes/{person_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print(f"  ステータス: {response.status_code}")
    if response.status_code == 200:
        print(f"  ✅ 削除成功")
    else:
        print(f"  ❌ 失敗: {response.text[:100]}")


if __name__ == "__main__":
    try:
        # 1. 読取アクセステスト
        test_read_access()

        # 2. 作成アクセステスト
        created_id = test_create_access()

        # 3. 更新アクセステスト
        test_update_access(created_id)

        # 4. 削除アクセステスト
        test_delete_access(created_id)

        print("\n" + "=" * 60)
        print("✅ すべてのRBACテスト完了")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
