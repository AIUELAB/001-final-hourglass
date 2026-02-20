"""
storytelling_quality → story_quality カラム統一マイグレーション

マージルール:
1. story_quality のみ値あり → そのまま保持
2. storytelling_quality のみ値あり → story_quality にコピー
3. 両方に値あり → max(story_quality, storytelling_quality) を採用
4. マイグレーション後、storytelling_quality カラムを削除

Usage:
    python scripts/migration/unify_story_quality_column.py [--dry-run | --execute]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"


def migrate(dry_run: bool = True) -> dict:
    if not CSV_PATH.exists():
        return {"success": False, "error": f"CSV not found: {CSV_PATH}"}

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    stats = {"total_rows": len(df)}

    has_storytelling = "storytelling_quality" in df.columns
    has_story = "story_quality" in df.columns

    if not has_storytelling:
        return {
            "success": True,
            "message": "storytelling_quality カラムが存在しません。マイグレーション不要。",
            **stats,
        }

    if not has_story:
        # story_quality が無い場合はリネームのみ
        stats["action"] = "rename_only"
        stats["renamed_count"] = int(df["storytelling_quality"].notna().sum())
        if not dry_run:
            df = df.rename(columns={"storytelling_quality": "story_quality"})
    else:
        # 両方存在 → マージ
        st = pd.to_numeric(df["storytelling_quality"], errors="coerce")
        sq = pd.to_numeric(df["story_quality"], errors="coerce")

        only_storytelling = st.notna() & sq.isna()
        only_story = st.isna() & sq.notna()
        both = st.notna() & sq.notna()
        both_differ = both & (st != sq)
        storytelling_wins = both & (st > sq)

        stats["only_storytelling"] = int(only_storytelling.sum())
        stats["only_story_quality"] = int(only_story.sum())
        stats["both_same"] = int((both & (st == sq)).sum())
        stats["both_differ"] = int(both_differ.sum())
        stats["storytelling_wins"] = int(storytelling_wins.sum())
        stats["story_quality_wins"] = int((both & (sq >= st)).sum())

        if not dry_run:
            # storytelling_quality のみ → story_quality にコピー
            df.loc[only_storytelling, "story_quality"] = df.loc[only_storytelling, "storytelling_quality"]
            # 両方あり → max を採用
            df.loc[both, "story_quality"] = pd.concat([st[both], sq[both]], axis=1).max(axis=1)
            # storytelling_quality カラム削除
            df = df.drop(columns=["storytelling_quality"])

    if dry_run:
        return {"success": True, "dry_run": True, **stats}

    # バックアップ
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"pre_story_quality_unify_{timestamp}.csv"
    pd.read_csv(CSV_PATH, encoding="utf-8-sig").to_csv(backup_path, index=False, encoding="utf-8-sig")

    # 保存
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

    return {
        "success": True,
        "dry_run": False,
        "backup_path": str(backup_path),
        **stats,
    }


def main():
    parser = argparse.ArgumentParser(description="storytelling_quality → story_quality 統一")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", default=True)
    group.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    dry_run = not args.execute
    result = migrate(dry_run=dry_run)

    mode = "DRY-RUN" if dry_run else "EXECUTE"
    print(f"\n{'=' * 60}")
    print(f"  storytelling_quality → story_quality 統一 [{mode}]")
    print(f"{'=' * 60}")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print(f"{'=' * 60}\n")

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
