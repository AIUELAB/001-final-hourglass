"""
Wiki Fact Checker - Wikidata API連携ファクトチェック

Phase 6: 外部API連携による事実検証強化。
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import requests

from ..config import RejectionReason


# ==============================================================================
# データクラス
# ==============================================================================


@dataclass
class PersonInfo:
    """Wikidataから取得した人物情報"""

    wikidata_id: str
    name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    occupations: list[str] = field(default_factory=list)
    notable_works: list[str] = field(default_factory=list)
    awards: list[str] = field(default_factory=list)
    key_events: dict[int, list[str]] = field(default_factory=dict)  # year -> events


@dataclass
class WikiFactCheckResult:
    """Wikiファクトチェック結果"""

    passed: bool
    score: float  # 0.0-1.0
    verified_facts: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    anachronisms: list[str] = field(default_factory=list)
    timeline_issues: list[str] = field(default_factory=list)
    rejection_reason: Optional[RejectionReason] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "verified_facts": self.verified_facts,
            "unverified_claims": self.unverified_claims,
            "anachronisms": self.anachronisms,
            "timeline_issues": self.timeline_issues,
        }


# ==============================================================================
# WikidataClient
# ==============================================================================


class WikidataClient:
    """
    Wikidata APIクライアント

    人物情報・事象の取得・検証を行う。
    """

    WIKIDATA_API = "https://www.wikidata.org/w/api.php"
    WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

    # プロパティID
    PROPS = {
        "birth_date": "P569",
        "death_date": "P570",
        "occupation": "P106",
        "notable_work": "P800",
        "award": "P166",
        "education": "P69",
        "employer": "P108",
    }

    def __init__(self, timeout: int = 10, cache_enabled: bool = True):
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self._cache: dict[str, PersonInfo] = {}

    def get_person_info(self, wikidata_id: str) -> Optional[PersonInfo]:
        """
        人物情報を取得

        Args:
            wikidata_id: Wikidata ID (例: Q937 = アルベルト・アインシュタイン)

        Returns:
            PersonInfo or None
        """
        # キャッシュチェック
        if self.cache_enabled and wikidata_id in self._cache:
            return self._cache[wikidata_id]

        try:
            # Wikidata API呼び出し
            params = {
                "action": "wbgetentities",
                "ids": wikidata_id,
                "props": "labels|claims",
                "languages": "ja|en",
                "format": "json",
            }

            response = requests.get(self.WIKIDATA_API, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if "entities" not in data or wikidata_id not in data["entities"]:
                return None

            entity = data["entities"][wikidata_id]

            # 名前取得
            labels = entity.get("labels", {})
            name = labels.get("ja", {}).get("value") or labels.get("en", {}).get("value", "")

            # クレーム解析
            claims = entity.get("claims", {})

            # 生年・没年
            birth_year = self._extract_year(claims, self.PROPS["birth_date"])
            death_year = self._extract_year(claims, self.PROPS["death_date"])

            # 職業
            occupations = self._extract_labels(claims, self.PROPS["occupation"])

            # 主な作品
            notable_works = self._extract_labels(claims, self.PROPS["notable_work"])

            # 受賞
            awards = self._extract_labels(claims, self.PROPS["award"])

            info = PersonInfo(
                wikidata_id=wikidata_id,
                name=name,
                birth_year=birth_year,
                death_year=death_year,
                occupations=occupations,
                notable_works=notable_works,
                awards=awards,
            )

            # キャッシュ保存
            if self.cache_enabled:
                self._cache[wikidata_id] = info

            return info

        except (requests.RequestException, KeyError, ValueError):
            return None

    def search_person(self, name: str) -> Optional[str]:
        """
        人物名からWikidata IDを検索

        Args:
            name: 人物名

        Returns:
            Wikidata ID or None
        """
        try:
            params = {
                "action": "wbsearchentities",
                "search": name,
                "language": "ja",
                "type": "item",
                "limit": 5,
                "format": "json",
            }

            response = requests.get(self.WIKIDATA_API, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            results = data.get("search", [])
            if results:
                # 最初のマッチを返す
                return results[0]["id"]

            return None

        except requests.RequestException:
            return None

    def verify_event(self, wikidata_id: str, year: int, event_keywords: list[str]) -> bool:
        """
        特定年の事象を検証

        Args:
            wikidata_id: Wikidata ID
            year: 年
            event_keywords: 事象を示すキーワード

        Returns:
            事象が確認できたか
        """
        # SPARQL クエリで検証（簡易版）
        person_info = self.get_person_info(wikidata_id)
        if not person_info:
            return False

        # 年齢範囲チェック
        if person_info.birth_year and year < person_info.birth_year:
            return False
        if person_info.death_year and year > person_info.death_year:
            return False

        # キーワードと主要作品・受賞の照合
        all_items = person_info.notable_works + person_info.awards
        for keyword in event_keywords:
            for item in all_items:
                if keyword.lower() in item.lower():
                    return True

        return False

    def _extract_year(self, claims: dict, prop_id: str) -> Optional[int]:
        """クレームから年を抽出"""
        if prop_id not in claims:
            return None

        try:
            claim = claims[prop_id][0]
            time_value = claim["mainsnak"]["datavalue"]["value"]["time"]
            # +1879-03-14T00:00:00Z 形式
            year_match = re.match(r"[+-]?(\d{4})", time_value)
            if year_match:
                return int(year_match.group(1))
        except (KeyError, IndexError, ValueError):
            pass

        return None

    def _extract_labels(self, claims: dict, prop_id: str, limit: int = 10) -> list[str]:
        """クレームからラベルリストを抽出"""
        if prop_id not in claims:
            return []

        labels = []
        for claim in claims[prop_id][:limit]:
            try:
                entity_id = claim["mainsnak"]["datavalue"]["value"]["id"]
                # 簡易版: IDのみ保存（詳細はAPIで取得可能）
                labels.append(entity_id)
            except (KeyError, TypeError):
                pass

        return labels


# ==============================================================================
# CrossReferenceValidator
# ==============================================================================


class CrossReferenceValidator:
    """
    クロスリファレンス検証

    同一人物の複数エピソードの時系列整合性を検証。
    """

    def __init__(self, wikidata_client: Optional[WikidataClient] = None):
        self.client = wikidata_client or WikidataClient()

    def validate_timeline(
        self,
        person_id: str,
        episodes: list[dict],
        wikidata_id: Optional[str] = None,
    ) -> tuple[bool, list[str]]:
        """
        時系列整合性を検証

        Args:
            person_id: 人物ID
            episodes: エピソードリスト [{"age": int, "text": str}, ...]
            wikidata_id: Wikidata ID（オプション）

        Returns:
            (passed, issues): 検証結果と問題リスト
        """
        issues = []

        # 人物情報取得
        person_info = None
        if wikidata_id:
            person_info = self.client.get_person_info(wikidata_id)

        # 年齢順にソート
        sorted_episodes = sorted(episodes, key=lambda x: x.get("age", 0))

        # 時系列チェック
        for i, ep in enumerate(sorted_episodes):
            age = ep.get("age", 0)
            text = ep.get("text", "")

            # 年号抽出
            years = re.findall(r"(1[89]\d{2}|20[0-2]\d)年", text)
            if not years:
                continue

            for year_str in years:
                year = int(year_str)

                # 生年との整合性
                if person_info and person_info.birth_year:
                    expected_year = person_info.birth_year + age
                    # ±2年の許容誤差
                    if abs(year - expected_year) > 2:
                        issues.append(f"年齢{age}歳で{year}年の記述は不整合 " f"(期待値: {expected_year}年)")

                # 死亡年との整合性
                if person_info and person_info.death_year:
                    if year > person_info.death_year:
                        issues.append(f"没年{person_info.death_year}年以降の記述: {year}年")

        return len(issues) == 0, issues

    def detect_anachronisms(
        self,
        episode_text: str,
        birth_year: Optional[int],
        death_year: Optional[int],
        age: int,
    ) -> list[str]:
        """
        時代錯誤を検出

        Args:
            episode_text: エピソードテキスト
            birth_year: 生年
            death_year: 没年
            age: 年齢

        Returns:
            anachronisms: 検出された時代錯誤リスト
        """
        anachronisms = []

        # 年号抽出
        years = re.findall(r"(1[89]\d{2}|20[0-2]\d)年", episode_text)

        for year_str in years:
            year = int(year_str)

            # 生前チェック
            if birth_year and year < birth_year:
                anachronisms.append(f"{year}年は生年({birth_year}年)より前")

            # 没後チェック
            if death_year and year > death_year:
                anachronisms.append(f"{year}年は没年({death_year}年)より後")

            # 年齢との整合性
            if birth_year:
                calculated_age = year - birth_year
                # ±3年の許容誤差
                if abs(calculated_age - age) > 3:
                    anachronisms.append(f"{year}年時点での年齢は{calculated_age}歳 " f"(エピソード年齢: {age}歳)")

        return anachronisms


# ==============================================================================
# CategoryFactRules
# ==============================================================================


class CategoryFactRules:
    """
    カテゴリ別ファクトチェックルール

    カテゴリごとに異なる検証ルールを適用。
    """

    # カテゴリ別必須パターン
    CATEGORY_REQUIREMENTS = {
        "科学": {
            "patterns": [
                (r"\d{4}年", "年号"),
                (r"論文|研究|発見|発明|理論", "学術用語"),
            ],
            "min_patterns": 2,
        },
        "スポーツ": {
            "patterns": [
                (r"\d+[位回]|優勝|記録", "競技結果"),
                (r"\d{4}年", "年号"),
            ],
            "min_patterns": 2,
        },
        "政治": {
            "patterns": [
                (r"選挙|政策|法案|演説|就任", "政治用語"),
                (r"\d{4}年", "年号"),
            ],
            "min_patterns": 2,
        },
        "芸術": {
            "patterns": [
                (r"「[^」]+」|『[^』]+』", "作品名"),
            ],
            "min_patterns": 1,
        },
        "歴史": {
            "patterns": [
                (r"\d{3,4}年", "年号"),
                (r"戦争|条約|改革|革命", "歴史用語"),
            ],
            "min_patterns": 2,
        },
    }

    def check(self, text: str, category: str) -> tuple[bool, list[str]]:
        """
        カテゴリ別ルールでチェック

        Args:
            text: エピソードテキスト
            category: カテゴリ

        Returns:
            (passed, missing): 検証結果と不足項目
        """
        rules = self.CATEGORY_REQUIREMENTS.get(category, {})
        if not rules:
            # 未定義カテゴリはデフォルトルール
            return True, []

        patterns = rules.get("patterns", [])
        min_patterns = rules.get("min_patterns", 1)

        found = 0
        missing = []

        for pattern, name in patterns:
            if re.search(pattern, text):
                found += 1
            else:
                missing.append(name)

        passed = found >= min_patterns
        return passed, missing


# ==============================================================================
# WikiFactChecker（統合クラス）
# ==============================================================================


class WikiFactChecker:
    """
    Wikiファクトチェッカー（統合）

    WikidataClient + CrossReferenceValidator + CategoryFactRules を統合。
    """

    def __init__(
        self,
        wikidata_client: Optional[WikidataClient] = None,
        category_rules: Optional[CategoryFactRules] = None,
        cross_validator: Optional[CrossReferenceValidator] = None,
    ):
        self.client = wikidata_client or WikidataClient()
        self.category_rules = category_rules or CategoryFactRules()
        self.cross_validator = cross_validator or CrossReferenceValidator(self.client)

    def check(
        self,
        text: str,
        person_name: str,
        age: int,
        category: str = "",
        wikidata_id: Optional[str] = None,
        birth_year: Optional[int] = None,
        death_year: Optional[int] = None,
    ) -> WikiFactCheckResult:
        """
        統合ファクトチェック

        Args:
            text: エピソードテキスト
            person_name: 人物名
            age: 年齢
            category: カテゴリ
            wikidata_id: Wikidata ID
            birth_year: 生年
            death_year: 没年

        Returns:
            WikiFactCheckResult: チェック結果
        """
        verified_facts = []
        unverified_claims = []
        anachronisms = []
        timeline_issues = []

        score = 1.0

        # 1. Wikidata情報取得
        person_info = None
        if wikidata_id:
            person_info = self.client.get_person_info(wikidata_id)
        elif person_name:
            # 名前から検索
            found_id = self.client.search_person(person_name)
            if found_id:
                person_info = self.client.get_person_info(found_id)

        # 2. 生年・没年の補完
        if person_info:
            if not birth_year and person_info.birth_year:
                birth_year = person_info.birth_year
            if not death_year and person_info.death_year:
                death_year = person_info.death_year

        # 3. 時代錯誤検出
        if birth_year or death_year:
            anachronisms = self.cross_validator.detect_anachronisms(text, birth_year, death_year, age)
            if anachronisms:
                score -= 0.3 * len(anachronisms)

        # 4. カテゴリ別ルールチェック
        if category:
            cat_passed, cat_missing = self.category_rules.check(text, category)
            if not cat_passed:
                unverified_claims.extend([f"カテゴリ必須項目不足: {m}" for m in cat_missing])
                score -= 0.1 * len(cat_missing)

        # 5. 年号検証（Wikidataと照合）
        years = re.findall(r"(1[89]\d{2}|20[0-2]\d)年", text)
        for year_str in years:
            year = int(year_str)
            # 基本的な年代整合性
            if birth_year and year >= birth_year:
                verified_facts.append(f"{year}年は生年以降")
            if death_year and year <= death_year:
                verified_facts.append(f"{year}年は没年以前")

        # 6. スコア正規化
        score = max(0.0, min(1.0, score))

        # 7. 判定
        passed = score >= 0.7 and len(anachronisms) == 0
        rejection_reason = None

        if not passed:
            if anachronisms:
                rejection_reason = RejectionReason.FABRICATION_DETECTED
            elif len(unverified_claims) > 2:
                rejection_reason = RejectionReason.NO_EVIDENCE

        return WikiFactCheckResult(
            passed=passed,
            score=score,
            verified_facts=verified_facts,
            unverified_claims=unverified_claims,
            anachronisms=anachronisms,
            timeline_issues=timeline_issues,
            rejection_reason=rejection_reason,
        )


# ==============================================================================
# 便利関数
# ==============================================================================


def verify_episode_facts(
    text: str,
    person_name: str,
    age: int,
    category: str = "",
    wikidata_id: Optional[str] = None,
) -> WikiFactCheckResult:
    """
    エピソードのファクトチェック（便利関数）

    Args:
        text: エピソードテキスト
        person_name: 人物名
        age: 年齢
        category: カテゴリ
        wikidata_id: Wikidata ID

    Returns:
        WikiFactCheckResult
    """
    checker = WikiFactChecker()
    return checker.check(
        text=text,
        person_name=person_name,
        age=age,
        category=category,
        wikidata_id=wikidata_id,
    )


if __name__ == "__main__":
    print("=== Wiki Fact Checker Test ===")

    # テスト1: WikidataClient
    client = WikidataClient()
    print("\n1. Wikidata検索テスト")
    qid = client.search_person("アルベルト・アインシュタイン")
    print(f"  アインシュタイン ID: {qid}")

    if qid:
        info = client.get_person_info(qid)
        if info:
            print(f"  名前: {info.name}")
            print(f"  生年: {info.birth_year}")
            print(f"  没年: {info.death_year}")

    # テスト2: 時代錯誤検出
    print("\n2. 時代錯誤検出テスト")
    validator = CrossReferenceValidator()
    anachronisms = validator.detect_anachronisms(
        episode_text="1920年に相対性理論を発表した",
        birth_year=1879,
        death_year=1955,
        age=41,
    )
    print(f"  時代錯誤: {anachronisms}")

    # テスト3: カテゴリルール
    print("\n3. カテゴリルールテスト")
    rules = CategoryFactRules()
    passed, missing = rules.check("1905年に特殊相対性理論を発表した", "科学")
    print(f"  科学カテゴリ: passed={passed}, missing={missing}")

    # テスト4: 統合チェック
    print("\n4. 統合ファクトチェック")
    result = verify_episode_facts(
        text="1905年、26歳のアインシュタインは「特殊相対性理論」を発表した。",
        person_name="アルベルト・アインシュタイン",
        age=26,
        category="科学",
    )
    print(f"  passed: {result.passed}")
    print(f"  score: {result.score}")
    print(f"  verified: {result.verified_facts}")
    print(f"  anachronisms: {result.anachronisms}")
