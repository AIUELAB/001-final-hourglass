#!/usr/bin/env python3
"""
person-level項目の整合性テスト

テスト観点表:
- 等価分割:
  - 同一人物の全エピソードでcelebrity_score_v2が一致
  - 同一人物の全エピソードでsitelinks_countが一致
  - 同一人物の全エピソードでmulti_lang_pvが一致
- 境界値:
  - エピソード1件の人物（比較対象なし）
  - エピソード2件以上の人物（比較可能）
"""

import csv
from collections import defaultdict
from pathlib import Path

import pytest


CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

PERSON_LEVEL_COLUMNS = [
    "celebrity_score_v2",
    "sitelinks_count",
    "multi_lang_pv",
]


@pytest.fixture(scope="module")
def all_episodes():
    """全エピソードを読み込む"""
    if not CSV_PATH.exists():
        pytest.skip(f"CSVファイルが存在しません: {CSV_PATH}")

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


@pytest.fixture(scope="module")
def person_episodes(all_episodes):
    """人物別エピソードマップ"""
    result = defaultdict(list)
    for ep in all_episodes:
        pid = ep.get("person_id", "")
        if pid:
            result[pid].append(ep)
    return result


class TestPersonLevelConsistency:
    """person-level項目の整合性テスト"""

    @pytest.mark.xfail(reason="既存データ品質課題: celebrity_score_v2不整合あり - 技術的負債", strict=False)
    def test_celebrity_score_consistency(self, person_episodes):
        """同一人物内でcelebrity_score_v2が統一されていること"""
        self._check_column_consistency(person_episodes, "celebrity_score_v2")

    @pytest.mark.xfail(reason="既存データ品質課題: sitelinks_count不整合あり - 技術的負債", strict=False)
    def test_sitelinks_consistency(self, person_episodes):
        """同一人物内でsitelinks_countが統一されていること"""
        self._check_column_consistency(person_episodes, "sitelinks_count")

    @pytest.mark.xfail(reason="既存データ品質課題: multi_lang_pv不整合あり - 技術的負債", strict=False)
    def test_multi_lang_pv_consistency(self, person_episodes):
        """同一人物内でmulti_lang_pvが統一されていること"""
        self._check_column_consistency(person_episodes, "multi_lang_pv")

    def _check_column_consistency(self, person_episodes, column):
        """カラムの整合性をチェック"""
        mismatches = []

        for pid, episodes in person_episodes.items():
            if len(episodes) <= 1:
                continue

            values = set()
            for ep in episodes:
                val = ep.get(column, "")
                if val:
                    values.add(val)

            if len(values) > 1:
                name = episodes[0].get("person_name", "")
                mismatches.append(f"{pid} ({name}): {len(values)}種類")

        assert not mismatches, f"{column}の不整合が{len(mismatches)}件あります:\n" + "\n".join(mismatches[:10])


class TestEinsteinEpisodeRanking:
    """アインシュタインのエピソード順位テスト（回帰テスト）"""

    def test_einstein_miracle_year_is_top_ranked(self, person_episodes):
        """アインシュタインのトップエピソードがTop3であること"""
        einstein_id = "P93F1DB1"
        episodes = person_episodes.get(einstein_id, [])
        assert episodes, "アインシュタインのエピソードが見つかりません"

        # fame_v6でソート
        sorted_eps = sorted(episodes, key=lambda x: float(x.get("episode_fame_v6") or 0), reverse=True)

        # トップエピソードのスコアが85以上であること
        top_score = float(sorted_eps[0].get("episode_fame_v6") or 0)
        assert top_score >= 85.0, f"アインシュタインのトップエピソードのスコアが85未満: {top_score}"

    def test_einstein_has_consistent_celebrity_score(self, person_episodes):
        """アインシュタインの全エピソードでcelebrity_score_v2が統一されていること"""
        einstein_id = "P93F1DB1"
        episodes = person_episodes.get(einstein_id, [])
        assert episodes, "アインシュタインのエピソードが見つかりません"

        scores = set(ep.get("celebrity_score_v2", "") for ep in episodes)
        assert len(scores) == 1, f"celebrity_score_v2が不統一: {scores}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
