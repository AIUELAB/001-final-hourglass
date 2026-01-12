#!/usr/bin/env python3
"""
SAGE Turbo Auto Loop - 375到達自動運用

各年齢（1-100歳）で375件のエピソードを達成するまで自動ループ実行。
dry-run → submit → watch → retrieve → dashboard更新 を繰り返す。

Usage:
    python scripts/sage/auto_loop.py --target 375 --batch-size 10000
    python scripts/sage/auto_loop.py --target 375 --batch-size 10000 --dry-run-only
"""

import argparse
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.inventory_manager import InventoryManager, InventoryConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class LoopConfig:
    """自動ループ設定"""

    target_per_age: int = 375  # 年齢別目標本数
    batch_size: int = 10000  # 1バッチあたりの件数
    max_error_rate: float = 0.10  # 10%超でエラー停止
    dry_run_only: bool = False  # dry-runのみ実行
    poll_interval: int = 60  # バッチステータス確認間隔（秒）
    max_wait_time: int = 7200  # 最大待機時間（秒） = 2時間


@dataclass
class LoopStatus:
    """ループステータス"""

    achieved_ages: int = 0
    total_ages: int = 100
    total_deficit: int = 0
    batch_accepted: int = 0
    batch_rejected: int = 0
    total_processed: int = 0


class AutoLoopRunner:
    """自動ループ実行エンジン"""

    def __init__(self, config: LoopConfig | None = None):
        self.config = config or LoopConfig()
        inv_config = InventoryConfig(
            target_per_age=self.config.target_per_age,
            min_age=1,
            max_age=100,
        )
        self.inventory = InventoryManager(config=inv_config)
        self.status = LoopStatus()

    def print_banner(self) -> None:
        """バナー表示"""
        print(
            """
╔════════════════════════════════════════════════════════════════╗
║              SAGE Turbo 375到達 自動運用                       ║
╚════════════════════════════════════════════════════════════════╝
"""
        )

    def print_progress(self) -> None:
        """進捗表示"""
        self.inventory.refresh()
        summary = self.inventory.get_summary()

        achieved = summary["achieved_ages"]
        total = summary["total_ages"]
        total_upper = summary["total_upper_episodes"]
        total_target = summary["total_target"]
        deficit = total_target - total_upper

        self.status.achieved_ages = achieved
        self.status.total_ages = total
        self.status.total_deficit = max(0, deficit)

        pct = (achieved / total * 100) if total > 0 else 0
        bar_width = 50
        filled = int(bar_width * achieved / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)

        print(
            f"""
=== ノルマ達成状況 ===
達成年齢: {achieved}/{total} ({pct:.1f}%)
[{bar}]
上位レベル総数: {total_upper:,}/{total_target:,}
総不足: {deficit:,}件
"""
        )

    def get_deficit_ages(self) -> list[tuple[int, int]]:
        """不足年齢リスト取得 (age, deficit)"""
        self.inventory.refresh()
        deficits = []
        for age in range(1, 101):
            status = self.inventory.get_status(age)
            if status and status.deficit > 0:
                deficits.append((age, status.deficit))
        # 不足数の多い順にソート
        deficits.sort(key=lambda x: x[1], reverse=True)
        return deficits

    def run_command(self, cmd: list[str], capture: bool = False) -> tuple[int, str]:
        """コマンド実行"""
        logger.info(f"実行: {' '.join(cmd)}")
        try:
            if capture:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.config.max_wait_time,
                )
                return result.returncode, result.stdout + result.stderr
            else:
                result = subprocess.run(cmd, timeout=self.config.max_wait_time)
                return result.returncode, ""
        except subprocess.TimeoutExpired:
            logger.error("コマンドタイムアウト")
            return 1, "timeout"
        except Exception as e:
            logger.error(f"コマンド実行エラー: {e}")
            return 1, str(e)

    def submit_batch(self) -> str | None:
        """バッチ送信（dry-run → submit）"""
        # dry-run実行
        logger.info("=== dry-run 実行 ===")
        cmd_dry = [
            sys.executable,
            "-m",
            "scripts.sage.turbo_cli",
            "submit",
            "--count",
            str(self.config.batch_size),
            "--dry-run",
        ]
        ret, output = self.run_command(cmd_dry, capture=True)

        if ret != 0:
            logger.error(f"dry-run失敗: {output}")
            return None

        if self.config.dry_run_only:
            logger.info("dry-run-onlyモード: submitをスキップ")
            return None

        # 本番submit
        logger.info("=== 本番 submit ===")
        cmd_submit = [
            sys.executable,
            "-m",
            "scripts.sage.turbo_cli",
            "submit",
            "--count",
            str(self.config.batch_size),
        ]
        ret, output = self.run_command(cmd_submit, capture=True)

        if ret != 0:
            logger.error(f"submit失敗: {output}")
            return None

        # batch_idを抽出
        for line in output.splitlines():
            if "batch_id:" in line:
                batch_id = line.split("batch_id:")[1].strip()
                return batch_id

        logger.error("batch_idが見つかりません")
        return None

    def wait_for_completion(self, batch_id: str) -> bool:
        """バッチ完了待機"""
        logger.info(f"=== バッチ完了待機: {batch_id} ===")

        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed > self.config.max_wait_time:
                logger.error("最大待機時間超過")
                return False

            # ステータス確認
            cmd = [
                sys.executable,
                "-m",
                "scripts.sage.turbo_cli",
                "status",
                "--batch-id",
                batch_id,
            ]
            _, output = self.run_command(cmd, capture=True)

            # ステータス判定（JSONの "status": "xxx" を解析）
            if '"status": "ended"' in output:
                logger.info("バッチ完了")
                return True

            if '"status": "canceled"' in output or '"status": "failed"' in output:
                logger.error("バッチ失敗/キャンセル")
                return False

            logger.info(f"処理中... (経過: {int(elapsed)}秒)")
            time.sleep(self.config.poll_interval)

    def retrieve_results(self, batch_id: str) -> tuple[int, int]:
        """結果取得・書き込み"""
        logger.info(f"=== 結果取得: {batch_id} ===")

        cmd = [
            sys.executable,
            "-m",
            "scripts.sage.turbo_cli",
            "retrieve",
            "--batch-id",
            batch_id,
            "--write",
            "--wait",
        ]
        ret, output = self.run_command(cmd, capture=True)

        if ret != 0:
            logger.error(f"retrieve失敗: {output}")
            return 0, 0

        # accepted/rejected数を抽出
        accepted = 0
        rejected = 0
        for line in output.splitlines():
            if "accepted:" in line:
                try:
                    accepted = int(line.split("accepted:")[1].strip())
                except ValueError:
                    pass
            if "rejected:" in line:
                try:
                    rejected = int(line.split("rejected:")[1].strip())
                except ValueError:
                    pass

        self.status.batch_accepted = accepted
        self.status.batch_rejected = rejected
        self.status.total_processed += accepted

        return accepted, rejected

    def update_dashboard(self) -> bool:
        """ダッシュボード更新"""
        logger.info("=== ダッシュボード更新 ===")

        cmd = [sys.executable, "scripts/update_dashboard_v10.py"]
        ret, _ = self.run_command(cmd)

        if ret != 0:
            logger.warning("ダッシュボード更新失敗（続行）")
            return False
        return True

    def check_safety(self, accepted: int, rejected: int) -> bool:
        """安全性チェック"""
        total = accepted + rejected
        if total == 0:
            logger.warning("処理件数が0件")
            return True  # 続行可能（候補がない可能性）

        error_rate = rejected / total
        if error_rate > self.config.max_error_rate:
            logger.error(f"エラー率 {error_rate:.1%} > {self.config.max_error_rate:.0%}: 安全停止")
            return False

        return True

    def run_loop(self) -> int:
        """メインループ実行"""
        self.print_banner()

        loop_count = 0
        while True:
            loop_count += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"=== ループ #{loop_count} 開始 ===")
            logger.info(f"{'='*60}\n")

            # 進捗確認
            self.print_progress()

            # 不足チェック
            deficits = self.get_deficit_ages()
            if not deficits:
                logger.info("🎉 全年齢で375件達成! ループ終了")
                return 0

            logger.info(f"未達成年齢: {len(deficits)}件")
            top5 = deficits[:5]
            for age, deficit in top5:
                logger.info(f"  {age}歳: 不足{deficit}件")

            # バッチ送信
            batch_id = self.submit_batch()
            if not batch_id:
                if self.config.dry_run_only:
                    logger.info("dry-run-onlyモード終了")
                    return 0
                logger.error("バッチ送信失敗")
                return 1

            # 完了待機
            if not self.wait_for_completion(batch_id):
                logger.error("バッチ処理失敗")
                return 1

            # 結果取得
            accepted, rejected = self.retrieve_results(batch_id)
            logger.info(f"直近バッチ: +{accepted}件採用, -{rejected}件拒否")

            # 安全チェック
            if not self.check_safety(accepted, rejected):
                return 1

            # ダッシュボード更新
            self.update_dashboard()

            # 最終進捗表示
            self.print_progress()

            logger.info(f"=== ループ #{loop_count} 完了 ===\n")

            # 全件達成チェック
            if self.status.total_deficit == 0:
                logger.info("🎉 全年齢で375件達成!")
                return 0


def main():
    """エントリーポイント"""
    parser = argparse.ArgumentParser(
        description="SAGE Turbo 375到達 自動ループ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        type=int,
        default=375,
        help="年齢別目標件数 (default: 375)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="1バッチあたりの件数 (default: 10000)",
    )
    parser.add_argument(
        "--dry-run-only",
        action="store_true",
        help="dry-runのみ実行（本番submitなし）",
    )
    parser.add_argument(
        "--max-error-rate",
        type=float,
        default=0.10,
        help="最大エラー率 (default: 0.10 = 10%%)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="ステータス確認間隔（秒） (default: 60)",
    )

    args = parser.parse_args()

    config = LoopConfig(
        target_per_age=args.target,
        batch_size=args.batch_size,
        dry_run_only=args.dry_run_only,
        max_error_rate=args.max_error_rate,
        poll_interval=args.poll_interval,
    )

    runner = AutoLoopRunner(config)
    return runner.run_loop()


if __name__ == "__main__":
    sys.exit(main())
