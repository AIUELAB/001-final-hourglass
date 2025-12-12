#!/usr/bin/env python3
"""
エピソードフォーマットプレフィックス修正スクリプト

「【改稿後のエピソード】」「【改稿版】」などの不要プレフィックスを除去

使用方法:
    # ドライラン（検出のみ）
    python scripts/fix_format_prefix.py --dry-run

    # 実行
    python scripts/fix_format_prefix.py --execute
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

# 除去対象パターン（順序重要：長いパターンを先に）
REMOVE_PATTERNS = [
    r"^【改稿後のエピソード】\s*\n*",
    r"^【改稿版エピソード】\s*\n*",
    r"^【改稿後エピソード】\s*\n*",
    r"^【改稿版】\s*\n*",
    r"^【改稿後】\s*\n*",
    r"^【改善版】\s*\n*",
    r"^【修正版】\s*\n*",
    r"^【更新版】\s*\n*",
]

# 標準フォーマット検証パターン（西暦年が含まれる場合も許容）
STANDARD_FORMAT = r"^あなたと同じ\d+歳のとき[（\(]?\d*年?[）\)]?[、,]"


def detect_prefix_issues(df: pd.DataFrame) -> list:
    """
    プレフィックス問題を検出

    Args:
        df: エピソードDataFrame

    Returns:
        問題リスト
    """
    issues = []

    for idx, row in df.iterrows():
        text = str(row.get("episode_text", ""))
        if not text or text == "nan":
            continue

        for pattern in REMOVE_PATTERNS:
            if re.match(pattern, text):
                issues.append(
                    {
                        "index": idx,
                        "episode_id": row.get("episode_id", ""),
                        "person_name": row.get("person_name", ""),
                        "age": row.get("age", ""),
                        "pattern": pattern,
                        "preview": text[:100],
                    }
                )
                break

    return issues


def fix_prefix(text: str) -> str:
    """
    プレフィックスを除去

    Args:
        text: エピソードテキスト

    Returns:
        修正後テキスト
    """
    if not text or text == "nan":
        return text

    for pattern in REMOVE_PATTERNS:
        text = re.sub(pattern, "", text)

    return text.strip()


def validate_after_fix(text: str) -> dict:
    """
    修正後のテキストを検証

    Args:
        text: 修正後テキスト

    Returns:
        検証結果
    """
    result = {
        "valid": True,
        "issues": [],
    }

    # 空チェック
    if not text or len(text.strip()) == 0:
        result["valid"] = False
        result["issues"].append("empty_text")
        return result

    # 標準フォーマットチェック
    if not re.match(STANDARD_FORMAT, text):
        result["valid"] = False
        result["issues"].append("non_standard_format")

    # 文字数チェック
    if len(text) < 50:
        result["valid"] = False
        result["issues"].append("too_short")

    return result


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="エピソードフォーマットプレフィックス修正")
    parser.add_argument("--dry-run", action="store_true", help="検出のみ（変更なし）")
    parser.add_argument("--execute", action="store_true", help="変更を実行")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        return

    dry_run = not args.execute

    print("=" * 70)
    print(f"🔧 フォーマットプレフィックス修正 {'(dry-run)' if dry_run else '(実行)'}")
    print("=" * 70)
    print(f"  実行日時: {datetime.now().isoformat()}")

    # CSV読み込み
    print(f"\n📂 CSV読み込み: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  レコード数: {len(df)}件")

    # 問題検出
    print("\n🔍 プレフィックス問題検出中...")
    issues = detect_prefix_issues(df)
    print(f"  検出件数: {len(issues)}件")

    if not issues:
        print("\n✅ プレフィックス問題なし")
        return

    # パターン別集計
    pattern_counts = {}
    for issue in issues:
        pattern = issue["pattern"]
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    print("\n📊 パターン別内訳:")
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        # パターンを読みやすく表示
        readable = pattern.replace(r"\s*\n*", "").replace("^", "").replace(r"\s*", "")
        print(f"  {readable}: {count}件")

    # 修正処理
    print("\n🔄 修正処理中...")
    fix_log = []
    validation_failures = []

    for issue in issues:
        idx = issue["index"]
        original_text = df.loc[idx, "episode_text"]
        fixed_text = fix_prefix(original_text)

        # 検証
        validation = validate_after_fix(fixed_text)

        log_entry = {
            "episode_id": issue["episode_id"],
            "person_name": issue["person_name"],
            "age": issue["age"],
            "pattern": issue["pattern"],
            "original_preview": original_text[:80] if original_text else "",
            "fixed_preview": fixed_text[:80] if fixed_text else "",
            "validation": validation,
        }
        fix_log.append(log_entry)

        if not validation["valid"]:
            validation_failures.append(log_entry)

        if not dry_run:
            df.loc[idx, "episode_text"] = fixed_text

    # 結果表示
    print("\n" + "=" * 70)
    print("📊 結果サマリー")
    print("=" * 70)
    print(f"  検出件数: {len(issues)}件")
    print(f"  修正成功: {len(issues) - len(validation_failures)}件")
    print(f"  検証失敗: {len(validation_failures)}件")

    if validation_failures:
        print("\n⚠️ 検証失敗エピソード（先頭5件）:")
        for f in validation_failures[:5]:
            print(f"  - {f['person_name']} ({f['age']}歳): {f['validation']['issues']}")

    # 修正例表示
    print("\n📋 修正例（先頭5件）:")
    for log in fix_log[:5]:
        print(f"  {log['person_name']} ({log['age']}歳)")
        print(f"    前: {log['original_preview'][:50]}...")
        print(f"    後: {log['fixed_preview'][:50]}...")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = (
        REPORTS_DIR
        / f"format_fix_{'dryrun' if dry_run else 'executed'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    report = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "summary": {
            "total_issues": len(issues),
            "fixed": len(issues) - len(validation_failures),
            "validation_failures": len(validation_failures),
        },
        "pattern_counts": pattern_counts,
        "fix_log": fix_log[:100],  # 先頭100件のみ保存
        "validation_failures": validation_failures,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート保存: {report_path}")

    # CSV保存
    if not dry_run:
        print("\n💾 CSV保存中...")
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  保存完了: {len(df)}件")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
