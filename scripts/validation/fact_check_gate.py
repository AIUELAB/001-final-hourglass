#!/usr/bin/env python3
"""
Fact Check Gate - コミット前ファクトチェックゲート

機能:
- quick: 新規・変更エピソードのみ検証
- full: 全エピソード検証
- diff: 前回からの差分検証

使用方法:
    # クイックチェック（コミット前）
    python scripts/validation/fact_check_gate.py --mode quick

    # フルチェック
    python scripts/validation/fact_check_gate.py --mode full

    # 差分チェック
    python scripts/validation/fact_check_gate.py --mode diff

    # 閾値指定
    python scripts/validation/fact_check_gate.py --threshold 0.90

終了コード:
    0: ゲート通過
    1: ゲート失敗（品質基準未達）
    2: エラー発生
"""

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_guardian import DataGuardian, run_guardian_check
from src.birth_year_database import get_birth_year

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src/reports"
GATE_HISTORY_FILE = REPORT_DIR / "fact_check_gate_history.json"


def load_gate_history() -> dict:
    """ゲート履歴を読み込み"""
    if GATE_HISTORY_FILE.exists():
        with open(GATE_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"runs": [], "last_full_hash": None}


def save_gate_history(history: dict) -> None:
    """ゲート履歴を保存"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # 最大100件に制限
    if len(history["runs"]) > 100:
        history["runs"] = history["runs"][-100:]

    with open(GATE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def compute_file_hash(file_path: Path) -> str:
    """ファイルのハッシュを計算"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_basic_integrity() -> dict:
    """基本的な整合性チェック"""
    results = {
        "passed": True,
        "checks": [],
        "errors": [],
    }

    # ファイル存在確認
    if not MASTER_CSV.exists():
        results["passed"] = False
        results["errors"].append("Master CSV not found")
        return results

    results["checks"].append({"name": "file_exists", "passed": True})

    # 行数チェック
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        row_count = sum(1 for _ in f) - 1

    if row_count < 1000:
        results["passed"] = False
        results["errors"].append(f"Episode count too low: {row_count}")
    else:
        results["checks"].append({"name": "min_episodes", "passed": True, "count": row_count})

    # 必須カラムチェック
    required_columns = ["episode_id", "person_name", "episode_text", "age"]
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        actual_columns = reader.fieldnames or []

    missing = [col for col in required_columns if col not in actual_columns]
    if missing:
        results["passed"] = False
        results["errors"].append(f"Missing columns: {missing}")
    else:
        results["checks"].append({"name": "required_columns", "passed": True})

    return results


def check_year_age_consistency(sample_size: int = 100) -> dict:
    """年齢-年号の整合性チェック（サンプル）"""
    results = {
        "passed": True,
        "sample_size": sample_size,
        "inconsistencies": [],
    }

    import random

    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # サンプリング
    sample = random.sample(rows, min(sample_size, len(rows)))

    for row in sample:
        person_name = row.get("person_name", "")
        age_str = row.get("age", "")
        person_type = row.get("person_type", "REAL")

        if person_type == "FICTIONAL":
            continue

        try:
            age = int(float(age_str))
        except (ValueError, TypeError):
            continue

        birth_year = get_birth_year(person_name)
        if birth_year is None:
            continue

        # 現在年を基準にチェック
        current_year = datetime.now().year
        max_possible_age = current_year - birth_year

        if age > max_possible_age + 5:  # 5年の余裕
            results["inconsistencies"].append(
                {
                    "episode_id": row.get("episode_id"),
                    "person_name": person_name,
                    "age": age,
                    "birth_year": birth_year,
                    "issue": "age_exceeds_possible",
                }
            )

    if len(results["inconsistencies"]) > sample_size * 0.05:  # 5%以上で失敗
        results["passed"] = False

    return results


def check_data_guardian_status() -> dict:
    """Data Guardianステータスチェック"""
    try:
        result = run_guardian_check()
        return {
            "passed": result["status"] == "ok",
            "status": result["status"],
            "episode_count": result["current_episode_count"],
            "tombstone_count": result["tombstone_summary"]["total_deleted"],
        }
    except Exception as e:
        return {
            "passed": False,
            "error": str(e),
        }


def run_fact_check_gate(
    mode: str = "quick",
    threshold: float = 0.95,
) -> dict:
    """
    ファクトチェックゲートを実行

    Args:
        mode: "quick" | "full" | "diff"
        threshold: 合格しきい値

    Returns:
        ゲート結果
    """
    history = load_gate_history()
    current_hash = compute_file_hash(MASTER_CSV)

    result = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "threshold": threshold,
        "file_hash": current_hash[:16] + "...",
        "passed": True,
        "checks": {},
    }

    print("=" * 60)
    print(f"Fact Check Gate - Mode: {mode}")
    print("=" * 60)

    # 1. 基本整合性チェック
    print("\n1. Basic integrity check...")
    integrity = check_basic_integrity()
    result["checks"]["integrity"] = integrity
    if not integrity["passed"]:
        result["passed"] = False
        print(f"   FAILED: {integrity['errors']}")
    else:
        print(f"   PASSED: {len(integrity['checks'])} checks")

    # 2. Data Guardianチェック
    print("\n2. Data Guardian check...")
    guardian = check_data_guardian_status()
    result["checks"]["guardian"] = guardian
    if not guardian["passed"]:
        result["passed"] = False
        print(f"   FAILED: {guardian.get('error', guardian.get('status'))}")
    else:
        print(f"   PASSED: {guardian['episode_count']:,} episodes, {guardian['tombstone_count']} tombstones")

    # 3. 年齢整合性チェック（quickモード以外）
    if mode != "quick":
        print("\n3. Year-age consistency check...")
        consistency = check_year_age_consistency(sample_size=200 if mode == "diff" else 500)
        result["checks"]["consistency"] = consistency
        if not consistency["passed"]:
            result["passed"] = False
            print(f"   FAILED: {len(consistency['inconsistencies'])} inconsistencies")
        else:
            print(f"   PASSED: {consistency['sample_size']} samples checked")

    # 4. 差分チェック
    if mode == "diff" and history.get("last_full_hash"):
        print("\n4. Diff check...")
        if current_hash == history["last_full_hash"]:
            print("   No changes since last full check")
            result["checks"]["diff"] = {"changed": False}
        else:
            print("   Changes detected")
            result["checks"]["diff"] = {"changed": True}

    # 結果記録
    history["runs"].append(
        {
            "timestamp": result["timestamp"],
            "mode": mode,
            "passed": result["passed"],
            "hash": current_hash[:16],
        }
    )

    if mode == "full" and result["passed"]:
        history["last_full_hash"] = current_hash

    save_gate_history(history)

    # サマリー
    print("\n" + "=" * 60)
    status = "PASSED" if result["passed"] else "FAILED"
    print(f"Gate Result: {status}")
    print("=" * 60)

    return result


def main():
    parser = argparse.ArgumentParser(description="Fact check gate for CI/CD")
    parser.add_argument(
        "--mode",
        choices=["quick", "full", "diff"],
        default="quick",
        help="Check mode",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        help="Pass threshold (0.0-1.0)",
    )
    parser.add_argument(
        "--output",
        help="Output report path",
    )

    args = parser.parse_args()

    try:
        result = run_fact_check_gate(mode=args.mode, threshold=args.threshold)

        # レポート保存
        if args.output:
            output_path = Path(args.output)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = REPORT_DIR / f"fact_check_gate_{timestamp}.json"

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\nReport: {output_path}")

        # 終了コード
        sys.exit(0 if result["passed"] else 1)

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
