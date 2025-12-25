"""
Google検索ヒット数を取得するモジュール（Phase 2用）。

キャッシュ優先方式:
- 同一person_idは再検索しない（DBキャッシュを返す）
- 初回のみAPI呼び出し→DB保存
- --force-refresh で強制再検索可能

使用には以下のAPIキーが必要:
- GOOGLE_API_KEY: Google Cloud APIキー
- GOOGLE_CSE_ID: Custom Search Engine ID
"""

import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

import requests

# APIキー（遅延読み込み用のキャッシュ）
_api_keys_cache: dict = {}


def _get_api_key(key_name: str) -> str:
    """APIキーを遅延読み込みで取得（環境変数の変更に対応）"""
    if key_name not in _api_keys_cache:
        _api_keys_cache[key_name] = os.environ.get(key_name, "")
    return _api_keys_cache[key_name]


def _refresh_api_keys() -> None:
    """APIキーキャッシュをクリア（再読み込み用）"""
    global _api_keys_cache
    _api_keys_cache = {}


# キャッシュDB
CACHE_DB_PATH = Path("data/cache/fame_score.db")

# レート制限用
_last_request_time = 0.0
REQUEST_INTERVAL = 1.0  # 1 req/sec（API制限対策）

# 統計カウンター（監視用）
_stats = {
    "cache_hits": 0,
    "api_calls": 0,
    "api_errors": 0,
}


def get_stats() -> dict:
    """統計情報を取得（監視用）"""
    return _stats.copy()


def reset_stats() -> None:
    """統計情報をリセット"""
    global _stats
    _stats = {"cache_hits": 0, "api_calls": 0, "api_errors": 0}


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
    return bool(_get_api_key("GOOGLE_API_KEY") and _get_api_key("GOOGLE_CSE_ID"))


def is_serpapi_available() -> bool:
    """SerpAPIが利用可能か確認"""
    return bool(_get_api_key("SERPAPI_API_KEY"))


def is_bing_available() -> bool:
    """Bing検索APIが利用可能か確認"""
    return bool(_get_api_key("BING_API_KEY"))


def get_cached_google_hits(person_id: str) -> Optional[int]:
    """
    キャッシュからGoogle検索ヒット数を取得。

    Args:
        person_id: 人物ID

    Returns:
        キャッシュ済みヒット数（未キャッシュならNone）
    """
    if not CACHE_DB_PATH.exists():
        return None

    try:
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.execute(
            "SELECT google_hits FROM fame_cache WHERE person_id = ? AND google_hits IS NOT NULL",
            (person_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            _stats["cache_hits"] += 1
            return row[0]
        return None
    except sqlite3.Error:
        return None


def save_google_hits_to_cache(person_id: str, hits: int) -> None:
    """
    Google検索ヒット数をキャッシュに保存。

    Args:
        person_id: 人物ID
        hits: ヒット数
    """
    if not CACHE_DB_PATH.exists():
        return

    try:
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        conn.execute(
            "UPDATE fame_cache SET google_hits = ? WHERE person_id = ?",
            (hits, person_id),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass


def get_google_search_hits(
    query: str,
    person_id: Optional[str] = None,
    force_refresh: bool = False,
    timeout: float = 10.0,
) -> Optional[int]:
    """
    Google Custom Search APIで検索ヒット数を取得（キャッシュ優先）。

    Args:
        query: 検索クエリ（人物名）
        person_id: 人物ID（キャッシュキー）
        force_refresh: キャッシュを無視して再検索
        timeout: タイムアウト秒数

    Returns:
        検索ヒット数（取得失敗時はNone）
    """
    # キャッシュチェック（force_refreshでない場合）
    if person_id and not force_refresh:
        cached = get_cached_google_hits(person_id)
        if cached is not None:
            return cached

    if not is_google_available():
        return None

    _rate_limit()
    _stats["api_calls"] += 1

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": _get_api_key("GOOGLE_API_KEY"),
        "cx": _get_api_key("GOOGLE_CSE_ID"),
        "q": query,
        "num": 1,
    }

    try:
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            total = data.get("searchInformation", {}).get("totalResults", "0")
            hits = int(total)

            # キャッシュに保存
            if person_id:
                save_google_hits_to_cache(person_id, hits)

            return hits
        elif response.status_code == 429:
            print("    [WARNING] Google API rate limit exceeded")
            _stats["api_errors"] += 1
            return None
        else:
            _stats["api_errors"] += 1
            return None
    except (requests.RequestException, ValueError) as e:
        print(f"    [WARNING] Google search error: {e}")
        _stats["api_errors"] += 1
        return None


def get_serpapi_search_hits(
    query: str,
    person_id: Optional[str] = None,
    force_refresh: bool = False,
    timeout: float = 10.0,
) -> Optional[int]:
    """
    SerpAPIで検索ヒット数を取得（Google検索の代替）。

    Args:
        query: 検索クエリ（人物名）
        person_id: 人物ID（キャッシュキー）
        force_refresh: キャッシュを無視して再検索
        timeout: タイムアウト秒数

    Returns:
        検索ヒット数（取得失敗時はNone）
    """
    # キャッシュチェック
    if person_id and not force_refresh:
        cached = get_cached_google_hits(person_id)
        if cached is not None:
            return cached

    if not is_serpapi_available():
        return None

    _rate_limit()
    _stats["api_calls"] += 1

    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "api_key": _get_api_key("SERPAPI_API_KEY"),
        "num": 1,
        "hl": "ja",
        "gl": "jp",
    }

    try:
        response = requests.get(url, params=params, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            total = data.get("search_information", {}).get("total_results", 0)
            hits = int(total)

            # キャッシュに保存
            if person_id:
                save_google_hits_to_cache(person_id, hits)

            return hits
        elif response.status_code == 429:
            print("    [WARNING] SerpAPI rate limit exceeded")
            _stats["api_errors"] += 1
            return None
        else:
            _stats["api_errors"] += 1
            return None
    except (requests.RequestException, ValueError) as e:
        print(f"    [WARNING] SerpAPI search error: {e}")
        _stats["api_errors"] += 1
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
    _stats["api_calls"] += 1

    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": _get_api_key("BING_API_KEY")}
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
            _stats["api_errors"] += 1
            return None
        else:
            _stats["api_errors"] += 1
            return None
    except (requests.RequestException, ValueError) as e:
        print(f"    [WARNING] Bing search error: {e}")
        _stats["api_errors"] += 1
        return None


def get_search_hits(
    query: str,
    person_id: Optional[str] = None,
    force_refresh: bool = False,
    prefer_google: bool = True,
) -> Optional[int]:
    """
    検索ヒット数を取得（キャッシュ優先、SerpAPI/Google優先、フォールバックでBing）。

    優先順位:
    1. SerpAPI（利用可能な場合）
    2. Google Custom Search API
    3. Bing Search API

    Args:
        query: 検索クエリ（人物名）
        person_id: 人物ID（キャッシュキー）
        force_refresh: キャッシュを無視して再検索
        prefer_google: Googleを優先するか

    Returns:
        検索ヒット数（取得失敗時はNone）
    """
    # SerpAPIを最優先（Google Custom Searchより安定）
    if is_serpapi_available():
        result = get_serpapi_search_hits(query, person_id, force_refresh)
        if result is not None:
            return result

    # Google Custom Search API
    if prefer_google and is_google_available():
        result = get_google_search_hits(query, person_id, force_refresh)
        if result is not None:
            return result

    # Bing Search API
    if is_bing_available():
        return get_bing_search_hits(query)

    if not prefer_google and is_google_available():
        return get_google_search_hits(query, person_id, force_refresh)

    return None


if __name__ == "__main__":
    print("=== Google/Bing検索ヒット数テスト（キャッシュ優先）===\n")
    print(f"Google API: {'有効' if is_google_available() else '無効'}")
    print(f"Bing API: {'有効' if is_bing_available() else '無効'}")
    print(f"Cache DB: {CACHE_DB_PATH}")
    print()

    if not is_google_available() and not is_bing_available():
        print("APIキーが設定されていません。")
    else:
        test_cases = [
            ("P22A0493", "ドナルド・トランプ"),
            ("P22A0493", "ドナルド・トランプ"),  # 2回目はキャッシュヒット
        ]

        for pid, name in test_cases:
            print(f"検索中: {name} ({pid})...")
            hits = get_search_hits(name, person_id=pid)
            if hits is not None:
                print(f"  ヒット数: {hits:,}")
            else:
                print("  取得失敗")

        print(f"\n統計: {get_stats()}")
