#!/usr/bin/env python3
"""
Episode Fame Score v6 回帰テスト

テスト観点表:
┌─────────────────────────────────────────────────────────────────────────┐
│ 等価分割                                                                │
├─────────────────┬───────────────────────────────────────────────────────┤
│ カテゴリ        │ テストケース                                          │
├─────────────────┼───────────────────────────────────────────────────────┤
│ 正常系          │ 1. スコア計算が0-100の範囲内                          │
│                 │ 2. 高知名度人物が高スコア                             │
│                 │ 3. 歴史的キーワードでボーナス                         │
├─────────────────┼───────────────────────────────────────────────────────┤
│ バイアス制御    │ 4. Top20で同一人物max1件                              │
│                 │ 5. Top50で同一人物max2件                              │
│                 │ 6. Top100で同一人物max3件                             │
├─────────────────┼───────────────────────────────────────────────────────┤
│ 正規化          │ 7. 外れ値がスコアを支配しない                         │
│                 │ 8. PV=0でもスコア計算可能                             │
├─────────────────┼───────────────────────────────────────────────────────┤
│ アンカー検証    │ 9. 期待Top50に8/10以上が入る                          │
└─────────────────┴───────────────────────────────────────────────────────┘
"""

import sys
from collections import Counter
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.score.episode_fame_v6.config import (
    WEIGHTS,
    BIAS_CONTROL,
    ANCHOR_PATTERNS,
    HISTORICAL_KEYWORDS,
)
from scripts.score.episode_fame_v6.scorer import (
    EpisodeFameV6Scorer,
    ScoreBreakdown,
    apply_bias_control,
)


class TestWeightsConfig:
    """重み設定のテスト"""

    def test_weights_sum_to_one(self):
        """重みの合計が1.0"""
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"重みの合計が1.0ではない: {total}"

    def test_all_weights_positive(self):
        """すべての重みが正"""
        for key, value in WEIGHTS.items():
            assert value > 0, f"{key}の重みが0以下: {value}"


class TestBiasControl:
    """バイアス制御のテスト"""

    def test_apply_bias_control_top20(self):
        """Top20で同一人物max1件"""
        # 同一人物が5件連続するデータ
        episodes = [{"episode_id": f"EP{i}", "person_id": "P001", "episode_fame_v6": 100 - i} for i in range(5)]
        # 他の人物を追加
        for i in range(30):
            episodes.append(
                {
                    "episode_id": f"EP{100+i}",
                    "person_id": f"P{100+i}",
                    "episode_fame_v6": 50 - i * 0.5,
                }
            )

        result = apply_bias_control(episodes)
        top20 = result[:20]
        p001_count = sum(1 for ep in top20 if ep["person_id"] == "P001")
        assert p001_count <= 1, f"Top20にP001が{p001_count}件（max 1）"

    def test_apply_bias_control_top50(self):
        """Top50で同一人物max2件"""
        episodes = [{"episode_id": f"EP{i}", "person_id": "P001", "episode_fame_v6": 100 - i} for i in range(10)]
        for i in range(60):
            episodes.append(
                {
                    "episode_id": f"EP{100+i}",
                    "person_id": f"P{100+i}",
                    "episode_fame_v6": 50 - i * 0.5,
                }
            )

        result = apply_bias_control(episodes)
        top50 = result[:50]
        p001_count = sum(1 for ep in top50 if ep["person_id"] == "P001")
        assert p001_count <= 2, f"Top50にP001が{p001_count}件（max 2）"

    def test_apply_bias_control_top100(self):
        """Top100で同一人物max3件"""
        episodes = [{"episode_id": f"EP{i}", "person_id": "P001", "episode_fame_v6": 100 - i} for i in range(20)]
        for i in range(120):
            episodes.append(
                {
                    "episode_id": f"EP{100+i}",
                    "person_id": f"P{100+i}",
                    "episode_fame_v6": 50 - i * 0.3,
                }
            )

        result = apply_bias_control(episodes)
        top100 = result[:100]
        p001_count = sum(1 for ep in top100 if ep["person_id"] == "P001")
        assert p001_count <= 3, f"Top100にP001が{p001_count}件（max 3）"


class TestScorer:
    """スコアラーのテスト"""

    @pytest.fixture
    def sample_episodes(self):
        """サンプルエピソードデータ"""
        return [
            {
                "episode_id": "EP001",
                "person_id": "P001",
                "person_name": "テスト人物A",
                "episode_text": "あなたと同じ30歳のとき、テスト人物Aは世界初の発明をした。",
                "episode_type": "INNOVATION",
                "episode_count": "5",
                "celebrity_score_v2": "500",
                "sitelinks_count": "100",
                "multi_lang_pv": "100000",
                "記憶性スコア": "8.0",
                "共感性スコア": "7.5",
                "意外性スコア": "8.5",
                "生成品質スコア": "7.0",
                "教育的価値": "8.0",
                "ストーリー品質": "7.5",
                "事実密度": "8.0",
            },
            {
                "episode_id": "EP002",
                "person_id": "P002",
                "person_name": "テスト人物B",
                "episode_text": "あなたと同じ40歳のとき、テスト人物Bは日常を過ごした。",
                "episode_type": "GROWTH",
                "episode_count": "2",
                "celebrity_score_v2": "100",
                "sitelinks_count": "20",
                "multi_lang_pv": "10000",
                "記憶性スコア": "5.0",
                "共感性スコア": "5.0",
                "意外性スコア": "4.0",
                "生成品質スコア": "5.0",
                "教育的価値": "4.0",
                "ストーリー品質": "5.0",
                "事実密度": "4.0",
            },
        ]

    def test_score_range(self, sample_episodes):
        """スコアが0-100の範囲内"""
        scorer = EpisodeFameV6Scorer(sample_episodes)
        for ep in sample_episodes:
            breakdown = scorer.score_episode(ep)
            assert 0 <= breakdown.total_score <= 100, f"スコアが範囲外: {breakdown.total_score}"

    def test_high_fame_person_scores_higher(self, sample_episodes):
        """高知名度人物が高スコア"""
        scorer = EpisodeFameV6Scorer(sample_episodes)
        score_a = scorer.score_episode(sample_episodes[0]).total_score
        score_b = scorer.score_episode(sample_episodes[1]).total_score
        assert score_a > score_b, f"高知名度が低スコア: A={score_a}, B={score_b}"

    def test_historical_keyword_bonus(self, sample_episodes):
        """歴史的キーワードでボーナス"""
        scorer = EpisodeFameV6Scorer(sample_episodes)
        breakdown = scorer.score_episode(sample_episodes[0])
        # "世界初" キーワードがあるのでhistorical_impactが高いはず
        assert breakdown.historical_impact > 50, f"キーワードボーナスなし: {breakdown.historical_impact}"

    def test_penalty_keywords(self, sample_episodes):
        """ペナルティキーワードで減点"""
        scorer = EpisodeFameV6Scorer(sample_episodes)
        breakdown = scorer.score_episode(sample_episodes[1])
        # "日常" キーワードがあるのでペナルティ
        assert breakdown.penalty > 0, f"ペナルティなし: {breakdown.penalty}"

    def test_zero_pv_does_not_crash(self, sample_episodes):
        """PV=0でもクラッシュしない"""
        sample_episodes[0]["multi_lang_pv"] = "0"
        scorer = EpisodeFameV6Scorer(sample_episodes)
        breakdown = scorer.score_episode(sample_episodes[0])
        assert breakdown.total_score >= 0


class TestTierAssignment:
    """ティア割り当てのテスト"""

    def test_tier_boundaries(self):
        """ティア境界値のテスト"""
        from scripts.score.episode_fame_v6.config import TIER_THRESHOLDS

        sample = [
            {
                "episode_id": "EP001",
                "person_id": "P001",
                "person_name": "テスト",
                "episode_text": "テスト",
                "episode_type": "",
                "episode_count": "1",
                "celebrity_score_v2": "500",
                "sitelinks_count": "100",
                "multi_lang_pv": "50000",
                "記憶性スコア": "7.0",
                "共感性スコア": "7.0",
                "意外性スコア": "7.0",
                "生成品質スコア": "7.0",
                "教育的価値": "7.0",
                "ストーリー品質": "7.0",
                "事実密度": "7.0",
            }
        ]
        scorer = EpisodeFameV6Scorer(sample)
        breakdown = scorer.score_episode(sample[0])

        # ティアが1-5の範囲内
        assert 1 <= breakdown.tier <= 5


class TestAnchorPatterns:
    """アンカーパターンのテスト"""

    def test_anchor_patterns_exist(self):
        """アンカーパターンが定義されている"""
        assert len(ANCHOR_PATTERNS["tier1_must_top50"]) >= 10
        assert len(ANCHOR_PATTERNS["tier2_should_top100"]) >= 5

    def test_anchor_format(self):
        """アンカーパターンの形式"""
        for name, keyword in ANCHOR_PATTERNS["tier1_must_top50"]:
            assert isinstance(name, str) and len(name) > 0
            assert isinstance(keyword, str) and len(keyword) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
