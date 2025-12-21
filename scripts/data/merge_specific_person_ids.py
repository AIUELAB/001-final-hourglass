#!/usr/bin/env python3
"""
特定のPERSON ID統合スクリプト

指示された3件のみを統合:
1. 50セント: PFABA8D4 → PEE4E73D
2. ドウェイン・ジョンソン: P819E2AF, P49D9DE1 → P3D6E339
3. マルクス・ペルソン: PA70EC02 → PD5D1CCF

使用方法:
    python scripts/merge_specific_person_ids.py --dry-run
    python scripts/merge_specific_person_ids.py --execute
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


# 統合対象（旧ID → 新ID）
MERGE_MAP = {
    # 50セント
    "PFABA8D4": "PEE4E73D",
    # ドウェイン・ジョンソン
    "P819E2AF": "P3D6E339",
    "P49D9DE1": "P3D6E339",
    # マルクス・ペルソン
    "PA70EC02": "PD5D1CCF",
}


def main():
    parser = argparse.ArgumentParser(description="特定のPERSON ID統合")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（変更なし）")
    parser.add_argument("--execute", action="store_true", help="実行（CSV更新）")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        return

    mode = "dry-run" if args.dry_run else "実行"
    print("=" * 60)
    print(f"🔧 特定PERSON ID統合 ({mode})")
    print("=" * 60)

    # CSV読み込み
    csv_path = get_master_csv_path()
    print(f"\n📂 CSV読み込み: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  レコード数: {len(df):,}")

    # 統合対象を検出
    results = []
    for old_id, new_id in MERGE_MAP.items():
        old_records = df[df["person_id"] == old_id]
        new_records = df[df["person_id"] == new_id]

        if len(old_records) > 0:
            result = {
                "old_id": old_id,
                "new_id": new_id,
                "old_count": len(old_records),
                "new_count": len(new_records),
                "person_names": old_records["person_name"].unique().tolist(),
            }
            results.append(result)
            print(f"\n✅ {old_id} → {new_id}")
            print(f"   対象レコード: {len(old_records)}件")
            print(f"   person_name: {result['person_names']}")
        else:
            print(f"\n⚠️ {old_id}: 該当レコードなし（すでに統合済み？）")

    print(f"\n📊 統合対象: {len(results)}件のID置換")

    if args.execute and results:
        print("\n💾 変更を適用中...")

        for old_id, new_id in MERGE_MAP.items():
            df.loc[df["person_id"] == old_id, "person_id"] = new_id

        # 保存
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"  保存完了: {len(df):,}件")

    # レポート出力
    reports_dir = get_reports_dir()
    logs_dir = reports_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_str = "dryrun" if args.dry_run else "executed"
    output_path = logs_dir / f"specific_merge_{mode_str}_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "merge_map": MERGE_MAP,
        "results": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 レポート保存: {output_path}")
    print("\n✅ 完了")


if __name__ == "__main__":
    main()
