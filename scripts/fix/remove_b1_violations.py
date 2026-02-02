#!/usr/bin/env python3
"""
EPUP Phase 20 Step 1: B1違反エピソード削除スクリプト

B1違反（人物名が本文に不在）のエピソードをCSVから削除する。

検出ロジック:
- detect_all_inconsistencies.py の check_name_text_consistency() と同じロジック
- 「のとき、{person_name}は」パターンが本文に含まれていない
- 名前の部分一致（姓/名/通称）もチェック

処理フロー:
1. MASTER_EPISODES_CURRENT.csv のバックアップ作成
2. B1違反エピソードを検出
3. 違反エピソードをCSVから削除
4. 削除前後の件数を報告

使用方法:
    # ドライラン（確認のみ、デフォルト）
    python scripts/fix/remove_b1_violations.py
    python scripts/fix/remove_b1_violations.py --dry-run

    # 実行（実際に削除）
    python scripts/fix/remove_b1_violations.py --execute

    # 詳細出力
    python scripts/fix/remove_b1_violations.py --verbose

Author: EPUP Fix Team
Date: 2026-02-02
"""

import argparse
import csv
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/data/backups"
LOG_DIR = PROJECT_ROOT / "src/reports/logs"


@dataclass
class B1ViolationRecord:
    """B1違反レコード"""

    episode_id: str
    person_name: str
    text_preview: str
    detail: str


def load_episodes() -> list[dict]:
    """エピソード読み込み"""
    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def check_b1_violation(row: dict) -> B1ViolationRecord | None:
    """
    B1違反（人物名が本文に不在）をチェック

    detect_all_inconsistencies.py の check_name_text_consistency() と同じロジック
    """
    person_name = row.get("person_name", "")
    text = row.get("episode_text", "")
    episode_id = row.get("episode_id", "")

    if not person_name or not text:
        return None

    # 「あなたと同じXX歳のとき、{person_name}は」パターンをチェック
    expected_pattern = f"のとき、{person_name}は"
    alt_pattern = f"のとき、{person_name}の"

    if expected_pattern not in text and alt_pattern not in text:
        # 名前の一部（姓/名/通称）が含まれているかチェック
        # スペース区切り、中黒区切り、姓名分離などを考慮
        name_parts = re.split(r"[\s・　]+", person_name)
        # 2文字以上の部分一致でOK（略称使用は許容）
        found_partial = any(part in text[:150] for part in name_parts if len(part) >= 2)

        # 姓のみ、名のみでも許容（例: モーツァルト、ダーウィン）
        if not found_partial:
            return B1ViolationRecord(
                episode_id=episode_id,
                person_name=person_name,
                text_preview=text[:80] + "..." if len(text) > 80 else text,
                detail=f"person_name='{person_name}' not found in text start",
            )

    return None


def detect_all_b1_violations() -> list[B1ViolationRecord]:
    """全エピソードからB1違反を検出"""
    episodes = load_episodes()
    violations = []

    for row in episodes:
        violation = check_b1_violation(row)
        if violation:
            violations.append(violation)

    return violations


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


def write_deletion_log(deleted_records: list[B1ViolationRecord], log_dir: Path) -> Path:
    """
    削除したエピソードをログファイルに記録

    Args:
        deleted_records: 削除したレコードのリスト
        log_dir: ログ出力ディレクトリ

    Returns:
        ログファイルのパス
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"deleted_b1_violations_{timestamp}.log"
    log_path = log_dir / log_filename

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("# B1違反（人物名が本文に不在）エピソード削除ログ\n")
        f.write(f"# 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 削除件数: {len(deleted_records)}\n")
        f.write("#\n")
        f.write("# 削除したエピソード一覧:\n")
        f.write("# episode_id | person_name | detail\n")
        f.write("#\n")
        for record in deleted_records:
            f.write(f"{record.episode_id} | {record.person_name} | {record.detail}\n")

    return log_path


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP Phase 20: B1違反エピソード削除")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に削除を実行（デフォルトはドライラン）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライランモード（デフォルト動作、--executeと排他）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細出力",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="表示する最大件数（デフォルト: 30）",
    )

    args = parser.parse_args()
    is_dry_run = not args.execute

    # ヘッダー
    print("=" * 70)
    print("EPUP Phase 20 Step 1: B1違反エピソード削除")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"モード: {'ドライラン（確認のみ）' if is_dry_run else '実行モード'}")
    print("=" * 70)

    # マスターCSV存在確認
    if not MASTER_CSV.exists():
        print(f"\nError: Master CSV not found: {MASTER_CSV}")
        return 2

    print(f"\nマスターCSV: {MASTER_CSV}")

    # B1違反検出
    print("\nB1違反エピソードを検出中...")
    violations = detect_all_b1_violations()

    if not violations:
        print("\n[OK] B1違反エピソードは検出されませんでした")
        return 0

    # サマリー
    print(f"\n{'=' * 70}")
    print("検出結果サマリー")
    print(f"{'=' * 70}")
    print(f"B1違反エピソード: {len(violations)}件")

    # 人物名別集計
    person_counts: dict[str, int] = {}
    for v in violations:
        person_counts[v.person_name] = person_counts.get(v.person_name, 0) + 1

    sorted_persons = sorted(person_counts.items(), key=lambda x: x[1], reverse=True)

    print("\n人物名別違反数（上位10）:")
    for person, count in sorted_persons[:10]:
        print(f"  {person}: {count}件")

    # 詳細出力
    if args.verbose:
        limit = args.limit
        print(f"\n{'=' * 70}")
        print(f"違反エピソード詳細（上位{min(limit, len(violations))}件）")
        print(f"{'=' * 70}")

        for i, record in enumerate(violations[:limit], 1):
            print(f"\n{i}. {record.episode_id}")
            print(f"   人物名: {record.person_name}")
            print(f"   本文冒頭: {record.text_preview[:60]}...")
            print(f"   詳細: {record.detail}")

    # 削除対象エピソードID一覧
    print(f"\n{'=' * 70}")
    print("削除対象エピソードID一覧")
    print(f"{'=' * 70}")
    print(f"総数: {len(violations)}件")
    for v in violations[:20]:
        print(f"  {v.episode_id} ({v.person_name})")
    if len(violations) > 20:
        print(f"  ... 他 {len(violations) - 20}件")

    # ドライランの場合はここで終了
    if is_dry_run:
        print(f"\n{'=' * 70}")
        print("[DRY RUN] 確認のみ - 実際の削除は行われていません")
        print("削除を実行するには --execute オプションを付けて再実行してください:")
        print("  python scripts/fix/remove_b1_violations.py --execute")
        print(f"{'=' * 70}")
        return 0

    # 実行モード: バックアップ作成
    print(f"\n{'=' * 70}")
    print("削除実行")
    print(f"{'=' * 70}")

    print("\n1. バックアップを作成中...")
    backup_path = create_backup(MASTER_CSV)
    print(f"   バックアップ: {backup_path}")

    # CSVから削除
    print("\n2. CSVから該当エピソードを削除中...")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    original_count = len(df)

    # 削除対象のエピソードIDをリストに変換
    ids_to_delete = [v.episode_id for v in violations]

    # エピソードID列を文字列に変換して比較
    df["episode_id"] = df["episode_id"].astype(str)

    # 削除対象以外を残す
    df_filtered = df[~df["episode_id"].isin(ids_to_delete)]
    deleted_count = original_count - len(df_filtered)

    print(f"   削除前: {original_count:,}件")
    print(f"   削除後: {len(df_filtered):,}件")
    print(f"   削除数: {deleted_count:,}件")

    # CSVを上書き保存
    print("\n3. CSVを保存中...")
    df_filtered.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
    print(f"   保存完了: {MASTER_CSV}")

    # 削除ログ出力
    print("\n4. 削除ログを出力中...")
    log_path = write_deletion_log(violations, LOG_DIR)
    print(f"   ログ: {log_path}")

    # 完了
    print(f"\n{'=' * 70}")
    print("[SUCCESS] B1違反エピソード削除完了")
    print(f"{'=' * 70}")
    print(f"削除件数: {deleted_count:,}件")
    print(f"バックアップ: {backup_path}")
    print(f"削除ログ: {log_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
