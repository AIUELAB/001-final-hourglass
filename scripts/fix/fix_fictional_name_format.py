#!/usr/bin/env python3
"""
架空キャラクター名フォーマット修正スクリプト

FICTIONALエピソードに対して以下の修正を行う:
1. person_name正規化（FICTIONAL_NAME_ALIASESを使用）
2. work_title自動補完（空の場合、get_work_for_characterで取得）
3. episode_text冒頭フォーマット修正
   - 冒頭を「あなたと同じ{age}歳のとき、{person_name}『{work_title}』は」に統一
   - episode_text内の重複work_title（冒頭以外の『{work_title}』）を削除

Usage:
    # dry-run（変更をプレビューのみ）
    python scripts/fix/fix_fictional_name_format.py --dry-run

    # 実行（修正を適用）
    python scripts/fix/fix_fictional_name_format.py --execute

    # CSVパス指定
    python scripts/fix/fix_fictional_name_format.py --csv path/to/file.csv --execute

Author: EPUP Fix Team
Date: 2026-01-28
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.fictional_characters import (
    get_work_for_character,
    normalize_fictional_name,
)

# デフォルトパス
DEFAULT_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"


# =============================================================================
# 修正ロジック
# =============================================================================


def normalize_person_name(person_name: str) -> tuple[str, bool]:
    """
    person_nameを正規形式に変換

    Args:
        person_name: 元の人物名

    Returns:
        (正規化された名前, 変換が行われたかどうか)
    """
    if not person_name or pd.isna(person_name):
        return person_name, False

    return normalize_fictional_name(person_name)


def fill_work_title(person_name: str, work_title: str) -> tuple[str, bool]:
    """
    work_titleが空の場合、キャラクター名から作品名を取得

    Args:
        person_name: 人物名
        work_title: 現在のwork_title

    Returns:
        (work_title, 補完されたかどうか)
    """
    if work_title and not pd.isna(work_title) and str(work_title).strip():
        return str(work_title).strip(), False

    # キャラクター名から作品名を取得
    found_work = get_work_for_character(person_name)
    if found_work:
        return found_work, True

    return "", False


def fix_episode_text_lead(episode_text: str, person_name: str, work_title: str, age: int) -> tuple[str, str]:
    """
    episode_textの冒頭を正規フォーマットに修正

    正規フォーマット: 「あなたと同じ{age}歳のとき、{person_name}『{work_title}』は」

    Args:
        episode_text: 元のエピソードテキスト
        person_name: 正規化された人物名
        work_title: 作品タイトル
        age: 年齢

    Returns:
        (修正後テキスト, 修正内容の説明)
    """
    if not episode_text or pd.isna(episode_text):
        return episode_text, "テキストなし"

    text = str(episode_text)

    # 期待する冒頭
    expected_prefix = f"あなたと同じ{age}歳のとき、{person_name}『{work_title}』は"

    # 既に正しい形式かチェック
    if text.startswith(expected_prefix):
        return text, "既に正規形式"

    # パターン1: 「あなたと同じ{age}歳のとき、{人物名}『{作品名}』は」（名前・作品が異なる場合）
    pattern1 = r"^あなたと同じ\d+歳のとき、[^『]+『[^』]+』は"
    match1 = re.match(pattern1, text)
    if match1:
        # 冒頭部分を置換
        new_text = expected_prefix + text[match1.end() :]
        return new_text, "冒頭置換（名前/作品修正）"

    # パターン2: 「あなたと同じ{age}歳のとき、{人物名}は」（『作品名』なし）
    pattern2 = r"^あなたと同じ(\d+)歳のとき、([^は『]+)は"
    match2 = re.match(pattern2, text)
    if match2:
        # 『作品名』を挿入
        new_text = expected_prefix + text[match2.end() :]
        return new_text, "作品名挿入"

    # パターン3: その他の冒頭形式
    # 冒頭が「あなたと同じ」で始まるが予期しない形式
    if text.startswith("あなたと同じ"):
        # 最初の「は」までを置換
        first_ha = text.find("は")
        if first_ha > 0:
            new_text = expected_prefix + text[first_ha + 1 :]
            return new_text, "冒頭再構築"

    return text, "修正不可（パターン不一致）"


def remove_duplicate_work_title(episode_text: str, work_title: str) -> tuple[str, int]:
    """
    episode_text内の重複work_title（冒頭以外）を削除

    冒頭の『{work_title}』は残し、それ以降の『{work_title}』を削除する。
    他の書名（『忍者辞典』等）は残す。

    Args:
        episode_text: エピソードテキスト
        work_title: 削除対象の作品タイトル

    Returns:
        (修正後テキスト, 削除した回数)
    """
    if not episode_text or not work_title or pd.isna(work_title):
        return episode_text, 0

    text = str(episode_text)
    target = f"『{work_title}』"

    # 最初の出現位置を見つける
    first_pos = text.find(target)
    if first_pos == -1:
        return text, 0

    # 最初の出現以降のテキストから、同じ『{work_title}』を削除
    before_first = text[: first_pos + len(target)]
    after_first = text[first_pos + len(target) :]

    # 後続部分から『{work_title}』を削除
    removed_count = after_first.count(target)
    after_first_cleaned = after_first.replace(target, "")

    return before_first + after_first_cleaned, removed_count


# =============================================================================
# メイン処理
# =============================================================================


def create_backup(csv_path: Path) -> Path:
    """バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_pre_fictional_name_format_{timestamp}.csv"
    shutil.copy2(csv_path, backup_path)
    return backup_path


def analyze_and_fix(df: pd.DataFrame, dry_run: bool = True) -> tuple[pd.DataFrame, list[dict]]:
    """
    FICTIONALエピソードを分析し、修正を適用

    Args:
        df: データフレーム
        dry_run: Trueの場合、変更をプレビューのみ

    Returns:
        (修正後のデータフレーム, 変更リスト)
    """
    changes = []

    # FICTIONALエピソードのみ対象
    fictional_mask = df["person_type"].str.contains("FICTIONAL", case=False, na=False)
    fictional_indices = df[fictional_mask].index

    print(f"\n対象: FICTIONALエピソード {len(fictional_indices):,}件")

    for idx in fictional_indices:
        row = df.loc[idx]
        episode_id = row.get("episode_id", "N/A")
        original_name = str(row.get("person_name", ""))
        original_work_title = row.get("work_title", "")
        original_text = str(row.get("episode_text", ""))
        age = int(row.get("age", 0)) if pd.notna(row.get("age")) else 0

        changes_list: list[str] = []
        change_record: dict[str, Any] = {
            "idx": idx,
            "episode_id": episode_id,
            "original_name": original_name,
            "original_work_title": original_work_title,
            "original_text_preview": original_text[:80] if original_text else "",
            "changes": changes_list,
        }

        # 1. person_name正規化
        normalized_name, name_changed = normalize_person_name(original_name)
        if name_changed:
            changes_list.append(f"name: {original_name} -> {normalized_name}")
            if not dry_run:
                df.at[idx, "person_name"] = normalized_name
        else:
            normalized_name = original_name

        # 2. work_title補完
        filled_work_title, work_title_changed = fill_work_title(
            normalized_name,
            str(original_work_title) if pd.notna(original_work_title) else "",
        )
        if work_title_changed:
            changes_list.append(f"work_title: (empty) -> {filled_work_title}")
            if not dry_run:
                df.at[idx, "work_title"] = filled_work_title
        else:
            filled_work_title = str(original_work_title).strip() if pd.notna(original_work_title) else ""

        # work_titleがない場合、episode_text修正はスキップ
        if not filled_work_title:
            if name_changed or work_title_changed:
                changes.append(change_record)
            continue

        # 3. episode_text冒頭修正
        fixed_text, lead_fix_status = fix_episode_text_lead(original_text, normalized_name, filled_work_title, age)
        if lead_fix_status not in ("既に正規形式", "テキストなし", "修正不可（パターン不一致）"):
            changes_list.append(f"lead: {lead_fix_status}")
            if not dry_run:
                df.at[idx, "episode_text"] = fixed_text
        else:
            fixed_text = original_text

        # 4. 重複work_title削除
        final_text, removed_count = remove_duplicate_work_title(fixed_text, filled_work_title)
        if removed_count > 0:
            changes_list.append(f"duplicate_work_title: {removed_count}件削除")
            if not dry_run:
                df.at[idx, "episode_text"] = final_text

        # 変更があった場合のみ記録
        if change_record["changes"]:
            change_record["new_name"] = normalized_name
            change_record["new_work_title"] = filled_work_title
            change_record["new_text_preview"] = final_text[:80] if final_text else ""
            changes.append(change_record)

    return df, changes


def print_summary(changes: list[dict]) -> None:
    """変更サマリーを表示"""
    if not changes:
        print("\n変更対象なし")
        return

    # 変更タイプ別にカウント
    name_changes = sum(1 for c in changes if any("name:" in ch for ch in c["changes"]))
    work_title_changes = sum(1 for c in changes if any("work_title:" in ch for ch in c["changes"]))
    lead_changes = sum(1 for c in changes if any("lead:" in ch for ch in c["changes"]))
    duplicate_changes = sum(1 for c in changes if any("duplicate_work_title:" in ch for ch in c["changes"]))

    print("\n" + "=" * 60)
    print("変更サマリー")
    print("=" * 60)
    print(f"総変更対象: {len(changes):,}件")
    print(f"  - person_name正規化: {name_changes:,}件")
    print(f"  - work_title補完: {work_title_changes:,}件")
    print(f"  - 冒頭フォーマット修正: {lead_changes:,}件")
    print(f"  - 重複work_title削除: {duplicate_changes:,}件")


def print_samples(changes: list[dict], max_samples: int = 10) -> None:
    """変更サンプルを表示"""
    if not changes:
        return

    print("\n" + "-" * 60)
    print(f"変更サンプル（最大{max_samples}件）")
    print("-" * 60)

    for c in changes[:max_samples]:
        print(f"\n[{c['episode_id']}] {c['original_name']}")
        for ch in c["changes"]:
            print(f"  - {ch}")
        if "new_text_preview" in c:
            print(f"  新テキスト冒頭: {c['new_text_preview']}...")


def main():
    parser = argparse.ArgumentParser(description="架空キャラクター名フォーマット修正スクリプト")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="変更をプレビューのみ（デフォルト）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に修正を適用",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_CSV),
        help=f"CSVパス指定（デフォルト: {DEFAULT_CSV}）",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="バックアップを作成（--execute時は自動で有効）",
    )

    args = parser.parse_args()

    # --execute指定時はdry_runを無効化
    dry_run = not args.execute

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"エラー: CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print("=" * 60)
    print("架空キャラクター名フォーマット修正")
    print("=" * 60)
    print(f"モード: {'dry-run（プレビュー）' if dry_run else '実行'}")
    print(f"CSV: {csv_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    print(f"総エピソード数: {len(df):,}件")

    # 分析・修正
    df_modified, changes = analyze_and_fix(df, dry_run=dry_run)

    # サマリー表示
    print_summary(changes)

    if dry_run:
        # サンプル表示
        print_samples(changes)
        print("\n" + "=" * 60)
        print("実行するには --execute フラグを付けてください")
        print("=" * 60)
        sys.exit(0)

    if not changes:
        print("\n変更対象がないため、終了します")
        sys.exit(0)

    # バックアップ作成（--execute時は自動）
    if args.execute or args.backup:
        backup_path = create_backup(csv_path)
        print(f"\nバックアップ作成: {backup_path}")

    # CSV保存
    df_modified.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\nCSV更新完了: {csv_path}")
    print(f"変更件数: {len(changes):,}件")

    # 検証
    print("\n検証中...")
    df_verify = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    fictional_verify = df_verify[df_verify["person_type"].str.contains("FICTIONAL", case=False, na=False)]

    # 冒頭フォーマット違反チェック
    lead_pattern = re.compile(r"^あなたと同じ\d+歳のとき、[^『]+『[^』]+』は")
    violations = fictional_verify[~fictional_verify["episode_text"].str.match(lead_pattern, na=False)]

    print(f"残存冒頭違反: {len(violations):,}件")

    if len(violations) == 0:
        print("\n全FICTIONALエピソードが正規フォーマットに準拠しています")
    else:
        print("\n一部違反が残っています（work_title欠損等）")
        print("サンプル:")
        for _, row in violations.head(3).iterrows():
            print(f"  [{row['episode_id']}] {row['person_name']}: {str(row['episode_text'])[:60]}...")


if __name__ == "__main__":
    main()
