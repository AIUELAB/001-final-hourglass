#!/usr/bin/env python3
"""
エピソード有名度v6 逆転防止回帰テスト

テスト観点表:
+------------------+----------------------------------------+------------------+
| 観点             | 等価分割                               | 境界値           |
+------------------+----------------------------------------+------------------+
| 村上春樹順位     | EP-000002037が1位                      | 1位 vs 2位       |
| TYPE_MAPPING     | 日本語タイプ→英語変換                  | 全マッピング確認 |
| KEYWORDS拡充     | 「万部」「ベストセラー」がTier2        | キーワード境界   |
| episode_count    | 同一人物で統一                         | 0, 1, 8(飽和)    |
+------------------+----------------------------------------+------------------+
"""

import csv
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.score.episode_fame_v6.config import (
    HISTORICAL_KEYWORDS,
    TYPE_BONUS,
    TYPE_MAPPING,
)
from scripts.score.episode_fame_v6.scorer import EpisodeFameV6Scorer

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


class TestMurakamiInversion:
    """村上春樹問題の回帰テスト"""

    @pytest.fixture
    def murakami_episodes(self):
        """村上春樹のエピソードを取得"""
        if not CSV_PATH.exists():
            pytest.skip("CSVファイルが存在しません")

        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            all_eps = list(reader)

        return [e for e in all_eps if e.get("person_name") == "村上春樹"]

    def test_norwegian_wood_is_top(self, murakami_episodes):
        """EP-000002037（ノルウェイの森1000万部）が村上春樹内で1位"""
        sorted_eps = sorted(
            murakami_episodes,
            key=lambda x: float(x.get("episode_fame_v6") or 0),
            reverse=True,
        )

        top_ep = sorted_eps[0]
        assert (
            top_ep.get("episode_id") == "EP-000002037"
        ), f"EP-000002037が1位であるべき。実際: {top_ep.get('episode_id')} (v6={top_ep.get('episode_fame_v6')})"

    def test_norwegian_wood_score_above_threshold(self, murakami_episodes):
        """EP-000002037のスコアが80点以上"""
        target = next(
            (e for e in murakami_episodes if e.get("episode_id") == "EP-000002037"),
            None,
        )
        assert target is not None, "EP-000002037が見つかりません"

        score = float(target.get("episode_fame_v6") or 0)
        assert score >= 80.0, f"EP-000002037は80点以上であるべき。実際: {score}"


class TestTypeMapping:
    """TYPE_MAPPINGのテスト"""

    def test_all_japanese_types_mapped(self):
        """全ての日本語タイプがマッピングされている"""
        expected_types = ["達成", "転機", "挑戦", "革新", "創業", "復帰", "死去"]
        for jp_type in expected_types:
            assert jp_type in TYPE_MAPPING, f"'{jp_type}'がTYPE_MAPPINGにない"

    def test_mapped_types_have_bonus(self):
        """マッピング先の英語タイプにボーナスが設定されている"""
        for jp_type, en_type in TYPE_MAPPING.items():
            assert en_type in TYPE_BONUS, f"'{jp_type}'→'{en_type}'のボーナスがTYPE_BONUSにない"


class TestHistoricalKeywords:
    """HISTORICAL_KEYWORDSのテスト"""

    def test_sales_keywords_in_tier2(self):
        """販売実績キーワードがTier2に含まれている"""
        tier2 = HISTORICAL_KEYWORDS["tier2"]
        sales_keywords = ["ミリオンセラー", "ベストセラー", "大ヒット", "万部"]
        for kw in sales_keywords:
            assert kw in tier2, f"'{kw}'がHISTORICAL_KEYWORDS tier2にない"


class TestEpisodeCountConsistency:
    """episode_count整合性テスト"""

    @pytest.fixture
    def all_episodes(self):
        """全エピソードを取得"""
        if not CSV_PATH.exists():
            pytest.skip("CSVファイルが存在しません")

        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def test_episode_count_consistent_per_person(self, all_episodes):
        """同一人物のepisode_countが統一されている"""
        from collections import defaultdict

        person_counts = defaultdict(set)
        for ep in all_episodes:
            person_id = ep.get("person_id", "")
            count = ep.get("episode_count", "0")
            if person_id:
                person_counts[person_id].add(count)

        inconsistent = [pid for pid, counts in person_counts.items() if len(counts) > 1]
        assert len(inconsistent) == 0, f"{len(inconsistent)}人でepisode_countが不整合: {inconsistent[:5]}"


class TestScorerIntegration:
    """スコアラー統合テスト"""

    @pytest.fixture
    def scorer(self):
        """スコアラーを初期化"""
        if not CSV_PATH.exists():
            pytest.skip("CSVファイルが存在しません")

        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            all_eps = list(reader)

        return EpisodeFameV6Scorer(all_eps)

    def test_achievement_type_gets_bonus(self, scorer):
        """「達成」タイプにボーナスが適用される"""
        mock_row = {
            "episode_id": "TEST",
            "person_id": "TEST",
            "person_name": "テスト",
            "episode_text": "テストテキスト",
            "episode_type": "達成",
            "episode_count": "5",
            "celebrity_score_v2": "50",
            "sitelinks_count": "50",
            "multi_lang_pv": "1000",
            "memorability_score": "5",
            "empathy_score": "5",
            "surprise_score": "5",
            "generation_quality_score": "5",
            "educational_value": "5",
            "story_quality": "5",
            "factual_density": "5",
        }

        breakdown = scorer.score_episode(mock_row)
        # 達成 → ACHIEVEMENT → +15点
        # historical_impact = 50 + 15 = 65
        assert (
            breakdown.historical_impact >= 65
        ), f"達成タイプのhistorical_impactは65以上であるべき。実際: {breakdown.historical_impact}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
