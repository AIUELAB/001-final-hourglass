#!/usr/bin/env python3
"""
「私は」パターン修正スクリプト

EPUPの定型仕様:
- 正: 「あなたと同じ{age}歳のとき、{person_name}は...」
- 誤: 「あなたと同じ{age}歳のとき、私は...」

本スクリプトは「私は」を人物名に置換する。

Phase 1: 定型形式違反（文頭の「私は」「私[名前]は」）
Phase 2: 文中の「私は/私の/私が」（引用外のみ）

使用法:
    python scripts/validation/fix_watashi_pattern.py --dry-run
    python scripts/validation/fix_watashi_pattern.py --execute
    python scripts/validation/fix_watashi_pattern.py --dry-run --phase2
    python scripts/validation/fix_watashi_pattern.py --execute --phase2
"""

import argparse
import json
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
REPORTS_DIR = PROJECT_ROOT / "src" / "reports"
LOGS_DIR = PROJECT_ROOT / "src" / "reports" / "logs"


@dataclass
class FixResult:
    """修正結果"""

    episode_id: str
    person_name: str
    age: int
    original_text: str
    fixed_text: str
    changes: list[str] = field(default_factory=list)


@dataclass
class FixStats:
    """修正統計"""

    total_episodes: int = 0
    detected: int = 0
    fixed: int = 0
    skipped: int = 0
    errors: int = 0


class WatashiPatternFixer:
    """「私は」パターン修正エンジン"""

    # 検出パターン（Phase 1: 定型形式違反）
    # パターンA: 「あなたと同じXX歳のとき、私は」
    DETECT_PATTERN_A = r"^あなたと同じ\d+歳のとき、私は"
    # パターンB: 「あなたと同じXX歳のとき、私[名前]は」（Phase 1の主要対象）
    DETECT_PATTERN_B = r"^あなたと同じ\d+歳のとき、私[^は\s]{1,50}は"

    # 置換対象のパターン（優先度順）- Phase 1
    REPLACE_PATTERNS = [
        # Phase 1: 「私[名前]は」→「{name}は」（文頭の定型部分）
        # 例: 「私ミケランジェロ・メリージ・ダ・カラヴァッジオは」→「カラヴァッジオは」
        (r"(あなたと同じ\d+歳のとき、)私[^は\s]{1,50}は", r"\1{name}は"),
        # 「私は」→「{name}は」（文頭の定型部分）
        (r"(あなたと同じ\d+歳のとき、)私は", r"\1{name}は"),
    ]

    # Phase 2: 文中の「私は/私の/私が」パターン（引用外のみ）
    PHASE2_PATTERNS = [
        (r"私は", "{name}は"),
        (r"私の", "{name}の"),
        (r"私が", "{name}が"),
    ]

    # 引用パターン（保護対象）
    QUOTE_PATTERNS = [
        r"「[^」]*」",
        r"『[^』]*』",
        r"（[^）]*）",
    ]

    def __init__(self, csv_path: Path = MASTER_CSV, phase2: bool = False):
        self.csv_path = csv_path
        self.stats = FixStats()
        self.phase2 = phase2

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
        """「私は」パターンを検出（Phase 1: 定型形式違反）"""
        # パターンA: 「私は」で始まる
        if re.match(self.DETECT_PATTERN_A, text):
            return True
        # パターンB: 「私[名前]は」で始まる
        if re.match(self.DETECT_PATTERN_B, text):
            return True
        return False

    def detect_phase2(self, text: str) -> bool:
        """「私は/私の/私が」パターンを検出（Phase 2: 引用外）"""
        # 引用を保護
        protected, _ = self._protect_quotes(text)

        # 保護後のテキストで「私は/私の/私が」を検索
        for pattern, _ in self.PHASE2_PATTERNS:
            if re.search(pattern, protected):
                return True
        return False

    def fix_text(self, text: str, person_name: str) -> tuple[str, list[str]]:
        """テキストを修正（Phase 1）"""
        if not text or not person_name:
            return text, []

        changes = []
        fixed = text

        for pattern, replacement in self.REPLACE_PATTERNS:
            # {name}を実際の人物名に置換
            actual_replacement = replacement.replace("{name}", person_name)

            # マッチを検索
            matches = re.findall(pattern, fixed)
            if matches:
                # 変更を記録
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match else ""
                    if match:
                        original = re.search(pattern, fixed)
                        if original:
                            changes.append(
                                f"{original.group(0)} → {re.sub(pattern, actual_replacement, original.group(0))}"
                            )

                # 置換実行
                fixed = re.sub(pattern, actual_replacement, fixed)

        return fixed, changes

    def fix_text_phase2(self, text: str, person_name: str) -> tuple[str, list[str]]:
        """テキストを修正（Phase 2: 引用外の「私は/私の/私が」）"""
        if not text or not person_name:
            return text, []

        changes = []

        # 1. 引用を保護
        protected, quotes = self._protect_quotes(text)

        # 2. 保護済みテキスト内で「私は/私の/私が」を置換
        for pattern, replacement in self.PHASE2_PATTERNS:
            actual_replacement = replacement.replace("{name}", person_name)

            # マッチを検索
            matches = re.findall(pattern, protected)
            if matches:
                for match in matches:
                    changes.append(f"{match} → {actual_replacement}")

                # 置換実行
                protected = re.sub(pattern, actual_replacement, protected)

        # 3. 引用を復元
        fixed = self._restore_quotes(protected, quotes)

        return fixed, changes

    def scan(self) -> list[dict]:
        """全エピソードをスキャン"""
        df = pd.read_csv(self.csv_path, encoding="utf-8-sig", low_memory=False)
        self.stats.total_episodes = len(df)

        detected = []

        for idx, row in df.iterrows():
            text = str(row.get("episode_text", "") or "")
            if self.detect(text):
                self.stats.detected += 1
                detected.append(
                    {
                        "episode_id": row.get("episode_id", ""),
                        "person_name": row.get("person_name", ""),
                        "age": row.get("age", ""),
                        "text_preview": text[:150],
                    }
                )

        return detected

    def execute(self, dry_run: bool = True) -> list[FixResult]:
        """修正を実行"""
        # バックアップ作成
        if not dry_run:
            self._create_backup()

        df = pd.read_csv(self.csv_path, encoding="utf-8-sig", low_memory=False)
        self.stats.total_episodes = len(df)

        results = []

        for idx, row in df.iterrows():
            text = str(row.get("episode_text", "") or "")
            episode_id = row.get("episode_id", "")
            person_name = str(row.get("person_name", "") or "")
            age = row.get("age", 0)

            # Phase 2モードの場合は detect_phase2 を使用
            if self.phase2:
                if not self.detect_phase2(text):
                    continue
            else:
                if not self.detect(text):
                    continue

            self.stats.detected += 1

            if not person_name:
                self.stats.errors += 1
                continue

            # Phase 2モードの場合は fix_text_phase2 を使用
            if self.phase2:
                fixed_text, changes = self.fix_text_phase2(text, person_name)
            else:
                fixed_text, changes = self.fix_text(text, person_name)

            if changes:
                result = FixResult(
                    episode_id=episode_id,
                    person_name=person_name,
                    age=int(age) if pd.notna(age) else 0,
                    original_text=text,
                    fixed_text=fixed_text,
                    changes=changes,
                )
                results.append(result)

                if not dry_run:
                    df.at[idx, "episode_text"] = fixed_text
                    self.stats.fixed += 1
            else:
                self.stats.skipped += 1

        # 保存
        if not dry_run:
            df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")

        return results

    def _create_backup(self):
        """バックアップ作成"""
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"MASTER_BACKUP_watashi_{timestamp}.csv"
        shutil.copy(self.csv_path, backup_path)
        print(f"バックアップ作成: {backup_path}")
        return backup_path


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="「私は」パターン修正")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード")
    parser.add_argument("--execute", action="store_true", help="実行モード")
    parser.add_argument("--scan-only", action="store_true", help="検出のみ")
    parser.add_argument("--phase2", action="store_true", help="Phase 2モード（文中の私は/私の/私が）")
    args = parser.parse_args()

    phase_label = "Phase 2" if args.phase2 else "Phase 1"
    print(f"=== 「私は」パターン修正 ({phase_label}) ===\n")

    fixer = WatashiPatternFixer(phase2=args.phase2)

    if args.scan_only:
        # スキャンのみ
        print("スキャン中...")
        detected = fixer.scan()

        print(f"\n総エピソード: {fixer.stats.total_episodes}")
        print(f"「私は」パターン検出: {len(detected)}件")

        if detected:
            print("\nサンプル（最大10件）:")
            for ep in detected[:10]:
                print(f"  {ep['episode_id']} ({ep['person_name']}, {ep['age']}歳)")
                print(f"    {ep['text_preview'][:80]}...")

    elif args.execute:
        # 実行モード
        print("修正実行中...")
        results = fixer.execute(dry_run=False)

        print("\n修正完了:")
        print(f"  検出: {fixer.stats.detected}件")
        print(f"  修正: {fixer.stats.fixed}件")
        print(f"  スキップ: {fixer.stats.skipped}件")
        print(f"  エラー: {fixer.stats.errors}件")

        # ログ保存
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOGS_DIR / f"watashi_fix_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_data = {
            "stats": {
                "total": fixer.stats.total_episodes,
                "detected": fixer.stats.detected,
                "fixed": fixer.stats.fixed,
                "skipped": fixer.stats.skipped,
                "errors": fixer.stats.errors,
            },
            "samples": [
                {
                    "episode_id": r.episode_id,
                    "person_name": r.person_name,
                    "changes": r.changes[:5],
                }
                for r in results[:50]
            ],
        }
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        print(f"\nログ保存: {log_path}")

    else:
        # デフォルト: dry-run
        print("ドライランモード")
        print("シミュレーション中...")
        results = fixer.execute(dry_run=True)

        print("\n結果（dry-run）:")
        print(f"  検出: {fixer.stats.detected}件")
        print(f"  修正予定: {len(results)}件")
        print(f"  スキップ: {fixer.stats.skipped}件")

        if results:
            print("\n変更サンプル（最大5件）:")
            for r in results[:5]:
                print(f"\n  {r.episode_id} ({r.person_name}, {r.age}歳)")
                print(f"    変更前: {r.original_text[:80]}...")
                print(f"    変更後: {r.fixed_text[:80]}...")
                print(f"    変更点: {r.changes[:3]}")

        print("\n実行するには: python scripts/validation/fix_watashi_pattern.py --execute")


if __name__ == "__main__":
    main()
