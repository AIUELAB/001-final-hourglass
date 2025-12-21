#!/usr/bin/env python3
"""
グループ情報の修正・補完スクリプト

機能:
1. group_name='ソロ' を修正（→ null, is_group_member=False）
2. MAPベースで既存データを補完
3. ソロアーティストのis_group_memberをFalseに設定
4. レポート生成

使用方法:
    # ドライラン（変更なし、レポートのみ）
    python scripts/fix_group_data.py

    # 実際に修正を適用
    python scripts/fix_group_data.py --execute

    # 特定のCSVファイルを指定
    python scripts/fix_group_data.py --csv path/to/file.csv --execute
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.group_master import (
    SOLO_ARTISTS,
    get_group_info,
    get_statistics,
)


def fix_solo_entries(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    group_name='ソロ' のエントリを修正

    Args:
        df: データフレーム

    Returns:
        (修正後のデータフレーム, 修正ログ)
    """
    changes = []

    mask = df["group_name"] == "ソロ"
    affected_rows = df[mask]

    for idx, row in affected_rows.iterrows():
        changes.append(
            {
                "type": "solo_fix",
                "person_name": row["person_name"],
                "before": {"group_name": "ソロ", "is_group_member": row.get("is_group_member")},
                "after": {"group_name": None, "is_group_member": False},
            }
        )
        df.loc[idx, "group_name"] = None
        df.loc[idx, "is_group_member"] = False

    return df, changes


def fill_group_from_map(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    MAPベースでグループ情報を補完

    Args:
        df: データフレーム

    Returns:
        (修正後のデータフレーム, 修正ログ)
    """
    changes = []

    for idx, row in df.iterrows():
        person_name = row.get("person_name", "")
        person_type = str(row.get("person_type", "")).upper()
        current_group = row.get("group_name")
        current_member = row.get("is_group_member")

        # 既に設定済みならスキップ
        if pd.notna(current_group) and str(current_group) not in ["", "nan", "ソロ"]:
            continue

        # MAPから取得
        group_name, is_member = get_group_info(person_name, person_type)

        if group_name is not None and is_member is True:
            changes.append(
                {
                    "type": "map_fill",
                    "person_name": person_name,
                    "before": {"group_name": current_group, "is_group_member": current_member},
                    "after": {"group_name": group_name, "is_group_member": True},
                }
            )
            df.loc[idx, "group_name"] = group_name
            df.loc[idx, "is_group_member"] = True

    return df, changes


def set_solo_artists(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    ソロアーティストのis_group_memberをFalseに設定

    Args:
        df: データフレーム

    Returns:
        (修正後のデータフレーム, 修正ログ)
    """
    changes = []

    for idx, row in df.iterrows():
        person_name = row.get("person_name", "")
        current_member = row.get("is_group_member")

        if person_name in SOLO_ARTISTS:
            # 既にFalseなら何もしない
            if current_member is False or str(current_member) == "False":
                continue

            changes.append(
                {
                    "type": "solo_artist",
                    "person_name": person_name,
                    "before": {"is_group_member": current_member},
                    "after": {"is_group_member": False},
                }
            )
            df.loc[idx, "is_group_member"] = False

    return df, changes


def generate_report(df: pd.DataFrame, all_changes: List[Dict], dry_run: bool = True) -> str:
    """
    修正レポートを生成

    Args:
        df: データフレーム
        all_changes: 全変更ログ
        dry_run: ドライランかどうか

    Returns:
        レポート文字列
    """
    lines = []
    lines.append("=" * 70)
    lines.append("グループ情報修正レポート")
    lines.append(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"モード: {'ドライラン（変更なし）' if dry_run else '本番実行'}")
    lines.append("=" * 70)

    # 統計情報
    stats = get_statistics()
    lines.append("\n【マスタ統計】")
    lines.append(f"  登録メンバー数: {stats['total_members']}")
    lines.append(f"  ユニークグループ数: {stats['unique_groups']}")
    lines.append(f"  ソロアーティスト数: {stats['solo_artists']}")

    # 変更サマリー
    solo_fix = [c for c in all_changes if c["type"] == "solo_fix"]
    map_fill = [c for c in all_changes if c["type"] == "map_fill"]
    solo_artist = [c for c in all_changes if c["type"] == "solo_artist"]

    lines.append("\n【変更サマリー】")
    lines.append(f"  ソロ問題修正: {len(solo_fix)}件")
    lines.append(f"  MAPベース補完: {len(map_fill)}件")
    lines.append(f"  ソロアーティスト設定: {len(solo_artist)}件")
    lines.append(f"  合計: {len(all_changes)}件")

    # 詳細
    if solo_fix:
        lines.append("\n【ソロ問題修正詳細】")
        for c in solo_fix:
            lines.append(f"  - {c['person_name']}: group_name='ソロ' → null")

    if map_fill:
        lines.append("\n【MAPベース補完詳細】")
        for c in map_fill:
            lines.append(f"  - {c['person_name']} → {c['after']['group_name']}")

    if solo_artist:
        lines.append("\n【ソロアーティスト設定詳細】")
        for c in solo_artist[:10]:  # 最初の10件のみ
            lines.append(f"  - {c['person_name']}: is_group_member → False")
        if len(solo_artist) > 10:
            lines.append(f"  ... 他 {len(solo_artist) - 10}件")

    # 現在のデータ状況
    non_null_group = df["group_name"].notna() & (df["group_name"] != "") & (df["group_name"].astype(str) != "nan")
    group_true = df["is_group_member"].eq(True)
    group_false = df["is_group_member"].eq(False)

    lines.append("\n【修正後のデータ状況】")
    lines.append(f"  総エピソード数: {len(df)}")
    lines.append(f"  group_name 充填数: {non_null_group.sum()} ({non_null_group.sum()/len(df)*100:.2f}%)")
    lines.append(f"  is_group_member=True: {group_true.sum()}件")
    lines.append(f"  is_group_member=False: {group_false.sum()}件")

    # ソロ問題残存チェック
    solo_remaining = df[df["group_name"] == "ソロ"]
    lines.append(f"  ソロ問題残存: {len(solo_remaining)}件 {'❌' if len(solo_remaining) > 0 else '✅'}")

    return "\n".join(lines)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="グループ情報の修正・補完スクリプト")
    parser.add_argument("--execute", action="store_true", help="実際に修正を適用")
    parser.add_argument("--csv", type=str, help="対象CSVファイルパス")
    args = parser.parse_args()

    # CSVファイルパス
    if args.csv:
        csv_path = Path(args.csv)
    else:
        csv_path = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1

    print(f"📂 対象ファイル: {csv_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"📊 読み込み完了: {len(df)}件")

    # 修正実行
    all_changes = []

    # Step 1: ソロ問題修正
    df, changes = fix_solo_entries(df)
    all_changes.extend(changes)

    # Step 2: MAPベース補完
    df, changes = fill_group_from_map(df)
    all_changes.extend(changes)

    # Step 3: ソロアーティスト設定
    df, changes = set_solo_artists(df)
    all_changes.extend(changes)

    # レポート生成
    report = generate_report(df, all_changes, dry_run=not args.execute)
    print(report)

    # 実行モードの場合は保存
    if args.execute:
        if all_changes:
            # バックアップ作成
            backup_path = csv_path.with_name(csv_path.stem + f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            df_original = pd.read_csv(csv_path, encoding="utf-8-sig")
            df_original.to_csv(backup_path, index=False, encoding="utf-8-sig")
            print(f"\n📦 バックアップ: {backup_path}")

            # 保存
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"💾 保存完了: {csv_path}")
        else:
            print("\n✅ 修正対象がありませんでした")
    else:
        if all_changes:
            print("\n💡 実際に修正を適用するには --execute オプションを付けて実行してください")
            print(f"   python {Path(__file__).name} --execute")
        else:
            print("\n✅ 修正対象がありませんでした")

    return 0


if __name__ == "__main__":
    sys.exit(main())
