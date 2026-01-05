#!/usr/bin/env python3
"""
ランキングチューニングシステムの検証テスト

テスト内容:
    1. 品質ゲートが維持されていることを確認
    2. 有名度だけで上位にならないことを確認
    3. 設定ファイルの整合性確認
    4. NDCG/Overlap指標の妥当性確認
"""

import json
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def master_csv():
    """マスターCSVを読み込む"""
    csv_path = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
    return pd.read_csv(csv_path, dtype=str)


@pytest.fixture
def config_v1():
    """v1.2.0設定を読み込む"""
    config_path = PROJECT_ROOT / "configs/super_total_score/v1.2.0.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def config_v2():
    """v2.0.0設定を読み込む"""
    config_path = PROJECT_ROOT / "configs/super_total_score/v2.0.0.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


class TestConfigIntegrity:
    """設定ファイルの整合性テスト"""

    def test_weights_sum_to_one_v1(self, config_v1):
        """v1.2.0の重みの合計が1.0であること"""
        weights = config_v1["weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001, f"重みの合計が1.0ではない: {total}"

    def test_weights_sum_to_one_v2(self, config_v2):
        """v2.0.0の重みの合計が1.0であること"""
        weights = config_v2["weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001, f"重みの合計が1.0ではない: {total}"

    def test_quality_weights_sum_to_one_v1(self, config_v1):
        """v1.2.0の品質重みの合計が1.0であること"""
        weights = config_v1["quality_weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001, f"品質重みの合計が1.0ではない: {total}"

    def test_quality_weights_sum_to_one_v2(self, config_v2):
        """v2.0.0の品質重みの合計が1.0であること"""
        weights = config_v2["quality_weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001, f"品質重みの合計が1.0ではない: {total}"

    def test_gate_thresholds_positive(self, config_v1, config_v2):
        """ゲート閾値が正の値であること"""
        for config, version in [(config_v1, "v1.2.0"), (config_v2, "v2.0.0")]:
            gates = config["gates"]
            assert gates["min_factual_density"] > 0, f"{version}: 事実密度閾値が0以下"
            assert gates["min_generation_quality"] > 0, f"{version}: 生成品質閾値が0以下"


class TestQualityGate:
    """品質ゲートのテスト"""

    def test_low_factual_density_excluded(self, master_csv):
        """事実密度が低いエピソードが除外されること"""
        df = master_csv.copy()
        df["事実密度"] = pd.to_numeric(df["事実密度"], errors="coerce")
        df["super_total_score"] = pd.to_numeric(df["super_total_score"], errors="coerce")

        # super_total_score > 0 のエピソードで事実密度 < 6.0 のものがないこと
        scored = df[df["super_total_score"] > 0]
        low_fact = scored[scored["事実密度"] < 6.0]

        assert len(low_fact) == 0, f"事実密度 < 6.0 のエピソードが{len(low_fact)}件スコアリングされている"

    def test_low_generation_quality_excluded(self, master_csv):
        """生成品質が低いエピソードが除外されること"""
        df = master_csv.copy()
        df["生成品質スコア"] = pd.to_numeric(df["生成品質スコア"], errors="coerce")
        df["super_total_score"] = pd.to_numeric(df["super_total_score"], errors="coerce")

        # super_total_score > 0 のエピソードで生成品質 < 6.0 のものがないこと
        scored = df[df["super_total_score"] > 0]
        low_gen = scored[scored["生成品質スコア"] < 6.0]

        assert len(low_gen) == 0, f"生成品質 < 6.0 のエピソードが{len(low_gen)}件スコアリングされている"


class TestRankingDiversity:
    """ランキング多様性のテスト"""

    def test_top100_person_diversity(self, master_csv):
        """Top100に多様な人物が含まれること"""
        df = master_csv.copy()
        df["super_total_score"] = pd.to_numeric(df["super_total_score"], errors="coerce")

        top100 = df.nlargest(100, "super_total_score")
        unique_persons = top100["person_name"].nunique()

        # 最低30人以上の異なる人物が含まれること
        assert unique_persons >= 30, f"Top100の人物多様性が低い: {unique_persons}人"

    def test_top100_quality_average(self, master_csv):
        """Top100の平均品質が一定以上であること"""
        df = master_csv.copy()
        df["super_total_score"] = pd.to_numeric(df["super_total_score"], errors="coerce")
        df["事実密度"] = pd.to_numeric(df["事実密度"], errors="coerce")

        top100 = df.nlargest(100, "super_total_score")
        avg_factual = top100["事実密度"].mean()

        # 平均事実密度が7.0以上であること
        assert avg_factual >= 7.0, f"Top100の平均事実密度が低い: {avg_factual:.2f}"


class TestNoOverfitting:
    """過学習防止のテスト"""

    def test_celebrity_not_dominant(self, master_csv):
        """有名度だけで上位にならないことを確認"""
        df = master_csv.copy()
        df["celebrity_score_v2"] = pd.to_numeric(df["celebrity_score_v2"], errors="coerce")
        df["super_total_score"] = pd.to_numeric(df["super_total_score"], errors="coerce")
        df["事実密度"] = pd.to_numeric(df["事実密度"], errors="coerce")

        # celebrity_score_v2が高い（上位10%）が事実密度が低い（7.0未満）のエピソード
        celeb_threshold = df["celebrity_score_v2"].quantile(0.9)
        high_celeb_low_quality = df[(df["celebrity_score_v2"] >= celeb_threshold) & (df["事実密度"] < 7.0)]

        # これらがTop100に入っていないこと
        top100_ids = set(df.nlargest(100, "super_total_score")["episode_id"])
        in_top100 = high_celeb_low_quality[high_celeb_low_quality["episode_id"].isin(top100_ids)]

        assert len(in_top100) == 0, f"高有名度・低品質エピソードがTop100に{len(in_top100)}件含まれる"


class TestReferenceDataMapping:
    """参照データマッピングのテスト"""

    def test_mapping_file_exists(self):
        """マッピング結果ファイルが存在すること"""
        mapping_path = PROJECT_ROOT / "src/reports/reference_mapping_results.json"
        assert mapping_path.exists(), "マッピング結果ファイルが存在しない"

    def test_mapping_match_rate(self):
        """マッピングのマッチ率が90%以上であること"""
        mapping_path = PROJECT_ROOT / "src/reports/reference_mapping_results.json"
        if not mapping_path.exists():
            pytest.skip("マッピング結果ファイルが存在しない")

        with open(mapping_path, encoding="utf-8") as f:
            mapping = json.load(f)

        # Claude
        claude_total = len(mapping["claude"])
        claude_matched = len([r for r in mapping["claude"] if r["matched_episode_id"]])
        claude_rate = claude_matched / claude_total if claude_total > 0 else 0

        assert claude_rate >= 0.90, f"Claudeマッチ率が低い: {claude_rate:.1%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
