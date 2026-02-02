#!/usr/bin/env python3
"""
未来年号エピソード削除スクリプト

C2違反（2027年以降の年号を含むエピソード）を削除する。
episode_textに2027年以降の年号が含まれるエピソードは、
架空の未来イベント（「2029年の東京国際映画祭で受賞」など）であり、
事実違反となる。

処理ロジック:
1. CSVを読み込む
2. 各行について:
   - episode_textから年号パターンを検索: (202[7-9]|20[3-9]\d|21\d{2})年
   - マッチした場合、そのエピソードを削除対象としてマーク
3. 削除対象以外のエピソードのみを保存

Usage:
    # ドライラン（確認のみ）
    python scripts/fix/remove_future_event_episodes.py --dry-run

    # 実行（実際に削除）
    python scripts/fix/remove_future_event_episodes.py --execute

    # 詳細出力
    python scripts/fix/remove_future_event_episodes.py --execute --verbose

Author: EPUP Fix Team
Date: 2026-02-02
RCA: C2違反 - 未来年号エピソード
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/data/backups"
LOG_DIR = PROJECT_ROOT / "src/reports/logs"

# 2027年以降を検出するパターン
# 202[7-9]年、203X年、204X年...209X年、21XX年
FUTURE_YEAR_PATTERN = re.compile(r"(202[7-9]|20[3-9]\d|21\d{2})年")


def detect_future_years(text: str) -> list[str]:
    """
    テキストから未来年号を検出する

    Args:
        text: エピソードテキスト

    Returns:
        検出された未来年号のリスト
    """
    if pd.isna(text) or not isinstance(text, str):
        return []

    matches = FUTURE_YEAR_PATTERN.findall(text)
    return [f"{m}年" for m in matches]


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
    backup_filename = f"MASTER_EPISODES_{timestamp}_pre_future_fix.csv"
    backup_path = BACKUP_DIR / backup_filename

    shutil.copy2(csv_path, backup_path)

    return backup_path


def write_deletion_log(
    deleted_records: list[dict],
    log_dir: Path,
) -> Path:
    """
    削除したエピソードをログファイルに記録

    Args:
        deleted_records: 削除したエピソードの詳細リスト
        log_dir: ログ出力ディレクトリ

    Returns:
        ログファイルのパス
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"deleted_future_events_{timestamp}.log"
    log_path = log_dir / log_filename

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("# 未来年号エピソード削除ログ\n")
        f.write(f"# 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 削除件数: {len(deleted_records)}\n")
        f.write("# RCA: C2違反 - 未来年号エピソード\n")
        f.write("#\n")
        f.write("# 削除したエピソード一覧:\n")
        f.write("# episode_id | person_name | 検出された年号\n")
        f.write("#\n")
        for rec in deleted_records:
            f.write(f"{rec['episode_id']} | {rec['person_name']} | {rec['years']}\n")

    return log_path


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="C2違反: 未来年号エピソード削除スクリプト")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（確認のみ）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に削除を実行",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細出力",
    )
    parser.add_argument(
        "--show-samples",
        type=int,
        default=20,
        help="サンプル表示件数（デフォルト: 20）",
    )

    args = parser.parse_args()

    # --executeも--dry-runも指定されていない場合はdry-run
    if not args.execute and not args.dry_run:
        args.dry_run = True

    is_dry_run = args.dry_run or not args.execute

    # ヘッダー
    print("=" * 70)
    print("C2違反: 未来年号エピソード削除スクリプト")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"モード: {'ドライラン（確認のみ）' if is_dry_run else '実行モード'}")
    print("=" * 70)

    # マスターCSV存在確認
    if not MASTER_CSV.exists():
        print(f"\n[ERROR] マスターCSVが見つかりません: {MASTER_CSV}")
        return 2

    # マスターCSV読み込み
    print(f"\nマスターCSV: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    print(f"現在のエピソード数: {len(df):,}件")

    # episode_textから未来年号を検出
    print("\n未来年号（2027年以降）を検出中...")

    deleted_records = []
    delete_indices = []

    for idx, row in df.iterrows():
        episode_text = row.get("episode_text", "")
        future_years = detect_future_years(episode_text)

        if future_years:
            delete_indices.append(idx)
            deleted_records.append(
                {
                    "episode_id": row.get("episode_id", "N/A"),
                    "person_name": row.get("person_name", "N/A"),
                    "years": ", ".join(future_years),
                    "text_preview": str(episode_text)[:100] if episode_text else "",
                }
            )

    print("\n検出結果:")
    print(f"  削除対象: {len(deleted_records):,}件")

    if not deleted_records:
        print("\n[INFO] 未来年号を含むエピソードはありませんでした。")
        return 0

    # 年号別の集計
    year_counts = {}
    for rec in deleted_records:
        for y in rec["years"].split(", "):
            year_counts[y] = year_counts.get(y, 0) + 1

    print("\n年号別件数（上位10件）:")
    for year, count in sorted(year_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {year}: {count:,}件")

    # サンプル表示
    if args.verbose or is_dry_run:
        print(f"\n{'=' * 70}")
        print(f"削除対象エピソード（{min(args.show_samples, len(deleted_records))}件）")
        print("=" * 70)

        for i, rec in enumerate(deleted_records[: args.show_samples], 1):
            print(f"\n{i}. {rec['episode_id']}")
            print(f"   人物名: {rec['person_name']}")
            print(f"   検出年号: {rec['years']}")
            print(f"   テキスト: {rec['text_preview']}...")

        if len(deleted_records) > args.show_samples:
            print(f"\n   ... 他 {len(deleted_records) - args.show_samples:,}件")

    # ドライランの場合はここで終了
    if is_dry_run:
        print(f"\n{'=' * 70}")
        print("[DRY RUN] 確認のみ - 実際の削除は行われていません")
        print("=" * 70)
        print(f"\n[INFO] 削除対象: {len(deleted_records):,}件")
        print("\n削除を実行するには --execute オプションを付けて再実行してください:")
        print("  python scripts/fix/remove_future_event_episodes.py --execute")
        print(f"{'=' * 70}")
        return 0

    # 実行モード: バックアップ作成
    print(f"\n{'=' * 70}")
    print("削除実行")
    print("=" * 70)

    print("\n1. バックアップを作成中...")
    backup_path = create_backup(MASTER_CSV)
    print(f"   [INFO] バックアップ作成: {backup_path}")

    # CSVから削除
    print("\n2. CSVから該当エピソードを削除中...")
    original_count = len(df)

    # 削除対象以外を残す
    df_filtered = df.drop(delete_indices)
    deleted_count = original_count - len(df_filtered)

    print(f"   削除前: {original_count:,}件")
    print(f"   削除後: {len(df_filtered):,}件")
    print(f"   [INFO] 削除完了: {deleted_count:,}件")

    # CSVを上書き保存
    print("\n3. CSVを保存中...")
    df_filtered.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
    print(f"   保存完了: {MASTER_CSV}")

    # 削除ログ出力
    print("\n4. 削除ログを出力中...")
    log_path = write_deletion_log(deleted_records, LOG_DIR)
    print(f"   ログ: {log_path}")

    # 完了
    print(f"\n{'=' * 70}")
    print("[SUCCESS] 削除完了")
    print("=" * 70)
    print(f"削除件数: {deleted_count:,}件")
    print(f"残存エピソード: {len(df_filtered):,}件")
    print(f"バックアップ: {backup_path}")
    print(f"ログファイル: {log_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
