#!/usr/bin/env python3
"""
ダッシュボードv11のフィールド同期テスト

RCA-Kaizen対策として追加:
- update_dashboard_v11.py のJSON出力形式確認
- 翻訳関数の存在確認
- 新フィールド追加時の回帰防止

Phase 28: v10 → v11 移行、storytelling_quality → story_quality
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
UPDATE_SCRIPT = PROJECT_ROOT / "scripts/update_dashboard_v11.py"
DASHBOARD_HTML = PROJECT_ROOT / "preserved/episode_database_dashboard_v11.html"

# v11で使用される短縮キー (update_dashboard_v11.py の episode 辞書)
V11_SHORT_KEYS = [
    "id",  # episode_id
    "pid",  # person_id
    "name",  # person_name
    "age",
    "slot",
    "nd",  # nendai
    "cat",  # category
    "type",  # episode_type
    "ts",  # generation_timestamp
    "text",  # episode_text
    "etype",  # person_type (lowercase)
    "ptype",  # person_type
    "work",  # work_title
    "group",  # group_name
    "is_grp",  # is_group_member
    "ep_cnt",  # episode_count
    "fame",  # fame_score_v3
    "fame_jp",  # fame_score_japan
    "ftier",  # fame_tier
    "celeb",  # celebrity_score_v2
    "celeb_r",  # celebrity_rank_v2
    "efv6",  # episode_fame_v6
    "eftv6",  # episode_fame_tier_v6
    "super",  # super_total_score
    "comp",  # composite_score
    # 8軸スコア（短縮キー）
    "mem",  # memorability_score
    "emp",  # empathy_score
    "sur",  # surprise_score
    "gen",  # generation_quality_score
    "edu",  # educational_value
    "story",  # story_quality
    "fact",  # factual_density
    "icon",  # iconic_score
]


def extract_fields_from_update_script():
    """update_dashboard_v11.py から短縮キー名を抽出"""
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


class TestDashboardV11FieldSync:
    """ダッシュボードv11フィールド同期テスト"""

    @pytest.fixture(scope="class")
    def update_fields(self):
        """update_dashboard_v11.py のフィールド"""
        return extract_fields_from_update_script()

    @pytest.fixture(scope="class")
    def template_fields(self):
        """HTMLテンプレートで使用されるフィールド"""
        return extract_fields_from_html_template()

    @pytest.mark.parametrize("key", V11_SHORT_KEYS)
    def test_short_key_in_update_script(self, key, update_fields):
        """短縮キーがupdate_dashboard_v11.pyに存在すること"""
        assert key in update_fields, f"{key} が update_dashboard_v11.py に存在しません"

    def test_loadData_function_exists(self):
        """loadData関数が存在すること（v11: JSONからデータ読み込み）"""
        content = DASHBOARD_HTML.read_text(encoding="utf-8")
        assert "async function loadData" in content, "loadData関数が定義されていません"

    def test_applyFilters_function_exists(self):
        """applyFilters関数が存在すること"""
        content = DASHBOARD_HTML.read_text(encoding="utf-8")
        assert "function applyFilters" in content, "applyFilters関数が定義されていません"

    def test_renderPage_function_exists(self):
        """renderPage関数が存在すること"""
        content = DASHBOARD_HTML.read_text(encoding="utf-8")
        assert "function renderPage" in content, "renderPage関数が定義されていません"

    def test_iconic_score_key_exists(self, update_fields):
        """iconic_scoreの短縮キー(icon)が存在すること（Phase 28）"""
        assert "icon" in update_fields, "iconic_score短縮キー(icon)が存在しません（Phase 28）"

    def test_story_quality_key_exists(self, update_fields):
        """story_qualityの短縮キー(story)が存在すること（Phase 28）"""
        assert "story" in update_fields, "story_quality短縮キー(story)が存在しません（Phase 28）"

    def test_8axis_scores_complete(self, update_fields):
        """8軸スコアがすべて存在すること"""
        required_8axis = ["mem", "emp", "sur", "gen", "edu", "story", "fact", "icon"]
        for key in required_8axis:
            assert key in update_fields, f"8軸スコア {key} が存在しません"

    def test_template_uses_expected_fields(self, template_fields):
        """テンプレートが期待するフィールドを使用していること"""
        # 基本フィールド
        assert "name" in template_fields, "テンプレートで ep.name が使用されていません"
        assert "text" in template_fields, "テンプレートで ep.text が使用されていません"
        assert "age" in template_fields, "テンプレートで ep.age が使用されていません"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
