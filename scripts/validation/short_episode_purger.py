#!/usr/bin/env python3
"""
ShortEpisodePurger - 短文・破損エピソード削除CLI

短すぎるエピソードや破損したエピソードを検出・削除するツール。
HallucinationPurger と同様の構造でスキャン、削除実行、復元の3機能を提供。

## 削除基準

1. **60文字未満** - 即時削除（内容が根本的に不足）
2. **破損パターン含有 AND 80文字未満**:
   - 「できない。」で終わる
   - 「続くる」等の文法エラー
   - 導入部のみで終わる（30文字以内で終わる）

## 使用方法

### スキャン（ドライラン）
    python scripts/validation/short_episode_purger.py --scan
    python scripts/validation/short_episode_purger.py --scan --limit 100

### 削除実行
    python scripts/validation/short_episode_purger.py --execute \\
        --candidates-file src/reports/short_episode_candidates_20260204.json

### 復元
    python scripts/validation/short_episode_purger.py --restore \\
        --backup-file preserved/backups/purge/pre_purge_20260204.csv

Author: EPUP Validation Team
Date: 2026-02-04
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.physical_deleter import PhysicalDeleter

# =============================================================================
# パス設定
# =============================================================================

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "src/reports"

# =============================================================================
# 定数
# =============================================================================

# 短文閾値（60文字未満は即削除）
MIN_CHARS_IMMEDIATE = 60

# 破損パターン閾値（破損パターン含有かつ80文字未満で削除）
MIN_CHARS_BROKEN = 80

# 破損パターン（正規表現）
BROKEN_PATTERNS = [
    (r"できない。$", "破損した文末: 「できない。」で終わる"),
    (r"続くる", "文法エラー: 「続くる」"),
    (r"^あなたと同じ\d+歳のとき、[^。]{0,30}$", "導入部のみで終わる（30文字以内で終わる）"),
]

# =============================================================================
# ロギング設定
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# データクラス
# =============================================================================


@dataclass
class ScanResult:
    """スキャン結果"""

    scan_timestamp: str
    total_scanned: int
    candidates_count: int
    by_reason: dict[str, int]
    candidates: list[dict]
    output_path: Optional[Path] = None

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "scan_timestamp": self.scan_timestamp,
            "total_scanned": self.total_scanned,
            "candidates_count": self.candidates_count,
            "by_reason": self.by_reason,
            "candidates": self.candidates,
        }


@dataclass
class ExecutionResult:
    """実行結果"""

    success: bool
    execution_timestamp: str
    backup_path: Optional[Path]
    deleted_count: int
    failed_count: int
    deleted_episodes: list[dict] = field(default_factory=list)
    error_message: str = ""


# =============================================================================
# ShortEpisodePurger クラス
# =============================================================================


class ShortEpisodePurger:
    """
    短文・破損エピソード削除クラス

    短すぎるエピソードや破損パターンを含むエピソードを検出し、
    PhysicalDeleter で削除を実行する。
    """

    def __init__(self, master_csv: Path = MASTER_CSV):
        """
        初期化

        Args:
            master_csv: マスターCSVのパス
        """
        self.master_csv = master_csv
        self.deleter = PhysicalDeleter(master_csv=master_csv)
        self.reports_dir = REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # 破損パターンをコンパイル
        self.broken_patterns = [(re.compile(pattern), description) for pattern, description in BROKEN_PATTERNS]

        logger.info("ShortEpisodePurger initialized")
        logger.info(f"  Master CSV: {self.master_csv}")
        logger.info(f"  Reports dir: {self.reports_dir}")

    def _check_broken_pattern(self, text: str) -> Optional[str]:
        """
        破損パターンをチェック

        Args:
            text: エピソードテキスト

        Returns:
            マッチした場合は理由を返す、マッチしない場合はNone
        """
        for pattern, description in self.broken_patterns:
            if pattern.search(text):
                return description
        return None

    def _analyze_episode(self, row: pd.Series) -> Optional[dict]:
        """
        エピソードを解析して削除候補かどうか判定

        Args:
            row: CSVの1行（pandas Series）

        Returns:
            削除候補の場合は詳細辞書、そうでなければNone
        """
        episode_id = str(row.get("episode_id", ""))
        episode_text = str(row.get("episode_text", ""))
        person_name = str(row.get("person_name", ""))
        age = row.get("age", "")

        # 空チェック
        if not episode_text or episode_text == "nan":
            return {
                "episode_id": episode_id,
                "person_name": person_name,
                "age": age,
                "char_count": 0,
                "reason": "空のエピソード",
                "episode_preview": "",
            }

        char_count = len(episode_text)

        # 1. 60文字未満は即削除
        if char_count < MIN_CHARS_IMMEDIATE:
            return {
                "episode_id": episode_id,
                "person_name": person_name,
                "age": age,
                "char_count": char_count,
                "reason": f"文字数不足（{char_count}文字 < {MIN_CHARS_IMMEDIATE}文字）",
                "episode_preview": episode_text[:50],
            }

        # 2. 破損パターン含有かつ80文字未満
        broken_reason = self._check_broken_pattern(episode_text)
        if broken_reason and char_count < MIN_CHARS_BROKEN:
            return {
                "episode_id": episode_id,
                "person_name": person_name,
                "age": age,
                "char_count": char_count,
                "reason": f"破損パターン + 短文（{char_count}文字）: {broken_reason}",
                "episode_preview": episode_text[:50],
            }

        return None

    def scan(
        self,
        limit: int = 0,
        output_json: bool = True,
    ) -> ScanResult:
        """
        削除候補をスキャン

        Args:
            limit: 処理件数上限（0=無制限）
            output_json: JSONファイルを出力するか

        Returns:
            ScanResult
        """
        scan_timestamp = datetime.now().isoformat()
        logger.info(f"Scan started at {scan_timestamp}")

        # CSVを読み込み
        if not self.master_csv.exists():
            logger.error(f"Master CSV not found: {self.master_csv}")
            return ScanResult(
                scan_timestamp=scan_timestamp,
                total_scanned=0,
                candidates_count=0,
                by_reason={},
                candidates=[],
            )

        df = pd.read_csv(self.master_csv, encoding="utf-8-sig")
        total_rows = len(df)

        if limit > 0:
            df = df.head(limit)

        total_scanned = len(df)
        logger.info(f"Scanning {total_scanned} episodes (total in CSV: {total_rows})")

        # 削除候補を収集
        candidates: list[dict] = []
        by_reason: dict[str, int] = {}

        for i, (_, row) in enumerate(df.iterrows()):
            result = self._analyze_episode(row)
            if result:
                candidates.append(result)

                # 理由別集計
                reason_key = result["reason"].split(":")[0].strip()
                by_reason[reason_key] = by_reason.get(reason_key, 0) + 1

            # 進捗表示（1000件ごと）
            if (i + 1) % 1000 == 0:
                print_progress_bar(
                    i + 1,
                    total_scanned,
                    prefix="スキャン中",
                    suffix="",
                )

        # 最終進捗
        print_progress_bar(total_scanned, total_scanned, prefix="スキャン中", suffix="完了")
        print()

        candidates_count = len(candidates)
        logger.info(f"Scan completed: {candidates_count} candidates found")

        # 結果オブジェクト作成
        scan_result = ScanResult(
            scan_timestamp=scan_timestamp,
            total_scanned=total_scanned,
            candidates_count=candidates_count,
            by_reason=by_reason,
            candidates=candidates,
        )

        # JSON出力
        if output_json and candidates_count > 0:
            date_str = datetime.now().strftime("%Y%m%d")
            output_path = self.reports_dir / f"short_episode_candidates_{date_str}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(scan_result.to_dict(), f, ensure_ascii=False, indent=2)
            scan_result.output_path = output_path
            logger.info(f"Candidates saved to: {output_path}")

        return scan_result

    def execute(
        self,
        candidates_file: Path,
        force: bool = False,
    ) -> ExecutionResult:
        """
        候補ファイルから削除を実行

        Args:
            candidates_file: 削除候補JSONファイルのパス
            force: 確認プロンプトをスキップするか

        Returns:
            ExecutionResult
        """
        execution_timestamp = datetime.now().isoformat()
        logger.info(f"Execution started at {execution_timestamp}")

        # 候補ファイルを読み込み
        if not candidates_file.exists():
            error_msg = f"Candidates file not found: {candidates_file}"
            logger.error(error_msg)
            return ExecutionResult(
                success=False,
                execution_timestamp=execution_timestamp,
                backup_path=None,
                deleted_count=0,
                failed_count=0,
                error_message=error_msg,
            )

        with open(candidates_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        candidates = data.get("candidates", [])
        if not candidates:
            logger.warning("No candidates in file")
            return ExecutionResult(
                success=True,
                execution_timestamp=execution_timestamp,
                backup_path=None,
                deleted_count=0,
                failed_count=0,
            )

        # 削除対象のエピソードIDを抽出
        episode_ids = [c["episode_id"] for c in candidates if "episode_id" in c]
        logger.info(f"Candidates to delete: {len(episode_ids)}")

        # 確認プロンプト（forceでない場合）
        if not force:
            print(f"\n削除対象: {len(episode_ids)} 件")
            print("続行しますか? (y/N): ", end="")
            response = input().strip().lower()
            if response != "y":
                logger.info("Operation cancelled by user")
                return ExecutionResult(
                    success=False,
                    execution_timestamp=execution_timestamp,
                    backup_path=None,
                    deleted_count=0,
                    failed_count=0,
                    error_message="Operation cancelled by user",
                )

        # 削除実行
        deletion_result = self.deleter.delete_episodes(episode_ids, dry_run=False)

        if not deletion_result.success:
            return ExecutionResult(
                success=False,
                execution_timestamp=execution_timestamp,
                backup_path=deletion_result.backup_path,
                deleted_count=0,
                failed_count=len(episode_ids),
                error_message=deletion_result.error_message,
            )

        # 削除されたエピソードの詳細を取得
        deleted_episodes = []
        deleted_ids_set = set(deletion_result.deleted_episodes)
        for c in candidates:
            if c.get("episode_id") in deleted_ids_set:
                deleted_episodes.append(c)

        failed_count = len(episode_ids) - deletion_result.deleted_count

        # Markdownレポートを出力
        self._write_execution_report(
            execution_timestamp=execution_timestamp,
            backup_path=deletion_result.backup_path,
            total_candidates=len(episode_ids),
            deleted_count=deletion_result.deleted_count,
            failed_count=failed_count,
            deleted_episodes=deleted_episodes,
        )

        return ExecutionResult(
            success=True,
            execution_timestamp=execution_timestamp,
            backup_path=deletion_result.backup_path,
            deleted_count=deletion_result.deleted_count,
            failed_count=failed_count,
            deleted_episodes=deleted_episodes,
        )

    def _write_execution_report(
        self,
        execution_timestamp: str,
        backup_path: Path,
        total_candidates: int,
        deleted_count: int,
        failed_count: int,
        deleted_episodes: list[dict],
    ) -> Path:
        """
        実行レポートをMarkdown形式で出力

        Args:
            execution_timestamp: 実行タイムスタンプ
            backup_path: バックアップファイルパス
            total_candidates: 削除対象総数
            deleted_count: 削除成功件数
            failed_count: 削除失敗件数
            deleted_episodes: 削除済みエピソードリスト

        Returns:
            レポートファイルのパス
        """
        date_str = datetime.now().strftime("%Y%m%d")
        report_path = self.reports_dir / f"short_episode_execution_{date_str}.md"

        lines = [
            "# 短文エピソード削除実行レポート",
            "",
            "## 実行情報",
            f"- 実行日時: {execution_timestamp}",
            f"- バックアップ: {backup_path}",
            "",
            "## 削除結果",
            f"- 削除対象: {total_candidates}件",
            f"- 削除成功: {deleted_count}件",
            f"- 削除失敗: {failed_count}件",
            "",
            "## 削除済みエピソード一覧",
            "| episode_id | person_name | age | char_count | reason |",
            "|-----------|-------------|-----|------------|--------|",
        ]

        for ep in deleted_episodes:
            episode_id = ep.get("episode_id", "")
            person_name = ep.get("person_name", "")
            age = ep.get("age", "")
            char_count = ep.get("char_count", "")
            reason = ep.get("reason", "")[:30]
            lines.append(f"| {episode_id} | {person_name} | {age} | {char_count} | {reason} |")

        content = "\n".join(lines)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Execution report saved to: {report_path}")
        return report_path

    def restore(self, backup_file: Path) -> bool:
        """
        バックアップから復元

        Args:
            backup_file: 復元するバックアップファイルのパス

        Returns:
            成功した場合True
        """
        logger.info(f"Restoring from: {backup_file}")
        return self.deleter.restore_from_backup(backup_file)


# =============================================================================
# プログレスバー表示用関数
# =============================================================================


def print_progress_bar(
    current: int,
    total: int,
    prefix: str = "",
    suffix: str = "",
    length: int = 50,
) -> None:
    """
    プログレスバーを表示

    Args:
        current: 現在の進捗
        total: 総数
        prefix: プレフィックス
        suffix: サフィックス
        length: バーの長さ
    """
    if total == 0:
        return

    percent = current / total
    filled = int(length * percent)
    bar = "█" * filled + "░" * (length - filled)
    print(f"\r{prefix} |{bar}| {current}/{total} {suffix}", end="", flush=True)


def print_summary_box(scan_result: ScanResult) -> None:
    """
    サマリーボックスを表示

    Args:
        scan_result: スキャン結果
    """
    print()
    print("╔" + "═" * 62 + "╗")
    print("║" + "  短文エピソード候補スキャン結果".center(52) + "║")
    print("╚" + "═" * 62 + "╝")
    print()
    print(f"  📅 スキャン日時: {scan_result.scan_timestamp}")
    print()
    print("  ┌────────────────────────────────────────────────────────┐")
    filled = int(50 * scan_result.candidates_count / max(scan_result.total_scanned, 1))
    bar = "█" * filled + "░" * (50 - filled)
    print(f"  │  {bar}  │")
    print("  └────────────────────────────────────────────────────────┘")
    print()
    print("  ┌─────────────────┬─────────────────┬─────────────────┐")
    print("  │    📊 総数      │   ❌ 候補       │   ✅ 合格       │")
    print("  ├─────────────────┼─────────────────┼─────────────────┤")
    passed = scan_result.total_scanned - scan_result.candidates_count
    print(
        f"  │  {scan_result.total_scanned:>8} 件    │  {scan_result.candidates_count:>8} 件    │  {passed:>8} 件    │"
    )
    print("  └─────────────────┴─────────────────┴─────────────────┘")
    print()

    # 理由別
    print("  【理由別】")
    for reason, count in sorted(scan_result.by_reason.items(), key=lambda x: -x[1]):
        print(f"    {reason}: {count}件")

    print()


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """CLI エントリーポイント"""
    parser = argparse.ArgumentParser(
        description="ShortEpisodePurger - 短文・破損エピソード削除CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # スキャン（ドライラン）
  python scripts/validation/short_episode_purger.py --scan
  python scripts/validation/short_episode_purger.py --scan --limit 100

  # 削除実行
  python scripts/validation/short_episode_purger.py --execute \\
    --candidates-file src/reports/short_episode_candidates_20260204.json

  # 復元
  python scripts/validation/short_episode_purger.py --restore \\
    --backup-file preserved/backups/purge/pre_purge_20260204.csv
        """,
    )

    # モード選択（排他的）
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--scan",
        action="store_true",
        help="削除候補をスキャンしてJSONレポートを出力",
    )
    mode_group.add_argument(
        "--execute",
        action="store_true",
        help="候補ファイルから削除を実行",
    )
    mode_group.add_argument(
        "--restore",
        action="store_true",
        help="バックアップから復元",
    )

    # スキャンオプション
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="スキャン件数上限（0=無制限）",
    )

    # 実行オプション
    parser.add_argument(
        "--candidates-file",
        type=Path,
        help="削除候補JSONファイルのパス",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="確認プロンプトをスキップ",
    )

    # 復元オプション
    parser.add_argument(
        "--backup-file",
        type=Path,
        help="復元するバックアップファイルのパス",
    )

    # 共通オプション
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細ログ出力",
    )

    args = parser.parse_args()

    # ログ設定
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ヘッダー表示
    print("=" * 70)
    print("ShortEpisodePurger - 短文・破損エピソード削除CLI")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Purger初期化
    purger = ShortEpisodePurger()

    # モードに応じた処理
    if args.scan:
        # スキャンモード
        print("\n[スキャンモード]")
        print(f"  制限: {args.limit if args.limit > 0 else '無制限'}")
        print()

        scan_result = purger.scan(
            limit=args.limit,
            output_json=True,
        )

        # サマリー表示
        print_summary_box(scan_result)

        # 候補上位10件を表示
        if scan_result.candidates:
            print("【削除候補（上位10件）】")
            for i, c in enumerate(scan_result.candidates[:10], 1):
                print(f"  [{i}] {c['episode_id']} | {c['person_name']} ({c['age']}歳) | {c['char_count']}文字")
                reason = c.get("reason", "")[:60]
                print(f"      理由: {reason}")
                preview = c.get("episode_preview", "")[:40]
                if preview:
                    print(f"      内容: {preview}...")
            print()

        # 出力ファイル情報
        if scan_result.output_path:
            print(f"📁 候補ファイル: {scan_result.output_path}")
            print()
            print("削除を実行するには:")
            print("  python scripts/validation/short_episode_purger.py --execute \\")
            print(f"    --candidates-file {scan_result.output_path}")

        return 0

    elif args.execute:
        # 実行モード
        if not args.candidates_file:
            print("エラー: --candidates-file が必要です")
            return 1

        print("\n[削除実行モード]")
        print(f"  候補ファイル: {args.candidates_file}")
        print(f"  強制実行: {args.force}")
        print()

        exec_result = purger.execute(
            candidates_file=args.candidates_file,
            force=args.force,
        )

        # 結果表示
        print()
        print("=" * 70)
        print("実行結果")
        print("=" * 70)
        print(f"  成功: {exec_result.success}")
        print(f"  削除成功: {exec_result.deleted_count}件")
        print(f"  削除失敗: {exec_result.failed_count}件")
        if exec_result.backup_path:
            print(f"  バックアップ: {exec_result.backup_path}")
        if exec_result.error_message:
            print(f"  エラー: {exec_result.error_message}")

        return 0 if exec_result.success else 1

    elif args.restore:
        # 復元モード
        if not args.backup_file:
            print("エラー: --backup-file が必要です")
            return 1

        print("\n[復元モード]")
        print(f"  バックアップファイル: {args.backup_file}")
        print()

        success = purger.restore(args.backup_file)

        # 結果表示
        print()
        print("=" * 70)
        print("復元結果")
        print("=" * 70)
        if success:
            print("  ✅ 復元成功")
        else:
            print("  ❌ 復元失敗")

        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
