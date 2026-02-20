#!/usr/bin/env python3
"""
全件エピソード検証スクリプト

EPUPの全ルールに対して全エピソードを検証し、問題をレポート出力。

検証項目:
1. 定型パターン
2. 必須スコア欠損
3. 禁止表現
4. 年齢境界違反
5. 同一年齢重複
6. episode_fame_v6範囲
"""

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src" / "reports" / "logs"


@dataclass
class Issue:
    """検出された問題"""

    episode_id: str
    person_name: str
    age: float
    issue_type: str
    severity: str  # critical, warning, info
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckerReport:
    """検証レポート"""

    timestamp: str
    total_episodes: int
    issues: list[Issue]
    summary: dict[str, int]
    by_issue_type: dict[str, int]
    by_severity: dict[str, int]


class ComprehensiveEpisodeChecker:
    """全件エピソード検証"""

    # 定型パターン（は/の両方を許可）
    VALID_FORMAT = re.compile(r"^あなたと同じ\d+歳のとき、[^、]+(は|の)")
    INVALID_WATASHI = re.compile(r"^あなたと同じ\d+歳のとき.*私は")

    # 禁止パターン
    PROHIBITED_PATTERNS = [
        (r"のような人物です", "メタ表現"),
        (r"という記録は", "メタ表現"),
        (r"について語られています", "メタ表現"),
        (r"^\*\*.*\*\*\s*\n", "Markdownヘッダー"),
        (r"^[\d]{4}年", "年号開始"),
    ]

    # 必須スコアカラム
    REQUIRED_SCORES = [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]

    # LLMスコアカラム
    LLM_SCORES = {
        "memorability_score": "llm_memorability_score",
        "empathy_score": "llm_empathy_score",
        "surprise_score": "llm_surprise_score",
        "generation_quality_score": "llm_generation_quality_score",
        "educational_value": "llm_educational_value",
        "story_quality": "llm_story_quality",
        "factual_density": "llm_factual_density",
    }

    def __init__(self, csv_path: Path = MASTER_CSV):
        self.csv_path = csv_path
        self.df = None
        self.issues: list[Issue] = []

    def load(self):
        """CSVを読み込み"""
        self.df = pd.read_csv(self.csv_path, encoding="utf-8-sig", low_memory=False)
        return self

    def check_all(self) -> CheckerReport:
        """全件検証を実行"""
        if self.df is None:
            self.load()

        self.issues = []

        # 各検証を実行
        self._check_format()
        self._check_required_scores()
        self._check_prohibited_patterns()
        self._check_episode_fame_v6()
        self._check_age_boundary()
        self._check_same_age_duplicates()
        self._check_composite_scores()

        # レポート生成
        return self._generate_report()

    def _check_format(self):
        """定型パターン検証"""
        for idx, row in self.df.iterrows():
            text = str(row.get("episode_text", "") or "")

            # 一人称パターン
            if self.INVALID_WATASHI.match(text):
                self.issues.append(
                    Issue(
                        episode_id=row.get("episode_id", ""),
                        person_name=row.get("person_name", ""),
                        age=row.get("age", 0),
                        issue_type="format_watashi",
                        severity="critical",
                        message="一人称「私は」パターンを使用",
                        details={"text_preview": text[:100]},
                    )
                )
            # 定型パターン不一致
            elif not self.VALID_FORMAT.match(text):
                self.issues.append(
                    Issue(
                        episode_id=row.get("episode_id", ""),
                        person_name=row.get("person_name", ""),
                        age=row.get("age", 0),
                        issue_type="format_invalid",
                        severity="critical",
                        message="定型パターンで開始していない",
                        details={"text_preview": text[:100]},
                    )
                )

    def _check_required_scores(self):
        """必須スコア欠損検証"""
        for idx, row in self.df.iterrows():
            missing_scores = []

            for score_col in self.REQUIRED_SCORES:
                val = row.get(score_col)
                if pd.isna(val) or val == "":
                    # LLMカラムに値があるか確認
                    llm_col = self.LLM_SCORES.get(score_col)
                    llm_val = row.get(llm_col) if llm_col else None

                    if pd.notna(llm_val) and llm_val != "":
                        # LLMカラムには値がある→同期可能
                        missing_scores.append(f"{score_col}(llm同期可)")
                    else:
                        missing_scores.append(score_col)

            if missing_scores:
                syncable = [s for s in missing_scores if "llm同期可" in s]
                not_syncable = [s for s in missing_scores if "llm同期可" not in s]

                if not_syncable:
                    self.issues.append(
                        Issue(
                            episode_id=row.get("episode_id", ""),
                            person_name=row.get("person_name", ""),
                            age=row.get("age", 0),
                            issue_type="score_missing_critical",
                            severity="critical",
                            message=f"必須スコア欠損: {', '.join(not_syncable)}",
                            details={"missing": not_syncable},
                        )
                    )

                if syncable:
                    self.issues.append(
                        Issue(
                            episode_id=row.get("episode_id", ""),
                            person_name=row.get("person_name", ""),
                            age=row.get("age", 0),
                            issue_type="score_missing_syncable",
                            severity="warning",
                            message=f"スコア欠損（llmから同期可）: {', '.join(syncable)}",
                            details={"syncable": syncable},
                        )
                    )

    def _check_prohibited_patterns(self):
        """禁止パターン検証"""
        for idx, row in self.df.iterrows():
            text = str(row.get("episode_text", "") or "")

            for pattern, description in self.PROHIBITED_PATTERNS:
                if re.search(pattern, text):
                    self.issues.append(
                        Issue(
                            episode_id=row.get("episode_id", ""),
                            person_name=row.get("person_name", ""),
                            age=row.get("age", 0),
                            issue_type="prohibited_pattern",
                            severity="warning",
                            message=f"禁止パターン: {description}",
                            details={"pattern": pattern},
                        )
                    )

    def _check_episode_fame_v6(self):
        """episode_fame_v6範囲検証"""
        for idx, row in self.df.iterrows():
            v6 = pd.to_numeric(row.get("episode_fame_v6"), errors="coerce")
            if pd.notna(v6) and (v6 < 0 or v6 > 200):
                self.issues.append(
                    Issue(
                        episode_id=row.get("episode_id", ""),
                        person_name=row.get("person_name", ""),
                        age=row.get("age", 0),
                        issue_type="v6_out_of_range",
                        severity="warning",
                        message=f"episode_fame_v6が範囲外: {v6:.2f}",
                        details={"value": v6},
                    )
                )

    def _check_age_boundary(self):
        """年齢境界検証"""
        for idx, row in self.df.iterrows():
            age = row.get("age")
            birth_year = row.get("birth_year")
            death_year = row.get("death_year")

            if pd.notna(age) and pd.notna(birth_year):
                # エピソードの年を推定
                episode_year = int(birth_year) + int(age)

                if pd.notna(death_year) and episode_year > int(death_year):
                    self.issues.append(
                        Issue(
                            episode_id=row.get("episode_id", ""),
                            person_name=row.get("person_name", ""),
                            age=row.get("age", 0),
                            issue_type="age_boundary",
                            severity="critical",
                            message=f"死亡年({int(death_year)})以降のエピソード",
                            details={
                                "birth_year": birth_year,
                                "death_year": death_year,
                                "episode_year": episode_year,
                            },
                        )
                    )

    def _check_same_age_duplicates(self):
        """同一年齢重複検証"""
        # person_id + age でグループ化
        grouped = self.df.groupby(["person_id", "age"])

        for (person_id, age), group in grouped:
            if len(group) > 1:
                episode_ids = group["episode_id"].tolist()
                person_name = group["person_name"].iloc[0]

                self.issues.append(
                    Issue(
                        episode_id=episode_ids[0],
                        person_name=person_name,
                        age=age,
                        issue_type="same_age_duplicate",
                        severity="warning",
                        message=f"同一人物・同一年齢で{len(group)}件のエピソード",
                        details={"episode_ids": episode_ids},
                    )
                )

    def _check_composite_scores(self):
        """統合スコア検証"""
        for idx, row in self.df.iterrows():
            composite = row.get("composite_score")
            super_total = row.get("super_total_score")

            if pd.isna(composite) or composite == "":
                self.issues.append(
                    Issue(
                        episode_id=row.get("episode_id", ""),
                        person_name=row.get("person_name", ""),
                        age=row.get("age", 0),
                        issue_type="composite_missing",
                        severity="warning",
                        message="composite_score欠損",
                    )
                )

            if pd.isna(super_total) or super_total == "":
                self.issues.append(
                    Issue(
                        episode_id=row.get("episode_id", ""),
                        person_name=row.get("person_name", ""),
                        age=row.get("age", 0),
                        issue_type="super_total_missing",
                        severity="warning",
                        message="super_total_score欠損",
                    )
                )

    def _generate_report(self) -> CheckerReport:
        """レポート生成"""
        by_type = defaultdict(int)
        by_severity = defaultdict(int)

        for issue in self.issues:
            by_type[issue.issue_type] += 1
            by_severity[issue.severity] += 1

        return CheckerReport(
            timestamp=datetime.now().isoformat(),
            total_episodes=len(self.df),
            issues=self.issues,
            summary={
                "total_issues": len(self.issues),
                "critical": by_severity.get("critical", 0),
                "warning": by_severity.get("warning", 0),
                "info": by_severity.get("info", 0),
            },
            by_issue_type=dict(by_type),
            by_severity=dict(by_severity),
        )


def run_comprehensive_check(
    csv_path: Path = MASTER_CSV,
    output_report: bool = True,
    verbose: bool = False,
) -> CheckerReport:
    """
    全件検証を実行

    Args:
        csv_path: CSVファイルパス
        output_report: レポートをファイル出力するか
        verbose: 詳細ログ

    Returns:
        CheckerReport: 検証レポート
    """
    print("=" * 60)
    print("全件エピソード検証")
    print("=" * 60)
    print(f"対象: {csv_path}")
    print()

    checker = ComprehensiveEpisodeChecker(csv_path)
    report = checker.check_all()

    # サマリー出力
    print(f"総エピソード数: {report.total_episodes}")
    print(f"検出された問題: {report.summary['total_issues']}")
    print()
    print("重大度別:")
    print(f"  Critical: {report.summary['critical']}")
    print(f"  Warning: {report.summary['warning']}")
    print(f"  Info: {report.summary['info']}")
    print()
    print("問題タイプ別:")
    for issue_type, count in sorted(report.by_issue_type.items(), key=lambda x: -x[1]):
        print(f"  {issue_type}: {count}")

    # 詳細ログ
    if verbose:
        print()
        print("=" * 60)
        print("Critical Issues (最大20件)")
        print("=" * 60)
        critical_issues = [i for i in report.issues if i.severity == "critical"]
        for issue in critical_issues[:20]:
            print(f"  {issue.episode_id}: {issue.message}")
            if issue.details.get("text_preview"):
                print(f"    {issue.details['text_preview'][:50]}...")

    # レポートファイル出力
    if output_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / f"episode_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("全件エピソード検証レポート\n")
            f.write(f"生成日時: {report.timestamp}\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"総エピソード数: {report.total_episodes}\n")
            f.write(f"検出された問題: {report.summary['total_issues']}\n\n")

            f.write("重大度別:\n")
            for severity, count in report.by_severity.items():
                f.write(f"  {severity}: {count}\n")

            f.write("\n問題タイプ別:\n")
            for issue_type, count in sorted(report.by_issue_type.items(), key=lambda x: -x[1]):
                f.write(f"  {issue_type}: {count}\n")

            f.write("\n" + "=" * 60 + "\n")
            f.write("詳細\n")
            f.write("=" * 60 + "\n\n")

            for issue in report.issues[:100]:  # 最大100件
                f.write(f"[{issue.severity}] {issue.episode_id}\n")
                f.write(f"  人物: {issue.person_name}, 年齢: {issue.age}\n")
                f.write(f"  問題: {issue.message}\n")
                if issue.details:
                    f.write(f"  詳細: {issue.details}\n")
                f.write("\n")

        print()
        print(f"レポート出力: {report_path}")

    return report


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="全件エピソード検証")
    parser.add_argument(
        "--csv",
        default=str(MASTER_CSV),
        help="対象CSVファイル",
    )
    parser.add_argument("--verbose", action="store_true", help="詳細ログ")
    parser.add_argument("--no-report", action="store_true", help="レポートファイル出力しない")
    args = parser.parse_args()

    run_comprehensive_check(
        csv_path=Path(args.csv),
        output_report=not args.no_report,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
