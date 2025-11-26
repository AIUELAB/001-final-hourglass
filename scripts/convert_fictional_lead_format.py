#!/usr/bin/env python3
"""
架空キャラクターリード文フォーマット変換スクリプト

既存の架空キャラクターエピソードを新フォーマットに変換する。

変換前: 「あなたと同じ17歳のとき、毛利蘭は〜」
変換後: 「あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は〜」
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.episode_lead_builder import (
    WORK_TITLE_MAP,
    convert_episode_lead,
    get_work_title,
)

# 定数
CSV_PATH = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = project_root / "preserved" / "data" / "backups"


def analyze_work_title_status():
    """work_titleの欠損状況を分析"""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    fictional = df[df["person_type"].str.upper().str.contains("FICTIONAL", na=False)]

    print("=" * 60)
    print("📊 work_title欠損分析")
    print("=" * 60)

    missing = []
    for _, row in fictional.iterrows():
        work_title = row.get("work_title")
        person_name = row["person_name"]

        if pd.isna(work_title) or str(work_title) in ("", "nan", "None"):
            resolved, warning = get_work_title(person_name, None)
            status = "✅ MAP補完可" if resolved else "❌ 補完不可"
            missing.append({"person_name": person_name, "age": row["age"], "resolved": resolved, "status": status})

    print(f"\n架空キャラクター総数: {len(fictional)}件")
    print(f"work_title欠損: {len(missing)}件")

    if missing:
        print("\n--- 欠損詳細 ---")
        for item in missing:
            print(f"  {item['status']} {item['person_name']} ({item['age']}歳) → {item['resolved'] or '要手動設定'}")

    # 補完不可の件数
    unresolved = [m for m in missing if m["resolved"] is None]
    if unresolved:
        print(f"\n⚠️ 補完不可: {len(unresolved)}件")
        for item in unresolved:
            print(f"  - {item['person_name']} ({item['age']}歳)")

    return missing


def fill_missing_work_titles(dry_run: bool = True):
    """work_title欠損をMAPから補完"""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    updated_count = 0
    for idx, row in df.iterrows():
        person_type = str(row.get("person_type", "")).upper()
        if "FICTIONAL" not in person_type:
            continue

        work_title = row.get("work_title")
        if pd.isna(work_title) or str(work_title) in ("", "nan", "None"):
            person_name = row["person_name"]
            resolved, _ = get_work_title(person_name, None)
            if resolved:
                if not dry_run:
                    df.loc[idx, "work_title"] = resolved
                updated_count += 1
                print(f"  補完: {person_name} → {resolved}")

    if not dry_run and updated_count > 0:
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"\n💾 CSV更新完了: {updated_count}件のwork_titleを補完")

    return updated_count


def convert_fictional_leads(dry_run: bool = True):
    """架空キャラクターのリード文を新フォーマットに変換"""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    results = {"converted": [], "skipped": [], "warnings": [], "already_new_format": []}

    for idx, row in df.iterrows():
        person_type = str(row.get("person_type", "")).upper()
        if "FICTIONAL" not in person_type:
            continue

        person_name = row["person_name"]
        age = row["age"]
        work_title = row.get("work_title")
        episode_text = str(row["episode_text"])

        # 変換実行
        new_text, warning = convert_episode_lead(episode_text, person_name, int(age), person_type, work_title)

        if warning:
            results["warnings"].append({"person_name": person_name, "age": age, "warning": warning})
            continue

        if new_text == episode_text:
            # 変換なし（すでに新フォーマットまたはパターン不一致）
            if "『" in episode_text[:50] and "（『" not in episode_text[:50]:
                results["already_new_format"].append({"person_name": person_name, "age": age})
            else:
                results["skipped"].append({"person_name": person_name, "age": age, "reason": "パターン不一致"})
            continue

        # 変換成功
        results["converted"].append(
            {"person_name": person_name, "age": age, "old": episode_text[:80], "new": new_text[:80]}
        )

        if not dry_run:
            df.loc[idx, "episode_text"] = new_text

    if not dry_run and results["converted"]:
        # バックアップ作成
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"MASTER_EPISODES_backup_lead_convert_{timestamp}.csv"
        df_original = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        df_original.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"\n📦 バックアップ作成: {backup_path}")

        # 保存
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print("💾 CSV更新完了")

    return results


def print_conversion_report(results: dict):
    """変換結果レポートを表示"""
    print("\n" + "=" * 60)
    print("📊 リード文変換結果")
    print("=" * 60)

    print(f"\n✅ 変換成功: {len(results['converted'])}件")
    for item in results["converted"][:5]:
        print(f"  {item['person_name']} ({item['age']}歳)")
        print(f"    前: {item['old'][:60]}...")
        print(f"    後: {item['new'][:60]}...")
    if len(results["converted"]) > 5:
        print(f"  ... 他 {len(results['converted']) - 5}件")

    print(f"\n⏭️ すでに新フォーマット: {len(results['already_new_format'])}件")
    for item in results["already_new_format"][:3]:
        print(f"  {item['person_name']} ({item['age']}歳)")

    if results["warnings"]:
        print(f"\n⚠️ 警告: {len(results['warnings'])}件")
        for item in results["warnings"]:
            print(f"  {item['person_name']} ({item['age']}歳): {item['warning']}")

    if results["skipped"]:
        print(f"\n⏭️ スキップ: {len(results['skipped'])}件")
        for item in results["skipped"][:3]:
            print(f"  {item['person_name']} ({item['age']}歳): {item['reason']}")


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="架空キャラクターリード文フォーマット変換")
    parser.add_argument("--analyze", action="store_true", help="work_title欠損を分析")
    parser.add_argument("--fill-titles", action="store_true", help="work_title欠損を補完")
    parser.add_argument("--convert", action="store_true", help="リード文を変換（ドライラン）")
    parser.add_argument("--execute", action="store_true", help="リード文を変換（実行）")
    args = parser.parse_args()

    if args.analyze:
        analyze_work_title_status()
        return

    if args.fill_titles:
        print("🔧 work_title欠損を補完中...")
        count = fill_missing_work_titles(dry_run=False)
        print(f"完了: {count}件補完")
        return

    if args.convert or args.execute:
        dry_run = not args.execute

        if dry_run:
            print("🔍 ドライラン: 実際の変換は行いません")
        else:
            print("⚠️ 実行モード: データを変換します")

        # まずwork_title補完
        print("\n--- Step 1: work_title補完 ---")
        fill_count = fill_missing_work_titles(dry_run=dry_run)
        print(f"補完対象: {fill_count}件")

        # リード文変換
        print("\n--- Step 2: リード文変換 ---")
        results = convert_fictional_leads(dry_run=dry_run)
        print_conversion_report(results)

        if dry_run:
            print("\n💡 実際に変換を適用するには --execute オプションを使用してください")
        return

    # デフォルト: 分析のみ
    analyze_work_title_status()


if __name__ == "__main__":
    main()
