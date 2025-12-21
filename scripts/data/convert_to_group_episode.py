#!/usr/bin/env python3
"""
グループエピソード変換スクリプト

目的:
- グループ自体のエピソードをperson_type=GROUPに変換
- グループ名混入KPIの改善

使用方法:
    # ドライラン（変更なし）
    python scripts/convert_to_group_episode.py --dry-run

    # 本番実行
    python scripts/convert_to_group_episode.py --execute --groups "フィッシャーズ,NON STYLE"
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"
REPORTS_DIR = PROJECT_ROOT / "reports"


def create_backup(csv_path: Path) -> Path:
    """
    マスターCSVのバックアップを作成

    Args:
        csv_path: マスターCSVのパス

    Returns:
        バックアップファイルのパス
    """
    # バックアップディレクトリを作成
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # バックアップファイル名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_group_convert_{timestamp}.csv"

    # バックアップ作成
    shutil.copy(csv_path, backup_path)
    print(f"📦 バックアップ作成: {backup_path}")

    return backup_path


def verify_before_fix(df: pd.DataFrame, target_groups: list[str]) -> dict:
    """
    修正前のデータを検証

    Args:
        df: マスターCSVのDataFrame
        target_groups: 対象グループ名のリスト

    Returns:
        検証結果の辞書
    """
    results = {}

    for group_name in target_groups:
        mask = df["person_name"] == group_name
        if not mask.any():
            results[group_name] = {"status": "ERROR", "message": f"グループ名 {group_name} が見つかりません"}
            continue

        episode_count = mask.sum()
        current_person_types = df.loc[mask, "person_type"].unique()

        results[group_name] = {
            "status": "OK",
            "episode_count": episode_count,
            "current_person_types": list(current_person_types),
        }

    return results


def apply_conversion(df: pd.DataFrame, target_groups: list[str], dry_run: bool = True) -> tuple[pd.DataFrame, dict]:
    """
    変換を適用

    Args:
        df: マスターCSVのDataFrame
        target_groups: 対象グループ名のリスト
        dry_run: ドライランモード（Trueの場合は変更なし）

    Returns:
        (変換後のDataFrame, 変換レポート)
    """
    report = {"timestamp": datetime.now().isoformat(), "dry_run": dry_run, "conversions_applied": []}

    if dry_run:
        df_modified = df.copy()
    else:
        df_modified = df

    for group_name in target_groups:
        mask = df_modified["person_name"] == group_name

        if not mask.any():
            print(f"❌ {group_name}: グループ名が見つかりません")
            continue

        # 変換前の確認
        episode_count = mask.sum()
        before_types = df_modified.loc[mask, "person_type"].unique()

        # 変換適用
        if not dry_run:
            df_modified.loc[mask, "person_type"] = "GROUP"

        after_types = ["GROUP"] if not dry_run else before_types

        print(
            f"{'🔍' if dry_run else '✅'} {group_name}: person_type={list(before_types)} → GROUP ({episode_count}エピソード)"
        )

        # レポートに追加
        report["conversions_applied"].append(
            {
                "group_name": group_name,
                "episode_count": int(episode_count),
                "before_person_types": [str(t) for t in before_types],
                "after_person_types": [str(t) for t in after_types],
            }
        )

    return df_modified, report


def verify_after_fix(df_original: pd.DataFrame, df_modified: pd.DataFrame) -> dict:
    """
    修正後のデータを検証

    Args:
        df_original: 修正前のDataFrame
        df_modified: 修正後のDataFrame

    Returns:
        検証結果の辞書
    """
    results = {
        "row_count_changed": len(df_original) != len(df_modified),
        "column_count_changed": len(df_original.columns) != len(df_modified.columns),
        "person_id_changed": set(df_original["person_id"]) != set(df_modified["person_id"]),
    }

    # エラーチェック
    errors = []
    if results["row_count_changed"]:
        errors.append(f"行数が変化しています: {len(df_original)} → {len(df_modified)}")
    if results["column_count_changed"]:
        errors.append(f"カラム数が変化しています: {len(df_original.columns)} → {len(df_modified.columns)}")
    if results["person_id_changed"]:
        errors.append("person_idが変化しています")

    results["errors"] = errors
    results["status"] = "ERROR" if errors else "OK"

    return results


def save_report(report: dict, report_path: Path):
    """
    変換レポートを保存

    Args:
        report: 変換レポートの辞書
        report_path: 保存先のパス
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート保存: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="グループエピソード変換スクリプト")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード（変更なし）")
    parser.add_argument("--execute", action="store_true", help="本番実行（変更あり）")
    parser.add_argument(
        "--groups",
        type=str,
        required=True,
        help="対象グループ名（カンマ区切り）例: フィッシャーズ,NON STYLE",
    )
    args = parser.parse_args()

    # 排他チェック
    if args.dry_run and args.execute:
        print("❌ エラー: --dry-run と --execute は同時に指定できません")
        return 1

    # デフォルトはドライラン
    dry_run = not args.execute

    # グループ名をリストに変換
    target_groups = [g.strip() for g in args.groups.split(",")]

    print("=" * 70)
    print(f"🔧 グループエピソード変換 ({'ドライラン' if dry_run else '本番実行'})")
    print("=" * 70)
    print(f"  マスターCSV: {CSV_PATH}")
    print(f"  対象グループ: {', '.join(target_groups)}")
    print("=" * 70)

    # CSVを読み込み
    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        print(f"✅ CSV読み込み完了: {len(df)}レコード")
    except Exception as e:
        print(f"❌ CSV読み込みエラー: {e}")
        return 1

    # 修正前の検証
    print("\n" + "=" * 70)
    print("🔍 修正前の検証")
    print("=" * 70)
    verification_before = verify_before_fix(df, target_groups)
    for group_name, result in verification_before.items():
        if result["status"] == "ERROR":
            print(f"❌ {group_name}: {result['message']}")
            return 1
        else:
            print(
                f"✅ {group_name}: {result['episode_count']}エピソード (person_type={result['current_person_types']})"
            )

    # バックアップ作成（本番実行時のみ）
    if not dry_run:
        backup_path = create_backup(CSV_PATH)

    # 変換適用
    print("\n" + "=" * 70)
    print(f"{'🔍 変換内容のプレビュー' if dry_run else '✅ 変換を適用中'}")
    print("=" * 70)
    df_modified, conversion_report = apply_conversion(df, target_groups, dry_run=dry_run)

    # 修正後の検証
    if not dry_run:
        print("\n" + "=" * 70)
        print("🔍 修正後の検証")
        print("=" * 70)
        verification_after = verify_after_fix(df, df_modified)

        if verification_after["status"] == "ERROR":
            print("❌ 検証失敗:")
            for error in verification_after["errors"]:
                print(f"   - {error}")
            print("\n⚠️  変換を中止します（バックアップから復元してください）")
            return 1
        else:
            print("✅ 検証成功: データ整合性が維持されています")

            # CSVを保存
            df_modified.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
            print(f"💾 保存完了: {CSV_PATH}")

    # レポート保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"group_convert_{'dryrun' if dry_run else 'executed'}_{timestamp}.json"
    save_report(conversion_report, report_path)

    print("\n" + "=" * 70)
    print(f"{'✅ ドライラン完了' if dry_run else '🎉 変換完了'}")
    print("=" * 70)

    if dry_run:
        print("\n💡 本番実行する場合:")
        print(f'   python scripts/convert_to_group_episode.py --execute --groups "{args.groups}"')

    return 0


if __name__ == "__main__":
    exit(main())
