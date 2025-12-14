#!/usr/bin/env python3
"""
EPUP 自動監視（Episode Update Pipeline - Auto Watch）

目的:
  エピソードDB（MASTER_EPISODES_CURRENT.csv 系）の更新を検知し、
  変更があったタイミングで「軽量EPUPチェック」を自動実行する。

方針:
  - まずはローカルで完結する軽量チェックを回す（LLM不要）
  - アラートが出た場合のみ、必要に応じて成果評価も回す（LLM不要）
  - 自動修正（--fix / --auto-fix 等）は絶対に勝手に実行しない

使い方:
  python scripts/epup_auto_watch.py --csv preserved/data/MASTER_EPISODES_CURRENT.csv
  python scripts/epup_auto_watch.py --mode weekly
  python scripts/epup_auto_watch.py --once

注意:
  watchdog が無い場合はポーリング監視に自動フォールバックします。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    _WATCHDOG_AVAILABLE = True
except Exception:
    # watchdog が無い環境でも使えるようにする（CIや最小環境向け）
    FileSystemEventHandler = object  # type: ignore
    Observer = None  # type: ignore
    _WATCHDOG_AVAILABLE = False


PROJECT_ROOT = Path(__file__).parent.parent


@dataclass(frozen=True)
class EpupRunResult:
    """EPUP自動チェック1回分の実行結果（最小情報）"""

    csv_path: Path
    check_report_path: Optional[Path]
    check_exit_code: int
    evaluation_report_path: Optional[Path]
    evaluation_exit_code: Optional[int]


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _resolve_csv_path(user_csv: Optional[str]) -> Path:
    """
    監視対象CSVパスを解決する。

    優先順位:
      1) ユーザー指定
      2) 既存ファイルがある候補を上から採用
      3) デフォルト（存在しない場合でも、監視したい意図として返す）
    """
    if user_csv:
        path = Path(user_csv)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    candidates = [
        PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv",
        PROJECT_ROOT / "preserved" / "MASTER_EPISODES_CURRENT.csv",
        PROJECT_ROOT / "MASTER_EPISODES_CURRENT.csv",
        PROJECT_ROOT / "data" / "MASTER_EPISODES_CURRENT.csv",
    ]

    for c in candidates:
        if c.exists():
            return c

    # 見つからない場合でも、最も標準的なパスを返す（あとで存在チェックする）
    return candidates[0]


def _wait_for_file_stable(path: Path, max_wait_seconds: int = 10, stable_window_seconds: float = 1.0) -> bool:
    """
    保存中の一時的な中途半端状態を避けるため、ファイルサイズが安定するまで待つ。
    """
    if not path.exists():
        return False

    start = time.time()
    last_size = -1
    last_change_time = time.time()

    while time.time() - start < max_wait_seconds:
        try:
            size = path.stat().st_size
        except OSError:
            time.sleep(0.2)
            continue

        if size != last_size:
            last_size = size
            last_change_time = time.time()
        else:
            if time.time() - last_change_time >= stable_window_seconds:
                return True

        time.sleep(0.2)

    # タイムアウトしても、とりあえず続行できることが多いので True 扱いにする
    return True


def _run_subprocess(args: list[str], timeout_seconds: int, quiet: bool) -> tuple[int, str]:
    """
    サブプロセス実行（エラー時も出力を保持する）
    """
    try:
        result = subprocess.run(
            args,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if not quiet and output.strip():
            print(output.rstrip())
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:
        return 1, f"exception: {e}"


def run_epup_checks_once(
    csv_path: Path,
    mode: str,
    evaluate_on_alert: bool,
    evaluate_always: bool,
    quiet: bool,
    report_dir: Path,
) -> EpupRunResult:
    """
    EPUPチェックを1回実行（監視トリガー/手動トリガー共通）
    """
    if not csv_path.exists():
        if not quiet:
            print(f"❌ CSVが見つかりません: {csv_path}")
            print("   監視対象のパスを --csv で指定してください。")
        return EpupRunResult(
            csv_path=csv_path,
            check_report_path=None,
            check_exit_code=2,
            evaluation_report_path=None,
            evaluation_exit_code=None,
        )

    report_dir.mkdir(parents=True, exist_ok=True)

    # 1) 単一マスター整合性チェック（失敗しても続行）
    if (PROJECT_ROOT / "scripts" / "check_single_master.py").exists():
        if not quiet:
            print("🔍 check_single_master.py 実行...")
        _run_subprocess([sys.executable, "scripts/check_single_master.py"], timeout_seconds=60, quiet=quiet)

    # 2) 軽量/完全チェック
    if not quiet:
        print(f"📊 scheduled_epup_check.py 実行... (mode={mode})")
    check_report_path = report_dir / f"epup_auto_{mode}_{_now_stamp()}.json"

    check_args = [
        sys.executable,
        "scripts/scheduled_epup_check.py",
        "--csv",
        str(csv_path),
        "--output",
        str(check_report_path),
    ]
    if mode == "weekly":
        check_args.insert(2, "--weekly")
    else:
        check_args.insert(2, "--daily")
    if quiet:
        check_args.append("--quiet")

    check_exit_code, _ = _run_subprocess(check_args, timeout_seconds=300, quiet=quiet)

    # 3) 成果評価（必要時のみ）
    should_eval = evaluate_always or (evaluate_on_alert and check_exit_code != 0)
    evaluation_report_path: Optional[Path] = None
    evaluation_exit_code: Optional[int] = None

    if should_eval and (PROJECT_ROOT / "scripts" / "evaluate_epup_effectiveness.py").exists():
        if not quiet:
            print("📈 evaluate_epup_effectiveness.py 実行...")
        evaluation_report_path = report_dir / f"epup_evaluation_auto_{_now_stamp()}.json"
        eval_args = [
            sys.executable,
            "scripts/evaluate_epup_effectiveness.py",
            "--csv",
            str(csv_path),
            "--output",
            str(evaluation_report_path),
        ]
        evaluation_exit_code, _ = _run_subprocess(eval_args, timeout_seconds=600, quiet=quiet)

    if not quiet:
        print("✅ EPUP自動チェック完了")
        print(f"  - CSV: {csv_path}")
        print(f"  - check: exit={check_exit_code}, report={check_report_path}")
        if evaluation_report_path:
            print(f"  - eval : exit={evaluation_exit_code}, report={evaluation_report_path}")

    return EpupRunResult(
        csv_path=csv_path,
        check_report_path=check_report_path,
        check_exit_code=check_exit_code,
        evaluation_report_path=evaluation_report_path,
        evaluation_exit_code=evaluation_exit_code,
    )


class _SingleFileHandler(FileSystemEventHandler):
    """特定ファイル名のみ監視するハンドラ（デバウンス付き）"""

    def __init__(self, target_path: Path, cooldown_seconds: float, args: argparse.Namespace):
        self.target_path = target_path
        self.target_name = target_path.name
        self.cooldown_seconds = cooldown_seconds
        self.args = args
        self._last_run_at = 0.0

    def on_modified(self, event):  # type: ignore[override]
        if getattr(event, "is_directory", False):
            return

        try:
            changed = Path(getattr(event, "src_path", ""))
        except Exception:
            return

        if changed.name != self.target_name:
            return

        now = time.time()
        if now - self._last_run_at < self.cooldown_seconds:
            return

        self._last_run_at = now
        if not self.args.quiet:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{ts}] 📝 変更検知: {changed}")

        _wait_for_file_stable(self.target_path)
        run_epup_checks_once(
            csv_path=self.target_path,
            mode=self.args.mode,
            evaluate_on_alert=self.args.evaluate_on_alert,
            evaluate_always=self.args.evaluate_always,
            quiet=self.args.quiet,
            report_dir=Path(self.args.report_dir),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="EPUP自動監視（CSV更新でチェックを自動実行）")
    parser.add_argument("--csv", type=str, help="監視対象CSV（省略時は候補から自動選択）")
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily", help="実行するチェック種別")
    parser.add_argument(
        "--evaluate-on-alert",
        action="store_true",
        help="scheduled_epup_check が非0終了（アラート/失敗）の時だけ評価を追加実行",
    )
    parser.add_argument(
        "--evaluate-always",
        action="store_true",
        help="毎回 evaluate_epup_effectiveness を実行（重いので通常は非推奨）",
    )
    parser.add_argument("--cooldown", type=float, default=10.0, help="連続イベント抑制（秒）")
    parser.add_argument("--report-dir", type=str, default="reports", help="レポート出力先ディレクトリ")
    parser.add_argument("--once", action="store_true", help="監視せず1回だけ実行して終了")
    parser.add_argument("--poll", action="store_true", help="watchdog があってもポーリング監視を使う")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="ポーリング間隔（秒）")
    parser.add_argument("--quiet", action="store_true", help="出力を抑制")
    args = parser.parse_args()

    # evaluate_on_alert はデフォルト有効にしたいが、フラグ形式を維持するため、
    # evaluate_always が false の場合に限り暗黙で True にする（安全・低負荷）
    if not args.evaluate_always and not args.evaluate_on_alert:
        args.evaluate_on_alert = True

    csv_path = _resolve_csv_path(args.csv)

    # 1回だけ実行
    if args.once:
        run_epup_checks_once(
            csv_path=csv_path,
            mode=args.mode,
            evaluate_on_alert=args.evaluate_on_alert,
            evaluate_always=args.evaluate_always,
            quiet=args.quiet,
            report_dir=Path(args.report_dir),
        )
        return 0

    # 監視開始
    if not args.quiet:
        print("=" * 70)
        print("👁️  EPUP 自動監視 起動")
        print("=" * 70)
        print(f"  CSV: {csv_path}")
        print(f"  mode: {args.mode}")
        print(f"  cooldown: {args.cooldown}s")
        print(f"  evaluate_on_alert: {args.evaluate_on_alert}")
        print(f"  evaluate_always: {args.evaluate_always}")
        print(f"  reports: {args.report_dir}")
        print(f"  watchdog: {'available' if _WATCHDOG_AVAILABLE else 'not_installed'}")
        print("  (Ctrl+C で終了)")
        print()

    if _WATCHDOG_AVAILABLE and not args.poll:
        if Observer is None:
            # 型的にはありえないが、念のため
            print("⚠️ watchdogは利用できません（ObserverがNone）→ポーリングへフォールバック")
        else:
            handler = _SingleFileHandler(csv_path, cooldown_seconds=args.cooldown, args=args)
            observer = Observer()
            observer.schedule(handler, str(csv_path.parent), recursive=False)
            observer.start()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                if not args.quiet:
                    print("\n🛑 終了します")
            finally:
                observer.stop()
                observer.join()
            return 0

    # ポーリング監視（watchdog無し/強制poll）
    if not args.quiet:
        print("ℹ️ ポーリング監視を使用します")

    last_mtime = 0.0
    while True:
        try:
            if csv_path.exists():
                mtime = csv_path.stat().st_mtime
                if mtime > last_mtime:
                    last_mtime = mtime
                    if not args.quiet:
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"\n[{ts}] 📝 変更検知（poll）: {csv_path}")
                    _wait_for_file_stable(csv_path)
                    run_epup_checks_once(
                        csv_path=csv_path,
                        mode=args.mode,
                        evaluate_on_alert=args.evaluate_on_alert,
                        evaluate_always=args.evaluate_always,
                        quiet=args.quiet,
                        report_dir=Path(args.report_dir),
                    )
            time.sleep(args.poll_interval)
        except KeyboardInterrupt:
            if not args.quiet:
                print("\n🛑 終了します")
            return 0
        except Exception as e:
            # 監視は止めず、エラーは表示して継続（運用優先）
            if not args.quiet:
                print(f"⚠️ 監視中エラー: {e}")
            time.sleep(max(args.poll_interval, 1.0))


if __name__ == "__main__":
    raise SystemExit(main())
