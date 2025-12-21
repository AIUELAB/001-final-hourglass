#!/usr/bin/env python3
"""
episode_text内の人物名置換スクリプト

指示された3件の人物名をepisode_text内で統一:
1. 50 Cent → 50セント
2. Dwayne "The Rock" Johnson, The Rock, ザ・ロック → ドウェイン・ジョンソン
3. Notch, Markus Persson → マルクス・ペルソン

使用方法:
    python scripts/replace_episode_text_names.py --dry-run
    python scripts/replace_episode_text_names.py --execute
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
sys.path.insert(0, str(PROJECT_ROOT))

from src.csv_path_resolver import get_master_csv_path, get_reports_dir


# 置換マップ（順序重要: 長い文字列を先に）
# (パターン, 置換後, 正規表現フラグ)
REPLACEMENT_MAP = [
    # Dwayne Johnson系（長い順）
    (r'Dwayne "The Rock" Johnson', "ドウェイン・ジョンソン", False),
    (r"Dwayne \"The Rock\" Johnson", "ドウェイン・ジョンソン", False),
    # The Rock は単語境界で判定（The Rockafellerなどを除外）
    (r"\bThe Rock\b(?![a-zA-Z])", "ドウェイン・ジョンソン", True),
    # 50 Cent
    (r"50 Cent", "50セント", False),
    # Notch / Markus Persson（単語境界）
    (r"Markus Persson", "マルクス・ペルソン", False),
    (r"\bNotch\b", "マルクス・ペルソン", True),
]


def replace_in_text(text: str) -> tuple:
    """テキスト内の人物名を置換"""
    if pd.isna(text):
        return text, []

    original = text
    changes = []

    for pattern, replacement, is_regex in REPLACEMENT_MAP:
        if is_regex:
            # 正規表現で置換
            matches = re.findall(pattern, text)
            if matches:
                new_text = re.sub(pattern, replacement, text)
                if new_text != text:
                    changes.append({"pattern": pattern, "replacement": replacement, "count": len(matches)})
                    text = new_text
        else:
            # 単純な文字列置換
            if pattern in text:
                count = text.count(pattern)
                text = text.replace(pattern, replacement)
                if count > 0:
                    changes.append({"pattern": pattern, "replacement": replacement, "count": count})

    return text, changes


def main():
    parser = argparse.ArgumentParser(description="episode_text内の人物名置換")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（変更なし）")
    parser.add_argument("--execute", action="store_true", help="実行（CSV更新）")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        return

    mode = "dry-run" if args.dry_run else "実行"
    print("=" * 60)
    print(f"🔧 episode_text内 人物名置換 ({mode})")
    print("=" * 60)

    # CSV読み込み
    csv_path = get_master_csv_path()
    print(f"\n📂 CSV読み込み: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  レコード数: {len(df):,}")

    # 置換実行
    all_changes = []
    modified_count = 0

    for idx, row in df.iterrows():
        text = row.get("episode_text", "")
        new_text, changes = replace_in_text(text)

        if changes:
            all_changes.append(
                {
                    "episode_id": row.get("episode_id", idx),
                    "person_name": row.get("person_name", ""),
                    "changes": changes,
                }
            )
            modified_count += 1

            if args.execute:
                df.at[idx, "episode_text"] = new_text

    print(f"\n📊 置換対象: {modified_count}件")

    if all_changes:
        print("\n📋 置換例（先頭10件）:")
        for item in all_changes[:10]:
            print(f"  {item['episode_id']} ({item['person_name']})")
            for c in item["changes"]:
                print(f"    「{c['pattern']}」→「{c['replacement']}」: {c['count']}箇所")

    if args.execute and modified_count > 0:
        print("\n💾 変更を適用中...")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"  保存完了: {len(df):,}件")

    # レポート出力
    reports_dir = get_reports_dir()
    logs_dir = reports_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_str = "dryrun" if args.dry_run else "executed"
    output_path = logs_dir / f"episode_text_replace_{mode_str}_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "replacement_map": [(p, r, is_re) for p, r, is_re in REPLACEMENT_MAP],
        "modified_count": modified_count,
        "changes": all_changes,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 レポート保存: {output_path}")
    print("\n✅ 完了")


if __name__ == "__main__":
    main()
