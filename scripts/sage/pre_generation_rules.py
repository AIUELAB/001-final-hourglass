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
from typing import TYPE_CHECKING, Optional

import pandas as pd

if TYPE_CHECKING:
    from .inventory_manager import InventoryManager

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
    retryable: bool = False  # Trueの場合、リトライで改善可能

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
        inventory_manager: Optional["InventoryManager"] = None,
    ):
        self.master_csv = master_csv
        self.rules = rules or GENERATION_RULES.copy()
        self.thresholds = thresholds or QUALITY_THRESHOLDS.copy()
        # Phase 17: 置換モード対応
        self._inventory_manager = inventory_manager

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
        全ルールをチェック（Phase 17: 置換モード対応）

        Args:
            candidate: 生成候補

        Returns:
            RuleCheckResult: チェック結果
        """
        # Phase 17: 置換候補情報を保持
        replacement_details: dict = {}

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
            # Phase 17: 置換候補情報を保持
            if result.details.get("is_replacement_candidate"):
                replacement_details = result.details.copy()

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

        # 6. RCA-20260110: 極端年齢チェック（0-5歳, 90歳以上の品質リスク軽減）
        if self.rules.get("extreme_age_filter", True):
            result = self._check_extreme_ages(candidate)
            if not result.passed:
                return result

        # Phase 17: 置換候補情報を最終結果に含める
        return RuleCheckResult(
            passed=True,
            message="All pre-generation rules passed",
            details=replacement_details if replacement_details else {},
        )

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
        同一年齢重複チェック（Phase 17: 置換モード対応）

        同一人物・同一年齢のエピソードが既に存在するか確認。
        置換モードが有効な場合、棄却せずに置換候補としてマークする。
        """
        if self.master_df.empty:
            return RuleCheckResult(passed=True, message="No existing episodes to check")

        # 同一人物・同一年齢のエピソードを検索
        existing = self.master_df[
            (self.master_df["person_id"] == candidate.person_id) & (self.master_df["age"] == candidate.age)
        ]

        if not existing.empty:
            first = existing.iloc[0]
            existing_episode_id = first.get("episode_id", "unknown")
            existing_score = float(first.get("super_total_score", 0) or 0)

            # Phase 17: 置換モードチェック
            if self._inventory_manager is not None:
                if self._inventory_manager.is_replacement_mode(candidate.age):
                    # 置換モード: 棄却せずに置換候補としてマーク
                    return RuleCheckResult(
                        passed=True,  # 通過を許可
                        message=f"Replacement candidate: {candidate.person_name} at age {candidate.age}",
                        details={
                            "is_replacement_candidate": True,
                            "existing_episode_id": existing_episode_id,
                            "existing_score": existing_score,
                            "existing_count": len(existing),
                        },
                    )

            # 通常モード: 従来通り棄却
            return RuleCheckResult(
                passed=False,
                reason=RejectionReason.SAME_AGE_DUPLICATE,
                message=f"Episode for {candidate.person_name} at age {candidate.age} already exists",
                details={"existing_count": len(existing), "existing_score": existing_score},
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

    def _check_extreme_ages(self, candidate: Candidate) -> RuleCheckResult:
        """
        RCA-20260110: 極端年齢チェック

        0-5歳と90歳以上は品質リスクが高いため除外。
        - 0-5歳: 幼児の業績エピソードはハルシネーションになりやすい
        - 90歳以上: 死亡年が未確認の場合、存命と仮定して生成されるリスク

        例外:
        - death_yearが明確で、その年齢まで生きていた場合は90歳以上も許可
        - 6-10歳は許可（子役デビュー、神童など実例あり）
        """
        age = candidate.age

        # 0-5歳は一律除外（幼児の業績エピソードはハルシネーションになりやすい）
        if age <= 5:
            return RuleCheckResult(
                passed=False,
                reason=RejectionReason.AGE_BOUNDARY_VIOLATION,
                message=f"Extreme young age {age} filtered (high hallucination risk)",
                details={"age": age, "reason": "infant_age"},
            )

        # 90歳以上のチェック
        if age >= 90:
            # Phase 28: 架空キャラ・神話キャラはpreferred_ageに基づき許可
            if self.master_df is not None and not self.master_df.empty:
                person_data = self.master_df[self.master_df["person_id"] == candidate.person_id]
                if not person_data.empty:
                    row = person_data.iloc[0]
                    person_type = str(row.get("person_type", "REAL"))
                    preferred_age = row.get("preferred_age")
                    # FICTIONAL/MYTHOLOGICALでpreferred_age >= 80なら許可
                    if person_type in ("FICTIONAL", "MYTHOLOGICAL"):
                        if preferred_age is not None and not pd.isna(preferred_age) and float(preferred_age) >= 80:
                            return RuleCheckResult(
                                passed=True,
                                message=f"Fictional character with high preferred_age ({preferred_age}) allowed at age {age}",
                            )
            # death_yearが明確で、その年齢まで生きていた場合は許可
            if candidate.death_year and candidate.birth_year:
                max_age = candidate.death_year - candidate.birth_year
                if age <= max_age:
                    return RuleCheckResult(
                        passed=True, message=f"Age {age} is within verified lifespan (max={max_age})"
                    )
            # それ以外は除外
            return RuleCheckResult(
                passed=False,
                reason=RejectionReason.AGE_BOUNDARY_VIOLATION,
                message=f"Extreme elderly age {age} filtered (unverified lifespan)",
                details={"age": age, "reason": "unverified_elderly"},
            )

        return RuleCheckResult(passed=True, message="Age is within acceptable range")


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
    具体性チェック（埋め草検出）- 段階的閾値

    年号、固有名詞、数値データの存在を確認。
    - score < 1: 即棄却（FILLER_DETECTED, リトライ不可）
    - score 1: リトライ可（LOW_SPECIFICITY, retryable=True）
    - score >= 2: 合格

    Args:
        text: チェック対象テキスト
        min_specificity: 最低具体性スコア

    Returns:
        RuleCheckResult: チェック結果
    """
    specificity_score = 0

    # 年号の存在（西暦 + 元号対応）
    year_pattern = r"(1[789]\d{2}|20[0-2]\d)年|(明治|大正|昭和|平成|令和)\d{1,2}年"
    year_matches = re.findall(year_pattern, text)
    if year_matches:
        specificity_score += 1
        # 2つ以上の年号でボーナス
        if len(year_matches) >= 2:
            specificity_score += 0.5

    # 固有名詞の存在（カタカナ3文字以上連続、「」『』内）
    katakana_pattern = r"[\u30A0-\u30FF]{3,}"
    quoted_pattern = r"「[^」]+」|『[^』]+』"
    katakana_count = len(re.findall(katakana_pattern, text))
    quoted_count = len(re.findall(quoted_pattern, text))

    if katakana_count >= 3 or quoted_count >= 2:
        specificity_score += 1
    elif katakana_count >= 1 or quoted_count >= 1:
        specificity_score += 0.5

    # 数値データの存在（例：100万人、50%、第1位）
    number_pattern = r"\d+[本回度件位番勝敗万億個年日月%]|\d+\.\d+"
    number_matches = re.findall(number_pattern, text)
    if len(number_matches) >= 3:
        specificity_score += 1
    elif len(number_matches) >= 1:
        specificity_score += 0.5

    # イベント・出来事キーワード
    event_pattern = r"(受賞|優勝|達成|記録|就任|引退|完成|公開|発表|死去|誕生|デビュー|発売|創設|設立|開催)"
    if re.search(event_pattern, text):
        specificity_score += 0.5

    # 段階的判定
    if specificity_score < 1:
        # 極度に具体性不足 → 即棄却（リトライ不可）
        return RuleCheckResult(
            passed=False,
            reason=RejectionReason.FILLER_DETECTED,
            message=f"Very low specificity: {specificity_score:.1f} < 1 (no retry)",
            details={"specificity_score": specificity_score},
            retryable=False,
        )
    elif specificity_score < min_specificity:
        # 具体性やや不足 → リトライ可
        return RuleCheckResult(
            passed=False,
            reason=RejectionReason.LOW_SPECIFICITY,
            message=f"Low specificity: {specificity_score:.1f} < {min_specificity} (retryable)",
            details={"specificity_score": specificity_score},
            retryable=True,
        )

    return RuleCheckResult(
        passed=True,
        message=f"Specificity check passed: {specificity_score:.1f}",
        details={"specificity_score": specificity_score},
    )
