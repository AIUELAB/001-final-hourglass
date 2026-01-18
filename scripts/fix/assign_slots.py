#!/usr/bin/env python3
"""
Slot Assignment Script

CSVの全エピソードに年齢ベースでスロット値を割り当てる。

スロット定義:
| スロット値 | 年齢範囲    | 説明          |
|-----------|------------|---------------|
| 1         | 0-5歳      | 幼少期         |
| 10        | 6-15歳     | 少年・少女期    |
| 20        | 16-25歳    | 青年期         |
| 30        | 26-35歳    | 壮年期前期      |
| 40        | 36-45歳    | 壮年期後期      |
| 50        | 46-55歳    | 成熟期         |
| 60        | 56歳以上   | 晩年期         |

Usage:
    # dry-run（スロット分布を表示、CSVは変更しない）
    python scripts/fix/assign_slots.py --dry-run

    # 実行（全エピソードにスロット割り当て）
    python scripts/fix/assign_slots.py --execute
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Paths
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"

# Slot definitions
SLOTS = [1, 10, 20, 30, 40, 50, 60]
SLOT_LABELS = {
    1: "幼少期 (0-5歳)",
    10: "少年・少女期 (6-15歳)",
    20: "青年期 (16-25歳)",
    30: "壮年期前期 (26-35歳)",
    40: "壮年期後期 (36-45歳)",
    50: "成熟期 (46-55歳)",
    60: "晩年期 (56歳以上)",
}


def assign_slot(age: float | None) -> int | None:
    """
    年齢から最も近いスロット値を返す。

    Args:
        age: エピソードの年齢（NaN/Noneの場合はNone返却）

    Returns:
        スロット値（1, 10, 20, 30, 40, 50, 60）またはNone
    """
    if age is None:
        return None

    try:
        age_float = float(age)
        # NaN チェック（float('nan') は自分自身と等しくない）
        if age_float != age_float:
            return None
    except (ValueError, TypeError):
        return None

    # 最も近いスロットを探す
    return min(SLOTS, key=lambda slot: abs(age_float - slot))


def calculate_slot_distribution(df: pd.DataFrame, slot_column: str = "slot") -> dict[int | str, int]:
    """
    スロット分布を計算する。

    Args:
        df: データフレーム
        slot_column: スロット列名

    Returns:
        スロット値 -> 件数のマッピング
    """
    distribution: dict[int | str, int] = {}

    for slot in SLOTS:
        count = (df[slot_column] == slot).sum()
        distribution[slot] = count

    # NULL/NaN の件数
    null_count = df[slot_column].isna().sum()
    distribution["NULL"] = null_count

    return distribution


def print_distribution(distribution: dict[int | str, int], title: str = "スロット分布"):
    """
    分布を整形して出力する。
    """
    total = sum(distribution.values())

    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()
    print("  ┌─────────┬────────────────────────────────┬──────────┬────────┐")
    print("  │ スロット │ 年齢カテゴリ                  │   件数   │ 割合   │")
    print("  ├─────────┼────────────────────────────────┼──────────┼────────┤")

    for slot in SLOTS:
        count = distribution.get(slot, 0)
        pct = (count / total * 100) if total > 0 else 0
        label = SLOT_LABELS.get(slot, "")
        print(f"  │   {slot:>2}    │ {label:<28} │ {count:>8,} │ {pct:>5.1f}% │")

    print("  ├─────────┼────────────────────────────────┼──────────┼────────┤")
    null_count = distribution.get("NULL", 0)
    null_pct = (null_count / total * 100) if total > 0 else 0
    print(f"  │  NULL   │ 年齢なし / 割り当て不可        │ {null_count:>8,} │ {null_pct:>5.1f}% │")
    print("  └─────────┴────────────────────────────────┴──────────┴────────┘")
    print()
    print(f"  合計: {total:,} 件")
    print("=" * 70)


def print_age_slot_examples(df: pd.DataFrame, n: int = 10):
    """
    年齢 -> スロット 割り当ての具体例を表示する。
    """
    print("\n" + "-" * 70)
    print("  年齢 → スロット 割り当て例 (先頭10件)")
    print("-" * 70)
    print()
    print("  ┌──────────────────────────────────────┬───────┬─────────┐")
    print("  │ 人物名                               │ 年齢  │ スロット │")
    print("  ├──────────────────────────────────────┼───────┼─────────┤")

    sample = df[df["age"].notna()].head(n)
    for _, row in sample.iterrows():
        name = str(row.get("person_name", ""))[:34]
        age_val = row.get("age")
        slot_val = row.get("slot")

        # 年齢文字列
        try:
            age_float = float(age_val)  # type: ignore[arg-type]
            age_str = f"{int(age_float)}" if age_float == age_float else "N/A"
        except (ValueError, TypeError):
            age_str = "N/A"

        # スロット文字列
        try:
            slot_float = float(slot_val)  # type: ignore[arg-type]
            slot_str = f"{int(slot_float)}" if slot_float == slot_float else "N/A"
        except (ValueError, TypeError):
            slot_str = "N/A"

        print(f"  │ {name:<36} │ {age_str:>5} │   {slot_str:>2}    │")

    print("  └──────────────────────────────────────┴───────┴─────────┘")


def dry_run(df: pd.DataFrame):
    """
    Dry-run: スロット分布をシミュレートして表示。
    """
    logger.info("Dry-run モード: CSVは変更しません")

    # スロット列をシミュレート
    df_sim = df.copy()
    df_sim["slot"] = df_sim["age"].apply(assign_slot)

    # 現在の状態（slot列が存在する場合）
    if "slot" in df.columns:
        current_dist = calculate_slot_distribution(df, "slot")
        print_distribution(current_dist, "現在のスロット分布")

    # シミュレーション結果
    new_dist = calculate_slot_distribution(df_sim, "slot")
    print_distribution(new_dist, "割り当て後のスロット分布 (シミュレーション)")

    # 具体例
    print_age_slot_examples(df_sim, n=10)

    # 年齢分布のサマリー
    print("\n" + "-" * 70)
    print("  年齢統計")
    print("-" * 70)
    age_stats = df["age"].describe()
    print(f"  - 総エピソード数: {len(df):,}")
    print(f"  - 年齢あり: {df['age'].notna().sum():,}")
    print(f"  - 年齢なし (NULL): {df['age'].isna().sum():,}")
    print(f"  - 平均年齢: {age_stats['mean']:.1f}")
    print(f"  - 中央値: {age_stats['50%']:.1f}")
    print(f"  - 最小: {age_stats['min']:.0f}")
    print(f"  - 最大: {age_stats['max']:.0f}")
    print("-" * 70)

    print("\n実行コマンド:")
    print("  python scripts/fix/assign_slots.py --execute")


def execute(df: pd.DataFrame):
    """
    実行: 全エピソードにスロットを割り当てて保存。
    """
    logger.info("スロット割り当てを実行します")

    # バックアップ作成
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_pre_slot_assign_{timestamp}.csv"
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    logger.info(f"バックアップ作成: {backup_path}")

    # 現在の状態を記録
    if "slot" in df.columns:
        existing_slots = df["slot"].notna().sum()
        logger.info(f"既存スロット割り当て: {existing_slots:,} 件")
    else:
        logger.info("slot列が存在しないため新規作成します")

    # スロット割り当て
    df["slot"] = df["age"].apply(assign_slot)

    # 結果確認
    assigned_count = df["slot"].notna().sum()
    null_count = df["slot"].isna().sum()

    logger.info(f"スロット割り当て完了: {assigned_count:,} 件")
    logger.info(f"NULL (年齢なし): {null_count:,} 件")

    # CSV保存
    df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
    logger.info(f"CSV保存完了: {MASTER_CSV}")

    # 最終分布を表示
    final_dist = calculate_slot_distribution(df, "slot")
    print_distribution(final_dist, "最終スロット分布")

    # サマリー
    print("\n" + "=" * 70)
    print("  実行サマリー")
    print("=" * 70)
    print(f"  - バックアップ: {backup_path}")
    print(f"  - スロット割り当て: {assigned_count:,} 件")
    print(f"  - NULL: {null_count:,} 件")
    print(f"  - 出力ファイル: {MASTER_CSV}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="CSVの全エピソードに年齢ベースでスロット値を割り当てる",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
スロット定義:
  1  - 幼少期 (0-5歳)
  10 - 少年・少女期 (6-15歳)
  20 - 青年期 (16-25歳)
  30 - 壮年期前期 (26-35歳)
  40 - 壮年期後期 (36-45歳)
  50 - 成熟期 (46-55歳)
  60 - 晩年期 (56歳以上)

使用例:
  # 分布確認 (dry-run)
  python scripts/fix/assign_slots.py --dry-run

  # 実行
  python scripts/fix/assign_slots.py --execute
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="スロット分布を表示（CSVは変更しない）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="全エピソードにスロット割り当て実行",
    )
    args = parser.parse_args()

    # どちらのフラグも指定されていない場合はヘルプを表示
    if not args.dry_run and not args.execute:
        parser.print_help()
        sys.exit(0)

    # マスターCSV読み込み
    if not MASTER_CSV.exists():
        logger.error(f"マスターCSVが見つかりません: {MASTER_CSV}")
        sys.exit(1)

    logger.info(f"読み込み: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    logger.info(f"総エピソード数: {len(df):,}")

    # age列の確認
    if "age" not in df.columns:
        logger.error("CSVに 'age' 列がありません")
        sys.exit(1)

    if args.dry_run:
        dry_run(df)
    elif args.execute:
        execute(df)


if __name__ == "__main__":
    main()
