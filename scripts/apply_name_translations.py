#!/usr/bin/env python3
"""
翻訳結果をMASTER CSVに適用するスクリプト

機能:
1. translation_results.csvから翻訳結果を読み込む
2. MASTER_EPISODES_CURRENT.csvのperson_nameを更新
3. display_name_original（元の英語名）カラムを追加

Usage:
    python scripts/apply_name_translations.py [--dry-run] [--execute]
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


# ========================================
# 定数
# ========================================

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
TRANSLATION_RESULTS = PROJECT_ROOT / "output" / "name_translation" / "translation_results.csv"
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"
OUTPUT_DIR = PROJECT_ROOT / "output" / "name_application"


def load_translations() -> Dict[str, Dict]:
    """
    翻訳結果を読み込む

    Returns:
        {person_id: {"japanese": str, "original": str, "confidence": float}} の辞書
    """
    if not TRANSLATION_RESULTS.exists():
        print(f"❌ 翻訳結果ファイルが見つかりません: {TRANSLATION_RESULTS}")
        sys.exit(1)

    df = pd.read_csv(TRANSLATION_RESULTS, encoding="utf-8-sig")
    translations = {}

    for _, row in df.iterrows():
        person_id = row["person_id"]
        translations[person_id] = {
            "japanese": row["japanese"],
            "original": row["original"],
            "confidence": row.get("confidence", 0),
            "name_type": row.get("name_type", "unknown"),
            "source": row.get("source", "unknown"),
        }

    print(f"📖 翻訳結果をロード: {len(translations)}件")
    return translations


def apply_translations(dry_run: bool = True, min_confidence: float = 0.8) -> Dict:
    """
    翻訳をMASTER CSVに適用

    Args:
        dry_run: ドライランモード
        min_confidence: 最小確信度閾値

    Returns:
        適用結果サマリー
    """
    # 翻訳結果をロード
    translations = load_translations()

    # MASTER CSVをロード
    print(f"📖 MASTER CSVをロード: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    original_count = len(df)

    # display_name_originalカラムがなければ追加
    if "display_name_original" not in df.columns:
        df["display_name_original"] = ""

    # 適用カウンター
    applied = 0
    skipped_low_confidence = 0
    skipped_not_found = 0
    unchanged = 0

    # 各行を処理
    for idx, row in df.iterrows():
        person_id = row["person_id"]
        current_name = row["person_name"]

        if person_id in translations:
            trans = translations[person_id]
            japanese_name = trans["japanese"]
            original_name = trans["original"]
            confidence = trans["confidence"]

            # 確信度チェック
            if confidence < min_confidence:
                skipped_low_confidence += 1
                continue

            # 名前が変わる場合のみ更新
            if current_name != japanese_name:
                df.at[idx, "person_name"] = japanese_name
                df.at[idx, "display_name_original"] = original_name
                applied += 1
            else:
                unchanged += 1
        else:
            skipped_not_found += 1

    # サマリー
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_rows": original_count,
        "translations_available": len(translations),
        "applied": applied,
        "unchanged": unchanged,
        "skipped_low_confidence": skipped_low_confidence,
        "skipped_not_found": skipped_not_found,
        "min_confidence": min_confidence,
        "dry_run": dry_run,
    }

    # 結果表示
    print()
    print("=" * 60)
    print("適用結果サマリー")
    print("=" * 60)
    print(f"総行数: {original_count:,}")
    print(f"翻訳可能: {len(translations):,}")
    print(f"適用件数: {applied:,}")
    print(f"変更なし: {unchanged:,}")
    print(f"確信度不足でスキップ: {skipped_low_confidence:,}")
    print(f"翻訳なしでスキップ: {skipped_not_found:,}")

    if not dry_run and applied > 0:
        # バックアップ作成
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"MASTER_EPISODES_CURRENT_{timestamp}_pre_name_translation.csv"
        shutil.copy(MASTER_CSV, backup_path)
        print(f"\n📦 バックアップ作成: {backup_path}")

        # MASTER CSVを更新
        df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        print(f"✅ MASTER CSV更新: {MASTER_CSV}")

    elif dry_run:
        # ドライランモードではプレビューを出力
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        preview_path = OUTPUT_DIR / "preview_applied.csv"
        df.to_csv(preview_path, index=False, encoding="utf-8-sig")
        print(f"\n📋 プレビュー出力: {preview_path}")

    # サマリーJSON出力
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    summary_path = OUTPUT_DIR / "application_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"📋 サマリーJSON: {summary_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="翻訳結果をMASTER CSVに適用")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード（実際の変更なし）")
    parser.add_argument("--execute", action="store_true", help="実際に適用を実行")
    parser.add_argument("--min-confidence", type=float, default=0.8, help="最小確信度閾値 (default: 0.8)")

    args = parser.parse_args()

    # ドライランがデフォルト
    dry_run = not args.execute

    print("=" * 60)
    print("翻訳結果適用スクリプト")
    print("=" * 60)
    print(f"MASTER CSV: {MASTER_CSV}")
    print(f"翻訳結果: {TRANSLATION_RESULTS}")
    print(f"モード: {'ドライラン' if dry_run else '実行'}")
    print(f"最小確信度: {args.min_confidence}")
    print()

    # 適用実行
    apply_translations(dry_run=dry_run, min_confidence=args.min_confidence)

    print()
    print("✅ 処理完了")

    if dry_run:
        print()
        print("💡 実際に適用するには --execute オプションを付けて再実行してください")


if __name__ == "__main__":
    main()
