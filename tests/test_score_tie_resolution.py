#!/usr/bin/env python3
"""
スコア同率解消テスト

テスト対象:
- scripts/score/episode_fame_v6/scorer.py (上限クランプ削除)
- scripts/validation/score_tie_detection_gate.py (同率検出ゲート)

テスト観点:
1. 100.00同率解消
2. 決定論性
3. 数値安定性
"""

import csv
import math
import sys
from collections import Counter
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "validation"))
sys.path.insert(0, str(PROJECT_ROOT))

from score_tie_detection_gate import scan_score_ties, evaluate_thresholds, DEFAULT_THRESHOLDS


class TestScore100Resolution:
    """100.00同率解消テスト"""

    @pytest.fixture
    def master_csv(self):
        return PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    def test_no_score_100_ties(self, master_csv):
        """T1: 100.00同率が0件"""
        with open(master_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count_100 = sum(
                1 for row in reader if row.get("episode_fame_v6") and float(row["episode_fame_v6"]) == 100.0
            )

        assert count_100 == 0, f"100.00同率が{count_100}件存在"

    def test_top200_unique_scores(self, master_csv):
        """T2: 上位200件の最大同率が5件以下"""
        with open(master_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            scores = [float(row["episode_fame_v6"]) for row in reader if row.get("episode_fame_v6")]

        sorted_scores = sorted(scores, reverse=True)
        top200 = sorted_scores[:200]
        counts = Counter(round(s, 2) for s in top200)
        max_tie = max(counts.values()) if counts else 0

        assert max_tie <= 5, f"上位200件の最大同率が{max_tie}件"

    def test_scores_above_100_exist(self, master_csv):
        """100超のスコアが存在することを確認"""
        with open(master_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            max_score = max(float(row["episode_fame_v6"]) for row in reader if row.get("episode_fame_v6"))

        assert max_score > 100, f"最大スコアが{max_score}（100超のスコアがない）"


class TestScoreStability:
    """数値安定性テスト"""

    @pytest.fixture
    def master_csv(self):
        return PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    def test_no_negative_scores(self, master_csv):
        """T4: スコアが0未満にならない"""
        with open(master_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            negative_count = sum(
                1 for row in reader if row.get("episode_fame_v6") and float(row["episode_fame_v6"]) < 0
            )

        assert negative_count == 0, f"負のスコアが{negative_count}件存在"

    def test_no_nan_or_inf(self, master_csv):
        """T5: NaN/Infが存在しない"""
        with open(master_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            invalid_count = 0
            for row in reader:
                v6 = row.get("episode_fame_v6", "")
                if v6:
                    try:
                        score = float(v6)
                        if math.isnan(score) or math.isinf(score):
                            invalid_count += 1
                    except ValueError:
                        invalid_count += 1

        assert invalid_count == 0, f"無効なスコアが{invalid_count}件存在"


class TestScoreTieGate:
    """同率検出ゲートテスト"""

    def test_scan_returns_structure(self):
        """スキャン結果の構造確認"""
        result = scan_score_ties()

        assert "total_episodes" in result
        assert "unique_scores" in result
        assert "score_100_count" in result
        assert "top200_max_tie_size" in result
        assert "total_max_tie_size" in result

    def test_score_100_threshold(self):
        """T6: 100.00同率が閾値を超えない"""
        result = scan_score_ties()
        violations = evaluate_thresholds(result, DEFAULT_THRESHOLDS)

        # CRITICALな違反がないことを確認
        critical_violations = [v for v in violations if v["severity"] == "CRITICAL"]
        assert len(critical_violations) == 0, f"CRITICAL違反: {critical_violations}"

    def test_deterministic_calculation(self):
        """T3: スキャン結果が決定論的"""
        result1 = scan_score_ties()
        result2 = scan_score_ties()

        assert result1["score_100_count"] == result2["score_100_count"]
        assert result1["unique_scores"] == result2["unique_scores"]
        assert result1["total_max_tie_size"] == result2["total_max_tie_size"]


class TestTier1MinimumGuarantee:
    """Tier1最低保証（78.00）のテスト"""

    @pytest.fixture
    def master_csv(self):
        return PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    def test_tier1_floor_exists(self, master_csv):
        """T7: 78.00同率が存在（Tier1最低保証の結果）"""
        with open(master_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count_78 = sum(
                1 for row in reader if row.get("episode_fame_v6") and round(float(row["episode_fame_v6"]), 2) == 78.0
            )

        # 78.00同率は許容される（Tier1最低保証の設計上の結果）
        # ただし、上位ランキング（100超）には影響しない
        assert count_78 > 0, "78.00同率が存在しない（Tier1最低保証が機能していない可能性）"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
