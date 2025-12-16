#!/usr/bin/env python3
"""
力士表示名修正スクリプト（四股名統一）

目的:
- 力士の表示名を四股名に修正（本名混入を解消）

修正対象:
- P5420FBE: 舞の海秀平 → 舞の海
- P887D990: 土佐ノ海敏生 → 土佐ノ海

使用方法:
    # ドライラン（変更なし）
    python scripts/fix_rikishi_display_names.py --dry-run

    # 本番実行
    python scripts/fix_rikishi_display_names.py --execute
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

# 修正辞書
RIKISHI_FIXES = {
    "P5420FBE": {"old": "舞の海秀平", "new": "舞の海", "reason": "四股名「舞の海」+本名「秀平」"},
    "P887D990": {"old": "土佐ノ海敏生", "new": "土佐ノ海", "reason": "四股名「土佐ノ海」+本名「敏生」"},
}


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
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_rikishi_fix_{timestamp}.csv"

    # バックアップ作成
    shutil.copy(csv_path, backup_path)
    print(f"📦 バックアップ作成: {backup_path}")

    return backup_path


def verify_before_fix(df: pd.DataFrame) -> dict:
    """
    修正前のデータを検証

    Args:
        df: マスターCSVのDataFrame

    Returns:
        検証結果の辞書
    """
    results = {}

    for person_id, fix in RIKISHI_FIXES.items():
        mask = df["person_id"] == person_id
        if not mask.any():
            results[person_id] = {"status": "ERROR", "message": f"person_id {person_id} が見つかりません"}
            continue

        actual_name = df.loc[mask, "person_name"].iloc[0]
        if actual_name != fix["old"]:
            results[person_id] = {
                "status": "ERROR",
                "message": f"期待する表示名が一致しません: 期待={fix['old']}, 実際={actual_name}",
            }
            continue

        episode_count = mask.sum()
        results[person_id] = {
            "status": "OK",
            "current_name": actual_name,
            "expected_name": fix["new"],
            "episode_count": episode_count,
        }

    return results


def apply_fixes(df: pd.DataFrame, dry_run: bool = True) -> tuple[pd.DataFrame, dict]:
    """
    修正を適用

    Args:
        df: マスターCSVのDataFrame
        dry_run: ドライランモード（Trueの場合は変更なし）

    Returns:
        (修正後のDataFrame, 修正レポート)
    """
    report = {"timestamp": datetime.now().isoformat(), "dry_run": dry_run, "fixes_applied": []}

    if dry_run:
        df_modified = df.copy()
    else:
        df_modified = df

    for person_id, fix in RIKISHI_FIXES.items():
        mask = df_modified["person_id"] == person_id

        if not mask.any():
            print(f"❌ {person_id}: person_idが見つかりません")
            continue

        # 修正前の確認
        old_name = df_modified.loc[mask, "person_name"].iloc[0]
        if old_name != fix["old"]:
            print(f"❌ {person_id}: 期待する表示名が一致しません（期待={fix['old']}, 実際={old_name}）")
            continue

        # 修正適用
        if not dry_run:
            df_modified.loc[mask, "person_name"] = fix["new"]

        episode_count = mask.sum()
        print(f"{'🔍' if dry_run else '✅'} {person_id}: {fix['old']} → {fix['new']} ({episode_count}エピソード)")

        # レポートに追加
        report["fixes_applied"].append(
            {
                "person_id": person_id,
                "before": fix["old"],
                "after": fix["new"],
                "reason": fix["reason"],
                "episode_count": int(episode_count),  # int64 → int変換
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
    修正レポートを保存

    Args:
        report: 修正レポートの辞書
        report_path: 保存先のパス
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート保存: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="力士表示名修正スクリプト（四股名統一）")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード（変更なし）")
    parser.add_argument("--execute", action="store_true", help="本番実行（変更あり）")
    args = parser.parse_args()

    # 排他チェック
    if args.dry_run and args.execute:
        print("❌ エラー: --dry-run と --execute は同時に指定できません")
        return 1

    # デフォルトはドライラン
    dry_run = not args.execute

    print("=" * 70)
    print(f"🔧 力士表示名修正 ({'ドライラン' if dry_run else '本番実行'})")
    print("=" * 70)
    print(f"  マスターCSV: {CSV_PATH}")
    print(f"  修正対象: {len(RIKISHI_FIXES)}件")
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
    verification_before = verify_before_fix(df)
    for person_id, result in verification_before.items():
        if result["status"] == "ERROR":
            print(f"❌ {person_id}: {result['message']}")
            return 1
        else:
            print(
                f"✅ {person_id}: {result['current_name']} → {result['expected_name']} ({result['episode_count']}エピソード)"
            )

    # バックアップ作成（本番実行時のみ）
    if not dry_run:
        backup_path = create_backup(CSV_PATH)

    # 修正適用
    print("\n" + "=" * 70)
    print(f"{'🔍 修正内容のプレビュー' if dry_run else '✅ 修正を適用中'}")
    print("=" * 70)
    df_modified, fix_report = apply_fixes(df, dry_run=dry_run)

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
            print("\n⚠️  修正を中止します（バックアップから復元してください）")
            return 1
        else:
            print("✅ 検証成功: データ整合性が維持されています")

            # CSVを保存
            df_modified.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
            print(f"💾 保存完了: {CSV_PATH}")

    # レポート保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"rikishi_fix_{'dryrun' if dry_run else 'executed'}_{timestamp}.json"
    save_report(fix_report, report_path)

    print("\n" + "=" * 70)
    print(f"{'✅ ドライラン完了' if dry_run else '🎉 修正完了'}")
    print("=" * 70)

    if dry_run:
        print("\n💡 本番実行する場合:")
        print("   python scripts/fix_rikishi_display_names.py --execute")

    return 0


if __name__ == "__main__":
    exit(main())
