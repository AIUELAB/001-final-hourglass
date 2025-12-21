#!/usr/bin/env python3
"""
PERSON ID整合性修正スクリプト

同一person_nameで異なるperson_idを持つレコードを検出し、
正しいID（person_nameのMD5ハッシュ）に統一する。

使用方法:
    python scripts/fix_person_id_consistency.py --dry-run
    python scripts/fix_person_id_consistency.py --execute
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.csv_path_resolver import get_master_csv_path, get_reports_dir


def generate_person_id(person_name: str) -> str:
    """person_nameからperson_idを生成（MD5ハッシュ）"""
    hash_val = hashlib.md5(person_name.encode("utf-8")).hexdigest()[:7].upper()
    return f"P{hash_val}"


def find_duplicate_candidates_file() -> Path:
    """最新のduplicate_candidatesファイルを検索"""
    reports_dir = get_reports_dir()
    logs_dir = reports_dir / "logs"
    files = sorted(logs_dir.glob("duplicate_candidates_*.json"), reverse=True)
    if not files:
        raise FileNotFoundError("duplicate_candidates_*.json が見つかりません")
    return files[0]


def main():
    parser = argparse.ArgumentParser(description="PERSON ID整合性修正")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（変更なし）")
    parser.add_argument("--execute", action="store_true", help="実行（CSV更新）")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        return

    mode = "dry-run" if args.dry_run else "実行"
    print("=" * 60)
    print(f"🔧 PERSON ID整合性修正 ({mode})")
    print("=" * 60)

    # 重複候補ファイル読み込み
    candidates_file = find_duplicate_candidates_file()
    print(f"\n📂 重複候補ファイル: {candidates_file}")

    with open(candidates_file, encoding="utf-8") as f:
        data = json.load(f)

    exact_duplicates = data.get("exact_duplicates", [])
    print(f"  exact_duplicates: {len(exact_duplicates)}件")

    if not exact_duplicates:
        print("\n✅ 修正対象なし")
        return

    # CSV読み込み
    csv_path = get_master_csv_path()
    print(f"\n📂 CSV読み込み: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  レコード数: {len(df):,}")

    # 修正マップ作成
    corrections = []  # (old_id, new_id, person_name, record_count)
    total_records_to_fix = 0

    for item in exact_duplicates:
        person_name = item["person_name"]
        expected_id = generate_person_id(person_name)

        for old_id in item["person_ids"]:
            if old_id != expected_id:
                record_count = len(df[df["person_id"] == old_id])
                if record_count > 0:
                    corrections.append((old_id, expected_id, person_name, record_count))
                    total_records_to_fix += record_count

    print("\n📊 修正対象:")
    print(f"  不正ID数: {len(corrections)}件")
    print(f"  影響レコード数: {total_records_to_fix}件")

    if not corrections:
        print("\n✅ 修正対象なし（すべて正しいIDです）")
        return

    # 修正例を表示
    print("\n📋 修正例（先頭20件）:")
    for old_id, new_id, person_name, count in corrections[:20]:
        print(f"  {old_id} → {new_id} ({person_name}): {count}件")

    if len(corrections) > 20:
        print(f"  ... 他 {len(corrections) - 20}件")

    # 実行
    if args.execute:
        print("\n💾 修正を適用中...")

        modified_count = 0
        for old_id, new_id, person_name, _ in corrections:
            mask = df["person_id"] == old_id
            count = mask.sum()
            if count > 0:
                df.loc[mask, "person_id"] = new_id
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
    output_path = logs_dir / f"person_id_consistency_fix_{mode_str}_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "source_file": str(candidates_file),
        "total_exact_duplicates": len(exact_duplicates),
        "corrections_count": len(corrections),
        "records_fixed": total_records_to_fix,
        "corrections": [
            {
                "old_id": old_id,
                "new_id": new_id,
                "person_name": person_name,
                "record_count": count,
            }
            for old_id, new_id, person_name, count in corrections
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 レポート保存: {output_path}")
    print("\n✅ 完了")


if __name__ == "__main__":
    main()
