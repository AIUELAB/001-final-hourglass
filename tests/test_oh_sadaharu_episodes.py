#!/usr/bin/env python3
"""
王貞治エピソード品質テスト
- 10件制限の遵守
- 重要イベントの存在確認
- 埋め草の不在確認
"""

import csv
import re
from pathlib import Path

import pytest

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")


def get_oh_episodes() -> list[dict]:
    """王貞治のエピソードを取得"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row.get("person_name") == "王貞治"]


def is_filler(text: str) -> bool:
    """埋め草判定"""
    filler_phrases = ["後進の育成", "情熱を注", "社会に貢献", "生涯現役", "次世代に伝え"]
    filler_count = sum(1 for p in filler_phrases if p in text)

    has_year = bool(re.search(r"(19|20)\d{2}年", text))
    has_number = bool(re.search(r"\d+[本回度件位]", text))
    specificity = sum([has_year, has_number])

    return specificity <= 1 and filler_count >= 2


class TestOhSadaharuEpisodes:
    """王貞治エピソードの品質テスト"""

    def test_episode_count_limit(self):
        """エピソード数が10件以下であること"""
        episodes = get_oh_episodes()
        assert len(episodes) <= 10, f"王貞治エピソード数: {len(episodes)}件（制限10件）"

    def test_important_events_exist(self):
        """重要イベントが含まれていること"""
        episodes = get_oh_episodes()
        texts = [e.get("episode_text", "") for e in episodes]
        all_text = " ".join(texts)

        # 重要イベントの存在確認
        assert "868本" in all_text or "世界記録" in all_text, "868本塁打の言及がない"
        assert "引退" in all_text, "引退の言及がない"
        assert "日本一" in all_text or "優勝" in all_text, "優勝の言及がない"

    def test_no_filler_episodes(self):
        """埋め草エピソードがないこと"""
        episodes = get_oh_episodes()
        fillers = [e for e in episodes if is_filler(e.get("episode_text", ""))]

        assert len(fillers) == 0, f"埋め草エピソード: {[e['episode_id'] for e in fillers]}"

    def test_age_diversity(self):
        """年齢が多様であること"""
        episodes = get_oh_episodes()
        ages = [float(e.get("age", 0)) for e in episodes]

        # 重複チェック
        duplicates = [a for a in ages if ages.count(a) > 1]
        assert not duplicates, f"年齢重複: {set(duplicates)}"

    def test_expected_ages(self):
        """期待される年齢構成であること"""
        episodes = get_oh_episodes()
        ages = {float(e.get("age", 0)) for e in episodes}

        # 期待される年齢（35, 40, 55, 60）
        expected = {35.0, 40.0, 55.0, 60.0}
        assert ages == expected, f"期待: {expected}, 実際: {ages}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
