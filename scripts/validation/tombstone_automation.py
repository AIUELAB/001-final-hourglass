#!/usr/bin/env python3
"""
Tombstone Automation - エピソード削除の自動追跡システム

機能:
- 削除前の自動チェックポイント作成
- Tombstoneレコードの自動生成
- 削除理由の必須入力
- 復元可能性の維持
- 削除レポートの自動生成

使用方法:
    # 単一エピソード削除
    python scripts/validation/tombstone_automation.py --delete EP-000001234 --reason "死亡年齢超過"

    # 複数エピソード削除（ファイル指定）
    python scripts/validation/tombstone_automation.py --delete-file delete_list.txt --reason "品質基準未達"

    # 削除履歴確認
    python scripts/validation/tombstone_automation.py --history

    # 復元
    python scripts/validation/tombstone_automation.py --restore EP-000001234
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_guardian import DataGuardian, TombstoneManager

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src/reports"


def validate_episode_ids(episode_ids: list[str]) -> tuple[list[str], list[str]]:
    """エピソードIDの存在確認"""
    existing = []
    not_found = []

    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        all_ids = {row["episode_id"] for row in reader}

    for ep_id in episode_ids:
        if ep_id in all_ids:
            existing.append(ep_id)
        else:
            not_found.append(ep_id)

    return existing, not_found


def delete_episodes(episode_ids: list[str], reason: str, dry_run: bool = False) -> dict:
    """
    エピソードを安全に削除

    Args:
        episode_ids: 削除するエピソードIDのリスト
        reason: 削除理由（必須）
        dry_run: True の場合、実際には削除しない

    Returns:
        削除結果の辞書
    """
    if not reason or len(reason) < 5:
        raise ValueError("削除理由は5文字以上で入力してください")

    # 存在確認
    existing, not_found = validate_episode_ids(episode_ids)

    if not_found:
        print(f"  Not found: {len(not_found)} episodes")
        for ep_id in not_found[:5]:
            print(f"    - {ep_id}")

    if not existing:
        return {"error": "No valid episodes to delete", "not_found": not_found}

    print(f"\nDeletion target: {len(existing)} episodes")
    print(f"Reason: {reason}")

    if dry_run:
        print("\n[DRY RUN] No actual deletion performed")
        return {
            "dry_run": True,
            "would_delete": existing,
            "not_found": not_found,
        }

    # Data Guardianを使用して安全に削除
    guardian = DataGuardian()
    result = guardian.safe_delete_episodes(existing, reason)

    # レポート生成
    report = {
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "deleted": result["deleted_ids"],
        "not_found": not_found,
        "checkpoint_id": result["checkpoint_id"],
        "verification": result["verification"],
    }

    # レポート保存
    report_path = REPORT_DIR / f"deletion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nReport saved: {report_path}")

    return result


def show_deletion_history(limit: int = 20) -> None:
    """削除履歴を表示"""
    tombstone_manager = TombstoneManager()
    deleted = tombstone_manager.get_deleted_episodes(limit)

    print("=" * 60)
    print("Deletion History")
    print("=" * 60)
    print(f"Total deleted: {tombstone_manager.tombstones['total_deleted']}")
    print(f"Showing last {len(deleted)} entries\n")

    for tombstone in reversed(deleted):
        print(f"  {tombstone['episode_id']}: {tombstone['person_name']}")
        print(f"    Reason: {tombstone['reason']}")
        print(f"    Deleted: {tombstone['deletion_timestamp']}")
        print(f"    Restorable: {'Yes' if tombstone.get('restorable') else 'No'}")
        print()


def restore_episode(episode_id: str) -> dict:
    """削除されたエピソードを復元"""
    tombstone_manager = TombstoneManager()
    guardian = DataGuardian()

    # Tombstoneから復元データを取得
    original_data = tombstone_manager.restore_episode(episode_id)

    if original_data is None:
        return {"error": f"Episode {episode_id} not found in tombstones or not restorable"}

    # チェックポイント作成
    checkpoint_id = guardian.pre_modification_checkpoint(f"Restore {episode_id}")

    # CSVに追加
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 重複チェック
    existing_ids = {row["episode_id"] for row in rows}
    if episode_id in existing_ids:
        return {"error": f"Episode {episode_id} already exists in master CSV"}

    # 復元データを追加
    original_data["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows.append(original_data)

    # 保存
    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Tombstoneを更新（restorable = False）
    for t in tombstone_manager.tombstones["deleted_episodes"]:
        if t["episode_id"] == episode_id:
            t["restorable"] = False
            t["restored_timestamp"] = datetime.now().isoformat()
            break
    tombstone_manager._save_tombstones()

    print(f"\nRestored: {episode_id}")
    print(f"  Person: {original_data.get('person_name', 'N/A')}")
    print(f"  Checkpoint: {checkpoint_id}")

    return {
        "restored": episode_id,
        "checkpoint_id": checkpoint_id,
        "person_name": original_data.get("person_name"),
    }


def main():
    parser = argparse.ArgumentParser(description="Tombstone Automation - Episode deletion tracking")
    parser.add_argument("--delete", nargs="+", help="Episode IDs to delete")
    parser.add_argument("--delete-file", help="File containing episode IDs to delete (one per line)")
    parser.add_argument("--reason", help="Deletion reason (required for deletion)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--history", action="store_true", help="Show deletion history")
    parser.add_argument("--history-limit", type=int, default=20, help="Number of history entries to show")
    parser.add_argument("--restore", help="Episode ID to restore")

    args = parser.parse_args()

    if args.history:
        show_deletion_history(args.history_limit)
        return

    if args.restore:
        result = restore_episode(args.restore)
        if "error" in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        return

    if args.delete or args.delete_file:
        episode_ids = []

        if args.delete:
            episode_ids.extend(args.delete)

        if args.delete_file:
            file_path = Path(args.delete_file)
            if not file_path.exists():
                print(f"Error: File not found: {args.delete_file}")
                sys.exit(1)
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    ep_id = line.strip()
                    if ep_id and not ep_id.startswith("#"):
                        episode_ids.append(ep_id)

        if not args.reason:
            print("Error: --reason is required for deletion")
            sys.exit(1)

        try:
            result = delete_episodes(episode_ids, args.reason, dry_run=args.dry_run)
            if "error" in result:
                print(f"Error: {result['error']}")
                sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

        return

    parser.print_help()


if __name__ == "__main__":
    main()
