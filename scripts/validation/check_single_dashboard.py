#!/usr/bin/env python3
"""
ダッシュボード単一正規版確認スクリプト

EPUPの一環として、ダッシュボードが単一正規版原則に従っていることを確認する。
以下のルールを検証:
1. preserved/ に episode_database_dashboard_v*.html が1つのみ存在すること
2. ルート直下に *dashboard*.html が存在しないこと
3. archive/dashboards/ ディレクトリが存在すること（旧バージョン保存先）

使用方法:
    python scripts/check_single_dashboard.py

戻り値:
    0: すべてのチェックが成功
    1: チェックに失敗（不整合あり）
"""

import re
import sys
from pathlib import Path


def check_single_dashboard() -> dict:
    """
    ダッシュボード単一正規版確認を実行

    Returns:
        チェック結果の辞書
    """
    project_root = Path(__file__).parent.parent.parent
    results = {
        "passed": True,
        "checks": [],
        "warnings": [],
        "errors": [],
    }

    # 1. preserved/ のダッシュボード確認
    preserved_dir = project_root / "preserved"
    if preserved_dir.exists():
        # episode_database_dashboard_v*.html を検索
        dashboard_pattern = re.compile(r"episode_database_dashboard_v(\d+)\.html")
        dashboards = []

        for f in preserved_dir.glob("episode_database_dashboard_v*.html"):
            match = dashboard_pattern.match(f.name)
            if match:
                version = int(match.group(1))
                dashboards.append((version, f))

        if len(dashboards) == 0:
            results["passed"] = False
            results["errors"].append("❌ preserved/ に正規ダッシュボードが存在しません")
        elif len(dashboards) == 1:
            version, path = dashboards[0]
            results["checks"].append(f"✅ 正規ダッシュボード: {path.name} (v{version})")
        else:
            results["passed"] = False
            dashboards.sort(key=lambda x: x[0], reverse=True)
            latest_version, latest_path = dashboards[0]
            old_versions = dashboards[1:]

            results["errors"].append(
                f"❌ preserved/ に複数バージョンが存在（単一正規版原則違反）:\n"
                f"   最新版: {latest_path.name}\n"
                f"   旧版（要移動）: {', '.join(p.name for _, p in old_versions)}\n"
                f"   → 旧バージョンを archive/dashboards/ に移動してください"
            )
    else:
        results["passed"] = False
        results["errors"].append("❌ preserved/ ディレクトリが存在しません")

    # 2. ルート直下のダッシュボード確認
    root_dashboards = list(project_root.glob("*dashboard*.html"))
    # 除外: archive/, preserved/, episode_quality_system/ 配下
    root_dashboards = [
        f
        for f in root_dashboards
        if not any(part in f.parts for part in ["archive", "preserved", "episode_quality_system"])
    ]

    if root_dashboards:
        results["passed"] = False
        for dashboard in root_dashboards:
            results["errors"].append(
                f"❌ ルート直下にダッシュボードが存在: {dashboard.name}\n"
                f"   → preserved/ または archive/dashboards/ に移動してください"
            )
    else:
        results["checks"].append("✅ ルート直下にダッシュボードなし")

    # 3. archive/dashboards/ の存在確認
    archive_dir = project_root / "archive" / "dashboards"
    if archive_dir.exists():
        archived_count = len(list(archive_dir.glob("*.html")))
        results["checks"].append(f"✅ archive/dashboards/ 存在（{archived_count}ファイル）")
    else:
        results["warnings"].append(
            "⚠️ archive/dashboards/ が存在しません\n   → 旧バージョン保存先として作成を推奨: mkdir -p archive/dashboards"
        )

    return results


def main():
    print("=" * 70)
    print("🔍 ダッシュボード単一正規版確認スクリプト")
    print("=" * 70)

    results = check_single_dashboard()

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
        print("   ダッシュボードは単一正規版原則に従っています")
        return 0
    else:
        print("❌ チェックに失敗しました")
        print("   上記のエラーを確認し、修正してください")
        return 1


if __name__ == "__main__":
    sys.exit(main())
