#!/usr/bin/env python3
"""
エピソード品質違反修正スクリプト

丁寧語・「私は」パターンをテキスト変換で自動修正。
再生成よりも効率的にデータ品質を改善。

Usage:
    python scripts/fix/fix_episode_quality_violations.py --dry-run
    python scripts/fix/fix_episode_quality_violations.py --execute
"""

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backup"


class EpisodeQualityFixer:
    """エピソード品質違反修正"""

    # 丁寧語→常体変換マップ
    POLITE_TO_PLAIN = [
        # でした/ました → だった/た（過去形）
        (r"でした([。、])", r"だった\1"),
        (r"ました([。、])", r"た\1"),
        # です/ます → だ/る（現在形）- 文脈注意
        (r"です([。、])", r"だ\1"),
        (r"ます([。、])", r"る\1"),
        # ません → ない（否定）
        (r"ません([。、])", r"ない\1"),
        # でしょう → だろう（推量）
        (r"でしょう([。、])", r"だろう\1"),
        # 連用形パターン
        (r"しています([。、])", r"している\1"),
        (r"していました([。、])", r"していた\1"),
        (r"されています([。、])", r"されている\1"),
        (r"されていました([。、])", r"されていた\1"),
        (r"なっています([。、])", r"なっている\1"),
        (r"なっていました([。、])", r"なっていた\1"),
    ]

    # 引用パターン（変換対象外）
    QUOTE_PATTERNS = [
        r"「[^」]*」",
        r"『[^』]*』",
        r"（[^）]*）",
    ]

    def __init__(self, csv_path: Path = MASTER_CSV):
        self.csv_path = csv_path
        self.episodes = []
        self.stats = {
            "total": 0,
            "polite_fixed": 0,
            "watashi_fixed": 0,
            "unchanged": 0,
        }

    def load_episodes(self) -> int:
        """CSVを読み込む"""
        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.episodes = list(reader)
            self.fieldnames = reader.fieldnames
        self.stats["total"] = len(self.episodes)
        return len(self.episodes)

    def _extract_quotes(self, text: str) -> tuple[str, list[tuple[str, str]]]:
        """引用を一時プレースホルダーに置換"""
        placeholders = []
        for i, pattern in enumerate(self.QUOTE_PATTERNS):
            for j, match in enumerate(re.finditer(pattern, text)):
                placeholder = f"__QUOTE_{i}_{j}__"
                placeholders.append((placeholder, match.group()))
                text = text.replace(match.group(), placeholder, 1)
        return text, placeholders

    def _restore_quotes(self, text: str, placeholders: list[tuple[str, str]]) -> str:
        """プレースホルダーを引用に復元"""
        for placeholder, original in placeholders:
            text = text.replace(placeholder, original)
        return text

    def fix_polite_forms(self, text: str) -> tuple[str, int]:
        """丁寧語を常体に変換"""
        # 引用を保護
        text, placeholders = self._extract_quotes(text)
        fix_count = 0

        for pattern, replacement in self.POLITE_TO_PLAIN:
            new_text, n = re.subn(pattern, replacement, text)
            if n > 0:
                fix_count += n
                text = new_text

        # 引用を復元
        text = self._restore_quotes(text, placeholders)
        return text, fix_count

    def fix_watashi_pattern(self, text: str, person_name: str) -> tuple[str, int]:
        """「私は/私の/私が」を三人称に変換"""
        fix_count = 0

        # 人物名が空の場合は「彼」を使用
        replacement_name = person_name if person_name else "彼"

        # 引用を挟んだパターン（私『...』は → 人物名『...』は）を先に処理
        # 引用保護せずに直接置換
        quote_between_patterns = [
            (r"私(『[^』]*』)は", rf"{replacement_name}\1は"),
            (r"私(「[^」]*」)は", rf"{replacement_name}\1は"),
            (r"私(『[^』]*』)の", rf"{replacement_name}\1の"),
            (r"私(「[^」]*」)の", rf"{replacement_name}\1の"),
            (r"私(『[^』]*』)が", rf"{replacement_name}\1が"),
            (r"私(「[^」]*」)が", rf"{replacement_name}\1が"),
        ]

        for pattern, replacement in quote_between_patterns:
            new_text, n = re.subn(pattern, replacement, text)
            if n > 0:
                fix_count += n
                text = new_text

        # 引用を保護して基本パターンを処理
        text, placeholders = self._extract_quotes(text)

        # 私は → 人物名は（複数パターンに対応）
        watashi_patterns = [
            # 基本パターン
            (r"私は", f"{replacement_name}は"),
            (r"私の", f"{replacement_name}の"),
            (r"私が", f"{replacement_name}が"),
            (r"私を", f"{replacement_name}を"),
            (r"私に", f"{replacement_name}に"),
            (r"私も", f"{replacement_name}も"),
            # 複合パターン（された私は等）
            (r"された私は", f"された{replacement_name}は"),
            (r"した私は", f"した{replacement_name}は"),
        ]

        for pattern, replacement in watashi_patterns:
            new_text, n = re.subn(pattern, replacement, text)
            if n > 0:
                fix_count += n
                text = new_text

        # 引用を復元
        text = self._restore_quotes(text, placeholders)
        return text, fix_count

    def fix_episode(self, episode: dict) -> tuple[dict, bool, dict]:
        """1エピソードを修正"""
        text = episode.get("episode_text", "")
        person_name = episode.get("person_name", "")
        changes = {"polite": 0, "watashi": 0}

        # 丁寧語修正
        text, polite_count = self.fix_polite_forms(text)
        changes["polite"] = polite_count

        # 私は修正
        text, watashi_count = self.fix_watashi_pattern(text, person_name)
        changes["watashi"] = watashi_count

        modified = polite_count > 0 or watashi_count > 0
        if modified:
            episode["episode_text"] = text

        return episode, modified, changes

    def fix_all(self, dry_run: bool = True) -> dict:
        """全エピソードを修正"""
        modified_episodes = []
        samples = []

        for ep in self.episodes:
            original_text = ep.get("episode_text", "")
            fixed_ep, modified, changes = self.fix_episode(ep.copy())

            if modified:
                if changes["polite"] > 0:
                    self.stats["polite_fixed"] += 1
                if changes["watashi"] > 0:
                    self.stats["watashi_fixed"] += 1

                modified_episodes.append(fixed_ep)

                # サンプル収集（最大10件）
                if len(samples) < 10:
                    samples.append(
                        {
                            "episode_id": ep.get("episode_id"),
                            "person_name": ep.get("person_name"),
                            "polite_fixes": changes["polite"],
                            "watashi_fixes": changes["watashi"],
                            "before": original_text[:100] + "..." if len(original_text) > 100 else original_text,
                            "after": fixed_ep["episode_text"][:100] + "..."
                            if len(fixed_ep["episode_text"]) > 100
                            else fixed_ep["episode_text"],
                        }
                    )
            else:
                self.stats["unchanged"] += 1
                modified_episodes.append(ep)

        if not dry_run:
            self._save_episodes(modified_episodes)

        return {
            "stats": self.stats,
            "samples": samples,
            "dry_run": dry_run,
        }

    def _save_episodes(self, episodes: list[dict]):
        """修正済みエピソードを保存"""
        # バックアップ作成
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"MASTER_EPISODES_pre_quality_fix_{timestamp}.csv"

        # 現在のファイルをバックアップ
        import shutil

        shutil.copy2(self.csv_path, backup_path)
        print(f"バックアップ作成: {backup_path}")

        # 修正済みファイルを保存
        with open(self.csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(episodes)

        print(f"修正完了: {self.csv_path}")


def main():
    parser = argparse.ArgumentParser(description="エピソード品質違反修正")
    parser.add_argument("--dry-run", action="store_true", help="変更をシミュレート（デフォルト）")
    parser.add_argument("--execute", action="store_true", help="実際に変更を適用")
    parser.add_argument("--csv", type=str, default=str(MASTER_CSV), help="対象CSVパス")

    args = parser.parse_args()
    dry_run = not args.execute

    print("=" * 60)
    print("エピソード品質違反修正")
    print("=" * 60)
    print(f"モード: {'DRY-RUN（シミュレーション）' if dry_run else '⚠️ 実行モード'}")
    print(f"対象: {args.csv}")
    print()

    fixer = EpisodeQualityFixer(csv_path=Path(args.csv))
    count = fixer.load_episodes()
    print(f"ロード完了: {count}件")

    result = fixer.fix_all(dry_run=dry_run)

    print()
    print("=" * 60)
    print("修正結果")
    print("=" * 60)
    stats = result["stats"]
    print(f"  総エピソード数: {stats['total']}")
    print(f"  丁寧語修正: {stats['polite_fixed']}件")
    print(f"  「私は」修正: {stats['watashi_fixed']}件")
    print(f"  変更なし: {stats['unchanged']}件")

    if result["samples"]:
        print()
        print("サンプル変更:")
        for s in result["samples"][:5]:
            print(f"\n  [{s['episode_id']}] {s['person_name']}")
            print(f"    丁寧語修正: {s['polite_fixes']}箇所, 私は修正: {s['watashi_fixes']}箇所")
            print(f"    前: {s['before']}")
            print(f"    後: {s['after']}")

    if dry_run:
        print()
        print("💡 実際に修正するには --execute オプションを使用してください")

    return 0 if dry_run else (0 if stats["polite_fixed"] + stats["watashi_fixed"] > 0 else 1)


if __name__ == "__main__":
    sys.exit(main())
