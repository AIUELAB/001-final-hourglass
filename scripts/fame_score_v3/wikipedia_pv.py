"""
Wikipedia Pageviews API を使用して多言語PVを取得するモジュール。

Wikimedia REST API:
https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/{access}/user/{article}/daily/{start}/{end}
"""

import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

import requests

# 対象言語リスト
LANGUAGES = ["ja", "en", "zh", "ko", "es", "fr", "de", "ru", "pt", "it"]

# APIベースURL
PAGEVIEWS_API_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"

# レート制限用
_last_request_time = 0.0
REQUEST_INTERVAL = 0.02  # 50 req/sec


def _rate_limit() -> None:
    """レート制限を適用"""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def get_pageviews(
    project: str,
    article_title: str,
    days: int = 90,
    timeout: float = 10.0,
) -> int:
    """
    指定したWikipedia記事のページビュー数を取得。

    Args:
        project: プロジェクト名（例: "ja.wikipedia", "en.wikipedia"）
        article_title: 記事タイトル
        days: 取得期間（日数）
        timeout: タイムアウト秒数

    Returns:
        期間内の合計ページビュー数（取得失敗時は0）
    """
    _rate_limit()

    # 日付範囲を計算
    end_date = datetime.now() - timedelta(days=1)  # 昨日まで
    start_date = end_date - timedelta(days=days - 1)

    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    # 記事タイトルをURLエンコード
    encoded_title = urllib.parse.quote(article_title.replace(" ", "_"), safe="")

    url = f"{PAGEVIEWS_API_BASE}/{project}/all-access/user/{encoded_title}/daily/{start_str}/{end_str}"

    headers = {"User-Agent": "FameScoreBot/3.0 (https://github.com/example; contact@example.com)"}

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            total_views = sum(item.get("views", 0) for item in data.get("items", []))
            return total_views
        elif response.status_code == 404:
            # 記事が存在しない
            return 0
        else:
            return 0
    except (requests.RequestException, ValueError):
        return 0


def get_wiki_title_from_wikidata(
    wikidata_id: str,
    lang: str,
    timeout: float = 10.0,
) -> Optional[str]:
    """
    WikidataからWikipedia記事タイトルを取得。

    Args:
        wikidata_id: Wikidata ID（例: "Q312"）
        lang: 言語コード（例: "ja", "en"）
        timeout: タイムアウト秒数

    Returns:
        Wikipedia記事タイトル（存在しない場合はNone）
    """
    _rate_limit()

    url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"
    headers = {"User-Agent": "FameScoreBot/3.0 (https://github.com/example; contact@example.com)"}

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return None

        data = response.json()
        entities = data.get("entities", {})
        entity = entities.get(wikidata_id, {})
        sitelinks = entity.get("sitelinks", {})

        wiki_key = f"{lang}wiki"
        if wiki_key in sitelinks:
            return sitelinks[wiki_key].get("title")
        return None
    except (requests.RequestException, ValueError, KeyError):
        return None


def search_wikidata_by_name(
    name: str,
    lang: str = "ja",
    timeout: float = 10.0,
) -> Optional[str]:
    """
    人物名からWikidata IDを検索。

    Args:
        name: 人物名
        lang: 検索言語
        timeout: タイムアウト秒数

    Returns:
        Wikidata ID（見つからない場合はNone）
    """
    _rate_limit()

    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": lang,
        "format": "json",
        "limit": 1,
        "type": "item",
    }
    headers = {"User-Agent": "FameScoreBot/3.0 (https://github.com/example; contact@example.com)"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return None

        data = response.json()
        search_results = data.get("search", [])
        if search_results:
            return search_results[0].get("id")
        return None
    except (requests.RequestException, ValueError):
        return None


def get_multi_lang_pageviews(
    person_name: str,
    wikidata_id: Optional[str] = None,
    days: int = 90,
    languages: Optional[list[str]] = None,
) -> dict:
    """
    複数言語版のWikipedia PVを取得。

    Args:
        person_name: 人物名
        wikidata_id: Wikidata ID（指定しない場合は名前から検索）
        days: 取得期間（日数）
        languages: 言語リスト（指定しない場合はデフォルト10言語）

    Returns:
        {
            "wikidata_id": str,
            "total_pv": int,
            "avg_daily_pv": float,
            "by_lang": {"ja": int, "en": int, ...},
            "found_langs": int,
        }
    """
    if languages is None:
        languages = LANGUAGES

    result = {
        "wikidata_id": wikidata_id,
        "total_pv": 0,
        "avg_daily_pv": 0.0,
        "by_lang": {},
        "found_langs": 0,
    }

    # Wikidata IDがない場合は検索
    if not wikidata_id:
        wikidata_id = search_wikidata_by_name(person_name)
        result["wikidata_id"] = wikidata_id

    if not wikidata_id:
        # Wikidata IDが見つからない場合、日本語名で直接検索
        ja_pv = get_pageviews("ja.wikipedia", person_name, days)
        if ja_pv > 0:
            result["by_lang"]["ja"] = ja_pv
            result["total_pv"] = ja_pv
            result["avg_daily_pv"] = ja_pv / days
            result["found_langs"] = 1
        return result

    # 各言語版のタイトルを取得してPVを集計
    total_pv = 0
    for lang in languages:
        title = get_wiki_title_from_wikidata(wikidata_id, lang)
        if title:
            project = f"{lang}.wikipedia"
            pv = get_pageviews(project, title, days)
            if pv > 0:
                result["by_lang"][lang] = pv
                total_pv += pv
                result["found_langs"] += 1

    result["total_pv"] = total_pv
    result["avg_daily_pv"] = total_pv / days if days > 0 else 0.0

    return result


if __name__ == "__main__":
    # テスト実行
    test_persons = [
        "大谷翔平",
        "スティーブ・ジョブズ",
        "マイケル・ジョーダン",
        "小泉八雲",
    ]

    print("=== Wikipedia多言語PV取得テスト ===\n")

    for name in test_persons:
        print(f"取得中: {name}...")
        result = get_multi_lang_pageviews(name)
        print(f"  Wikidata ID: {result['wikidata_id']}")
        print(f"  合計PV: {result['total_pv']:,}")
        print(f"  日平均: {result['avg_daily_pv']:,.1f}")
        print(f"  言語版数: {result['found_langs']}")
        print(f"  内訳: {result['by_lang']}")
        print()
