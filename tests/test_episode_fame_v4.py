"""
Episode Fame Score v4 テスト
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.score.episode_fame_v4.scorer import (
    EpisodeFameSignals,
    EpisodeFameResult,
    calculate_episode_fame_v4,
    calculate_tier,
    calculate_llm_component,
    calculate_keyword_component,
    calculate_type_component,
    calculate_person_component,
)
from scripts.score.episode_fame_v4.config import TIER_THRESHOLDS


class TestScoreRange:
    """スコア範囲テスト"""

    def test_score_within_0_100(self):
        """通常入力で0-100に収まる"""
        signals = EpisodeFameSignals(
            llm_memorability=6.5,
            llm_empathy=5.5,
            llm_surprise=5.0,
            llm_generation_quality=8.0,
            llm_educational_value=6.0,
            llm_story_quality=5.5,
            llm_factual_density=7.0,
            episode_type="ACHIEVEMENT",
            person_fame_score=500,
        )
        result = calculate_episode_fame_v4(signals)
        assert 0 <= result.score <= 100

    def test_zero_input(self):
        """全て0でも正常動作"""
        signals = EpisodeFameSignals()
        result = calculate_episode_fame_v4(signals)
        assert result.score >= 0
        assert result.tier >= 1

    def test_extreme_high_input(self):
        """極端に高い入力でも100以下"""
        signals = EpisodeFameSignals(
            llm_memorability=10.0,
            llm_empathy=10.0,
            llm_surprise=10.0,
            llm_generation_quality=10.0,
            llm_educational_value=10.0,
            llm_story_quality=10.0,
            llm_factual_density=10.0,
            episode_text="世界初 ノーベル賞 オリンピック 金メダル",
            episode_type="ACHIEVEMENT",
            person_fame_score=1000,
        )
        result = calculate_episode_fame_v4(signals)
        assert result.score <= 100

    def test_negative_values_handled(self):
        """負の値でもエラーにならない"""
        signals = EpisodeFameSignals(
            llm_memorability=-5.0,
            person_fame_score=-100,
        )
        result = calculate_episode_fame_v4(signals)
        assert result.score >= 0


class TestTierCalculation:
    """ティア計算テスト"""

    @pytest.mark.parametrize(
        "score,expected_tier",
        [
            (95, 5),
            (90, 5),
            (89, 4),
            (75, 4),
            (74, 3),
            (60, 3),
            (59, 2),
            (45, 2),
            (44, 1),
            (0, 1),
        ],
    )
    def test_tier_boundaries(self, score, expected_tier):
        """ティア境界値"""
        assert calculate_tier(score) == expected_tier


class TestLLMComponent:
    """LLMコンポーネントテスト"""

    def test_all_zeros(self):
        """全て0で0を返す"""
        signals = EpisodeFameSignals()
        score = calculate_llm_component(signals)
        assert score == 0.0

    def test_all_tens(self):
        """全て10で100を返す"""
        signals = EpisodeFameSignals(
            llm_memorability=10.0,
            llm_empathy=10.0,
            llm_surprise=10.0,
            llm_generation_quality=10.0,
            llm_educational_value=10.0,
            llm_story_quality=10.0,
            llm_factual_density=10.0,
        )
        score = calculate_llm_component(signals)
        assert score == 100.0

    def test_memorability_highest_weight(self):
        """memorability_scoreが最も影響"""
        base = EpisodeFameSignals(
            llm_memorability=5.0,
            llm_surprise=5.0,
        )
        high_mem = EpisodeFameSignals(
            llm_memorability=10.0,
            llm_surprise=5.0,
        )
        high_surp = EpisodeFameSignals(
            llm_memorability=5.0,
            llm_surprise=10.0,
        )

        base_score = calculate_llm_component(base)
        mem_score = calculate_llm_component(high_mem)
        surp_score = calculate_llm_component(high_surp)

        # 記憶性の差分 > 意外性の差分
        mem_diff = mem_score - base_score
        surp_diff = surp_score - base_score
        assert mem_diff > surp_diff


class TestKeywordComponent:
    """キーワードコンポーネントテスト"""

    def test_no_keywords(self):
        """キーワードなしで基準点"""
        score, keywords = calculate_keyword_component("特筆すべきエピソード")
        assert score == 50.0
        assert keywords == []

    def test_historical_keywords_bonus(self):
        """歴史的キーワードでボーナス"""
        score_no, _ = calculate_keyword_component("普通のエピソード")
        score_with, keywords = calculate_keyword_component("世界初の偉業を達成")

        assert score_with > score_no
        assert "世界初" in keywords

    def test_multiple_keywords(self):
        """複数キーワードで累積"""
        score1, kw1 = calculate_keyword_component("世界初")
        score2, kw2 = calculate_keyword_component("世界初 ノーベル賞 金メダル")

        assert score2 > score1
        assert len(kw2) > len(kw1)

    def test_keyword_bonus_capped(self):
        """キーワードボーナス上限"""
        # 多数のキーワードを含むテキスト
        text = "日本初 世界初 ノーベル賞 オリンピック 金メダル 革命 発明 代表作 傑作 名作"
        score, _ = calculate_keyword_component(text)
        # 上限25 + 基準50 = 75
        assert score <= 75

    def test_personal_keywords_penalty(self):
        """個人的キーワードでペナルティ"""
        score_normal, _ = calculate_keyword_component("偉大な業績")
        score_personal, _ = calculate_keyword_component("家族と入院した日々")

        assert score_personal < score_normal


class TestTypeComponent:
    """タイプコンポーネントテスト"""

    def test_no_type(self):
        """タイプなしで基準点"""
        score = calculate_type_component("")
        assert score == 50.0

    def test_achievement_bonus(self):
        """ACHIEVEMENTでボーナス"""
        score_none = calculate_type_component("")
        score_ach = calculate_type_component("ACHIEVEMENT", factual_density=5.0)

        assert score_ach > score_none

    def test_fact_density_adjustment(self):
        """factual_densityによる補正"""
        score_high = calculate_type_component("ACHIEVEMENT", factual_density=8.0)
        score_low = calculate_type_component("ACHIEVEMENT", factual_density=2.0)

        assert score_high > score_low

    def test_case_insensitive(self):
        """大文字小文字を区別しない"""
        score_upper = calculate_type_component("ACHIEVEMENT")
        score_lower = calculate_type_component("achievement")

        assert score_upper == score_lower


class TestPersonComponent:
    """人物知名度コンポーネントテスト"""

    def test_zero_fame(self):
        """知名度0で0を返す"""
        score = calculate_person_component(0)
        assert score == 0.0

    def test_max_fame(self):
        """知名度1000で100を返す"""
        score = calculate_person_component(1000)
        assert score == 100.0

    def test_mid_fame(self):
        """知名度500で50を返す"""
        score = calculate_person_component(500)
        assert score == 50.0

    def test_over_max_capped(self):
        """上限超えても100以下"""
        score = calculate_person_component(1500)
        assert score <= 100.0


class TestDeterminism:
    """決定性テスト"""

    def test_same_input_same_output(self):
        """同じ入力で同じ出力"""
        signals = EpisodeFameSignals(
            llm_memorability=6.24,
            llm_empathy=5.44,
            llm_surprise=4.69,
            llm_generation_quality=8.30,
            llm_educational_value=5.83,
            llm_story_quality=5.59,
            llm_factual_density=7.47,
            episode_text="テスト用エピソード",
            episode_type="ACHIEVEMENT",
            person_fame_score=500,
        )

        result1 = calculate_episode_fame_v4(signals, "EP-001")
        result2 = calculate_episode_fame_v4(signals, "EP-001")

        assert result1.score == result2.score
        assert result1.tier == result2.tier


class TestResultStructure:
    """結果構造テスト"""

    def test_result_has_required_fields(self):
        """結果に必要なフィールドがある"""
        signals = EpisodeFameSignals()
        result = calculate_episode_fame_v4(signals)

        assert hasattr(result, "score")
        assert hasattr(result, "tier")
        assert hasattr(result, "components")
        assert hasattr(result, "reason")

    def test_components_has_breakdown(self):
        """componentsに内訳がある"""
        signals = EpisodeFameSignals(
            llm_memorability=7.0,
            episode_text="世界初の発見",
            episode_type="DISCOVERY",
            person_fame_score=600,
        )
        result = calculate_episode_fame_v4(signals)

        assert "llm" in result.components
        assert "keyword" in result.components
        assert "type" in result.components
        assert "person" in result.components


class TestIntegration:
    """統合テスト"""

    def test_famous_episode_high_score(self):
        """有名なエピソードは高スコア"""
        signals = EpisodeFameSignals(
            llm_memorability=9.0,
            llm_empathy=7.0,
            llm_surprise=8.5,
            llm_generation_quality=8.0,
            llm_educational_value=8.0,
            llm_story_quality=8.0,
            llm_factual_density=9.0,
            episode_text="ノーベル賞を受賞した画期的な発見",
            episode_type="ACHIEVEMENT",
            person_fame_score=800,
        )
        result = calculate_episode_fame_v4(signals)

        assert result.score >= 70
        assert result.tier >= 4

    def test_personal_episode_low_score(self):
        """個人的なエピソードは低スコア"""
        signals = EpisodeFameSignals(
            llm_memorability=3.0,
            llm_empathy=4.0,
            llm_surprise=2.0,
            llm_generation_quality=5.0,
            llm_educational_value=2.0,
            llm_story_quality=4.0,
            llm_factual_density=3.0,
            episode_text="家族との日常的な思い出",
            episode_type="",
            person_fame_score=100,
        )
        result = calculate_episode_fame_v4(signals)

        assert result.score < 50
        assert result.tier <= 2
