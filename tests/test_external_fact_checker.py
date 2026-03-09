"""
Tests for src/external_fact_checker.py

Comprehensive test suite covering:
- FactCache: init, get/set, TTL, edge cases
- WikipediaFactChecker: API requests, page extraction, search, birth/death verification
- WikidataVerifier: SPARQL execution, person search, facts retrieval, birth verification
- ExternalFactChecker: rate limiting, person verification, overall status determination
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.external_fact_checker import (
    ExternalFactChecker,
    FactCache,
    WikidataVerifier,
    WikipediaFactChecker,
)


# ============================================================
# FactCache Tests
# ============================================================
class TestFactCache:
    """FactCache unit tests."""

    def test_init_with_custom_cache_dir(self, tmp_path):
        cache_dir = tmp_path / "custom_cache"
        cache = FactCache(cache_dir=cache_dir, ttl_days=3)
        assert cache.cache_dir == cache_dir
        assert cache.cache_dir.exists()
        assert cache.ttl_seconds == 3 * 24 * 60 * 60

    @patch("src.external_fact_checker.get_project_root")
    def test_init_default_cache_dir(self, mock_root, tmp_path):
        mock_root.return_value = tmp_path
        cache = FactCache()
        assert cache.cache_dir == tmp_path / "preserved" / "fact_cache"
        assert cache.cache_dir.exists()

    def test_get_cache_key_deterministic(self, tmp_path):
        cache = FactCache(cache_dir=tmp_path)
        key1 = cache._get_cache_key("test_key")
        key2 = cache._get_cache_key("test_key")
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hex digest

    def test_get_cache_key_different_for_different_input(self, tmp_path):
        cache = FactCache(cache_dir=tmp_path)
        assert cache._get_cache_key("a") != cache._get_cache_key("b")

    def test_get_cache_miss(self, tmp_path):
        cache = FactCache(cache_dir=tmp_path)
        assert cache.get("nonexistent") is None

    def test_set_and_get_cache_hit(self, tmp_path):
        cache = FactCache(cache_dir=tmp_path, ttl_days=1)
        data = {"name": "test", "value": 42}
        cache.set("my_key", data)
        result = cache.get("my_key")
        assert result == data

    def test_get_expired_ttl(self, tmp_path):
        cache = FactCache(cache_dir=tmp_path, ttl_days=1)
        cache_key = cache._get_cache_key("expired_key")
        cache_file = tmp_path / f"{cache_key}.json"

        # Write a cache entry with a past timestamp
        old_time = (datetime.now() - timedelta(days=2)).isoformat()
        cache_file.write_text(
            json.dumps({"cached_at": old_time, "data": {"x": 1}}),
            encoding="utf-8",
        )

        result = cache.get("expired_key")
        assert result is None
        assert not cache_file.exists()  # expired file removed

    def test_get_invalid_json(self, tmp_path):
        cache = FactCache(cache_dir=tmp_path)
        cache_key = cache._get_cache_key("bad_json")
        cache_file = tmp_path / f"{cache_key}.json"
        cache_file.write_text("not valid json{{{", encoding="utf-8")

        assert cache.get("bad_json") is None

    def test_get_non_dict_cached(self, tmp_path):
        cache = FactCache(cache_dir=tmp_path)
        cache_key = cache._get_cache_key("list_data")
        cache_file = tmp_path / f"{cache_key}.json"
        cache_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

        assert cache.get("list_data") is None

    def test_get_missing_cached_at(self, tmp_path):
        cache = FactCache(cache_dir=tmp_path)
        cache_key = cache._get_cache_key("no_ts")
        cache_file = tmp_path / f"{cache_key}.json"
        cache_file.write_text(json.dumps({"data": {"x": 1}}), encoding="utf-8")

        assert cache.get("no_ts") is None

    def test_get_non_string_cached_at(self, tmp_path):
        cache = FactCache(cache_dir=tmp_path)
        cache_key = cache._get_cache_key("int_ts")
        cache_file = tmp_path / f"{cache_key}.json"
        cache_file.write_text(json.dumps({"cached_at": 12345, "data": {"x": 1}}), encoding="utf-8")

        assert cache.get("int_ts") is None

    def test_get_non_dict_data_field(self, tmp_path):
        cache = FactCache(cache_dir=tmp_path)
        cache_key = cache._get_cache_key("str_data")
        cache_file = tmp_path / f"{cache_key}.json"
        cache_file.write_text(
            json.dumps(
                {
                    "cached_at": datetime.now().isoformat(),
                    "data": "not a dict",
                }
            ),
            encoding="utf-8",
        )

        assert cache.get("str_data") is None


# ============================================================
# WikipediaFactChecker Tests
# ============================================================
class TestWikipediaFactChecker:
    """WikipediaFactChecker unit tests."""

    @pytest.fixture
    def cache(self, tmp_path):
        return FactCache(cache_dir=tmp_path, ttl_days=1)

    @pytest.fixture
    def checker(self, cache):
        return WikipediaFactChecker(cache=cache)

    @patch("src.external_fact_checker.get_project_root")
    def test_init_default_cache(self, mock_root, tmp_path):
        mock_root.return_value = tmp_path
        checker = WikipediaFactChecker()
        assert checker.cache is not None

    # --- _make_request ---

    def test_make_request_success(self, checker):
        mock_response = MagicMock()
        mock_response.json.return_value = {"query": {"pages": {}}}
        mock_response.raise_for_status = MagicMock()

        with patch.object(checker.session, "get", return_value=mock_response):
            result = checker._make_request({"action": "query"})

        assert result == {"query": {"pages": {}}}

    def test_make_request_request_exception(self, checker):
        with patch.object(checker.session, "get", side_effect=requests.RequestException("timeout")):
            result = checker._make_request({"action": "query"})

        assert result is None

    def test_make_request_non_dict_response(self, checker):
        mock_response = MagicMock()
        mock_response.json.return_value = [1, 2, 3]
        mock_response.raise_for_status = MagicMock()

        with patch.object(checker.session, "get", return_value=mock_response):
            result = checker._make_request({"action": "query"})

        assert result is None

    # --- get_page_extract ---

    def test_get_page_extract_cache_hit(self, checker, cache):
        cache.set("wp_extract:TestPerson", {"extract": "Some bio text"})
        result = checker.get_page_extract("TestPerson")
        assert result == "Some bio text"

    def test_get_page_extract_api_success(self, checker):
        api_response = {
            "query": {
                "pages": {
                    "12345": {
                        "pageid": 12345,
                        "title": "TestPerson",
                        "extract": "This is a biography.",
                    }
                }
            }
        }
        with patch.object(checker, "_make_request", return_value=api_response):
            result = checker.get_page_extract("TestPerson")

        assert result == "This is a biography."

    def test_get_page_extract_page_id_minus_one(self, checker):
        api_response = {"query": {"pages": {"-1": {"title": "NotFound", "missing": ""}}}}
        with patch.object(checker, "_make_request", return_value=api_response):
            result = checker.get_page_extract("NonexistentPerson")

        assert result is None

    def test_get_page_extract_api_failure(self, checker):
        with patch.object(checker, "_make_request", return_value=None):
            result = checker.get_page_extract("AnyPerson")

        assert result is None

    def test_get_page_extract_extract_not_string(self, checker):
        """extract field is not a string -> returns None."""
        api_response = {
            "query": {
                "pages": {
                    "123": {
                        "pageid": 123,
                        "extract": 42,  # not a string
                    }
                }
            }
        }
        with patch.object(checker, "_make_request", return_value=api_response):
            result = checker.get_page_extract("NumericExtract")

        assert result is None

    # --- search_person ---

    def test_search_person_cache_hit(self, checker, cache):
        page_info = {"title": "Cached", "pageid": 1, "snippet": "cached"}
        cache.set("wp_search:CachedPerson", page_info)
        result = checker.search_person("CachedPerson")
        assert result == page_info

    def test_search_person_success(self, checker):
        api_response = {
            "query": {
                "search": [
                    {"title": "Person A", "pageid": 100, "snippet": "A bio"},
                    {"title": "Person B", "pageid": 101, "snippet": "B bio"},
                ]
            }
        }
        with patch.object(checker, "_make_request", return_value=api_response):
            result = checker.search_person("Person A")

        assert result["title"] == "Person A"
        assert result["pageid"] == 100

    def test_search_person_no_results(self, checker):
        api_response = {"query": {"search": []}}
        with patch.object(checker, "_make_request", return_value=api_response):
            result = checker.search_person("Nobody")

        assert result is None

    def test_search_person_api_failure(self, checker):
        with patch.object(checker, "_make_request", return_value=None):
            result = checker.search_person("AnyPerson")

        assert result is None

    # --- verify_birth_year ---

    def test_verify_birth_year_match(self, checker):
        extract = "1994年7月5日 - は日本のプロ野球選手。"
        with patch.object(checker, "get_page_extract", return_value=extract):
            result = checker.verify_birth_year("大谷翔平", 1994)

        assert result["verified"] is True
        assert result["status"] == "verified"
        assert result["found_year"] == 1994
        assert result["diff"] == 0

    def test_verify_birth_year_mismatch(self, checker):
        extract = "1993年1月1日生まれ"
        with patch.object(checker, "get_page_extract", return_value=extract):
            result = checker.verify_birth_year("Someone", 1994)

        assert result["verified"] is False
        assert result["status"] == "mismatch"
        assert result["found_year"] == 1993
        assert result["diff"] == 1

    def test_verify_birth_year_not_found(self, checker):
        with patch.object(checker, "get_page_extract", return_value=None):
            result = checker.verify_birth_year("Nobody", 2000)

        assert result["status"] == "not_found"
        assert result["verified"] is False

    def test_verify_birth_year_year_not_found_no_pattern(self, checker):
        extract = "This person exists but no year info."
        with patch.object(checker, "get_page_extract", return_value=extract):
            result = checker.verify_birth_year("NoYear", 2000)

        assert result["status"] == "year_not_found"
        assert result["verified"] is False

    def test_verify_birth_year_pattern_born(self, checker):
        """Pattern: YYYY年生まれ"""
        extract = "1928年生まれの漫画家"
        with patch.object(checker, "get_page_extract", return_value=extract):
            result = checker.verify_birth_year("手塚治虫", 1928)

        assert result["verified"] is True
        assert result["found_year"] == 1928

    def test_verify_birth_year_pattern_birth_date(self, checker):
        """Pattern: 生年月日.*YYYY年"""
        extract = "生年月日は1867年2月9日。"
        with patch.object(checker, "get_page_extract", return_value=extract):
            result = checker.verify_birth_year("夏目漱石", 1867)

        assert result["verified"] is True

    # --- verify_death_year ---

    def test_verify_death_year_match(self, checker):
        extract = "1989年2月9日没。手塚治虫は日本の漫画家。"
        with patch.object(checker, "get_page_extract", return_value=extract):
            result = checker.verify_death_year("手塚治虫", 1989)

        assert result["verified"] is True
        assert result["status"] == "verified"
        assert result["found_year"] == 1989

    def test_verify_death_year_mismatch(self, checker):
        extract = "1990年12月1日死去"
        with patch.object(checker, "get_page_extract", return_value=extract):
            result = checker.verify_death_year("Someone", 1989)

        assert result["verified"] is False
        assert result["status"] == "mismatch"

    def test_verify_death_year_not_found(self, checker):
        with patch.object(checker, "get_page_extract", return_value=None):
            result = checker.verify_death_year("Ghost", 2000)

        assert result["status"] == "not_found"

    def test_verify_death_year_year_not_found(self, checker):
        extract = "This person has no death year info."
        with patch.object(checker, "get_page_extract", return_value=extract):
            result = checker.verify_death_year("Alive", 2000)

        assert result["status"] == "year_not_found"

    def test_verify_death_year_dash_pattern(self, checker):
        """Pattern: - YYYY年"""
        extract = "1867年 - 1916年の文豪。"
        with patch.object(checker, "get_page_extract", return_value=extract):
            result = checker.verify_death_year("夏目漱石", 1916)

        assert result["verified"] is True


# ============================================================
# WikidataVerifier Tests
# ============================================================
class TestWikidataVerifier:
    """WikidataVerifier unit tests."""

    @pytest.fixture
    def cache(self, tmp_path):
        return FactCache(cache_dir=tmp_path, ttl_days=1)

    @pytest.fixture
    def verifier(self, cache):
        return WikidataVerifier(cache=cache)

    @patch("src.external_fact_checker.get_project_root")
    def test_init_default_cache(self, mock_root, tmp_path):
        mock_root.return_value = tmp_path
        v = WikidataVerifier()
        assert v.cache is not None

    # --- _execute_sparql ---

    def test_execute_sparql_success(self, verifier):
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_response.raise_for_status = MagicMock()

        with patch.object(verifier.session, "get", return_value=mock_response):
            result = verifier._execute_sparql("SELECT ?x WHERE {}")

        assert result == {"results": {"bindings": []}}

    def test_execute_sparql_request_exception(self, verifier):
        with patch.object(verifier.session, "get", side_effect=requests.RequestException("err")):
            result = verifier._execute_sparql("SELECT ?x WHERE {}")

        assert result is None

    def test_execute_sparql_non_dict_response(self, verifier):
        mock_response = MagicMock()
        mock_response.json.return_value = "not a dict"
        mock_response.raise_for_status = MagicMock()

        with patch.object(verifier.session, "get", return_value=mock_response):
            result = verifier._execute_sparql("SELECT ?x WHERE {}")

        assert result is None

    # --- search_person_by_name ---

    def test_search_person_by_name_cache_hit(self, verifier, cache):
        cache.set("wd_search:TestPerson:ja", {"wikidata_id": "Q12345"})
        result = verifier.search_person_by_name("TestPerson")
        assert result == "Q12345"

    def test_search_person_by_name_cache_hit_non_string_id(self, verifier, cache):
        cache.set("wd_search:BadCache:ja", {"wikidata_id": 12345})
        result = verifier.search_person_by_name("BadCache")
        assert result is None

    def test_search_person_by_name_success(self, verifier):
        sparql_result = {"results": {"bindings": [{"item": {"value": "http://www.wikidata.org/entity/Q54321"}}]}}
        with patch.object(verifier, "_execute_sparql", return_value=sparql_result):
            result = verifier.search_person_by_name("SomePerson")

        assert result == "Q54321"

    def test_search_person_by_name_no_bindings(self, verifier):
        sparql_result = {"results": {"bindings": []}}
        with patch.object(verifier, "_execute_sparql", return_value=sparql_result):
            result = verifier.search_person_by_name("NobodyKnown")

        assert result is None

    def test_search_person_by_name_api_failure(self, verifier):
        with patch.object(verifier, "_execute_sparql", return_value=None):
            result = verifier.search_person_by_name("AnyPerson")

        assert result is None

    def test_search_person_by_name_binding_item_not_dict(self, verifier):
        sparql_result = {"results": {"bindings": ["not_a_dict"]}}
        with patch.object(verifier, "_execute_sparql", return_value=sparql_result):
            result = verifier.search_person_by_name("WeirdBinding")

        assert result is None

    def test_search_person_by_name_item_value_empty(self, verifier):
        sparql_result = {"results": {"bindings": [{"item": {"value": ""}}]}}
        with patch.object(verifier, "_execute_sparql", return_value=sparql_result):
            result = verifier.search_person_by_name("EmptyValue")

        assert result is None

    # --- get_person_facts ---

    def test_get_person_facts_cache_hit(self, verifier, cache):
        facts = {"wikidata_id": "Q1", "birth_date": "1990-01-01", "death_date": None, "occupations": []}
        cache.set("wd_facts:Q1", facts)
        result = verifier.get_person_facts("Q1")
        assert result == facts

    def test_get_person_facts_success_with_data(self, verifier):
        sparql_result = {
            "results": {
                "bindings": [
                    {
                        "birthDate": {"value": "1994-07-05T00:00:00Z"},
                        "occupationLabel": {"value": "baseball player"},
                    },
                    {
                        "birthDate": {"value": "1994-07-05T00:00:00Z"},
                        "deathDate": {"value": "2050-01-01T00:00:00Z"},
                        "occupationLabel": {"value": "pitcher"},
                    },
                ]
            }
        }
        with patch.object(verifier, "_execute_sparql", return_value=sparql_result):
            result = verifier.get_person_facts("Q123")

        assert result["wikidata_id"] == "Q123"
        assert result["birth_date"] == "1994-07-05"
        assert result["death_date"] == "2050-01-01"
        assert "baseball player" in result["occupations"]
        assert "pitcher" in result["occupations"]

    def test_get_person_facts_no_bindings(self, verifier):
        sparql_result = {"results": {"bindings": []}}
        with patch.object(verifier, "_execute_sparql", return_value=sparql_result):
            result = verifier.get_person_facts("Q999")

        assert result is None

    def test_get_person_facts_api_failure(self, verifier):
        with patch.object(verifier, "_execute_sparql", return_value=None):
            result = verifier.get_person_facts("Q999")

        assert result is None

    def test_get_person_facts_duplicate_occupation_ignored(self, verifier):
        sparql_result = {
            "results": {
                "bindings": [
                    {"occupationLabel": {"value": "writer"}},
                    {"occupationLabel": {"value": "writer"}},  # duplicate
                ]
            }
        }
        with patch.object(verifier, "_execute_sparql", return_value=sparql_result):
            result = verifier.get_person_facts("Q50")

        assert result["occupations"] == ["writer"]

    # --- verify_birth_year ---

    def test_verify_birth_year_verified(self, verifier):
        with patch.object(verifier, "search_person_by_name", return_value="Q100"):
            with patch.object(
                verifier,
                "get_person_facts",
                return_value={
                    "wikidata_id": "Q100",
                    "birth_date": "1994-07-05",
                    "death_date": None,
                    "occupations": [],
                },
            ):
                result = verifier.verify_birth_year("Ohtani", 1994)

        assert result["verified"] is True
        assert result["status"] == "verified"
        assert result["wikidata_id"] == "Q100"

    def test_verify_birth_year_mismatch(self, verifier):
        with patch.object(verifier, "search_person_by_name", return_value="Q200"):
            with patch.object(
                verifier,
                "get_person_facts",
                return_value={
                    "wikidata_id": "Q200",
                    "birth_date": "1993-01-01",
                    "death_date": None,
                    "occupations": [],
                },
            ):
                result = verifier.verify_birth_year("Wrong", 1994)

        assert result["verified"] is False
        assert result["status"] == "mismatch"
        assert result["diff"] == 1

    def test_verify_birth_year_not_found(self, verifier):
        with patch.object(verifier, "search_person_by_name", return_value=None):
            result = verifier.verify_birth_year("Ghost", 2000)

        assert result["status"] == "not_found"

    def test_verify_birth_year_birth_date_not_found(self, verifier):
        with patch.object(verifier, "search_person_by_name", return_value="Q300"):
            with patch.object(
                verifier,
                "get_person_facts",
                return_value={
                    "wikidata_id": "Q300",
                    "birth_date": None,
                    "death_date": None,
                    "occupations": [],
                },
            ):
                result = verifier.verify_birth_year("NoBirth", 2000)

        assert result["status"] == "birth_date_not_found"

    def test_verify_birth_year_parse_error(self, verifier):
        with patch.object(verifier, "search_person_by_name", return_value="Q400"):
            with patch.object(
                verifier,
                "get_person_facts",
                return_value={
                    "wikidata_id": "Q400",
                    "birth_date": "not-a-date",
                    "death_date": None,
                    "occupations": [],
                },
            ):
                result = verifier.verify_birth_year("BadDate", 2000)

        assert result["status"] == "parse_error"

    def test_verify_birth_year_facts_none(self, verifier):
        with patch.object(verifier, "search_person_by_name", return_value="Q500"):
            with patch.object(verifier, "get_person_facts", return_value=None):
                result = verifier.verify_birth_year("NoFacts", 2000)

        assert result["status"] == "birth_date_not_found"


# ============================================================
# ExternalFactChecker Tests
# ============================================================
class TestExternalFactChecker:
    """ExternalFactChecker integration/unit tests."""

    @pytest.fixture
    def checker(self, tmp_path):
        with patch("src.external_fact_checker.get_project_root", return_value=tmp_path):
            c = ExternalFactChecker(delay_seconds=0.0)
        return c

    def test_init_custom_delay(self, tmp_path):
        with patch("src.external_fact_checker.get_project_root", return_value=tmp_path):
            c = ExternalFactChecker(delay_seconds=2.5)
        assert c.delay == 2.5

    # --- _rate_limit ---

    def test_rate_limit_sleeps_when_needed(self, checker):
        checker.delay = 1.0
        checker.last_request_time = time.time()  # just requested

        with patch("src.external_fact_checker.time.sleep") as mock_sleep:
            with patch(
                "src.external_fact_checker.time.time",
                side_effect=[
                    checker.last_request_time + 0.3,  # elapsed check: 0.3s < 1.0s
                    checker.last_request_time + 1.0,  # after sleep: update last_request_time
                ],
            ):
                checker._rate_limit()

            mock_sleep.assert_called_once()
            sleep_arg = mock_sleep.call_args[0][0]
            assert 0.6 < sleep_arg < 0.8  # ~0.7s sleep

    def test_rate_limit_skips_sleep_when_enough_time(self, checker):
        checker.delay = 1.0
        checker.last_request_time = time.time() - 5.0  # 5 seconds ago

        with patch("src.external_fact_checker.time.sleep") as mock_sleep:
            checker._rate_limit()

        mock_sleep.assert_not_called()

    # --- verify_person ---

    def test_verify_person_wp_found_wd_found_with_birth(self, checker):
        with patch.object(checker.wikipedia, "get_page_extract", return_value="A short bio about someone."):
            with patch.object(
                checker.wikipedia,
                "verify_birth_year",
                return_value={"verified": True, "status": "verified", "found_year": 1994},
            ):
                with patch.object(checker.wikidata, "search_person_by_name", return_value="Q100"):
                    with patch.object(
                        checker.wikidata,
                        "get_person_facts",
                        return_value={"birth_date": "1994-07-05"},
                    ):
                        with patch.object(
                            checker.wikidata,
                            "verify_birth_year",
                            return_value={"verified": True, "status": "verified"},
                        ):
                            result = checker.verify_person("TestPerson", expected_birth_year=1994)

        assert result["person_name"] == "TestPerson"
        assert result["sources"]["wikipedia"]["found"] is True
        assert result["sources"]["wikidata"]["found"] is True
        assert result["overall_status"] == "verified"

    def test_verify_person_wp_not_found_wd_not_found(self, checker):
        with patch.object(checker.wikipedia, "get_page_extract", return_value=None):
            with patch.object(checker.wikidata, "search_person_by_name", return_value=None):
                result = checker.verify_person("Nobody")

        assert result["sources"]["wikipedia"]["found"] is False
        assert result["sources"]["wikidata"]["found"] is False
        assert result["overall_status"] == "unknown"

    def test_verify_person_no_birth_year(self, checker):
        with patch.object(checker.wikipedia, "get_page_extract", return_value="Some extract"):
            with patch.object(checker.wikidata, "search_person_by_name", return_value=None):
                result = checker.verify_person("PersonNoBirth")

        assert result["sources"]["wikipedia"]["found"] is True
        assert "birth_verification" not in result["sources"]["wikipedia"]
        assert result["overall_status"] == "partially_verified"

    def test_verify_person_extract_preview_truncated(self, checker):
        long_text = "A" * 500
        with patch.object(checker.wikipedia, "get_page_extract", return_value=long_text):
            with patch.object(checker.wikidata, "search_person_by_name", return_value=None):
                result = checker.verify_person("LongBio")

        preview = result["sources"]["wikipedia"]["extract_preview"]
        assert len(preview) == 200

    # --- _determine_overall_status ---

    def test_determine_overall_unknown(self, checker):
        result = {
            "sources": {
                "wikipedia": {"found": False},
                "wikidata": {"found": False},
            }
        }
        assert checker._determine_overall_status(result) == "unknown"

    def test_determine_overall_verified_by_wp(self, checker):
        result = {
            "sources": {
                "wikipedia": {
                    "found": True,
                    "birth_verification": {"verified": True, "status": "verified"},
                },
                "wikidata": {"found": False},
            }
        }
        assert checker._determine_overall_status(result) == "verified"

    def test_determine_overall_verified_by_wd(self, checker):
        result = {
            "sources": {
                "wikipedia": {"found": False},
                "wikidata": {
                    "found": True,
                    "birth_verification": {"verified": True, "status": "verified"},
                },
            }
        }
        assert checker._determine_overall_status(result) == "verified"

    def test_determine_overall_mismatch_wp(self, checker):
        result = {
            "sources": {
                "wikipedia": {
                    "found": True,
                    "birth_verification": {"verified": False, "status": "mismatch"},
                },
                "wikidata": {"found": False},
            }
        }
        assert checker._determine_overall_status(result) == "mismatch"

    def test_determine_overall_mismatch_wd(self, checker):
        result = {
            "sources": {
                "wikipedia": {"found": True},
                "wikidata": {
                    "found": True,
                    "birth_verification": {"verified": False, "status": "mismatch"},
                },
            }
        }
        assert checker._determine_overall_status(result) == "mismatch"

    def test_determine_overall_partially_verified(self, checker):
        result = {
            "sources": {
                "wikipedia": {"found": True},
                "wikidata": {"found": False},
            }
        }
        assert checker._determine_overall_status(result) == "partially_verified"

    def test_determine_overall_partially_verified_both_found_no_birth(self, checker):
        result = {
            "sources": {
                "wikipedia": {"found": True},
                "wikidata": {"found": True},
            }
        }
        assert checker._determine_overall_status(result) == "partially_verified"

    def test_determine_overall_birth_not_found_status(self, checker):
        """Birth verification exists but status is year_not_found (not mismatch)."""
        result = {
            "sources": {
                "wikipedia": {
                    "found": True,
                    "birth_verification": {"verified": False, "status": "year_not_found"},
                },
                "wikidata": {"found": False},
            }
        }
        assert checker._determine_overall_status(result) == "partially_verified"
