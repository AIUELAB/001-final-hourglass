#!/usr/bin/env python3
"""
リード文の人物名不一致修正スクリプト

CSVのperson_nameとエピソード本文のリード文の人物名が不一致のエピソードを修正する。

修正モード:
1. CORRECTION_MAPベース: リード文の誤った名前を正しい名前に置換
2. B1違反修正: テキストに人物名がない場合、冒頭に人物名を挿入

Usage:
    # ドライラン（変更内容の確認のみ）
    python scripts/fix/fix_person_name_mismatch.py

    # 本番実行
    python scripts/fix/fix_person_name_mismatch.py --execute

    # B1違反のみ修正
    python scripts/fix/fix_person_name_mismatch.py --b1-only --execute
"""

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

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

# B1違反対象のエピソードID（テキストに人物名がないケース）
# detect_all_inconsistencies.py で検出された B1_name_not_in_text 違反
B1_VIOLATION_IDS = [
    "EP-260117001544165",
    "EP-260118072321768",
    "EP-260118100239523",
    "EP-260118072308914",
    "EP-260118094839912",
    "EP-260118100230689",
    "EP-260116232909031",
    "EP-260116232909042",
    "EP-260116232908180",
    "EP-260118093404973",
    "EP-260118072310704",
    "EP-260118072316068",
    "EP-260118093044514",
    "EP-260118072301203",
    "EP-260118072300081",
    "EP-260118072303552",
    "EP-260118072300027",
    "EP-260118072741676",
    "EP-260118072327770",
    "EP-260118072315883",
    "EP-260118072306106",
    "EP-260116232910139",
    "EP-260116235011744",
    "EP-260118072310762",
    "EP-260118072327236",
    "EP-260118093227099",
    "EP-260118100711636",
    "EP-260118072300235",
    "EP-260118071717400",
    "EP-260118093413661",
    "EP-260118072318654",
    "EP-260118072326517",
    "EP-260118072804966",
    "EP-260118072157622",
    "EP-260116231610527",
    "EP-260117002321212",
    "EP-260118072305799",
    "EP-260116235010954",
    "EP-260116232909867",
    "EP-260116235458266",
    "EP-260116232910828",
    "EP-260116213255305",
    "EP-260118071228944",
    "EP-260118072312485",
    "EP-260117000725169",
    "EP-260116231608178",
    "EP-260118071155334",
    "EP-260118072302187",
    "EP-260118101139094",
    "EP-260118092918181",
    "EP-260118073222629",
    "EP-260118070802591",
    "EP-260118070802821",
    "EP-260118070802604",
    "EP-260118070803338",
    "EP-260118100711641",
    "EP-260118072320006",
    "EP-260118072311003",
    "EP-260116232908679",
    "EP-260118072304059",
    "EP-260116235829050",
    "EP-260116235458385",
    "EP-260118072305111",
    "EP-260116235828473",
    "EP-260117000724677",
    "EP-260116235011767",
    "EP-260116231610922",
    "EP-260118101140618",
    "EP-260118072309658",
    "EP-260118072304290",
    "EP-260118072312568",
    "EP-260118071228714",
    "EP-260118070838674",
    "EP-260118072328559",
    "EP-260118072323742",
    "EP-260118072327060",
    "EP-260118073222985",
    "EP-260118072321170",
    "EP-260118095859000",
    "EP-260118071728906",
    "EP-260118072322564",
    "EP-260117001544494",
    "EP-260118072320178",
    "EP-260118093409462",
    "EP-260118093118050",
    "EP-260118072328194",
    "EP-260118093118863",
    "EP-2601161401370238",
    "EP-2601161353220244",
    "EP-2601161353220242",
    "EP-2601161353220423",
    "EP-2601161401370404",
    "EP-2601161401370427",
    "EP-260112014047311238",
    "EP-260112014047311141",
    "EP-260112014047311880",
    "EP-260112014047311406",
]


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
            print(f"⚠️ 警告（行{idx}）: CSV={person_name}, 修正マップ={correct_name} - 不一致")
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


def fix_b1_violations(df: pd.DataFrame, dry_run: bool = True) -> Dict[str, Any]:
    """
    B1違反（テキストに人物名がない）を修正

    修正方法:
    - 三人称エピソード: 「あなたと同じXX歳のとき、」の後に「{person_name}は」を挿入
    - 一人称エピソード（僕は/私は等）: 削除（品質問題のため）

    Args:
        df: エピソードデータフレーム
        dry_run: ドライランモード

    Returns:
        処理結果の詳細
    """
    # 一人称パターン（これで始まるエピソードは削除対象）
    first_person_patterns = ["僕は", "僕が", "私は", "私が", "俺は", "俺が"]

    results = {
        "timestamp": datetime.now().isoformat(),
        "total": len(B1_VIOLATION_IDS),
        "fixed": 0,
        "deleted": 0,
        "skipped": 0,
        "not_found": 0,
        "changes": [],
        "deletions": [],
    }

    # エピソードIDでインデックス作成
    df_indexed = df.set_index("episode_id", drop=False)

    for ep_id in B1_VIOLATION_IDS:
        if ep_id not in df_indexed.index:
            results["not_found"] += 1
            continue

        row = df_indexed.loc[ep_id]
        person_name = str(row.get("person_name", ""))
        episode_text = str(row.get("episode_text", ""))
        age = str(row.get("age", ""))

        # すでに人物名が含まれている場合はスキップ
        if person_name in episode_text:
            results["skipped"] += 1
            continue

        # テキストパターン: 「あなたと同じXX歳のとき、」で始まる
        pattern = re.compile(r"^(あなたと同じ\d+歳のとき、)")
        match = pattern.match(episode_text)

        if not match:
            print(f"⚠️ パターン不一致（{ep_id}）: {episode_text[:50]}...")
            results["skipped"] += 1
            continue

        prefix = match.group(1)
        rest = episode_text[match.end() :]

        # 一人称エピソードかチェック
        is_first_person = any(rest.startswith(fp) or f"、{fp}" in rest[:30] for fp in first_person_patterns)

        if is_first_person:
            # 一人称エピソードは削除
            results["deletions"].append(
                {
                    "episode_id": ep_id,
                    "person_name": person_name,
                    "age": age,
                    "reason": "一人称で記述されており、修正困難",
                    "text_preview": episode_text[:100] + "..." if len(episode_text) > 100 else episode_text,
                }
            )
            results["deleted"] += 1

            # 実行モードの場合、DataFrameから削除
            if not dry_run:
                original_idx = df[df["episode_id"] == ep_id].index[0]
                df.drop(original_idx, inplace=True)
        else:
            # 三人称エピソードは修正
            new_text = f"{prefix}{person_name}は{rest}"

            change_record = {
                "episode_id": ep_id,
                "person_name": person_name,
                "age": age,
                "before": episode_text[:100] + "..." if len(episode_text) > 100 else episode_text,
                "after": new_text[:100] + "..." if len(new_text) > 100 else new_text,
            }
            results["changes"].append(change_record)
            results["fixed"] += 1

            # 実行モードの場合、DataFrameを更新
            if not dry_run:
                original_idx = df[df["episode_id"] == ep_id].index[0]
                df.at[original_idx, "episode_text"] = new_text

    return results


def print_b1_summary(results: Dict[str, Any]):
    """B1修正結果のサマリーを表示"""
    print("\n" + "=" * 80)
    print("📊 B1違反修正 処理結果サマリー")
    print("=" * 80)
    print(f"対象エピソード数: {results['total']:,}件")
    print(f"テキスト修正: {results['fixed']:,}件")
    print(f"削除（一人称）: {results['deleted']:,}件")
    print(f"スキップ（既に修正済み）: {results['skipped']:,}件")
    print(f"未検出: {results['not_found']:,}件")

    if results["changes"]:
        print("\n【テキスト修正内容（先頭10件）】")
        for i, change in enumerate(results["changes"][:10], 1):
            print(f"\n{i}. {change['person_name']} (EP: {change['episode_id']})")
            print(f"   Before: {change['before']}")
            print(f"   After:  {change['after']}")
        if len(results["changes"]) > 10:
            print(f"\n... 他 {len(results['changes']) - 10}件")

    if results["deletions"]:
        print("\n【削除対象（一人称エピソード）】")
        for i, deletion in enumerate(results["deletions"], 1):
            print(f"\n{i}. {deletion['person_name']} (EP: {deletion['episode_id']})")
            print(f"   理由: {deletion['reason']}")
            print(f"   テキスト: {deletion['text_preview']}")

    print("=" * 80)


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
  python scripts/fix/fix_person_name_mismatch.py

  # 本番実行
  python scripts/fix/fix_person_name_mismatch.py --execute

  # B1違反のみ修正
  python scripts/fix/fix_person_name_mismatch.py --b1-only --execute
        """,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に変更を適用（デフォルト: ドライラン）",
    )
    parser.add_argument(
        "--b1-only",
        action="store_true",
        help="B1違反（テキストに人物名がない）のみ修正",
    )

    args = parser.parse_args()

    print("=" * 80)
    if args.b1_only:
        print("📝 B1違反（テキストに人物名がない）修正スクリプト")
    else:
        print("📝 リード文の人物名不一致修正スクリプト")
    print("=" * 80)
    print(f"モード: {'実行' if args.execute else 'ドライラン（プレビュー）'}")
    print()

    # CSV読み込み
    if not MASTER_CSV_PATH.exists():
        print(f"❌ エラー: マスターCSVが見つかりません: {MASTER_CSV_PATH}")
        return

    df = pd.read_csv(MASTER_CSV_PATH, encoding="utf-8-sig", low_memory=False)
    print(f"✅ マスターCSV読み込み完了: {len(df)}件")

    # バックアップ作成（実行モードの場合のみ）
    if args.execute:
        create_backup(df)

    # 処理実行
    print("\n🔄 処理中...")

    if args.b1_only:
        # B1違反のみ修正
        results = fix_b1_violations(df, dry_run=not args.execute)
        print_b1_summary(results)
    else:
        # CORRECTION_MAPベースの修正
        results = find_and_fix_mismatches(df, dry_run=not args.execute)
        print_summary(results)

    # 実行モードの場合、CSVを保存
    total_changes = results["fixed"] + results.get("deleted", 0)
    if args.execute and total_changes > 0:
        print("\n💾 マスターCSVを更新中...")
        df.to_csv(MASTER_CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"✅ 更新完了: {MASTER_CSV_PATH}")

    # 最終メッセージ
    print("\n" + "=" * 80)
    if args.execute:
        print("✅ 処理完了: 変更を適用しました")
        if args.b1_only:
            print(f"   テキスト修正: {results['fixed']:,}件")
            print(f"   削除: {results.get('deleted', 0):,}件")
        else:
            print(f"   修正件数: {results['fixed']:,}件")
    else:
        print("💡 ドライランモード: 実際の変更は行われていません")
        if args.b1_only:
            print(f"   テキスト修正対象: {results['fixed']:,}件")
            print(f"   削除対象: {results.get('deleted', 0):,}件")
            print("\n   本番実行するには --execute オプションを追加してください：")
            print("   python scripts/fix/fix_person_name_mismatch.py --b1-only --execute")
        else:
            print(f"   修正対象: {results['fixed']:,}件")
            print("\n   本番実行するには --execute オプションを追加してください：")
            print("   python scripts/fix/fix_person_name_mismatch.py --execute")
    print("=" * 80)


if __name__ == "__main__":
    main()
