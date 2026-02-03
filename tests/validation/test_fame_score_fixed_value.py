#!/usr/bin/env python3
"""
test_fame_score_fixed_value.py - fame_score_v3固定値問題の回帰テスト

fame_score_v3が同一の固定値で大量に設定されている場合を検出する。
この問題は、バッチ処理やキャッシュ処理のバグで発生しうる。

テスト対象:
1. 人物ごとに異なる値が入ること（正常系）
2. 同一値の大量出現検出（異常系）
3. デフォルト値の除外（400.00, 500.00）

Author: EPUP Validation Team
Date: 2026-02-03
"""

import csv
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# テスト用ユーティリティ関数
# =============================================================================


# デフォルト値として除外するスコア
# これらはシステムが意図的に設定するデフォルト値
DEFAULT_SCORES = {400.00, 500.00}


def detect_fixed_value_anomaly(
    csv_path: Path,
    threshold_ratio: float = 0.1,
    threshold_count: int = 50,
    exclude_defaults: bool = True,
) -> dict:
    """
    fame_score_v3の固定値異常を検出する

    Args:
        csv_path: CSVファイルパス
        threshold_ratio: 同一値が全体の何割以上で異常とするか（デフォルト: 10%）
        threshold_count: 同一値が何件以上で異常とするか（デフォルト: 50件）
        exclude_defaults: デフォルト値を除外するか

    Returns:
        dict: 検出結果
            - anomalies: 異常検出された値のリスト
            - value_distribution: 値の出現回数辞書
            - total_records: 総レコード数
            - unique_values: ユニーク値数
    """
    scores = []
    person_scores = {}  # person_id -> fame_score_v3

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("person_id", "")
            score_str = row.get("fame_score_v3", "")

            if not score_str or not person_id:
                continue

            try:
                score = float(score_str)
            except (ValueError, TypeError):
                continue

            # 人物ごとに1回だけカウント
            if person_id not in person_scores:
                person_scores[person_id] = score
                scores.append(score)

    if not scores:
        return {
            "anomalies": [],
            "value_distribution": {},
            "total_records": 0,
            "unique_values": 0,
            "person_count": 0,
        }

    # 値の出現回数をカウント
    value_counts = Counter(scores)
    total_persons = len(person_scores)

    # 異常検出
    anomalies = []
    for value, count in value_counts.items():
        # デフォルト値は除外
        if exclude_defaults and value in DEFAULT_SCORES:
            continue

        ratio = count / total_persons

        # 閾値を超えたら異常
        if ratio >= threshold_ratio and count >= threshold_count:
            anomalies.append(
                {
                    "value": value,
                    "count": count,
                    "ratio": ratio,
                    "is_default": value in DEFAULT_SCORES,
                }
            )

    return {
        "anomalies": sorted(anomalies, key=lambda x: x["count"], reverse=True),
        "value_distribution": dict(value_counts.most_common(20)),
        "total_records": len(scores),
        "unique_values": len(value_counts),
        "person_count": total_persons,
    }


def detect_multi_person_fixed_value(
    csv_path: Path,
    min_persons: int = 10,
    exclude_defaults: bool = True,
) -> dict:
    """
    複数人物に同一fame_score_v3が設定されているケースを検出

    Args:
        csv_path: CSVファイルパス
        min_persons: 何人以上同一スコアで異常とするか
        exclude_defaults: デフォルト値を除外するか

    Returns:
        dict: 検出結果
    """
    # スコア -> 人物名リスト
    score_to_persons: dict[float, list[str]] = {}

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("person_id", "")
            person_name = row.get("person_name", "")
            score_str = row.get("fame_score_v3", "")

            if not score_str or not person_id:
                continue

            try:
                score = float(score_str)
            except (ValueError, TypeError):
                continue

            # デフォルト値は除外
            if exclude_defaults and score in DEFAULT_SCORES:
                continue

            if score not in score_to_persons:
                score_to_persons[score] = []

            # 同じ人物は1回だけ
            if person_name not in score_to_persons[score]:
                score_to_persons[score].append(person_name)

    # 異常検出
    violations = []
    for score, persons in score_to_persons.items():
        if len(persons) >= min_persons:
            violations.append(
                {
                    "score": score,
                    "person_count": len(persons),
                    "sample_persons": persons[:5],  # 最初の5人をサンプル
                }
            )

    return {
        "violations": sorted(violations, key=lambda x: x["person_count"], reverse=True),
        "total_unique_scores": len(score_to_persons),
    }


# =============================================================================
# テスト用フィクスチャ
# =============================================================================


@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成するフィクスチャ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def create_test_csv(temp_dir: Path, rows: list[dict]) -> Path:
    """テスト用CSVを作成"""
    csv_path = temp_dir / "test_episodes.csv"
    fieldnames = ["episode_id", "person_id", "person_name", "fame_score_v3"]

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


@pytest.fixture
def csv_normal_distribution(temp_dir):
    """正常な分布のテストデータ（異なる値が入っている）"""
    rows = []
    for i in range(100):
        rows.append(
            {
                "episode_id": f"EP-{i:03d}",
                "person_id": f"P-{i:03d}",
                "person_name": f"人物{i}",
                "fame_score_v3": 100 + i * 5,  # 100, 105, 110, ... 595
            }
        )
    return create_test_csv(temp_dir, rows)


@pytest.fixture
def csv_fixed_value_anomaly(temp_dir):
    """固定値異常のテストデータ（同一値が大量）"""
    rows = []
    # 70件が同じスコア（70%）
    for i in range(70):
        rows.append(
            {
                "episode_id": f"EP-FIXED-{i:03d}",
                "person_id": f"P-FIXED-{i:03d}",
                "person_name": f"固定値人物{i}",
                "fame_score_v3": 555.55,  # 同一値
            }
        )
    # 30件は異なるスコア
    for i in range(30):
        rows.append(
            {
                "episode_id": f"EP-NORMAL-{i:03d}",
                "person_id": f"P-NORMAL-{i:03d}",
                "person_name": f"正常人物{i}",
                "fame_score_v3": 100 + i * 10,
            }
        )
    return create_test_csv(temp_dir, rows)


@pytest.fixture
def csv_multi_person_fixed(temp_dir):
    """複数人物に同一スコアが設定されたテストデータ"""
    rows = []
    # 15人が同じスコア
    for i in range(15):
        rows.append(
            {
                "episode_id": f"EP-SAME-{i:03d}",
                "person_id": f"P-SAME-{i:03d}",
                "person_name": f"同一スコア人物{i}",
                "fame_score_v3": 777.77,
            }
        )
    # 残りは異なるスコア
    for i in range(35):
        rows.append(
            {
                "episode_id": f"EP-DIFF-{i:03d}",
                "person_id": f"P-DIFF-{i:03d}",
                "person_name": f"異なるスコア人物{i}",
                "fame_score_v3": 100 + i * 5,
            }
        )
    return create_test_csv(temp_dir, rows)


@pytest.fixture
def csv_with_defaults(temp_dir):
    """デフォルト値を含むテストデータ"""
    rows = []
    # 60件がデフォルト値400.00
    for i in range(60):
        rows.append(
            {
                "episode_id": f"EP-DEF400-{i:03d}",
                "person_id": f"P-DEF400-{i:03d}",
                "person_name": f"デフォルト400人物{i}",
                "fame_score_v3": 400.00,
            }
        )
    # 20件がデフォルト値500.00
    for i in range(20):
        rows.append(
            {
                "episode_id": f"EP-DEF500-{i:03d}",
                "person_id": f"P-DEF500-{i:03d}",
                "person_name": f"デフォルト500人物{i}",
                "fame_score_v3": 500.00,
            }
        )
    # 20件は正常値
    for i in range(20):
        rows.append(
            {
                "episode_id": f"EP-NORMAL-{i:03d}",
                "person_id": f"P-NORMAL-{i:03d}",
                "person_name": f"正常人物{i}",
                "fame_score_v3": 100 + i * 20,
            }
        )
    return create_test_csv(temp_dir, rows)


@pytest.fixture
def csv_empty(temp_dir):
    """空のテストデータ"""
    csv_path = temp_dir / "empty.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["episode_id", "person_id", "person_name", "fame_score_v3"],
        )
        writer.writeheader()
    return csv_path


@pytest.fixture
def csv_single_record(temp_dir):
    """1件のみのテストデータ"""
    rows = [
        {
            "episode_id": "EP-SINGLE-001",
            "person_id": "P-SINGLE-001",
            "person_name": "単独人物",
            "fame_score_v3": 500.00,
        }
    ]
    return create_test_csv(temp_dir, rows)


@pytest.fixture
def csv_threshold_boundary(temp_dir):
    """閾値境界のテストデータ（ちょうど10%）"""
    rows = []
    # 10件が同じスコア（100件中10件 = ちょうど10%）
    for i in range(10):
        rows.append(
            {
                "episode_id": f"EP-BOUNDARY-{i:03d}",
                "person_id": f"P-BOUNDARY-{i:03d}",
                "person_name": f"境界人物{i}",
                "fame_score_v3": 888.88,
            }
        )
    # 90件は異なるスコア
    for i in range(90):
        rows.append(
            {
                "episode_id": f"EP-NORMAL-{i:03d}",
                "person_id": f"P-NORMAL-{i:03d}",
                "person_name": f"正常人物{i}",
                "fame_score_v3": 100 + i,
            }
        )
    return create_test_csv(temp_dir, rows)


# =============================================================================
# 正常系テスト
# =============================================================================


class TestNormalCases:
    """正常系テスト"""

    def test_different_values_per_person(self, csv_normal_distribution):
        """人物ごとに異なる値が入ること"""
        result = detect_fixed_value_anomaly(csv_normal_distribution)

        # 異常が検出されないこと
        assert len(result["anomalies"]) == 0, f"異常が検出されました: {result['anomalies']}"

        # ユニーク値数がレコード数と同じ（全員異なる値）
        assert result["unique_values"] == result["total_records"]

    def test_normal_distribution_no_anomaly(self, csv_normal_distribution):
        """正常な分布では異常検出されないこと"""
        result = detect_fixed_value_anomaly(csv_normal_distribution)

        # 異常なし
        assert len(result["anomalies"]) == 0

        # 統計情報の確認
        assert result["total_records"] == 100
        assert result["person_count"] == 100


# =============================================================================
# 異常系テスト
# =============================================================================


class TestAnomalyCases:
    """異常系テスト"""

    def test_detect_fixed_value_anomaly(self, csv_fixed_value_anomaly):
        """同一値が大量に出現した場合に検出"""
        result = detect_fixed_value_anomaly(
            csv_fixed_value_anomaly,
            threshold_ratio=0.1,
            threshold_count=50,
        )

        # 異常が検出されること
        assert len(result["anomalies"]) >= 1, "固定値異常が検出されませんでした"

        # 555.55が検出されていること
        detected_values = [a["value"] for a in result["anomalies"]]
        assert 555.55 in detected_values, f"555.55が検出されていません: {detected_values}"

        # 検出された異常の詳細確認
        anomaly = next(a for a in result["anomalies"] if a["value"] == 555.55)
        assert anomaly["count"] == 70
        assert anomaly["ratio"] == 0.7  # 70%

    def test_detect_multi_person_fixed_value(self, csv_multi_person_fixed):
        """複数人物に同一値が設定された場合に検出"""
        result = detect_multi_person_fixed_value(
            csv_multi_person_fixed,
            min_persons=10,
        )

        # 違反が検出されること
        assert len(result["violations"]) >= 1, "複数人物同一スコア違反が検出されませんでした"

        # 777.77が検出されていること
        detected_scores = [v["score"] for v in result["violations"]]
        assert 777.77 in detected_scores, f"777.77が検出されていません: {detected_scores}"

        # 検出された違反の詳細確認
        violation = next(v for v in result["violations"] if v["score"] == 777.77)
        assert violation["person_count"] == 15


# =============================================================================
# 境界値テスト
# =============================================================================


class TestBoundaryValues:
    """境界値テスト"""

    def test_empty_csv(self, csv_empty):
        """空のCSVで例外が発生しないこと"""
        result = detect_fixed_value_anomaly(csv_empty)

        # エラーなく結果が返ること
        assert result["anomalies"] == []
        assert result["total_records"] == 0
        assert result["unique_values"] == 0
        assert result["person_count"] == 0

    def test_single_record(self, csv_single_record):
        """1件のみでも正常動作"""
        result = detect_fixed_value_anomaly(csv_single_record)

        # エラーなく結果が返ること
        assert result["total_records"] == 1
        assert result["unique_values"] == 1
        assert result["person_count"] == 1

        # 1件では閾値に達しないため異常なし
        assert len(result["anomalies"]) == 0

    def test_threshold_boundary(self, csv_threshold_boundary):
        """閾値ちょうどの場合の挙動"""
        # ちょうど10%（threshold_ratio=0.1）
        # threshold_count=10 としてテスト
        result = detect_fixed_value_anomaly(
            csv_threshold_boundary,
            threshold_ratio=0.1,
            threshold_count=10,  # ちょうど10件
        )

        # 閾値ちょうどの場合は検出される（>=）
        assert len(result["anomalies"]) >= 1, "閾値ちょうどで検出されませんでした"

        # 888.88が検出されていること
        detected_values = [a["value"] for a in result["anomalies"]]
        assert 888.88 in detected_values

    def test_threshold_below_boundary(self, csv_threshold_boundary):
        """閾値未満の場合は検出されない"""
        # threshold_count=11 とすると10件では足りない
        result = detect_fixed_value_anomaly(
            csv_threshold_boundary,
            threshold_ratio=0.1,
            threshold_count=11,  # 10件では不足
        )

        # 閾値未満なので検出されない
        anomaly_values = [a["value"] for a in result["anomalies"]]
        assert 888.88 not in anomaly_values, "閾値未満で検出されてしまいました"


# =============================================================================
# デフォルト値除外テスト
# =============================================================================


class TestDefaultExclusion:
    """デフォルト値除外テスト"""

    def test_exclude_defaults(self, csv_with_defaults):
        """400.00, 500.00が除外されること"""
        # デフォルト値除外あり
        result = detect_fixed_value_anomaly(
            csv_with_defaults,
            threshold_ratio=0.1,
            threshold_count=10,
            exclude_defaults=True,
        )

        # 400.00, 500.00は検出されない
        detected_values = [a["value"] for a in result["anomalies"]]
        assert 400.00 not in detected_values, "デフォルト値400.00が除外されていません"
        assert 500.00 not in detected_values, "デフォルト値500.00が除外されていません"

    def test_include_defaults(self, csv_with_defaults):
        """デフォルト値除外なしの場合は検出される"""
        # デフォルト値除外なし
        result = detect_fixed_value_anomaly(
            csv_with_defaults,
            threshold_ratio=0.1,
            threshold_count=10,
            exclude_defaults=False,
        )

        # 400.00は検出される（60件/100件 = 60%）
        detected_values = [a["value"] for a in result["anomalies"]]
        assert 400.00 in detected_values, "デフォルト値400.00が検出されませんでした"

    def test_multi_person_exclude_defaults(self, csv_with_defaults):
        """複数人物検出でもデフォルト値が除外されること"""
        result = detect_multi_person_fixed_value(
            csv_with_defaults,
            min_persons=10,
            exclude_defaults=True,
        )

        # 400.00, 500.00は検出されない
        detected_scores = [v["score"] for v in result["violations"]]
        assert 400.00 not in detected_scores, "デフォルト値400.00が除外されていません"
        assert 500.00 not in detected_scores, "デフォルト値500.00が除外されていません"


# =============================================================================
# 本番データ回帰テスト
# =============================================================================


class TestProductionDataRegression:
    """本番データに対する回帰テスト"""

    @pytest.fixture
    def master_csv_path(self):
        """本番マスターCSVのパス"""
        csv_path = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
        if not csv_path.exists():
            pytest.skip(f"マスターCSVが見つかりません: {csv_path}")
        return csv_path

    def test_no_fixed_value_anomaly_in_production(self, master_csv_path):
        """本番データに固定値異常がないこと"""
        result = detect_fixed_value_anomaly(
            master_csv_path,
            threshold_ratio=0.05,  # 5%以上で異常
            threshold_count=100,  # 100件以上
            exclude_defaults=True,
        )

        # 異常がないこと
        anomalies = result["anomalies"]
        if anomalies:
            anomaly_details = [(a["value"], a["count"], f"{a['ratio'] * 100:.1f}%") for a in anomalies]
            pytest.fail(f"本番データに固定値異常が検出されました: {anomaly_details}")

    def test_no_multi_person_fixed_score_in_production(self, master_csv_path):
        """本番データに複数人物同一スコア問題がないこと"""
        result = detect_multi_person_fixed_value(
            master_csv_path,
            min_persons=20,  # 20人以上同一スコアで異常
            exclude_defaults=True,
        )

        # 違反がないこと
        violations = result["violations"]
        if violations:
            violation_details = [(v["score"], v["person_count"], v["sample_persons"][:3]) for v in violations]
            pytest.fail(f"本番データに複数人物同一スコア問題が検出されました: {violation_details}")

    def test_sufficient_unique_values(self, master_csv_path):
        """本番データに十分なユニーク値があること"""
        result = detect_fixed_value_anomaly(
            master_csv_path,
            exclude_defaults=True,
        )

        # 人物数に対して十分なユニーク値があること
        # 最低でも人物数の50%以上のユニーク値が期待される
        if result["person_count"] > 0:
            unique_ratio = result["unique_values"] / result["person_count"]
            assert unique_ratio >= 0.5, (
                f"ユニーク値の割合が低すぎます: {result['unique_values']}/{result['person_count']} "
                f"({unique_ratio * 100:.1f}%) - 固定値問題の可能性"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
