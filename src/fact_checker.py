#!/usr/bin/env python3
"""
Fact Checker System - 事実確認システム
PDCAガーディアンと連携してエピソードの事実正確性を検証
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# ログ設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [FactChecker] - %(message)s")
logger = logging.getLogger(__name__)


class FactCheckResult(Enum):
    """事実確認結果"""

    VERIFIED = "verified"  # 検証済み
    UNVERIFIED = "unverified"  # 未検証
    INCORRECT = "incorrect"  # 誤り
    SUSPICIOUS = "suspicious"  # 疑わしい
    PARTIAL = "partial"  # 部分的に正しい


@dataclass
class FactCheckViolation:
    """事実確認違反情報"""

    violation_type: str
    message: str
    severity: str  # critical, high, medium, low
    evidence: Optional[str] = None
    suggestion: Optional[str] = None
    confidence: float = 0.0  # 0.0-1.0の確信度


@dataclass
class FactCheckReport:
    """事実確認レポート"""

    person_id: str
    person_name: str
    timestamp: str
    result: FactCheckResult
    violations: List[FactCheckViolation] = field(default_factory=list)
    verified_facts: List[str] = field(default_factory=list)
    unverified_claims: List[str] = field(default_factory=list)
    total_score: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class FactChecker:
    """事実確認システム"""

    # 既知の事実データベース（実際にはWikipedia等から取得）
    KNOWN_FACTS = {
        "安倍晋三": {
            "birth_year": 1954,
            "death_year": 2022,
            "positions": ["内閣総理大臣", "自民党総裁"],
            "major_events": [
                {"year": 2006, "event": "第90代内閣総理大臣就任"},
                {"year": 2012, "event": "第96代内閣総理大臣就任"},
                {"year": 2022, "event": "銃撃事件により死去"},
            ],
        },
        "イチロー": {
            "birth_year": 1973,
            "real_name": "鈴木一朗",
            "achievements": [
                {"year": 2001, "event": "MLB新人王・MVP同時受賞"},
                {"year": 2004, "event": "シーズン262安打記録"},
                {"year": 2016, "event": "MLB通算3000本安打達成"},
                {"year": 2019, "event": "現役引退"},
            ],
        },
        "HIKAKIN": {
            "birth_year": 1989,
            "real_name": "開發光",
            "career_start": 2006,
            "platforms": ["YouTube", "TikTok"],
            "milestones": [
                {"year": 2013, "event": "YouTube登録者100万人突破"},
                {"year": 2018, "event": "YouTube登録者600万人突破"},
            ],
        },
    }

    # ハルシネーションパターン
    HALLUCINATION_PATTERNS = [
        (r"世界で初めて", "世界初の主張は要検証"),
        (r"日本で唯一", "唯一性の主張は要検証"),
        (r"史上最[年若高]", "最上級表現は要検証"),
        (r"\d{5,}[万億]", "巨大な数値は要検証"),
        (r"全[国世界]で\d+位", "ランキング情報は要検証"),
        (r"ノーベル賞", "受賞歴は要検証"),
        (r"ギネス[記録認定]", "ギネス記録は要検証"),
    ]

    # 時代錯誤パターン
    ANACHRONISM_PATTERNS = [
        (r"江戸時代.*インターネット", "時代錯誤：江戸時代にインターネットは存在しない"),
        (r"明治.*テレビ", "時代錯誤：明治時代にテレビは存在しない"),
        (r"昭和初期.*スマートフォン", "時代錯誤：昭和初期にスマートフォンは存在しない"),
        (r"戦前.*コンピュータ", "時代錯誤：戦前にコンピュータは一般的でない"),
    ]

    def __init__(self, wikipedia_api=None):
        """
        初期化

        Args:
            wikipedia_api: Wikipedia APIのインスタンス（オプション）
        """
        self.wikipedia_api = wikipedia_api
        self.cache = {}

    def check_episode(
        self,
        person_id: str,
        person_name: str,
        episode_text: str,
        birth_year: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> FactCheckReport:
        """
        エピソードの事実確認

        Args:
            person_id: 人物ID
            person_name: 人物名
            episode_text: エピソードテキスト
            birth_year: 生年（オプション）
            metadata: メタデータ（オプション）

        Returns:
            FactCheckReport: 事実確認レポート
        """
        report = FactCheckReport(
            person_id=person_id,
            person_name=person_name,
            timestamp=datetime.now().isoformat(),
            result=FactCheckResult.VERIFIED,
            metadata=metadata or {},
        )

        # 1. ハルシネーション検出
        self._check_hallucination(episode_text, report)

        # 2. 時代錯誤チェック
        self._check_anachronism(episode_text, report)

        # 3. 年代整合性チェック
        if birth_year:
            self._check_chronological_consistency(episode_text, birth_year, report)

        # 4. 既知の事実との照合
        self._verify_known_facts(person_name, episode_text, report)

        # 5. 数値の妥当性チェック
        self._check_numerical_validity(episode_text, report)

        # 6. 最終評価
        self._evaluate_report(report)

        return report

    def _check_hallucination(self, text: str, report: FactCheckReport):
        """ハルシネーションパターンの検出"""
        for pattern, description in self.HALLUCINATION_PATTERNS:
            if re.search(pattern, text):
                violation = FactCheckViolation(
                    violation_type="HALLUCINATION_PATTERN",
                    message=f"ハルシネーションの可能性: {description}",
                    severity="high",
                    suggestion="Wikipedia等の信頼できる情報源で検証が必要",
                    confidence=0.8,
                )
                report.violations.append(violation)
                report.unverified_claims.append(description)

    def _check_anachronism(self, text: str, report: FactCheckReport):
        """時代錯誤の検出"""
        for pattern, description in self.ANACHRONISM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violation = FactCheckViolation(
                    violation_type="ANACHRONISM",
                    message=description,
                    severity="critical",
                    evidence=pattern,
                    suggestion="歴史的事実を確認し、正しい時代背景に修正",
                    confidence=0.95,
                )
                report.violations.append(violation)

    def _check_chronological_consistency(self, text: str, birth_year: int, report: FactCheckReport):
        """年代の整合性チェック"""
        # 年齢と年代の抽出
        age_matches = re.findall(r"(\d+)歳", text)
        year_matches = re.findall(r"(19|20)\d{2}年", text)

        for age_str in age_matches:
            age = int(age_str)
            for year_str in year_matches:
                year = int(year_str.replace("年", ""))
                expected_birth = year - age

                if abs(expected_birth - birth_year) > 1:
                    violation = FactCheckViolation(
                        violation_type="CHRONOLOGICAL_INCONSISTENCY",
                        message=f"年代不整合: {year}年に{age}歳なら生年は{expected_birth}年（実際: {birth_year}年）",
                        severity="high",
                        evidence=f"{year}年, {age}歳",
                        suggestion="正しい年齢または年代に修正",
                        confidence=0.9,
                    )
                    report.violations.append(violation)

    def _verify_known_facts(self, person_name: str, text: str, report: FactCheckReport):
        """既知の事実との照合"""
        if person_name not in self.KNOWN_FACTS:
            return

        facts = self.KNOWN_FACTS[person_name]

        # 生没年チェック
        if "birth_year" in facts:
            birth_year_pattern = f"{facts['birth_year']}年.*生"
            if re.search(r"\d{4}年.*生", text):
                if not re.search(birth_year_pattern, text):
                    report.unverified_claims.append(f"生年が既知の事実（{facts['birth_year']}年）と異なる可能性")
            else:
                report.verified_facts.append(f"生年: {facts['birth_year']}年")

        # 重要イベントの確認
        if "major_events" in facts:
            for event in facts["major_events"]:
                event_year = event["year"]
                event_desc = event["event"]

                if str(event_year) in text:
                    report.verified_facts.append(f"{event_year}年: {event_desc}")

    def _check_numerical_validity(self, text: str, report: FactCheckReport):
        """数値の妥当性チェック"""
        # 異常に大きな数値のチェック
        large_numbers = re.findall(r"(\d{6,})[^年]", text)
        for num_str in large_numbers:
            num = int(num_str)
            if num > 1000000000:  # 10億以上
                violation = FactCheckViolation(
                    violation_type="SUSPICIOUS_NUMBER",
                    message=f"異常に大きな数値: {num:,}",
                    severity="medium",
                    evidence=num_str,
                    suggestion="数値の正確性を確認",
                    confidence=0.7,
                )
                report.violations.append(violation)

        # パーセンテージの妥当性
        percentages = re.findall(r"(\d+(?:\.\d+)?)[%％]", text)
        for pct_str in percentages:
            pct = float(pct_str)
            if pct > 100:
                violation = FactCheckViolation(
                    violation_type="INVALID_PERCENTAGE",
                    message=f"100%を超える割合: {pct}%",
                    severity="critical",
                    evidence=f"{pct}%",
                    suggestion="正しい割合に修正",
                    confidence=1.0,
                )
                report.violations.append(violation)

    def _evaluate_report(self, report: FactCheckReport):
        """レポートの最終評価"""
        # 違反の重大度に基づいてスコアを計算
        score_deductions = {
            "critical": 50,  # より厳格に
            "high": 30,  # より厳格に
            "medium": 20,  # より厳格に
            "low": 10,  # より厳格に
        }

        total_score = 100.0
        for violation in report.violations:
            deduction = score_deductions.get(violation.severity, 0)
            total_score -= deduction

        report.total_score = max(0, total_score)

        # 結果の判定（より厳格な基準）
        if len(report.violations) == 0:
            report.result = FactCheckResult.VERIFIED
        elif any(v.severity == "critical" for v in report.violations):
            report.result = FactCheckResult.INCORRECT
        elif total_score < 60:  # 閾値を上げる
            report.result = FactCheckResult.SUSPICIOUS
        elif total_score < 85:  # 閾値を上げる
            report.result = FactCheckResult.PARTIAL
        else:
            report.result = FactCheckResult.UNVERIFIED

    def generate_summary(self, report: FactCheckReport) -> str:
        """
        レポートのサマリー生成

        Args:
            report: 事実確認レポート

        Returns:
            str: サマリーテキスト
        """
        lines = [
            "【事実確認レポート】",
            f"人物: {report.person_name} (ID: {report.person_id})",
            f"結果: {report.result.value}",
            f"スコア: {report.total_score:.1f}/100",
            "",
        ]

        if report.violations:
            lines.append("■ 検出された問題:")
            for v in report.violations:
                lines.append(f"  - [{v.severity.upper()}] {v.message}")
                if v.suggestion:
                    lines.append(f"    → {v.suggestion}")

        if report.verified_facts:
            lines.append("\n■ 検証済みの事実:")
            for fact in report.verified_facts:
                lines.append(f"  ✓ {fact}")

        if report.unverified_claims:
            lines.append("\n■ 未検証の主張:")
            for claim in report.unverified_claims:
                lines.append(f"  ? {claim}")

        return "\n".join(lines)


# テスト用関数
def test_fact_checker():
    """FactCheckerのテスト"""
    checker = FactChecker()

    # テストケース1: 正常なエピソード
    episode1 = """
    2004年、31歳のイチローはMLBでシーズン262安打の新記録を樹立。
    この記録は84年ぶりの更新となった。
    """

    report1 = checker.check_episode(person_id="P001", person_name="イチロー", episode_text=episode1, birth_year=1973)

    print(checker.generate_summary(report1))
    print("\n" + "=" * 50 + "\n")

    # テストケース2: ハルシネーションを含むエピソード
    episode2 = """
    世界で初めてYouTubeで1億人の登録者を獲得したHIKAKINは、
    2025年にノーベル平和賞を受賞した。
    """

    report2 = checker.check_episode(person_id="P002", person_name="HIKAKIN", episode_text=episode2, birth_year=1989)

    print(checker.generate_summary(report2))
    print("\n" + "=" * 50 + "\n")

    # テストケース3: 時代錯誤を含むエピソード
    episode3 = """
    江戸時代にインターネットで情報発信を始めた侍。
    """

    report3 = checker.check_episode(person_id="P003", person_name="架空の侍", episode_text=episode3)

    print(checker.generate_summary(report3))


if __name__ == "__main__":
    test_fact_checker()
