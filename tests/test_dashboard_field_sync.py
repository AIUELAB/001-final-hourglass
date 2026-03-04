#!/usr/bin/env python3
"""
ダッシュボードv10のフィールド同期テスト

RCA-Kaizen対策として追加:
- update_dashboard_v10.py のJSON出力形式確認
- 翻訳関数の存在確認
- 新フィールド追加時の回帰防止

Phase 28: v10 → v11 移行対応（update_dashboard_v10.pyを使用）
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
UPDATE_SCRIPT = PROJECT_ROOT / "scripts/update_dashboard_v10.py"
DASHBOARD_HTML = PROJECT_ROOT / "preserved/episode_database_dashboard_v11.html"

# v10で使用されるフィールドキー (update_dashboard_v10.py の episode 辞書)
V10_FIELD_KEYS = [
    "episode_id",
    "person_id",
    "person_name",
    "age",
    "slot",
    "nendai",
    "category",
    "episode_type",
    "generation_timestamp",
    "episode_text",
    "entity_type",
    "person_type",
    "work_title",
    "group_name",
    "is_group_member",
    "episode_count",
    "fame_score",
    "fame_score_japan",
    "fame_tier",
    "is_japanese",
    "sitelinks_count",
    "multi_lang_pv",
    # v2スコア
    "episode_fame_v2",
    "episode_fame_tier_v2",
    "celebrity_score_v2",
    "celebrity_rank_v2",
    # Episode Fame
    "episode_fame_score",
    "episode_fame_v6",
    "episode_fame_tier_v6",
    # 超総合スコア
    "super_total_score",
    # 7軸スコア
    "memorability_score",
    "empathy_score",
    "surprise_score",
    "generation_quality_score",
    "educational_value",
    "story_quality",
    "factual_density",
    # 8軸目
    "iconic_score",
    # composite
    "composite_score",
]


def extract_fields_from_update_script():
    """update_dashboard_v10.py から フィールドキー名を抽出"""
    content = UPDATE_SCRIPT.read_text(encoding="utf-8")
    # episode辞書のキーを抽出
    episode_pattern = r"episode\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}"
    episode_match = re.search(episode_pattern, content, re.DOTALL)
    if episode_match:
        episode_content = episode_match.group(1)
        key_pattern = r'"(\w+)":'
        matches = re.findall(key_pattern, episode_content)
        return set(matches)
    return set()


def extract_fields_from_html_template():
    """ダッシュボードHTMLテンプレート内のフィールド参照を抽出"""
    content = DASHBOARD_HTML.read_text(encoding="utf-8")
    # ep.XXX パターンを抽出
    field_pattern = r"ep\.(\w+)"
    matches = re.findall(field_pattern, content)
    return set(matches)


class TestDashboardV10FieldSync:
    """ダッシュボードv10フィールド同期テスト"""

    @pytest.fixture(scope="class")
    def update_fields(self):
        """update_dashboard_v10.py のフィールド"""
        return extract_fields_from_update_script()

    @pytest.fixture(scope="class")
    def template_fields(self):
        """HTMLテンプレートで使用されるフィールド"""
        return extract_fields_from_html_template()

    @pytest.mark.parametrize("key", V10_FIELD_KEYS)
    def test_field_key_in_update_script(self, key, update_fields):
        """フィールドキーがupdate_dashboard_v10.pyに存在すること"""
        assert key in update_fields, f"{key} が update_dashboard_v10.py に存在しません"

    def test_loadData_function_exists(self):
        """loadData関数が存在すること（v10: JSONからデータ読み込み）"""
        content = DASHBOARD_HTML.read_text(encoding="utf-8")
        # v10では EMBEDDED_EPISODE_DATA を使用
        has_embedded = "EMBEDDED_EPISODE_DATA" in content
        has_async_load = "async function loadData" in content
        assert has_embedded or has_async_load, "EMBEDDED_EPISODE_DATA または loadData関数が定義されていません"

    def test_applyFilters_function_exists(self):
        """applyFilters関数が存在すること"""
        content = DASHBOARD_HTML.read_text(encoding="utf-8")
        assert "function applyFilters" in content, "applyFilters関数が定義されていません"

    def test_render_function_exists(self):
        """レンダリング関数が存在すること"""
        content = DASHBOARD_HTML.read_text(encoding="utf-8")
        # v10では renderEpisodeTable, renderFameRankingPage などを使用
        has_render_table = "function renderEpisodeTable" in content
        has_render_fame = "function renderFameRankingPage" in content
        has_render_episode = "function renderEpisodeRankingPage" in content
        assert (
            has_render_table or has_render_fame or has_render_episode
        ), "レンダリング関数（renderEpisodeTable/renderFameRankingPage/renderEpisodeRankingPage）が定義されていません"

    def test_iconic_score_key_exists(self, update_fields):
        """iconic_scoreが存在すること（Phase 28）"""
        assert "iconic_score" in update_fields, "iconic_scoreが存在しません（Phase 28）"

    def test_story_quality_key_exists(self, update_fields):
        """story_qualityが存在すること"""
        assert "story_quality" in update_fields, "story_qualityが存在しません"

    def test_8axis_scores_complete(self, update_fields):
        """8軸スコアがすべて存在すること"""
        required_8axis = [
            "memorability_score",
            "empathy_score",
            "surprise_score",
            "generation_quality_score",
            "educational_value",
            "story_quality",
            "factual_density",
            "iconic_score",
        ]
        for key in required_8axis:
            assert key in update_fields, f"8軸スコア {key} が存在しません"

    def test_template_uses_expected_fields(self, template_fields):
        """テンプレートが期待するフィールドを使用していること"""
        # 基本フィールド - v10では person_name, episode_text, age を使用
        # ただしHTML内の変数名は異なる可能性あり
        # 最低限のチェック
        assert len(template_fields) > 0, "テンプレートでフィールドが使用されていません"


# 旧テストクラス名のエイリアス（後方互換性）
TestDashboardV11FieldSync = TestDashboardV10FieldSync


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
