#!/usr/bin/env python3
"""
定型違反自動修正スクリプト

「あなたと同じ{age}歳のとき、{person_name}は」で始まらないエピソードを自動修正。

修正対象:
- Markdownヘッダーで始まるもの: **名前 年齢時の記録**
- 年号で始まるもの: 1492年10月12日、...
- 引用符で始まるもの: 「あなたと同じ...

修正不可（要手動対応）:
- 一人称「私は」を含むもの（内容の書き換えが必要）
"""

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"


def create_backup(csv_path: Path, operation: str) -> Path:
    """バックアップを作成"""
    import shutil

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"MASTER_EPISODES_{operation}_{timestamp}.csv"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(csv_path, backup_path)
    return backup_path


@dataclass
class FixResult:
    """修正結果"""

    episode_id: str
    person_name: str
    original_text: str
    fixed_text: str
    fix_type: str


def fix_format_violations(
    csv_path: Path = MASTER_CSV,
    dry_run: bool = True,
    verbose: bool = False,
    target_ids: list[str] = None,
) -> dict:
    """
    定型違反を自動修正

    Args:
        csv_path: CSVファイルパス
        dry_run: Trueの場合、変更を保存しない
        verbose: 詳細ログを出力
        target_ids: 特定のエピソードIDのみ対象にする場合

    Returns:
        修正結果のサマリー
    """
    print("=" * 60)
    print("定型違反自動修正")
    print("=" * 60)
    print(f"対象: {csv_path}")
    print(f"モード: {'dry-run' if dry_run else '実行'}")
    print()

    # バックアップ作成
    if not dry_run:
        backup_path = create_backup(csv_path, "format_fix")
        print(f"バックアップ: {backup_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    print(f"総エピソード数: {len(df)}")

    # 対象を絞り込み
    if target_ids:
        df_target = df[df["episode_id"].isin(target_ids)].copy()
        print(f"対象エピソード: {len(df_target)}")
    else:
        df_target = df.copy()

    results = {
        "total": len(df_target),
        "valid": 0,
        "fixed": 0,
        "unfixable": 0,
        "fixes": [],
        "unfixable_list": [],
    }

    # 定型パターン（は/の両方を許可）
    valid_pattern = re.compile(r"^あなたと同じ\d+歳のとき、[^、]+(は|の)")

    for idx, row in df_target.iterrows():
        episode_id = row.get("episode_id", "")
        person_name = str(row.get("person_name", "") or "")
        age = row.get("age")
        text = str(row.get("episode_text", "") or "")

        # 既に定型パターンにマッチする場合はスキップ
        if valid_pattern.match(text):
            results["valid"] += 1
            continue

        # 修正を試みる
        fixed_text, fix_type = _try_fix(text, person_name, age)

        if fixed_text:
            results["fixed"] += 1
            results["fixes"].append(
                FixResult(
                    episode_id=episode_id,
                    person_name=person_name,
                    original_text=text[:100],
                    fixed_text=fixed_text[:100],
                    fix_type=fix_type,
                )
            )

            # DataFrameを更新
            df.loc[df["episode_id"] == episode_id, "episode_text"] = fixed_text

            if verbose:
                print(f"✓ {episode_id}: {fix_type}")
                print(f"  Before: {text[:60]}...")
                print(f"  After:  {fixed_text[:60]}...")
        else:
            results["unfixable"] += 1
            results["unfixable_list"].append(
                {
                    "episode_id": episode_id,
                    "person_name": person_name,
                    "text_preview": text[:100],
                }
            )

            if verbose:
                print(f"✗ {episode_id}: 自動修正不可")
                print(f"  Text: {text[:60]}...")

    # サマリー出力
    print()
    print("=" * 60)
    print("修正サマリー")
    print("=" * 60)
    print(f"検証済み: {results['valid']}")
    print(f"修正成功: {results['fixed']}")
    print(f"修正不可: {results['unfixable']}")

    if results["fixes"]:
        print()
        print("修正内容:")
        for fix in results["fixes"][:10]:  # 最大10件表示
            print(f"  {fix.episode_id}: {fix.fix_type}")

    if results["unfixable_list"]:
        print()
        print("修正不可リスト（手動対応が必要）:")
        for item in results["unfixable_list"][:10]:
            print(f"  {item['episode_id']}: {item['person_name']}")
            print(f"    {item['text_preview'][:50]}...")

    # 保存
    if not dry_run and results["fixed"] > 0:
        print()
        print("保存中...")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print("保存完了")

    return results


def _try_fix(text: str, person_name: str, age) -> tuple[str | None, str]:
    """
    テキストの修正を試みる

    Returns:
        (修正後テキスト or None, 修正タイプ)
    """
    if not person_name or pd.isna(age):
        return None, "missing_metadata"

    age_int = int(age)

    # 一人称「私は」を含む場合は修正不可
    if "私は" in text and "あなたと同じ" in text:
        return None, "contains_watashi"

    # 1. Markdownヘッダーで始まる場合
    # **名前 年齢時の記録**\n内容...
    if text.startswith("**"):
        match = re.match(r"^\*\*[^*]+\*\*\s*\n?(.+)", text, re.DOTALL)
        if match:
            content = match.group(1).strip()

            # 内容が日付パターンで始まる場合、その形式で処理
            date_match = re.match(
                r"^(\d{4}年\d{1,2}月\d{1,2}日)、?" + re.escape(person_name) + r"は(\d+歳で)?(.+)",
                content,
                re.DOTALL,
            )
            if date_match:
                date_part = date_match.group(1)
                rest = date_match.group(3).strip()
                fixed = f"あなたと同じ{age_int}歳のとき、{person_name}は{date_part}に{rest}"
                return fixed, "markdown_header_date"

            # 内容から人物名で始まる部分を探して除去
            content = re.sub(rf"^{re.escape(person_name)}は", "", content).strip()
            fixed = f"あなたと同じ{age_int}歳のとき、{person_name}は{content}"
            return fixed, "markdown_header"

    # 2. 引用符で始まる場合
    # 「あなたと同じ...私は...
    if text.startswith("「") or text.startswith("『"):
        # 引用符を除去して再構成
        content = re.sub(r"^[「『]", "", text).strip()
        # 「あなたと同じN歳のとき、」の部分を抽出
        match = re.match(r"あなたと同じ\d+歳のとき、.*?私は(.+)", content, re.DOTALL)
        if match:
            # 「私は」を人物名に置換
            inner_content = match.group(1).strip()
            fixed = f"あなたと同じ{age_int}歳のとき、{person_name}は{inner_content}"
            return fixed, "quote_and_watashi"

        # 引用符だけの問題
        if content.startswith("あなたと同じ"):
            return content, "quote_only"

    # 3. 年号で始まる場合
    # 1492年10月12日、41歳の名前は...
    year_match = re.match(r"^(\d{4}年\d{1,2}月\d{1,2}日)、?(\d+)歳の([^、]+)は(.+)", text, re.DOTALL)
    if year_match:
        date_part = year_match.group(1)
        # 人物名部分は除去（新しい定型で置き換える）
        rest = year_match.group(4).strip()
        fixed = f"あなたと同じ{age_int}歳のとき、{person_name}は{date_part}に{rest}"
        return fixed, "year_start"

    # 4. 年のみで始まる場合
    # 1904年、23歳のパブロ・ピカソは...
    year_only_match = re.match(r"^(\d{4}年)、?(\d+)歳の([^、]+)は(.+)", text, re.DOTALL)
    if year_only_match:
        year_part = year_only_match.group(1)
        # 人物名部分は除去（新しい定型で置き換える）
        rest = year_only_match.group(4).strip()
        fixed = f"あなたと同じ{age_int}歳のとき、{person_name}は{year_part}に{rest}"
        return fixed, "year_only_start"

    # 5. その他のパターン（年月日で始まるがパターン3にマッチしない場合）
    simple_date_match = re.match(r"^(\d{4}年\d{1,2}月\d{1,2}日)、?(.+)", text, re.DOTALL)
    if simple_date_match:
        date_part = simple_date_match.group(1)
        rest = simple_date_match.group(2).strip()
        # 人物名で始まる部分を除去
        rest = re.sub(rf"^{re.escape(person_name)}は", "", rest).strip()
        fixed = f"あなたと同じ{age_int}歳のとき、{person_name}は{date_part}に{rest}"
        return fixed, "date_start"

    # 6. その他のパターン
    # 単純に先頭に定型を追加（人物名重複を避ける）
    if text and not text.startswith("あなたと同じ"):
        # 人物名で始まる場合は除去
        content = re.sub(rf"^{re.escape(person_name)}は", "", text).strip()
        fixed = f"あなたと同じ{age_int}歳のとき、{person_name}は{content}"
        return fixed, "prepend_format"

    return None, "unknown"


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="定型違反自動修正")
    parser.add_argument("--dry-run", action="store_true", help="dry-runモード")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ")
    parser.add_argument(
        "--csv",
        default=str(MASTER_CSV),
        help="対象CSVファイル",
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        help="対象エピソードID（スペース区切り）",
    )
    args = parser.parse_args()

    fix_format_violations(
        csv_path=Path(args.csv),
        dry_run=args.dry_run,
        verbose=args.verbose,
        target_ids=args.ids,
    )


if __name__ == "__main__":
    main()
