#!/usr/bin/env python3
"""
転機エピソード保護の回帰テスト

テスト観点:
- Tier1キーワード含有エピソードがBIAS_CONTROL制限で落ちないこと
- apply_bias_control関数がTier1追加枠を正しく適用すること
- 転機カバレッジ検出が正しく動作すること
"""

import pytest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.score.episode_fame_v6.scorer import (
    apply_bias_control,
    _contains_tier1_keyword,
)
from scripts.score.episode_fame_v6.config import TIER1_KEYWORDS, BIAS_CONTROL


class TestTier1KeywordDetection:
    """Tier1キーワード検出テスト"""

    def test_contains_nobel_prize(self):
        """ノーベル賞キーワードの検出"""
        text = "アインシュタインは1921年にノーベル物理学賞を受賞しました。"
        assert _contains_tier1_keyword(text) is True

    def test_contains_president_inauguration(self):
        """大統領就任キーワードの検出"""
        text = "プーチンは2000年に大統領初当選を果たしました。"
        assert _contains_tier1_keyword(text) is True

    def test_contains_olympic_gold(self):
        """オリンピック金メダルキーワードの検出"""
        text = "北島康介はオリンピック金メダルを獲得しました。"
        assert _contains_tier1_keyword(text) is True

    def test_no_tier1_keyword(self):
        """Tier1キーワードを含まないテキスト"""
        text = "彼は幼少期を田舎で過ごしました。"
        assert _contains_tier1_keyword(text) is False

    def test_empty_text(self):
        """空テキスト"""
        assert _contains_tier1_keyword("") is False
        assert _contains_tier1_keyword(None) is False


class TestBiasControlWithTier1Protection:
    """BIAS_CONTROL + Tier1保護テスト"""

    def _make_episode(self, person_id: str, episode_id: str, text: str, score: float) -> dict:
        """テスト用エピソード生成"""
        return {
            "person_id": person_id,
            "episode_id": episode_id,
            "episode_text": text,
            "episode_fame_v6": score,
        }

    def test_tier1_gets_extra_slot_in_top20(self):
        """Top20内でTier1エピソードが追加枠を獲得"""
        # 先に他の人物で19件埋める（rank 1-19）
        episodes = []
        for i in range(19):
            episodes.append(self._make_episode(f"P{100 + i}", f"E{100 + i}", "他の人物", 95.0 - i * 0.1))

        # 同一人物の2件のエピソード（1件はTier1）をrank 20以降に配置
        episodes.append(self._make_episode("P001", "E001", "普通のエピソード", 70.0))  # rank 20
        episodes.append(self._make_episode("P001", "E002", "ノーベル賞を受賞しました", 69.0))  # rank 21, Tier1

        # スコア順にソート
        episodes.sort(key=lambda x: x["episode_fame_v6"], reverse=True)

        result = apply_bias_control(episodes)

        # P001のエピソードが両方Top21に入っていることを確認
        # (Tier1追加枠により、rank 20の後ろにrank 21も入る)
        top21_p001 = [ep for ep in result[:21] if ep["person_id"] == "P001"]
        assert len(top21_p001) == 2, "Tier1エピソードで追加枠が適用されるべき"

    def test_non_tier1_limited_in_top20(self):
        """Top20内で非Tier1エピソードは1件制限"""
        # 先に他の人物で18件埋める
        episodes = []
        for i in range(18):
            episodes.append(self._make_episode(f"P{100 + i}", f"E{100 + i}", "他の人物", 95.0 - i * 0.1))

        # 同一人物の2件の普通のエピソード
        episodes.append(self._make_episode("P001", "E001", "普通のエピソード1", 70.0))  # rank 19
        episodes.append(self._make_episode("P001", "E002", "普通のエピソード2", 69.0))  # rank 20

        # 追加の人物で埋める（deferredがTop20外に押し出されるように）
        for i in range(10):
            episodes.append(self._make_episode(f"P{200 + i}", f"E{200 + i}", "追加の人物", 68.0 - i * 0.1))

        # スコア順にソート
        episodes.sort(key=lambda x: x["episode_fame_v6"], reverse=True)

        result = apply_bias_control(episodes)

        # P001のエピソードはTop20に1件のみ（E002はdeferredに入って21位以降に移動）
        top20_p001 = [ep for ep in result[:20] if ep["person_id"] == "P001"]
        assert len(top20_p001) == 1, "非Tier1は1件制限のまま"

    def test_tier1_extra_slot_limit(self):
        """Tier1追加枠は1人1件まで"""
        # 先に他の人物で17件埋める
        episodes = []
        for i in range(17):
            episodes.append(self._make_episode(f"P{100 + i}", f"E{100 + i}", "他の人物", 95.0 - i * 0.1))

        # 同一人物の3件のTier1エピソード
        episodes.append(self._make_episode("P001", "E001", "ノーベル物理学賞を受賞", 70.0))  # rank 18
        episodes.append(self._make_episode("P001", "E002", "ノーベル化学賞を受賞", 69.0))  # rank 19
        episodes.append(self._make_episode("P001", "E003", "ノーベル平和賞を受賞", 68.0))  # rank 20

        # 追加の人物で埋める（deferredがTop20外に押し出されるように）
        for i in range(10):
            episodes.append(self._make_episode(f"P{200 + i}", f"E{200 + i}", "追加の人物", 67.0 - i * 0.1))

        # スコア順にソート
        episodes.sort(key=lambda x: x["episode_fame_v6"], reverse=True)

        result = apply_bias_control(episodes)

        # P001のエピソードはTop20に2件（通常1件 + Tier1追加1件、3件目はdeferred）
        top20_p001 = [ep for ep in result[:20] if ep["person_id"] == "P001"]
        assert len(top20_p001) == 2, "Tier1追加枠は1件まで"


class TestTurningPointCoverage:
    """転機カバレッジ検出テスト"""

    def test_tier1_keywords_are_defined(self):
        """Tier1キーワードが定義されていること"""
        assert len(TIER1_KEYWORDS) > 0
        assert "ノーベル賞" in TIER1_KEYWORDS
        assert "大統領就任" in TIER1_KEYWORDS or "大統領初当選" in TIER1_KEYWORDS

    def test_bias_control_thresholds(self):
        """BIAS_CONTROL閾値が適切に設定されていること"""
        assert 20 in BIAS_CONTROL
        assert 50 in BIAS_CONTROL
        assert 100 in BIAS_CONTROL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
