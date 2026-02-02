#!/usr/bin/env python3
"""
WikipediaClient - Wikipedia/Wikidataを使用した実在人物検証クライアント

実在人物の存在確認と基本情報（生年・没年・職業・国籍）の取得を行う。
キャッシュ機能により、同一人物への重複リクエストを削減。

## 設計方針
- キャッシュ優先: 7日間有効なキャッシュで外部API呼び出しを削減
- 正規表現パース: Wikipedia検索結果から生年/没年を抽出
- 信頼度スコア: データの完全性に基づくconfidence値を算出

## 使用例
    client = WikipediaClient()

    # 人物検証（キャッシュ確認のみ）
    info = client.verify_person("織田信長")

    # Wikipedia検索結果のパース
    info = client.parse_wikipedia_result(
        "織田信長",
        "織田信長（1534年－1582年）は、日本の戦国武将..."
    )

Author: EPUP Validation Team
Date: 2026-02-01
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# データクラス定義
# =============================================================================


@dataclass
class PersonInfo:
    """人物情報データクラス"""

    name: str  # 人物名
    exists: bool  # 存在確認フラグ
    birth_year: Optional[int]  # 生年
    death_year: Optional[int]  # 没年
    occupation: Optional[str]  # 職業
    nationality: Optional[str]  # 国籍
    source_url: Optional[str]  # 情報源URL
    confidence: float  # 信頼度 (0.0-1.0)
    cache_timestamp: Optional[str]  # キャッシュ保存日時

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> PersonInfo:
        """辞書からPersonInfoを生成"""
        return cls(
            name=data.get("name", ""),
            exists=data.get("exists", False),
            birth_year=data.get("birth_year"),
            death_year=data.get("death_year"),
            occupation=data.get("occupation"),
            nationality=data.get("nationality"),
            source_url=data.get("source_url"),
            confidence=data.get("confidence", 0.0),
            cache_timestamp=data.get("cache_timestamp"),
        )

    @classmethod
    def not_found(cls, name: str) -> PersonInfo:
        """存在しない人物のPersonInfoを生成"""
        return cls(
            name=name,
            exists=False,
            birth_year=None,
            death_year=None,
            occupation=None,
            nationality=None,
            source_url=None,
            confidence=0.0,
            cache_timestamp=datetime.now().isoformat(),
        )


# =============================================================================
# WikipediaClient クラス
# =============================================================================


class WikipediaClient:
    """
    Wikipedia/Wikidata検証クライアント

    実在人物の検証とキャッシュ管理を行う。
    """

    # デフォルトキャッシュファイルパス
    CACHE_FILE = Path("preserved/data/verification_cache.json")

    # キャッシュ有効期限（日数）
    CACHE_EXPIRY_DAYS = 7

    # 生年抽出パターン
    BIRTH_PATTERNS = [
        r"(\d{4})年生まれ",  # 「1534年生まれ」
        r"(\d{4})年\d{1,2}月\d{1,2}日\s*[-–]",  # 「1534年6月23日 - 」
        r"(\d{4})年\s*[-–]\s*",  # 「1534年 - 」
        r"\((\d{4})[-–]",  # 「(1534-」
        r"生年[：:]\s*(\d{4})",  # 「生年: 1534」
        r"(\d{4})年\d{1,2}月\d{1,2}日生",  # 「1534年6月23日生」
        r"生誕[：:]?\s*(\d{4})年",  # 「生誕: 1534年」
        r"(\d{4})[-–](\d{4})",  # 「1534-1582」（最初の4桁）
    ]

    # 没年抽出パターン
    DEATH_PATTERNS = [
        r"[-–]\s*(\d{4})年\)?",  # 「- 1582年）」
        r"(\d{4})年没",  # 「1582年没」
        r"(\d{4})年死去",  # 「1582年死去」
        r"没年[：:]\s*(\d{4})",  # 「没年: 1582」
        r"(\d{4})年\d{1,2}月\d{1,2}日没",  # 「1582年6月21日没」
        r"死没[：:]?\s*(\d{4})年",  # 「死没: 1582年」
        r"(\d{4})[-–](\d{4})",  # 「1534-1582」（2番目の4桁）
    ]

    # 職業キーワードパターン
    OCCUPATION_PATTERNS = [
        r"(武将|政治家|科学者|芸術家|作家|俳優|音楽家|実業家|発明家|哲学者)",
        r"(物理学者|化学者|数学者|生物学者|医師|建築家|画家|彫刻家)",
        r"(歌手|作曲家|指揮者|演奏家|監督|プロデューサー|アナウンサー)",
        r"(スポーツ選手|野球選手|サッカー選手|テニス選手|ゴルファー)",
        r"(僧侶|宗教家|軍人|外交官|弁護士|教育者|ジャーナリスト)",
    ]

    # 国籍キーワードパターン
    NATIONALITY_PATTERNS = [
        r"(日本|アメリカ|イギリス|フランス|ドイツ|中国|韓国|イタリア|ロシア|スペイン)",
        r"(オーストラリア|カナダ|ブラジル|インド|オランダ|スイス|オーストリア)",
        r"の(武将|政治家|科学者)",  # 「日本の武将」から国籍を抽出するためのパターン
    ]

    def __init__(self, cache_file: Optional[Path] = None):
        """
        クライアント初期化

        Args:
            cache_file: キャッシュファイルパス（指定しない場合はデフォルト使用）
        """
        self.cache_file = cache_file or self.CACHE_FILE
        self.cache: dict = {}
        self._load_cache()
        logger.info(f"WikipediaClient initialized with cache: {self.cache_file}")

    def verify_person(self, person_name: str) -> PersonInfo:
        """
        人物の実在性を検証（キャッシュ確認）

        キャッシュに有効なエントリがあればそれを返す。
        なければ not_found を返す（外部API呼び出しは行わない）。

        Args:
            person_name: 検証対象の人物名

        Returns:
            PersonInfo: 人物情報
        """
        # キャッシュ確認
        cache_key = self._normalize_name(person_name)

        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry):
                logger.debug(f"Cache hit for: {person_name}")
                return PersonInfo.from_dict(cache_entry)
            else:
                logger.debug(f"Cache expired for: {person_name}")

        # キャッシュになければ未検証として返す
        logger.debug(f"No valid cache for: {person_name}")
        return PersonInfo.not_found(person_name)

    def parse_wikipedia_result(
        self,
        person_name: str,
        search_result: str,
    ) -> PersonInfo:
        """
        Wikipedia検索結果をパースしてPersonInfoを生成

        検索結果テキストから生年・没年・職業・国籍を抽出し、
        キャッシュに保存する。

        Args:
            person_name: 人物名
            search_result: Wikipedia検索結果テキスト

        Returns:
            PersonInfo: パース結果
        """
        if not search_result or not search_result.strip():
            return PersonInfo.not_found(person_name)

        # 存在フラグ
        exists = True

        # 生年抽出
        birth_year = self._extract_birth_year(search_result)

        # 没年抽出
        death_year = self._extract_death_year(search_result)

        # 職業抽出
        occupation = self._extract_occupation(search_result)

        # 国籍抽出
        nationality = self._extract_nationality(search_result)

        # Wikipedia URL生成（推測）
        source_url = self._generate_wikipedia_url(person_name)

        # 信頼度計算
        confidence = self._calculate_confidence(
            exists=exists,
            birth_year=birth_year,
            death_year=death_year,
            occupation=occupation,
            nationality=nationality,
        )

        # タイムスタンプ
        cache_timestamp = datetime.now().isoformat()

        # PersonInfo生成
        person_info = PersonInfo(
            name=person_name,
            exists=exists,
            birth_year=birth_year,
            death_year=death_year,
            occupation=occupation,
            nationality=nationality,
            source_url=source_url,
            confidence=confidence,
            cache_timestamp=cache_timestamp,
        )

        # キャッシュ保存
        cache_key = self._normalize_name(person_name)
        self.cache[cache_key] = person_info.to_dict()
        self._save_cache()

        logger.info(
            f"Parsed Wikipedia result for {person_name}: "
            f"birth={birth_year}, death={death_year}, confidence={confidence:.2f}"
        )

        return person_info

    def _extract_birth_year(self, text: str) -> Optional[int]:
        """
        テキストから生年を抽出

        Args:
            text: 検索結果テキスト

        Returns:
            生年（見つからなければNone）
        """
        for pattern in self.BIRTH_PATTERNS:
            match = re.search(pattern, text)
            if match:
                # グループ1を優先（複数グループの場合）
                year_str = match.group(1)
                try:
                    year = int(year_str)
                    # 妥当性チェック（紀元前～現在）
                    if -3000 <= year <= datetime.now().year:
                        return year
                except ValueError:
                    continue
        return None

    def _extract_death_year(self, text: str) -> Optional[int]:
        """
        テキストから没年を抽出

        Args:
            text: 検索結果テキスト

        Returns:
            没年（見つからなければNone）
        """
        for pattern in self.DEATH_PATTERNS:
            match = re.search(pattern, text)
            if match:
                # 「1534-1582」形式の場合、グループ2を使用
                if match.lastindex and match.lastindex >= 2:
                    year_str = match.group(2)
                else:
                    year_str = match.group(1)
                try:
                    year = int(year_str)
                    # 妥当性チェック
                    if -3000 <= year <= datetime.now().year:
                        return year
                except ValueError:
                    continue
        return None

    def _extract_occupation(self, text: str) -> Optional[str]:
        """
        テキストから職業を抽出

        Args:
            text: 検索結果テキスト

        Returns:
            職業（見つからなければNone）
        """
        for pattern in self.OCCUPATION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_nationality(self, text: str) -> Optional[str]:
        """
        テキストから国籍を抽出

        Args:
            text: 検索結果テキスト

        Returns:
            国籍（見つからなければNone）
        """
        # 「日本の武将」のようなパターンを検索
        nationality_with_occupation = re.search(r"(日本|アメリカ|イギリス|フランス|ドイツ|中国|韓国)の", text)
        if nationality_with_occupation:
            return nationality_with_occupation.group(1)

        # 単独の国籍キーワード
        for pattern in self.NATIONALITY_PATTERNS:
            if "の(" not in pattern:  # 複合パターンをスキップ
                match = re.search(pattern, text)
                if match:
                    return match.group(1)
        return None

    def _calculate_confidence(
        self,
        exists: bool,
        birth_year: Optional[int],
        death_year: Optional[int],
        occupation: Optional[str],
        nationality: Optional[str],
    ) -> float:
        """
        信頼度スコアを計算

        各フィールドの有無に基づいて0.0-1.0のスコアを算出。

        Args:
            exists: 存在フラグ
            birth_year: 生年
            death_year: 没年
            occupation: 職業
            nationality: 国籍

        Returns:
            信頼度スコア (0.0-1.0)
        """
        if not exists:
            return 0.0

        # 基本スコア（存在確認）
        score = 0.2

        # 各フィールドの加算
        if birth_year is not None:
            score += 0.25
        if death_year is not None:
            score += 0.15
        if occupation is not None:
            score += 0.2
        if nationality is not None:
            score += 0.2

        return min(score, 1.0)

    def _generate_wikipedia_url(self, person_name: str) -> str:
        """
        Wikipedia URLを生成

        Args:
            person_name: 人物名

        Returns:
            Wikipedia URL
        """
        # URLエンコード
        from urllib.parse import quote

        encoded_name = quote(person_name)
        return f"https://ja.wikipedia.org/wiki/{encoded_name}"

    def _normalize_name(self, name: str) -> str:
        """
        キャッシュキー用に名前を正規化

        Args:
            name: 人物名

        Returns:
            正規化された名前
        """
        # 空白を削除、小文字化
        return name.strip().lower().replace(" ", "").replace("　", "")

    def _is_cache_valid(self, cache_entry: dict) -> bool:
        """
        キャッシュが有効期限内か確認

        Args:
            cache_entry: キャッシュエントリ

        Returns:
            True if valid, False otherwise
        """
        timestamp_str = cache_entry.get("cache_timestamp")
        if not timestamp_str:
            return False

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            expiry = timestamp + timedelta(days=self.CACHE_EXPIRY_DAYS)
            return datetime.now() < expiry
        except (ValueError, TypeError):
            return False

    def _load_cache(self) -> None:
        """キャッシュファイルを読み込み"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} entries from cache")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load cache: {e}")
                self.cache = {}
        else:
            self.cache = {}
            logger.info("No cache file found, starting with empty cache")

    def _save_cache(self) -> None:
        """キャッシュをファイルに保存"""
        try:
            # 親ディレクトリが存在しなければ作成
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved {len(self.cache)} entries to cache")
        except OSError as e:
            logger.error(f"Failed to save cache: {e}")

    def clear_cache(self, person_name: Optional[str] = None) -> None:
        """
        キャッシュをクリア

        Args:
            person_name: 特定の人物のみクリアする場合は名前を指定
                         Noneの場合は全キャッシュをクリア
        """
        if person_name:
            cache_key = self._normalize_name(person_name)
            if cache_key in self.cache:
                del self.cache[cache_key]
                logger.info(f"Cleared cache for: {person_name}")
            else:
                logger.warning(f"No cache entry found for: {person_name}")
        else:
            count = len(self.cache)
            self.cache = {}
            logger.info(f"Cleared all {count} cache entries")

        self._save_cache()

    def get_cache_stats(self) -> dict:
        """
        キャッシュ統計情報を取得

        Returns:
            統計情報の辞書
        """
        total = len(self.cache)
        valid = sum(1 for entry in self.cache.values() if self._is_cache_valid(entry))
        expired = total - valid

        # 存在確認済み人物数
        exists_count = sum(1 for entry in self.cache.values() if entry.get("exists", False))

        # 平均信頼度
        confidences = [entry.get("confidence", 0.0) for entry in self.cache.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": expired,
            "exists_count": exists_count,
            "not_found_count": total - exists_count,
            "average_confidence": round(avg_confidence, 3),
            "cache_file": str(self.cache_file),
        }


# =============================================================================
# ユーティリティ関数
# =============================================================================


def verify_person(person_name: str) -> PersonInfo:
    """
    人物検証のシンプルAPI

    Args:
        person_name: 検証対象の人物名

    Returns:
        PersonInfo
    """
    client = WikipediaClient()
    return client.verify_person(person_name)


def parse_wikipedia_result(person_name: str, search_result: str) -> PersonInfo:
    """
    Wikipedia検索結果パースのシンプルAPI

    Args:
        person_name: 人物名
        search_result: 検索結果テキスト

    Returns:
        PersonInfo
    """
    client = WikipediaClient()
    return client.parse_wikipedia_result(person_name, search_result)


# =============================================================================
# CLI (テスト用)
# =============================================================================


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("WikipediaClient - テスト実行")
    print("=" * 60)

    client = WikipediaClient()

    # テストケース1: Wikipedia検索結果のパース
    print("\n[Test 1: Wikipedia検索結果のパース]")
    test_text = """
    織田信長（おだ のぶなが、1534年6月23日 - 1582年6月21日）は、
    日本の戦国時代から安土桃山時代にかけての武将、戦国大名。
    三英傑の一人。尾張国の古渡城主・織田信秀の嫡男。
    """
    result = client.parse_wikipedia_result("織田信長", test_text)
    print(f"  Name: {result.name}")
    print(f"  Exists: {result.exists}")
    print(f"  Birth Year: {result.birth_year}")
    print(f"  Death Year: {result.death_year}")
    print(f"  Occupation: {result.occupation}")
    print(f"  Nationality: {result.nationality}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Source URL: {result.source_url}")

    # テストケース2: キャッシュからの取得
    print("\n[Test 2: キャッシュからの取得]")
    cached_result = client.verify_person("織田信長")
    print(f"  Name: {cached_result.name}")
    print(f"  Exists: {cached_result.exists}")
    print(f"  From Cache: {cached_result.cache_timestamp is not None}")

    # テストケース3: 存在しない人物
    print("\n[Test 3: キャッシュにない人物]")
    not_found = client.verify_person("存在しない人物名XYZ")
    print(f"  Name: {not_found.name}")
    print(f"  Exists: {not_found.exists}")
    print(f"  Confidence: {not_found.confidence}")

    # テストケース4: 別形式のWikipediaテキスト
    print("\n[Test 4: 別形式のWikipediaテキスト]")
    test_text2 = """
    アルベルト・アインシュタイン（Albert Einstein、1879年 - 1955年）は、
    ドイツ生まれの理論物理学者である。
    """
    result2 = client.parse_wikipedia_result("アルベルト・アインシュタイン", test_text2)
    print(f"  Name: {result2.name}")
    print(f"  Birth Year: {result2.birth_year}")
    print(f"  Death Year: {result2.death_year}")
    print(f"  Nationality: {result2.nationality}")
    print(f"  Confidence: {result2.confidence:.2f}")

    # テストケース5: キャッシュ統計
    print("\n[Test 5: キャッシュ統計]")
    stats = client.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # テストケース6: 特定人物のキャッシュクリア
    print("\n[Test 6: 特定人物のキャッシュクリア]")
    client.clear_cache("アルベルト・アインシュタイン")
    verify_after_clear = client.verify_person("アルベルト・アインシュタイン")
    print(f"  After clear - Exists: {verify_after_clear.exists}")

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)
