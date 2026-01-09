"""
Quality Evaluator

8軸評価（iconic_score追加）と品質ゲートチェックを実行。
既存の評価ロジックを統合。
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..adapters.base import AxisScores, EvaluationResult
from ..config import QUALITY_THRESHOLDS, RejectionReason

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ICONIC_ACHIEVEMENTS_PATH = PROJECT_ROOT / "preserved" / "data" / "iconic_achievements_master.json"


@dataclass
class GateCheckResult:
    """ゲートチェック結果"""

    passed: bool
    failures: list[str]
    reason: Optional[RejectionReason] = None


class QualityEvaluator:
    """
    品質評価器

    7軸評価と品質ゲートを統合管理。
    Phase 13: カテゴリ別閾値対応。
    """

    def __init__(self, thresholds: dict[str, float] = None):
        self.thresholds = thresholds or QUALITY_THRESHOLDS.copy()
        # Phase 13: CategoryThresholdsインスタンス（遅延初期化）
        self._category_thresholds = None

    def _get_category_thresholds(self):
        """CategoryThresholdsの遅延初期化"""
        if self._category_thresholds is None:
            from .category_evaluator import CategoryThresholds

            self._category_thresholds = CategoryThresholds()
        return self._category_thresholds

    def check_quality_gates(
        self,
        scores: AxisScores,
        category: Optional[str] = None,
        use_category: bool = True,
    ) -> GateCheckResult:
        """
        品質ゲートをチェック

        Args:
            scores: 7軸スコア
            category: カテゴリ名（Phase 13: カテゴリ別閾値用）
            use_category: カテゴリ別閾値を使用するか（デフォルトTrue）

        Returns:
            GateCheckResult: ゲートチェック結果
        """
        failures = []

        # Phase 13: カテゴリ別閾値の適用
        if category and use_category:
            cat_threshold = self._get_category_thresholds().get_threshold(category)
            min_fd = cat_threshold.factual_density
            min_gq = cat_threshold.generation_quality
            min_mem = cat_threshold.memorability
            min_emp = cat_threshold.empathy
            min_sur = cat_threshold.surprise
            min_edu = cat_threshold.educational_value
            min_story = cat_threshold.story_quality
        else:
            # グローバル閾値を使用
            min_fd = self.thresholds.get("min_factual_density", 6.0)
            min_gq = self.thresholds.get("min_generation_quality", 6.0)
            min_mem = self.thresholds.get("min_memorability", 5.5)
            min_emp = self.thresholds.get("min_empathy", 5.0)
            min_sur = self.thresholds.get("min_surprise", 5.0)
            min_edu = self.thresholds.get("min_educational_value", 5.0)
            min_story = self.thresholds.get("min_story_quality", 5.0)

        # factual_density（ハードゲート）
        if scores.factual_density < min_fd:
            failures.append(f"factual_density {scores.factual_density:.1f} < {min_fd}")

        # 生成品質（ハードゲート）
        if scores.generation_quality < min_gq:
            failures.append(f"generation_quality {scores.generation_quality:.1f} < {min_gq}")

        # 記憶性
        if scores.memorability < min_mem:
            failures.append(f"memorability {scores.memorability:.1f} < {min_mem}")

        # 共感性
        if scores.empathy < min_emp:
            failures.append(f"empathy {scores.empathy:.1f} < {min_emp}")

        # 意外性
        if scores.surprise < min_sur:
            failures.append(f"surprise {scores.surprise:.1f} < {min_sur}")

        # educational_value
        if scores.educational_value < min_edu:
            failures.append(f"educational_value {scores.educational_value:.1f} < {min_edu}")

        # story_quality
        if scores.story_quality < min_story:
            failures.append(f"story_quality {scores.story_quality:.1f} < {min_story}")

        if failures:
            # factual_densityまたは生成品質が低い場合は特別な理由コード
            if scores.factual_density < min_fd:
                reason = RejectionReason.LOW_FACTUAL_DENSITY
            elif scores.generation_quality < min_gq:
                reason = RejectionReason.LOW_GENERATION_QUALITY
            else:
                reason = RejectionReason.LOW_COMPOSITE_SCORE
            return GateCheckResult(passed=False, failures=failures, reason=reason)

        return GateCheckResult(passed=True, failures=[])

    def check_composite_threshold(self, composite: float) -> tuple[bool, Optional[str]]:
        """
        統合スコア閾値をチェック

        Args:
            composite: 統合スコア

        Returns:
            (passed, action): パスしたか、アクション（'accept', 'retry', 'reject'）
        """
        min_composite = self.thresholds.get("min_composite", 380)
        target_composite = self.thresholds.get("target_composite", 550)
        retry_composite = self.thresholds.get("retry_composite", 470)

        if composite >= target_composite:
            return True, "accept"
        elif composite >= retry_composite:
            return True, "retry"
        elif composite >= min_composite:
            return False, "retry"
        else:
            return False, "reject"

    def evaluate_text_quality(self, text: str) -> dict[str, Any]:
        """
        テキスト品質を分析

        Args:
            text: エピソードテキスト

        Returns:
            dict: 品質分析結果
        """
        analysis = {
            "char_count": len(text),
            "has_year": False,
            "year_count": 0,
            "has_proper_nouns": False,
            "proper_noun_count": 0,
            "has_numbers": False,
            "number_count": 0,
            "has_quoted": False,
            "quoted_count": 0,
            "specificity_score": 0,
        }

        # 年号の存在（例：1955年、2024年）
        years = re.findall(r"(1[89]\d{2}|20[0-2]\d)年", text)
        if years:
            analysis["has_year"] = True
            analysis["year_count"] = len(years)
            analysis["specificity_score"] += 1

        # 固有名詞（カタカナ3文字以上連続）
        katakana = re.findall(r"[\u30A0-\u30FF]{3,}", text)
        if katakana:
            analysis["has_proper_nouns"] = True
            analysis["proper_noun_count"] = len(katakana)
            analysis["specificity_score"] += 1

        # 数値データ
        numbers = re.findall(r"\d+[万億%位回番]|\d+\.\d+", text)
        if numbers:
            analysis["has_numbers"] = True
            analysis["number_count"] = len(numbers)
            analysis["specificity_score"] += 1

        # 「」内の固有名詞
        quoted = re.findall(r"「([^」]+)」", text)
        if quoted:
            analysis["has_quoted"] = True
            analysis["quoted_count"] = len(quoted)
            analysis["specificity_score"] += 1

        return analysis


class CompositeScoreCalculator:
    """
    統合スコア計算器

    8軸スコアから統合スコアを計算。
    """

    # 軸ごとの重み
    WEIGHTS = {
        "memorability": 1.0,
        "empathy": 1.0,
        "surprise": 1.0,
        "generation_quality": 1.5,  # 重要度高
        "educational_value": 1.0,
        "story_quality": 1.0,
        "factual_density": 1.5,  # 重要度高
        "iconic_score": 1.5,  # 重要度高（感銘度）
    }

    @classmethod
    def calculate(cls, scores: AxisScores) -> float:
        """
        統合スコアを計算

        Args:
            scores: 8軸スコア

        Returns:
            float: 統合スコア（0-1000スケール）
        """
        weighted_sum = (
            scores.memorability * cls.WEIGHTS["memorability"]
            + scores.empathy * cls.WEIGHTS["empathy"]
            + scores.surprise * cls.WEIGHTS["surprise"]
            + scores.generation_quality * cls.WEIGHTS["generation_quality"]
            + scores.educational_value * cls.WEIGHTS["educational_value"]
            + scores.story_quality * cls.WEIGHTS["story_quality"]
            + scores.factual_density * cls.WEIGHTS["factual_density"]
            + scores.iconic_score * cls.WEIGHTS["iconic_score"]
        )
        total_weight = sum(cls.WEIGHTS.values())
        avg = weighted_sum / total_weight

        # 0-10 → 0-100 → 0-1000 にスケール
        return avg * 100

    @classmethod
    def calculate_with_penalties(cls, scores: AxisScores, penalties: list[str] = None) -> float:
        """
        ペナルティ付きで統合スコアを計算

        Args:
            scores: 7軸スコア
            penalties: ペナルティリスト

        Returns:
            float: ペナルティ適用後の統合スコア
        """
        base_score = cls.calculate(scores)

        if not penalties:
            return base_score

        # ペナルティ適用（1つあたり10%減）
        penalty_rate = 0.10 * len(penalties)
        penalty_rate = min(penalty_rate, 0.5)  # 最大50%減

        return base_score * (1 - penalty_rate)


def create_evaluation_result(
    scores: AxisScores,
    composite_override: float = None,
    super_total: float = None,
) -> EvaluationResult:
    """
    評価結果を生成

    Args:
        scores: 8軸スコア
        composite_override: 統合スコア（オーバーライド）
        super_total: 超総合スコア

    Returns:
        EvaluationResult: 評価結果
    """
    evaluator = QualityEvaluator()

    # 統合スコア計算
    if composite_override is not None:
        composite = composite_override
    else:
        composite = CompositeScoreCalculator.calculate(scores)

    # ゲートチェック
    gate_result = evaluator.check_quality_gates(scores)

    return EvaluationResult(
        axis_scores=scores,
        composite_score=composite,
        super_total_score=super_total or 0.0,
        passed_gate=gate_result.passed,
        gate_failures=gate_result.failures,
    )


class IconicScoreCalculator:
    """
    iconic_score計算器

    エピソードが人物の象徴的な業績や転機を描写しているかを評価。
    「ユーザーが読んで感銘を受ける」度合いを数値化。
    """

    # 象徴的キーワード（ボーナス対象）
    ICONIC_KEYWORDS = [
        "初めて",
        "史上最年少",
        "史上初",
        "唯一",
        "世界記録",
        "歴史的",
        "革命的",
        "画期的",
        "転機",
        "人生を変えた",
        "金メダル",
        "優勝",
        "ノーベル賞",
        "受賞",
        "達成",
        "発明",
        "発見",
        "創業",
        "設立",
        "デビュー",
    ]

    def __init__(self):
        self._iconic_achievements: Optional[dict[str, Any]] = None

    def _load_iconic_achievements(self) -> dict[str, Any]:
        """象徴的業績マスターデータを読み込み"""
        if self._iconic_achievements is None:
            if ICONIC_ACHIEVEMENTS_PATH.exists():
                with open(ICONIC_ACHIEVEMENTS_PATH, encoding="utf-8") as f:
                    self._iconic_achievements = json.load(f)
            else:
                self._iconic_achievements = {"persons": {}}
        return self._iconic_achievements

    def _check_achievement_match(
        self,
        text: str,
        person_name: str,
        age: int,
    ) -> tuple[bool, float]:
        """
        マスターデータとのマッチをチェック

        Returns:
            (matched, bonus): マッチしたか、ボーナススコア
        """
        achievements = self._load_iconic_achievements()
        persons = achievements.get("persons", {})
        person_data = persons.get(person_name)

        if not person_data:
            return False, 0.0

        required_episodes = person_data.get("required_episodes", [])
        max_bonus = 0.0

        for ep in required_episodes:
            ep_age = ep.get("age", 0)
            keywords = ep.get("keywords", [])
            importance = ep.get("importance", 8.0)

            # 年齢一致チェック（±2歳）
            if abs(ep_age - age) <= 2:
                # キーワードマッチチェック
                keyword_matches = sum(1 for kw in keywords if kw in text)
                if keyword_matches >= 1:
                    # マッチ度に応じたボーナス
                    match_ratio = keyword_matches / max(len(keywords), 1)
                    bonus = (importance / 10) * 3.0 * match_ratio  # 最大+3.0
                    max_bonus = max(max_bonus, bonus)

        return max_bonus > 0, max_bonus

    def calculate(
        self,
        text: str,
        person_name: str = "",
        age: int = 0,
    ) -> float:
        """
        iconic_scoreを計算

        Args:
            text: エピソードテキスト
            person_name: 人物名
            age: 年齢

        Returns:
            float: iconic_score（1.0-10.0）
        """
        score = 5.0  # ベースライン

        # マスターデータマッチ: 最大+3.0
        matched, match_bonus = self._check_achievement_match(text, person_name, age)
        if matched:
            score += match_bonus

        # キーワードボーナス: 最大+1.5
        keyword_bonus = 0.0
        for kw in self.ICONIC_KEYWORDS:
            if kw in text:
                keyword_bonus += 0.3
        keyword_bonus = min(keyword_bonus, 1.5)
        score += keyword_bonus

        # 具体性ボーナス: 最大+0.5
        # 西暦年号の存在
        if re.search(r"(1[89]\d{2}|20[0-2]\d)年", text):
            score += 0.25
        # 「」で囲まれた固有名詞の存在
        if re.search(r"「[^」]+」", text):
            score += 0.25

        # スコアを1.0-10.0の範囲に制限
        return max(1.0, min(10.0, score))
