#!/usr/bin/env python3
"""
エピソード形式検証ゲートのテスト

検証項目:
1. 正しい定型パターンの検出
2. 一人称「私は」パターンの検出
3. episode_fame_v6の範囲検証
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.episode_format_gate import EpisodeFormatGate


class TestEpisodeFormatGate:
    """EpisodeFormatGateのテスト"""

    def setup_method(self):
        """テスト前の初期化"""
        self.gate = EpisodeFormatGate()

    def test_valid_format(self):
        """正しい定型パターンのテスト"""
        valid_text = (
            "あなたと同じ26歳のとき、アインシュタインは1905年、「奇跡の年」と呼ばれる驚異的な業績を成し遂げました。"
        )
        errors = self.gate.validate_single(valid_text, v6_score=75.0)
        assert len(errors) == 0, f"正しい形式でエラーが出た: {errors}"

    def test_invalid_watashi_pattern(self):
        """一人称「私は」パターンの検出テスト"""
        invalid_text = "あなたと同じ15歳のとき、私は1987年の春に東京の駒場東邦中学校から高等学校へと進学していました。"
        errors = self.gate.validate_single(invalid_text)
        assert len(errors) == 1
        assert "私は" in errors[0]

    def test_v6_out_of_range_high(self):
        """v6が上限超えのテスト"""
        valid_text = "あなたと同じ30歳のとき、田中太郎は記録を達成しました。"
        errors = self.gate.validate_single(valid_text, v6_score=408931.0)
        assert len(errors) == 1
        assert "範囲外" in errors[0]

    def test_v6_in_range(self):
        """v6が正常範囲のテスト"""
        valid_text = "あなたと同じ30歳のとき、田中太郎は記録を達成しました。"
        errors = self.gate.validate_single(valid_text, v6_score=75.5)
        assert len(errors) == 0

    def test_v6_boundary_max(self):
        """v6が上限境界値のテスト"""
        valid_text = "あなたと同じ30歳のとき、田中太郎は記録を達成しました。"
        errors = self.gate.validate_single(valid_text, v6_score=200.0)
        assert len(errors) == 0

    def test_v6_boundary_over_max(self):
        """v6が上限境界値超えのテスト"""
        valid_text = "あなたと同じ30歳のとき、田中太郎は記録を達成しました。"
        errors = self.gate.validate_single(valid_text, v6_score=200.01)
        assert len(errors) == 1


class TestTargetEpisodes:
    """対象4件のエピソードの検証テスト"""

    def setup_method(self):
        """テスト前の初期化"""
        self.gate = EpisodeFormatGate()
        # 調査で特定された問題パターン
        self.problem_texts = [
            "あなたと同じ15歳のとき、私は1987年の春に東京の駒場東邦中学校から高等学校へと進学していました。",
            "あなたと同じ15歳のとき、私は1985年に体操の世界で大きな転機を迎えていました。",
            "あなたと同じ15歳のとき、1985年の春、私は大阪の履正社高等学校で野球部に入部した。",
            "あなたと同じ15歳のとき、私は1969年の春、東京オリンピックの余韻がまだ残る日本で、体操競技に全てを捧げていました。",
        ]

    def test_all_problem_episodes_detected(self):
        """対象エピソードの全てが検出されること"""
        for text in self.problem_texts:
            errors = self.gate.validate_single(text)
            assert len(errors) >= 1, f"問題エピソードが検出されなかった: {text[:50]}..."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
