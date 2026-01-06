#!/usr/bin/env python3
"""
ダッシュボードv10のフィールド同期テスト

RCA-Kaizen対策として追加:
- update_dashboard_v10.py と CSVパースの同期確認
- 翻訳関数の存在確認
- 新フィールド追加時の回帰防止
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
UPDATE_SCRIPT = PROJECT_ROOT / "scripts/update_dashboard_v10.py"
DASHBOARD_HTML = PROJECT_ROOT / "preserved/episode_database_dashboard_v10.html"

# 必須フィールド（両方のソースに存在すべき）
REQUIRED_FIELDS = [
    "episode_id",
    "person_id",
    "person_name",
    "age",
    "nendai",
    "category",
    "episode_text",
    "episode_type",
    "person_type",
    "work_title",
    "group_name",
    "is_group_member",
    "episode_count",
    "fame_score",
    "fame_score_japan",
    "celebrity_score_v2",
    "celebrity_rank_v2",
    "fame_tier",
    "episode_fame_score",
    "episode_fame_v6",
    "episode_fame_tier_v6",
    "super_total_score",
    "memorability_score",
    "empathy_score",
    "surprise_score",
    "generation_quality_score",
    "educational_value",
    "storytelling_quality",
    "factual_density",
    "composite_score",
    "generation_timestamp",
]


def extract_fields_from_update_script():
    """update_dashboard_v10.py からフィールド名を抽出"""
    content = UPDATE_SCRIPT.read_text(encoding="utf-8")
    episode_pattern = r"episode\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}"
    episode_match = re.search(episode_pattern, content, re.DOTALL)
    if episode_match:
        episode_content = episode_match.group(1)
        key_pattern = r'"(\w+)":'
        matches = re.findall(key_pattern, episode_content)
        return set(matches)
    return set()


def extract_fields_from_csv_parse():
    """ダッシュボードのCSVパース部分からフィールド名を抽出"""
    content = DASHBOARD_HTML.read_text(encoding="utf-8")
    lines = content.split("\n")
    fields = set()
    in_csv_parse = False
    in_return_block = False
    brace_count = 0

    for line in lines:
        if "CSVファイルから読み込み" in line or "loadEpisodesFromCSV" in line:
            in_csv_parse = True
            continue

        if in_csv_parse:
            if "return {" in line and not in_return_block:
                in_return_block = True
                brace_count = line.count("{") - line.count("}")
                continue

            if in_return_block:
                brace_count += line.count("{") - line.count("}")
                match = re.match(r"\s*(\w+):\s*", line)
                if match:
                    field_name = match.group(1)
                    if field_name not in ["id", "const", "let", "var", "if", "return"]:
                        fields.add(field_name)

                if brace_count <= 0 and "}" in line:
                    in_return_block = False
                    if len(fields) > 10:
                        break

    return fields


class TestDashboardFieldSync:
    """ダッシュボードフィールド同期テスト"""

    @pytest.fixture(scope="class")
    def update_fields(self):
        """update_dashboard_v10.py のフィールド"""
        return extract_fields_from_update_script()

    @pytest.fixture(scope="class")
    def csv_parse_fields(self):
        """CSVパースのフィールド"""
        return extract_fields_from_csv_parse()

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_required_field_in_update_script(self, field, update_fields):
        """必須フィールドがupdate_dashboard_v10.pyに存在すること"""
        assert field in update_fields, f"{field} が update_dashboard_v10.py に存在しません"

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_required_field_in_csv_parse(self, field, csv_parse_fields):
        """必須フィールドがCSVパースに存在すること"""
        assert field in csv_parse_fields, f"{field} が CSVパースに存在しません"

    def test_getTypeLabel_function_exists(self):
        """getTypeLabel翻訳関数が存在すること"""
        content = DASHBOARD_HTML.read_text(encoding="utf-8")
        assert "const getTypeLabel" in content, "getTypeLabel関数が定義されていません"

    def test_getTypeLabel_used_in_template(self):
        """getTypeLabelがテンプレートで使用されていること"""
        content = DASHBOARD_HTML.read_text(encoding="utf-8")
        assert "getTypeLabel(ep.episode_type)" in content, "getTypeLabelがテンプレートで使用されていません"

    def test_formatGeneratedDate_function_exists(self):
        """formatGeneratedDate関数が存在すること"""
        content = DASHBOARD_HTML.read_text(encoding="utf-8")
        assert "function formatGeneratedDate" in content, "formatGeneratedDate関数が定義されていません"

    def test_formatGeneratedDate_handles_placeholder(self):
        """formatGeneratedDateがプレースホルダー日付を処理すること"""
        content = DASHBOARD_HTML.read_text(encoding="utf-8")
        assert "1900-01-01" in content, "formatGeneratedDateが1900-01-01プレースホルダーを処理していません"

    def test_generation_timestamp_in_csv_parse(self, csv_parse_fields):
        """generation_timestampがCSVパースに含まれること（RCA対策）"""
        assert (
            "generation_timestamp" in csv_parse_fields
        ), "generation_timestampがCSVパースに存在しません（RCA-Kaizen: 2026-01-06）"

    def test_episode_type_in_update_script(self, update_fields):
        """episode_typeがupdate_dashboard_v10.pyに含まれること（RCA対策）"""
        assert (
            "episode_type" in update_fields
        ), "episode_typeがupdate_dashboard_v10.pyに存在しません（RCA-Kaizen: 2026-01-06）"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
