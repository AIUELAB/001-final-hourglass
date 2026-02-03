#!/usr/bin/env python3
"""
EPUP: 上位独占エピソード削除スクリプト

特定の人物がTop N内で過剰にエピソードを占有している場合、
低スコアのエピソードを削除して上限に収める。

上限ルール（top_monopoly_gate.pyと同じ）:
- Top20: 同一person_id 最大1件
- Top100: 同一person_id 最大2件
- Top1000: 同一person_id 最大3件

処理フロー:
1. CSVを読み込み、super_total_score降順でソート
2. 各Tier（Top20/100/1000）で上限超過を検出
3. 上限を超える低スコアエピソードを削除候補として特定
4. バックアップ作成 → 削除 → ログ出力

使用方法:
    # ドライラン（確認のみ、デフォルト）
    python scripts/fix/resolve_top_monopoly.py --csv PATH

    # 実行（ユーザー承認後に削除）
    python scripts/fix/resolve_top_monopoly.py --csv PATH --execute

Author: EPUP Fix Team
Date: 2026-02-03
"""

import argparse
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/data/backups"
LOG_DIR = PROJECT_ROOT / "src/reports"

# 上位N件ごとの最大許容件数（top_monopoly_gate.pyと同じ）
MONOPOLY_LIMITS = {
    20: 1,  # Top20: 最大1件
    100: 2,  # Top100: 最大2件
    1000: 3,  # Top1000: 最大3件
}


def create_backup(csv_path: Path) -> Path:
    """
    CSVファイルのバックアップを作成

    Args:
        csv_path: バックアップ元のCSVパス

    Returns:
        バックアップファイルのパス
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"MASTER_EPISODES_CURRENT_backup_{timestamp}.csv"
    backup_path = BACKUP_DIR / backup_filename

    shutil.copy2(csv_path, backup_path)

    return backup_path


def write_deletion_log(deletions: list[dict], log_dir: Path) -> Path:
    """
    削除したエピソード情報をログファイルに記録

    Args:
        deletions: 削除情報のリスト
        log_dir: ログ出力ディレクトリ

    Returns:
        ログファイルのパス
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"deleted_top_monopoly_{timestamp}.log"
    log_path = log_dir / log_filename

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("# 上位独占エピソード削除ログ\n")
        f.write(f"# 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 削除件数: {len(deletions)}\n")
        f.write("#\n")
        f.write("# フォーマット: episode_id | person_name | tier | score | reason\n")
        f.write("#\n")
        for d in deletions:
            f.write(f"{d['episode_id']} | {d['person_name']} | {d['tier']} | {d['score']:.2f} | {d['reason']}\n")

    return log_path


def detect_monopoly_removals(df: pd.DataFrame, top_n: int = 1000) -> list[dict]:
    """
    上位独占違反を検出し、削除候補を返す

    Args:
        df: エピソードDataFrame（super_total_score降順ソート済み）
        top_n: 検査対象の上位N件

    Returns:
        削除候補リスト（重複除去済み）
    """
    # 上位N件に限定
    top_df = df.head(top_n).copy()

    # 削除候補を収集（episode_idで重複除去）
    removal_ids = set()
    removal_details = []

    # 各Tierで独占をチェック（Top20 → Top100 → Top1000の順）
    tiers_to_check = [(k, v) for k, v in MONOPOLY_LIMITS.items() if k <= top_n]

    for tier_n, limit in sorted(tiers_to_check):
        tier_df = top_df.head(tier_n)
        tier_name = f"Top{tier_n}"

        # person_idごとにグループ化
        person_groups = defaultdict(list)
        for _, row in tier_df.iterrows():
            person_id = row.get("person_id", "")
            if person_id:
                person_groups[person_id].append(row)

        # 上限超過チェック
        for person_id, person_rows in person_groups.items():
            if len(person_rows) > limit:
                # スコア降順でソート済みなので、上限以降が削除候補
                person_name = person_rows[0].get("person_name", "Unknown")
                excess_rows = person_rows[limit:]

                for row in excess_rows:
                    ep_id = str(row.get("episode_id", ""))
                    if ep_id and ep_id not in removal_ids:
                        removal_ids.add(ep_id)
                        removal_details.append(
                            {
                                "episode_id": ep_id,
                                "person_id": person_id,
                                "person_name": person_name,
                                "tier": tier_name,
                                "score": row.get("super_total_score", 0.0),
                                "reason": f"{tier_name}で{person_name}が{len(person_rows)}件占有（上限{limit}件）",
                            }
                        )

    return removal_details


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP: 上位独占エピソード削除")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"対象CSV（デフォルト: {DEFAULT_CSV}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="ドライラン（確認のみ、デフォルト）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に削除を実行（ユーザー承認後）",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=1000,
        help="検査対象の上位N件（デフォルト: 1000）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細出力",
    )

    args = parser.parse_args()

    # --executeが指定されたらdry-runをオフ
    if args.execute:
        args.dry_run = False

    is_dry_run = args.dry_run

    # ヘッダー
    print("=" * 70)
    print("EPUP: 上位独占エピソード削除")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"モード: {'ドライラン（確認のみ）' if is_dry_run else '実行モード'}")
    print("=" * 70)

    # CSV存在確認
    if not args.csv.exists():
        print(f"\n[ERROR] CSVファイルが見つかりません: {args.csv}")
        return 2

    # CSV読み込み
    print(f"\nCSV: {args.csv}")
    df = pd.read_csv(args.csv, encoding="utf-8-sig", low_memory=False)
    print(f"総エピソード数: {len(df):,}件")
    print(f"検査範囲: Top{args.top_n}")
    print("ルール: Top20≤1件, Top100≤2件, Top1000≤3件")

    # super_total_scoreで降順ソート
    df["super_total_score"] = pd.to_numeric(df["super_total_score"], errors="coerce")
    df = df.sort_values("super_total_score", ascending=False).reset_index(drop=True)

    # 削除候補を検出
    print("\n上位独占を検出中...")
    removals = detect_monopoly_removals(df, args.top_n)

    if not removals:
        print("\n[OK] 上位独占違反は検出されませんでした")
        return 0

    # サマリー表示
    print(f"\n{'=' * 70}")
    print("検出結果サマリー")
    print(f"{'=' * 70}")
    print(f"削除対象エピソード: {len(removals)}件")

    # Tier別集計
    tier_counts = defaultdict(int)
    person_counts = defaultdict(int)
    for r in removals:
        tier_counts[r["tier"]] += 1
        person_counts[r["person_name"]] += 1

    print("\nTier別削除対象数:")
    for tier in ["Top20", "Top100", "Top1000"]:
        if tier in tier_counts:
            print(f"  {tier}: {tier_counts[tier]}件")

    print("\n人物別削除対象数:")
    for person, count in sorted(person_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {person}: {count}件")
    if len(person_counts) > 10:
        print(f"  ... 他{len(person_counts) - 10}人")

    # 詳細表示
    print(f"\n{'=' * 70}")
    print("削除対象一覧")
    print(f"{'=' * 70}")

    limit_display = 20 if not args.verbose else len(removals)
    for i, r in enumerate(removals[:limit_display], 1):
        print(f"\n{i}. {r['episode_id']}")
        print(f"   人物: {r['person_name']}")
        print(f"   Tier: {r['tier']}")
        print(f"   スコア: {r['score']:.2f}")
        print(f"   理由: {r['reason']}")

    if len(removals) > limit_display:
        print(f"\n... 他{len(removals) - limit_display}件（-v で全件表示）")

    # ドライランの場合はここで終了
    if is_dry_run:
        print(f"\n{'=' * 70}")
        print("[DRY RUN] 確認のみ - 実際の削除は行われていません")
        print("=" * 70)
        print(f"\n削除対象: {len(removals)}件")
        print("\n削除を実行するには --execute オプションを付けて再実行してください:")
        print(f"  python {Path(__file__).name} --csv {args.csv} --execute")
        print(f"{'=' * 70}")
        return 0

    # 実行モード: ユーザー確認
    print(f"\n{'=' * 70}")
    print("削除確認")
    print("=" * 70)
    print(f"\n以下の {len(removals)}件 のエピソードを削除します。")
    print("この操作は取り消せません（バックアップは自動作成されます）。")
    print("")

    try:
        confirm = input("続行しますか？ [Y/n]: ").strip().lower()
    except EOFError:
        confirm = "n"

    if confirm not in ("y", "yes", ""):
        print("\n[CANCELLED] 削除をキャンセルしました")
        return 0

    # バックアップ作成
    print(f"\n{'=' * 70}")
    print("削除実行")
    print("=" * 70)

    print("\n1. バックアップを作成中...")
    backup_path = create_backup(args.csv)
    print(f"   バックアップ: {backup_path}")

    # CSVから削除
    print("\n2. CSVから該当エピソードを削除中...")
    original_count = len(df)

    # 削除対象のエピソードIDをセットに変換
    ids_to_delete = {r["episode_id"] for r in removals}

    # episode_idを文字列に変換
    df["episode_id"] = df["episode_id"].astype(str)

    # 削除対象以外を残す
    df_filtered = df[~df["episode_id"].isin(list(ids_to_delete))]
    deleted_count = original_count - len(df_filtered)

    print(f"   削除前: {original_count:,}件")
    print(f"   削除後: {len(df_filtered):,}件")
    print(f"   削除数: {deleted_count:,}件")

    # CSVを上書き保存
    print("\n3. CSVを保存中...")
    df_filtered.to_csv(args.csv, index=False, encoding="utf-8-sig")
    print(f"   保存完了: {args.csv}")

    # 削除ログ出力
    print("\n4. 削除ログを出力中...")
    log_path = write_deletion_log(removals, LOG_DIR)
    print(f"   ログ: {log_path}")

    # 完了
    print(f"\n{'=' * 70}")
    print("[SUCCESS] 削除完了")
    print("=" * 70)
    print(f"削除件数: {deleted_count:,}件")
    print(f"バックアップ: {backup_path}")
    print(f"削除ログ: {log_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
