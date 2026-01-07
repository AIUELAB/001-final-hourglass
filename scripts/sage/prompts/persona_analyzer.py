"""
Persona Analyzer - Phase 7D

人物特性分析（Wikipedia/Wikidata連携）。
人物の特性を分析してプロンプト最適化に活用。
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# キャッシュディレクトリ
CACHE_DIR = PROJECT_ROOT / "src" / "cache" / "persona"


@dataclass
class PersonaProfile:
    """人物プロファイル"""

    person_id: str
    person_name: str
    wikidata_id: Optional[str] = None

    # 基本情報
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    nationality: str = ""
    occupation: list[str] = field(default_factory=list)

    # 特性
    primary_domain: str = ""  # 主要分野
    notable_traits: list[str] = field(default_factory=list)  # 特徴
    notable_works: list[str] = field(default_factory=list)  # 代表作・業績
    story_potential: dict[str, float] = field(default_factory=dict)  # ストーリー可能性

    # Wikipediaサマリー
    wikipedia_summary: str = ""

    # メタデータ
    analyzed_at: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "person_id": self.person_id,
            "person_name": self.person_name,
            "wikidata_id": self.wikidata_id,
            "birth_year": self.birth_year,
            "death_year": self.death_year,
            "nationality": self.nationality,
            "occupation": self.occupation,
            "primary_domain": self.primary_domain,
            "notable_traits": self.notable_traits,
            "notable_works": self.notable_works,
            "story_potential": self.story_potential,
            "wikipedia_summary": self.wikipedia_summary[:500] if self.wikipedia_summary else "",
            "analyzed_at": self.analyzed_at,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersonaProfile":
        """辞書から生成"""
        return cls(
            person_id=data.get("person_id", ""),
            person_name=data.get("person_name", ""),
            wikidata_id=data.get("wikidata_id"),
            birth_year=data.get("birth_year"),
            death_year=data.get("death_year"),
            nationality=data.get("nationality", ""),
            occupation=data.get("occupation", []),
            primary_domain=data.get("primary_domain", ""),
            notable_traits=data.get("notable_traits", []),
            notable_works=data.get("notable_works", []),
            story_potential=data.get("story_potential", {}),
            wikipedia_summary=data.get("wikipedia_summary", ""),
            analyzed_at=data.get("analyzed_at", ""),
            confidence=data.get("confidence", 0.0),
        )


class PersonaAnalyzer:
    """
    人物特性分析クラス

    Wikipedia/Wikidataから人物情報を取得し、
    エピソード生成に活用できる特性を抽出。
    """

    # ドメインマッピング
    DOMAIN_KEYWORDS = {
        "科学・技術": [
            "科学者",
            "物理学者",
            "化学者",
            "数学者",
            "発明家",
            "エンジニア",
            "技術者",
            "researcher",
            "scientist",
        ],
        "スポーツ": ["選手", "アスリート", "プロ野球", "サッカー", "テニス", "オリンピック", "athlete", "player"],
        "芸術・文化": ["画家", "音楽家", "作曲家", "作家", "詩人", "彫刻家", "デザイナー", "artist", "musician"],
        "政治・経済": ["政治家", "首相", "大統領", "大臣", "経済学者", "politician", "economist"],
        "エンターテインメント": ["俳優", "女優", "歌手", "アイドル", "お笑い", "タレント", "actor", "singer"],
        "ビジネス・起業": ["実業家", "起業家", "経営者", "CEO", "創業者", "entrepreneur", "businessman"],
        "医療・福祉": ["医師", "医学者", "看護師", "福祉", "doctor", "physician"],
        "宗教・思想": ["僧侶", "神父", "哲学者", "思想家", "宗教家", "philosopher"],
    }

    # ストーリー可能性キーワード
    STORY_KEYWORDS = {
        "逆境克服": ["困難", "挫折", "復活", "克服", "乗り越え", "苦労"],
        "革新": ["革命", "発明", "発見", "画期的", "イノベーション", "先駆"],
        "人間関係": ["師弟", "ライバル", "友情", "協力", "対立", "家族"],
        "転機": ["転機", "きっかけ", "運命", "決断", "出会い", "変化"],
        "栄光": ["優勝", "受賞", "記録", "達成", "成功", "世界一"],
    }

    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        if cache_enabled:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def analyze(
        self,
        person_id: str,
        person_name: str,
        wikidata_id: Optional[str] = None,
    ) -> PersonaProfile:
        """
        人物を分析

        Args:
            person_id: 人物ID
            person_name: 人物名
            wikidata_id: WikidataID（省略時は検索）

        Returns:
            PersonaProfile: 分析結果
        """
        # キャッシュ確認
        if self.cache_enabled:
            cached = self._load_cache(person_id)
            if cached:
                return cached

        from datetime import datetime

        profile = PersonaProfile(
            person_id=person_id,
            person_name=person_name,
            wikidata_id=wikidata_id,
            analyzed_at=datetime.now().isoformat(),
        )

        # Wikipedia情報取得
        wiki_info = self._fetch_wikipedia_info(person_name)
        if wiki_info:
            profile.wikipedia_summary = wiki_info.get("summary", "")
            profile.confidence = 0.7

        # Wikidata情報取得
        if wikidata_id:
            wikidata_info = self._fetch_wikidata_info(wikidata_id)
            if wikidata_info:
                profile.birth_year = wikidata_info.get("birth_year")
                profile.death_year = wikidata_info.get("death_year")
                profile.nationality = wikidata_info.get("nationality", "")
                profile.occupation = wikidata_info.get("occupation", [])
                profile.confidence = 0.9

        # ドメイン推定
        profile.primary_domain = self._infer_domain(profile)

        # 特性抽出
        profile.notable_traits = self._extract_traits(profile)

        # ストーリー可能性分析
        profile.story_potential = self._analyze_story_potential(profile)

        # キャッシュ保存
        if self.cache_enabled:
            self._save_cache(profile)

        return profile

    def _fetch_wikipedia_info(self, person_name: str) -> Optional[dict[str, Any]]:
        """Wikipedia API から情報取得"""
        try:
            # 日本語Wikipedia
            url = "https://ja.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(person_name)
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return {
                    "summary": data.get("extract", ""),
                    "title": data.get("title", ""),
                    "description": data.get("description", ""),
                }

            # 英語Wikipediaフォールバック
            url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(person_name)
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return {
                    "summary": data.get("extract", ""),
                    "title": data.get("title", ""),
                    "description": data.get("description", ""),
                }

        except Exception as e:
            logger.warning(f"Wikipedia fetch failed for {person_name}: {e}")

        return None

    def _fetch_wikidata_info(self, wikidata_id: str) -> Optional[dict[str, Any]]:
        """Wikidata API から情報取得"""
        try:
            url = f"https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                return None

            data = response.json()
            entity = data.get("entities", {}).get(wikidata_id, {})
            claims = entity.get("claims", {})

            result: dict[str, Any] = {}

            # 生年 (P569)
            if "P569" in claims:
                try:
                    time_value = claims["P569"][0]["mainsnak"]["datavalue"]["value"]["time"]
                    result["birth_year"] = int(time_value[1:5])
                except (KeyError, ValueError):
                    pass

            # 没年 (P570)
            if "P570" in claims:
                try:
                    time_value = claims["P570"][0]["mainsnak"]["datavalue"]["value"]["time"]
                    result["death_year"] = int(time_value[1:5])
                except (KeyError, ValueError):
                    pass

            # 国籍 (P27)
            if "P27" in claims:
                try:
                    country_id = claims["P27"][0]["mainsnak"]["datavalue"]["value"]["id"]
                    # 国名は簡易的にIDから推定（本格実装では別途取得）
                    result["nationality"] = country_id
                except (KeyError, ValueError):
                    pass

            # 職業 (P106)
            occupations = []
            if "P106" in claims:
                for claim in claims["P106"][:5]:  # 最大5件
                    try:
                        occ_id = claim["mainsnak"]["datavalue"]["value"]["id"]
                        occupations.append(occ_id)
                    except (KeyError, ValueError):
                        pass
            result["occupation"] = occupations

            return result

        except Exception as e:
            logger.warning(f"Wikidata fetch failed for {wikidata_id}: {e}")

        return None

    def _infer_domain(self, profile: PersonaProfile) -> str:
        """ドメインを推定"""
        text = profile.wikipedia_summary.lower() + " ".join(profile.occupation).lower()

        scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)

        return "一般"

    def _extract_traits(self, profile: PersonaProfile) -> list[str]:
        """特性を抽出"""
        traits = []
        summary = profile.wikipedia_summary

        # パターンマッチング
        patterns = [
            (r"(\d+)年.*?に.*?生まれ", "出生"),
            (r"(\d+)歳.*?で", "年齢milestone"),
            (r"世界.*?初", "世界初"),
            (r"日本.*?初", "日本初"),
            (r"最年少", "最年少記録"),
            (r"最高齢", "最高齢記録"),
            (r"ノーベル.*?賞", "ノーベル賞受賞"),
            (r"オリンピック", "オリンピック関連"),
        ]

        for pattern, trait in patterns:
            if re.search(pattern, summary):
                traits.append(trait)

        return traits[:10]  # 最大10件

    def _analyze_story_potential(self, profile: PersonaProfile) -> dict[str, float]:
        """ストーリー可能性を分析"""
        text = profile.wikipedia_summary
        potential = {}

        for story_type, keywords in self.STORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text) / len(keywords)
            potential[story_type] = min(score * 2, 1.0)  # 0-1にスケール

        return potential

    def _load_cache(self, person_id: str) -> Optional[PersonaProfile]:
        """キャッシュから読み込み"""
        cache_file = CACHE_DIR / f"{person_id}.json"
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                return PersonaProfile.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    def _save_cache(self, profile: PersonaProfile) -> None:
        """キャッシュに保存"""
        cache_file = CACHE_DIR / f"{profile.person_id}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)

    def get_optimized_prompt(self, profile: PersonaProfile, age: int) -> str:
        """
        人物特性に基づく最適化プロンプトを生成

        Args:
            profile: 人物プロファイル
            age: 対象年齢

        Returns:
            str: 最適化プロンプト
        """
        lines = [f"【人物特性情報: {profile.person_name}】\n"]

        # 基本情報
        if profile.primary_domain:
            lines.append(f"■ 主要分野: {profile.primary_domain}")

        if profile.nationality:
            lines.append(f"■ 国籍: {profile.nationality}")

        if profile.occupation:
            lines.append(f"■ 職業: {', '.join(profile.occupation[:3])}")

        # 年代情報
        if profile.birth_year:
            target_year = profile.birth_year + age
            lines.append(f"\n■ 対象年: {target_year}年頃（{age}歳時点）")

            if profile.death_year and target_year > profile.death_year:
                lines.append(f"  ※ 没年（{profile.death_year}年）以降のため注意")

        # 特性
        if profile.notable_traits:
            lines.append(f"\n■ 特徴: {', '.join(profile.notable_traits)}")

        # ストーリー可能性
        high_potential = [k for k, v in profile.story_potential.items() if v > 0.5]
        if high_potential:
            lines.append(f"\n■ ストーリー可能性が高いテーマ: {', '.join(high_potential)}")

        # Wikipediaサマリー（抜粋）
        if profile.wikipedia_summary:
            summary = (
                profile.wikipedia_summary[:200] + "..."
                if len(profile.wikipedia_summary) > 200
                else profile.wikipedia_summary
            )
            lines.append(f"\n■ 概要:\n{summary}")

        return "\n".join(lines)


# ==============================================================================
# テスト
# ==============================================================================


if __name__ == "__main__":
    print("=== PersonaAnalyzer Test ===")

    analyzer = PersonaAnalyzer(cache_enabled=True)

    # テスト分析
    test_persons = [
        ("TEST001", "アルベルト・アインシュタイン", "Q937"),
        ("TEST002", "イチロー", "Q194045"),
    ]

    for person_id, person_name, wikidata_id in test_persons:
        print(f"\n--- Analyzing: {person_name} ---")
        profile = analyzer.analyze(person_id, person_name, wikidata_id)

        print(f"ドメイン: {profile.primary_domain}")
        print(f"特性: {profile.notable_traits}")
        print(f"信頼度: {profile.confidence}")
        print(f"ストーリー可能性: {profile.story_potential}")

        # 最適化プロンプト
        print("\n--- Optimized Prompt (age=30) ---")
        prompt = analyzer.get_optimized_prompt(profile, 30)
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)

    print("\n=== Test Complete ===")
