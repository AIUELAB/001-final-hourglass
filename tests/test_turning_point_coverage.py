#!/usr/bin/env python3
"""
転機カバレッジ回帰テスト

重要人物に転機エピソードが存在することを保証するテスト。
新規データ追加時に転機が落ちないことを検証。
"""

import csv
from collections import defaultdict
from pathlib import Path

import pytest


CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")


# テスト観点表
# =============================================================================
# 等価分割:
#   - 政治家: 大統領/首相就任エピソードが存在すること
#   - 科学者: ノーベル賞/重要発見エピソードが存在すること
#   - アスリート: 金メダル/世界記録エピソードが存在すること
#   - 芸術家: 代表作/受賞エピソードが存在すること
#   - 実業家: 創業/上場エピソードが存在すること
#
# 境界値:
#   - エピソード数が5件の人物でも転機があること
#   - エピソード数が1件の人物でも転機があること
# =============================================================================


# 重要人物と期待される転機キーワード
CRITICAL_TURNING_POINTS = [
    # (person_id, person_name, expected_keywords, description)
    # 政治家
    ("PA254CB0", "ウラジーミル・プーチン", ["大統領"], "2000年大統領初当選"),
    # 追加予定: 他の重要人物
]


@pytest.fixture(scope="module")
def all_episodes():
    """全エピソードを読み込むフィクスチャ"""
    if not CSV_PATH.exists():
        pytest.skip(f"CSVファイルが存在しません: {CSV_PATH}")

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


@pytest.fixture(scope="module")
def person_episodes(all_episodes):
    """人物別エピソードマップ"""
    person_map = defaultdict(list)
    for ep in all_episodes:
        person_id = ep.get("person_id", "")
        if person_id:
            person_map[person_id].append(ep)
    return person_map


class TestCriticalTurningPoints:
    """重要人物の転機テスト"""

    @pytest.mark.parametrize(
        "person_id,person_name,expected_keywords,description",
        CRITICAL_TURNING_POINTS,
    )
    def test_critical_turning_point_exists(
        self,
        person_episodes,
        person_id,
        person_name,
        expected_keywords,
        description,
    ):
        """重要人物に転機エピソードが存在することを確認"""
        episodes = person_episodes.get(person_id, [])
        assert episodes, f"{person_name} のエピソードが存在しません"

        # 全エピソードテキストを結合
        all_text = " ".join(ep.get("episode_text", "") for ep in episodes)

        # 期待キーワードのいずれかが含まれることを確認
        found_keywords = [kw for kw in expected_keywords if kw in all_text]
        assert (
            found_keywords
        ), f"{person_name} の転機エピソード({description})が見つかりません。期待キーワード: {expected_keywords}"


class TestPutinPresidentialElection:
    """プーチン大統領初当選テスト（具体的なケース）"""

    def test_putin_has_presidential_episode(self, person_episodes):
        """プーチンに大統領関連エピソードがあること"""
        putin_id = "PA254CB0"
        episodes = person_episodes.get(putin_id, [])
        assert len(episodes) >= 1, "プーチンのエピソードが存在しません"

        all_text = " ".join(ep.get("episode_text", "") for ep in episodes)
        assert "大統領" in all_text, "プーチンに大統領関連エピソードがありません"

    def test_putin_2000_election_episode(self, person_episodes):
        """プーチンに2000年大統領選挙エピソードがあること"""
        putin_id = "PA254CB0"
        episodes = person_episodes.get(putin_id, [])

        # 47歳のエピソードが存在すること（2000年選挙時）
        age_47_episodes = [ep for ep in episodes if ep.get("age") and abs(float(ep.get("age")) - 47.0) < 1]
        assert age_47_episodes, "プーチンの47歳（2000年）エピソードがありません"

        # 2000年/選挙関連の内容を含むこと
        text = age_47_episodes[0].get("episode_text", "")
        assert any(
            kw in text for kw in ["2000", "選挙", "大統領"]
        ), "プーチン47歳エピソードに2000年大統領選挙の内容がありません"


class TestTurningPointCoverage:
    """転機カバレッジ一般テスト"""

    def test_turning_point_keywords_defined(self):
        """転機キーワードが定義されていること"""
        from scripts.generate.generate_with_quality_gate import TURNING_POINT_KEYWORDS

        assert TURNING_POINT_KEYWORDS, "転機キーワードが定義されていません"
        assert len(TURNING_POINT_KEYWORDS) >= 10, "転機キーワードが少なすぎます"

    def test_is_critical_turning_point_function(self):
        """is_critical_turning_point関数が正しく動作すること"""
        from scripts.generate.generate_with_quality_gate import is_critical_turning_point

        # 転機を含むテキスト
        assert is_critical_turning_point("大統領に就任しました")
        assert is_critical_turning_point("ノーベル賞を受賞")
        assert is_critical_turning_point("オリンピック金メダル獲得")

        # 転機を含まないテキスト
        assert not is_critical_turning_point("日常生活を送っていた")
        assert not is_critical_turning_point("")
        assert not is_critical_turning_point(None)

    def test_episode_limit_with_turning_point_priority(self):
        """転機優先時のエピソード制限が正しく設定されていること"""
        from scripts.generate.generate_with_quality_gate import (
            EPISODE_LIMIT,
            TURNING_POINT_EXTRA_SLOTS,
        )

        assert EPISODE_LIMIT == 10, f"EPISODE_LIMITが10でない: {EPISODE_LIMIT}"
        assert TURNING_POINT_EXTRA_SLOTS >= 1, "転機追加枠が1未満"
        assert EPISODE_LIMIT + TURNING_POINT_EXTRA_SLOTS >= 11, "転機時の制限が11未満"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
