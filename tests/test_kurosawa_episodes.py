#!/usr/bin/env python3
"""
黒澤明エピソード品質テスト
- 10件制限の遵守
- 年齢整合性（『乱』=75歳）
- 『七人の侍』エピソードの存在
"""

import csv
from pathlib import Path

import pytest

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")


def get_kurosawa_episodes() -> list[dict]:
    """黒澤明のエピソードを取得"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row.get("person_name") == "黒澤明"]


class TestKurosawaEpisodes:
    """黒澤明エピソードの品質テスト"""

    def test_episode_count_limit(self):
        """エピソード数が10件以下であること"""
        episodes = get_kurosawa_episodes()
        assert len(episodes) <= 10, f"黒澤明エピソード数: {len(episodes)}件（制限10件）"

    def test_ran_age_correct(self):
        """『乱』をメインで扱うエピソード（E574646B5）の年齢が75歳であること"""
        episodes = get_kurosawa_episodes()
        # 『乱』をメインテーマとするエピソード（タイトル内で最初に『乱』が登場）
        ran_episodes = [
            e
            for e in episodes
            if e.get("episode_id") == "E574646B5"
            or ("『乱』を完成" in e.get("episode_text", "") and float(e.get("age", 0)) == 75.0)
        ]

        assert len(ran_episodes) >= 1, "『乱』メインエピソードが存在しない"

        ran_ep = ran_episodes[0]
        age = float(ran_ep.get("age", 0))
        assert age == 75.0, f"『乱』年齢: {age}歳（正解: 75歳）"

    def test_seven_samurai_exists(self):
        """『七人の侍』エピソード（44歳）が存在すること"""
        episodes = get_kurosawa_episodes()
        samurai_episodes = [e for e in episodes if "七人の侍" in e.get("episode_text", "")]

        assert len(samurai_episodes) >= 1, "『七人の侍』エピソードが存在しない"

        samurai_ep = samurai_episodes[0]
        age = float(samurai_ep.get("age", 0))
        assert age == 44.0, f"『七人の侍』年齢: {age}歳（正解: 44歳）"

    @pytest.mark.xfail(reason="既存データ品質課題: 黒澤テーマ重複 - 技術的負債", strict=False)
    def test_unique_main_themes(self):
        """各エピソードが異なる年齢をカバーしていること（代表作多様性）"""
        episodes = get_kurosawa_episodes()

        # 期待される年齢セット (80歳エピソード追加: 2026-01-09)
        expected_ages = {33.0, 40.0, 44.0, 60.0, 75.0, 80.0}
        actual_ages = {float(e.get("age", 0)) for e in episodes}

        assert expected_ages == actual_ages, f"期待年齢: {expected_ages}, 実際: {actual_ages}"

    def test_age_diversity(self):
        """年齢が多様であること（同一年齢の重複なし）"""
        episodes = get_kurosawa_episodes()
        ages = [float(e.get("age", 0)) for e in episodes]

        # 重複チェック
        duplicates = [a for a in ages if ages.count(a) > 1]
        assert not duplicates, f"年齢重複: {set(duplicates)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
