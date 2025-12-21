#!/usr/bin/env python3
"""
EPUP: 架空キャラクターエピソード作品名欠落修正スクリプト

架空キャラクター（person_type=FICTIONAL）でwork_titleが設定されている場合、
エピソード冒頭に『作品名』が含まれていなければ自動挿入して修正する。

正しいフォーマット:
  「あなたと同じ10歳のとき、ナミ『ONE PIECE』は...」

問題のあるフォーマット:
  「あなたと同じ10歳のとき、ナミは...」（作品名欠落）

使用方法:
    python scripts/fix_fictional_work_title_format.py           # 検出のみ
    python scripts/fix_fictional_work_title_format.py --fix     # 修正実行
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent

# データファイル
CSV_PATH = PROJECT_ROOT / "preserved" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def detect_missing_work_title(df: pd.DataFrame) -> list[dict]:
    """
    作品名が欠落している架空キャラエピソードを検出

    Args:
        df: エピソードDataFrame

    Returns:
        問題エピソードのリスト
    """
    issues = []

    for idx, row in df.iterrows():
        person_type = str(row.get("person_type", "")).upper()
        work_title = str(row.get("work_title", ""))
        episode_text = str(row.get("episode_text", ""))
        person_name = str(row.get("person_name", ""))

        # FICTIONALでwork_titleありのエピソードのみ対象
        if "FICTIONAL" not in person_type:
            continue

        if not work_title or work_title == "nan" or work_title == "":
            continue

        # リード文（冒頭100文字）に作品名があるか
        lead = episode_text[:100]
        expected = f"『{work_title}』"

        if expected not in lead:
            issues.append(
                {
                    "index": idx,
                    "episode_id": row.get("episode_id", ""),
                    "person_name": person_name,
                    "work_title": work_title,
                    "age": row.get("age", ""),
                    "current_lead": episode_text[:80],
                }
            )

    return issues


def fix_missing_work_title(episode_text: str, person_name: str, work_title: str) -> str:
    """
    作品名を挿入して修正

    Args:
        episode_text: 元のエピソードテキスト
        person_name: キャラクター名
        work_title: 作品名

    Returns:
        修正後のエピソードテキスト
    """
    # パターン1: 「あなたと同じN歳のとき、{person_name}は」（フルネーム）
    pattern1 = rf"(あなたと同じ\d+歳のとき、){re.escape(person_name)}(は|が)"
    replacement1 = rf"\1{person_name}『{work_title}』\2"
    fixed_text = re.sub(pattern1, replacement1, episode_text, count=1)

    # 置換されたか確認
    if fixed_text != episode_text:
        return fixed_text

    # パターン2: 「同じN歳のとき、{person_name}は」（代替形式）
    pattern2 = rf"(同じ\d+歳のとき、){re.escape(person_name)}(は|が)"
    fixed_text = re.sub(pattern2, replacement1, episode_text, count=1)
    if fixed_text != episode_text:
        return fixed_text

    # パターン3: 一人称「僕は」「私は」「オレは」を「{person_name}『{work_title}』は」に置換
    first_person_patterns = [
        (r"(あなたと同じ\d+歳のとき、)僕(は|が)", rf"\1{person_name}『{work_title}』\2"),
        (r"(あなたと同じ\d+歳のとき、)私(は|が)", rf"\1{person_name}『{work_title}』\2"),
        (r"(あなたと同じ\d+歳のとき、)オレ(は|が)", rf"\1{person_name}『{work_title}』\2"),
        (r"(あなたと同じ\d+歳のとき、)俺(は|が)", rf"\1{person_name}『{work_title}』\2"),
        (r"(あなたと同じ\d+歳のとき、)わたし(は|が)", rf"\1{person_name}『{work_title}』\2"),
        (r"(あなたと同じ\d+歳のとき、)ボク(は|が)", rf"\1{person_name}『{work_title}』\2"),
    ]

    for pattern, replacement in first_person_patterns:
        fixed_text = re.sub(pattern, replacement, episode_text, count=1)
        if fixed_text != episode_text:
            return fixed_text

    # パターン4: 略称パターン（person_nameの一部分で始まる）
    # 例: 「毛利蘭」→「蘭」、「竈門禰豆子」→「禰豆子」、「胡蝶しのぶ」→「しのぶ」
    # person_nameの最後の2-4文字を抽出して試行
    for name_len in [2, 3, 4]:
        if len(person_name) > name_len:
            short_name = person_name[-name_len:]
            pattern_short = rf"(あなたと同じ\d+歳のとき、){re.escape(short_name)}(は|が)"
            replacement_short = rf"\1{person_name}『{work_title}』\2"
            fixed_text = re.sub(pattern_short, replacement_short, episode_text, count=1)
            if fixed_text != episode_text:
                return fixed_text

    # パターン5: 名前の一部（姓を除いた名前部分）
    # 例: 「モンキー・D・ルフィ」→「ルフィ」
    if "・" in person_name:
        parts = person_name.split("・")
        last_part = parts[-1]
        pattern_last = rf"(あなたと同じ\d+歳のとき、){re.escape(last_part)}(は|が)"
        replacement_last = rf"\1{person_name}『{work_title}』\2"
        fixed_text = re.sub(pattern_last, replacement_last, episode_text, count=1)
        if fixed_text != episode_text:
            return fixed_text

    # パターン6: 括弧付き名前の括弧内名前で始まる場合
    # 例: 「セーラームーン（月野うさぎ）」→「月野うさぎ」
    paren_match = re.search(r"（([^）]+)）", person_name)
    if paren_match:
        inner_name = paren_match.group(1)
        pattern_inner = rf"(あなたと同じ\d+歳のとき、){re.escape(inner_name)}(は|が)"
        replacement_inner = rf"\1{person_name}『{work_title}』\2"
        fixed_text = re.sub(pattern_inner, replacement_inner, episode_text, count=1)
        if fixed_text != episode_text:
            return fixed_text
        # 括弧内名前の最後の2-4文字も試行
        for name_len in [2, 3, 4, 5]:
            if len(inner_name) >= name_len:
                short_inner = inner_name[-name_len:]
                pattern_short_inner = rf"(あなたと同じ\d+歳のとき、){re.escape(short_inner)}(は|が)"
                fixed_text = re.sub(pattern_short_inner, replacement_inner, episode_text, count=1)
                if fixed_text != episode_text:
                    return fixed_text

    # パターン7: 作品名と同じ名前の場合 「〇〇さん」→「〇〇」パターン
    # 例: 「サザエさん」→「サザエ」、「ルパン三世」→「ルパン」
    # 名前から「さん」「三世」等のサフィックスを除去して試行
    for suffix in ["さん", "三世", "くん", "ちゃん", "様"]:
        if person_name.endswith(suffix):
            base_name = person_name[: -len(suffix)]
            pattern_base = rf"(あなたと同じ\d+歳のとき、){re.escape(base_name)}(は|が)"
            replacement_base = rf"\1{person_name}『{work_title}』\2"
            fixed_text = re.sub(pattern_base, replacement_base, episode_text, count=1)
            if fixed_text != episode_text:
                return fixed_text

    # パターン8: 姓のみで始まる場合
    # 例: 「毛利蘭」→「蘭」
    if len(person_name) >= 2:
        # 最初の1-2文字（姓）以外の部分を試行
        for start_pos in [1, 2]:
            if len(person_name) > start_pos:
                name_part = person_name[start_pos:]
                pattern_name = rf"(あなたと同じ\d+歳のとき、){re.escape(name_part)}(は|が)"
                replacement_name = rf"\1{person_name}『{work_title}』\2"
                fixed_text = re.sub(pattern_name, replacement_name, episode_text, count=1)
                if fixed_text != episode_text:
                    return fixed_text

    return episode_text


def fix_episodes(df: pd.DataFrame, issues: list[dict], dry_run: bool = True) -> dict:
    """
    問題エピソードを修正

    Args:
        df: エピソードDataFrame
        issues: 問題エピソードのリスト
        dry_run: Trueの場合は実際に更新しない

    Returns:
        修正結果
    """
    results = {"success": [], "failed": [], "total": len(issues)}

    for issue in issues:
        idx = issue["index"]
        person_name = issue["person_name"]
        work_title = issue["work_title"]
        original_text = df.loc[idx, "episode_text"]

        # 修正実行
        fixed_text = fix_missing_work_title(original_text, person_name, work_title)

        # 修正が成功したか確認
        expected = f"『{work_title}』"
        if expected in fixed_text[:100]:
            results["success"].append(
                {
                    "episode_id": issue["episode_id"],
                    "person_name": person_name,
                    "work_title": work_title,
                    "before": original_text[:60],
                    "after": fixed_text[:60],
                }
            )

            if not dry_run:
                df.loc[idx, "episode_text"] = fixed_text
        else:
            results["failed"].append(
                {
                    "episode_id": issue["episode_id"],
                    "person_name": person_name,
                    "work_title": work_title,
                    "reason": "パターンマッチ失敗",
                }
            )

    return results


def main():
    parser = argparse.ArgumentParser(description="EPUP: 架空キャラクターエピソード作品名欠落修正")
    parser.add_argument("--fix", action="store_true", help="修正を実行")
    parser.add_argument("--csv", type=str, help="対象CSVファイル")
    args = parser.parse_args()

    print("=" * 70)
    print("📊 EPUP: 架空キャラクター作品名欠落修正")
    print("=" * 70)

    # CSVパス
    csv_path = Path(args.csv) if args.csv else CSV_PATH
    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1

    print(f"\n📂 対象ファイル: {csv_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"📋 読み込み完了: {len(df)}件")

    # 検出
    print("\n🔍 作品名欠落エピソードを検出中...")
    issues = detect_missing_work_title(df)

    if not issues:
        print("✅ 作品名欠落エピソードは見つかりませんでした")
        return 0

    print(f"\n⚠️ 作品名欠落検出: {len(issues)}件")
    print()

    # 詳細表示
    print("=== 検出されたエピソード ===")
    for i, issue in enumerate(issues, 1):
        print(f"[{i}] {issue['episode_id']}: {issue['person_name']}『{issue['work_title']}』({issue['age']}歳)")
        print(f"    現在: {issue['current_lead']}...")
        print()

    # 修正実行
    if args.fix:
        print("🔧 修正を実行中...")
        results = fix_episodes(df, issues, dry_run=False)

        if results["success"]:
            # バックアップ作成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = csv_path.with_suffix(f".bak_worktitle_{timestamp}.csv")
            df_original = pd.read_csv(csv_path, encoding="utf-8-sig")
            df_original.to_csv(backup_path, index=False, encoding="utf-8-sig")
            print(f"\n💾 バックアップ: {backup_path}")

            # 保存
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"💾 CSV更新完了: {csv_path}")
    else:
        print("🔧 ドライラン: 修正をシミュレート中...")
        results = fix_episodes(df, issues, dry_run=True)

    # 結果表示
    print("\n" + "=" * 70)
    print("📊 修正結果")
    print("=" * 70)
    print(f"成功: {len(results['success'])}件")
    print(f"失敗: {len(results['failed'])}件")

    if results["success"]:
        print("\n✅ 修正成功サンプル:")
        for item in results["success"][:5]:
            print(f"  {item['person_name']}『{item['work_title']}』")
            print(f"    Before: {item['before']}...")
            print(f"    After:  {item['after']}...")
            print()

    if results["failed"]:
        print("\n❌ 修正失敗:")
        for item in results["failed"]:
            print(f"  {item['person_name']}『{item['work_title']}』: {item['reason']}")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"work_title_fix_{timestamp}.json"

    report = {
        "timestamp": timestamp,
        "csv_file": str(csv_path),
        "total_issues": len(issues),
        "fixed": len(results["success"]),
        "failed": len(results["failed"]),
        "dry_run": not args.fix,
        "issues": issues,
        "results": results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート保存: {report_path}")

    if not args.fix and results["success"]:
        print("\n💡 実際に修正を適用するには --fix オプションを追加してください")

    print("\n" + "=" * 70)
    print("✅ 完了")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
