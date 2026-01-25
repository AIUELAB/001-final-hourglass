#!/usr/bin/env python3
"""
FICTIONAL文頭フォーマット修正ツール

FICTIONALエピソードの文頭に『作品名』を挿入して修正する。

Usage:
    python scripts/fix/fix_fictional_lead_format.py --dry-run   # 対象確認
    python scripts/fix/fix_fictional_lead_format.py --execute   # 実行
    python scripts/fix/fix_fictional_lead_format.py --verify    # 検証
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved/backups"

# 必須パターン
FICTIONAL_LEAD_PATTERN = re.compile(r"^あなたと同じ\d+歳のとき、[^『]+『[^』]+』は")


def fix_fictional_lead(episode_text: str, person_name: str, work_title: str) -> tuple[str, str, float]:
    """
    FICTIONAL文頭を修正

    Args:
        episode_text: エピソードテキスト
        person_name: 人物名
        work_title: 作品名

    Returns:
        (修正後テキスト, ステータス, 確信度)
        確信度: 1.0=完全一致, 0.5=部分一致, 0.0=不一致
    """
    # 既に正しい形式
    if FICTIONAL_LEAD_PATTERN.match(episode_text):
        return episode_text, "既に準拠", 1.0

    # work_titleが空
    if not work_title or pd.isna(work_title):
        return episode_text, "work_title欠損", 0.0

    # パターン1: 「あなたと同じ{age}歳のとき、{person_name}は」
    pattern1 = rf"^(あなたと同じ\d+歳のとき、{re.escape(person_name)})は"
    if re.match(pattern1, episode_text):
        new_text = re.sub(pattern1, rf"\1『{work_title}』は", episode_text)
        return new_text, "修正完了（完全一致）", 1.0

    # パターン2: 「あなたと同じ{age}歳のとき、{person_name（別表記）}は」
    # 名前の後に括弧がある場合を許容
    pattern2 = rf"^(あなたと同じ\d+歳のとき、{re.escape(person_name)}(?:（[^）]+）)?)は"
    if re.match(pattern2, episode_text):
        new_text = re.sub(pattern2, rf"\1『{work_title}』は", episode_text)
        return new_text, "修正完了（括弧付き）", 0.9

    # パターン3: 名前が部分一致（スラッシュ区切りなど）
    # 例: 「デク/緑谷出久」
    name_parts = person_name.split("/")
    for part in name_parts:
        pattern3 = rf"^(あなたと同じ\d+歳のとき、[^は]*{re.escape(part)}[^は]*)は"
        match = re.match(pattern3, episode_text)
        if match:
            prefix = match.group(1)
            new_text = f"{prefix}『{work_title}』は{episode_text[match.end() :]}"
            return new_text, "修正完了（部分一致）", 0.8

    # パターン4: 「あなたと同じ{age}歳のとき、」だけはある
    pattern4 = r"^(あなたと同じ\d+歳のとき、)([^は]+)は"
    match = re.match(pattern4, episode_text)
    if match:
        # 既存の名前部分を確認
        existing_name = match.group(2)
        new_text = f"{match.group(1)}{existing_name}『{work_title}』は{episode_text[match.end() :]}"
        return new_text, "修正完了（名前不一致）", 0.6

    # 修正できない
    return episode_text, "パターン不一致（保留）", 0.0


def create_backup() -> Path:
    """バックアップを作成"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_before_lead_fix_{timestamp}.csv"
    shutil.copy2(MASTER_CSV, backup_path)
    return backup_path


def main():
    parser = argparse.ArgumentParser(description="FICTIONAL文頭フォーマット修正")
    parser.add_argument("--dry-run", action="store_true", help="対象確認のみ")
    parser.add_argument("--execute", action="store_true", help="修正を実行")
    parser.add_argument("--verify", action="store_true", help="修正後の検証")
    parser.add_argument("--min-confidence", type=float, default=0.6, help="修正する最小確信度（デフォルト: 0.6）")

    args = parser.parse_args()

    if not args.dry_run and not args.execute and not args.verify:
        args.dry_run = True

    print(f"📂 マスターCSV: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, low_memory=False)
    print(f"📊 総エピソード数: {len(df):,}件")

    fictional = df[df["person_type"] == "FICTIONAL"].copy()
    print(f"🎭 FICTIONALエピソード数: {len(fictional):,}件")

    # 違反を検出
    violations = fictional[~fictional["episode_text"].str.match(FICTIONAL_LEAD_PATTERN, na=False)]
    print(f"❌ 文頭違反: {len(violations):,}件")

    if len(violations) == 0:
        print("\n✅ 全FICTIONALエピソードが文頭フォーマットに準拠しています")
        sys.exit(0)

    if args.verify:
        sys.exit(1 if len(violations) > 0 else 0)

    # 修正プラン作成
    fix_results = []
    for idx, row in violations.iterrows():
        new_text, status, confidence = fix_fictional_lead(
            episode_text=str(row["episode_text"]),
            person_name=str(row["person_name"]),
            work_title=str(row["work_title"]) if pd.notna(row["work_title"]) else "",
        )
        fix_results.append(
            {
                "idx": idx,
                "episode_id": row["episode_id"],
                "person_name": row["person_name"],
                "work_title": row["work_title"],
                "status": status,
                "confidence": confidence,
                "new_text": new_text,
                "old_text": row["episode_text"],
            }
        )

    # 結果サマリー
    by_status = {}
    for r in fix_results:
        status = r["status"]
        by_status[status] = by_status.get(status, 0) + 1

    print("\n" + "=" * 60)
    print("修正プランサマリー")
    print("=" * 60)
    for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
        print(f"  {status}: {count}件")

    # 修正可能件数
    fixable = [r for r in fix_results if r["confidence"] >= args.min_confidence]
    pending = [r for r in fix_results if r["confidence"] < args.min_confidence]
    print(f"\n修正可能（確信度>={args.min_confidence}）: {len(fixable)}件")
    print(f"保留（確信度<{args.min_confidence}）: {len(pending)}件")

    if args.dry_run:
        # サンプル表示
        print("\n" + "-" * 60)
        print("修正サンプル（最大10件）")
        print("-" * 60)
        for r in fixable[:10]:
            print(f"\n[{r['episode_id']}] {r['person_name']} ({r['work_title']})")
            print(f"  確信度: {r['confidence']:.1f}")
            print(f"  Before: {r['old_text'][:60]}...")
            print(f"  After:  {r['new_text'][:60]}...")

        if pending:
            print("\n" + "-" * 60)
            print("保留サンプル（最大5件）")
            print("-" * 60)
            for r in pending[:5]:
                print(f"\n[{r['episode_id']}] {r['person_name']} ({r['work_title']})")
                print(f"  {r['status']}")
                print(f"  文頭: {r['old_text'][:80]}...")

        print("\n💡 実行するには --execute フラグを付けてください")
        sys.exit(0)

    if args.execute:
        # バックアップ作成
        backup_path = create_backup()
        print(f"\n💾 バックアップ作成: {backup_path}")

        # 修正実行
        modified_count = 0
        for r in fixable:
            df.at[r["idx"], "episode_text"] = r["new_text"]
            modified_count += 1

        # 保存
        df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")

        print("\n" + "=" * 60)
        print("✅ 修正完了")
        print("=" * 60)
        print(f"修正件数: {modified_count}件")
        print(f"保留件数: {len(pending)}件")

        # 検証
        df_verify = pd.read_csv(MASTER_CSV, low_memory=False)
        fictional_verify = df_verify[df_verify["person_type"] == "FICTIONAL"]
        remaining = fictional_verify[~fictional_verify["episode_text"].str.match(FICTIONAL_LEAD_PATTERN, na=False)]
        print(f"\n残存違反: {len(remaining)}件")

        if len(remaining) == 0:
            print("🎉 全FICTIONALエピソードが文頭フォーマットに準拠しました")
        else:
            print("⚠️ 一部違反が残っています（保留分）")

        sys.exit(0)


if __name__ == "__main__":
    main()
