#!/usr/bin/env python3
"""
normalize_state_labels.py - 状態ラベル付き人物名を正規化するスクリプト

状態ラベル（「ポケモン博士」「赤ちゃん」「金色の」「老」など）が
付いた人物名を正規名に変換する。

Usage:
    python scripts/fix/normalize_state_labels.py --dry-run        # 対象確認（デフォルト）
    python scripts/fix/normalize_state_labels.py --check-collision # 衝突チェック
    python scripts/fix/normalize_state_labels.py --execute         # 実行
    python scripts/fix/normalize_state_labels.py --verify          # 正規化後の検証
"""

import argparse
import csv
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/backups"

# 正規化マッピング（16件）
# 注意: 老界王神は界王神と別キャラなので除外
NORMALIZATION_MAP = {
    # ポケモン博士 → X博士（10件）
    "ポケモン博士アララギ": "アララギ博士",
    "ポケモン博士オーキド": "オーキド博士",
    "ポケモン博士ウツギ": "ウツギ博士",
    "ポケモン博士オダマキ": "オダマキ博士",
    "ポケモン博士ナナカマド": "ナナカマド博士",
    "ポケモン博士プラターヌ": "プラターヌ博士",
    "ポケモン博士ククイ": "ククイ博士",
    "ポケモン博士マグノリア": "マグノリア博士",
    "ポケモン博士オーリム": "オーリム博士",
    "ポケモン博士フトゥー": "フトゥー博士",
    # 赤ちゃん → 正規名（4件）
    "赤ちゃんピカチュウ": "ピカチュウ",
    "赤ちゃんしんのすけ": "野原しんのすけ",
    "赤ちゃんしずくちゃん": "しずくちゃん",
    "赤ちゃんメロンパンナちゃん": "メロンパンナちゃん",
    # 形態プレフィックス除去（2件）
    "金色のフリーザ": "フリーザ",
    "老ソフィー": "ソフィー",
}

# person_id統合マッピング（既存キャラに統合するケース）
# 元のperson_id → 統合先のperson_id
PERSON_ID_MERGE_MAP = {
    "PD5B3249": "P59F8D5D",  # 赤ちゃんピカチュウ → ピカチュウ
    "P60A490A": "PF9B0150",  # 赤ちゃんしんのすけ → 野原しんのすけ
}


def load_master_csv() -> tuple[list[dict], list[str]]:
    """マスターCSVを読み込む"""
    if not MASTER_CSV.exists():
        print(f"❌ マスターCSVが見つかりません: {MASTER_CSV}")
        sys.exit(1)

    try:
        with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames) if reader.fieldnames else []
            if not fieldnames:
                print(f"❌ CSVにヘッダーがありません: {MASTER_CSV}")
                sys.exit(1)
            rows = list(reader)
    except UnicodeDecodeError as e:
        print(f"❌ CSVのエンコーディング問題: {e}")
        print("対処: ファイルがUTF-8形式か確認してください。")
        sys.exit(1)
    except csv.Error as e:
        print(f"❌ CSV形式が不正: {e}")
        sys.exit(1)
    except PermissionError:
        print(f"❌ ファイルの読み取り権限がありません: {MASTER_CSV}")
        sys.exit(1)

    return rows, fieldnames


def find_targets(rows: list[dict]) -> dict[str, list[dict]]:
    """正規化対象の行を検索"""
    targets = defaultdict(list)

    for row in rows:
        person_name = row.get("person_name", "")
        if person_name in NORMALIZATION_MAP:
            targets[person_name].append(row)

    return targets


def check_collisions(rows: list[dict], targets: dict[str, list[dict]]) -> dict[str, dict]:
    """正規化先との衝突をチェック"""
    # 現在のperson_nameとperson_idのマッピングを構築
    existing_names = {}
    for row in rows:
        name = row.get("person_name", "")
        pid = row.get("person_id", "")
        if name and pid:
            if name not in existing_names:
                existing_names[name] = set()
            existing_names[name].add(pid)

    collisions = {}
    for original, normalized in NORMALIZATION_MAP.items():
        if original not in targets:
            continue

        if normalized in existing_names:
            # 正規化先が既存
            original_pids = {r.get("person_id") for r in targets[original]}
            existing_pids = existing_names[normalized]

            collisions[original] = {
                "normalized": normalized,
                "original_person_ids": original_pids,
                "existing_person_ids": existing_pids,
                "is_same_person": original_pids == existing_pids or original_pids.issubset(existing_pids),
            }

    return collisions


def create_backup() -> Path:
    """バックアップを作成"""
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print(f"❌ バックアップディレクトリを作成できません: {BACKUP_DIR}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_before_normalize_{timestamp}.csv"

    try:
        shutil.copy2(MASTER_CSV, backup_path)
    except (PermissionError, OSError, shutil.Error) as e:
        print(f"❌ バックアップ作成失敗: {e}")
        print("バックアップなしでは処理を続行できません。")
        sys.exit(1)

    return backup_path


def execute_normalization(rows: list[dict], fieldnames: list[str]) -> tuple[int, dict[str, int]]:
    """正規化を実行（person_id統合を含む）"""
    changes = defaultdict(int)
    total_changed = 0
    person_id_merged = 0

    for row in rows:
        person_name = row.get("person_name", "")
        person_id = row.get("person_id", "")

        if person_name in NORMALIZATION_MAP:
            normalized = NORMALIZATION_MAP[person_name]
            row["person_name"] = normalized
            changes[f"{person_name} → {normalized}"] += 1
            total_changed += 1

            # person_id統合が必要な場合
            if person_id in PERSON_ID_MERGE_MAP:
                new_person_id = PERSON_ID_MERGE_MAP[person_id]
                row["person_id"] = new_person_id
                person_id_merged += 1

    # 一時ファイルに書き込み後、アトミックに置換
    temp_path = MASTER_CSV.with_suffix(".tmp")

    try:
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    except (PermissionError, OSError) as e:
        print(f"❌ ファイル書き込み失敗: {e}")
        if temp_path.exists():
            temp_path.unlink()
        sys.exit(1)

    # アトミックな置換
    try:
        temp_path.replace(MASTER_CSV)
    except OSError as e:
        print(f"❌ ファイル置換失敗: {e}")
        print(f"一時ファイルは保持: {temp_path}")
        sys.exit(1)

    if person_id_merged > 0:
        print(f"📌 person_id統合: {person_id_merged}件")

    return total_changed, dict(changes)


def verify_normalization(rows: list[dict]) -> list[str]:
    """正規化後に状態ラベルが残っていないか検証"""
    remaining = []
    state_labels = list(NORMALIZATION_MAP.keys())

    for row in rows:
        person_name = row.get("person_name", "")
        if person_name in state_labels:
            remaining.append(person_name)

    return remaining


def print_summary_table(targets: dict[str, list[dict]]):
    """サマリーテーブルを表示"""
    print("\n" + "=" * 80)
    print("状態ラベル正規化対象サマリー")
    print("=" * 80)

    if not targets:
        print("\n✅ 正規化対象は見つかりませんでした。")
        return

    # テーブルヘッダー
    print(f"\n{'元の名前':<30} {'→':<3} {'正規名':<25} {'件数':>8}")
    print("-" * 80)

    total = 0
    for original in sorted(targets.keys()):
        normalized = NORMALIZATION_MAP[original]
        count = len(targets[original])
        total += count
        print(f"{original:<30} {'→':<3} {normalized:<25} {count:>8}件")

    print("-" * 80)
    print(f"{'合計':<60} {total:>8}件")
    print("=" * 80)


def print_collision_warnings(collisions: dict[str, dict]):
    """衝突警告を表示"""
    if not collisions:
        print("\n✅ 衝突は検出されませんでした。")
        return

    print("\n" + "=" * 80)
    print("⚠️  衝突警告")
    print("=" * 80)

    for original, info in collisions.items():
        normalized = info["normalized"]
        is_same = info["is_same_person"]

        print(f"\n{original} → {normalized}")
        print(f"  元のperson_id: {info['original_person_ids']}")
        print(f"  既存のperson_id: {info['existing_person_ids']}")

        if is_same:
            print("  ✅ 同一人物 - 安全にマージ可能")
        else:
            print("  ⚠️  異なるperson_id - 要確認")


def main():
    parser = argparse.ArgumentParser(description="状態ラベル付き人物名を正規化する")
    parser.add_argument("--dry-run", action="store_true", default=True, help="対象を表示するのみ（デフォルト）")
    parser.add_argument("--check-collision", action="store_true", help="正規化先との衝突をチェック")
    parser.add_argument("--execute", action="store_true", help="実際に正規化を実行")
    parser.add_argument("--verify", action="store_true", help="正規化後の検証")

    args = parser.parse_args()

    # CSVを読み込み
    print(f"📂 マスターCSV: {MASTER_CSV}")
    rows, fieldnames = load_master_csv()
    print(f"📊 総エピソード数: {len(rows):,}件")

    # 対象を検索
    targets = find_targets(rows)

    if args.verify:
        # 検証モード
        remaining = verify_normalization(rows)
        if remaining:
            print(f"\n❌ 状態ラベルが残っています: {len(set(remaining))}種類")
            for name in sorted(set(remaining)):
                print(f"  - {name}")
            sys.exit(1)
        else:
            print("\n✅ 状態ラベルは全て正規化済みです。")
            sys.exit(0)

    if args.check_collision:
        # 衝突チェックモード
        print_summary_table(targets)
        collisions = check_collisions(rows, targets)
        print_collision_warnings(collisions)
        sys.exit(0)

    if args.execute:
        # 実行モード
        if not targets:
            print("\n✅ 正規化対象は見つかりませんでした。")
            sys.exit(0)

        # 衝突チェック
        collisions = check_collisions(rows, targets)
        dangerous_collisions = []
        for k, v in collisions.items():
            if v["is_same_person"]:
                continue
            # PERSON_ID_MERGE_MAPで処理されるケースは安全
            original_pids = v["original_person_ids"]
            if all(pid in PERSON_ID_MERGE_MAP for pid in original_pids):
                continue
            dangerous_collisions.append(k)

        if dangerous_collisions:
            print("\n❌ 処理されていない衝突があります。")
            for k in dangerous_collisions:
                print(f"   - {k}")
            print("   --check-collision で詳細を確認してください。")
            sys.exit(1)

        # バックアップ作成
        backup_path = create_backup()
        print(f"\n💾 バックアップ作成: {backup_path}")

        # 実行
        total, changes = execute_normalization(rows, fieldnames)

        print("\n" + "=" * 80)
        print("✅ 正規化完了")
        print("=" * 80)

        for change, count in sorted(changes.items()):
            print(f"  {change}: {count}件")

        print(f"\n合計: {total}件のエピソードを更新しました。")
        sys.exit(0)

    # デフォルト: dry-run
    print_summary_table(targets)

    if targets:
        print("\n💡 実行するには --execute フラグを付けてください。")
        print("💡 衝突チェックは --check-collision で確認できます。")


if __name__ == "__main__":
    main()
