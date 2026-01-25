#!/usr/bin/env python3
"""
全「私は」パターン修正スクリプト（包括版）

EPUP定型仕様:
- 正: 「あなたと同じ{age}歳のとき、{person_name}は...」
- 誤: 「あなたと同じ{age}歳のとき、私は...」、文中の「私は/私の/私が」

本スクリプトは全エピソードから「私は/私の/私が」を検出し、
person_name列の値で置換する包括修正を実行する。

使用法:
    python scripts/validation/fix_all_watashi_patterns.py --dry-run
    python scripts/validation/fix_all_watashi_patterns.py --execute
"""

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "data" / "backups"


@dataclass
class FixResult:
    """修正結果"""

    episode_id: str
    person_name: str
    age: int
    text_length_before: int
    text_length_after: int
    changes_count: int
    changes: list[str] = field(default_factory=list)


@dataclass
class FixStats:
    """修正統計"""

    total_episodes: int = 0
    detected: int = 0
    fixed: int = 0
    skipped: int = 0
    errors: int = 0
    total_replacements: int = 0


class AllWatashiPatternFixer:
    """全「私は」パターン修正エンジン"""

    # 置換対象のパターン（優先度順）
    # 「私は/私の/私が」を全て対象にする
    WATASHI_PATTERNS = [
        (r"私は", "{name}は"),
        (r"私の", "{name}の"),
        (r"私が", "{name}が"),
        (r"私に", "{name}に"),
        (r"私を", "{name}を"),
        (r"私と", "{name}と"),
    ]

    # 引用パターン（保護対象）
    QUOTE_PATTERNS = [
        r"「[^」]*」",
        r"『[^』]*』",
        r"（[^）]*）",
    ]

    def __init__(self, csv_path: Path = MASTER_CSV):
        self.csv_path = csv_path
        self.stats = FixStats()

    def _protect_quotes(self, text: str) -> tuple[str, list[str]]:
        """引用を一時プレースホルダーに置換して保護"""
        quotes = []
        protected = text

        for pattern in self.QUOTE_PATTERNS:
            matches = re.findall(pattern, protected)
            for match in matches:
                placeholder = f"__QUOTE_{len(quotes)}__"
                quotes.append(match)
                protected = protected.replace(match, placeholder, 1)

        return protected, quotes

    def _restore_quotes(self, text: str, quotes: list[str]) -> str:
        """プレースホルダーを元の引用に復元"""
        restored = text
        for i, quote in enumerate(quotes):
            placeholder = f"__QUOTE_{i}__"
            restored = restored.replace(placeholder, quote)
        return restored

    def detect(self, text: str) -> bool:
        """「私は/私の/私が」パターンを検出"""
        if not text:
            return False

        # 引用を保護
        protected, _ = self._protect_quotes(text)

        # 保護後のテキストで「私は/私の/私が」を検索
        for pattern, _ in self.WATASHI_PATTERNS:
            if re.search(pattern, protected):
                return True
        return False

    def fix_text(self, text: str, person_name: str) -> tuple[str, list[str], int]:
        """テキストを修正"""
        if not text or not person_name:
            return text, [], 0

        changes = []
        fixed = text
        total_replacements = 0

        # 1. 引用を保護
        protected, quotes = self._protect_quotes(text)

        # 2. 保護済みテキスト内で「私は/私の/私が」を置換
        for pattern, replacement in self.WATASHI_PATTERNS:
            actual_replacement = replacement.replace("{name}", person_name)

            # マッチを検索
            matches = re.findall(pattern, protected)
            if matches:
                count = len(matches)
                total_replacements += count
                changes.append(f"{pattern} → {actual_replacement} ({count}件)")

                # 置換実行
                protected = re.sub(pattern, actual_replacement, protected)

        # 3. 引用を復元
        fixed = self._restore_quotes(protected, quotes)

        return fixed, changes, total_replacements

    def execute(self, dry_run: bool = True) -> list[FixResult]:
        """修正を実行"""
        # バックアップ作成
        if not dry_run:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = BACKUP_DIR / f"MASTER_BACKUP_allwatashi_{timestamp}.csv"
            shutil.copy(self.csv_path, backup_path)
            print(f"バックアップ作成: {backup_path}")

        df = pd.read_csv(self.csv_path, encoding="utf-8-sig", low_memory=False)
        self.stats.total_episodes = len(df)

        results = []

        for idx, row in df.iterrows():
            text = str(row.get("episode_text", "") or "")
            episode_id = row.get("episode_id", "")
            person_name = str(row.get("person_name", "") or "")
            age = row.get("age", 0)

            # 検出
            if not self.detect(text):
                continue

            self.stats.detected += 1

            if not person_name:
                self.stats.errors += 1
                continue

            # 修正
            fixed_text, changes, replacements = self.fix_text(text, person_name)

            if changes:
                result = FixResult(
                    episode_id=episode_id,
                    person_name=person_name,
                    age=int(age) if pd.notna(age) else 0,
                    text_length_before=len(text),
                    text_length_after=len(fixed_text),
                    changes_count=replacements,
                    changes=changes,
                )
                results.append(result)

                self.stats.total_replacements += replacements

                if not dry_run:
                    df.at[idx, "episode_text"] = fixed_text
                    self.stats.fixed += 1
            else:
                self.stats.skipped += 1

        # 保存
        if not dry_run:
            df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
            print(f"CSV保存完了: {self.csv_path}")

        return results


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="全「私は」パターン修正")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード")
    parser.add_argument("--execute", action="store_true", help="実行モード")
    args = parser.parse_args()

    print("=" * 70)
    print("全「私は」パターン修正スクリプト")
    print("=" * 70)

    fixer = AllWatashiPatternFixer()

    if args.execute:
        # 実行モード
        print("\n実行モード: CSV修正を実行します...")
        results = fixer.execute(dry_run=False)

        print("\n" + "=" * 70)
        print("修正完了")
        print("=" * 70)
        print(f"総エピソード数: {fixer.stats.total_episodes}")
        print(f"「私は」検出件数: {fixer.stats.detected}")
        print(f"修正件数: {fixer.stats.fixed}")
        print(f"スキップ: {fixer.stats.skipped}")
        print(f"エラー: {fixer.stats.errors}")
        print(f"総置換数: {fixer.stats.total_replacements}")
        print("=" * 70)

        if results:
            print("\n修正サンプル（最大10件）:")
            for r in results[:10]:
                print(f"\n  EP: {r.episode_id} | Person: {r.person_name} | Age: {r.age} | 置換数: {r.changes_count}")
                for change in r.changes:
                    print(f"    - {change}")

        print("\n検証コマンド:")
        print("  python scripts/validation/quality_regression_check.py --check watashi")

    else:
        # デフォルト: dry-run
        print("\nドライランモード")
        print("修正をシミュレートします（実ファイルは変更されません）...\n")

        results = fixer.execute(dry_run=True)

        print("\n" + "=" * 70)
        print("ドライラン結果")
        print("=" * 70)
        print(f"総エピソード数: {fixer.stats.total_episodes}")
        print(f"「私は」検出件数: {fixer.stats.detected}")
        print(f"修正予定件数: {len(results)}")
        print(f"総置換予定数: {fixer.stats.total_replacements}")
        print("=" * 70)

        if results:
            print("\n修正予定サンプル（最大10件）:")
            for r in results[:10]:
                print(f"\n  EP: {r.episode_id} | Person: {r.person_name} | Age: {r.age} | 置換数: {r.changes_count}")
                for change in r.changes:
                    print(f"    - {change}")

        print("\n" + "=" * 70)
        print("実行コマンド:")
        print("  python scripts/validation/fix_all_watashi_patterns.py --execute")
        print("=" * 70)


if __name__ == "__main__":
    main()
