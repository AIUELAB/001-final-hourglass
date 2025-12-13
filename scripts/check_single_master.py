#!/usr/bin/env python3
"""
CSV単一マスター確認スクリプト

EPUPの一環として、マスターCSVが唯一であることを確認する。
以下のルールを検証:
1. preserved/data/MASTER_EPISODES_CURRENT.csv が存在すること
2. preserved/MASTER_EPISODES_CURRENT.csv がシンボリックリンクであること
3. dashboard/ フォルダにMASTER_EPISODES*.csv が存在しないこと
4. プロジェクトルート直下にMASTER_EPISODES*.csv が存在しないこと

使用方法:
    python scripts/check_single_master.py

戻り値:
    0: すべてのチェックが成功
    1: チェックに失敗（不整合あり）
"""

import sys
from pathlib import Path


def check_single_master() -> dict:
    """
    CSV単一マスター確認を実行

    Returns:
        チェック結果の辞書
    """
    project_root = Path(__file__).parent.parent
    results = {
        "passed": True,
        "checks": [],
        "warnings": [],
        "errors": [],
    }

    # 1. メインマスターの存在確認
    main_master = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
    if main_master.exists() and main_master.is_file():
        results["checks"].append(f"✅ メインマスター存在: {main_master}")
    else:
        results["passed"] = False
        results["errors"].append(f"❌ メインマスターが見つかりません: {main_master}")

    # 2. シンボリックリンクの確認
    symlink_path = project_root / "preserved" / "MASTER_EPISODES_CURRENT.csv"
    if symlink_path.is_symlink():
        target = symlink_path.resolve()
        if target == main_master.resolve():
            results["checks"].append(f"✅ シンボリックリンク正常: {symlink_path} → {target}")
        else:
            results["passed"] = False
            results["errors"].append(
                f"❌ シンボリックリンクが不正なターゲットを指しています: {symlink_path} → {target}"
            )
    elif symlink_path.exists():
        results["passed"] = False
        results["errors"].append(
            f"❌ シンボリックリンクではなく実ファイルが存在: {symlink_path}\n"
            "   → これにより二重マスター問題が発生する可能性があります"
        )
    else:
        results["warnings"].append(f"⚠️ シンボリックリンクが存在しません: {symlink_path}")

    # 3. dashboard/ フォルダの確認
    dashboard_dir = project_root / "dashboard"
    if dashboard_dir.exists():
        dashboard_csvs = list(dashboard_dir.glob("MASTER_EPISODES*.csv"))
        if dashboard_csvs:
            results["passed"] = False
            for csv_file in dashboard_csvs:
                results["errors"].append(
                    f"❌ dashboard/にマスター風CSVが存在: {csv_file}\n" "   → archive/ に移動してください"
                )
        else:
            results["checks"].append("✅ dashboard/にマスター風CSVなし")
    else:
        results["checks"].append("✅ dashboard/フォルダなし（問題なし）")

    # 4. プロジェクトルート直下の確認
    root_csvs = list(project_root.glob("MASTER_EPISODES*.csv"))
    if root_csvs:
        results["passed"] = False
        for csv_file in root_csvs:
            results["errors"].append(
                f"❌ ルート直下にマスター風CSVが存在: {csv_file}\n" "   → preserved/data/ に移動してください"
            )
    else:
        results["checks"].append("✅ ルート直下にマスター風CSVなし")

    # 5. generated/ フォルダの確認（情報のみ）
    generated_dir = project_root / "generated"
    if generated_dir.exists():
        generated_csvs = list(generated_dir.glob("*episodes*.csv"))
        if generated_csvs:
            results["warnings"].append(f"ℹ️ generated/に{len(generated_csvs)}個のエピソードCSVあり（派生物として正常）")

    return results


def main():
    print("=" * 70)
    print("🔍 CSV単一マスター確認スクリプト")
    print("=" * 70)

    results = check_single_master()

    # チェック結果表示
    print("\n【チェック結果】")
    for check in results["checks"]:
        print(f"  {check}")

    # 警告表示
    if results["warnings"]:
        print("\n【警告】")
        for warning in results["warnings"]:
            print(f"  {warning}")

    # エラー表示
    if results["errors"]:
        print("\n【エラー】")
        for error in results["errors"]:
            print(f"  {error}")

    # 総合結果
    print("\n" + "=" * 70)
    if results["passed"]:
        print("✅ すべてのチェックに成功しました")
        print("   マスターCSVは唯一であり、整合性が保たれています")
        return 0
    else:
        print("❌ チェックに失敗しました")
        print("   上記のエラーを確認し、修正してください")
        return 1


if __name__ == "__main__":
    sys.exit(main())
