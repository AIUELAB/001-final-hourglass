"""
Super Total Score Calculator

超総合スコア（0-1,000,000）の計算。
既存の scripts/score/super_total_scorer.py を再利用。
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ..adapters.base import AxisScores
from ..config import MASTER_CSV, PROJECT_ROOT, QUALITY_THRESHOLDS

# 既存スコアラーをインポートパスに追加
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "score"))


@dataclass
class SuperTotalResult:
    """超総合スコア結果"""

    score: float  # 0-1,000,000
    celebrity_norm: float
    fame_norm: float
    quality_norm: float
    historical_norm: float
    passed_gate: bool
    gate_failures: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "super_total_score": self.score,
            "celebrity_norm": self.celebrity_norm,
            "fame_norm": self.fame_norm,
            "quality_norm": self.quality_norm,
            "historical_norm": self.historical_norm,
            "passed_gate": self.passed_gate,
            "gate_failures": self.gate_failures,
        }


class SuperTotalCalculator:
    """
    超総合スコア計算器

    既存の SuperTotalScorer を活用しつつ、ハイブリッドシステム用に統合。
    """

    # 重み配分
    WEIGHTS = {
        "celebrity": 0.30,  # 知名度
        "fame": 0.30,  # 有名度
        "quality": 0.20,  # 品質
        "historical": 0.20,  # 歴史的重要性
    }

    def __init__(self, thresholds: dict[str, float] = None):
        self.thresholds = thresholds or QUALITY_THRESHOLDS.copy()
        self._normalization_params: Optional[dict] = None
        self._load_normalization_params()

    def _load_normalization_params(self) -> None:
        """正規化パラメータを読み込み"""
        params_path = PROJECT_ROOT / "preserved" / "data" / "super_total_norm_params_v1.2.0.json"
        if params_path.exists():
            with open(params_path, encoding="utf-8") as f:
                self._normalization_params = json.load(f)

    def _robust_normalize(self, value: float, median: float, iqr: float) -> float:
        """ロバスト正規化（外れ値に強い）"""
        if iqr == 0:
            return 0.5

        # IQR正規化
        z = (value - median) / iqr

        # シグモイド変換で0-1に収める
        import math

        return 1 / (1 + math.exp(-z))

    def calculate(
        self,
        person_id: str,
        axis_scores: AxisScores,
        master_df: pd.DataFrame = None,
    ) -> SuperTotalResult:
        """
        超総合スコアを計算

        Args:
            person_id: 人物ID
            axis_scores: 7軸スコア
            master_df: マスターDataFrame（オプション）

        Returns:
            SuperTotalResult: 超総合スコア結果
        """
        gate_failures = []

        # 1. 品質ゲートチェック
        min_fd = self.thresholds.get("min_factual_density", 6.0)
        min_gq = self.thresholds.get("min_generation_quality", 6.0)

        if axis_scores.factual_density < min_fd:
            gate_failures.append(f"factual_density < {min_fd}")
        if axis_scores.generation_quality < min_gq:
            gate_failures.append(f"generation_quality < {min_gq}")

        # 2. 人物データ取得
        celebrity_score = 500.0  # デフォルト
        fame_score = 50.0  # デフォルト
        importance_score = 7.0  # デフォルト

        if master_df is None:
            if MASTER_CSV.exists():
                master_df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")

        if master_df is not None and not master_df.empty:
            person_data = master_df[master_df["person_id"] == person_id]
            if not person_data.empty:
                row = person_data.iloc[0]
                celebrity_score = self._safe_float(row.get("celebrity_score"), 500.0)
                fame_score = self._safe_float(row.get("fame_score"), 50.0)
                importance_score = self._safe_float(row.get("importance_score", row.get("historical_impact")), 7.0)

        # 3. 正規化
        params = self._normalization_params or {}

        celebrity_norm = self._robust_normalize(
            celebrity_score,
            params.get("celebrity_median", 500.0),
            params.get("celebrity_iqr", 150.0),
        )

        fame_norm = self._robust_normalize(
            fame_score,
            params.get("fame_median", 50.0),
            params.get("fame_iqr", 15.0),
        )

        # 品質スコア（7軸加重平均）
        quality_raw = axis_scores.weighted_average()
        quality_norm = min(max(quality_raw / 10.0, 0.0), 1.0)

        # 歴史的重要性
        historical_norm = self._robust_normalize(
            importance_score,
            params.get("importance_median", 7.0),
            params.get("importance_iqr", 1.5),
        )

        # 4. 超総合スコア計算
        super_total = (
            celebrity_norm * self.WEIGHTS["celebrity"]
            + fame_norm * self.WEIGHTS["fame"]
            + quality_norm * self.WEIGHTS["quality"]
            + historical_norm * self.WEIGHTS["historical"]
        ) * 1_000_000

        # 5. 最終ゲートチェック
        min_super_total = self.thresholds.get("min_super_total", 300000)
        if super_total < min_super_total:
            gate_failures.append(f"super_total {super_total:.0f} < {min_super_total}")

        return SuperTotalResult(
            score=super_total,
            celebrity_norm=celebrity_norm,
            fame_norm=fame_norm,
            quality_norm=quality_norm,
            historical_norm=historical_norm,
            passed_gate=len(gate_failures) == 0,
            gate_failures=gate_failures,
        )

    def _safe_float(self, value: Any, default: float) -> float:
        """安全にfloatに変換"""
        if value is None or pd.isna(value):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default


def calculate_super_total_for_episode(
    person_id: str,
    axis_scores: AxisScores,
    master_df: pd.DataFrame = None,
) -> float:
    """
    エピソードの超総合スコアを計算（簡易版）

    Args:
        person_id: 人物ID
        axis_scores: 7軸スコア
        master_df: マスターDataFrame

    Returns:
        float: 超総合スコア（0-1,000,000）
    """
    calculator = SuperTotalCalculator()
    result = calculator.calculate(person_id, axis_scores, master_df)
    return result.score
