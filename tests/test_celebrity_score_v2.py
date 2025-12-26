"""
Celebrity Score v2 回帰テスト

テスト観点:
1. スコア範囲: 0-1000に収まること
2. カテゴリ上限: 政治家は700以下
3. 同名曖昧性: 確信度<0.8で半減
4. 重複加算なし: 同じシグナルで同じスコア
5. 外れ値暴走なし: 極端な入力でも1000以下
"""

import pytest

from scripts.fame_score_v3.scorer_v2 import (
    CelebrityScoreResult,
    CelebritySignals,
    assign_ranks_v2,
    calculate_celebrity_score_v2,
)


class TestScoreRange:
    """スコア範囲テスト"""

    def test_score_within_range(self):
        """通常入力で0-1000に収まる"""
        signals = CelebritySignals(
            multi_lang_pv=1000000,
            sitelinks=50,
            inlinks=1000,
            google_hits=10000000,
            episode_count=5,
            llm_quality=7.5,
        )
        result = calculate_celebrity_score_v2(signals)
        assert 0 <= result.score <= 1000

    def test_zero_input(self):
        """全て0でも正常動作"""
        signals = CelebritySignals()
        result = calculate_celebrity_score_v2(signals)
        assert result.score >= 0

    def test_extreme_high_input(self):
        """極端に高い入力でも1000以下"""
        signals = CelebritySignals(
            multi_lang_pv=100000000,  # 1億
            sitelinks=500,
            inlinks=1000000,
            google_hits=10000000000,  # 100億
            episode_count=100,
            llm_quality=10.0,
        )
        result = calculate_celebrity_score_v2(signals)
        assert result.score <= 1000


class TestCategoryCap:
    """カテゴリ上限テスト"""

    def test_politics_cap_700(self):
        """政治家は700上限"""
        signals = CelebritySignals(
            multi_lang_pv=10000000,
            sitelinks=180,
            inlinks=10000,
            google_hits=50000000,
            episode_count=20,
            llm_quality=9.0,
            category="政治・社会",
        )
        result = calculate_celebrity_score_v2(signals)
        assert result.score <= 700
        assert result.category_cap_applied

    def test_anime_cap_700(self):
        """アニメキャラは700上限"""
        signals = CelebritySignals(
            multi_lang_pv=5000000,
            sitelinks=100,
            inlinks=5000,
            google_hits=20000000,
            episode_count=10,
            llm_quality=8.0,
            category="アニメ・漫画・ゲーム",
        )
        result = calculate_celebrity_score_v2(signals)
        assert result.score <= 700

    def test_no_cap_for_science(self):
        """科学者には上限なし"""
        signals = CelebritySignals(
            multi_lang_pv=10000000,
            sitelinks=200,
            inlinks=50000,
            google_hits=100000000,
            episode_count=25,
            llm_quality=9.5,
            category="科学・技術",
        )
        result = calculate_celebrity_score_v2(signals)
        assert not result.category_cap_applied


class TestDisambiguationConfidence:
    """同名曖昧性テスト"""

    def test_low_confidence_halved(self):
        """確信度<0.8でスコア半減"""
        signals_high = CelebritySignals(
            multi_lang_pv=1000000,
            sitelinks=50,
            inlinks=1000,
            episode_count=5,
            llm_quality=7.0,
            disambiguation_confidence=1.0,
        )
        signals_low = CelebritySignals(
            multi_lang_pv=1000000,
            sitelinks=50,
            inlinks=1000,
            episode_count=5,
            llm_quality=7.0,
            disambiguation_confidence=0.5,  # 低確信度
        )

        result_high = calculate_celebrity_score_v2(signals_high)
        result_low = calculate_celebrity_score_v2(signals_low)

        assert result_low.confidence_penalty_applied
        # 生スコアの半分程度になること
        assert abs(result_low.score - result_low.raw_score * 0.5) < 1.0

    def test_confidence_threshold_08(self):
        """確信度0.8境界値"""
        signals_08 = CelebritySignals(
            multi_lang_pv=1000000,
            sitelinks=50,
            inlinks=1000,
            episode_count=5,
            llm_quality=7.0,
            disambiguation_confidence=0.8,  # ちょうど0.8
        )
        signals_079 = CelebritySignals(
            multi_lang_pv=1000000,
            sitelinks=50,
            inlinks=1000,
            episode_count=5,
            llm_quality=7.0,
            disambiguation_confidence=0.79,  # 0.8未満
        )

        result_08 = calculate_celebrity_score_v2(signals_08)
        result_079 = calculate_celebrity_score_v2(signals_079)

        assert not result_08.confidence_penalty_applied  # 0.8はペナルティなし
        assert result_079.confidence_penalty_applied  # 0.79はペナルティあり


class TestDeterminism:
    """決定性テスト"""

    def test_same_input_same_output(self):
        """同じ入力で同じ出力"""
        signals = CelebritySignals(
            multi_lang_pv=1234567,
            sitelinks=42,
            inlinks=789,
            google_hits=98765432,
            episode_count=7,
            llm_quality=6.3,
            category="音楽",
        )

        result1 = calculate_celebrity_score_v2(signals, "P12345678")
        result2 = calculate_celebrity_score_v2(signals, "P12345678")

        assert result1.score == result2.score
        assert result1.raw_score == result2.raw_score


class TestRanking:
    """順位計算テスト"""

    def test_ranking_order(self):
        """スコア降順で順位付け"""
        scores = [
            ("P1", 800.0),
            ("P2", 600.0),
            ("P3", 900.0),
            ("P4", 700.0),
        ]
        ranks = assign_ranks_v2(scores)

        assert ranks["P3"] == 1
        assert ranks["P1"] == 2
        assert ranks["P4"] == 3
        assert ranks["P2"] == 4

    def test_tied_scores_same_rank(self):
        """同スコアは同順位"""
        scores = [
            ("P1", 800.0),
            ("P2", 800.0),
            ("P3", 700.0),
        ]
        ranks = assign_ranks_v2(scores)

        assert ranks["P1"] == 1
        assert ranks["P2"] == 1  # 同順位
        assert ranks["P3"] == 3  # 次は3位
