"""
Inventory Manager - 年齢別エピソード在庫管理

SAGE vNext Phase 1: 年齢ごとに上位レベルエピソードを365本揃える運用設計。
- 365本達成で生成停止
- 達成後は置換モード（スコアΔ>=5%で入替）
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import pandas as pd

from .config import CACHE_DIR, MASTER_CSV, QUALITY_THRESHOLDS


class GenerationMode(Enum):
    """生成モード"""

    GENERATE = "generate"  # 未達成：生成継続
    STOP = "stop"  # 達成済み：生成停止
    REPLACE = "replace"  # 達成済み＋置換対象あり：置換モード


@dataclass
class InventoryConfig:
    """在庫管理設定"""

    target_per_age: int = 375  # 年齢別目標本数（Phase 16: 365→375）
    min_factual_density: float = 7.0  # 上位レベル: factual_density閾値
    min_generation_quality: float = 8.0  # 上位レベル: 生成品質閾値
    replacement_threshold: float = 0.05  # 置換閾値: 5%改善
    min_age: int = 1  # 管理対象最小年齢（Phase 16: 1-100歳のみ）
    max_age: int = 100  # 管理対象最大年齢（Phase 16: 1-100歳のみ）
    person_type_filter: str | None = "REAL"  # 人物タイプフィルタ（None=全て）


@dataclass
class ReplacementTarget:
    """置換対象情報"""

    episode_id: str
    person_id: str
    person_name: str
    age: int
    score: float  # super_total_score


@dataclass
class AgeStatus:
    """年齢別ステータス"""

    age: int
    total_count: int  # 総エピソード数
    upper_count: int  # 上位レベル数
    target: int  # 目標数
    achieved: bool  # 達成済みか
    mode: GenerationMode  # 生成モード
    min_upper_score: float  # 上位レベル最低スコア（置換判定用）
    deficit: int  # 不足数（負なら余剰）
    replacement_threshold: float = 0.0  # 置換必要スコア（min * 1.05）

    def to_dict(self) -> dict:
        return {
            "age": self.age,
            "total_count": self.total_count,
            "upper_count": self.upper_count,
            "target": self.target,
            "achieved": self.achieved,
            "mode": self.mode.value,
            "min_upper_score": self.min_upper_score,
            "deficit": self.deficit,
            "replacement_threshold": self.replacement_threshold,
        }


class InventoryManager:
    """
    年齢別エピソード在庫管理

    主な機能:
    - 年齢別の上位レベルエピソード数をカウント
    - 365本達成判定
    - 生成/停止/置換モードの判定
    - 置換条件（スコアΔ>=5%）の判定
    """

    def __init__(
        self,
        master_csv: Path | None = None,
        cache_dir: Path | None = None,
        config: InventoryConfig | None = None,
    ):
        self.master_csv = master_csv or MASTER_CSV
        self.cache_dir = cache_dir or CACHE_DIR
        self.config = config or InventoryConfig()
        self._cache_file = self.cache_dir / "age_inventory.json"
        self._df: pd.DataFrame | None = None
        self._inventory: dict[int, AgeStatus] = {}
        self._last_update: datetime | None = None

    def _load_master(self) -> pd.DataFrame:
        """マスターCSVを読み込み"""
        if self._df is None:
            self._df = pd.read_csv(self.master_csv, encoding="utf-8-sig", low_memory=False)
            # 数値変換
            for col in ["factual_density", "generation_quality_score", "super_total_score"]:
                if col in self._df.columns:
                    self._df[col] = pd.to_numeric(self._df[col], errors="coerce")
        return self._df

    def _is_upper_level(self, row: pd.Series) -> bool:
        """上位レベル判定: factual_density>=7 AND 生成品質>=8"""
        factual = row.get("factual_density", 0) or 0
        quality = row.get("generation_quality_score", 0) or 0
        return factual >= self.config.min_factual_density and quality >= self.config.min_generation_quality

    def refresh(self) -> None:
        """在庫情報を更新"""
        df = self._load_master()

        # 有効年齢範囲でフィルタ（person_typeフィルタ付き）
        if self.config.person_type_filter:
            df_valid = df[
                (df["age"] >= self.config.min_age)
                & (df["age"] <= self.config.max_age)
                & (df["person_type"] == self.config.person_type_filter)
            ].copy()
        else:
            df_valid = df[(df["age"] >= self.config.min_age) & (df["age"] <= self.config.max_age)].copy()

        # 上位レベル判定
        df_valid["is_upper"] = df_valid.apply(self._is_upper_level, axis=1)

        # 年齢別集計
        self._inventory = {}
        for age in range(self.config.min_age, self.config.max_age + 1):
            age_df = df_valid[df_valid["age"] == age]
            upper_df = age_df[age_df["is_upper"]]

            total_count = len(age_df)
            upper_count = len(upper_df)
            achieved = upper_count >= self.config.target_per_age
            deficit = self.config.target_per_age - upper_count

            # 上位レベル最低スコア
            min_upper_score = 0.0
            if len(upper_df) > 0:
                upper_scores = upper_df["super_total_score"].dropna()  # type: ignore[union-attr]
                if len(upper_scores) > 0:
                    min_upper_score = float(upper_scores.min())

            # モード判定 (Phase 4: 置換モード対応)
            if not achieved:
                mode = GenerationMode.GENERATE
            else:
                # 達成済みの場合は置換モード（品質改善のみ許可）
                mode = GenerationMode.REPLACE

            # 置換閾値を計算（5%改善必要）
            replacement_threshold = (
                min_upper_score * (1 + self.config.replacement_threshold) if min_upper_score > 0 else 0.0
            )

            self._inventory[age] = AgeStatus(
                age=age,
                total_count=total_count,
                upper_count=upper_count,
                target=self.config.target_per_age,
                achieved=achieved,
                mode=mode,
                min_upper_score=min_upper_score,
                deficit=deficit,
                replacement_threshold=replacement_threshold,
            )

        self._last_update = datetime.now()
        self._save_cache()

    def _save_cache(self) -> None:
        """キャッシュに保存"""
        cache_data = {
            "updated_at": self._last_update.isoformat() if self._last_update else None,
            "config": {
                "target_per_age": self.config.target_per_age,
                "min_factual_density": self.config.min_factual_density,
                "min_generation_quality": self.config.min_generation_quality,
            },
            "summary": self.get_summary(),
            "ages": {age: status.to_dict() for age, status in self._inventory.items()},
        }
        with open(self._cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

    def _load_cache(self) -> bool:
        """キャッシュから読み込み"""
        if not self._cache_file.exists():
            return False
        try:
            with open(self._cache_file, encoding="utf-8") as f:
                data = json.load(f)
            # キャッシュが古い場合は無効
            if data.get("updated_at"):
                updated = datetime.fromisoformat(data["updated_at"])
                # 1時間以内なら有効
                if (datetime.now() - updated).total_seconds() < 3600:
                    self._last_update = updated
                    return True
        except (json.JSONDecodeError, KeyError):
            pass
        return False

    def get_status(self, age: int) -> AgeStatus | None:
        """年齢別ステータスを取得"""
        if not self._inventory:
            self.refresh()
        return self._inventory.get(age)

    def should_generate(self, age: int) -> bool:
        """生成すべきか判定"""
        status = self.get_status(age)
        if status is None:
            return False  # 範囲外
        return status.mode == GenerationMode.GENERATE

    def should_replace(self, age: int, new_score: float) -> bool:
        """置換すべきか判定（Δ>=5%で置換）"""
        status = self.get_status(age)
        if status is None:
            return False

        # 未達成なら常に追加（置換ではない）
        if not status.achieved:
            return False

        # 達成済みの場合、最低スコアより5%以上高ければ置換
        if status.min_upper_score <= 0:
            return False

        threshold = status.min_upper_score * (1 + self.config.replacement_threshold)
        return new_score >= threshold

    def get_replacement_target(self, age: int) -> ReplacementTarget | None:
        """
        置換対象を取得（最低スコアのエピソード）

        Args:
            age: 年齢

        Returns:
            ReplacementTarget: 置換対象情報、またはNone
        """
        if not self._inventory:
            self.refresh()

        status = self.get_status(age)
        if status is None or not status.achieved:
            return None

        df = self._load_master()
        age_df = df[(df["age"] == age)].copy()

        # 上位レベル判定
        age_df["is_upper"] = age_df.apply(self._is_upper_level, axis=1)
        upper_df = age_df[age_df["is_upper"]]

        if len(upper_df) == 0:
            return None

        # 最低スコアのエピソード
        scores = upper_df["super_total_score"]
        min_idx = scores.idxmin()  # type: ignore[union-attr]
        row = upper_df.loc[min_idx]  # type: ignore[union-attr]

        score_val = row["super_total_score"]
        return ReplacementTarget(
            episode_id=str(row["episode_id"]),
            person_id=str(row["person_id"]),
            person_name=str(row["person_name"]),
            age=int(row["age"]),
            score=float(score_val) if not pd.isna(score_val) else 0.0,
        )

    def is_replacement_mode(self, age: int) -> bool:
        """置換モードかどうかを判定"""
        status = self.get_status(age)
        if status is None:
            return False
        return status.mode == GenerationMode.REPLACE

    def get_summary(self) -> dict:
        """全体サマリーを取得"""
        if not self._inventory:
            self.refresh()

        total_ages = len(self._inventory)
        achieved_ages = sum(1 for s in self._inventory.values() if s.achieved)
        total_upper = sum(s.upper_count for s in self._inventory.values())
        total_target = self.config.target_per_age * total_ages

        return {
            "total_ages": total_ages,
            "achieved_ages": achieved_ages,
            "achievement_rate": round(achieved_ages / total_ages * 100, 1) if total_ages > 0 else 0,
            "total_upper_episodes": total_upper,
            "total_target": total_target,
            "overall_progress": round(total_upper / total_target * 100, 1) if total_target > 0 else 0,
        }

    def get_priority_ages(self, limit: int = 10) -> list[int]:
        """優先生成すべき年齢リスト（不足数が多い順）"""
        if not self._inventory:
            self.refresh()

        # 未達成の年齢を不足数順にソート
        unachieved = [s for s in self._inventory.values() if not s.achieved]
        unachieved.sort(key=lambda s: s.deficit, reverse=True)

        return [s.age for s in unachieved[:limit]]

    def print_report(self) -> None:
        """レポートを出力"""
        summary = self.get_summary()
        print("=" * 60)
        print("年齢別在庫レポート")
        print("=" * 60)
        print(
            f"定義: 上位レベル = factual_density>={self.config.min_factual_density} AND 生成品質>={self.config.min_generation_quality}"
        )
        print()
        print(f"365本達成年齢: {summary['achieved_ages']}/{summary['total_ages']} ({summary['achievement_rate']}%)")
        print(
            f"上位レベル総数: {summary['total_upper_episodes']:,}/{summary['total_target']:,} ({summary['overall_progress']}%)"
        )
        print()

        # 優先年齢
        priority = self.get_priority_ages(5)
        print("優先生成年齢（不足数上位5）:")
        for age in priority:
            status = self._inventory[age]
            print(f"  {age}歳: {status.upper_count}/{status.target} (不足{status.deficit})")


# ==============================================================================
# テスト用
# ==============================================================================

if __name__ == "__main__":
    manager = InventoryManager()
    manager.refresh()
    manager.print_report()
