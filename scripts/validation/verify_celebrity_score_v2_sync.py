#!/usr/bin/env python3
"""
celebrity_score_v2 整合性検証（品質ゲート）

CSV と DB の celebrity_score_v2 の整合性をチェックし、
不整合があればエラー終了する。

使用方法:
    python scripts/validation/verify_celebrity_score_v2_sync.py

終了コード:
    0: 不整合なし
    1: 不整合あり（詳細はレポートに出力）
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# 定数
PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
DB_PATH = PROJECT_ROOT / "data" / "cache" / "fame_score.db"
REPORT_DIR = PROJECT_ROOT / "src" / "reports"

# 許容差（浮動小数点の誤差を考慮）
TOLERANCE = 0.01


def load_csv_scores() -> dict[str, tuple[float, str]]:
    """CSVからperson_id毎のスコアを取得"""
    if not CSV_PATH.exists():
        return {}

    df = pd.read_csv(CSV_PATH, low_memory=False)
    df_persons = df[["person_id", "person_name", "celebrity_score_v2"]].drop_duplicates(subset=["person_id"])

    result = {}
    for _, row in df_persons.iterrows():
        pid = row["person_id"]
        name = row["person_name"]
        score = row["celebrity_score_v2"]
        if pd.notna(score):
            result[pid] = (float(score), name)

    return result


def load_db_scores() -> dict[str, float]:
    """DBからperson_id毎のスコアを取得"""
    if not DB_PATH.exists():
        return {}

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.execute("SELECT person_id, celebrity_score_v2 FROM fame_cache")
    result = {}
    for pid, score in cursor.fetchall():
        if score is not None:
            result[pid] = float(score)
    conn.close()

    return result


def detect_mismatches(csv_scores: dict[str, tuple[float, str]], db_scores: dict[str, float]) -> list[dict]:
    """不整合を検出"""
    mismatches = []

    for pid, (csv_score, person_name) in csv_scores.items():
        db_score = db_scores.get(pid)
        if db_score is None:
            continue  # DBに存在しない場合はスキップ

        diff = abs(csv_score - db_score)
        if diff > TOLERANCE:
            mismatches.append(
                {
                    "person_id": pid,
                    "person_name": person_name,
                    "csv_score": round(csv_score, 6),
                    "db_score": round(db_score, 6),
                    "difference": round(diff, 6),
                }
            )

    # 差が大きい順にソート
    mismatches.sort(key=lambda x: x["difference"], reverse=True)

    return mismatches


def detect_template_copy(csv_scores: dict[str, tuple[float, str]]) -> dict:
    """テンプレートコピー問題を検出（同一値が多数存在）

    閾値: 10人以上が完全に同一のスコアを持つ場合のみ検出
    （5人程度の重複は自然発生することがある）
    """
    score_counts: dict[float, int] = {}
    for score, _ in csv_scores.values():
        rounded = round(score, 6)
        score_counts[rounded] = score_counts.get(rounded, 0) + 1

    # 10人以上が同じ値を持つ場合のみ検出（テンプレートコピー問題）
    duplicates = {score: count for score, count in score_counts.items() if count >= 10}

    return duplicates


def main() -> int:
    print("=" * 60)
    print("celebrity_score_v2 整合性検証")
    print("=" * 60)

    # データ読み込み
    print("\nデータ読み込み中...")
    csv_scores = load_csv_scores()
    db_scores = load_db_scores()
    print(f"  CSV人物数: {len(csv_scores)}")
    print(f"  DB人物数: {len(db_scores)}")

    # 不整合検出
    print("\n不整合検出中...")
    mismatches = detect_mismatches(csv_scores, db_scores)
    print(f"  不整合: {len(mismatches)}人")

    # テンプレートコピー検出
    print("\nテンプレートコピー検出中...")
    duplicates = detect_template_copy(csv_scores)
    if duplicates:
        print(f"  警告: {len(duplicates)}種類の重複値を検出")
        for score, count in sorted(duplicates.items(), key=lambda x: -x[1])[:3]:
            print(f"    {score}: {count}人")
    else:
        print("  重複値なし（正常）")

    # レポート保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "celebrity_v2_sync_check.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "csv_persons": len(csv_scores),
            "db_persons": len(db_scores),
            "mismatches": len(mismatches),
            "template_copy_detected": len(duplicates) > 0,
        },
        "duplicates": duplicates,
        "mismatches": mismatches[:20],  # 上位20件のみ
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nレポート保存: {report_path}")

    # 結果判定
    print("\n" + "=" * 60)
    if mismatches:
        print(f"NG: {len(mismatches)}件の不整合を検出")
        print("\n上位5件:")
        for m in mismatches[:5]:
            print(f"  {m['person_id']} ({m['person_name'][:12]}): " f"CSV={m['csv_score']:.2f}, DB={m['db_score']:.2f}")
        return 1
    elif duplicates:
        print("警告: テンプレートコピー問題の可能性あり")
        return 1
    else:
        print("OK: 不整合なし")
        return 0


if __name__ == "__main__":
    sys.exit(main())
