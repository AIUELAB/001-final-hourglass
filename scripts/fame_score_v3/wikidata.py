"""
Wikidata SPARQL を使用して人物情報を取得するモジュール。

取得する指標:
- sitelinks: 言語版数（何言語のWikipediaに記事があるか）
- statements: プロパティ数（Wikidataに登録された情報量）
- inlinks: 被リンク数（他のWikidata項目からの参照数）
"""

import time
from typing import Optional

import requests

# Wikidata SPARQL エンドポイント
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# レート制限用
_last_request_time = 0.0
REQUEST_INTERVAL = 0.1  # 10 req/sec（SPARQLは控えめに）


def _rate_limit() -> None:
    """レート制限を適用"""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def get_wikidata_metrics_by_id(
    wikidata_id: str,
    timeout: float = 30.0,
) -> dict:
    """
    Wikidata IDから指標を取得。

    Args:
        wikidata_id: Wikidata ID（例: "Q312"）
        timeout: タイムアウト秒数

    Returns:
        {
            "wikidata_id": str,
            "sitelinks": int,      # 言語版数
            "statements": int,      # プロパティ数
            "inlinks": int,         # 被リンク数（概算）
            "label_ja": str,        # 日本語ラベル
            "label_en": str,        # 英語ラベル
            "description_ja": str,  # 日本語説明
            "is_japanese": bool,    # 日本人フラグ
        }
    """
    _rate_limit()

    result = {
        "wikidata_id": wikidata_id,
        "sitelinks": 0,
        "statements": 0,
        "inlinks": 0,
        "label_ja": "",
        "label_en": "",
        "description_ja": "",
        "is_japanese": False,
    }

    # Entity Data APIを使用（SPARQLより高速）
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"
    headers = {"User-Agent": "FameScoreBot/3.0 (https://github.com/example; contact@example.com)"}

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return result

        data = response.json()
        entity = data.get("entities", {}).get(wikidata_id, {})

        # 言語版数（sitelinks）
        sitelinks = entity.get("sitelinks", {})
        result["sitelinks"] = len(sitelinks)

        # プロパティ数（claims/statements）
        claims = entity.get("claims", {})
        statement_count = sum(len(v) for v in claims.values())
        result["statements"] = statement_count

        # ラベル・説明
        labels = entity.get("labels", {})
        descriptions = entity.get("descriptions", {})
        result["label_ja"] = labels.get("ja", {}).get("value", "")
        result["label_en"] = labels.get("en", {}).get("value", "")
        result["description_ja"] = descriptions.get("ja", {}).get("value", "")

        # 日本人判定（P27 = country of citizenship）
        result["is_japanese"] = _check_is_japanese(claims)

        return result

    except (requests.RequestException, ValueError, KeyError):
        return result


def _check_is_japanese(claims: dict) -> bool:
    """
    P27（国籍）をチェックして日本人かどうか判定。

    Q17 = Japan
    """
    Q_JAPAN = "Q17"

    # P27 (country of citizenship)
    p27_claims = claims.get("P27", [])
    for claim in p27_claims:
        try:
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if value.get("id") == Q_JAPAN:
                return True
        except (KeyError, TypeError):
            continue

    # P27がない場合、P19（出生地）をフォールバック確認
    # 日本の都道府県/市区町村は Q17 の下位エンティティだが、
    # 完全な判定は複雑なためP27優先
    return False


def get_inlinks_count(
    wikidata_id: str,
    timeout: float = 60.0,
) -> int:
    """
    Wikidata IDへの被リンク数を取得（SPARQL使用）。

    Note: この処理は重いため、キャッシュを推奨。

    Args:
        wikidata_id: Wikidata ID（例: "Q312"）
        timeout: タイムアウト秒数

    Returns:
        被リンク数
    """
    _rate_limit()

    # 被リンク数をカウントするSPARQLクエリ
    query = f"""
    SELECT (COUNT(?item) AS ?count) WHERE {{
        ?item ?p wd:{wikidata_id} .
        FILTER(STRSTARTS(STR(?item), "http://www.wikidata.org/entity/Q"))
    }}
    """

    headers = {
        "User-Agent": "FameScoreBot/3.0 (https://github.com/example; contact@example.com)",
        "Accept": "application/sparql-results+json",
    }
    params = {"query": query}

    try:
        response = requests.get(SPARQL_ENDPOINT, headers=headers, params=params, timeout=timeout)
        if response.status_code != 200:
            return 0

        data = response.json()
        bindings = data.get("results", {}).get("bindings", [])
        if bindings:
            count_str = bindings[0].get("count", {}).get("value", "0")
            return int(count_str)
        return 0

    except (requests.RequestException, ValueError):
        return 0


def get_wikipedia_backlinks_count(
    wikidata_id: str,
    lang: str = "ja",
    timeout: float = 30.0,
) -> int:
    """
    Wikipedia記事の被リンク数（バックリンク）を取得。

    Wikipedia APIを使用するため、SPARQLより高速。

    Args:
        wikidata_id: Wikidata ID（例: "Q312"）
        lang: Wikipedia言語コード（例: "ja", "en"）
        timeout: タイムアウト秒数

    Returns:
        被リンク数（取得失敗時は0）
    """
    _rate_limit()

    # まずWikidata IDからWikipedia記事タイトルを取得
    entity_url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"
    headers = {"User-Agent": "FameScoreBot/3.0 (https://github.com/example; contact@example.com)"}

    try:
        response = requests.get(entity_url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return 0

        data = response.json()
        entity = data.get("entities", {}).get(wikidata_id, {})
        sitelinks = entity.get("sitelinks", {})

        # 言語版Wikipediaのタイトルを取得
        wiki_key = f"{lang}wiki"
        if wiki_key not in sitelinks:
            # 日本語版がない場合は英語版を試す
            wiki_key = "enwiki"
            if wiki_key not in sitelinks:
                return 0

        article_title = sitelinks[wiki_key].get("title", "")
        if not article_title:
            return 0

        # Wikipedia APIでバックリンク数を取得
        wiki_lang = "en" if wiki_key == "enwiki" else lang
        return _get_backlinks_from_wikipedia(article_title, wiki_lang, timeout)

    except (requests.RequestException, ValueError, KeyError):
        return 0


def _get_backlinks_from_wikipedia(
    article_title: str,
    lang: str = "ja",
    timeout: float = 30.0,
) -> int:
    """
    Wikipedia記事タイトルから被リンク数を取得。

    Args:
        article_title: Wikipedia記事タイトル
        lang: Wikipedia言語コード
        timeout: タイムアウト秒数

    Returns:
        被リンク数
    """
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": article_title,
        "prop": "linkshere",
        "lhlimit": "500",  # 最大500件まで取得
        "lhnamespace": "0",  # 記事名前空間のみ
        "format": "json",
    }
    headers = {"User-Agent": "FameScoreBot/3.0 (https://github.com/example; contact@example.com)"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return 0

        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        for page_data in pages.values():
            if "linkshere" in page_data:
                return len(page_data["linkshere"])
        return 0

    except (requests.RequestException, ValueError):
        return 0


def get_inlinks_hybrid(
    wikidata_id: str,
    lang: str = "ja",
    use_sparql_fallback: bool = False,
) -> int:
    """
    被リンク数をハイブリッド方式で取得。

    優先順位:
    1. Wikipedia API（高速、言語別）
    2. Wikidata SPARQL（正確、全言語）- オプション

    Args:
        wikidata_id: Wikidata ID
        lang: Wikipedia言語コード
        use_sparql_fallback: Wikipedia APIで0の場合SPARQLを試すか

    Returns:
        被リンク数
    """
    if not wikidata_id:
        return 0

    # Wikipedia APIを優先（高速）
    backlinks = get_wikipedia_backlinks_count(wikidata_id, lang)
    if backlinks > 0:
        return backlinks

    # SPARQLフォールバック（オプション、時間がかかる）
    if use_sparql_fallback:
        return get_inlinks_count(wikidata_id)

    return 0


def search_wikidata(
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


def get_wikidata_info(
    person_name: str,
    wikidata_id: Optional[str] = None,
    include_inlinks: bool = False,
) -> dict:
    """
    人物名からWikidata情報を取得。

    Args:
        person_name: 人物名
        wikidata_id: Wikidata ID（指定しない場合は名前から検索）
        include_inlinks: 被リンク数も取得するか（時間がかかる）

    Returns:
        {
            "wikidata_id": str,
            "sitelinks": int,
            "statements": int,
            "inlinks": int,
            "label_ja": str,
            "label_en": str,
            "description_ja": str,
        }
    """
    # Wikidata IDがない場合は検索
    if not wikidata_id:
        wikidata_id = search_wikidata(person_name)

    if not wikidata_id:
        return {
            "wikidata_id": None,
            "sitelinks": 0,
            "statements": 0,
            "inlinks": 0,
            "label_ja": person_name,
            "label_en": "",
            "description_ja": "",
        }

    # 基本情報を取得
    result = get_wikidata_metrics_by_id(wikidata_id)

    # 被リンク数を取得（オプション）
    if include_inlinks:
        result["inlinks"] = get_inlinks_count(wikidata_id)

    return result


if __name__ == "__main__":
    # テスト実行
    test_persons = [
        "大谷翔平",
        "スティーブ・ジョブズ",
        "マイケル・ジョーダン",
        "小泉八雲",
    ]

    print("=== Wikidata情報取得テスト ===\n")

    for name in test_persons:
        print(f"取得中: {name}...")
        result = get_wikidata_info(name, include_inlinks=True)
        print(f"  Wikidata ID: {result['wikidata_id']}")
        print(f"  言語版数: {result['sitelinks']}")
        print(f"  プロパティ数: {result['statements']}")
        print(f"  被リンク数: {result['inlinks']}")
        print(f"  日本語名: {result['label_ja']}")
        print(f"  英語名: {result['label_en']}")
        print(f"  説明: {result['description_ja']}")
        print()
