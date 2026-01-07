"""
Anti-Gaming Monitor

ゲーミング（スコア水増し）検出ゲート。
キーワード密度、具体性、抽象語比率、テンプレート臭を監視。
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ..config import RejectionReason


# ==============================================================================
# 設定定数
# ==============================================================================

# キーワード密度閾値（高すぎると詰め込み）
MAX_KEYWORD_DENSITY = 0.15

# 抽象語比率閾値（高すぎると具体性不足）
MAX_ABSTRACT_RATIO = 0.30

# N-gram重複閾値（高すぎるとテンプレート臭）
MAX_NGRAM_REPETITION = 0.20

# 必須具体性（年号または固有名詞の最小数）
MIN_SPECIFICS = 1


# ==============================================================================
# 抽象語・キーワードパターン
# ==============================================================================

# 抽象表現パターン
ABSTRACT_PATTERNS = [
    r"ある日",
    r"ある時",
    r"いつか",
    r"いつの日か",
    r"多くの人",
    r"様々な",
    r"いろいろ",
    r"ある意味",
    r"それなりに",
    r"なんとなく",
    r"とにかく",
    r"基本的に",
    r"一般的に",
    r"ほとんど",
    r"たいてい",
    r"だいたい",
    r"おそらく",
    r"たぶん",
    r"きっと",
    r"もしかしたら",
    r"もしかすると",
]

# 回顧的表現パターン（過去の振り返り）
RETROSPECTIVE_PATTERNS = [
    r"振り返ると",
    r"思い返せば",
    r"後になって",
    r"後から考えると",
    r"今思えば",
    r"当時は",
    r"その頃は",
    r"あの頃",
    r"思い出すと",
    r"懐かしい",
]

# スコアブーストキーワード（詰め込み検出用）
BOOST_KEYWORDS = [
    "衝撃",
    "革命",
    "伝説",
    "前代未聞",
    "空前",
    "歴史的",
    "画期的",
    "驚異",
    "奇跡",
    "感動",
    "涙",
    "絶賛",
    "大ヒット",
    "記録的",
    "最高",
    "最大",
    "最強",
    "最速",
    "世界初",
    "日本初",
    "史上初",
    "金字塔",
    "不朽",
    "永遠",
    "偉大",
    "天才",
    "巨匠",
    "レジェンド",
    "カリスマ",
    "唯一無二",
]

# 固有名詞パターン（具体性チェック用）
PROPER_NOUN_PATTERNS = [
    # 年号
    (r"(1[0-9]{3}|20[0-2][0-9])年", "year"),
    # 作品名（「」『』）
    (r"「([^」]{2,30})」", "work_title"),
    (r"『([^』]{2,30})』", "book_title"),
    # 数値データ
    (r"\d+[万億兆]", "large_number"),
    (r"\d+%", "percentage"),
    (r"第\d+[位回章節話]", "ranking"),
    # カタカナ名詞（3文字以上）
    (r"[ァ-ヶー]{3,}", "katakana_name"),
    # 組織名パターン
    (r"[^\s]{2,}(大学|研究所|病院|会社|銀行|協会|連盟|機構)", "organization"),
    # 地名パターン
    (r"[^\s]{2,}(県|市|区|町|村|国)", "place"),
]


# ==============================================================================
# 結果データクラス
# ==============================================================================


@dataclass
class AntiGamingResult:
    """アンチゲーミングチェック結果"""

    passed: bool
    violations: list[str] = field(default_factory=list)
    keyword_density: float = 0.0
    abstract_ratio: float = 0.0
    ngram_repetition: float = 0.0
    specifics_count: int = 0
    details: dict[str, Any] = field(default_factory=dict)
    rejection_reason: RejectionReason | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "keyword_density": round(self.keyword_density, 3),
            "abstract_ratio": round(self.abstract_ratio, 3),
            "ngram_repetition": round(self.ngram_repetition, 3),
            "specifics_count": self.specifics_count,
            "details": self.details,
        }


# ==============================================================================
# AntiGamingMonitor
# ==============================================================================


class AntiGamingMonitor:
    """
    アンチゲーミングモニター

    エピソードテキストのゲーミング（スコア水増し）を検出。

    チェック項目:
    1. キーワード密度 - ブーストキーワードの詰め込み検出
    2. 固有名詞/年号必須 - 具体性の担保
    3. 抽象語比率 - 曖昧表現の抑制
    4. N-gram重複 - テンプレート臭の検出
    """

    def __init__(
        self,
        max_keyword_density: float = MAX_KEYWORD_DENSITY,
        max_abstract_ratio: float = MAX_ABSTRACT_RATIO,
        max_ngram_repetition: float = MAX_NGRAM_REPETITION,
        min_specifics: int = MIN_SPECIFICS,
    ):
        self.max_keyword_density = max_keyword_density
        self.max_abstract_ratio = max_abstract_ratio
        self.max_ngram_repetition = max_ngram_repetition
        self.min_specifics = min_specifics

    def check(self, text: str, person_name: str | None = None) -> AntiGamingResult:
        """
        アンチゲーミングチェックを実行

        Args:
            text: エピソードテキスト
            person_name: 人物名（オプション、除外用）

        Returns:
            AntiGamingResult: チェック結果
        """
        violations = []
        details = {}

        # テキスト前処理（人物名を除外）
        clean_text = text
        if person_name:
            clean_text = clean_text.replace(person_name, "")

        # 1. キーワード密度チェック
        keyword_density, keyword_details = self._check_keyword_density(clean_text)
        details["keyword_stuffing"] = keyword_details
        if keyword_density > self.max_keyword_density:
            violations.append("keyword_stuffing")

        # 2. 固有名詞/年号必須チェック
        specifics_count, specifics_details = self._check_specifics(clean_text)
        details["specifics"] = specifics_details
        if specifics_count < self.min_specifics:
            violations.append("missing_specifics")

        # 3. 抽象語比率チェック
        abstract_ratio, abstract_details = self._check_abstract_ratio(clean_text)
        details["abstract_words"] = abstract_details
        if abstract_ratio > self.max_abstract_ratio:
            violations.append("too_abstract")

        # 4. N-gram重複チェック
        ngram_repetition, ngram_details = self._check_ngram_repetition(clean_text)
        details["ngram_repetition"] = ngram_details
        if ngram_repetition > self.max_ngram_repetition:
            violations.append("template_smell")

        # 結果を構築
        passed = len(violations) == 0
        rejection_reason = None
        if not passed:
            if "missing_specifics" in violations:
                rejection_reason = RejectionReason.LOW_SPECIFICITY
            elif "keyword_stuffing" in violations:
                rejection_reason = RejectionReason.PROHIBITED_PATTERN
            elif "too_abstract" in violations:
                rejection_reason = RejectionReason.LOW_SPECIFICITY
            elif "template_smell" in violations:
                rejection_reason = RejectionReason.HIGH_SIMILARITY

        return AntiGamingResult(
            passed=passed,
            violations=violations,
            keyword_density=keyword_density,
            abstract_ratio=abstract_ratio,
            ngram_repetition=ngram_repetition,
            specifics_count=specifics_count,
            details=details,
            rejection_reason=rejection_reason,
        )

    def _check_keyword_density(self, text: str) -> tuple[float, dict]:
        """キーワード密度をチェック"""
        # 単語に分割（簡易的）
        words = re.findall(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]+", text)
        if len(words) == 0:
            return 0.0, {"total_words": 0, "boost_keywords": []}

        # ブーストキーワードをカウント
        found_keywords = []
        for keyword in BOOST_KEYWORDS:
            count = text.count(keyword)
            if count > 0:
                found_keywords.extend([keyword] * count)

        density = len(found_keywords) / len(words) if len(words) > 0 else 0.0

        return density, {
            "total_words": len(words),
            "boost_keywords": list(set(found_keywords)),
            "boost_count": len(found_keywords),
        }

    def _check_specifics(self, text: str) -> tuple[int, dict]:
        """固有名詞/年号をチェック"""
        found_specifics = []

        for pattern, spec_type in PROPER_NOUN_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                found_specifics.append({"type": spec_type, "value": match})

        return len(found_specifics), {
            "count": len(found_specifics),
            "items": found_specifics[:10],  # 最大10件
        }

    def _check_abstract_ratio(self, text: str) -> tuple[float, dict]:
        """抽象語比率をチェック"""
        # 単語に分割（簡易的）
        words = re.findall(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]+", text)
        if len(words) == 0:
            return 0.0, {"total_words": 0, "abstract_words": []}

        # 抽象語をカウント
        found_abstract = []
        for pattern in ABSTRACT_PATTERNS:
            matches = re.findall(pattern, text)
            found_abstract.extend(matches)

        # 回顧的表現もカウント
        for pattern in RETROSPECTIVE_PATTERNS:
            matches = re.findall(pattern, text)
            found_abstract.extend(matches)

        ratio = len(found_abstract) / len(words) if len(words) > 0 else 0.0

        return ratio, {
            "total_words": len(words),
            "abstract_words": list(set(found_abstract)),
            "abstract_count": len(found_abstract),
        }

    def _check_ngram_repetition(self, text: str, n: int = 3) -> tuple[float, dict]:
        """N-gram重複をチェック"""
        # 空白・改行を正規化して除去
        clean_text = re.sub(r"\s+", "", text)

        # 文字N-gramを抽出
        ngrams = [clean_text[i : i + n] for i in range(len(clean_text) - n + 1)]
        if len(ngrams) == 0:
            return 0.0, {"total_ngrams": 0, "unique_ngrams": 0, "repeated": []}

        # 重複をカウント
        counter = Counter(ngrams)
        unique_count = len(counter)
        total_count = len(ngrams)

        # 重複率 = 1 - (ユニーク数 / 総数)
        repetition_rate = 1 - (unique_count / total_count) if total_count > 0 else 0.0

        # 複数回出現したN-gramを抽出（句読点のみは除外）
        repeated = [ng for ng, count in counter.items() if count >= 3 and not re.match(r"^[。、．，！？\s]+$", ng)]

        return repetition_rate, {
            "total_ngrams": total_count,
            "unique_ngrams": unique_count,
            "repeated_samples": repeated[:5],  # 最大5件
        }


# ==============================================================================
# 便利関数
# ==============================================================================


def quick_anti_gaming_check(text: str, person_name: str | None = None) -> bool:
    """
    クイックアンチゲーミングチェック

    Args:
        text: エピソードテキスト
        person_name: 人物名（オプション）

    Returns:
        bool: パスしたらTrue
    """
    monitor = AntiGamingMonitor()
    result = monitor.check(text, person_name)
    return result.passed


def get_gaming_violations(text: str, person_name: str | None = None) -> list[str]:
    """
    ゲーミング違反リストを取得

    Args:
        text: エピソードテキスト
        person_name: 人物名（オプション）

    Returns:
        list[str]: 違反リスト
    """
    monitor = AntiGamingMonitor()
    result = monitor.check(text, person_name)
    return result.violations
