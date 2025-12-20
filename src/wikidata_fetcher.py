#!/usr/bin/env python3
"""
Wikidata API を使用した人物→Wikipediaページ解決

Wikipedia Search APIよりも高精度で人物を特定できる。
Wikidataエンティティを経由してjawikiリンクを取得する。

Usage:
    from src.wikidata_fetcher import WikidataFetcher
    fetcher = WikidataFetcher()
    page_title = fetcher.resolve_person("大谷翔平")
    # -> "大谷翔平"
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, cast

import requests

# プロジェクトルート
project_root = Path(__file__).parent.parent


class WikidataFetcher:
    """Wikidata APIを使用した人物→Wikipediaページ解決"""

    def __init__(self, delay: float = 0.5, overrides_path: Optional[Path] = None):
        """
        Args:
            delay: API呼び出し間隔（秒）
            overrides_path: オーバーライドJSONファイルパス
        """
        self.delay = delay
        self.headers = {"User-Agent": "FinalHourglassBot/2.0 (https://github.com/AIUELAB/001-final-hourglass)"}
        self.stats = {
            "wikidata_calls": 0,
            "wikidata_hits": 0,
            "override_hits": 0,
            "fallback_calls": 0,
            "errors": 0,
        }

        # オーバーライド読み込み
        self.overrides_path = overrides_path or project_root / "config" / "wikipedia_overrides.json"
        self.overrides = self._load_overrides()

    def _load_overrides(self) -> Dict[str, str]:
        """オーバーライドJSONを読み込む"""
        if not self.overrides_path.exists():
            return {}

        try:
            with open(self.overrides_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # __comment__ などのメタキーを除外
                return {k: v for k, v in data.items() if not k.startswith("_")}
        except Exception as e:
            print(f"  ⚠️ オーバーライド読み込みエラー: {e}")
            return {}

    def search_entity(self, person_name: str) -> Optional[str]:
        """
        Wikidataエンティティを検索

        Args:
            person_name: 人物名

        Returns:
            Wikidata entity ID (e.g., "Q4391858") or None
        """
        url = "https://www.wikidata.org/w/api.php"
        params: Dict[str, Any] = {
            "action": "wbsearchentities",
            "search": person_name,
            "language": "ja",
            "format": "json",
            "limit": 1,
        }

        try:
            time.sleep(self.delay)
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = data.get("search", [])
            if results:
                self.stats["wikidata_calls"] += 1
                return cast(str, results[0]["id"])

            return None

        except Exception as e:
            self.stats["errors"] += 1
            print(f"  ⚠️ Wikidata検索エラー [{person_name}]: {e}")
            return None

    def get_jawiki_title(self, entity_id: str) -> Optional[str]:
        """
        WikidataエンティティからWikipedia日本語版タイトルを取得

        Args:
            entity_id: Wikidata entity ID (e.g., "Q4391858")

        Returns:
            Wikipedia日本語版ページタイトル or None
        """
        url = "https://www.wikidata.org/w/api.php"
        params: Dict[str, Any] = {
            "action": "wbgetentities",
            "ids": entity_id,
            "props": "sitelinks",
            "sitefilter": "jawiki",
            "format": "json",
        }

        try:
            time.sleep(self.delay)
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            entities = data.get("entities", {})
            entity = entities.get(entity_id, {})
            sitelinks = entity.get("sitelinks", {})
            jawiki = sitelinks.get("jawiki", {})

            title = jawiki.get("title")
            if title:
                self.stats["wikidata_hits"] += 1
                return cast(str, title)

            return None

        except Exception as e:
            self.stats["errors"] += 1
            print(f"  ⚠️ Wikidata sitelinks取得エラー [{entity_id}]: {e}")
            return None

    def resolve_person(self, person_name: str) -> Optional[str]:
        """
        人物名→Wikipediaページタイトルを解決

        解決順序:
        1. オーバーライド確認
        2. Wikidata検索 → jawikiリンク取得
        3. フォールバック: None（呼び出し元でWikipedia Searchを使用）

        Args:
            person_name: 人物名

        Returns:
            Wikipediaページタイトル or None
        """
        # 1. オーバーライド確認
        if person_name in self.overrides:
            self.stats["override_hits"] += 1
            return self.overrides[person_name]

        # 2. Wikidata検索
        entity_id = self.search_entity(person_name)
        if not entity_id:
            return None

        # 3. jawikiリンク取得
        title = self.get_jawiki_title(entity_id)
        return title

    def get_stats(self) -> Dict:
        """統計情報を取得"""
        return self.stats.copy()


# テスト用
if __name__ == "__main__":
    fetcher = WikidataFetcher()

    test_names = [
        "大谷翔平",
        "スティーブ・ジョブズ",
        "マイケル・ジョーダン",
        "小泉八雲",
        "IU",
        "Eve",
    ]

    print("=== Wikidata Fetcher Test ===\n")

    for name in test_names:
        result = fetcher.resolve_person(name)
        print(f"{name} → {result}")

    print(f"\n統計: {fetcher.get_stats()}")
