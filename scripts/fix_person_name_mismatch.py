#!/usr/bin/env python3
"""
リード文の人物名不一致修正スクリプト

CSVのperson_nameとエピソード本文のリード文の人物名が不一致のエピソードを修正する。

Usage:
    # ドライラン（変更内容の確認のみ）
    python scripts/fix_person_name_mismatch.py

    # 本番実行
    python scripts/fix_person_name_mismatch.py --execute
"""

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd


# マスターCSVパス
MASTER_CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# 修正マッピング（リード文の誤った名前 → 正しい名前）
CORRECTION_MAP = {
    "ヘプバーン": "オードリー・ヘプバーン",
    "Terry Gilliam": "テリー・ギリアム",
    "Camila Cabello": "カミラ・カベロ",
    "Justin Timberlake": "ジャスティン・ティンバーレイク",
    "George Michael": "ジョージ・マイケル",
    "Jun Maeda": "ジュン・マエダ",
    "アレクサンドル・ボロディン": "アレクサンダー・ボロディン",
    "コナー・マクデイビッド": "アイスホッケー・コナー・マクデイビッド",
    "L'Arc〜en〜CielのKen": "ken",
}


def fix_lead_person_name(episode_text: str, wrong_name: str, correct_name: str) -> str:
    """
    リード文の人物名を修正

    Args:
        episode_text: エピソード本文
        wrong_name: 誤った人物名
        correct_name: 正しい人物名

    Returns:
        修正後のエピソード本文
    """
    # リード文パターン: あなたと同じ{age}歳のとき、{person_name}は
    # 括弧がある場合とない場合の両方に対応
    pattern = re.compile(
        rf"^(あなたと同じ\d+歳のとき、){re.escape(wrong_name)}((?:（.+?）)?は)",
        re.DOTALL,
    )

    match = pattern.match(episode_text)
    if not match:
        raise ValueError(f"リード文のパターンが想定外です: {episode_text[:100]}...")

    prefix = match.group(1)  # あなたと同じ27歳のとき、
    bracket_and_wa = match.group(2)  # は or （グループ名）は
    rest = episode_text[match.end() :]  # 残りの本文

    # 修正後のテキスト
    new_text = f"{prefix}{correct_name}{bracket_and_wa}{rest}"

    return new_text


def find_and_fix_mismatches(df: pd.DataFrame, dry_run: bool = True) -> Dict[str, Any]:
    """
    人物名不一致を検出して修正

    Args:
        df: エピソードデータフレーム
        dry_run: ドライランモード（True: プレビューのみ、False: 実際に変更）

    Returns:
        処理結果の詳細
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "total": len(df),
        "fixed": 0,
        "skipped": 0,
        "changes": [],
    }

    lead_pattern = re.compile(r"^あなたと同じ(\d+)歳のとき、(.+?)(?:（.+?）)?は")

    for idx, row in df.iterrows():
        person_name = str(row.get("person_name", ""))
        episode_text = str(row.get("episode_text", ""))

        # リード文から人物名を抽出
        match = lead_pattern.match(episode_text)
        if not match:
            continue

        age = match.group(1)
        lead_name = match.group(2)

        # 括弧を除去してチェック
        if lead_name == person_name:
            continue  # 一致している場合はスキップ

        # 修正マップに該当するか確認
        if lead_name not in CORRECTION_MAP:
            results["skipped"] += 1
            continue

        correct_name = CORRECTION_MAP[lead_name]

        # CSVのperson_nameと一致するか確認
        if correct_name != person_name:
            print(f"⚠️ 警告（行{idx}）: CSV={person_name}, " f"修正マップ={correct_name} - 不一致")
            results["skipped"] += 1
            continue

        # 修正実行
        try:
            new_text = fix_lead_person_name(episode_text, lead_name, correct_name)

            # 変更記録
            change_record = {
                "index": int(idx),
                "episode_id": str(row.get("episode_id", "")),
                "person_id": str(row.get("person_id", "")),
                "person_name": person_name,
                "age": age,
                "wrong_name": lead_name,
                "correct_name": correct_name,
                "before": episode_text[:100] + "..." if len(episode_text) > 100 else episode_text,
                "after": new_text[:100] + "..." if len(new_text) > 100 else new_text,
            }
            results["changes"].append(change_record)
            results["fixed"] += 1

            # 実行モードの場合、DataFrameを更新
            if not dry_run:
                df.at[idx, "episode_text"] = new_text

        except Exception as e:
            print(f"❌ エラー（行{idx}）: {person_name} - {e}")

    return results


def print_summary(results: Dict[str, Any]):
    """処理結果のサマリーを表示"""
    print("\n" + "=" * 80)
    print("📊 処理結果サマリー")
    print("=" * 80)
    print(f"総エピソード数: {results['total']:,}件")
    print(f"修正実行: {results['fixed']:,}件")
    print(f"スキップ: {results['skipped']:,}件")

    if results["changes"]:
        print("\n【修正内容】")
        for i, change in enumerate(results["changes"], 1):
            print(f"\n{i}. {change['person_name']} (age={change['age']})")
            print(f"   誤: {change['wrong_name']}")
            print(f"   正: {change['correct_name']}")
            print(f"   Before: {change['before']}")
            print(f"   After:  {change['after']}")

    print("=" * 80)


def create_backup(df: pd.DataFrame) -> Path:
    """バックアップを作成"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = MASTER_CSV_PATH.parent / f"{MASTER_CSV_PATH.stem}.bak_namemismatch_{timestamp}.csv"

    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"💾 バックアップ作成: {backup_path}")
    return backup_path


def main():
    parser = argparse.ArgumentParser(
        description="リード文の人物名不一致修正スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # ドライラン（変更内容の確認のみ）
  python scripts/fix_person_name_mismatch.py

  # 本番実行
  python scripts/fix_person_name_mismatch.py --execute
        """,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に変更を適用（デフォルト: ドライラン）",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("📝 リード文の人物名不一致修正スクリプト")
    print("=" * 80)
    print(f"モード: {'実行' if args.execute else 'ドライラン（プレビュー）'}")
    print()

    # CSV読み込み
    if not MASTER_CSV_PATH.exists():
        print(f"❌ エラー: マスターCSVが見つかりません: {MASTER_CSV_PATH}")
        return

    df = pd.read_csv(MASTER_CSV_PATH, encoding="utf-8-sig")
    print(f"✅ マスターCSV読み込み完了: {len(df)}件")

    # バックアップ作成（実行モードの場合のみ）
    if args.execute:
        create_backup(df)

    # 処理実行
    print("\n🔄 処理中...")
    results = find_and_fix_mismatches(df, dry_run=not args.execute)

    # サマリー表示
    print_summary(results)

    # 実行モードの場合、CSVを保存
    if args.execute:
        print("\n💾 マスターCSVを更新中...")
        df.to_csv(MASTER_CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"✅ 更新完了: {MASTER_CSV_PATH}")

    # 最終メッセージ
    print("\n" + "=" * 80)
    if args.execute:
        print("✅ 処理完了: 変更を適用しました")
        print(f"   修正件数: {results['fixed']:,}件")
    else:
        print("💡 ドライランモード: 実際の変更は行われていません")
        print(f"   修正対象: {results['fixed']:,}件")
        print("\n   本番実行するには --execute オプションを追加してください：")
        print("   python scripts/fix_person_name_mismatch.py --execute")
    print("=" * 80)


if __name__ == "__main__":
    main()
