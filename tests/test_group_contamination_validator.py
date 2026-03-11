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


class TestValidateDataframeExtended:
    """validate_dataframe関数の拡張テスト"""

    def test_empty_person_name_skipped(self):
        """空のperson_nameはスキップされる"""
        df = pd.DataFrame(
            {
                "person_id": ["P001"],
                "person_name": [""],
                "episode_id": ["E001"],
            }
        )
        issues = validate_dataframe(df)
        assert len(issues) == 0

    def test_custom_column_name(self):
        """カスタムカラム名を指定できる"""
        df = pd.DataFrame(
            {
                "person_id": ["P001"],
                "name": ["Metallica"],
                "episode_id": ["E001"],
            }
        )
        issues = validate_dataframe(df, person_name_column="name")
        assert len(issues) == 1
        assert issues[0].person_name == "Metallica"

    def test_pattern_match_issue_type(self):
        """団体名サフィックスのパターンマッチで PATTERN_MATCH タイプ"""
        df = pd.DataFrame(
            {
                "person_id": ["P001"],
                "person_name": ["テスト楽団"],
                "episode_id": ["E001"],
            }
        )
        issues = validate_dataframe(df)
        assert len(issues) == 1
        assert issues[0].issue_type == "PATTERN_MATCH"

    def test_group_entity_suggested_fix(self):
        """GROUP_ENTITY検出時にメンバー名が提案される"""
        from src.group_master import GROUP_ENTITIES, GROUP_MEMBER_MAP

        # GROUP_MEMBER_MAPに含まれるグループを見つける
        for group_name in GROUP_ENTITIES:
            members = [k for k, v in GROUP_MEMBER_MAP.items() if v == group_name]
            if members:
                df = pd.DataFrame(
                    {
                        "person_id": ["P001"],
                        "person_name": [group_name],
                        "episode_id": ["E001"],
                    }
                )
                issues = validate_dataframe(df)
                assert len(issues) == 1
                assert issues[0].issue_type == "GROUP_ENTITY"
                assert issues[0].suggested_fix is not None
                break

    def test_multiple_issues_detected(self):
        """複数の問題を検出"""
        df = pd.DataFrame(
            {
                "person_id": ["P001", "P002", "P003"],
                "person_name": ["Metallica", "テスト楽団", "山田太郎"],
                "episode_id": ["E001", "E002", "E003"],
            }
        )
        issues = validate_dataframe(df)
        assert len(issues) == 2


class TestRunContaminationCheck:
    """run_contamination_check関数のテスト"""

    def test_csv_not_found(self, tmp_path):
        """CSVファイルが存在しない場合のエラーハンドリング"""
        from src.validators.group_contamination_validator import run_contamination_check

        nonexistent = tmp_path / "nonexistent.csv"
        result = run_contamination_check(csv_path=nonexistent, save_report=False)
        assert result["status"] == "ERROR"
        assert "error" in result

    def test_clean_csv_passes(self, tmp_path):
        """問題のないCSVでPASS"""
        from src.validators.group_contamination_validator import run_contamination_check

        csv_path = tmp_path / "clean.csv"
        df = pd.DataFrame(
            {
                "person_id": ["P001", "P002"],
                "person_name": ["山田太郎", "田中花子"],
                "episode_id": ["E001", "E002"],
            }
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        result = run_contamination_check(csv_path=csv_path, save_report=False)
        assert result["status"] == "PASS"
        assert result["contamination_count"] == 0
        assert result["total_records"] == 2

    def test_contaminated_csv_fails(self, tmp_path):
        """問題のあるCSVでFAIL"""
        from src.validators.group_contamination_validator import run_contamination_check

        csv_path = tmp_path / "contaminated.csv"
        df = pd.DataFrame(
            {
                "person_id": ["P001", "P002"],
                "person_name": ["Metallica", "山田太郎"],
                "episode_id": ["E001", "E002"],
            }
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        result = run_contamination_check(csv_path=csv_path, save_report=False)
        assert result["status"] == "FAIL"
        assert result["contamination_count"] == 1

    def test_save_report_creates_file(self, tmp_path):
        """レポート保存オプションでファイルが作成される"""
        from unittest.mock import patch

        from src.validators.group_contamination_validator import run_contamination_check

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "person_id": ["P001"],
                "person_name": ["山田太郎"],
                "episode_id": ["E001"],
            }
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # レポート保存先をtmp_pathに変更
        report_dir = tmp_path / "reports"
        report_dir.mkdir()
        with patch(
            "src.validators.group_contamination_validator.PROJECT_ROOT",
            tmp_path,
        ):
            result = run_contamination_check(csv_path=csv_path, save_report=True)
        assert result["status"] == "PASS"
        # レポートパスが結果に含まれる
        if "report_path" in result:
            assert result["report_path"] is not None


class TestValidatePersonIsNotGroupExtended:
    """validate_person_is_not_group 追加テスト"""

    def test_org_suffix_en_blocked(self):
        """英語の団体名サフィックスを検出"""
        is_valid, message = validate_person_is_not_group("Apple Inc.")
        assert is_valid is False
        assert "サフィックス" in message

    def test_org_suffix_en_with_space(self):
        """英語サフィックスの前にスペースがある場合"""
        is_valid, message = validate_person_is_not_group("Microsoft Corp.")
        assert is_valid is False

    def test_exclude_suffix_personal_names(self):
        """個人名除外パターン（太郎、子等）はパスする"""
        is_valid, message = validate_person_is_not_group("田中太郎")
        assert is_valid is True

        is_valid, message = validate_person_is_not_group("鈴木花子")
        assert is_valid is True

    def test_concatenated_with_various_separators(self):
        """様々なセパレータでの連結パターン検出"""
        # 実際のGROUP_ENTITIESのグループを使用
        from src.group_master import GROUP_ENTITIES

        if "ビートルズ" in GROUP_ENTITIES:
            for sep in ["・", "（", "(", "／", "/"]:
                name = f"ビートルズ{sep}ポール"
                is_valid, message = validate_person_is_not_group(name)
                assert is_valid is False, f"Separator '{sep}' should be detected"

    def test_org_suffix_ja_various(self):
        """日本語の様々な団体サフィックス"""
        test_cases = [
            ("テスト委員会", "委員会"),
            ("テスト協会", "協会"),
            ("テスト財団", "財団"),
            ("テストバンド", "バンド"),
            ("テストユニット", "ユニット"),
        ]
        for name, suffix in test_cases:
            is_valid, message = validate_person_is_not_group(name)
            assert is_valid is False, f"Suffix '{suffix}' should be detected in '{name}'"


class TestMainFunction:
    """main() 関数のテスト"""

    def test_main_no_args(self, tmp_path, monkeypatch, capsys):
        """引数なしでmain実行（デフォルトCSV）"""
        from unittest.mock import patch

        from src.validators import group_contamination_validator

        # 存在しないデフォルトCSVパスを使う
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "person_id": ["P001"],
                "person_name": ["山田太郎"],
                "episode_id": ["E001"],
            }
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        monkeypatch.setattr("sys.argv", ["group_contamination_validator.py", "--csv", str(csv_path), "--no-report"])
        exit_code = group_contamination_validator.main()
        captured = capsys.readouterr()
        assert "団体名混入チェック結果" in captured.out
        assert exit_code == 0

    def test_main_with_issues(self, tmp_path, monkeypatch, capsys):
        """問題を含むCSVでmain実行"""
        from src.validators import group_contamination_validator

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "person_id": ["P001", "P002"],
                "person_name": ["Metallica", "山田太郎"],
                "episode_id": ["E001", "E002"],
            }
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        monkeypatch.setattr("sys.argv", ["group_contamination_validator.py", "--csv", str(csv_path), "--no-report"])
        exit_code = group_contamination_validator.main()
        captured = capsys.readouterr()
        assert "混入件数:" in captured.out
        assert "検出された問題" in captured.out
        assert exit_code == 0

    def test_main_strict_mode_fails(self, tmp_path, monkeypatch, capsys):
        """--strictモードで問題があればexit 1"""
        from src.validators import group_contamination_validator

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "person_id": ["P001"],
                "person_name": ["Metallica"],
                "episode_id": ["E001"],
            }
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        monkeypatch.setattr(
            "sys.argv",
            ["group_contamination_validator.py", "--csv", str(csv_path), "--no-report", "--strict"],
        )
        with pytest.raises(SystemExit) as exc_info:
            group_contamination_validator.main()
        assert exc_info.value.code == 1

    def test_main_strict_mode_passes(self, tmp_path, monkeypatch, capsys):
        """--strictモードで問題がなければ正常終了"""
        from src.validators import group_contamination_validator

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "person_id": ["P001"],
                "person_name": ["山田太郎"],
                "episode_id": ["E001"],
            }
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        monkeypatch.setattr(
            "sys.argv",
            ["group_contamination_validator.py", "--csv", str(csv_path), "--no-report", "--strict"],
        )
        exit_code = group_contamination_validator.main()
        assert exit_code == 0


class TestMainWithReportPath:
    """main() でレポートパスが表示されるテスト (L272)"""

    def test_main_with_report_path(self, tmp_path, monkeypatch, capsys):
        """save_report=Trueでreport_pathが表示される"""
        from unittest.mock import patch

        from src.validators import group_contamination_validator

        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "person_id": ["P001"],
                "person_name": ["山田太郎"],
                "episode_id": ["E001"],
            }
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # レポート保存先をtmp_pathに設定
        report_dir = tmp_path / "reports"
        report_dir.mkdir()

        monkeypatch.setattr(
            "sys.argv",
            ["group_contamination_validator.py", "--csv", str(csv_path)],
        )
        with patch(
            "src.validators.group_contamination_validator.PROJECT_ROOT",
            tmp_path,
        ):
            exit_code = group_contamination_validator.main()

        captured = capsys.readouterr()
        assert "レポート:" in captured.out
        assert exit_code == 0


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
