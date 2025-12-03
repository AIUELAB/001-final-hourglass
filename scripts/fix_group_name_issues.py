#!/usr/bin/env python3
"""
グループ名問題の統合検出・修正スクリプト

問題パターン:
1. グループ名が人物名として登録（ビートルズ、AKB48等）
2. 「グループ名・個人名」連結パターン（嵐・大野智等）
3. 同一人物が複数IDで登録

EPUP 7ステップに基づく修正フロー:
1. 検出（問題レコードの特定）
2. 分散ルールに基づく処理決定
3. LLMによるエピソード再生成
4. CSV更新
5. レポート出力
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.group_master import (
    GROUP_ENTITIES,
    GROUP_MEMBER_MAP,
    DISPERSION_RULES,
    DispersionStrategy,
    get_group_info,
    get_dispersion_rule,
    get_group_members,
)


# ========================================
# 定数
# ========================================

CSV_PATH = "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = "reports"
CONCAT_DELIMITERS = ["・", "/", "･", "・"]  # 連結名区切り文字

# 誤検出除外リスト（人物名全体がこれに一致する場合は連結名として扱わない）
EXCLUDE_FROM_CONCATENATION = {
    # 「オードリー」を含むが、お笑いコンビではなく女優・俳優の名前
    "オードリー・ヘプバーン",
    "Audrey Hepburn",
    # 同様の誤検出を防ぐ追加
    "マリリン・モンロー",
    "ジャッキー・チェン",
    "ブルース・リー",
}


# ========================================
# データクラス
# ========================================


@dataclass
class DetectedIssue:
    """検出された問題"""

    episode_id: str
    person_id: str
    person_name: str
    issue_type: str  # GROUP_AS_PERSON, CONCATENATED_NAME
    detected_group: Optional[str] = None
    detected_individual: Optional[str] = None
    suggested_action: str = ""
    row_index: int = -1


@dataclass
class FixResult:
    """修正結果"""

    episode_id: str
    issue_type: str
    original_name: str
    fixed_name: str
    action: str  # dispersed, split, deleted, skipped
    details: str = ""


# ========================================
# 検出ロジック
# ========================================


def detect_group_as_person(df: pd.DataFrame) -> List[DetectedIssue]:
    """パターン1: グループ名が人物名として登録されているケースを検出"""
    issues = []

    for idx, row in df.iterrows():
        person_name = str(row.get("person_name", "")).strip()
        if not person_name:
            continue

        if person_name in GROUP_ENTITIES:
            rule = get_dispersion_rule(person_name)
            if rule:
                action = (
                    f"disperse_to_{len(rule.members)}_members"
                    if rule.strategy != DispersionStrategy.DELETE
                    else "delete"
                )
            else:
                action = "disperse_or_delete"

            issues.append(
                DetectedIssue(
                    episode_id=str(row.get("episode_id", "")),
                    person_id=str(row.get("person_id", "")),
                    person_name=person_name,
                    issue_type="GROUP_AS_PERSON",
                    detected_group=person_name,
                    suggested_action=action,
                    row_index=idx,
                )
            )

    return issues


def parse_concatenated_name(name: str) -> Tuple[Optional[str], str]:
    """連結名を分解: (グループ名, 個人名) または (None, 元の名前)"""
    for delim in CONCAT_DELIMITERS:
        if delim in name:
            parts = name.split(delim, 1)
            if len(parts) == 2:
                left, right = parts[0].strip(), parts[1].strip()
                # 左側がグループ名かどうか確認
                if left in GROUP_ENTITIES:
                    return (left, right)
                # GROUP_MEMBER_MAPで右側が登録されているか確認
                if right in GROUP_MEMBER_MAP:
                    expected_group = GROUP_MEMBER_MAP[right]
                    if left == expected_group or left in expected_group:
                        return (left, right)
    return (None, name)


def detect_concatenated_names(df: pd.DataFrame) -> List[DetectedIssue]:
    """パターン2: 「グループ名・個人名」連結パターンを検出"""
    issues = []

    for idx, row in df.iterrows():
        person_name = str(row.get("person_name", "")).strip()
        if not person_name:
            continue

        # 除外リストチェック
        if person_name in EXCLUDE_FROM_CONCATENATION:
            continue

        group_name, individual_name = parse_concatenated_name(person_name)

        if group_name is not None:
            issues.append(
                DetectedIssue(
                    episode_id=str(row.get("episode_id", "")),
                    person_id=str(row.get("person_id", "")),
                    person_name=person_name,
                    issue_type="CONCATENATED_NAME",
                    detected_group=group_name,
                    detected_individual=individual_name,
                    suggested_action="split_to_individual",
                    row_index=idx,
                )
            )

    return issues


def detect_all_issues(df: pd.DataFrame) -> Dict[str, List[DetectedIssue]]:
    """全問題パターンを検出"""
    return {
        "group_as_person": detect_group_as_person(df),
        "concatenated_names": detect_concatenated_names(df),
    }


# ========================================
# 修正ロジック
# ========================================


def fix_group_as_person(df: pd.DataFrame, issue: DetectedIssue, dry_run: bool = True) -> List[FixResult]:
    """グループ名を個人に分散または削除"""
    results = []
    group_name = issue.person_name

    rule = get_dispersion_rule(group_name)

    if rule is None:
        # ルール未定義の場合、削除
        if not dry_run:
            df.drop(issue.row_index, inplace=True)
        results.append(
            FixResult(
                episode_id=issue.episode_id,
                issue_type="GROUP_AS_PERSON",
                original_name=group_name,
                fixed_name="(deleted)",
                action="deleted",
                details="分散ルール未定義のため削除",
            )
        )
        return results

    if rule.strategy == DispersionStrategy.DELETE:
        # 削除戦略
        if not dry_run:
            df.drop(issue.row_index, inplace=True)
        results.append(
            FixResult(
                episode_id=issue.episode_id,
                issue_type="GROUP_AS_PERSON",
                original_name=group_name,
                fixed_name="(deleted)",
                action="deleted",
                details="DELETE戦略により削除",
            )
        )
    else:
        # 分散戦略（ALL or REPRESENTATIVE）
        # 最初のメンバーに変換（他のメンバーは新規エピソード生成が必要）
        if rule.members:
            first_member = rule.members[0]
            if not dry_run:
                df.at[issue.row_index, "person_name"] = first_member
                df.at[issue.row_index, "group_name"] = group_name
                df.at[issue.row_index, "is_group_member"] = True

            results.append(
                FixResult(
                    episode_id=issue.episode_id,
                    issue_type="GROUP_AS_PERSON",
                    original_name=group_name,
                    fixed_name=first_member,
                    action="dispersed",
                    details=f'代表メンバー({first_member})に変換。他メンバー: {rule.members[1:] if len(rule.members) > 1 else "なし"}',
                )
            )
        else:
            # メンバーリストが空の場合、GROUP_MEMBER_MAPから取得
            members = get_group_members(group_name)
            if members:
                first_member = members[0]
                if not dry_run:
                    df.at[issue.row_index, "person_name"] = first_member
                    df.at[issue.row_index, "group_name"] = group_name
                    df.at[issue.row_index, "is_group_member"] = True

                results.append(
                    FixResult(
                        episode_id=issue.episode_id,
                        issue_type="GROUP_AS_PERSON",
                        original_name=group_name,
                        fixed_name=first_member,
                        action="dispersed",
                        details=f"GROUP_MEMBER_MAPから代表メンバー({first_member})に変換",
                    )
                )
            else:
                # メンバー情報がない場合はスキップ
                results.append(
                    FixResult(
                        episode_id=issue.episode_id,
                        issue_type="GROUP_AS_PERSON",
                        original_name=group_name,
                        fixed_name=group_name,
                        action="skipped",
                        details="メンバー情報なし、手動対応が必要",
                    )
                )

    return results


def fix_concatenated_name(df: pd.DataFrame, issue: DetectedIssue, dry_run: bool = True) -> FixResult:
    """連結名を個人名のみに修正"""
    individual_name = issue.detected_individual
    group_name = issue.detected_group

    if individual_name and individual_name != issue.person_name:
        if not dry_run:
            df.at[issue.row_index, "person_name"] = individual_name
            df.at[issue.row_index, "group_name"] = group_name
            df.at[issue.row_index, "is_group_member"] = True

        return FixResult(
            episode_id=issue.episode_id,
            issue_type="CONCATENATED_NAME",
            original_name=issue.person_name,
            fixed_name=individual_name,
            action="split",
            details=f"グループ名({group_name})を除去し個人名のみに",
        )
    else:
        return FixResult(
            episode_id=issue.episode_id,
            issue_type="CONCATENATED_NAME",
            original_name=issue.person_name,
            fixed_name=issue.person_name,
            action="skipped",
            details="分解できませんでした",
        )


def fix_all_issues(df: pd.DataFrame, issues: Dict[str, List[DetectedIssue]], dry_run: bool = True) -> List[FixResult]:
    """全問題を修正"""
    results = []

    # グループ名問題
    for issue in issues["group_as_person"]:
        results.extend(fix_group_as_person(df, issue, dry_run))

    # 連結名問題
    for issue in issues["concatenated_names"]:
        results.append(fix_concatenated_name(df, issue, dry_run))

    return results


# ========================================
# レポート生成
# ========================================


def generate_report(issues: Dict[str, List[DetectedIssue]], results: List[FixResult]) -> Dict:
    """修正レポートを生成"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "group_as_person": {
                "detected": len(issues["group_as_person"]),
                "fixed": len([r for r in results if r.issue_type == "GROUP_AS_PERSON" and r.action != "skipped"]),
            },
            "concatenated_names": {
                "detected": len(issues["concatenated_names"]),
                "fixed": len([r for r in results if r.issue_type == "CONCATENATED_NAME" and r.action != "skipped"]),
            },
        },
        "issues": {
            "group_as_person": [asdict(i) for i in issues["group_as_person"]],
            "concatenated_names": [asdict(i) for i in issues["concatenated_names"]],
        },
        "results": [asdict(r) for r in results],
    }
    return report


# ========================================
# メイン処理
# ========================================


def main():
    parser = argparse.ArgumentParser(description="グループ名問題の検出・修正")
    parser.add_argument("--detect-only", action="store_true", help="検出のみ（修正しない）")
    parser.add_argument("--execute", action="store_true", help="実際に修正を実行")
    parser.add_argument("--csv", default=CSV_PATH, help="対象CSVファイル")
    args = parser.parse_args()

    print("=" * 70)
    print("グループ名問題 検出・修正スクリプト")
    print("=" * 70)

    # CSVロード
    print(f"\n📂 CSV読み込み: {args.csv}")
    df = pd.read_csv(args.csv)
    print(f"   総レコード数: {len(df)}")

    # 検出
    print("\n🔍 問題検出中...")
    issues = detect_all_issues(df)

    print("\n📊 検出結果:")
    print(f"   ├─ グループ名が人物名: {len(issues['group_as_person'])}件")
    print(f"   └─ 連結名パターン: {len(issues['concatenated_names'])}件")

    if issues["group_as_person"]:
        print("\n   【グループ名が人物名】")
        for issue in issues["group_as_person"][:10]:
            print(f"      {issue.episode_id}: {issue.person_name} → {issue.suggested_action}")
        if len(issues["group_as_person"]) > 10:
            print(f"      ... 他 {len(issues['group_as_person']) - 10}件")

    if issues["concatenated_names"]:
        print("\n   【連結名パターン】")
        for issue in issues["concatenated_names"][:10]:
            print(f"      {issue.episode_id}: {issue.person_name} → {issue.detected_individual}")
        if len(issues["concatenated_names"]) > 10:
            print(f"      ... 他 {len(issues['concatenated_names']) - 10}件")

    if args.detect_only:
        print("\n⚠️ --detect-only モード: 修正は実行しません")
        # レポート保存
        report = generate_report(issues, [])
        os.makedirs(REPORT_DIR, exist_ok=True)
        report_path = os.path.join(REPORT_DIR, f"group_issue_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"📄 検出レポート: {report_path}")
        return

    if not args.execute:
        print("\n💡 修正を実行するには --execute オプションを追加してください")
        return

    # 修正実行
    print("\n🔧 修正実行中...")

    # バックアップ
    backup_path = args.csv.replace(".csv", f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"   💾 バックアップ: {backup_path}")

    # 修正
    results = fix_all_issues(df, issues, dry_run=False)

    # CSV保存
    df.to_csv(args.csv, index=False, encoding="utf-8-sig")
    print("   ✅ CSV更新完了")

    # 結果サマリー
    actions = {}
    for r in results:
        actions[r.action] = actions.get(r.action, 0) + 1

    print("\n📊 修正結果:")
    for action, count in sorted(actions.items()):
        print(f"   ├─ {action}: {count}件")

    # レポート保存
    report = generate_report(issues, results)
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"group_issue_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 修正レポート: {report_path}")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
