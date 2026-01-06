"""
Fact Check Gate

ファクトチェックと創作検知を実行。
"""

import re
from dataclasses import dataclass, field
from typing import Any

from ..config import FABRICATION_SIGNALS, REQUIRED_EVIDENCE, RejectionReason


@dataclass
class FactCheckResult:
    """ファクトチェック結果"""

    passed: bool
    score: float  # 0.0-1.0
    reason: str = ""
    evidence_found: list[str] = field(default_factory=list)
    fabrication_signals: list[str] = field(default_factory=list)
    rejection_reason: RejectionReason = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "reason": self.reason,
            "evidence_found": self.evidence_found,
            "fabrication_signals": self.fabrication_signals,
        }


class FactChecker:
    """
    ファクトチェッカー

    エピソードテキストの事実性を検証。
    創作・捏造を検知。
    """

    # 創作検知パターン
    FABRICATION_PATTERNS = [
        (r"と言われている", "hearsay_phrase"),
        (r"かもしれない", "uncertainty_phrase"),
        (r"らしい$", "hearsay_suffix"),
        (r"だろう$", "speculation_suffix"),
        (r"ではないか", "rhetorical_question"),
        (r"と思われる", "assumption_phrase"),
        (r"伝説", "legend_reference"),
        (r"神話", "myth_reference"),
    ]

    # 根拠抽出パターン
    EVIDENCE_PATTERNS = [
        (r"(1[89]\d{2}|20[0-2]\d)年", "year"),
        (r"「([^」]{2,30})」", "quoted_name"),
        (r"『([^』]{2,30})』", "book_title"),
        (r"\d+[万億]", "large_number"),
        (r"\d+%", "percentage"),
        (r"第\d+[位回]", "ranking"),
        (r"[\u30A0-\u30FF]{3,}", "katakana_name"),
    ]

    # 抽象表現パターン
    ABSTRACT_PATTERNS = [
        (r"ある日", "vague_time"),
        (r"いつか", "vague_future"),
        (r"ある時", "vague_moment"),
        (r"多くの人", "vague_people"),
        (r"様々な", "vague_variety"),
        (r"いろいろ", "vague_variety"),
    ]

    def __init__(self, min_evidence: int = 2, max_fabrication: int = 1):
        self.min_evidence = min_evidence
        self.max_fabrication = max_fabrication

    def check(self, text: str, person_name: str = None) -> FactCheckResult:
        """
        ファクトチェックを実行

        Args:
            text: エピソードテキスト
            person_name: 人物名（オプション）

        Returns:
            FactCheckResult: チェック結果
        """
        evidence_found = []
        fabrication_signals = []

        # 1. 根拠を抽出
        for pattern, evidence_type in self.EVIDENCE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                evidence_found.append(f"{evidence_type}: {match}")

        # 2. 創作検知
        for pattern, signal_type in self.FABRICATION_PATTERNS:
            if re.search(pattern, text):
                fabrication_signals.append(signal_type)

        # 3. 抽象表現検知
        abstract_count = 0
        for pattern, signal_type in self.ABSTRACT_PATTERNS:
            if re.search(pattern, text):
                abstract_count += 1

        if abstract_count >= 2:
            fabrication_signals.append("too_many_abstracts")

        # 4. スコア計算
        evidence_score = min(len(evidence_found) / self.min_evidence, 1.0)
        fabrication_penalty = len(fabrication_signals) * 0.2
        score = max(evidence_score - fabrication_penalty, 0.0)

        # 5. 判定
        passed = True
        reason = ""
        rejection_reason = None

        if len(evidence_found) < self.min_evidence:
            passed = False
            reason = f"Not enough evidence: {len(evidence_found)} < {self.min_evidence}"
            rejection_reason = RejectionReason.NO_EVIDENCE

        if len(fabrication_signals) > self.max_fabrication:
            passed = False
            reason = f"Too many fabrication signals: {len(fabrication_signals)}"
            rejection_reason = RejectionReason.FABRICATION_DETECTED

        return FactCheckResult(
            passed=passed,
            score=score,
            reason=reason,
            evidence_found=evidence_found[:10],  # 最大10件
            fabrication_signals=fabrication_signals,
            rejection_reason=rejection_reason,
        )

    def check_required_evidence(self, text: str) -> tuple[bool, list[str]]:
        """
        必須根拠の存在確認

        Args:
            text: エピソードテキスト

        Returns:
            (has_required, missing): 必須根拠があるか、欠けている項目
        """
        missing = []

        # 年号チェック
        if not re.search(r"(1[89]\d{2}|20[0-2]\d)年", text):
            missing.append("年号 (YYYY年)")

        # 固有名詞チェック
        has_proper_noun = (
            re.search(r"「[^」]+」", text)  # 「」
            or re.search(r"『[^』]+』", text)  # 『』
            or re.search(r"[\u30A0-\u30FF]{3,}", text)  # カタカナ
        )
        if not has_proper_noun:
            missing.append("固有名詞 (作品名/イベント名/組織名)")

        return len(missing) == 0, missing


class FabricationDetector:
    """
    創作検知器

    LLMが勝手に作り出した架空の出来事を検知。
    """

    # 危険な表現パターン
    WARNING_PATTERNS = [
        (r"実は.*だった", "hidden_fact", 0.3),
        (r"秘密.*明かす", "secret_reveal", 0.3),
        (r"誰も知らない", "unknown_fact", 0.4),
        (r"あまり知られていない", "little_known", 0.2),
        (r"密かに", "secretly", 0.3),
        (r"ひそかに", "secretly", 0.3),
    ]

    def detect(self, text: str) -> tuple[float, list[str]]:
        """
        創作の可能性を検知

        Args:
            text: エピソードテキスト

        Returns:
            (fabrication_score, warnings): 創作スコアと警告リスト
        """
        fabrication_score = 0.0
        warnings = []

        for pattern, warning_type, weight in self.WARNING_PATTERNS:
            if re.search(pattern, text):
                fabrication_score += weight
                warnings.append(warning_type)

        # 具体性チェック
        if not re.search(r"(1[89]\d{2}|20[0-2]\d)年", text):
            fabrication_score += 0.2
            warnings.append("no_year")

        # 固有名詞チェック
        katakana_count = len(re.findall(r"[\u30A0-\u30FF]{3,}", text))
        if katakana_count < 2:
            fabrication_score += 0.1
            warnings.append("few_proper_nouns")

        return min(fabrication_score, 1.0), warnings


def quick_fact_check(text: str) -> bool:
    """
    簡易ファクトチェック

    Args:
        text: エピソードテキスト

    Returns:
        bool: パスしたか
    """
    checker = FactChecker()
    result = checker.check(text)
    return result.passed
