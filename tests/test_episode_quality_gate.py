#!/usr/bin/env python3
"""
エピソード品質ゲート 回帰テスト
EP-000006345, EP-000001326 のようなケースが再発しないことを検証
"""

import pytest
import pandas as pd
import re
import sys

sys.path.insert(0, "scripts")


class TestEpisodeQualityGate:
    """品質ゲートテスト"""

    @pytest.fixture
    def sample_episodes(self):
        """テスト用サンプルエピソード"""
        return [
            {
                "episode_id": "TEST-001",
                "person_name": "テスト太郎",
                "age": 35,
                "episode_text": "あなたと同じ35歳のとき、テスト太郎は...",
                "expected_violation": "メタ表現",
            },
            {
                "episode_id": "TEST-002",
                "person_name": "テスト花子",
                "age": 30,
                "episode_text": "30歳のとき、テスト花子は起業した。翌年には...",
                "expected_violation": "時系列矛盾",
            },
            {
                "episode_id": "TEST-003",
                "person_name": "テスト次郎",
                "age": 40,
                "episode_text": "40歳のとき、テスト次郎は新記録を達成した。",
                "expected_violation": None,  # 正常
            },
        ]

    def test_meta_expression_detection(self, sample_episodes):
        """メタ表現が検出されること"""
        meta_patterns = [r"あなたと同じ", r"あなたが", r"あなたの"]

        for ep in sample_episodes:
            text = ep["episode_text"]
            has_meta = any(re.search(p, text) for p in meta_patterns)

            if ep["expected_violation"] == "メタ表現":
                assert has_meta, f"{ep['episode_id']}: メタ表現が検出されるべき"
            elif ep["expected_violation"] is None:
                assert not has_meta, f"{ep['episode_id']}: メタ表現がないはず"

    def test_timeline_violation_detection(self, sample_episodes):
        """時系列矛盾が検出されること"""
        timeline_patterns = [r"翌年", r"翌々年", r"その後\d+年", r"数年後"]

        for ep in sample_episodes:
            text = ep["episode_text"]
            has_timeline = any(re.search(p, text) for p in timeline_patterns)

            if ep["expected_violation"] == "時系列矛盾":
                assert has_timeline, f"{ep['episode_id']}: 時系列矛盾が検出されるべき"
            elif ep["expected_violation"] is None:
                assert not has_timeline, f"{ep['episode_id']}: 時系列矛盾がないはず"

    def test_ep000006345_deleted(self):
        """EP-000006345 が削除されていること"""
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", low_memory=False)
        assert len(df[df["episode_id"] == "EP-000006345"]) == 0, "EP-000006345 は削除されているべき"

    def test_ep000000505_standard_format(self):
        """EP-000000505 が標準フォーマットに準拠していること"""
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", low_memory=False)
        ep = df[df["episode_id"] == "EP-000000505"]
        if len(ep) > 0:
            text = str(ep.iloc[0]["episode_text"])
            assert text.startswith("あなたと同じ"), "EP-000000505 は標準フォーマットで開始すべき"

    def test_ep000001326_deleted(self):
        """EP-000001326 が削除されていること（具体性欠如）"""
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", low_memory=False)
        assert len(df[df["episode_id"] == "EP-000001326"]) == 0, "EP-000001326 は削除されているべき"

    def test_ep251218185058630_deleted(self):
        """EP-251218185058630 が削除されていること（具体性欠如・たかし）"""
        df = pd.read_csv("preserved/data/MASTER_EPISODES_CURRENT.csv", low_memory=False)
        assert len(df[df["episode_id"] == "EP-251218185058630"]) == 0, "EP-251218185058630 は削除されているべき"

    def test_specificity_detection(self):
        """具体性欠如が検出されること"""
        abstract_patterns = [
            r"大きな困難",
            r"様々な問題",
            r"困難に直面",
            r"諦めることなく",
            r"解決策を見出し",
        ]

        # 低品質テキスト（具体情報なし + 抽象表現多数）
        low_quality_text = (
            "新作映画の撮影中に大きな困難に直面しました。"
            "様々な問題が発生したのです。しかし諦めることなく、"
            "解決策を見出しました。"
        )

        # 高品質テキスト（具体情報あり）
        high_quality_text = (
            "2023年、映画『首』の撮影中に大きな困難に直面しました。" "しかし諦めることなく解決策を見出しました。"
        )

        # 低品質は抽象表現3つ以上
        low_abstract = sum(1 for p in abstract_patterns if re.search(p, low_quality_text))
        assert low_abstract >= 3, "低品質テキストは抽象表現3つ以上"

        # 高品質は具体的年がある
        has_year = bool(re.search(r"(19|20)\d{2}年", high_quality_text))
        assert has_year, "高品質テキストは具体的年がある"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
