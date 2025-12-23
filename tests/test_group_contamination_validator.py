#!/usr/bin/env python3
"""
団体名混入バリデータのテスト
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.validators.group_contamination_validator import (
    ContaminationIssue,
    validate_dataframe,
    validate_person_is_not_group,
)


class TestValidatePersonIsNotGroup:
    """validate_person_is_not_group関数のテスト"""

    def test_valid_person_name(self):
        """正当な個人名はパスする"""
        is_valid, message = validate_person_is_not_group("山田太郎")
        assert is_valid is True
        assert message == ""

    def test_valid_western_name(self):
        """西洋人名はパスする"""
        is_valid, message = validate_person_is_not_group("ジョン・レノン")
        assert is_valid is True
        assert message == ""

    def test_group_entity_blocked(self):
        """GROUP_ENTITIESに登録された団体名はブロックされる"""
        is_valid, message = validate_person_is_not_group("Metallica")
        assert is_valid is False
        assert "団体名" in message

    def test_group_entity_japanese_blocked(self):
        """日本語の団体名もブロックされる"""
        is_valid, message = validate_person_is_not_group("ダウンタウン")
        assert is_valid is False
        assert "団体名" in message

    def test_concatenated_name_blocked(self):
        """グループ名+個人名の連結パターンはブロックされる"""
        is_valid, message = validate_person_is_not_group("ビートルズ・ジョン・レノン")
        assert is_valid is False
        assert "連結" in message

    def test_org_suffix_blocked(self):
        """団体名サフィックスを持つ名前はブロックされる"""
        is_valid, message = validate_person_is_not_group("東京交響楽団")
        assert is_valid is False
        assert "サフィックス" in message

    def test_exclude_pattern_passed(self):
        """除外パターンに一致する名前はパスする"""
        is_valid, message = validate_person_is_not_group("オードリー・ヘプバーン")
        assert is_valid is True
        assert message == ""

    def test_empty_name_passed(self):
        """空の名前はパスする"""
        is_valid, message = validate_person_is_not_group("")
        assert is_valid is True

    def test_none_name_passed(self):
        """Noneはパスする（内部で空文字列として処理）"""
        is_valid, message = validate_person_is_not_group(None)
        assert is_valid is True


class TestValidateDataframe:
    """validate_dataframe関数のテスト"""

    def test_clean_dataframe_no_issues(self):
        """問題のないDataFrameは空のリストを返す"""
        df = pd.DataFrame(
            {
                "person_id": ["P001", "P002"],
                "person_name": ["山田太郎", "ジョン・レノン"],
                "episode_id": ["E001", "E002"],
            }
        )
        issues = validate_dataframe(df)
        assert len(issues) == 0

    def test_contaminated_dataframe_returns_issues(self):
        """問題のあるDataFrameはIssueリストを返す"""
        df = pd.DataFrame(
            {
                "person_id": ["P001", "P002"],
                "person_name": ["山田太郎", "Metallica"],
                "episode_id": ["E001", "E002"],
            }
        )
        issues = validate_dataframe(df)
        assert len(issues) == 1
        assert issues[0].person_name == "Metallica"
        assert issues[0].issue_type == "GROUP_ENTITY"

    def test_missing_column_returns_empty(self):
        """person_nameカラムがない場合は空のリストを返す"""
        df = pd.DataFrame({"person_id": ["P001"], "name": ["山田太郎"]})
        issues = validate_dataframe(df)
        assert len(issues) == 0


class TestContaminationIssue:
    """ContaminationIssueデータクラスのテスト"""

    def test_dataclass_creation(self):
        """データクラスが正しく作成される"""
        issue = ContaminationIssue(
            person_id="P001",
            person_name="Metallica",
            episode_id="E001",
            issue_type="GROUP_ENTITY",
            message="団体名です",
            suggested_fix="James Hetfield",
        )
        assert issue.person_id == "P001"
        assert issue.person_name == "Metallica"
        assert issue.suggested_fix == "James Hetfield"


class TestIntegration:
    """統合テスト"""

    def test_all_group_entities_blocked(self):
        """GROUP_ENTITIESの全エントリがブロックされることを確認"""
        from src.group_master import GROUP_ENTITIES

        blocked_count = 0
        for entity in GROUP_ENTITIES:
            is_valid, _ = validate_person_is_not_group(entity)
            if not is_valid:
                blocked_count += 1

        # 全てブロックされるべき
        assert blocked_count == len(GROUP_ENTITIES)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
