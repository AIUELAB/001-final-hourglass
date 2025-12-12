#!/usr/bin/env python3
"""
正規化後の人物重複統合スクリプト

機能:
1. 同一person_nameを持つ複数のperson_idを検出
2. 代表person_idを決定（エピソード数最多、quality_score最高）
3. エピソードを代表person_idに統合
4. 重複person_idを削除

使用方法:
    # ドライラン（検出のみ）
    python scripts/merge_normalized_duplicates.py --dry-run

    # 実行
    python scripts/merge_normalized_duplicates.py --execute
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


def detect_duplicates(df: pd.DataFrame) -> dict:
    """重複人物を検出"""
    # person_nameでグループ化し、複数のperson_idを持つものを検出
    name_to_ids = df.groupby("person_name")["person_id"].apply(lambda x: x.unique().tolist())
    duplicates = name_to_ids[name_to_ids.apply(len) > 1]

    result = {}
    for name, ids in duplicates.items():
        # 各person_idのエピソード情報を収集
        candidates = []
        for pid in ids:
            pid_df = df[df["person_id"] == pid]
            candidates.append(
                {
                    "person_id": pid,
                    "episode_count": len(pid_df),
                    "avg_quality_score": pid_df["quality_score"].mean() if "quality_score" in pid_df.columns else 0,
                    "ages": sorted(pid_df["age"].unique().tolist()),
                    "name_raw": pid_df["name_raw"].iloc[0] if pid_df["name_raw"].notna().any() else None,
                }
            )

        result[name] = candidates

    return result


def select_canonical(candidates: list) -> dict:
    """代表person_idを選定"""
    # エピソード数 > quality_score > person_id（辞書順）
    return sorted(
        candidates,
        key=lambda x: (
            -x["episode_count"],
            -x["avg_quality_score"],
            x["person_id"],
        ),
    )[0]


def merge_duplicates(df: pd.DataFrame, duplicates: dict, dry_run: bool = True) -> tuple:
    """重複を統合"""
    merge_log = []
    deleted_ids = []

    for name, candidates in duplicates.items():
        canonical = select_canonical(candidates)
        canonical_id = canonical["person_id"]

        for candidate in candidates:
            if candidate["person_id"] != canonical_id:
                dup_id = candidate["person_id"]

                # エピソード統合（同じ年齢のエピソードがあるかチェック）
                canonical_ages = set(df[df["person_id"] == canonical_id]["age"].unique())
                dup_ages = set(df[df["person_id"] == dup_id]["age"].unique())
                conflicting_ages = canonical_ages & dup_ages

                log_entry = {
                    "person_name": name,
                    "canonical_id": canonical_id,
                    "duplicate_id": dup_id,
                    "canonical_episodes": canonical["episode_count"],
                    "duplicate_episodes": candidate["episode_count"],
                    "conflicting_ages": list(conflicting_ages),
                    "name_raw": candidate.get("name_raw"),
                }

                if not dry_run:
                    if conflicting_ages:
                        # 同じ年齢のエピソードは削除
                        df = df[~((df["person_id"] == dup_id) & (df["age"].isin(conflicting_ages)))]
                        log_entry["deleted_conflicting"] = len(conflicting_ages)

                    # 残りのエピソードを統合
                    df.loc[df["person_id"] == dup_id, "person_id"] = canonical_id

                deleted_ids.append(dup_id)
                merge_log.append(log_entry)

    return df, merge_log, deleted_ids


def main():
    parser = argparse.ArgumentParser(description="正規化後の人物重複統合")
    parser.add_argument("--dry-run", action="store_true", help="検出のみ（変更なし）")
    parser.add_argument("--execute", action="store_true", help="変更を実行")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        return

    dry_run = not args.execute

    print("=" * 70)
    print(f"🔧 正規化後の人物重複統合 {'(dry-run)' if dry_run else '(実行)'}")
    print("=" * 70)
    print(f"  実行日時: {datetime.now().isoformat()}")

    # CSV読み込み
    print(f"\n📂 CSV読み込み: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  レコード数: {len(df)}件")
    print(f"  ユニークperson_id数: {df['person_id'].nunique()}件")

    # 重複検出
    print("\n🔍 重複検出中...")
    duplicates = detect_duplicates(df)
    print(f"  重複人物名数: {len(duplicates)}件")

    if not duplicates:
        print("\n✅ 重複なし")
        return

    # 統合処理
    print("\n🔄 統合処理中...")
    df_merged, merge_log, deleted_ids = merge_duplicates(df, duplicates, dry_run)

    # 結果表示
    print("\n" + "=" * 70)
    print("📊 結果サマリー")
    print("=" * 70)
    print(f"  統合対象: {len(duplicates)}人物")
    print(f"  削除されるperson_id: {len(deleted_ids)}件")

    # 統合例を表示
    print("\n📋 統合例（先頭10件）:")
    for log in merge_log[:10]:
        print(f"  「{log['person_name']}」")
        print(f"    代表: {log['canonical_id']} ({log['canonical_episodes']}ep)")
        print(f"    削除: {log['duplicate_id']} ({log['duplicate_episodes']}ep)")
        if log["conflicting_ages"]:
            print(f"    重複年齢: {log['conflicting_ages']}")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = (
        REPORTS_DIR
        / f"person_merge_{'dryrun' if dry_run else 'executed'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "duplicate_names": len(duplicates),
            "deleted_person_ids": len(deleted_ids),
            "merge_entries": len(merge_log),
        },
        "merge_log": merge_log,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート保存: {report_path}")

    # 実行
    if not dry_run:
        print("\n💾 変更を適用中...")
        df_merged.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  保存完了: {len(df_merged)}件")
        print(f"  削除後ユニークperson_id数: {df_merged['person_id'].nunique()}件")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
