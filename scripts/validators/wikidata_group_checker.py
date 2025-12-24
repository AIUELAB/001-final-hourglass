#!/usr/bin/env python3
"""
Wikidata グループ名チェッカー (Layer 3)

定期バッチ処理でDBの人物名をWikidataと照合し、
グループ/企業名が個人名として登録されていないかを検証する。

使用例:
    # 疑わしい名前をWikidataでチェック
    python scripts/validators/wikidata_group_checker.py --check "チェッカーズ"

    # DBの警告レベル名前を一括チェック
    python scripts/validators/wikidata_group_checker.py --scan

    # レポート生成
    python scripts/validators/wikidata_group_checker.py --report
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import pandas as pd
import requests

# Wikidata SPARQL エンドポイント
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# エンティティタイプ (instance of - P31)
ENTITY_TYPES = {
    "Q5": "human",  # 人間
    "Q215380": "musical_group",  # 音楽グループ
    "Q105756498": "comedy_duo",  # お笑いコンビ
    "Q4830453": "business",  # 企業
    "Q43229": "organization",  # 組織
    "Q327333": "government_agency",  # 政府機関
    "Q2088357": "musical_ensemble",  # 音楽アンサンブル
    "Q24716636": "musical_duo",  # 音楽デュオ
}

# グループ系エンティティ
GROUP_TYPES = {"musical_group", "comedy_duo", "musical_ensemble", "musical_duo"}
ORGANIZATION_TYPES = {"business", "organization", "government_agency"}


class WikidataGroupChecker:
    """Wikidata連携グループ名チェッカー"""

    def __init__(self, cache_path: str = ".cache/wikidata_cache.json"):
        self.cache_path = Path(cache_path)
        self.cache = self._load_cache()
        self.request_count = 0
        self.rate_limit_delay = 1.0  # 秒

    def _load_cache(self) -> dict:
        """キャッシュを読み込み"""
        if self.cache_path.exists():
            with open(self.cache_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        """キャッシュを保存"""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _query_wikidata(self, name: str) -> Optional[dict]:
        """Wikidataで名前を検索"""
        # レート制限
        if self.request_count > 0:
            time.sleep(self.rate_limit_delay)
        self.request_count += 1

        # SPARQL クエリ
        query = f"""
        SELECT ?item ?itemLabel ?instanceOf ?instanceOfLabel WHERE {{
          ?item rdfs:label "{name}"@ja .
          OPTIONAL {{ ?item wdt:P31 ?instanceOf . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en". }}
        }}
        LIMIT 5
        """

        try:
            response = requests.get(
                WIKIDATA_ENDPOINT,
                params={"query": query, "format": "json"},
                headers={"User-Agent": "EpisodeDBValidator/1.0"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"  ⚠️ Wikidata API エラー: {e}")
            return None

    def check_name(self, name: str) -> dict:
        """
        名前をWikidataでチェック

        Returns:
            {
                "name": str,
                "found": bool,
                "entity_types": list[str],
                "is_group": bool,
                "is_organization": bool,
                "is_human": bool,
                "wikidata_id": str or None,
                "cached": bool,
            }
        """
        # キャッシュ確認
        if name in self.cache:
            result = self.cache[name].copy()
            result["cached"] = True
            return result

        result = {
            "name": name,
            "found": False,
            "entity_types": [],
            "is_group": False,
            "is_organization": False,
            "is_human": False,
            "wikidata_id": None,
            "cached": False,
        }

        data = self._query_wikidata(name)
        if not data or "results" not in data:
            self.cache[name] = result
            return result

        bindings = data["results"]["bindings"]
        if not bindings:
            self.cache[name] = result
            return result

        result["found"] = True

        # 最初の結果を使用
        first = bindings[0]
        if "item" in first:
            result["wikidata_id"] = first["item"]["value"].split("/")[-1]

        # エンティティタイプを収集
        entity_types = set()
        for binding in bindings:
            if "instanceOf" in binding:
                qid = binding["instanceOf"]["value"].split("/")[-1]
                if qid in ENTITY_TYPES:
                    entity_types.add(ENTITY_TYPES[qid])

        result["entity_types"] = list(entity_types)
        result["is_group"] = bool(entity_types & GROUP_TYPES)
        result["is_organization"] = bool(entity_types & ORGANIZATION_TYPES)
        result["is_human"] = "human" in entity_types

        # キャッシュに保存
        self.cache[name] = {k: v for k, v in result.items() if k != "cached"}
        self._save_cache()

        return result

    def scan_suspicious_names(self, csv_path: str = "preserved/data/MASTER_EPISODES_CURRENT.csv") -> list:
        """
        DBの疑わしい名前をスキャン
        """
        import sys

        sys.path.insert(0, "scripts/validators")
        from group_name_validator import GroupNameValidator

        validator = GroupNameValidator(csv_path)
        validation_result = validator.validate_all()

        suspicious = []

        # 警告レベルの名前を抽出
        for warning in validation_result.get("warnings", []):
            name = warning["name"]
            wikidata_result = self.check_name(name)

            if wikidata_result["is_group"] or wikidata_result["is_organization"]:
                suspicious.append(
                    {
                        "name": name,
                        "validator_reason": warning["suspicious_reason"],
                        "wikidata_result": wikidata_result,
                    }
                )

        return suspicious

    def generate_report(self, output_path: str = "reports/wikidata_group_check.md"):
        """レポートを生成"""
        suspicious = self.scan_suspicious_names()

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            f.write("# Wikidata グループ名チェックレポート\n\n")
            f.write(f"生成日時: {datetime.now().isoformat()}\n\n")

            if not suspicious:
                f.write("✅ グループ/組織名は検出されませんでした。\n")
            else:
                f.write(f"## 検出された問題 ({len(suspicious)}件)\n\n")
                f.write("| 名前 | Wikidataタイプ | バリデーター理由 |\n")
                f.write("|------|----------------|------------------|\n")

                for item in suspicious:
                    types = ", ".join(item["wikidata_result"]["entity_types"])
                    f.write(f"| {item['name']} | {types} | {item['validator_reason']} |\n")

        print(f"✅ レポート生成: {output}")
        return output


def main():
    parser = argparse.ArgumentParser(description="Wikidata グループ名チェッカー")
    parser.add_argument("--check", type=str, help="特定の名前をチェック")
    parser.add_argument("--scan", action="store_true", help="DBの疑わしい名前をスキャン")
    parser.add_argument("--report", action="store_true", help="レポートを生成")
    args = parser.parse_args()

    checker = WikidataGroupChecker()

    if args.check:
        result = checker.check_name(args.check)
        print(f"\n名前: {result['name']}")
        print(f"Wikidata検索: {'見つかりました' if result['found'] else '見つかりません'}")
        if result["found"]:
            print(f"Wikidata ID: {result['wikidata_id']}")
            print(f"エンティティタイプ: {', '.join(result['entity_types']) or 'なし'}")
            print(f"グループ判定: {'✅ グループ' if result['is_group'] else '❌ グループではない'}")
            print(f"組織判定: {'✅ 組織' if result['is_organization'] else '❌ 組織ではない'}")
            print(f"人間判定: {'✅ 人間' if result['is_human'] else '❌ 人間ではない'}")
        return 0

    if args.scan:
        print("DBの疑わしい名前をスキャン中...")
        suspicious = checker.scan_suspicious_names()
        print(f"\n検出されたグループ/組織名: {len(suspicious)}件")
        for item in suspicious[:10]:
            print(f"  - {item['name']}: {item['wikidata_result']['entity_types']}")
        return 0

    if args.report:
        checker.generate_report()
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    exit(main())
