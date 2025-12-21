#!/usr/bin/env python3
"""
GROUP_MEMBER_MAPからCSVデータへグループ情報を同期するスクリプト

GROUP_MEMBER_MAPに登録されている人物のis_group_memberとgroup_nameを
CSVデータに反映する。

使用方法:
    # ドライラン（変更内容の確認のみ）
    python scripts/sync_group_from_master.py

    # 実際に同期を実行
    python scripts/sync_group_from_master.py --execute

    # 特定のCSVファイルを指定
    python scripts/sync_group_from_master.py --csv path/to/file.csv --execute
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.group_master import GROUP_MEMBER_MAP, SOLO_ARTISTS, GROUP_ENTITIES


def find_sync_issues(df: pd.DataFrame) -> dict:
    """
    GROUP_MEMBER_MAPとデータの不整合を検出

    Args:
        df: エピソードDataFrame

    Returns:
        不整合情報の辞書
    """
    issues = {
        "map_not_reflected": [],  # MAPに登録済みだがデータ未反映
        "solo_not_reflected": [],  # SOLO_ARTISTSに登録済みだがデータ未反映
        "group_entity_found": [],  # GROUP_ENTITIESがperson_nameに存在
    }

    # GROUP_MEMBER_MAP の同期確認
    for person_name, expected_group in GROUP_MEMBER_MAP.items():
        matches = df[df["person_name"] == person_name]
        for idx, row in matches.iterrows():
            actual_member = row.get("is_group_member")
            actual_group = row.get("group_name")

            # 不整合チェック
            needs_fix = False
            if not actual_member:
                needs_fix = True
            if pd.isna(actual_group) or str(actual_group) == "nan" or actual_group != expected_group:
                needs_fix = True

            if needs_fix:
                issues["map_not_reflected"].append(
                    {
                        "index": idx,
                        "episode_id": row.get("episode_id", ""),
                        "person_name": person_name,
                        "expected_group": expected_group,
                        "actual_is_group_member": actual_member,
                        "actual_group_name": actual_group,
                    }
                )

    # SOLO_ARTISTS の同期確認
    for person_name in SOLO_ARTISTS:
        matches = df[df["person_name"] == person_name]
        for idx, row in matches.iterrows():
            actual_member = row.get("is_group_member")
            # Trueになっている場合は問題
            if actual_member:
                issues["solo_not_reflected"].append(
                    {
                        "index": idx,
                        "episode_id": row.get("episode_id", ""),
                        "person_name": person_name,
                        "actual_is_group_member": actual_member,
                        "actual_group_name": row.get("group_name"),
                    }
                )

    # GROUP_ENTITIES の確認
    for person_name in GROUP_ENTITIES:
        matches = df[df["person_name"] == person_name]
        if len(matches) > 0:
            for idx, row in matches.iterrows():
                issues["group_entity_found"].append(
                    {
                        "index": idx,
                        "episode_id": row.get("episode_id", ""),
                        "person_name": person_name,
                    }
                )

    return issues


def sync_group_info(df: pd.DataFrame, issues: dict, dry_run: bool = True) -> tuple:
    """
    グループ情報を同期

    Args:
        df: エピソードDataFrame
        issues: 不整合情報
        dry_run: ドライランかどうか

    Returns:
        (更新後のDataFrame, 変更ログ)
    """
    changes = []

    # GROUP_MEMBER_MAP からの同期
    for issue in issues["map_not_reflected"]:
        idx = issue["index"]
        person_name = issue["person_name"]
        expected_group = issue["expected_group"]

        if not dry_run:
            df.loc[idx, "is_group_member"] = True
            df.loc[idx, "group_name"] = expected_group

        changes.append(
            {
                "type": "group_member_sync",
                "index": idx,
                "person_name": person_name,
                "change": f"is_group_member=True, group_name={expected_group}",
            }
        )

    # SOLO_ARTISTS からの同期
    for issue in issues["solo_not_reflected"]:
        idx = issue["index"]
        person_name = issue["person_name"]

        if not dry_run:
            df.loc[idx, "is_group_member"] = False
            df.loc[idx, "group_name"] = None

        changes.append(
            {
                "type": "solo_artist_sync",
                "index": idx,
                "person_name": person_name,
                "change": "is_group_member=False, group_name=None",
            }
        )

    return df, changes


def main():
    parser = argparse.ArgumentParser(description="GROUP_MEMBER_MAPからCSVデータへグループ情報を同期")
    parser.add_argument("--execute", action="store_true", help="同期を実行（デフォルトはドライラン）")
    parser.add_argument("--csv", type=str, help="対象CSVファイルパス")
    args = parser.parse_args()

    print("=" * 70)
    print("📊 GROUP_MEMBER_MAP → CSV 同期スクリプト")
    print("=" * 70)

    # CSVパス
    if args.csv:
        csv_path = Path(args.csv)
    else:
        csv_path = project_root / "preserved" / "MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1

    print(f"\n📂 対象ファイル: {csv_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"📋 読み込み完了: {len(df)}件")

    # マスタ統計
    print("\n【マスタ統計】")
    print(f"  GROUP_MEMBER_MAP: {len(GROUP_MEMBER_MAP)}名")
    print(f"  SOLO_ARTISTS: {len(SOLO_ARTISTS)}名")
    print(f"  GROUP_ENTITIES: {len(GROUP_ENTITIES)}グループ")

    # 不整合検出
    print("\n🔍 不整合を検出中...")
    issues = find_sync_issues(df)

    map_count = len(issues["map_not_reflected"])
    solo_count = len(issues["solo_not_reflected"])
    entity_count = len(issues["group_entity_found"])

    print("\n【検出結果】")
    print(f"  MAP登録済み・データ未反映: {map_count}件")
    print(f"  SOLO登録済み・データ不整合: {solo_count}件")
    print(f"  GROUP_ENTITIES混入: {entity_count}件")

    total_issues = map_count + solo_count

    if total_issues == 0:
        print("\n✅ 不整合はありません。データは同期済みです。")
        return 0

    # 詳細表示
    if map_count > 0:
        print("\n【MAP未反映サンプル（最大10件）】")
        for issue in issues["map_not_reflected"][:10]:
            print(f"  ❌ {issue['person_name']} → {issue['expected_group']}")
            print(
                f"     現在: is_group_member={issue['actual_is_group_member']}, group_name={issue['actual_group_name']}"
            )

    if solo_count > 0:
        print("\n【SOLO不整合サンプル（最大5件）】")
        for issue in issues["solo_not_reflected"][:5]:
            print(f"  ⚠️ {issue['person_name']}: is_group_member={issue['actual_is_group_member']}")

    # 同期実行
    if args.execute:
        print("\n🔧 同期を実行中...")
        df, changes = sync_group_info(df, issues, dry_run=False)

        # バックアップ作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = csv_path.with_suffix(f".bak_sync_{timestamp}.csv")
        df_original = pd.read_csv(csv_path, encoding="utf-8-sig")
        df_original.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"💾 バックアップ: {backup_path}")

        # 保存
        # 注: preserved/MASTER_EPISODES_CURRENT.csv はシンボリックリンクで
        # preserved/data/MASTER_EPISODES_CURRENT.csv を指しているため、
        # 1回の書込で両方のパスからアクセス可能
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"💾 CSV更新完了: {csv_path}")

        # レポート保存
        report_dir = project_root / "reports"
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / f"group_sync_{timestamp}.json"

        report = {
            "timestamp": timestamp,
            "csv_file": str(csv_path),
            "issues_found": {
                "map_not_reflected": map_count,
                "solo_not_reflected": solo_count,
                "group_entity_found": entity_count,
            },
            "changes_made": len(changes),
            "changes": changes,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"📄 レポート: {report_path}")

        print(f"\n✅ 同期完了: {len(changes)}件を修正")
    else:
        print("\n💡 ドライラン: 実際の変更は行いません")
        print("   同期を実行するには --execute オプションを追加してください")

    print("\n" + "=" * 70)
    print("✅ 完了")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
