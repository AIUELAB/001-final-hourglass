#!/usr/bin/env python3
"""
重要エピソードランキング保護の回帰テスト

テスト観点:
- 歴史的に重要なエピソードが同一人物内で上位にランクされること
- episode_fame_v6スコアリングが適切に機能すること

等価分割:
- Tier1キーワード含有エピソード（ノーベル賞、アカデミー賞等）
- 歴史的マイルストーン（大統領就任、革命等）
- 科学的発見（相対性理論、DNA等）

境界値:
- 同一人物内1位（MUST）
- 同一人物内Top3（SHOULD）
"""

import csv
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


def get_person_episodes(person_id: str) -> list[dict]:
    """指定人物のエピソードをv6スコア順で取得"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        eps = [r for r in reader if r.get("person_id") == person_id]

    # episode_fame_v6でソート
    eps.sort(key=lambda x: float(x.get("episode_fame_v6") or 0), reverse=True)
    return eps


def get_episode_rank(person_id: str, episode_id: str) -> int:
    """指定エピソードの同一人物内順位を取得"""
    eps = get_person_episodes(person_id)
    for i, ep in enumerate(eps, 1):
        if ep.get("episode_id") == episode_id:
            return i
    return -1  # 見つからない


class TestEinsteinMiracleYear:
    """アインシュタイン「奇跡の年」テスト"""

    PERSON_ID = "P93F1DB1"  # アインシュタイン
    EPISODE_ID = "EP-3947C4DE"  # 奇跡の年

    def test_miracle_year_is_top_2(self):
        """EP-3947C4DE（奇跡の年）がアインシュタイン内Top2であること

        Note: 同点100点の場合があるため、Top2を許容
        """
        rank = get_episode_rank(self.PERSON_ID, self.EPISODE_ID)
        assert rank <= 2, f"奇跡の年はTop2であるべき（現在: {rank}位）"

    def test_miracle_year_has_high_score(self):
        """EP-3947C4DEのスコアが90以上であること"""
        eps = get_person_episodes(self.PERSON_ID)
        target = next((e for e in eps if e.get("episode_id") == self.EPISODE_ID), None)
        assert target is not None, "EP-3947C4DEが見つからない"

        score = float(target.get("episode_fame_v6") or 0)
        assert score >= 90, f"スコアは90以上であるべき（現在: {score}）"

    def test_miracle_year_is_tier_5(self):
        """EP-3947C4DEがTier5であること"""
        eps = get_person_episodes(self.PERSON_ID)
        target = next((e for e in eps if e.get("episode_id") == self.EPISODE_ID), None)
        assert target is not None

        tier = int(float(target.get("episode_fame_tier_v6") or 0))
        assert tier == 5, f"Tier5であるべき（現在: Tier{tier}）"


class TestImportantEpisodesNotInInversions:
    """重要エピソードが逆転候補に含まれないことをテスト"""

    # 重要エピソード定義（person_id, episode_id, 説明）
    IMPORTANT_EPISODES = [
        ("P93F1DB1", "EP-3947C4DE", "アインシュタイン奇跡の年"),
        # 追加可能: 他の重要エピソード
    ]

    @pytest.fixture
    def all_episodes(self):
        """全エピソード読み込み"""
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)

    @pytest.mark.parametrize("person_id,episode_id,desc", IMPORTANT_EPISODES)
    def test_important_episode_in_top_3(self, person_id, episode_id, desc):
        """重要エピソードが同一人物内Top3に入っていること"""
        rank = get_episode_rank(person_id, episode_id)
        assert rank <= 3, f"{desc}はTop3であるべき（現在: {rank}位）"


class TestNobelPrizeEpisodes:
    """ノーベル賞エピソードのランキングテスト"""

    def test_nobel_keywords_get_bonus(self):
        """ノーベル賞キーワードを含むエピソードが高スコアを得ること"""
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            all_eps = list(reader)

        nobel_eps = [
            e for e in all_eps if "ノーベル賞" in e.get("episode_text", "") or "ノーベル" in e.get("episode_text", "")
        ]

        # ノーベル賞エピソードの平均スコアが60以上であること
        if nobel_eps:
            avg_score = sum(float(e.get("episode_fame_v6") or 0) for e in nobel_eps) / len(nobel_eps)
            assert avg_score >= 60, f"ノーベル賞エピソードの平均スコアは60以上であるべき（現在: {avg_score:.2f}）"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
