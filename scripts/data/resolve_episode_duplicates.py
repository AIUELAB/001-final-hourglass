#!/usr/bin/env python3
"""
エピソード重複解決スクリプト

機能:
1. 同一人物・同一年齢のエピソード重複を検出
2. 品質スコアに基づいて保持するエピソードを決定
3. 低品質側を削除

使用方法:
    # ドライラン（検出のみ）
    python scripts/resolve_episode_duplicates.py --dry-run

    # 実行
    python scripts/resolve_episode_duplicates.py --execute
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def calculate_quality_score(row: pd.Series) -> float:
    """エピソードの品質スコアを計算"""
    # 7軸スコアを使用
    score = 0.0
    weights = {
        "memorability_score": 0.15,
        "empathy_score": 0.15,
        "surprise_score": 0.15,
        "educational_value": 0.15,
        "story_quality": 0.15,
        "factual_density": 0.10,
        "generation_quality_score": 0.15,
    }

    for col, weight in weights.items():
        if col in row and pd.notna(row[col]):
            score += float(row[col]) * weight

    # quality_scoreがある場合は加味
    if "quality_score" in row and pd.notna(row["quality_score"]):
        score = (score + float(row["quality_score"])) / 2

    # char_count（文字数）も考慮（長い方が情報量が多い傾向）
    if "char_count" in row and pd.notna(row["char_count"]):
        char_bonus = min(float(row["char_count"]) / 500, 1.0) * 0.5
        score += char_bonus

    return score


def detect_duplicates(df: pd.DataFrame) -> dict:
    """重複エピソードを検出"""
    # person_id + ageで重複をチェック
    duplicates = df[df.duplicated(subset=["person_id", "age"], keep=False)]

    result = {}
    for (pid, age), group in duplicates.groupby(["person_id", "age"]):
        if len(group) > 1:
            episodes = []
            for idx, row in group.iterrows():
                episodes.append(
                    {
                        "index": idx,
                        "episode_id": row["episode_id"],
                        "person_name": row["person_name"],
                        "episode_text": row["episode_text"][:100] if pd.notna(row["episode_text"]) else "",
                        "quality_score": calculate_quality_score(row),
                        "char_count": row.get("char_count", 0),
                    }
                )

            result[(pid, age)] = episodes

    return result


def resolve_duplicates(df: pd.DataFrame, duplicates: dict, dry_run: bool = True) -> tuple:
    """重複を解決"""
    delete_log = []
    indices_to_delete = []

    for (pid, age), episodes in duplicates.items():
        # 品質スコア順にソート
        sorted_eps = sorted(episodes, key=lambda x: -x["quality_score"])
        keep = sorted_eps[0]
        deletes = sorted_eps[1:]

        for d in deletes:
            log_entry = {
                "person_id": pid,
                "age": age,
                "person_name": d["person_name"],
                "kept_episode_id": keep["episode_id"],
                "kept_quality": keep["quality_score"],
                "deleted_episode_id": d["episode_id"],
                "deleted_quality": d["quality_score"],
            }
            delete_log.append(log_entry)
            indices_to_delete.append(d["index"])

    if not dry_run:
        df = df.drop(indices_to_delete)

    return df, delete_log, indices_to_delete


def main():
    parser = argparse.ArgumentParser(description="エピソード重複解決")
    parser.add_argument("--dry-run", action="store_true", help="検出のみ（変更なし）")
    parser.add_argument("--execute", action="store_true", help="変更を実行")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        return

    dry_run = not args.execute

    print("=" * 70)
    print(f"🔧 エピソード重複解決 {'(dry-run)' if dry_run else '(実行)'}")
    print("=" * 70)
    print(f"  実行日時: {datetime.now().isoformat()}")

    # CSV読み込み
    print(f"\n📂 CSV読み込み: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  レコード数: {len(df)}件")

    # 重複検出
    print("\n🔍 重複検出中...")
    duplicates = detect_duplicates(df)
    total_dup_count = sum(len(eps) for eps in duplicates.values())
    print(f"  重複グループ数: {len(duplicates)}件")
    print(f"  重複エピソード数: {total_dup_count}件")

    if not duplicates:
        print("\n✅ 重複なし")
        return

    # 解決処理
    print("\n🔄 重複解決中...")
    df_resolved, delete_log, indices = resolve_duplicates(df, duplicates, dry_run)

    # 結果表示
    print("\n" + "=" * 70)
    print("📊 結果サマリー")
    print("=" * 70)
    print(f"  処理グループ数: {len(duplicates)}件")
    print(f"  削除エピソード数: {len(indices)}件")

    # 解決例を表示
    print("\n📋 解決例（先頭10件）:")
    for log in delete_log[:10]:
        print(f"  {log['person_name']} (age {log['age']})")
        print(f"    保持: {log['kept_episode_id']} (score: {log['kept_quality']:.2f})")
        print(f"    削除: {log['deleted_episode_id']} (score: {log['deleted_quality']:.2f})")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = (
        REPORTS_DIR
        / f"episode_dedup_{'dryrun' if dry_run else 'executed'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "duplicate_groups": len(duplicates),
            "deleted_episodes": len(indices),
        },
        "delete_log": delete_log,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート保存: {report_path}")

    # 実行
    if not dry_run:
        print("\n💾 変更を適用中...")
        df_resolved.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  保存完了: {len(df_resolved)}件")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
