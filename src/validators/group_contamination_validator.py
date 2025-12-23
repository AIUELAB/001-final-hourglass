#!/usr/bin/env python3
"""
団体名混入バリデータ

エピソードの主語（person_name）に団体・グループ名が混入していないかを検証し、
登録前にブロック/登録後にアラートを発する品質ゲート。

機能:
1. 登録前ブロック: validate_person_is_not_group()
2. バッチ検証: validate_dataframe()
3. CI用検証: run_contamination_check()

Usage:
    # 単一検証（登録前）
    >>> from src.validators.group_contamination_validator import validate_person_is_not_group
    >>> is_valid, message = validate_person_is_not_group("Metallica")
    >>> assert is_valid is False

    # バッチ検証
    >>> from src.validators.group_contamination_validator import validate_dataframe
    >>> issues = validate_dataframe(df)
    >>> assert len(issues) == 0

    # CI用検証
    >>> from src.validators.group_contamination_validator import run_contamination_check
    >>> result = run_contamination_check()
    >>> assert result["contamination_count"] == 0
"""

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.group_master import GROUP_ENTITIES, GROUP_MEMBER_MAP

# 誤検出除外パターン（グループ名と同名だが個人名として正しいもの）
EXCLUDE_PERSON_NAMES = {
    # お笑いコンビ「オードリー」と同名の外国人名
    "オードリー・ヘプバーン",
    "オードリー・タトゥ",
    "オードリー・ヘップバーン",
}

# マスターCSVパス
MASTER_CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


@dataclass
class ContaminationIssue:
    """団体名混入問題"""

    person_id: str
    person_name: str
    episode_id: str
    issue_type: str  # "GROUP_ENTITY" | "CONCATENATED" | "PATTERN_MATCH"
    message: str
    suggested_fix: Optional[str] = None


def validate_person_is_not_group(person_name: str) -> tuple[bool, str]:
    """
    単一の人物名が団体名でないことを検証（登録前ブロック用）

    Args:
        person_name: 検証対象の人物名

    Returns:
        (is_valid, message) - 問題なければ(True, ""), 問題あれば(False, エラーメッセージ)
    """
    if not person_name:
        return True, ""

    person_name = str(person_name).strip()

    # 除外パターンをチェック（グループ名と同名だが正当な個人名）
    if person_name in EXCLUDE_PERSON_NAMES:
        return True, ""

    # 1. GROUP_ENTITIESに直接一致
    if person_name in GROUP_ENTITIES:
        return False, f"団体名 '{person_name}' は person_name として登録できません"

    # 2. グループ名＋個人名の連結パターン
    separators = ["・", "（", "(", "／", "/", "　", " "]
    for group in GROUP_ENTITIES:
        for sep in separators:
            prefix = f"{group}{sep}"
            if person_name.startswith(prefix):
                individual = person_name[len(prefix) :].rstrip("）)")
                if individual:
                    return (
                        False,
                        f"グループ名 '{group}' と個人名 '{individual}' が連結されています",
                    )

    # 3. 団体名サフィックスパターン
    org_suffixes_ja = (
        "グループ",
        "劇団",
        "楽団",
        "オーケストラ",
        "会社",
        "株式会社",
        "チーム",
        "委員会",
        "協会",
        "財団",
        "バンド",
        "ユニット",
        "デュオ",
        "トリオ",
    )
    org_suffixes_en = (
        "Inc.",
        "Corp.",
        "Ltd.",
        "LLC",
        "Group",
        "Team",
        "Band",
        "Orchestra",
    )

    # 個人名除外パターン
    exclude_suffixes = ("太郎", "次郎", "三郎", "一郎", "子", "美", "香", "恵")
    if any(person_name.endswith(s) for s in exclude_suffixes):
        return True, ""

    for suffix in org_suffixes_ja:
        if person_name.endswith(suffix):
            return False, f"団体名サフィックス '{suffix}' が検出されました"

    for suffix in org_suffixes_en:
        if person_name.endswith(suffix) or person_name.endswith(f" {suffix}"):
            return False, f"団体名サフィックス '{suffix}' が検出されました"

    return True, ""


def validate_dataframe(df: pd.DataFrame, person_name_column: str = "person_name") -> list[ContaminationIssue]:
    """
    DataFrameの全レコードを検証

    Args:
        df: 検証対象のDataFrame
        person_name_column: 人物名カラム名

    Returns:
        検出された問題のリスト
    """
    issues: list[ContaminationIssue] = []

    if person_name_column not in df.columns:
        return issues

    for _, row in df.iterrows():
        person_name = str(row.get(person_name_column, "")).strip()
        if not person_name:
            continue

        is_valid, message = validate_person_is_not_group(person_name)
        if not is_valid:
            # 問題タイプを判定
            if person_name in GROUP_ENTITIES:
                issue_type = "GROUP_ENTITY"
                # GROUP_MEMBER_MAPから代表メンバーを提案
                members = [k for k, v in GROUP_MEMBER_MAP.items() if v == person_name]
                suggested_fix = members[0] if members else None
            else:
                issue_type = "PATTERN_MATCH"
                suggested_fix = None

            issues.append(
                ContaminationIssue(
                    person_id=str(row.get("person_id", "")),
                    person_name=person_name,
                    episode_id=str(row.get("episode_id", "")),
                    issue_type=issue_type,
                    message=message,
                    suggested_fix=suggested_fix,
                )
            )

    return issues


def run_contamination_check(
    csv_path: Optional[Path] = None,
    save_report: bool = True,
) -> dict:
    """
    マスターCSVの団体名混入チェック（CI/監視用）

    Args:
        csv_path: 検証対象CSVパス（デフォルト: マスターCSV）
        save_report: レポートを保存するか

    Returns:
        {
            "timestamp": str,
            "total_records": int,
            "contamination_count": int,
            "status": "PASS" | "FAIL",
            "issues": list[dict],
            "report_path": Optional[str]
        }
    """
    csv_path = csv_path or MASTER_CSV_PATH

    if not csv_path.exists():
        return {
            "timestamp": datetime.now().isoformat(),
            "error": f"CSV not found: {csv_path}",
            "status": "ERROR",
        }

    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    issues = validate_dataframe(df)

    result = {
        "timestamp": datetime.now().isoformat(),
        "csv_path": str(csv_path),
        "total_records": len(df),
        "unique_persons": df["person_name"].nunique(),
        "contamination_count": len(issues),
        "status": "PASS" if len(issues) == 0 else "FAIL",
        "issues": [asdict(issue) for issue in issues[:50]],  # 最大50件
    }

    if save_report:
        report_dir = PROJECT_ROOT / "src" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"group_contamination_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        result["report_path"] = str(report_path)

    return result


def main():
    """CLIエントリーポイント"""
    import argparse

    parser = argparse.ArgumentParser(description="団体名混入チェック")
    parser.add_argument("--csv", type=str, help="対象CSVパス")
    parser.add_argument("--no-report", action="store_true", help="レポート保存をスキップ")
    parser.add_argument("--strict", action="store_true", help="1件でも検出したらexit 1")
    args = parser.parse_args()

    csv_path = Path(args.csv) if args.csv else None
    result = run_contamination_check(csv_path=csv_path, save_report=not args.no_report)

    print("=" * 60)
    print("団体名混入チェック結果")
    print("=" * 60)
    print(f"実行時刻: {result['timestamp']}")
    print(f"総レコード数: {result.get('total_records', 'N/A')}")
    print(f"混入件数: {result['contamination_count']}")
    print(f"ステータス: {result['status']}")

    if result.get("report_path"):
        print(f"レポート: {result['report_path']}")

    if result["issues"]:
        print("\n検出された問題（先頭10件）:")
        for issue in result["issues"][:10]:
            print(f"  - {issue['person_name']}: {issue['message']}")

    if args.strict and result["status"] == "FAIL":
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
