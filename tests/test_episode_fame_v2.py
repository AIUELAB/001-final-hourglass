"""
Episode Fame Score v2 テスト

感銘重視のスコアリングが正しく動作することを検証
"""

import pytest

from scripts.score.episode_fame_v2 import (
    calculate_episode_fame_v2,
    calculate_inspiration_score,
    calculate_historical_impact,
    check_specificity,
    check_meta_expressions,
    apply_bias_control,
    get_tier,
)


class TestInspirationScore:
    """感銘度スコアのテスト"""

    def test_mandela_high_inspiration(self):
        """マンデラ型エピソード（逆境→達成）で高スコア"""
        text = """ネルソン・マンデラは27年間の獄中生活を経て、
        南アフリカ初の黒人大統領に就任しました。
        人種差別撤廃と和解の道を選び、
        平和的な政権移行を実現しました。"""

        result = calculate_inspiration_score(text)
        assert result["total"] >= 40, f"マンデラ型エピソードの感銘度が低すぎる: {result['total']}"

    def test_empty_text_zero_score(self):
        """空テキストはスコア0"""
        result = calculate_inspiration_score("")
        assert result["total"] == 0

    def test_difficulty_keywords_detected(self):
        """困難キーワードが検出される"""
        text = "逆境を乗り越え、投獄されながらも信念を貫いた"
        result = calculate_inspiration_score(text)
        assert "difficulty" in result["details"]["matched_keywords"]
        assert any(kw in result["details"]["matched_keywords"]["difficulty"] for kw in ["逆境", "投獄"])

    def test_achievement_keywords_detected(self):
        """達成キーワードが検出される"""
        text = "ノーベル平和賞を受賞し、歴史的な偉業を成し遂げた"
        result = calculate_inspiration_score(text)
        assert "achievement" in result["details"]["matched_keywords"]

    def test_narrative_bonus_applied(self):
        """困難→達成パターンでナラティブボーナス"""
        # 困難と達成の両方があるケース
        text = "差別と迫害を受けながらも、最終的にノーベル平和賞を受賞した"
        result = calculate_inspiration_score(text)
        assert result["narrative_bonus"] > 0, "ナラティブボーナスが付与されていない"


class TestHistoricalImpact:
    """歴史的インパクトのテスト"""

    def test_nobel_prize_detected(self):
        """ノーベル平和賞が検出される"""
        text = "ノーベル平和賞を受賞した"
        result = calculate_historical_impact(text)
        assert "world_awards" in result["matched"]
        assert result["total"] > 0

    def test_world_first_detected(self):
        """史上初が検出される"""
        text = "史上最年少でこの記録を達成した"
        result = calculate_historical_impact(text)
        assert "world_first" in result["matched"]

    def test_social_change_detected(self):
        """社会変革キーワードが検出される"""
        text = "人権運動により法改正を実現した"
        result = calculate_historical_impact(text)
        assert "social_change" in result["matched"]


class TestQualityGate:
    """品質ゲートのテスト"""

    def test_specificity_with_proper_nouns(self):
        """固有名詞が含まれていれば合格"""
        text = "アインシュタインはドイツで生まれた"
        result = check_specificity(text)
        # カタカナが含まれているのでpass
        assert result["pass"] is True

    def test_meta_expression_penalty(self):
        """メタ表現でペナルティ"""
        text = "あなたと同じ30歳のとき、この偉業を達成した"
        result = check_meta_expressions(text)
        assert result["has_meta"] is True
        assert result["penalty"] < 1.0


class TestBiasControl:
    """偏り制御のテスト"""

    def test_same_person_limit(self):
        """同一人物の上位独占を防止"""
        episodes = [
            {"person_id": "P1", "episode_fame_v2": 90, "rank_v2": 1},
            {"person_id": "P1", "episode_fame_v2": 89, "rank_v2": 2},
            {"person_id": "P1", "episode_fame_v2": 88, "rank_v2": 3},
            {"person_id": "P1", "episode_fame_v2": 87, "rank_v2": 4},  # 4件目は制限
            {"person_id": "P2", "episode_fame_v2": 86, "rank_v2": 5},
        ]

        result = apply_bias_control(episodes, top_n=100)

        # P1は最大3件まで
        p1_not_excluded = [ep for ep in result if ep["person_id"] == "P1" and not ep.get("bias_excluded")]
        assert len(p1_not_excluded) <= 3


class TestIntegration:
    """統合テスト"""

    def test_calculate_episode_fame_v2_basic(self):
        """v2スコア計算の基本動作"""
        text = "ノーベル平和賞を受賞し、世界を変えた"
        llm_scores = {
            "memorability": 7.0,
            "storytelling_quality": 7.0,
            "factual_density": 7.0,
            "educational_value": 7.0,
            "empathy": 7.0,
        }

        result = calculate_episode_fame_v2(
            text=text,
            llm_scores=llm_scores,
            celebrity_score=500,
        )

        assert "total" in result
        assert "tier" in result
        assert "components" in result
        assert result["total"] > 0

    def test_tier_boundaries(self):
        """ティア境界値の正確性"""
        assert get_tier(90) == 5
        assert get_tier(85) == 5
        assert get_tier(70) == 4
        assert get_tier(55) == 3
        assert get_tier(40) == 2
        assert get_tier(30) == 1


class TestRegressionPrevention:
    """回帰テスト（問題の再発防止）"""

    def test_no_single_person_dominance(self):
        """同一人物がTop20を独占しない"""
        # 偏り制御が効いていることを確認
        episodes = [
            {"person_id": "SAME", "episode_fame_v2": 100 - i}
            for i in range(25)  # 同一人物25件
        ] + [
            {"person_id": f"OTHER_{i}", "episode_fame_v2": 70 - i}
            for i in range(10)  # 別人物10件
        ]

        result = apply_bias_control(episodes, top_n=20)
        top20 = [ep for ep in result[:20] if not ep.get("bias_excluded")]

        same_person_count = sum(1 for ep in top20 if ep["person_id"] == "SAME")
        assert same_person_count <= 1, f"Top20に同一人物が{same_person_count}件ある"

    def test_inspiration_weighted_properly(self):
        """感銘度が40%重み付けされている"""
        # 感銘度が高いエピソードはv2スコアが高くなる
        text_high_inspiration = "逆境を乗り越え、差別と戦い、ノーベル平和賞を受賞した偉業"
        text_low_inspiration = "普通の一日を過ごした"

        llm_scores = {
            k: 5.0 for k in ["memorability", "storytelling_quality", "factual_density", "educational_value", "empathy"]
        }

        result_high = calculate_episode_fame_v2(text=text_high_inspiration, llm_scores=llm_scores, celebrity_score=500)
        result_low = calculate_episode_fame_v2(text=text_low_inspiration, llm_scores=llm_scores, celebrity_score=500)

        assert (
            result_high["total"] > result_low["total"]
        ), f"感銘度が高いエピソードのスコアが低い: {result_high['total']} vs {result_low['total']}"
