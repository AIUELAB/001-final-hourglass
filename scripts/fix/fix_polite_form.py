#!/usr/bin/env python3
"""
丁寧語→常体変換スクリプト

変換対象:
- です。→ だ。/である。
- ます。→ た。/る。
- でした。→ だった。
- ました。→ た。
- ません。→ ない。
- ません。→ なかった。
- でしょう。→ だろう。

エピソードは常体（である調）で記述する必要がある。
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


def convert_polite_to_plain(text: str) -> tuple[str, int]:
    """
    丁寧語を常体に変換

    Returns:
        (変換後テキスト, 変換回数)
    """
    if not text or pd.isna(text):
        return text, 0

    original = text
    count = 0

    # 変換ルール（順序重要）
    # 1. 複合形式を先に処理
    conversions = [
        # 否定過去
        (r"ませんでした。", "なかった。"),
        (r"ませんでした、", "なかったが、"),
        (r"ませんでした$", "なかった"),
        # 否定現在
        (r"ません。", "ない。"),
        (r"ません、", "ないが、"),
        (r"ません$", "ない"),
        # 推量
        (r"でしょう。", "だろう。"),
        (r"でしょう、", "だろうが、"),
        (r"でしょう$", "だろう"),
        # 過去（でした）
        (r"でした。", "だった。"),
        (r"でした、", "だったが、"),
        (r"でした$", "だった"),
        # 過去（ました）- 動詞の活用
        (r"しました。", "した。"),
        (r"しました、", "したが、"),
        (r"しました$", "した"),
        (r"きました。", "きた。"),
        (r"きました、", "きたが、"),
        (r"きました$", "きた"),
        (r"りました。", "った。"),
        (r"りました、", "ったが、"),
        (r"りました$", "った"),
        (r"いました。", "いた。"),
        (r"いました、", "いたが、"),
        (r"いました$", "いた"),
        (r"ちました。", "った。"),
        (r"ちました、", "ったが、"),
        (r"ちました$", "った"),
        (r"にました。", "んだ。"),
        (r"にました、", "んだが、"),
        (r"にました$", "んだ"),
        (r"びました。", "んだ。"),
        (r"びました、", "んだが、"),
        (r"びました$", "んだ"),
        (r"みました。", "んだ。"),
        (r"みました、", "んだが、"),
        (r"みました$", "んだ"),
        (r"けました。", "けた。"),
        (r"けました、", "けたが、"),
        (r"けました$", "けた"),
        (r"げました。", "げた。"),
        (r"げました、", "げたが、"),
        (r"げました$", "げた"),
        (r"せました。", "せた。"),
        (r"せました、", "せたが、"),
        (r"せました$", "せた"),
        (r"てました。", "ていた。"),
        (r"てました、", "ていたが、"),
        (r"てました$", "ていた"),
        (r"れました。", "れた。"),
        (r"れました、", "れたが、"),
        (r"れました$", "れた"),
        (r"えました。", "えた。"),
        (r"えました、", "えたが、"),
        (r"えました$", "えた"),
        # 汎用「ました」（上記にマッチしなかったもの）
        (r"ました。", "た。"),
        (r"ました、", "たが、"),
        (r"ました$", "た"),
        # 現在（ます）- 動詞の活用
        (r"します。", "する。"),
        (r"します、", "するが、"),
        (r"します$", "する"),
        (r"きます。", "くる。"),
        (r"きます、", "くるが、"),
        (r"きます$", "くる"),
        (r"ります。", "る。"),
        (r"ります、", "るが、"),
        (r"ります$", "る"),
        (r"います。", "いる。"),
        (r"います、", "いるが、"),
        (r"います$", "いる"),
        (r"ちます。", "つ。"),
        (r"ちます、", "つが、"),
        (r"ちます$", "つ"),
        (r"にます。", "ぬ。"),
        (r"にます、", "ぬが、"),
        (r"にます$", "ぬ"),
        (r"びます。", "ぶ。"),
        (r"びます、", "ぶが、"),
        (r"びます$", "ぶ"),
        (r"みます。", "む。"),
        (r"みます、", "むが、"),
        (r"みます$", "む"),
        (r"けます。", "ける。"),
        (r"けます、", "けるが、"),
        (r"けます$", "ける"),
        (r"げます。", "げる。"),
        (r"げます、", "げるが、"),
        (r"げます$", "げる"),
        (r"せます。", "せる。"),
        (r"せます、", "せるが、"),
        (r"せます$", "せる"),
        (r"てます。", "ている。"),
        (r"てます、", "ているが、"),
        (r"てます$", "ている"),
        (r"れます。", "れる。"),
        (r"れます、", "れるが、"),
        (r"れます$", "れる"),
        (r"えます。", "える。"),
        (r"えます、", "えるが、"),
        (r"えます$", "える"),
        # 汎用「ます」
        (r"ます。", "る。"),
        (r"ます、", "るが、"),
        (r"ます$", "る"),
        # 名詞述語（です）
        (r"です。", "だ。"),
        (r"です、", "だが、"),
        (r"です$", "だ"),
    ]

    for pattern, replacement in conversions:
        new_text, n = re.subn(pattern, replacement, text)
        if n > 0:
            text = new_text
            count += n

    return text, count


def fix_polite_form(
    csv_path: Path = MASTER_CSV,
    dry_run: bool = True,
    verbose: bool = False,
    limit: int = None,
) -> dict:
    """
    丁寧語を常体に一括変換

    Args:
        csv_path: CSVファイルパス
        dry_run: Trueの場合、変更を保存しない
        verbose: 詳細ログを出力
        limit: 処理件数制限（テスト用）

    Returns:
        変換結果のサマリー
    """
    print("=" * 60)
    print("丁寧語→常体変換")
    print("=" * 60)
    print(f"対象: {csv_path}")
    print(f"モード: {'dry-run' if dry_run else '実行'}")
    print()

    # バックアップ作成
    if not dry_run:
        backup_path = create_backup(csv_path, "polite_fix")
        print(f"バックアップ: {backup_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    print(f"総エピソード数: {len(df)}")

    results = {
        "total": len(df),
        "converted": 0,
        "conversion_count": 0,
        "unchanged": 0,
        "converted_ids": [],
    }

    # 丁寧語パターン検出用
    polite_pattern = re.compile(r"(です|ます|でした|ました|ません|でしょう)[。、]")

    process_count = 0
    for idx, row in df.iterrows():
        if limit and process_count >= limit:
            break

        episode_id = row.get("episode_id", "")
        text = str(row.get("episode_text", "") or "")

        # 丁寧語が含まれていない場合はスキップ
        if not polite_pattern.search(text):
            results["unchanged"] += 1
            continue

        # 変換を実行
        converted_text, conv_count = convert_polite_to_plain(text)

        if conv_count > 0:
            results["converted"] += 1
            results["conversion_count"] += conv_count
            results["converted_ids"].append(episode_id)

            # DataFrameを更新
            df.at[idx, "episode_text"] = converted_text

            if verbose:
                print(f"✓ {episode_id}: {conv_count}箇所変換")
                if conv_count <= 3:
                    print(f"  Before: {text[:80]}...")
                    print(f"  After:  {converted_text[:80]}...")
        else:
            results["unchanged"] += 1

        process_count += 1

    # サマリー出力
    print()
    print("=" * 60)
    print("変換サマリー")
    print("=" * 60)
    print(f"変換対象: {results['converted']}件")
    print(f"変換箇所: {results['conversion_count']}箇所")
    print(f"変換なし: {results['unchanged']}件")

    # 保存
    if not dry_run and results["converted"] > 0:
        print()
        print("保存中...")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print("保存完了")

    return results


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="丁寧語→常体変換")
    parser.add_argument("--dry-run", action="store_true", help="dry-runモード")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ")
    parser.add_argument("--limit", type=int, help="処理件数制限")
    parser.add_argument(
        "--csv",
        default=str(MASTER_CSV),
        help="対象CSVファイル",
    )
    args = parser.parse_args()

    fix_polite_form(
        csv_path=Path(args.csv),
        dry_run=args.dry_run,
        verbose=args.verbose,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
