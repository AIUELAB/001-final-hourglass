#!/usr/bin/env python3
"""
文章品質修正スクリプト

ルールA: 終止形の誤り修正（例: 「にありた」→「にいた」）
ルールB: 末尾句点追加（末尾が「。」「！」「？」等でない場合）
ルールC: 導入文パターンの「は、」→「は」（改行 + 読点の崩れも含む）
ルールD: 「〜は」の直後重複を削除（例: 「ダコタ・ファニングはダコタ・ファニングは」）

安全設計:
- デフォルトは dry-run（変更しない）
- 実行時はバックアップを作成してから上書き

Usage:
  # まずは確認（dry-run）
  python scripts/fix/fix_text_quality.py

  # 実際に適用
  python scripts/fix/fix_text_quality.py --execute

  # 任意のCSVを対象にする
  python scripts/fix/fix_text_quality.py --csv path/to/file.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
from pathlib import Path
from datetime import datetime
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src" / "reports" / "logs"


def _subn(text: str, pattern: str | re.Pattern[str], repl: str) -> tuple[str, int]:
    """安全に置換し、(置換後, 置換回数) を返す"""
    return re.subn(pattern, repl, text)


def fix_text(text: str) -> tuple[str, list[str]]:
    """
    テキストを修正し、修正内容のリストを返す。

    注意:
    - 仕様に影響する“意味の変更”は避け、明確に誤りと判断できるものだけを自動修正する。
    """
    if not text:
        return text, []

    changes: list[str] = []
    updated = text

    # ----------------------------
    # ルールA: 終止形の誤り
    # ----------------------------
    # A1: 「にありた」→「にいた」
    updated, count = _subn(updated, r"にありた([。、]|$)", r"にいた\1")
    if count:
        changes.append("A1: にありた→にいた")

    # A2: 「繋がりた」→「繋がった」
    updated, count = _subn(updated, r"繋がりた([。、]|$)", r"繋がった\1")
    if count:
        changes.append("A2: 繋がりた→繋がった")

    # A3: 「になりた」→「になった」
    updated, count = _subn(updated, r"になりた([。、]|$)", r"になった\1")
    if count:
        changes.append("A3: になりた→になった")

    # A4: 「となりた」→「となった」
    updated, count = _subn(updated, r"となりた([。、]|$)", r"となった\1")
    if count:
        changes.append("A4: となりた→となった")

    # A5: 「○がりた」→「○がった」（上がりた、下がりた等）
    pattern_a5 = re.compile(r"(上|下|広|拡|高|深)がりた([。、]|$)")
    updated, count = _subn(updated, pattern_a5, r"\1がった\2")
    if count:
        changes.append("A5: ○がりた→○がった")

    # ----------------------------
    # ルールC: 導入文の「は、」の読点を削除
    # ----------------------------
    # 例:
    #   あなたと同じ36歳のとき
    #   テッド・バンディは
    #   、シアトルと...
    #
    # 「は、」だけでなく「は\n、」のような改行崩れも対象にする。
    pattern_c = re.compile(
        r"(あなたと同じ\d+歳のとき[、,]?[ \t]*\n?[ \t]*)"  # 導入部（改行含む）
        r"([^、。\n]{2,30})"  # 人名（簡易）
        r"(は)"  # は
        r"([ \t]*\n?[ \t]*)"  # 改行/空白（保持する）
        r"、"  # 削除対象の読点
    )
    updated, count = _subn(updated, pattern_c, r"\1\2\3\4")
    if count:
        changes.append("C: 導入文の「は、」→「は」(改行崩れ含む)")

    # ----------------------------
    # ルールD: 「〜は」の直後重複を削除
    # ----------------------------
    # 例:
    #   「ダコタ・ファニングはダコタ・ファニングは…」
    #   「森下仁丹は森下仁丹は森下仁丹の未来…」
    #
    # 方針:
    # - 直後に同じ「◯◯は」が繰り返された場合のみ対象（誤検知を減らす）
    # - 空白/改行の揺れは許容
    pattern_dup_ha = re.compile(r"([^\s、。]{2,60}は)([ \t]*\n?[ \t]*)(?:\1\2)+")
    updated, count = _subn(updated, pattern_dup_ha, r"\1\2")
    if count:
        changes.append("D: 「〜は」の重複削除")

    # ----------------------------
    # ルールB: 末尾句点の欠落
    # ----------------------------
    # なぜ: 最後の文だけ句点が無いと読みづらく、機械生成っぽさが強くなるため。
    stripped = updated.rstrip()
    if stripped:
        valid_endings = ("。", "！", "？", "」", "!", "?")
        if not stripped.endswith(valid_endings):
            updated = stripped + "。"
            changes.append("B: 末尾句点追加")

    return updated, changes


def create_backup(csv_path: Path) -> Path:
    """CSVバックアップを作成する（上書き前の保険）"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = csv_path.with_suffix(f".backup_{timestamp}.csv")
    shutil.copy2(csv_path, backup_path)
    return backup_path

def run(csv_path: Path, dry_run: bool, max_examples: int) -> int:
    """メイン処理（戻り値: 0=正常, 1=対象ファイルなし等）"""
    if not csv_path.exists():
        print(f"❌ CSVが見つかりません: {csv_path}")
        return 1

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"text_quality_fix_{timestamp}.log"

    rows: list[dict] = []
    affected_episode_ids: set[str] = set()
    details: list[dict] = []
    change_counter: Counter[str] = Counter()

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            print("❌ CSVヘッダーが取得できません（空ファイルの可能性）")
            return 1
        if "episode_text" not in fieldnames:
            print("❌ CSVに episode_text カラムがありません")
            return 1

        for row in reader:
            episode_id = str(row.get("episode_id", "") or "")
            text = str(row.get("episode_text", "") or "")

            fixed_text, changes = fix_text(text)
            if changes:
                affected_episode_ids.add(episode_id)
                for ch in changes:
                    change_counter[ch] += 1

                # 例は最大max_examples件だけ保存（ログ肥大化防止）
                if len(details) < max_examples:
                    details.append(
                        {
                            "episode_id": episode_id,
                            "changes": changes,
                            "before": text[:80],
                            "after": fixed_text[:80],
                        }
                    )

                if not dry_run:
                    row["episode_text"] = fixed_text
                    # 文字数カラムがある場合は追従（派生フィールドの整合性維持）
                    if "char_count" in fieldnames:
                        row["char_count"] = str(len(fixed_text))

            rows.append(row)

    backup_path: Path | None = None
    if not dry_run and affected_episode_ids:
        backup_path = create_backup(csv_path)
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # レポート出力
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("=== 文章品質修正レポート ===\n")
        f.write("=" * 60 + "\n")
        f.write(f"日時: {datetime.now().isoformat()}\n")
        f.write(f"対象CSV: {csv_path}\n")
        f.write(f"モード: {'DRY-RUN' if dry_run else 'EXECUTE'}\n")
        if backup_path:
            f.write(f"バックアップ: {backup_path}\n")
        f.write("\n")

        f.write("【サマリー】\n")
        f.write(f"  修正対象エピソード数: {len(affected_episode_ids)}\n")
        for k, v in change_counter.most_common():
            f.write(f"  - {k}: {v}件\n")
        f.write("\n")

        f.write("【サンプル（最大表示件数）】\n")
        for i, d in enumerate(details, start=1):
            f.write(f"  [{i}] {d['episode_id']}\n")
            f.write(f"    Changes: {', '.join(d['changes'])}\n")
            f.write(f"    Before: {d['before']}\n")
            f.write(f"    After:  {d['after']}\n\n")

    # コンソール出力（短く）
    print("=" * 60)
    print("文章品質修正（安全モード）")
    print("=" * 60)
    print(f"対象: {csv_path}")
    print(f"モード: {'DRY-RUN（変更なし）' if dry_run else 'EXECUTE（上書き）'}")
    print(f"修正対象エピソード数: {len(affected_episode_ids)}")
    print(f"レポート: {report_path}")
    if backup_path:
        print(f"バックアップ: {backup_path}")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="文章品質修正スクリプト（安全設計）")
    parser.add_argument("--execute", action="store_true", help="実際にCSVへ反映する（デフォルトはdry-run）")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="対象CSVファイル")
    parser.add_argument(
        "--max-examples",
        type=int,
        default=50,
        help="ログに出すサンプル件数（デフォルト: 50）",
    )
    args = parser.parse_args()

    raise SystemExit(run(csv_path=args.csv, dry_run=not args.execute, max_examples=args.max_examples))
