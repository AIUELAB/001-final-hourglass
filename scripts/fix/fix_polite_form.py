#!/usr/bin/env python3
"""
常体→丁寧語変換スクリプト

変換対象:
- だ。→ です。
- た。→ ました。
- だった。→ でした。
- である。→ です。
- ない。→ ません。
- なかった。→ ませんでした。
- だろう。→ でしょう。
- でいた。→ でいました。（取り組んでいた等）
- にいた。→ にいました。（渦中にいた等）
- てきた。→ てきました。（歩んできた等）
- [下一段動詞]た。→ [下一段動詞]ました。（与えた、集めた等）
- 安全な促音便（となった→となりました等）
- 安全な撥音便（込んだ→込みました等）

エピソードは丁寧語（です・ます調）で記述する必要がある。
引用（「」『』（））内のテキストは変換対象外。
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

# 引用パターン（引用内は変換対象外）
QUOTE_PATTERNS = [
    r"「[^」]*」",
    r"『[^』]*』",
    r"（[^）]*）",
]

# 事前フィルタ用: 常体検出パターン（quality_regression_check.pyと同等）
# 注: 事前フィルタは「変換候補の可能性がある」テキストを通すためのもの
# 厳密な変換判定は convert_plain_to_polite() で行う
PREFILTER_PATTERNS = [
    re.compile(r"(?<!し)(?<!でし)た[。、]"),  # 常体「た」
    re.compile(r"(?<!し)だ[。、]"),  # 常体「だ」
    re.compile(r"である[。、]"),  # 常体「である」
    re.compile(r"だった[。、]"),  # 常体「だった」
    re.compile(r"ない[。、]"),  # 常体「ない」
    re.compile(r"なかった[。、]"),  # 常体「なかった」
]


def _remove_quotes(text: str) -> str:
    """引用・台詞を除去（チェック用）"""
    for pattern in QUOTE_PATTERNS:
        text = re.sub(pattern, "", text)
    return text


def _has_plain_form(text: str) -> bool:
    """引用を除去した上で常体が含まれるかチェック"""
    clean = _remove_quotes(text)
    for pattern in PREFILTER_PATTERNS:
        if pattern.search(clean):
            return True
    return False


def create_backup(csv_path: Path, operation: str) -> Path:
    """バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"MASTER_EPISODES_{operation}_{timestamp}.csv"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(csv_path, backup_path)
    return backup_path


def convert_plain_to_polite(text: str) -> tuple[str, int]:
    """
    常体を丁寧語に変換（引用内は変換対象外）

    Returns:
        (変換後テキスト, 変換回数)
    """
    if not text or pd.isna(text):
        return text, 0

    # 引用部分を保護: プレースホルダーに置換してから変換し、最後に復元
    placeholders = []

    def _protect_quote(match):
        idx = len(placeholders)
        placeholders.append(match.group(0))
        return f"\x00QUOTE{idx}\x00"

    protected = text
    for qp in QUOTE_PATTERNS:
        protected = re.sub(qp, _protect_quote, protected)

    count = 0

    # 変換ルール（順序重要: 長いパターン・複合形式を先に処理）
    conversions = [
        # --- 否定過去 ---
        (r"なかった。", "ませんでした。"),
        (r"なかった、", "ませんでしたが、"),
        (r"なかった$", "ませんでした"),
        # --- 推量 ---
        (r"だろう。", "でしょう。"),
        (r"だろう、", "でしょうが、"),
        (r"だろう$", "でしょう"),
        # --- 過去（だった） ---
        (r"だった。", "でした。"),
        (r"だった、", "でしたが、"),
        (r"だった$", "でした"),
        # --- 「ていた」→「ていました」 ---
        (r"ていた。", "ていました。"),
        (r"ていた、", "ていましたが、"),
        (r"ていた$", "ていました"),
        # --- 「でいた」→「でいました」（取り組んでいた等） ---
        (r"でいた。", "でいました。"),
        (r"でいた、", "でいましたが、"),
        (r"でいた$", "でいました"),
        # --- 「にいた」→「にいました」（渦中にいた等） ---
        (r"にいた。", "にいました。"),
        (r"にいた、", "にいましたが、"),
        (r"にいた$", "にいました"),
        # --- 「てきた」→「てきました」（歩んできた等） ---
        (r"てきた。", "てきました。"),
        (r"てきた、", "てきましたが、"),
        (r"てきた$", "てきました"),
        # --- 「できた」→「できました」（歩んできた、実現できた等） ---
        (r"できた。", "できました。"),
        (r"できた、", "できましたが、"),
        (r"できた$", "できました"),
        # --- 「のだ」→「のです」 ---
        (r"のだ。", "のです。"),
        (r"のだ、", "のですが、"),
        (r"のだ$", "のです"),
        # --- 「のである」→「のです」 ---
        (r"のである。", "のです。"),
        (r"のである、", "のですが、"),
        (r"のである$", "のです"),
        # --- 「であった」→「でした」（「である」より先に処理） ---
        (r"であった。", "でした。"),
        (r"であった、", "でしたが、"),
        (r"であった$", "でした"),
        # --- 「である」→「です」 ---
        (r"である。", "です。"),
        (r"である、", "ですが、"),
        (r"である$", "です"),
        # --- 否定現在 ---
        (r"ない。", "ません。"),
        (r"ない、", "ませんが、"),
        (r"ない$", "ません"),
        # --- 安全な促音便パターン（頻出・変換が一意） ---
        # 「となった」→「となりました」
        (r"となった。", "となりました。"),
        (r"となった、", "となりましたが、"),
        (r"となった$", "となりました"),
        # 「になった」→「になりました」
        (r"になった。", "になりました。"),
        (r"になった、", "になりましたが、"),
        (r"になった$", "になりました"),
        # 「にあった」→「にありました」
        (r"にあった。", "にありました。"),
        (r"にあった、", "にありましたが、"),
        (r"にあった$", "にありました"),
        # 「もあった」→「もありました」
        (r"もあった。", "もありました。"),
        (r"もあった、", "もありましたが、"),
        (r"もあった$", "もありました"),
        # 「ていった」→「ていきました」
        (r"ていった。", "ていきました。"),
        (r"ていった、", "ていきましたが、"),
        (r"ていった$", "ていきました"),
        # 「でいった」→「でいきました」
        (r"でいった。", "でいきました。"),
        (r"でいった、", "でいきましたが、"),
        (r"でいった$", "でいきました"),
        # 「を行った」→「を行いました」
        (r"を行った。", "を行いました。"),
        (r"を行った、", "を行いましたが、"),
        (r"を行った$", "を行いました"),
        # 「語った」→「語りました」
        (r"語った。", "語りました。"),
        (r"語った、", "語りましたが、"),
        (r"語った$", "語りました"),
        # 「変わった」→「変わりました」
        (r"変わった。", "変わりました。"),
        (r"変わった、", "変わりましたが、"),
        (r"変わった$", "変わりました"),
        # --- 下一段動詞パターン ---
        # [えけせねめれげべ]た → [えけせねめれげべ]ました
        # 例: 与えた→与えました、集めた→集めました、受けた→受けました
        # 注: 「て」は除外（「〜してた」等は上の「ていた」ルールで対応済み）
        (r"([えけせねめれげべ])た。", r"\1ました。"),
        (r"([えけせねめれげべ])た、", r"\1ましたが、"),
        (r"([えけせねめれげべ])た$", r"\1ました"),
        # --- 過去（した）→「しました」 ---
        (r"(?<!ま)(?<!で)した。", "しました。"),
        (r"(?<!ま)(?<!で)した、", "しましたが、"),
        (r"(?<!ま)(?<!で)した$", "しました"),
        # --- 撥音便パターン（安全な個別対応） ---
        # 「込んだ」→「込みました」（吹き込んだ、注ぎ込んだ等）
        (r"込んだ。", "込みました。"),
        (r"込んだ、", "込みましたが、"),
        (r"込んだ$", "込みました"),
        # 「組んだ」→「組みました」
        (r"組んだ。", "組みました。"),
        (r"組んだ、", "組みましたが、"),
        (r"組んだ$", "組みました"),
        # 「学んだ」→「学びました」
        (r"学んだ。", "学びました。"),
        (r"学んだ、", "学びましたが、"),
        (r"学んだ$", "学びました"),
        # 「刻んだ」→「刻みました」
        (r"刻んだ。", "刻みました。"),
        (r"刻んだ、", "刻みましたが、"),
        (r"刻んだ$", "刻みました"),
        # 「歩んだ」→「歩みました」
        (r"歩んだ。", "歩みました。"),
        (r"歩んだ、", "歩みましたが、"),
        (r"歩んだ$", "歩みました"),
        # 「積んだ」→「積みました」
        (r"積んだ。", "積みました。"),
        (r"積んだ、", "積みましたが、"),
        (r"積んだ$", "積みました"),
        # 「結んだ」→「結びました」
        (r"結んだ。", "結びました。"),
        (r"結んだ、", "結びましたが、"),
        (r"結んだ$", "結びました"),
        # 「選んだ」→「選びました」
        (r"選んだ。", "選びました。"),
        (r"選んだ、", "選びましたが、"),
        (r"選んだ$", "選びました"),
        # 「臨んだ」→「臨みました」
        (r"臨んだ。", "臨みました。"),
        (r"臨んだ、", "臨みましたが、"),
        (r"臨んだ$", "臨みました"),
        # 「挑んだ」→「挑みました」
        (r"挑んだ。", "挑みました。"),
        (r"挑んだ、", "挑みましたが、"),
        (r"挑んだ$", "挑みました"),
        # 「呼んだ」→「呼びました」
        (r"呼んだ。", "呼びました。"),
        (r"呼んだ、", "呼びましたが、"),
        (r"呼んだ$", "呼びました"),
        # 「育んだ」→「育みました」
        (r"育んだ。", "育みました。"),
        (r"育んだ、", "育みましたが、"),
        (r"育んだ$", "育みました"),
        # --- 名詞述語 ---
        # 注: (?<!ん) で撥音便の「んだ」を除外（誤変換防止）
        (r"(?<!で)(?<!ま)(?<!ん)だ。", "です。"),
        (r"(?<!で)(?<!ま)(?<!ん)だ、", "ですが、"),
        (r"(?<!で)(?<!ま)(?<!ん)だ$", "です"),
    ]

    for pattern, replacement in conversions:
        new_text, n = re.subn(pattern, replacement, protected)
        if n > 0:
            protected = new_text
            count += n

    # プレースホルダーを元に戻す
    result = protected
    for idx, original in enumerate(placeholders):
        result = result.replace(f"\x00QUOTE{idx}\x00", original)

    return result, count


def fix_polite_form(
    csv_path: Path = MASTER_CSV,
    dry_run: bool = True,
    verbose: bool = False,
    limit: int = None,
) -> dict:
    """
    常体を丁寧語に一括変換

    Args:
        csv_path: CSVファイルパス
        dry_run: Trueの場合、変更を保存しない
        verbose: 詳細ログを出力
        limit: 処理件数制限（テスト用）

    Returns:
        変換結果のサマリー
    """
    print("=" * 60)
    print("常体→丁寧語変換")
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

    process_count = 0
    for idx, row in df.iterrows():
        if limit and process_count >= limit:
            break

        episode_id = row.get("episode_id", "")
        text = str(row.get("episode_text", "") or "")

        # 引用を除去してから常体チェック（事前フィルタ）
        if not _has_plain_form(text):
            results["unchanged"] += 1
            continue

        # 変換を実行
        converted_text, conv_count = convert_plain_to_polite(text)

        if conv_count > 0:
            results["converted"] += 1
            results["conversion_count"] += conv_count
            results["converted_ids"].append(episode_id)

            # DataFrameを更新
            df.at[idx, "episode_text"] = converted_text

            if verbose:
                print(f"  {episode_id}: {conv_count}箇所変換")
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

    parser = argparse.ArgumentParser(description="常体→丁寧語変換")
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
