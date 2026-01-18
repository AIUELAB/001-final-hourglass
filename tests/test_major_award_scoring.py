#!/usr/bin/env python3
"""
国際賞スコアリングの回帰テスト

テスト観点:
- グラミー賞、アカデミー賞等の国際賞を含むエピソードが78点以上であること
- MAJOR_AWARD_KEYWORDSボーナスが適切に適用されること

境界値:
- 78点以上（MUST）
"""

import csv
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


def get_episode_score(episode_id: str) -> float | None:
    """指定エピソードのv6スコアを取得"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("episode_id") == episode_id:
                return float(row.get("episode_fame_v6") or 0)
    return None


class TestGrammyAwardScoring:
    """グラミー賞エピソードのスコアテスト"""

    # (episode_id, person_name, expected_min_score)
    # Phase 15B: 存在するエピソードIDに更新
    # 2026-01-18: EP-000007894削除のため、EP-260117001545198に更新
    GRAMMY_EPISODES = [
        ("EP-000004782", "秋吉敏子", 78),
        ("EP-260117001545198", "ウェス・モンゴメリー", 78),  # 94歳:3つのグラミー賞ノミネート
        ("EP-260111162341103", "スタン・ゲッツ", 78),  # 更新: ボサノヴァ/グラミー賞EP
    ]

    @pytest.mark.parametrize("episode_id,person_name,expected_min", GRAMMY_EPISODES)
    def test_grammy_episode_reaches_78(self, episode_id, person_name, expected_min):
        """グラミー賞EPが78点以上になること（Phase 15Bで解消）"""
        score = get_episode_score(episode_id)
        assert score is not None, f"{episode_id}が見つからない"
        assert (
            score >= expected_min
        ), f"{person_name}のグラミー賞EPは{expected_min}点以上であるべき（現在: {score:.2f}）"


class TestAcademyAwardScoring:
    """アカデミー賞エピソードのスコアテスト"""

    # Phase 15B: 存在するエピソードIDに更新
    ACADEMY_EPISODES = [
        ("EP-260111162341087", "イツァーク・パールマン", 78),  # 更新: シンドラーのリストEP
        ("EP-000004265", "マリオン・コティヤール", 78),  # 追加: アカデミー主演女優賞EP
    ]

    @pytest.mark.parametrize("episode_id,person_name,expected_min", ACADEMY_EPISODES)
    def test_academy_episode_reaches_78(self, episode_id, person_name, expected_min):
        """アカデミー賞EPが78点以上になること（Phase 15Bで解消）"""
        score = get_episode_score(episode_id)
        assert score is not None, f"{episode_id}が見つからない"
        assert (
            score >= expected_min
        ), f"{person_name}のアカデミー賞EPは{expected_min}点以上であるべき（現在: {score:.2f}）"


class TestMajorAwardBonus:
    """MAJOR_AWARD_KEYWORDSボーナスが適用されることのテスト"""

    def test_major_award_keywords_exist(self):
        """MAJOR_AWARD_KEYWORDSが定義されていること"""
        from scripts.score.episode_fame_v6.config import MAJOR_AWARD_KEYWORDS

        assert len(MAJOR_AWARD_KEYWORDS) >= 10, "MAJOR_AWARD_KEYWORDSに十分なキーワードがあること"
        assert "グラミー賞" in MAJOR_AWARD_KEYWORDS
        assert "アカデミー賞" in MAJOR_AWARD_KEYWORDS
        assert "ノーベル賞" in MAJOR_AWARD_KEYWORDS

    def test_grammy_bonus_value(self):
        """グラミー賞ボーナスが適切な値であること"""
        from scripts.score.episode_fame_v6.config import MAJOR_AWARD_KEYWORDS

        grammy_bonus = MAJOR_AWARD_KEYWORDS.get("グラミー賞", 0)
        assert grammy_bonus >= 5, f"グラミー賞ボーナスは5以上であるべき（現在: {grammy_bonus}）"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
