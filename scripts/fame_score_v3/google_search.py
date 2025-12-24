"""
Google検索ヒット数を取得するモジュール（Phase 2用）。

使用には以下のAPIキーが必要:
- GOOGLE_API_KEY: Google Cloud APIキー
- GOOGLE_CSE_ID: Custom Search Engine ID

代替としてBing Search APIにも対応。
"""

import os
import time
from typing import Optional

import requests

# 環境変数からAPIキーを取得
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")
BING_API_KEY = os.environ.get("BING_API_KEY", "")

# レート制限用
_last_request_time = 0.0
REQUEST_INTERVAL = 1.0  # 1 req/sec（API制限対策）


def _rate_limit() -> None:
    """レート制限を適用"""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def is_google_available() -> bool:
    """Google検索APIが利用可能か確認"""
    return bool(GOOGLE_API_KEY and GOOGLE_CSE_ID)


def is_bing_available() -> bool:
    """Bing検索APIが利用可能か確認"""
    return bool(BING_API_KEY)


def get_google_search_hits(
    query: str,
    timeout: float = 10.0,
) -> Optional[int]:
    """
    Google Custom Search APIで検索ヒット数を取得。

    Args:
        query: 検索クエリ（人物名）
        timeout: タイムアウト秒数

    Returns:
        検索ヒット数（取得失敗時はNone）
    """
    if not is_google_available():
        return None

    _rate_limit()

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "num": 1,  # 最小限の結果のみ
    }

    try:
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            # totalResultsは概算値
            total = data.get("searchInformation", {}).get("totalResults", "0")
            return int(total)
        elif response.status_code == 429:
            # レート制限超過
            print("    [WARNING] Google API rate limit exceeded")
            return None
        else:
            return None
    except (requests.RequestException, ValueError) as e:
        print(f"    [WARNING] Google search error: {e}")
        return None


def get_bing_search_hits(
    query: str,
    timeout: float = 10.0,
) -> Optional[int]:
    """
    Bing Search APIで検索ヒット数を取得。

    Args:
        query: 検索クエリ（人物名）
        timeout: タイムアウト秒数

    Returns:
        検索ヒット数（取得失敗時はNone）
    """
    if not is_bing_available():
        return None

    _rate_limit()

    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
    params = {
        "q": query,
        "count": 1,
        "mkt": "ja-JP",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            total = data.get("webPages", {}).get("totalEstimatedMatches", 0)
            return int(total)
        elif response.status_code == 429:
            print("    [WARNING] Bing API rate limit exceeded")
            return None
        else:
            return None
    except (requests.RequestException, ValueError) as e:
        print(f"    [WARNING] Bing search error: {e}")
        return None


def get_search_hits(
    query: str,
    prefer_google: bool = True,
) -> Optional[int]:
    """
    検索ヒット数を取得（Google優先、フォールバックでBing）。

    Args:
        query: 検索クエリ（人物名）
        prefer_google: Googleを優先するか

    Returns:
        検索ヒット数（取得失敗時はNone）
    """
    if prefer_google and is_google_available():
        result = get_google_search_hits(query)
        if result is not None:
            return result

    if is_bing_available():
        return get_bing_search_hits(query)

    if not prefer_google and is_google_available():
        return get_google_search_hits(query)

    return None


if __name__ == "__main__":
    print("=== Google/Bing検索ヒット数テスト ===\n")
    print(f"Google API: {'有効' if is_google_available() else '無効'}")
    print(f"Bing API: {'有効' if is_bing_available() else '無効'}")
    print()

    if not is_google_available() and not is_bing_available():
        print("APIキーが設定されていません。")
        print("環境変数を設定してください:")
        print("  export GOOGLE_API_KEY=your_api_key")
        print("  export GOOGLE_CSE_ID=your_cse_id")
        print("または")
        print("  export BING_API_KEY=your_api_key")
    else:
        test_persons = [
            "大谷翔平",
            "スティーブ・ジョブズ",
            "マイケル・ジョーダン",
        ]

        for name in test_persons:
            print(f"検索中: {name}...")
            hits = get_search_hits(name)
            if hits is not None:
                print(f"  ヒット数: {hits:,}")
            else:
                print("  取得失敗")
            print()
