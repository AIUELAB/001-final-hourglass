#!/usr/bin/env python3
"""
test_top_monopoly_gate.py - 上位独占検出ゲートの単体・統合テスト

テスト対象:
1. detect_monopoly_violations - 独占違反検出
2. suggest_removals - 削除候補提案
3. CLI統合テスト

Author: EPUP Validation Team
Date: 2026-02-03
"""

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.top_monopoly_gate import (
    MONOPOLY_LIMITS,
    detect_monopoly_violations,
    get_violation_summary,
    suggest_removals,
)


# =============================================================================
# テスト用フィクスチャ
# =============================================================================


@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成するフィクスチャ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def create_test_csv(temp_dir: Path, episodes: list[dict]) -> Path:
    """
    テスト用CSVファイルを作成

    Args:
        temp_dir: 一時ディレクトリ
        episodes: エピソードのリスト

    Returns:
        作成したCSVファイルのパス
    """
    csv_path = temp_dir / "test_episodes.csv"
    fieldnames = ["episode_id", "person_id", "person_name", "super_total_score"]

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(episodes)

    return csv_path


@pytest.fixture
def csv_single_person_monopoly(temp_dir):
    """
    単一人物がTop20で5件占有するテストデータ
    同一person_idで5件がTop20内に存在
    """
    episodes = []
    # Top20を独占する人物A（5件、スコア1000-996）
    for i in range(5):
        episodes.append({
            "episode_id": f"EP-MONOPOLY-{i:03d}",
            "person_id": "P-MONOPOLY",
            "person_name": "独占太郎",
            "super_total_score": 1000 - i,
        })

    # 他の人物でTop20を埋める（15件、スコア900-886）
    for i in range(15):
        episodes.append({
            "episode_id": f"EP-OTHER-{i:03d}",
            "person_id": f"P-OTHER-{i:03d}",
            "person_name": f"他者{i}",
            "super_total_score": 900 - i,
        })

    return create_test_csv(temp_dir, episodes)


@pytest.fixture
def csv_multiple_persons_monopoly(temp_dir):
    """
    複数人物がTop100で独占するテストデータ
    人物A: 4件（上限2を2件超過）
    人物B: 3件（上限2を1件超過）
    """
    episodes = []

    # 人物A（4件、スコア1000-997）
    for i in range(4):
        episodes.append({
            "episode_id": f"EP-A-{i:03d}",
            "person_id": "P-A",
            "person_name": "人物A",
            "super_total_score": 1000 - i,
        })

    # 人物B（3件、スコア993-991）
    for i in range(3):
        episodes.append({
            "episode_id": f"EP-B-{i:03d}",
            "person_id": "P-B",
            "person_name": "人物B",
            "super_total_score": 993 - i,
        })

    # 他の人物でTop100を埋める（93件、スコア980-888）
    for i in range(93):
        episodes.append({
            "episode_id": f"EP-OTHER-{i:03d}",
            "person_id": f"P-OTHER-{i:03d}",
            "person_name": f"他者{i}",
            "super_total_score": 980 - i,
        })

    return create_test_csv(temp_dir, episodes)


@pytest.fixture
def csv_no_violation(temp_dir):
    """
    違反なしのテストデータ
    全人物がTop20で1件ずつ
    """
    episodes = []
    for i in range(30):
        episodes.append({
            "episode_id": f"EP-{i:03d}",
            "person_id": f"P-{i:03d}",
            "person_name": f"人物{i}",
            "super_total_score": 1000 - i,
        })

    return create_test_csv(temp_dir, episodes)


@pytest.fixture
def csv_exactly_at_limit_top20(temp_dir):
    """
    Top20でちょうど1件の境界値テストデータ
    """
    episodes = []
    for i in range(20):
        episodes.append({
            "episode_id": f"EP-{i:03d}",
            "person_id": f"P-{i:03d}",
            "person_name": f"人物{i}",
            "super_total_score": 1000 - i,
        })

    return create_test_csv(temp_dir, episodes)


@pytest.fixture
def csv_exactly_at_limit_top100(temp_dir):
    """
    Top100でちょうど2件の境界値テストデータ
    同一人物が2件ずつ（上限内）
    """
    episodes = []
    person_idx = 0
    for i in range(100):
        episodes.append({
            "episode_id": f"EP-{i:03d}",
            "person_id": f"P-{person_idx:03d}",
            "person_name": f"人物{person_idx}",
            "super_total_score": 1000 - i,
        })
        # 2件ごとに次の人物へ
        if i % 2 == 1:
            person_idx += 1

    return create_test_csv(temp_dir, episodes)


@pytest.fixture
def csv_one_over_limit_top1000(temp_dir):
    """
    Top1000で4件（上限3を1件超過）のテストデータ
    """
    episodes = []

    # 人物A（4件、スコア1000-997）
    for i in range(4):
        episodes.append({
            "episode_id": f"EP-A-{i:03d}",
            "person_id": "P-A",
            "person_name": "独占太郎",
            "super_total_score": 1000 - i,
        })

    # 他の人物でTop1000を埋める（996件、スコア996-1）
    for i in range(996):
        episodes.append({
            "episode_id": f"EP-OTHER-{i:03d}",
            "person_id": f"P-OTHER-{i:03d}",
            "person_name": f"他者{i}",
            "super_total_score": 996 - i,
        })

    return create_test_csv(temp_dir, episodes)


# =============================================================================
# 基本機能テスト
# =============================================================================


class TestDetectMonopolyViolations:
    """detect_monopoly_violationsのテスト"""

    def test_detect_monopoly_single_person_in_top20(self, csv_single_person_monopoly):
        """同一人物5件がTop20にある場合、4件削除対象として検出"""
        result = detect_monopoly_violations(csv_single_person_monopoly, top_n=20)

        assert result["total_violations"] >= 1

        # Top20での違反を探す
        top20_violations = [
            v for v in result["violations"] if v["tier"] == "Top20"
        ]
        assert len(top20_violations) >= 1

        # 独占太郎の違反を確認
        monopoly_violation = next(
            (v for v in top20_violations if v["person_name"] == "独占太郎"),
            None,
        )
        assert monopoly_violation is not None
        assert monopoly_violation["count"] == 5
        assert monopoly_violation["limit"] == 1  # Top20の上限は1
        assert monopoly_violation["excess"] == 4  # 5 - 1 = 4件超過
        assert len(monopoly_violation["removal_candidates"]) == 4

    def test_detect_monopoly_multiple_persons(self, csv_multiple_persons_monopoly):
        """複数人物の独占を正しく検出"""
        result = detect_monopoly_violations(csv_multiple_persons_monopoly, top_n=100)

        # Top100での違反を探す
        top100_violations = [
            v for v in result["violations"] if v["tier"] == "Top100"
        ]

        # 人物Aと人物Bの両方が検出されることを確認
        person_names = {v["person_name"] for v in top100_violations}
        assert "人物A" in person_names
        assert "人物B" in person_names

        # 人物Aの違反詳細（4件、上限2、超過2）
        violation_a = next(
            (v for v in top100_violations if v["person_name"] == "人物A"),
            None,
        )
        assert violation_a is not None
        assert violation_a["count"] == 4
        assert violation_a["excess"] == 2

        # 人物Bの違反詳細（3件、上限2、超過1）
        violation_b = next(
            (v for v in top100_violations if v["person_name"] == "人物B"),
            None,
        )
        assert violation_b is not None
        assert violation_b["count"] == 3
        assert violation_b["excess"] == 1

    def test_no_violation(self, csv_no_violation):
        """違反なしの正常ケース"""
        result = detect_monopoly_violations(csv_no_violation, top_n=20)

        assert result["total_violations"] == 0
        assert len(result["violations"]) == 0


# =============================================================================
# 境界値テスト
# =============================================================================


class TestBoundaryValues:
    """境界値のテスト"""

    def test_exactly_at_limit_top20(self, csv_exactly_at_limit_top20):
        """Top20でちょうど1件 → 違反なし"""
        result = detect_monopoly_violations(csv_exactly_at_limit_top20, top_n=20)

        # 各人物が1件ずつなので違反なし
        top20_violations = [
            v for v in result["violations"] if v["tier"] == "Top20"
        ]
        assert len(top20_violations) == 0

    def test_exactly_at_limit_top100(self, csv_exactly_at_limit_top100):
        """Top100でちょうど2件 → 違反なし"""
        result = detect_monopoly_violations(csv_exactly_at_limit_top100, top_n=100)

        # 各人物が2件ずつなので違反なし
        top100_violations = [
            v for v in result["violations"] if v["tier"] == "Top100"
        ]
        assert len(top100_violations) == 0

    def test_one_over_limit_top1000(self, csv_one_over_limit_top1000):
        """Top1000で4件 → 1件超過"""
        result = detect_monopoly_violations(csv_one_over_limit_top1000, top_n=1000)

        # Top1000での違反を探す
        top1000_violations = [
            v for v in result["violations"] if v["tier"] == "Top1000"
        ]
        assert len(top1000_violations) >= 1

        # 独占太郎の違反を確認
        monopoly_violation = next(
            (v for v in top1000_violations if v["person_name"] == "独占太郎"),
            None,
        )
        assert monopoly_violation is not None
        assert monopoly_violation["count"] == 4
        assert monopoly_violation["limit"] == 3  # Top1000の上限は3
        assert monopoly_violation["excess"] == 1  # 4 - 3 = 1件超過


# =============================================================================
# suggest_removals テスト
# =============================================================================


class TestSuggestRemovals:
    """suggest_removalsのテスト"""

    def test_suggest_removals_lowest_score_first(self, csv_single_person_monopoly):
        """低スコアから削除候補を提案"""
        result = detect_monopoly_violations(csv_single_person_monopoly, top_n=20)
        removals = suggest_removals(result)

        # 4件の削除候補が提案されることを確認
        assert len(removals) == 4

        # 全ての削除候補が独占太郎のものであることを確認
        for removal in removals:
            assert removal["person_name"] == "独占太郎"
            assert "Top20" in removal["tier"]

        # 削除候補のepisode_idを確認（スコア低い順）
        # EP-MONOPOLY-001, EP-MONOPOLY-002, EP-MONOPOLY-003, EP-MONOPOLY-004
        # （EP-MONOPOLY-000が最高スコアなので残る）
        expected_removals = {"EP-MONOPOLY-001", "EP-MONOPOLY-002", "EP-MONOPOLY-003", "EP-MONOPOLY-004"}
        actual_removals = {r["episode_id"] for r in removals}
        assert actual_removals == expected_removals


# =============================================================================
# get_violation_summary テスト
# =============================================================================


class TestGetViolationSummary:
    """get_violation_summaryのテスト"""

    def test_summary_counts(self, csv_multiple_persons_monopoly):
        """サマリーの集計が正しいことを確認"""
        result = detect_monopoly_violations(csv_multiple_persons_monopoly, top_n=100)
        summary = get_violation_summary(result)

        # 人物Aと人物Bの2人が違反
        assert summary["total_violation_persons"] == 2

        # 超過総数:
        # - Top20: 人物A 4件中3件超過、人物B 3件中2件超過 = 5件
        # - Top100: 人物A 4件中2件超過、人物B 3件中1件超過 = 3件
        # 合計 = 8件
        assert summary["total_excess_episodes"] == 8


# =============================================================================
# CLI統合テスト
# =============================================================================


class TestCLIIntegration:
    """CLI統合テスト"""

    def test_cli_dry_run_returns_zero(self, csv_single_person_monopoly):
        """dry-runは違反があってもexit 0"""
        script_path = PROJECT_ROOT / "scripts/validation/top_monopoly_gate.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--csv",
                str(csv_single_person_monopoly),
                "--top-n",
                "20",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "違反" in result.stdout or "[DRY-RUN]" in result.stdout

    def test_cli_violation_returns_one(self, csv_single_person_monopoly):
        """違反ありはexit 1"""
        script_path = PROJECT_ROOT / "scripts/validation/top_monopoly_gate.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--csv",
                str(csv_single_person_monopoly),
                "--top-n",
                "20",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "違反" in result.stdout

    def test_cli_no_violation_returns_zero(self, csv_no_violation):
        """違反なしはexit 0"""
        script_path = PROJECT_ROOT / "scripts/validation/top_monopoly_gate.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--csv",
                str(csv_no_violation),
                "--top-n",
                "20",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "OK" in result.stdout


# =============================================================================
# MONOPOLY_LIMITS 定数テスト
# =============================================================================


class TestMonopolyLimits:
    """MONOPOLY_LIMITS定数のテスト"""

    def test_limits_values(self):
        """上限値が正しく設定されていることを確認"""
        assert MONOPOLY_LIMITS[20] == 1  # Top20: 最大1件
        assert MONOPOLY_LIMITS[100] == 2  # Top100: 最大2件
        assert MONOPOLY_LIMITS[1000] == 3  # Top1000: 最大3件


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
