#!/usr/bin/env python3
"""
メタ表現違反修正スクリプト

違反エピソードをCSVから削除する。
対象パターン:
1. 声優/キャスト言及（俳優名、声優、キャスト）
2. 物語言及（物語の中で）
3. 原作言及（原作では）
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
import argparse

PROJECT_ROOT = Path(__file__).parent.parent.parent


def is_meta_演じ(text):
    """演じ系がメタ的（俳優/声優言及）かどうか判定"""
    meta_patterns = [
        r"が演じた",
        r"が演じる",
        r"を演じた[^。]*俳優",
        r"声優.*演じ",
        r"演じた.*俳優",
    ]
    for p in meta_patterns:
        if re.search(p, text):
            return True
    return False


def detect_violations(df):
    """違反エピソードを検出"""
    df_fictional = df[df["person_type"].str.upper().str.contains("FICTIONAL", na=False)].copy()

    all_violations = {}

    # 声優言及
    for idx, row in df_fictional[df_fictional["episode_text"].str.contains(r"声優", regex=True, na=False)].iterrows():
        ep_id = row["episode_id"]
        if ep_id not in all_violations:
            all_violations[ep_id] = {
                "index": idx,
                "episode_id": ep_id,
                "person_name": row["person_name"],
                "age": row["age"],
                "work_title": row["work_title"],
                "episode_text": row["episode_text"],
                "categories": set(),
            }
        all_violations[ep_id]["categories"].add("声優言及")

    # キャスト言及
    for idx, row in df_fictional[
        df_fictional["episode_text"].str.contains(r"キャスト", regex=True, na=False)
    ].iterrows():
        ep_id = row["episode_id"]
        if ep_id not in all_violations:
            all_violations[ep_id] = {
                "index": idx,
                "episode_id": ep_id,
                "person_name": row["person_name"],
                "age": row["age"],
                "work_title": row["work_title"],
                "episode_text": row["episode_text"],
                "categories": set(),
            }
        all_violations[ep_id]["categories"].add("キャスト言及")

    # 演じ系（メタ的のみ）
    for idx, row in df_fictional[df_fictional["episode_text"].str.contains(r"演じ", regex=True, na=False)].iterrows():
        if is_meta_演じ(row["episode_text"]):
            ep_id = row["episode_id"]
            if ep_id not in all_violations:
                all_violations[ep_id] = {
                    "index": idx,
                    "episode_id": ep_id,
                    "person_name": row["person_name"],
                    "age": row["age"],
                    "work_title": row["work_title"],
                    "episode_text": row["episode_text"],
                    "categories": set(),
                }
            all_violations[ep_id]["categories"].add("演じる言及")

    # 物語言及
    for idx, row in df_fictional[
        df_fictional["episode_text"].str.contains(r"物語の中で|物語で", regex=True, na=False)
    ].iterrows():
        ep_id = row["episode_id"]
        if ep_id not in all_violations:
            all_violations[ep_id] = {
                "index": idx,
                "episode_id": ep_id,
                "person_name": row["person_name"],
                "age": row["age"],
                "work_title": row["work_title"],
                "episode_text": row["episode_text"],
                "categories": set(),
            }
        all_violations[ep_id]["categories"].add("物語言及")

    # 原作言及
    for idx, row in df_fictional[
        df_fictional["episode_text"].str.contains(r"原作では|原作において", regex=True, na=False)
    ].iterrows():
        ep_id = row["episode_id"]
        if ep_id not in all_violations:
            all_violations[ep_id] = {
                "index": idx,
                "episode_id": ep_id,
                "person_name": row["person_name"],
                "age": row["age"],
                "work_title": row["work_title"],
                "episode_text": row["episode_text"],
                "categories": set(),
            }
        all_violations[ep_id]["categories"].add("原作言及")

    return list(all_violations.values())


def generate_report(violations, action="検出"):
    """レポート生成"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"メタ表現違反{action}レポート")
    lines.append(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"総{action}件数: {len(violations)}件")

    # カテゴリ別集計
    cat_counts = {}
    for v in violations:
        for cat in v["categories"]:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

    lines.append("\nカテゴリ別内訳:")
    for cat, count in sorted(cat_counts.items()):
        lines.append(f"  - {cat}: {count}件")

    lines.append("\n" + "-" * 70)
    lines.append("詳細一覧")
    lines.append("-" * 70)

    for i, v in enumerate(violations[:50], 1):  # 最大50件表示
        lines.append(f"\n[{i}] {v['episode_id']}")
        lines.append(f"    キャラ: {v['person_name']} ({v['age']}歳) - {v['work_title']}")
        lines.append(f"    違反: {', '.join(v['categories'])}")
        text_preview = v["episode_text"][:100].replace("\n", " ")
        lines.append(f"    テキスト: {text_preview}...")

    if len(violations) > 50:
        lines.append(f"\n...他 {len(violations) - 50}件")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="メタ表現違反修正")
    parser.add_argument("--execute", action="store_true", help="実際に削除を実行")
    parser.add_argument("--detect-only", action="store_true", help="検出のみ")
    args = parser.parse_args()

    csv_path = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return

    print("🔍 メタ表現違反を検出中...")
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    original_count = len(df)

    violations = detect_violations(df)

    if not violations:
        print("✅ メタ表現違反は見つかりませんでした")
        return

    # 検出レポート
    report = generate_report(violations, "検出")
    print(report)

    # レポート保存
    report_dir = PROJECT_ROOT / "src" / "reports" / "logs"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"meta_expression_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    if args.detect_only:
        print("\n--detect-only: 検出のみ実行しました")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"📄 レポート保存: {report_path}")
        return

    if not args.execute:
        print("\n⚠️ ドライラン: 実際の削除は行いません")
        print("   実行するには --execute オプションを付けてください")
        return

    # 削除実行
    print("\n" + "=" * 70)
    print("🗑️ 違反エピソード削除実行")
    print("=" * 70)

    violation_ids = [v["episode_id"] for v in violations]
    df_filtered = df[~df["episode_id"].isin(violation_ids)]

    # 削除結果
    deleted_count = original_count - len(df_filtered)
    print(f"\n削除前: {original_count}件")
    print(f"削除後: {len(df_filtered)}件")
    print(f"削除数: {deleted_count}件")

    # CSVを上書き保存
    df_filtered.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n✅ CSV更新完了: {csv_path}")

    # 削除レポート
    delete_report = generate_report(violations, "削除")
    delete_report += f"\n\n削除前: {original_count}件\n削除後: {len(df_filtered)}件"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(delete_report)
    print(f"📄 レポート保存: {report_path}")


if __name__ == "__main__":
    main()
