#!/usr/bin/env python3
"""
Data Guardian Check - データ保管整合性チェック

機能:
- マスターCSVの存在・整合性確認
- バックアップの存在確認
- Tombstoneの整合性確認
- 世代管理の状態確認

使用方法:
    # 基本チェック
    python scripts/validation/data_guardian_check.py

    # 詳細チェック
    python scripts/validation/data_guardian_check.py --verbose

    # JSON出力
    python scripts/validation/data_guardian_check.py --json

終了コード:
    0: チェック通過
    1: 警告あり
    2: エラーあり
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_guardian import DataGuardian, run_guardian_check
from src.backup_manager import BackupManager
from src.generation_manager import GenerationManager

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"


def check_master_csv() -> dict:
    """マスターCSVの状態をチェック"""
    result = {
        "name": "master_csv",
        "status": "ok",
        "details": {},
    }

    if not MASTER_CSV.exists():
        result["status"] = "error"
        result["details"]["error"] = "Master CSV not found"
        return result

    # ファイルサイズ
    file_size = MASTER_CSV.stat().st_size
    result["details"]["file_size_mb"] = round(file_size / (1024 * 1024), 2)

    # 行数カウント
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        row_count = sum(1 for _ in f) - 1
    result["details"]["episode_count"] = row_count

    # 最終更新時刻
    mtime = datetime.fromtimestamp(MASTER_CSV.stat().st_mtime)
    result["details"]["last_modified"] = mtime.isoformat()

    # 警告チェック
    if row_count < 10000:
        result["status"] = "warning"
        result["details"]["warning"] = f"Episode count ({row_count}) is lower than expected"

    return result


def check_backups() -> dict:
    """バックアップの状態をチェック"""
    result = {
        "name": "backups",
        "status": "ok",
        "details": {},
    }

    try:
        manager = BackupManager()
        backups = manager.list_backups(limit=10)

        result["details"]["backup_count"] = len(backups)
        result["details"]["backup_dir"] = str(manager.backup_dir)

        if backups:
            latest = backups[0]
            result["details"]["latest_backup"] = latest.name
            result["details"]["latest_backup_time"] = datetime.fromtimestamp(latest.stat().st_mtime).isoformat()

            # 24時間以内のバックアップがあるか
            age_hours = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() / 3600
            result["details"]["latest_backup_age_hours"] = round(age_hours, 1)

            if age_hours > 24:
                result["status"] = "warning"
                result["details"]["warning"] = "No backup in the last 24 hours"
        else:
            result["status"] = "warning"
            result["details"]["warning"] = "No backups found"

    except Exception as e:
        result["status"] = "error"
        result["details"]["error"] = str(e)

    return result


def check_tombstones() -> dict:
    """Tombstoneの状態をチェック"""
    result = {
        "name": "tombstones",
        "status": "ok",
        "details": {},
    }

    try:
        guardian = DataGuardian()
        summary = guardian.get_tombstone_summary()

        result["details"]["total_deleted"] = summary["total_deleted"]
        result["details"]["restorable_count"] = summary["restorable_count"]

        if summary["recent_deletions"]:
            result["details"]["recent_deletions"] = [
                {
                    "episode_id": t["episode_id"],
                    "person_name": t["person_name"],
                    "reason": t["reason"],
                }
                for t in summary["recent_deletions"][-5:]
            ]

    except Exception as e:
        result["status"] = "error"
        result["details"]["error"] = str(e)

    return result


def check_generations() -> dict:
    """世代管理の状態をチェック"""
    result = {
        "name": "generations",
        "status": "ok",
        "details": {},
    }

    try:
        manager = GenerationManager()
        generations = manager.list_generations()

        result["details"]["current_generation"] = manager.metadata["current_generation"]
        result["details"]["total_generations"] = len(generations)
        result["details"]["max_generations"] = manager.MAX_GENERATIONS

        if generations:
            latest = generations[-1]
            result["details"]["latest_generation"] = {
                "number": latest["generation_number"],
                "timestamp": latest["timestamp"],
                "description": latest["description"],
                "row_count": latest["stats"]["row_count"],
            }
        else:
            result["status"] = "warning"
            result["details"]["warning"] = "No generations created"

    except Exception as e:
        result["status"] = "error"
        result["details"]["error"] = str(e)

    return result


def check_checkpoints() -> dict:
    """チェックポイントの状態をチェック"""
    result = {
        "name": "checkpoints",
        "status": "ok",
        "details": {},
    }

    try:
        guardian = DataGuardian()
        checkpoints = guardian.get_checkpoint_history(limit=5)

        result["details"]["checkpoint_count"] = len(guardian.checkpoints)

        if checkpoints:
            latest = checkpoints[-1]
            result["details"]["latest_checkpoint"] = {
                "id": latest["checkpoint_id"],
                "timestamp": latest["timestamp"],
                "description": latest.get("description", ""),
                "status": latest["status"],
            }

    except Exception as e:
        result["status"] = "error"
        result["details"]["error"] = str(e)

    return result


def run_all_checks(verbose: bool = False) -> dict:
    """全チェックを実行"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "ok",
        "checks": [],
    }

    # 各チェック実行
    checks = [
        check_master_csv,
        check_backups,
        check_tombstones,
        check_generations,
        check_checkpoints,
    ]

    for check_func in checks:
        check_result = check_func()
        results["checks"].append(check_result)

        if check_result["status"] == "error":
            results["overall_status"] = "error"
        elif check_result["status"] == "warning" and results["overall_status"] == "ok":
            results["overall_status"] = "warning"

    return results


def print_results(results: dict, verbose: bool = False) -> None:
    """結果を表示"""
    print("=" * 60)
    print("Data Guardian Check")
    print("=" * 60)
    print(f"Timestamp: {results['timestamp']}")
    print(f"Overall Status: {results['overall_status'].upper()}")
    print()

    for check in results["checks"]:
        status_icon = {"ok": "OK", "warning": "WARN", "error": "ERR"}[check["status"]]
        print(f"[{status_icon}] {check['name']}")

        if verbose or check["status"] != "ok":
            for key, value in check["details"].items():
                if isinstance(value, (list, dict)):
                    print(f"     {key}:")
                    if isinstance(value, list):
                        for item in value[:3]:
                            print(f"       - {item}")
                    else:
                        for k, v in value.items():
                            print(f"       {k}: {v}")
                else:
                    print(f"     {key}: {value}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Data Guardian integrity check")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", help="Output file path")

    args = parser.parse_args()

    results = run_all_checks(verbose=args.verbose)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_results(results, verbose=args.verbose)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Report saved: {output_path}")

    # 終了コード
    if results["overall_status"] == "error":
        sys.exit(2)
    elif results["overall_status"] == "warning":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
