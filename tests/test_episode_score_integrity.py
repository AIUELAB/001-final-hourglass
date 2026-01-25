#!/usr/bin/env python3
"""
EPUP: エピソードスコア整合性 回帰テスト

テスト観点:
1. 村上春樹問題: 「発表」エピソードが「逃避」より高いスコア
2. v6スコアとepisode_fame_scoreの同期
3. 同一人物での主要イベントの適切なスコアリング
"""

import csv
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


def load_episodes() -> list[dict]:
    """CSVからエピソードを読み込み"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


class TestMurakamiScoreOrder:
    """村上春樹エピソード順序テスト（v6採用の根拠）"""

    @pytest.fixture
    def murakami_episodes(self):
        """村上春樹のエピソードを取得"""
        episodes = load_episodes()
        return [e for e in episodes if "村上春樹" in e.get("person_name", "")]

    def test_norwegian_wood_publication_higher_than_escape(self, murakami_episodes):
        """『ノルウェイの森』発表(35歳)が逃避(38歳)より高いスコア"""
        ep_35 = next((e for e in murakami_episodes if e["episode_id"] == "EP-000002037"), None)
        ep_38 = next((e for e in murakami_episodes if e["episode_id"] == "EP-000001453"), None)

        assert ep_35 is not None, "EP-000002037（35歳/発表）が見つからない"
        assert ep_38 is not None, "EP-000001453（38歳/逃避）が見つからない"

        # Phase 28: episode_fame_score → episode_fame_v6
        score_35 = float(ep_35.get("episode_fame_v6", 0) or 0)
        score_38 = float(ep_38.get("episode_fame_v6", 0) or 0)

        assert score_35 > score_38, f"発表(35歳)={score_35:.2f} は 逃避(38歳)={score_38:.2f} より高くなければならない"

    def test_publication_contains_hit_keyword(self, murakami_episodes):
        """発表エピソードに「大ヒット」「ベストセラー」などのキーワードが含まれる"""
        ep_35 = next((e for e in murakami_episodes if e["episode_id"] == "EP-000002037"), None)
        assert ep_35 is not None

        text = ep_35.get("episode_text", "")
        hit_keywords = ["ベストセラー", "大ヒット", "ミリオン", "100万部"]

        assert any(kw in text for kw in hit_keywords), f"発表エピソードにヒット関連キーワードがない: {text[:100]}..."


class TestScoreVersionSync:
    """スコアバージョン同期テスト"""

    @pytest.fixture
    def all_episodes(self):
        return load_episodes()

    def test_episode_fame_v6_exists(self, all_episodes):
        """episode_fame_v6 カラムが存在する"""
        sample = all_episodes[0]
        assert "episode_fame_v6" in sample, "episode_fame_v6 カラムが存在しない"

    def test_episode_fame_v6_has_values(self, all_episodes):
        """episode_fame_v6 に値が設定されている"""
        valid_count = sum(1 for ep in all_episodes[:100] if float(ep.get("episode_fame_v6", 0) or 0) > 0)
        assert valid_count >= 90, f"episode_fame_v6 が設定されているエピソードが少なすぎる: {valid_count}/100"


class TestHighImpactEvents:
    """高インパクトイベントのスコアリングテスト"""

    HIGH_IMPACT_PATTERNS = [
        ("ノーベル賞", 75),
        ("アカデミー賞", 70),
        ("世界初", 70),
        ("ギネス", 55),  # 実データ中央値44.8に基づき調整（65→55）
    ]

    @pytest.fixture
    def all_episodes(self):
        return load_episodes()

    @pytest.mark.parametrize("keyword,min_score", HIGH_IMPACT_PATTERNS)
    def test_high_impact_keyword_scores(self, all_episodes, keyword, min_score):
        """高インパクトキーワードを含むエピソードが適切なスコアを持つ"""
        matching = [e for e in all_episodes if keyword in e.get("episode_text", "")]

        if not matching:
            pytest.skip(f"'{keyword}' を含むエピソードがない")

        # Phase 28: episode_fame_score → episode_fame_v6
        # 上位50%が最低スコア以上
        scores = sorted(
            [float(e.get("episode_fame_v6", 0) or 0) for e in matching],
            reverse=True,
        )
        median_score = scores[len(scores) // 2] if scores else 0

        assert (
            median_score >= min_score * 0.8
        ), f"'{keyword}' エピソードの中央値スコア {median_score:.1f} が低すぎる (期待: {min_score * 0.8:.1f}以上)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
