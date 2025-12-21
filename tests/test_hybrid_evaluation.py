#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ハイブリッド評価関数の統合テスト

score_calculator.pyに統合されたハイブリッド評価関数のテスト。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from backend.app.utils.score_calculator import (
    HYBRID_WEIGHTS,
    calculate_hybrid_rule_scores,
    calculate_hybrid_scores,
    calculate_hybrid_seven_axes,
)


class TestHybridWeights:
    """重み設定のテスト"""

    def test_weights_exist(self):
        """全7軸の重みが定義されているか"""
        expected_axes = ["記憶性", "共感性", "意外性", "生成品質", "教育的価値", "ストーリー品質", "事実密度"]
        for axis in expected_axes:
            assert axis in HYBRID_WEIGHTS, f"Missing weight for {axis}"

    def test_weights_sum_to_one(self):
        """各軸の重みの合計が1.0か"""
        for axis, (rule_w, llm_w) in HYBRID_WEIGHTS.items():
            assert abs(rule_w + llm_w - 1.0) < 0.01, f"Weights for {axis} don't sum to 1.0"

    def test_weights_range(self):
        """重みが0-1の範囲内か"""
        for axis, (rule_w, llm_w) in HYBRID_WEIGHTS.items():
            assert 0 <= rule_w <= 1, f"Rule weight for {axis} out of range"
            assert 0 <= llm_w <= 1, f"LLM weight for {axis} out of range"


class TestCalculateHybridRuleScores:
    """ルールベーススコア計算のテスト"""

    def test_basic_episode(self):
        """基本的なエピソードでスコアが計算されるか"""
        episode = {"episode_text": "あなたと同じ25歳のとき、彼は1990年に重大な転機を迎えた。感動的な瞬間だった。"}
        scores = calculate_hybrid_rule_scores(episode)

        assert "記憶性" in scores
        assert "共感性" in scores
        assert "意外性" in scores
        assert "生成品質" in scores
        assert "教育的価値" in scores
        assert "ストーリー品質" in scores
        assert "事実密度" in scores

    def test_score_range(self):
        """スコアが1-10の範囲内か"""
        episode = {"episode_text": "あなたと同じ30歳のとき、彼女は大きな成功を収めた。"}
        scores = calculate_hybrid_rule_scores(episode)

        for axis, score in scores.items():
            assert 1 <= score <= 10, f"Score for {axis} out of range: {score}"

    def test_empty_text(self):
        """空テキストでもエラーにならないか"""
        episode = {"episode_text": ""}
        scores = calculate_hybrid_rule_scores(episode)

        assert len(scores) == 7
        for score in scores.values():
            assert 1 <= score <= 10

    def test_keyword_detection_emotion(self):
        """感情キーワードが検出されてスコアに反映されるか"""
        # 感情キーワードあり
        episode_with = {"episode_text": "彼は感動と涙の瞬間を経験した。喜びと希望に満ちていた。"}
        # 感情キーワードなし
        episode_without = {"episode_text": "彼は仕事をした。会議に出席した。報告書を書いた。"}

        scores_with = calculate_hybrid_rule_scores(episode_with)
        scores_without = calculate_hybrid_rule_scores(episode_without)

        assert scores_with["共感性"] > scores_without["共感性"]

    def test_keyword_detection_turning(self):
        """転機キーワードが検出されてスコアに反映されるか"""
        episode_with = {"episode_text": "ところが転機が訪れた。しかし実はそれが始まりだった。"}
        episode_without = {"episode_text": "彼は毎日同じ仕事をしていた。変化はなかった。"}

        scores_with = calculate_hybrid_rule_scores(episode_with)
        scores_without = calculate_hybrid_rule_scores(episode_without)

        assert scores_with["意外性"] > scores_without["意外性"]

    def test_structure_bonus(self):
        """「あなたと同じ」で始まるとスコアが上がるか"""
        episode_proper = {"episode_text": "あなたと同じ25歳のとき、彼は成功を収めた。努力の成果だった。"}
        episode_other = {"episode_text": "彼は25歳で成功を収めた。努力の成果だった。"}

        scores_proper = calculate_hybrid_rule_scores(episode_proper)
        scores_other = calculate_hybrid_rule_scores(episode_other)

        assert scores_proper["ストーリー品質"] >= scores_other["ストーリー品質"]


class TestCalculateHybridScores:
    """ハイブリッドスコア計算のテスト"""

    def test_without_llm_scores(self):
        """LLMスコアなしで計算できるか"""
        episode = {"episode_text": "あなたと同じ30歳のとき、彼は大きな成功を収めた。"}
        scores = calculate_hybrid_scores(episode, llm_scores=None)

        assert len(scores) == 7
        for axis, score in scores.items():
            assert 1 <= score <= 10, f"Score for {axis} out of range"

    def test_with_llm_scores(self):
        """LLMスコアありで計算できるか"""
        episode = {"episode_text": "あなたと同じ30歳のとき、彼は大きな成功を収めた。"}
        llm_scores = {"empathy": 8, "surprise": 7, "story_quality": 9}
        scores = calculate_hybrid_scores(episode, llm_scores=llm_scores)

        assert len(scores) == 7
        for axis, score in scores.items():
            assert 1 <= score <= 10, f"Score for {axis} out of range"

    def test_llm_influence_on_subjective_axes(self):
        """LLMスコアが主観的軸に影響を与えるか"""
        episode = {"episode_text": "普通のエピソード。特に何もなかった。"}

        # LLMが高評価
        llm_high = {"empathy": 9, "surprise": 9, "story_quality": 9}
        # LLMが低評価
        llm_low = {"empathy": 2, "surprise": 2, "story_quality": 2}

        scores_high = calculate_hybrid_scores(episode, llm_high)
        scores_low = calculate_hybrid_scores(episode, llm_low)

        # 共感性（LLM 70%）で差が出るはず
        assert scores_high["共感性"] > scores_low["共感性"]
        # 意外性（LLM 70%）でも差が出るはず
        assert scores_high["意外性"] > scores_low["意外性"]

    def test_fact_density_ignores_llm(self):
        """事実密度はLLMを無視するか（100%ルールベース）"""
        episode = {"episode_text": "2020年に100人が参加。50億円の投資。"}

        llm_high = {"empathy": 10, "surprise": 10, "story_quality": 10}
        llm_low = {"empathy": 1, "surprise": 1, "story_quality": 1}

        scores_high = calculate_hybrid_scores(episode, llm_high)
        scores_low = calculate_hybrid_scores(episode, llm_low)

        # 事実密度は同じはず（LLMの重みが0）
        assert scores_high["事実密度"] == scores_low["事実密度"]


class TestCalculateHybridSevenAxes:
    """7軸スコア計算のテスト"""

    def test_returns_correct_field_names(self):
        """正しい日本語フィールド名で返されるか"""
        episode = {"episode_text": "あなたと同じ25歳のとき、彼は成功した。"}
        scores = calculate_hybrid_seven_axes(episode)

        expected_fields = [
            "記憶性スコア",
            "共感性スコア",
            "意外性スコア",
            "生成品質スコア",
            "教育的価値",
            "ストーリー品質",
            "事実密度",
        ]
        for field in expected_fields:
            assert field in scores, f"Missing field: {field}"

    def test_all_scores_numeric(self):
        """全スコアが数値か"""
        episode = {"episode_text": "テストエピソード"}
        scores = calculate_hybrid_seven_axes(episode)

        for field, value in scores.items():
            assert isinstance(value, (int, float)), f"{field} is not numeric"

    def test_real_episode_example(self):
        """実際のエピソード形式でテスト"""
        episode = {
            "episode_text": """あなたと同じ27歳のとき、彼は1985年に人生の転機を迎えた。
それまで順調だったキャリアに突然の挫折が訪れた。しかし、この困難が彼の人生を大きく変えることになる。
苦悩の日々を乗り越え、彼は新たな道を切り開いた。この経験から学んだことは、逆境こそが成長の糧になるということだった。""",
            "episode_type": "TURNING_POINT",
            "fame_score": 75,
        }
        scores = calculate_hybrid_seven_axes(episode)

        # 各スコアが適切な範囲にあることを確認
        for field, value in scores.items():
            assert 1 <= value <= 10, f"{field} out of range: {value}"

        # 転機キーワードがあるので意外性が高めになるはず
        # （厳密な値は期待しないが、最低限のチェック）
        assert scores["意外性スコア"] >= 3


class TestIntegrationWithExistingFunctions:
    """既存関数との統合テスト"""

    def test_import_success(self):
        """インポートが正常にできるか"""
        from backend.app.utils.score_calculator import (
            calculate_composite_score,
            calculate_hybrid_seven_axes,
        )

        assert callable(calculate_composite_score)
        assert callable(calculate_hybrid_seven_axes)

    def test_hybrid_scores_work_with_composite(self):
        """ハイブリッドスコアがcomposite_score計算で使えるか"""
        from backend.app.utils.score_calculator import calculate_composite_score

        episode = {"episode_text": "あなたと同じ30歳のとき、彼は成功を収めた。"}
        hybrid_scores = calculate_hybrid_seven_axes(episode)

        # ハイブリッドスコアをエピソードデータに追加
        episode_with_scores = {**episode, **hybrid_scores}

        # composite_scoreが計算できるか
        composite = calculate_composite_score(episode_with_scores)

        assert composite is not None
        assert 1 <= composite <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
