#!/usr/bin/env python3
"""
エピソード本文の人物名不整合修正スクリプト（全文置換版）

目的: person_name と episode_text 内の人物名の不整合を全文で修正

Usage:
    # ドライラン（変更内容の確認のみ）
    python scripts/fix/fix_name_mismatch_full.py

    # 本番実行
    python scripts/fix/fix_name_mismatch_full.py --execute
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# マスターCSVパス
MASTER_CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "src/reports/logs"


def extract_name_from_lead(episode_text: str) -> tuple[str | None, int | None]:
    """
    リード文から人物名と年齢を抽出

    Returns:
        (人物名, 年齢) または (None, None)
    """
    # パターン: あなたと同じ{年齢}歳のとき、{人物名}は
    # 架空キャラの作品名付きパターンも考慮: {人物名}『{作品名}』は
    pattern = r"^あなたと同じ([\d.]+)歳のとき、(.+?)(?:『.+?』)?は"
    match = re.match(pattern, episode_text)
    if match:
        age = int(float(match.group(1)))
        name = match.group(2)
        return name, age
    return None, None


def replace_name_in_text(episode_text: str, old_name: str, new_name: str, age: int | None = None) -> tuple[str, int]:
    """
    本文全体で人物名を置換

    Args:
        episode_text: エピソードテキスト
        old_name: 置換前の名前
        new_name: 置換後の名前
        age: 年齢（リード文の再構築用）

    Returns:
        (置換後テキスト, 置換回数)
    """
    if old_name == new_name:
        return episode_text, 0

    # エスケープして正規表現パターンを作成
    pattern = re.escape(old_name)

    # 置換実行
    new_text, count = re.subn(pattern, new_name, episode_text)

    return new_text, count


def classify_mismatch(person_name: str, text_name: str) -> str:
    """不整合のタイプを分類"""
    if text_name.isascii():
        return "英語名混入"
    if re.search(r"[A-Za-z]", text_name):
        return "英語混在"
    if "(" in text_name or "（" in text_name:
        return "括弧表記"
    old_chars = "國學會髙濱邊邉齋齊澤澁"
    if any(c in text_name for c in old_chars):
        return "旧字体"
    if set(person_name) - set(text_name):
        return "表記ゆれ"
    return "その他"


def main():
    parser = argparse.ArgumentParser(description="エピソード本文の人物名不整合修正（全文置換版）")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に変更を適用（デフォルト: ドライラン）",
    )
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "execute" if args.execute else "dryrun"

    print("=" * 60)
    print("【人物名不整合修正スクリプト（全文置換版）】")
    print("=" * 60)
    print(f"モード: {'★実行★' if args.execute else 'ドライラン（プレビュー）'}")
    print(f"対象: {MASTER_CSV_PATH}")
    print()

    # CSV読み込み
    rows = []
    with open(MASTER_CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    print(f"総エピソード数: {len(rows):,}")

    # 処理統計
    mismatches = []
    type_counts = defaultdict(int)
    total_replacements = 0
    no_pattern = 0

    for i, row in enumerate(rows):
        episode_id = row.get("episode_id", "")
        person_name = row.get("person_name", "")
        episode_text = row.get("episode_text", "")
        name_raw = row.get("name_raw", "")

        # リード文から名前を抽出
        text_name, age = extract_name_from_lead(episode_text)

        if text_name is None:
            no_pattern += 1
            continue

        # 不整合チェック
        if text_name != person_name:
            mismatch_type = classify_mismatch(person_name, text_name)
            type_counts[mismatch_type] += 1

            # 全文置換
            new_text, replace_count = replace_name_in_text(episode_text, text_name, person_name, age)

            if replace_count > 0:
                total_replacements += replace_count
                mismatches.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "text_name": text_name,
                        "name_raw": name_raw,
                        "mismatch_type": mismatch_type,
                        "replace_count": replace_count,
                        "before": episode_text[:100],
                        "after": new_text[:100],
                    }
                )

                # 実行モードならデータを更新
                if args.execute:
                    rows[i]["episode_text"] = new_text

    # サマリー出力
    print()
    print("=" * 60)
    print("【処理結果】")
    print("=" * 60)
    print(f"パターン抽出不可: {no_pattern:,}")
    print(f"★ 不整合件数: {len(mismatches):,}")
    print(f"★ 総置換回数: {total_replacements:,}")
    print()

    print("【不整合タイプ別内訳】")
    for mtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {mtype}: {count:,}件")
    print()

    # 代表例（最大5件）
    print("【代表例（最大5件）】")
    for m in mismatches[:5]:
        print(f"  {m['episode_id']}: {m['text_name']} → {m['person_name']} ({m['replace_count']}箇所)")
    print()

    # 詳細レポート出力
    detail_path = REPORTS_DIR / f"name_mismatch_fix_{mode}_{timestamp}.csv"
    with open(detail_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "episode_id",
                "person_name",
                "text_name",
                "name_raw",
                "mismatch_type",
                "replace_count",
                "before",
                "after",
            ],
        )
        writer.writeheader()
        writer.writerows(mismatches)
    print(f"詳細レポート: {detail_path}")

    # 実行モードならCSV保存
    if args.execute and mismatches:
        # バックアップ作成
        backup_path = MASTER_CSV_PATH.parent / f"{MASTER_CSV_PATH.stem}.bak_namefix_{timestamp}.csv"
        with open(MASTER_CSV_PATH, "r", encoding="utf-8-sig") as src:
            with open(backup_path, "w", encoding="utf-8-sig") as dst:
                dst.write(src.read())
        print(f"バックアップ: {backup_path}")

        # 更新保存
        with open(MASTER_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"★ CSV更新完了: {len(rows):,}件")

    print()
    print("=" * 60)
    if args.execute:
        print("✅ 修正完了")
    else:
        print("💡 ドライランモード: 変更は適用されていません")
        print("   本番実行: python scripts/fix/fix_name_mismatch_full.py --execute")
    print("=" * 60)

    return len(mismatches)


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
