"""
Diversity Gate

多様性制約と偏り防止を管理。
"""

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ..config import CACHE_DIR, DIVERSITY_TARGETS, GENERATION_RULES, MASTER_CSV


@dataclass
class DiversityCheckResult:
    """多様性チェック結果"""

    passed: bool
    reason: str = ""
    category_gini: float = 0.0
    era_distribution: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "category_gini": self.category_gini,
            "era_distribution": self.era_distribution,
            "recommendations": self.recommendations,
        }


@dataclass
class GenerationQuota:
    """生成クォータ"""

    person_id: str
    daily_count: int = 0
    weekly_count: int = 0
    last_generation: Optional[str] = None
    cooldown_end: Optional[str] = None


class DiversityManager:
    """
    多様性管理

    カテゴリ/年代/人物の偏りを防止。
    """

    def __init__(
        self,
        master_csv: Path = MASTER_CSV,
        targets: dict = None,
        rules: dict = None,
    ):
        self.master_csv = master_csv
        self.targets = targets or DIVERSITY_TARGETS.copy()
        self.rules = rules or GENERATION_RULES.copy()
        self._master_df: Optional[pd.DataFrame] = None
        self._quota_cache: dict[str, GenerationQuota] = {}
        self._quota_cache_path = CACHE_DIR / "generation_quotas.json"
        self._load_quota_cache()

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

    def _load_quota_cache(self) -> None:
        """クォータキャッシュを読み込み"""
        if self._quota_cache_path.exists():
            try:
                with open(self._quota_cache_path, encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, quota_data in data.items():
                        self._quota_cache[pid] = GenerationQuota(
                            person_id=pid,
                            daily_count=quota_data.get("daily_count", 0),
                            weekly_count=quota_data.get("weekly_count", 0),
                            last_generation=quota_data.get("last_generation"),
                            cooldown_end=quota_data.get("cooldown_end"),
                        )
            except (json.JSONDecodeError, OSError):
                self._quota_cache = {}

    def _save_quota_cache(self) -> None:
        """クォータキャッシュを保存"""
        self._quota_cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for pid, quota in self._quota_cache.items():
            data[pid] = {
                "daily_count": quota.daily_count,
                "weekly_count": quota.weekly_count,
                "last_generation": quota.last_generation,
                "cooldown_end": quota.cooldown_end,
            }
        with open(self._quota_cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def calculate_gini(self, distribution: dict[str, int]) -> float:
        """
        ジニ係数を計算

        Args:
            distribution: カテゴリごとのカウント

        Returns:
            float: ジニ係数（0-1、低いほど均等）
        """
        if not distribution:
            return 0.0

        values = sorted(distribution.values())
        n = len(values)
        total = sum(values)

        if total == 0:
            return 0.0

        # ジニ係数計算
        cumsum = 0
        for i, v in enumerate(values):
            cumsum += v
        gini = 1 - 2 * sum((i + 1) * v for i, v in enumerate(values)) / (n * total) + (n + 1) / n

        return max(0.0, min(1.0, abs(gini)))

    def get_category_distribution(self) -> dict[str, int]:
        """現在のカテゴリ分布を取得"""
        if self.master_df.empty:
            return {}

        return dict(self.master_df["category"].value_counts())

    def get_era_distribution(self) -> dict[str, int]:
        """現在の年代分布を取得"""
        if self.master_df.empty:
            return {}

        # birth_yearから年代を計算
        era_counts = Counter()

        for _, row in self.master_df.iterrows():
            birth_year = row.get("birth_year")
            if pd.isna(birth_year):
                continue

            birth_year = int(birth_year)
            age = row.get("age", 0)
            target_year = birth_year + int(age)

            if target_year < 1500:
                era_counts["古代-中世"] += 1
            elif target_year < 1800:
                era_counts["近世"] += 1
            elif target_year < 1950:
                era_counts["近代"] += 1
            elif target_year < 2000:
                era_counts["現代前期"] += 1
            else:
                era_counts["現代後期"] += 1

        return dict(era_counts)

    def check_person_quota(self, person_id: str) -> tuple[bool, str]:
        """
        人物のクォータをチェック

        Args:
            person_id: 人物ID

        Returns:
            (passed, reason): パスしたか、理由
        """
        quota = self._quota_cache.get(person_id)
        if quota is None:
            return True, "No previous generations"

        now = datetime.now()

        # クールダウンチェック
        if quota.cooldown_end:
            cooldown_end = datetime.fromisoformat(quota.cooldown_end)
            if now < cooldown_end:
                remaining = cooldown_end - now
                return False, f"Cooldown active: {remaining}"

        # 日次上限チェック
        daily_limit = self.rules.get("max_per_person_per_day", 1)
        if quota.daily_count >= daily_limit:
            return False, f"Daily limit exceeded: {quota.daily_count}/{daily_limit}"

        # 週間上限チェック
        weekly_limit = self.rules.get("max_per_person_per_week", 3)
        if quota.weekly_count >= weekly_limit:
            return False, f"Weekly limit exceeded: {quota.weekly_count}/{weekly_limit}"

        return True, "Quota available"

    def record_generation(self, person_id: str) -> None:
        """
        生成を記録

        Args:
            person_id: 人物ID
        """
        now = datetime.now()
        cooldown_hours = self.rules.get("cooldown_hours", 24)

        quota = self._quota_cache.get(person_id)
        if quota is None:
            quota = GenerationQuota(person_id=person_id)
            self._quota_cache[person_id] = quota

        quota.daily_count += 1
        quota.weekly_count += 1
        quota.last_generation = now.isoformat()
        quota.cooldown_end = (now + timedelta(hours=cooldown_hours)).isoformat()

        self._save_quota_cache()

    def reset_daily_quotas(self) -> None:
        """日次クォータをリセット"""
        for quota in self._quota_cache.values():
            quota.daily_count = 0
        self._save_quota_cache()

    def reset_weekly_quotas(self) -> None:
        """週間クォータをリセット"""
        for quota in self._quota_cache.values():
            quota.daily_count = 0
            quota.weekly_count = 0
        self._save_quota_cache()

    def get_underrepresented_categories(self) -> list[str]:
        """
        過少カテゴリを取得

        Returns:
            list[str]: 優先すべきカテゴリ
        """
        current = self.get_category_distribution()
        target = self.targets.get("category_distribution", {})

        if not current or not target:
            return []

        total = sum(current.values())
        underrepresented = []

        for category, target_ratio in target.items():
            current_ratio = current.get(category, 0) / total
            if current_ratio < target_ratio * 0.8:  # 80%未満なら過少
                underrepresented.append(category)

        return underrepresented

    def check_diversity(self) -> DiversityCheckResult:
        """
        多様性チェック

        Returns:
            DiversityCheckResult: チェック結果
        """
        category_dist = self.get_category_distribution()
        era_dist = self.get_era_distribution()

        # ジニ係数計算
        category_gini = self.calculate_gini(category_dist)

        # 目標との比較
        max_gini = self.targets.get("max_category_gini", 0.3)
        passed = category_gini <= max_gini

        recommendations = []
        if not passed:
            recommendations.append("カテゴリ分布が偏っています")
            underrep = self.get_underrepresented_categories()
            if underrep:
                recommendations.append(f"過少カテゴリ: {', '.join(underrep)}")

        return DiversityCheckResult(
            passed=passed,
            reason=f"Category Gini: {category_gini:.3f} (max: {max_gini})",
            category_gini=category_gini,
            era_distribution=era_dist,
            recommendations=recommendations,
        )


def get_recommended_candidates(master_df: pd.DataFrame = None, count: int = 10) -> list[dict]:
    """
    推奨候補を取得

    多様性を考慮して候補を選定。

    Args:
        master_df: マスターDataFrame
        count: 候補数

    Returns:
        list[dict]: 推奨候補リスト
    """
    manager = DiversityManager()

    # 過少カテゴリを優先
    underrep = manager.get_underrepresented_categories()

    if master_df is None:
        if manager.master_csv.exists():
            master_df = pd.read_csv(manager.master_csv, encoding="utf-8-sig")
        else:
            return []

    candidates = []

    # 過少カテゴリから候補を選定
    for category in underrep:
        cat_episodes = master_df[master_df["category"] == category]
        if cat_episodes.empty:
            continue

        # ユニークな人物を取得
        unique_persons = cat_episodes.drop_duplicates(subset=["person_id"])

        for _, row in unique_persons.head(count // len(underrep) + 1).iterrows():
            person_id = row["person_id"]

            # クォータチェック
            passed, _ = manager.check_person_quota(person_id)
            if not passed:
                continue

            candidates.append(
                {
                    "person_id": person_id,
                    "person_name": row.get("person_name", ""),
                    "category": category,
                    "priority": "high",
                }
            )

            if len(candidates) >= count:
                break

        if len(candidates) >= count:
            break

    return candidates[:count]
