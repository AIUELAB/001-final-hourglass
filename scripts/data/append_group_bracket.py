#!/usr/bin/env python3
"""
グループ名括弧追記スクリプト

グループ所属人物のエピソードリード文に「（グループ名）」を追記する。

Usage:
    # ドライラン（変更内容の確認のみ）
    python scripts/append_group_bracket.py

    # 本番実行
    python scripts/append_group_bracket.py --execute

    # レポート付き実行
    python scripts/append_group_bracket.py --execute --report
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd

from src.bracket_group_appender import should_append_group, append_group_bracket_to_lead


# マスターCSVパス
MASTER_CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
REPORTS_DIR = Path("reports")


def load_master_csv() -> pd.DataFrame:
    """マスターCSVを読み込み"""
    if not MASTER_CSV_PATH.exists():
        raise FileNotFoundError(f"マスターCSVが見つかりません: {MASTER_CSV_PATH}")

    df = pd.read_csv(MASTER_CSV_PATH, encoding="utf-8-sig")
    print(f"✅ マスターCSV読み込み完了: {len(df)}件")
    return df


def create_backup(df: pd.DataFrame) -> Path:
    """バックアップを作成"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = MASTER_CSV_PATH.parent / f"{MASTER_CSV_PATH.stem}.bak_bracket_{timestamp}.csv"

    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"💾 バックアップ作成: {backup_path}")
    return backup_path


def process_episodes(
    df: pd.DataFrame,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    エピソードを処理してグループ名括弧を追記

    Args:
        df: エピソードデータフレーム
        dry_run: ドライランモード（True: プレビューのみ、False: 実際に変更）

    Returns:
        処理結果の詳細
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "total": len(df),
        "processed": 0,
        "skipped": {},
        "changes": [],
    }

    for idx, row in df.iterrows():
        person_name = str(row.get("person_name", ""))
        group_name = str(row.get("group_name", ""))
        episode_text = str(row.get("episode_text", ""))
        person_type = str(row.get("person_type", ""))
        is_group_member = str(row.get("is_group_member", ""))

        # 判定
        should, reason = should_append_group(
            person_name=person_name,
            group_name=group_name,
            episode_text=episode_text,
            person_type=person_type,
            is_group_member=is_group_member,
        )

        if not should:
            # スキップ
            if reason not in results["skipped"]:
                results["skipped"][reason] = 0
            results["skipped"][reason] += 1
            continue

        # 追記実行
        try:
            new_text = append_group_bracket_to_lead(
                episode_text=episode_text,
                person_name=person_name,
                group_name=group_name,
            )

            # 変更記録
            change_record = {
                "index": int(idx),
                "episode_id": str(row.get("episode_id", "")),
                "person_id": str(row.get("person_id", "")),
                "person_name": person_name,
                "group_name": group_name,
                "before": episode_text[:100] + "..." if len(episode_text) > 100 else episode_text,
                "after": new_text[:100] + "..." if len(new_text) > 100 else new_text,
            }
            results["changes"].append(change_record)
            results["processed"] += 1

            # 実行モードの場合、DataFrameを更新
            if not dry_run:
                df.at[idx, "episode_text"] = new_text

        except Exception as e:
            print(f"⚠️ エラー（行{idx}）: {person_name} - {e}")

    return results


def save_report(results: Dict[str, Any], report_path: Path):
    """レポートをJSON形式で保存"""
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート保存: {report_path}")


def print_summary(results: Dict[str, Any]):
    """処理結果のサマリーを表示"""
    print("\n" + "=" * 70)
    print("📊 処理結果サマリー")
    print("=" * 70)
    print(f"総エピソード数: {results['total']:,}件")
    print(f"追記実行: {results['processed']:,}件")
    print(f"スキップ: {sum(results['skipped'].values()):,}件")

    if results["skipped"]:
        print("\n【スキップ理由の内訳】")
        for reason, count in sorted(results["skipped"].items(), key=lambda x: -x[1]):
            print(f"  - {reason}: {count:,}件")

    if results["changes"]:
        print("\n【変更例（最大5件）】")
        for i, change in enumerate(results["changes"][:5], 1):
            print(f"\n{i}. {change['person_name']} （{change['group_name']}）")
            print(f"   Before: {change['before']}")
            print(f"   After:  {change['after']}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="グループ名括弧追記スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # ドライラン（変更内容の確認のみ）
  python scripts/append_group_bracket.py

  # 本番実行
  python scripts/append_group_bracket.py --execute

  # レポート付き実行
  python scripts/append_group_bracket.py --execute --report
        """,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に変更を適用（デフォルト: ドライラン）",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="詳細レポートをJSON形式で出力",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("📝 グループ名括弧追記スクリプト")
    print("=" * 70)
    print(f"モード: {'実行' if args.execute else 'ドライラン（プレビュー）'}")
    print()

    # CSV読み込み
    df = load_master_csv()

    # バックアップ作成（実行モードの場合のみ）
    if args.execute:
        create_backup(df)

    # 処理実行
    print("\n🔄 処理中...")
    results = process_episodes(df, dry_run=not args.execute)

    # サマリー表示
    print_summary(results)

    # 実行モードの場合、CSVを保存
    if args.execute:
        print("\n💾 マスターCSVを更新中...")
        df.to_csv(MASTER_CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"✅ 更新完了: {MASTER_CSV_PATH}")

    # レポート保存
    if args.report or args.execute:
        REPORTS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode = "execute" if args.execute else "dryrun"
        report_path = REPORTS_DIR / f"bracket_append_{mode}_{timestamp}.json"
        save_report(results, report_path)

    # 最終メッセージ
    print("\n" + "=" * 70)
    if args.execute:
        print("✅ 処理完了: 変更を適用しました")
        print(f"   追記件数: {results['processed']:,}件")
    else:
        print("💡 ドライランモード: 実際の変更は行われていません")
        print(f"   追記対象: {results['processed']:,}件")
        print("\n   本番実行するには --execute オプションを追加してください：")
        print("   python scripts/append_group_bracket.py --execute")
    print("=" * 70)


if __name__ == "__main__":
    main()
