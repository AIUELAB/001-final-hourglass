#!/usr/bin/env python3
"""
External Fact Checker - Wikipedia/Wikidata APIを使用した外部事実検証

機能:
- Wikipedia APIによる人物情報取得
- Wikidata SPARQLによる構造化データ検証
- 生年・没年・業績の外部検証
- キャッシュによるAPI呼び出し最適化

使用方法:
    >>> from src.external_fact_checker import ExternalFactChecker
    >>> checker = ExternalFactChecker()
    >>> result = checker.verify_person("大谷翔平")
    >>> print(result)
"""

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

import requests

from src.csv_path_resolver import get_project_root

JsonDict = dict[str, Any]


class FactCache:
    """ファクトチェック結果のキャッシュ管理"""

    def __init__(self, cache_dir: Optional[Path] = None, ttl_days: int = 7):
        if cache_dir is None:
            self.cache_dir = get_project_root() / "preserved" / "fact_cache"
        else:
            self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_days * 24 * 60 * 60

    def _get_cache_key(self, key: str) -> str:
        """キャッシュキーを生成"""
        return hashlib.md5(key.encode("utf-8"), usedforsecurity=False).hexdigest()

    def get(self, key: str) -> Optional[JsonDict]:
        """キャッシュから取得"""
        cache_key = self._get_cache_key(key)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)

            # TTLチェック
            if not isinstance(cached, dict):
                return None
            cached_at = cached.get("cached_at")
            if not isinstance(cached_at, str):
                return None
            cached_time = datetime.fromisoformat(cached_at)
            if (datetime.now() - cached_time).total_seconds() > self.ttl_seconds:
                cache_file.unlink()
                return None

            data = cached.get("data")
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            return None

    def set(self, key: str, data: JsonDict) -> None:
        """キャッシュに保存"""
        cache_key = self._get_cache_key(key)
        cache_file = self.cache_dir / f"{cache_key}.json"

        cached = {
            "key": key,
            "cached_at": datetime.now().isoformat(),
            "data": data,
        }

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cached, f, ensure_ascii=False, indent=2)


class WikipediaFactChecker:
    """Wikipedia APIを使用した事実検証"""

    WIKIPEDIA_API_URL = "https://ja.wikipedia.org/w/api.php"
    USER_AGENT = "EpisodeFactChecker/1.0 (https://example.com; contact@example.com)"

    def __init__(self, cache: Optional[FactCache] = None):
        self.cache = cache or FactCache()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    def _make_request(self, params: JsonDict) -> Optional[JsonDict]:
        """Wikipedia APIリクエスト"""
        params["format"] = "json"

        try:
            response = self.session.get(
                self.WIKIPEDIA_API_URL,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else None
        except requests.RequestException as e:
            print(f"  Wikipedia API error: {e}")
            return None

    def get_page_extract(self, title: str) -> Optional[str]:
        """ページの概要を取得"""
        cache_key = f"wp_extract:{title}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached.get("extract")

        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
        }

        result = self._make_request(params)
        if not result:
            return None

        pages = result.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id != "-1":
                extract = page.get("extract", "")
                self.cache.set(cache_key, {"extract": extract})
                return str(extract) if isinstance(extract, str) else None

        return None

    def search_person(self, name: str) -> Optional[JsonDict]:
        """人物を検索してページ情報を取得"""
        cache_key = f"wp_search:{name}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        params = {
            "action": "query",
            "list": "search",
            "srsearch": name,
            "srlimit": 5,
        }

        result = self._make_request(params)
        if not result:
            return None

        search_results = result.get("query", {}).get("search", [])
        if not search_results:
            return None

        # 最初の結果を使用
        page_info = {
            "title": search_results[0]["title"],
            "pageid": search_results[0]["pageid"],
            "snippet": search_results[0].get("snippet", ""),
        }

        self.cache.set(cache_key, page_info)
        return page_info

    def verify_birth_year(self, person_name: str, expected_year: int) -> dict:
        """生年を外部検証"""
        result = {
            "person_name": person_name,
            "expected_year": expected_year,
            "verified": False,
            "source": "wikipedia",
        }

        extract = self.get_page_extract(person_name)
        if not extract:
            result["status"] = "not_found"
            return result

        # 生年パターンを検索
        patterns = [
            r"(\d{4})年\s*(?:\d+月\s*\d+日\s*)?(?:[-–]|生まれ|出生)",
            r"(\d{4})年生まれ",
            r"(\d{4})年\s*\d+月\s*\d+日生",
            r"生年月日.*?(\d{4})年",
        ]

        for pattern in patterns:
            match = re.search(pattern, extract)
            if match:
                found_year = int(match.group(1))
                result["found_year"] = found_year
                result["verified"] = found_year == expected_year
                result["diff"] = abs(found_year - expected_year)
                result["status"] = "verified" if result["verified"] else "mismatch"
                return result

        result["status"] = "year_not_found"
        return result

    def verify_death_year(self, person_name: str, expected_year: int) -> dict:
        """没年を外部検証"""
        result = {
            "person_name": person_name,
            "expected_year": expected_year,
            "verified": False,
            "source": "wikipedia",
        }

        extract = self.get_page_extract(person_name)
        if not extract:
            result["status"] = "not_found"
            return result

        # 没年パターンを検索
        patterns = [
            r"(\d{4})年\s*(?:\d+月\s*\d+日\s*)?(?:没|死去|逝去)",
            r"[-–]\s*(\d{4})年",
            r"(\d{4})年.*?死去",
        ]

        for pattern in patterns:
            match = re.search(pattern, extract)
            if match:
                found_year = int(match.group(1))
                result["found_year"] = found_year
                result["verified"] = found_year == expected_year
                result["diff"] = abs(found_year - expected_year)
                result["status"] = "verified" if result["verified"] else "mismatch"
                return result

        result["status"] = "year_not_found"
        return result


class WikidataVerifier:
    """Wikidata SPARQLを使用した構造化データ検証"""

    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    USER_AGENT = "EpisodeFactChecker/1.0 (https://example.com; contact@example.com)"

    def __init__(self, cache: Optional[FactCache] = None):
        self.cache = cache or FactCache()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept": "application/sparql-results+json",
            }
        )

    def _execute_sparql(self, query: str) -> Optional[JsonDict]:
        """SPARQLクエリを実行"""
        try:
            response = self.session.get(
                self.SPARQL_ENDPOINT,
                params={"query": query},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else None
        except requests.RequestException as e:
            print(f"  Wikidata SPARQL error: {e}")
            return None

    def search_person_by_name(self, name: str, lang: str = "ja") -> Optional[str]:
        """名前からWikidata IDを検索"""
        cache_key = f"wd_search:{name}:{lang}"
        cached = self.cache.get(cache_key)
        if cached:
            wikidata_id = cached.get("wikidata_id")
            return wikidata_id if isinstance(wikidata_id, str) else None

        query = f"""
        SELECT ?item WHERE {{
          ?item rdfs:label "{name}"@{lang}.
          ?item wdt:P31 wd:Q5.
        }}
        LIMIT 1
        """

        result = self._execute_sparql(query)
        if not result:
            return None

        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            # mypy対策: `Any` になりやすいので型を確定させる
            item = bindings[0].get("item") if isinstance(bindings[0], dict) else None
            value = item.get("value") if isinstance(item, dict) else None
            if isinstance(value, str) and value:
                wikidata_id = value.split("/")[-1]
                self.cache.set(cache_key, {"wikidata_id": wikidata_id})
                return wikidata_id

        return None

    def get_person_facts(self, wikidata_id: str) -> Optional[JsonDict]:
        """人物の構造化事実データを取得"""
        cache_key = f"wd_facts:{wikidata_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        query = f"""
        SELECT ?birthDate ?deathDate ?occupation ?occupationLabel WHERE {{
          OPTIONAL {{ wd:{wikidata_id} wdt:P569 ?birthDate. }}
          OPTIONAL {{ wd:{wikidata_id} wdt:P570 ?deathDate. }}
          OPTIONAL {{ wd:{wikidata_id} wdt:P106 ?occupation. }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en". }}
        }}
        """

        result = self._execute_sparql(query)
        if not result:
            return None

        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return None

        occupations: list[str] = []
        facts: JsonDict = {
            "wikidata_id": wikidata_id,
            "birth_date": None,
            "death_date": None,
            "occupations": occupations,
        }

        for binding in bindings:
            if "birthDate" in binding and not facts["birth_date"]:
                facts["birth_date"] = binding["birthDate"]["value"][:10]
            if "deathDate" in binding and not facts["death_date"]:
                facts["death_date"] = binding["deathDate"]["value"][:10]
            if "occupationLabel" in binding:
                occ = binding["occupationLabel"]["value"]
                if isinstance(occ, str) and occ not in occupations:
                    occupations.append(occ)

        self.cache.set(cache_key, facts)
        return facts

    def verify_birth_year(self, person_name: str, expected_year: int) -> dict:
        """Wikidataで生年を検証"""
        result = {
            "person_name": person_name,
            "expected_year": expected_year,
            "verified": False,
            "source": "wikidata",
        }

        wikidata_id = self.search_person_by_name(person_name)
        if not wikidata_id:
            result["status"] = "not_found"
            return result

        facts = self.get_person_facts(wikidata_id)
        if not facts or not facts.get("birth_date"):
            result["status"] = "birth_date_not_found"
            return result

        try:
            found_year = int(facts["birth_date"][:4])
            result["found_year"] = found_year
            result["wikidata_id"] = wikidata_id
            result["verified"] = found_year == expected_year
            result["diff"] = abs(found_year - expected_year)
            result["status"] = "verified" if result["verified"] else "mismatch"
        except (ValueError, IndexError):
            result["status"] = "parse_error"

        return result


class ExternalFactChecker:
    """外部ファクトチェックの統合クラス"""

    def __init__(self, delay_seconds: float = 1.0):
        self.cache = FactCache()
        self.wikipedia = WikipediaFactChecker(self.cache)
        self.wikidata = WikidataVerifier(self.cache)
        self.delay = delay_seconds
        self.last_request_time: float = 0.0

    def _rate_limit(self) -> None:
        """レート制限"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()

    def verify_person(self, person_name: str, expected_birth_year: Optional[int] = None) -> JsonDict:
        """
        人物情報を総合的に検証

        Args:
            person_name: 人物名
            expected_birth_year: 期待される生年（オプション）

        Returns:
            検証結果の辞書
        """
        self._rate_limit()

        sources: JsonDict = {}
        result: JsonDict = {
            "person_name": person_name,
            "timestamp": datetime.now().isoformat(),
            "sources": sources,
        }

        # Wikipedia検証
        wp_extract = self.wikipedia.get_page_extract(person_name)
        sources["wikipedia"] = {
            "found": wp_extract is not None,
            "extract_preview": wp_extract[:200] if wp_extract else None,
        }

        if expected_birth_year:
            self._rate_limit()
            wp_birth = self.wikipedia.verify_birth_year(person_name, expected_birth_year)
            sources["wikipedia"]["birth_verification"] = wp_birth  # type: ignore[index]

        # Wikidata検証
        self._rate_limit()
        wd_id = self.wikidata.search_person_by_name(person_name)
        if wd_id:
            self._rate_limit()
            wd_facts = self.wikidata.get_person_facts(wd_id)
            sources["wikidata"] = {
                "found": True,
                "wikidata_id": wd_id,
                "facts": wd_facts,
            }

            if expected_birth_year:
                wd_birth = self.wikidata.verify_birth_year(person_name, expected_birth_year)
                sources["wikidata"]["birth_verification"] = wd_birth  # type: ignore[index]
        else:
            sources["wikidata"] = {"found": False}

        # 総合判定
        result["overall_status"] = self._determine_overall_status(result)

        return result

    def _determine_overall_status(self, result: dict) -> str:
        """総合ステータスを判定"""
        wp_found = result["sources"]["wikipedia"]["found"]
        wd_found = result["sources"]["wikidata"]["found"]

        if not wp_found and not wd_found:
            return "unknown"

        # 生年検証がある場合
        wp_birth = result["sources"]["wikipedia"].get("birth_verification", {})
        wd_birth = result["sources"]["wikidata"].get("birth_verification", {})

        if wp_birth.get("verified") or wd_birth.get("verified"):
            return "verified"

        if wp_birth.get("status") == "mismatch" or wd_birth.get("status") == "mismatch":
            return "mismatch"

        if wp_found or wd_found:
            return "partially_verified"

        return "unknown"


def verify_sample_persons():
    """サンプル人物の検証"""
    checker = ExternalFactChecker(delay_seconds=1.5)

    test_cases = [
        ("大谷翔平", 1994),
        ("手塚治虫", 1928),
        ("夏目漱石", 1867),
        ("坂本龍馬", 1836),
    ]

    print("=" * 60)
    print("External Fact Checker - Sample Verification")
    print("=" * 60)

    for name, expected_year in test_cases:
        print(f"\n{name} (expected: {expected_year})")
        result = checker.verify_person(name, expected_year)

        wp = result["sources"]["wikipedia"]
        wd = result["sources"]["wikidata"]

        print(f"  Wikipedia: {'Found' if wp['found'] else 'Not found'}")
        if wp.get("birth_verification"):
            bv = wp["birth_verification"]
            print(f"    Birth: {bv.get('status')} (found: {bv.get('found_year')})")

        print(f"  Wikidata: {'Found' if wd['found'] else 'Not found'}")
        if wd.get("birth_verification"):
            bv = wd["birth_verification"]
            print(f"    Birth: {bv.get('status')} (found: {bv.get('found_year')})")

        print(f"  Overall: {result['overall_status']}")


if __name__ == "__main__":
    verify_sample_persons()
