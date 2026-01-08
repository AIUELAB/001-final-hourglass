#!/usr/bin/env python3
"""
Critical問題一括修正スクリプト

修正対象:
1. 読点なし問題: 「あなたと同じN歳のとき 」→「あなたと同じN歳のとき、」
2. 一人称問題: 「私は」→「{person_name}は」
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"


def create_backup(csv_path: Path, operation: str) -> Path:
    """バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"MASTER_EPISODES_{operation}_{timestamp}.csv"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(csv_path, backup_path)
    return backup_path


def fix_critical_patterns(
    csv_path: Path = MASTER_CSV,
    dry_run: bool = True,
    verbose: bool = False,
) -> dict:
    """
    Critical問題を一括修正

    Args:
        csv_path: CSVファイルパス
        dry_run: Trueの場合、変更を保存しない
        verbose: 詳細ログを出力

    Returns:
        修正結果のサマリー
    """
    print("=" * 60)
    print("Critical問題一括修正")
    print("=" * 60)
    print(f"対象: {csv_path}")
    print(f"モード: {'dry-run' if dry_run else '実行'}")
    print()

    # バックアップ作成
    if not dry_run:
        backup_path = create_backup(csv_path, "critical_fix")
        print(f"バックアップ: {backup_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    print(f"総エピソード数: {len(df)}")

    results = {
        "total": len(df),
        "comma_fixed": 0,
        "watashi_fixed": 0,
        "unfixable": 0,
        "comma_fixed_ids": [],
        "watashi_fixed_ids": [],
        "unfixable_ids": [],
    }

    # 問題パターン
    # 1. 読点なし: あなたと同じN歳のとき {name}は
    comma_missing_pattern = re.compile(r"^あなたと同じ(\d+)歳のとき ([^、]+)(は|の)")

    # 2. 一人称: 私は/私の
    watashi_pattern = re.compile(r"私(は|の|が|を|に|へ|と|も|から|より|で)")

    for idx, row in df.iterrows():
        episode_id = row.get("episode_id", "")
        person_name = str(row.get("person_name", "") or "")
        text = str(row.get("episode_text", "") or "")
        modified = False
        fix_types = []

        # 1. 読点なし問題を修正
        comma_match = comma_missing_pattern.match(text)
        if comma_match:
            age = comma_match.group(1)
            name_in_text = comma_match.group(2)
            particle = comma_match.group(3)
            # 読点を追加
            new_start = f"あなたと同じ{age}歳のとき、{name_in_text}{particle}"
            text = comma_missing_pattern.sub(new_start, text, count=1)
            results["comma_fixed"] += 1
            results["comma_fixed_ids"].append(episode_id)
            modified = True
            fix_types.append("comma")

        # 2. 一人称問題を修正
        if watashi_pattern.search(text) and person_name:
            # 「私は」→「{person_name}は」などに置換
            original_text = text
            text = re.sub(r"私は", f"{person_name}は", text)
            text = re.sub(r"私の", f"{person_name}の", text)
            text = re.sub(r"私が", f"{person_name}が", text)
            text = re.sub(r"私を", f"{person_name}を", text)
            text = re.sub(r"私に", f"{person_name}に", text)
            text = re.sub(r"私へ", f"{person_name}へ", text)
            text = re.sub(r"私と", f"{person_name}と", text)
            text = re.sub(r"私も", f"{person_name}も", text)
            text = re.sub(r"私から", f"{person_name}から", text)
            text = re.sub(r"私より", f"{person_name}より", text)
            text = re.sub(r"私で", f"{person_name}で", text)

            if text != original_text:
                results["watashi_fixed"] += 1
                results["watashi_fixed_ids"].append(episode_id)
                modified = True
                fix_types.append("watashi")

        # DataFrameを更新
        if modified:
            df.at[idx, "episode_text"] = text
            if verbose:
                print(f"✓ {episode_id}: {', '.join(fix_types)}")

    # サマリー出力
    print()
    print("=" * 60)
    print("修正サマリー")
    print("=" * 60)
    print(f"読点追加: {results['comma_fixed']}件")
    print(f"一人称置換: {results['watashi_fixed']}件")
    print(f"合計修正: {results['comma_fixed'] + results['watashi_fixed']}件")

    # 保存
    total_fixed = results["comma_fixed"] + results["watashi_fixed"]
    if not dry_run and total_fixed > 0:
        print()
        print("保存中...")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print("保存完了")

    return results


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="Critical問題一括修正")
    parser.add_argument("--dry-run", action="store_true", help="dry-runモード")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ")
    parser.add_argument(
        "--csv",
        default=str(MASTER_CSV),
        help="対象CSVファイル",
    )
    args = parser.parse_args()

    fix_critical_patterns(
        csv_path=Path(args.csv),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
