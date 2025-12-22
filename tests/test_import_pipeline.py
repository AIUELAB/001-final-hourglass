"""
tests/test_import_pipeline.py - validators/import_pipeline.py ユニットテスト
"""

import pandas as pd
import pytest

from src.validators.import_pipeline import (
    ValidationLevel,
    EpisodeIssue,
    PipelineResult,
    ImportValidationPipeline,
)
from src.validators.person_name_validator import Severity


class TestValidationLevel:
    """ValidationLevel Enumテスト"""

    def test_strict_level(self):
        """STRICTレベル"""
        assert ValidationLevel.STRICT.value == "strict"

    def test_normal_level(self):
        """NORMALレベル"""
        assert ValidationLevel.NORMAL.value == "normal"

    def test_lenient_level(self):
        """LENIENTレベル"""
        assert ValidationLevel.LENIENT.value == "lenient"


class TestEpisodeIssue:
    """EpisodeIssueデータクラステスト"""

    def test_episode_issue_creation(self):
        """EpisodeIssue作成"""
        issue = EpisodeIssue(
            episode_id="EP001",
            row_index=0,
            field="person_name",
            issue_type="invalid_name",
            severity=Severity.ERROR,
            message="名前が無効です",
        )
        assert issue.episode_id == "EP001"
        assert issue.row_index == 0
        assert issue.severity == Severity.ERROR

    def test_episode_issue_with_suggestion(self):
        """修正提案付きEpisodeIssue"""
        issue = EpisodeIssue(
            episode_id="EP002",
            row_index=1,
            field="episode_text",
            issue_type="format_error",
            severity=Severity.WARNING,
            message="フォーマットエラー",
            suggestion="修正してください",
            auto_fixable=True,
            fixed_value="修正後の値",
        )
        assert issue.suggestion == "修正してください"
        assert issue.auto_fixable is True
        assert issue.fixed_value == "修正後の値"


class TestPipelineResult:
    """PipelineResultデータクラステスト"""

    def test_pipeline_result_creation(self):
        """PipelineResult作成"""
        result = PipelineResult(
            success=True,
            total_rows=100,
            valid_rows=95,
            invalid_rows=5,
            error_count=3,
            warning_count=2,
        )
        assert result.success is True
        assert result.total_rows == 100
        assert result.valid_rows == 95

    def test_pipeline_result_with_issues(self):
        """問題付きPipelineResult"""
        issue = EpisodeIssue(
            episode_id="EP001",
            row_index=0,
            field="test",
            issue_type="test",
            severity=Severity.WARNING,
            message="テスト",
        )
        result = PipelineResult(
            success=False,
            total_rows=10,
            valid_rows=9,
            invalid_rows=1,
            error_count=0,
            warning_count=1,
            issues=[issue],
        )
        assert len(result.issues) == 1


class TestImportValidationPipelineInit:
    """ImportValidationPipeline初期化テスト"""

    def test_init_default(self):
        """デフォルト初期化"""
        pipeline = ImportValidationPipeline()
        assert pipeline.level == ValidationLevel.NORMAL
        assert pipeline.auto_fix is False

    def test_init_strict(self):
        """STRICTモード初期化"""
        pipeline = ImportValidationPipeline(level=ValidationLevel.STRICT)
        assert pipeline.level == ValidationLevel.STRICT

    def test_init_with_auto_fix(self):
        """自動修正有効で初期化"""
        pipeline = ImportValidationPipeline(auto_fix=True)
        assert pipeline.auto_fix is True

    def test_lead_pattern_exists(self):
        """リード文パターン存在確認"""
        pipeline = ImportValidationPipeline()
        assert pipeline.LEAD_PATTERN is not None

    def test_required_fields(self):
        """必須フィールド確認"""
        pipeline = ImportValidationPipeline()
        assert "episode_id" in pipeline.REQUIRED_FIELDS
        assert "person_name" in pipeline.REQUIRED_FIELDS
        assert "episode_text" in pipeline.REQUIRED_FIELDS

    def test_meta_patterns(self):
        """メタ表現パターン確認"""
        pipeline = ImportValidationPipeline()
        assert "架空の" in pipeline.META_PATTERNS
        assert "フィクション" in pipeline.META_PATTERNS


class TestValidate:
    """validateメソッドテスト"""

    def test_validate_valid_dataframe(self):
        """正常なDataFrameのバリデーション"""
        pipeline = ImportValidationPipeline()
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["テスト太郎"],
            "age": [30],
            "episode_text": ["あなたと同じ30歳のとき、テスト太郎は活躍した。"],
            "person_type": ["REAL"],
        })
        result = pipeline.validate(df)
        assert result.total_rows == 1

    def test_validate_missing_required_field(self):
        """必須フィールド欠損"""
        pipeline = ImportValidationPipeline()
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": [""],  # 空
            "age": [30],
            "episode_text": ["テスト"],
        })
        result = pipeline.validate(df)
        assert result.error_count > 0

    def test_validate_strict_mode(self):
        """STRICTモードでのバリデーション"""
        pipeline = ImportValidationPipeline(level=ValidationLevel.STRICT)
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["テスト"],
            "age": [30],
            "episode_text": ["フォーマット違反のテキスト"],  # 警告発生
        })
        result = pipeline.validate(df)
        # STRICTモードでは警告もエラー扱い
        if result.warning_count > 0:
            assert result.success is False

    def test_validate_lenient_mode(self):
        """LENIENTモードでのバリデーション"""
        pipeline = ImportValidationPipeline(level=ValidationLevel.LENIENT)
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["テスト"],
            "age": [30],
            "episode_text": ["テスト"],
        })
        result = pipeline.validate(df)
        # LENIENTモードではすべて成功
        assert result.success is True


class TestCheckLeadFormat:
    """_check_lead_formatメソッドテスト"""

    def test_valid_lead_format(self):
        """正しいリード文フォーマット"""
        pipeline = ImportValidationPipeline()
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["テスト"],
            "age": [25],
            "episode_text": ["あなたと同じ25歳のとき、テストは成功した。"],
        })
        result = pipeline.validate(df)
        lead_issues = [i for i in result.issues if i.issue_type == "invalid_lead_format"]
        assert len(lead_issues) == 0

    def test_invalid_lead_format(self):
        """無効なリード文フォーマット"""
        pipeline = ImportValidationPipeline()
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["テスト"],
            "age": [25],
            "episode_text": ["これはリード文形式ではありません。"],
        })
        result = pipeline.validate(df)
        lead_issues = [i for i in result.issues if i.issue_type == "invalid_lead_format"]
        assert len(lead_issues) > 0

    def test_age_mismatch(self):
        """年齢不一致"""
        pipeline = ImportValidationPipeline()
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["テスト"],
            "age": [30],  # 30歳
            "episode_text": ["あなたと同じ25歳のとき、テスト。"],  # リード文は25歳
        })
        result = pipeline.validate(df)
        age_issues = [i for i in result.issues if i.issue_type == "age_mismatch"]
        assert len(age_issues) > 0


class TestCheckMetaExpressions:
    """_check_meta_expressionsメソッドテスト"""

    def test_no_meta_expression_real(self):
        """REALタイプでメタ表現なし"""
        pipeline = ImportValidationPipeline()
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["テスト"],
            "age": [30],
            "episode_text": ["あなたと同じ30歳のとき、テストは活躍した。"],
            "person_type": ["REAL"],
        })
        result = pipeline.validate(df)
        meta_issues = [i for i in result.issues if i.issue_type == "meta_expression"]
        assert len(meta_issues) == 0

    def test_meta_expression_in_fictional(self):
        """FICTIONALタイプでメタ表現検出"""
        pipeline = ImportValidationPipeline()
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["キャラ"],
            "age": [20],
            "episode_text": ["あなたと同じ20歳のとき、これは架空のキャラクターです。"],
            "person_type": ["FICTIONAL"],
        })
        result = pipeline.validate(df)
        meta_issues = [i for i in result.issues if i.issue_type == "meta_expression"]
        assert len(meta_issues) > 0


class TestValidateRow:
    """_validate_rowメソッドテスト"""

    def test_validate_row_all_fields_present(self):
        """全フィールド存在時のバリデーション"""
        pipeline = ImportValidationPipeline()
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["正常な名前"],
            "age": [35],
            "episode_text": ["あなたと同じ35歳のとき、正常な名前は活躍した。"],
            "person_type": ["REAL"],
        })
        result = pipeline.validate(df)
        missing_issues = [i for i in result.issues if i.issue_type == "missing_field"]
        assert len(missing_issues) == 0

    def test_validate_row_missing_episode_id(self):
        """episode_id欠損"""
        pipeline = ImportValidationPipeline()
        df = pd.DataFrame({
            "episode_id": [None],
            "person_id": ["P001"],
            "person_name": ["テスト"],
            "age": [30],
            "episode_text": ["テスト"],
        })
        result = pipeline.validate(df)
        missing_issues = [i for i in result.issues if i.issue_type == "missing_field"]
        assert len(missing_issues) > 0


class TestAutoFix:
    """自動修正テスト"""

    def test_auto_fix_disabled(self):
        """自動修正無効"""
        pipeline = ImportValidationPipeline(auto_fix=False)
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["テスト"],
            "age": [30],
            "episode_text": ["テスト"],
        })
        result = pipeline.validate(df)
        assert result.df is None

    def test_auto_fix_enabled(self):
        """自動修正有効"""
        pipeline = ImportValidationPipeline(auto_fix=True)
        df = pd.DataFrame({
            "episode_id": ["EP001"],
            "person_id": ["P001"],
            "person_name": ["テスト"],
            "age": [30],
            "episode_text": ["あなたと同じ30歳のとき、テストは成功した。"],
        })
        result = pipeline.validate(df)
        # 自動修正有効時はdfが返される
        assert result.df is not None


class TestResultCounts:
    """結果カウントテスト"""

    def test_count_valid_and_invalid(self):
        """有効・無効行数カウント"""
        pipeline = ImportValidationPipeline()
        df = pd.DataFrame({
            "episode_id": ["EP001", "EP002"],
            "person_id": ["P001", "P002"],
            "person_name": ["テスト1", ""],  # 2行目は無効
            "age": [30, 25],
            "episode_text": ["あなたと同じ30歳のとき、テスト1は成功。", "テスト"],
        })
        result = pipeline.validate(df)
        assert result.total_rows == 2
        assert result.invalid_rows >= 1
