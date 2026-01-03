#!/usr/bin/env python3
"""
ImportValidationPipeline - エピソードインポート時のバリデーション統合

機能:
1. PersonNameValidator による人物名チェック
2. エピソードフォーマットチェック（リード文形式）
3. 必須フィールドチェック
4. GROUP_MEMBER_MAP との整合性チェック
5. 自動修正可能な問題の自動修正
"""

import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.validators.person_name_validator import (
    PersonNameValidator,
    Severity,
)


class ValidationLevel(Enum):
    """バリデーションレベル"""

    STRICT = "strict"  # 警告もエラー扱い
    NORMAL = "normal"  # エラーのみ失敗
    LENIENT = "lenient"  # すべて警告


@dataclass
class EpisodeIssue:
    """エピソード単位の問題"""

    episode_id: str
    row_index: int
    field: str
    issue_type: str
    severity: Severity
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    fixed_value: Optional[Any] = None


@dataclass
class PipelineResult:
    """パイプライン実行結果"""

    success: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    error_count: int
    warning_count: int
    issues: list[EpisodeIssue] = field(default_factory=list)
    auto_fixed: int = 0
    df: Optional[pd.DataFrame] = None


class ImportValidationPipeline:
    """エピソードインポートバリデーションパイプライン"""

    # リード文の正規パターン
    LEAD_PATTERN = re.compile(r"^あなたと同じ(\d+)歳のとき、")

    # 必須フィールド
    REQUIRED_FIELDS = [
        "episode_id",
        "person_id",
        "person_name",
        "age",
        "episode_text",
    ]

    # FICTIONALタイプのメタ表現パターン
    META_PATTERNS = [
        "架空の",
        "フィクション",
        "設定上",
        "作品内では",
        "公式な描写は存在しません",
        "実在しない",
        "申し訳ございませんが",
        "キャラクターです",
        "存在しません",
        "描かれていません",
        "物語の中で",
        "作品世界",
        "著作権の関係",
    ]

    def __init__(
        self,
        level: ValidationLevel = ValidationLevel.NORMAL,
        auto_fix: bool = False,
    ):
        """
        初期化

        Args:
            level: バリデーションレベル
            auto_fix: 自動修正を有効にするか
        """
        self.level = level
        self.auto_fix = auto_fix
        self.person_validator = PersonNameValidator()

    def validate(self, df: pd.DataFrame) -> PipelineResult:
        """
        DataFrameをバリデーション

        Args:
            df: 検証対象のDataFrame

        Returns:
            PipelineResult
        """
        issues: list[EpisodeIssue] = []
        df = df.copy()
        auto_fixed = 0

        for idx, row in df.iterrows():
            row_issues = self._validate_row(row, idx)

            for issue in row_issues:
                if self.auto_fix and issue.auto_fixable and issue.fixed_value is not None:
                    df.at[idx, issue.field] = issue.fixed_value
                    auto_fixed += 1
                else:
                    issues.append(issue)

        # 結果集計
        error_count = len([i for i in issues if i.severity == Severity.ERROR])
        warning_count = len([i for i in issues if i.severity == Severity.WARNING])

        # 成功判定
        if self.level == ValidationLevel.STRICT:
            success = error_count == 0 and warning_count == 0
        elif self.level == ValidationLevel.LENIENT:
            success = True
        else:
            success = error_count == 0

        invalid_episodes = set(i.episode_id for i in issues if i.severity == Severity.ERROR)

        return PipelineResult(
            success=success,
            total_rows=len(df),
            valid_rows=len(df) - len(invalid_episodes),
            invalid_rows=len(invalid_episodes),
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            auto_fixed=auto_fixed,
            df=df if self.auto_fix else None,
        )

    def _validate_row(self, row: pd.Series, idx: int) -> list[EpisodeIssue]:
        """
        1行をバリデーション

        Args:
            row: データ行
            idx: 行インデックス

        Returns:
            問題リスト
        """
        issues = []
        episode_id = str(row.get("episode_id", f"row_{idx}"))

        # 1. 必須フィールドチェック
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in row or pd.isna(row[field_name]) or str(row[field_name]).strip() == "":
                issues.append(
                    EpisodeIssue(
                        episode_id=episode_id,
                        row_index=idx,
                        field=field_name,
                        issue_type="missing_field",
                        severity=Severity.ERROR,
                        message=f"必須フィールド '{field_name}' が空です",
                    )
                )

        # 2. 人物名チェック
        person_name = str(row.get("person_name", ""))
        if person_name:
            person_issues = self.person_validator.validate(person_name)
            for pi in person_issues:
                issues.append(
                    EpisodeIssue(
                        episode_id=episode_id,
                        row_index=idx,
                        field="person_name",
                        issue_type=pi.issue_type.value,
                        severity=pi.severity,
                        message=pi.message,
                        suggestion=pi.suggestion,
                        auto_fixable=pi.auto_fixable,
                        fixed_value=pi.fixed_value,
                    )
                )

        # 3. リード文フォーマットチェック
        content = str(row.get("episode_text", ""))
        if content:
            lead_issue = self._check_lead_format(content, row.get("age"), episode_id, idx)
            if lead_issue:
                issues.append(lead_issue)

        # 4. メタ表現チェック（FICTIONALタイプの場合）
        person_type = str(row.get("person_type", "")).upper()
        if person_type == "FICTIONAL" and content:
            meta_issue = self._check_meta_expressions(content, episode_id, idx)
            if meta_issue:
                issues.append(meta_issue)

        return issues

    def _check_lead_format(
        self,
        content: str,
        age: Any,
        episode_id: str,
        idx: int,
    ) -> Optional[EpisodeIssue]:
        """
        リード文フォーマットをチェック

        Args:
            content: エピソード内容
            age: 年齢
            episode_id: エピソードID
            idx: 行インデックス

        Returns:
            問題があればEpisodeIssue
        """
        match = self.LEAD_PATTERN.match(content)

        if not match:
            return EpisodeIssue(
                episode_id=episode_id,
                row_index=idx,
                field="episode_text",
                issue_type="invalid_lead_format",
                severity=Severity.WARNING,
                message="リード文が「あなたと同じ○歳のとき、」形式ではありません",
            )

        # 年齢整合性チェック
        lead_age = int(match.group(1))
        if age is not None and not pd.isna(age):
            try:
                row_age = int(age)
                if lead_age != row_age:
                    return EpisodeIssue(
                        episode_id=episode_id,
                        row_index=idx,
                        field="episode_text",
                        issue_type="age_mismatch",
                        severity=Severity.ERROR,
                        message=f"リード文の年齢({lead_age})とage列({row_age})が不一致",
                    )
            except (ValueError, TypeError):
                pass

        return None

    def _check_meta_expressions(
        self,
        content: str,
        episode_id: str,
        idx: int,
    ) -> Optional[EpisodeIssue]:
        """
        メタ表現をチェック

        Args:
            content: エピソード内容
            episode_id: エピソードID
            idx: 行インデックス

        Returns:
            問題があればEpisodeIssue
        """
        for pattern in self.META_PATTERNS:
            if pattern in content:
                return EpisodeIssue(
                    episode_id=episode_id,
                    row_index=idx,
                    field="episode_text",
                    issue_type="meta_expression",
                    severity=Severity.ERROR,
                    message=f"メタ表現 '{pattern}' が含まれています",
                    suggestion="作品世界内の視点で書き直し",
                )

        return None

    def validate_file(self, csv_path: str) -> PipelineResult:
        """
        CSVファイルをバリデーション

        Args:
            csv_path: CSVファイルパス

        Returns:
            PipelineResult
        """
        df = pd.read_csv(csv_path)
        return self.validate(df)


def main():
    """テスト実行"""
    import argparse

    parser = argparse.ArgumentParser(description="ImportValidationPipeline")
    parser.add_argument("csv_path", help="検証対象CSVファイル")
    parser.add_argument("--strict", action="store_true", help="厳格モード")
    parser.add_argument("--auto-fix", action="store_true", help="自動修正")
    parser.add_argument("--output", help="修正後の出力ファイル")

    args = parser.parse_args()

    level = ValidationLevel.STRICT if args.strict else ValidationLevel.NORMAL
    pipeline = ImportValidationPipeline(level=level, auto_fix=args.auto_fix)

    result = pipeline.validate_file(args.csv_path)

    print("=" * 60)
    print("ImportValidationPipeline 結果")
    print("=" * 60)
    print(f"成功: {'✅' if result.success else '❌'}")
    print(f"総行数: {result.total_rows}")
    print(f"有効行: {result.valid_rows}")
    print(f"無効行: {result.invalid_rows}")
    print(f"エラー: {result.error_count}")
    print(f"警告: {result.warning_count}")
    print(f"自動修正: {result.auto_fixed}")

    if result.issues:
        print("\n問題一覧:")
        for issue in result.issues[:20]:
            severity_icon = "❌" if issue.severity == Severity.ERROR else "⚠️"
            print(f"  {severity_icon} {issue.episode_id}: {issue.message}")
        if len(result.issues) > 20:
            print(f"  ... 他{len(result.issues) - 20}件")

    if args.output and result.df is not None:
        result.df.to_csv(args.output, index=False, encoding="utf-8-sig")
        print(f"\n✅ 修正後ファイル: {args.output}")


if __name__ == "__main__":
    main()
