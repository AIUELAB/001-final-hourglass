"""
Pre-Generation Rules

LLM呼び出し前に候補を弾くルールエンジン。
トークン節約と早期棄却を実現。
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import (
    CACHE_DIR,
    GENERATION_RULES,
    MASTER_CSV,
    PROHIBITED_PATTERNS,
    QUALITY_THRESHOLDS,
    RejectionReason,
)


@dataclass
class Candidate:
    """生成候補"""

    person_id: str
    person_name: str
    age: int
    category: str
    person_type: str = "REAL"
    birth_year: Optional[int] = None
    death_year: Optional[int] = None

    def __post_init__(self) -> None:
        # 年齢の妥当性チェック
        if self.age < 0 or self.age > 150:
            raise ValueError(f"Invalid age: {self.age}")


@dataclass
class RuleCheckResult:
    """ルールチェック結果"""

    passed: bool
    reason: Optional[RejectionReason] = None
    message: str = ""
    details: dict = None

    def __post_init__(self) -> None:
        if self.details is None:
            self.details = {}


class PreGenerationRules:
    """
    生成前ルールエンジン

    LLM呼び出し前に候補をフィルタリングし、トークン消費を削減。
    """

    def __init__(
        self,
        master_csv: Path = MASTER_CSV,
        rules: dict = None,
        thresholds: dict = None,
    ):
        self.master_csv = master_csv
        self.rules = rules or GENERATION_RULES.copy()
        self.thresholds = thresholds or QUALITY_THRESHOLDS.copy()

        # マスターデータ読み込み
        self._master_df: Optional[pd.DataFrame] = None

        # 生成履歴キャッシュ
        self._generation_history: dict = {}
        self._history_cache_path = CACHE_DIR / "generation_history.json"
        self._load_history_cache()

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

    def _load_history_cache(self) -> None:
        """生成履歴キャッシュを読み込み"""
        if self._history_cache_path.exists():
            try:
                with open(self._history_cache_path, encoding="utf-8") as f:
                    self._generation_history = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._generation_history = {}

    def _save_history_cache(self) -> None:
        """生成履歴キャッシュを保存"""
        self._history_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._history_cache_path, "w", encoding="utf-8") as f:
            json.dump(self._generation_history, f, ensure_ascii=False, indent=2)

    def record_generation(self, person_id: str, success: bool = True) -> None:
        """生成履歴を記録"""
        now = datetime.now().isoformat()
        if person_id not in self._generation_history:
            self._generation_history[person_id] = []
        self._generation_history[person_id].append({"timestamp": now, "success": success})
        self._save_history_cache()

    def check_all(self, candidate: Candidate) -> RuleCheckResult:
        """
        全ルールをチェック

        Args:
            candidate: 生成候補

        Returns:
            RuleCheckResult: チェック結果
        """
        # 1. 年齢境界チェック
        if self.rules.get("age_boundary", True):
            result = self._check_age_boundary(candidate)
            if not result.passed:
                return result

        # 2. 同一年齢重複チェック
        if self.rules.get("same_age_duplicate", True):
            result = self._check_same_age_duplicate(candidate)
            if not result.passed:
                return result

        # 3. クールダウンチェック
        cooldown_hours = self.rules.get("cooldown_hours", 24)
        if cooldown_hours > 0:
            result = self._check_cooldown(candidate, cooldown_hours)
            if not result.passed:
                return result

        # 4. 週間上限チェック
        weekly_limit = self.rules.get("max_per_person_per_week", 3)
        if weekly_limit > 0:
            result = self._check_weekly_limit(candidate, weekly_limit)
            if not result.passed:
                return result

        # 5. 日次上限チェック
        daily_limit = self.rules.get("max_per_person_per_day", 1)
        if daily_limit > 0:
            result = self._check_daily_limit(candidate, daily_limit)
            if not result.passed:
                return result

        return RuleCheckResult(passed=True, message="All pre-generation rules passed")

    def _check_age_boundary(self, candidate: Candidate) -> RuleCheckResult:
        """
        年齢境界チェック

        - 死亡後のエピソードを防止（age > death_year - birth_year）
        - 未来のエピソードを防止（age > current_year - birth_year）
        """
        current_year = datetime.now().year

        # マスターから人物情報を取得
        if not self.master_df.empty:
            person_data = self.master_df[self.master_df["person_id"] == candidate.person_id]
            if not person_data.empty:
                row = person_data.iloc[0]
                birth_year = candidate.birth_year or row.get("birth_year")
                death_year = candidate.death_year or row.get("death_year")
            else:
                birth_year = candidate.birth_year
                death_year = candidate.death_year
        else:
            birth_year = candidate.birth_year
            death_year = candidate.death_year

        # 生年が不明な場合はパス
        if birth_year is None or pd.isna(birth_year):
            return RuleCheckResult(passed=True, message="Birth year unknown, skipping age boundary check")

        birth_year = int(birth_year)
        target_year = birth_year + candidate.age

        # 死亡年チェック
        if death_year is not None and not pd.isna(death_year):
            death_year = int(death_year)
            max_age = death_year - birth_year
            if candidate.age > max_age:
                return RuleCheckResult(
                    passed=False,
                    reason=RejectionReason.AGE_BOUNDARY_VIOLATION,
                    message=f"Age {candidate.age} exceeds death age {max_age}",
                    details={"birth_year": birth_year, "death_year": death_year},
                )

        # 未来チェック
        if target_year > current_year:
            return RuleCheckResult(
                passed=False,
                reason=RejectionReason.AGE_BOUNDARY_VIOLATION,
                message=f"Target year {target_year} is in the future",
                details={"birth_year": birth_year, "target_year": target_year},
            )

        return RuleCheckResult(passed=True, message="Age boundary check passed")

    def _check_same_age_duplicate(self, candidate: Candidate) -> RuleCheckResult:
        """
        同一年齢重複チェック

        同一人物・同一年齢のエピソードが既に存在するか確認。
        """
        if self.master_df.empty:
            return RuleCheckResult(passed=True, message="No existing episodes to check")

        # 同一人物・同一年齢のエピソードを検索
        existing = self.master_df[
            (self.master_df["person_id"] == candidate.person_id) & (self.master_df["age"] == candidate.age)
        ]

        if not existing.empty:
            return RuleCheckResult(
                passed=False,
                reason=RejectionReason.SAME_AGE_DUPLICATE,
                message=f"Episode for {candidate.person_name} at age {candidate.age} already exists",
                details={"existing_count": len(existing)},
            )

        return RuleCheckResult(passed=True, message="No same-age duplicate found")

    def _check_cooldown(self, candidate: Candidate, cooldown_hours: int) -> RuleCheckResult:
        """
        クールダウンチェック

        同一人物の最終生成から一定時間経過しているか確認。
        """
        history = self._generation_history.get(candidate.person_id, [])
        if not history:
            return RuleCheckResult(passed=True, message="No generation history")

        # 最新の生成時刻を取得
        latest = max(h["timestamp"] for h in history)
        latest_dt = datetime.fromisoformat(latest)
        cooldown_end = latest_dt + timedelta(hours=cooldown_hours)

        if datetime.now() < cooldown_end:
            remaining = cooldown_end - datetime.now()
            return RuleCheckResult(
                passed=False,
                reason=RejectionReason.COOLDOWN_ACTIVE,
                message=f"Cooldown active, {remaining} remaining",
                details={
                    "last_generation": latest,
                    "cooldown_end": cooldown_end.isoformat(),
                },
            )

        return RuleCheckResult(passed=True, message="Cooldown period passed")

    def _check_weekly_limit(self, candidate: Candidate, weekly_limit: int) -> RuleCheckResult:
        """
        週間上限チェック

        同一人物の週間生成数が上限内か確認。
        """
        history = self._generation_history.get(candidate.person_id, [])
        if not history:
            return RuleCheckResult(passed=True, message="No generation history")

        # 過去7日間の生成数をカウント
        week_ago = datetime.now() - timedelta(days=7)
        weekly_count = sum(1 for h in history if datetime.fromisoformat(h["timestamp"]) > week_ago and h.get("success"))

        if weekly_count >= weekly_limit:
            return RuleCheckResult(
                passed=False,
                reason=RejectionReason.WEEKLY_LIMIT_EXCEEDED,
                message=f"Weekly limit ({weekly_limit}) exceeded: {weekly_count}",
                details={"weekly_count": weekly_count, "limit": weekly_limit},
            )

        return RuleCheckResult(passed=True, message="Weekly limit OK")

    def _check_daily_limit(self, candidate: Candidate, daily_limit: int) -> RuleCheckResult:
        """
        日次上限チェック

        同一人物の日次生成数が上限内か確認。
        """
        history = self._generation_history.get(candidate.person_id, [])
        if not history:
            return RuleCheckResult(passed=True, message="No generation history")

        # 過去24時間の生成数をカウント
        day_ago = datetime.now() - timedelta(days=1)
        daily_count = sum(1 for h in history if datetime.fromisoformat(h["timestamp"]) > day_ago and h.get("success"))

        if daily_count >= daily_limit:
            return RuleCheckResult(
                passed=False,
                reason=RejectionReason.COOLDOWN_ACTIVE,
                message=f"Daily limit ({daily_limit}) exceeded: {daily_count}",
                details={"daily_count": daily_count, "limit": daily_limit},
            )

        return RuleCheckResult(passed=True, message="Daily limit OK")


def check_prohibited_patterns(text: str) -> RuleCheckResult:
    """
    禁止パターンチェック

    メタ表現、曖昧表現、過度な推測などを検出。

    Args:
        text: チェック対象テキスト

    Returns:
        RuleCheckResult: チェック結果
    """
    matched_patterns = []

    for pattern in PROHIBITED_PATTERNS:
        if re.search(pattern, text):
            matched_patterns.append(pattern)

    if matched_patterns:
        return RuleCheckResult(
            passed=False,
            reason=RejectionReason.PROHIBITED_PATTERN,
            message=f"Prohibited patterns found: {len(matched_patterns)}",
            details={"patterns": matched_patterns[:5]},  # 最大5件
        )

    return RuleCheckResult(passed=True, message="No prohibited patterns found")


def check_specificity(text: str, min_specificity: int = 2) -> RuleCheckResult:
    """
    具体性チェック（埋め草検出）

    年号、固有名詞、数値データの存在を確認。

    Args:
        text: チェック対象テキスト
        min_specificity: 最低具体性スコア

    Returns:
        RuleCheckResult: チェック結果
    """
    specificity_score = 0

    # 年号の存在（例：1955年、2024年）
    year_pattern = r"\b(1[89]\d{2}|20[0-2]\d)年\b"
    if re.search(year_pattern, text):
        specificity_score += 1

    # 固有名詞の存在（カタカナ3文字以上連続）
    katakana_pattern = r"[\u30A0-\u30FF]{3,}"
    if re.search(katakana_pattern, text):
        specificity_score += 1

    # 数値データの存在（例：100万人、50%、第1位）
    number_pattern = r"\d+[万億%位回番]|\d+\.\d+"
    if re.search(number_pattern, text):
        specificity_score += 1

    # 作品名・イベント名（「」内）
    quoted_pattern = r"「[^」]+」"
    if re.search(quoted_pattern, text):
        specificity_score += 1

    if specificity_score < min_specificity:
        return RuleCheckResult(
            passed=False,
            reason=RejectionReason.FILLER_DETECTED,
            message=f"Low specificity score: {specificity_score} < {min_specificity}",
            details={"specificity_score": specificity_score},
        )

    return RuleCheckResult(
        passed=True,
        message=f"Specificity check passed: {specificity_score}",
        details={"specificity_score": specificity_score},
    )
