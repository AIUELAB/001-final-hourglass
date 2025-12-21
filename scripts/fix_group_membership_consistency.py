#!/usr/bin/env python3
"""
グループ所属整合性修正スクリプト

同一person_idで異なるis_group_member/group_name設定を統一する。

修正ルール:
1. GROUP_MEMBER_MAP登録者: is_group_member=True, group_name=MAPの値
2. 有効なgroup_name保持者: is_group_member=True に統一
3. group_name='未登録'のみ: is_group_member=False に統一

使用方法:
    python scripts/fix_group_membership_consistency.py --dry-run
    python scripts/fix_group_membership_consistency.py --execute
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.csv_path_resolver import get_master_csv_path, get_reports_dir
from src.group_master import GROUP_MEMBER_MAP


def main():
    parser = argparse.ArgumentParser(description="グループ所属整合性修正")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（変更なし）")
    parser.add_argument("--execute", action="store_true", help="実行（CSV更新）")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        return

    mode = "dry-run" if args.dry_run else "実行"
    print("=" * 60)
    print(f"🔧 グループ所属整合性修正 ({mode})")
    print("=" * 60)

    # CSV読み込み
    csv_path = get_master_csv_path()
    print(f"\n📂 CSV読み込み: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  レコード数: {len(df):,}")

    # 不整合を検出して修正計画を立てる
    corrections = []  # (person_id, person_name, new_is_member, new_group_name, reason, record_count)

    for pid, group in df.groupby("person_id"):
        is_member_vals = group["is_group_member"].dropna().unique()

        # is_group_memberの不整合がある場合のみ対象
        if len(is_member_vals) <= 1:
            continue

        person_name = group["person_name"].iloc[0]
        group_names = [g for g in group["group_name"].dropna().unique() if g != "未登録"]
        record_count = len(group)

        # 修正ルール適用
        if person_name in GROUP_MEMBER_MAP:
            # ルール1: GROUP_MEMBER_MAP登録者
            new_is_member = True
            new_group_name = GROUP_MEMBER_MAP[person_name]
            reason = "GROUP_MEMBER_MAP登録"
        elif group_names:
            # ルール2: 有効なgroup_name保持者
            new_is_member = True
            new_group_name = group_names[0]  # 最初の有効なグループ名を採用
            reason = "有効グループ名あり"
        else:
            # ルール3: group_name='未登録'のみ
            new_is_member = False
            new_group_name = "未登録"
            reason = "グループ所属なし"

        corrections.append((pid, person_name, new_is_member, new_group_name, reason, record_count))

    # 統計
    by_reason = {}
    total_records = 0
    for _, _, _, _, reason, count in corrections:
        by_reason[reason] = by_reason.get(reason, 0) + 1
        total_records += count

    print("\n📊 修正対象:")
    print(f"  不整合person_id数: {len(corrections)}件")
    print(f"  影響レコード数: {total_records}件")
    print("\n  理由別内訳:")
    for reason, count in sorted(by_reason.items(), key=lambda x: -x[1]):
        print(f"    {reason}: {count}件")

    if not corrections:
        print("\n✅ 修正対象なし")
        return

    # 修正例を表示
    print("\n📋 修正例（先頭20件）:")
    for pid, name, is_member, group_name, reason, count in corrections[:20]:
        print(f"  {name}: is_group_member={is_member}, group_name={group_name}")
        print(f"    理由: {reason}, レコード数: {count}")

    if len(corrections) > 20:
        print(f"  ... 他 {len(corrections) - 20}件")

    # 実行
    if args.execute:
        print("\n💾 修正を適用中...")

        modified_count = 0
        for pid, _, new_is_member, new_group_name, _, _ in corrections:
            mask = df["person_id"] == pid
            count = mask.sum()
            if count > 0:
                df.loc[mask, "is_group_member"] = new_is_member
                df.loc[mask, "group_name"] = new_group_name
                modified_count += count

        print(f"  修正完了: {modified_count}件")

        # CSV保存
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"  保存完了: {len(df):,}件")

    # レポート出力
    reports_dir = get_reports_dir()
    logs_dir = reports_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_str = "dryrun" if args.dry_run else "executed"
    output_path = logs_dir / f"group_membership_fix_{mode_str}_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "total_inconsistent_persons": len(corrections),
        "total_records_affected": total_records,
        "by_reason": by_reason,
        "corrections": [
            {
                "person_id": pid,
                "person_name": name,
                "new_is_group_member": is_member,
                "new_group_name": group_name,
                "reason": reason,
                "record_count": count,
            }
            for pid, name, is_member, group_name, reason, count in corrections
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 レポート保存: {output_path}")
    print("\n✅ 完了")


if __name__ == "__main__":
    main()
