#!/usr/bin/env python3
"""
進捗追跡システム - リアルタイム完了時間予測
待機とリトライを考慮した正確な終了時間表示
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
from pathlib import Path
from collections import deque
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich import box

# カラーコンソール
console = Console()

logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    """処理メトリクス"""
    total_records: int = 0
    processed_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    retry_count: int = 0

    # 時間関連
    start_time: float = field(default_factory=time.time)
    elapsed_time: float = 0.0
    total_wait_time: float = 0.0
    total_processing_time: float = 0.0

    # API別統計
    api_calls: Dict[str, int] = field(default_factory=dict)
    api_waits: Dict[str, float] = field(default_factory=dict)
    api_failures: Dict[str, int] = field(default_factory=dict)

    # 予測
    estimated_completion_time: Optional[datetime] = None
    confidence_level: float = 0.0

    # 履歴（最近100件）
    processing_times: deque = field(default_factory=lambda: deque(maxlen=100))
    wait_times: deque = field(default_factory=lambda: deque(maxlen=100))


class ProgressTracker:
    """進捗追跡クラス"""

    def __init__(self, total_records: int):
        self.metrics = ProcessingMetrics(total_records=total_records)
        self.start_time = datetime.now()
        self.last_update_time = time.time()

        # 移動平均用のウィンドウ
        self.time_window = deque(maxlen=20)  # 最近20件の処理時間
        self.wait_window = deque(maxlen=20)  # 最近20件の待機時間

        # API別レート制限状態
        self.api_states = {
            "Google": {"limit": 60, "remaining": 60, "reset_at": None},
            "YouTube": {"limit": 100, "remaining": 100, "reset_at": None},
            "Twitter": {"limit": 15, "remaining": 15, "reset_at": None},
            "News": {"limit": 30, "remaining": 30, "reset_at": None},
            "Brave": {"limit": 60, "remaining": 60, "reset_at": None}
        }

        # 予測モデルパラメータ
        self.avg_processing_time = 0.0
        self.avg_wait_time = 0.0
        self.avg_retry_rate = 0.0

    def update_record_processed(self, success: bool, processing_time: float,
                               wait_time: float = 0.0, retries: int = 0):
        """レコード処理完了を記録"""
        self.metrics.processed_records += 1

        if success:
            self.metrics.successful_records += 1
        else:
            self.metrics.failed_records += 1

        self.metrics.retry_count += retries
        self.metrics.total_processing_time += processing_time
        self.metrics.total_wait_time += wait_time

        # 履歴に追加
        self.metrics.processing_times.append(processing_time)
        self.metrics.wait_times.append(wait_time)

        # 移動平均を更新
        self.time_window.append(processing_time)
        self.wait_window.append(wait_time)

        # 予測を更新
        self._update_predictions()

    def update_api_call(self, api_name: str, wait_time: float = 0.0,
                       success: bool = True):
        """API呼び出しを記録"""
        if api_name not in self.metrics.api_calls:
            self.metrics.api_calls[api_name] = 0
            self.metrics.api_waits[api_name] = 0.0
            self.metrics.api_failures[api_name] = 0

        self.metrics.api_calls[api_name] += 1
        self.metrics.api_waits[api_name] += wait_time

        if not success:
            self.metrics.api_failures[api_name] += 1

    def update_api_limits(self, api_name: str, remaining: int,
                         reset_time: Optional[datetime] = None):
        """APIレート制限状態を更新"""
        if api_name in self.api_states:
            self.api_states[api_name]["remaining"] = remaining
            if reset_time:
                self.api_states[api_name]["reset_at"] = reset_time

    def _update_predictions(self):
        """完了時間予測を更新"""
        if self.metrics.processed_records == 0:
            return

        # 移動平均を計算
        if self.time_window:
            self.avg_processing_time = sum(self.time_window) / len(self.time_window)

        if self.wait_window:
            self.avg_wait_time = sum(self.wait_window) / len(self.wait_window)

        # リトライ率
        if self.metrics.processed_records > 0:
            self.avg_retry_rate = self.metrics.retry_count / self.metrics.processed_records

        # 残りレコード数
        remaining = self.metrics.total_records - self.metrics.processed_records

        if remaining <= 0:
            self.metrics.estimated_completion_time = datetime.now()
            self.metrics.confidence_level = 1.0
            return

        # 予測計算
        # 基本処理時間 + 待機時間 + リトライによる追加時間
        avg_time_per_record = (
            self.avg_processing_time +
            self.avg_wait_time +
            (self.avg_processing_time * self.avg_retry_rate * 0.5)
        )

        # レート制限による追加待機時間を考慮
        rate_limit_factor = self._calculate_rate_limit_factor()
        avg_time_per_record *= rate_limit_factor

        # 残り時間を計算
        estimated_seconds = remaining * avg_time_per_record

        # 完了予定時刻
        self.metrics.estimated_completion_time = (
            datetime.now() + timedelta(seconds=estimated_seconds)
        )

        # 信頼度（処理済みレコード数に基づく）
        self.metrics.confidence_level = min(
            1.0,
            self.metrics.processed_records / max(10, self.metrics.total_records * 0.1)
        )

    def _calculate_rate_limit_factor(self) -> float:
        """レート制限による遅延係数を計算"""
        factor = 1.0

        # 各APIの残り容量をチェック
        for api_name, state in self.api_states.items():
            if state["remaining"] < state["limit"] * 0.2:  # 20%未満
                factor *= 1.5  # 50%遅延
            elif state["remaining"] < state["limit"] * 0.5:  # 50%未満
                factor *= 1.2  # 20%遅延

        return min(factor, 3.0)  # 最大3倍まで

    def get_progress_display(self) -> Dict:
        """進捗表示用データを取得"""
        elapsed = time.time() - self.metrics.start_time

        # 進捗率
        progress_rate = (
            self.metrics.processed_records / max(1, self.metrics.total_records)
        ) * 100

        # 成功率
        success_rate = (
            self.metrics.successful_records /
            max(1, self.metrics.processed_records)
        ) * 100

        # 処理速度（レコード/分）
        processing_speed = (
            self.metrics.processed_records / max(1, elapsed)
        ) * 60

        # 残り時間
        if self.metrics.estimated_completion_time:
            remaining_time = (
                self.metrics.estimated_completion_time - datetime.now()
            ).total_seconds()
            remaining_str = self._format_time(max(0, remaining_time))
        else:
            remaining_str = "計算中..."

        return {
            "progress_rate": progress_rate,
            "processed": self.metrics.processed_records,
            "total": self.metrics.total_records,
            "success_rate": success_rate,
            "processing_speed": processing_speed,
            "elapsed_time": self._format_time(elapsed),
            "remaining_time": remaining_str,
            "estimated_completion": (
                self.metrics.estimated_completion_time.strftime("%H:%M:%S")
                if self.metrics.estimated_completion_time else "---"
            ),
            "confidence": self.metrics.confidence_level,
            "total_wait_time": self._format_time(self.metrics.total_wait_time),
            "retry_count": self.metrics.retry_count,
            "api_states": self.api_states
        }

    def _format_time(self, seconds: float) -> str:
        """時間をフォーマット"""
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}時間"

    def display_progress_table(self):
        """進捗テーブルを表示"""
        data = self.get_progress_display()

        # メインテーブル
        table = Table(title="🚀 処理進捗状況", box=box.ROUNDED)
        table.add_column("項目", style="cyan", width=20)
        table.add_column("値", style="green", width=30)

        table.add_row("進捗", f"{data['progress_rate']:.1f}% ({data['processed']}/{data['total']})")
        table.add_row("成功率", f"{data['success_rate']:.1f}%")
        table.add_row("処理速度", f"{data['processing_speed']:.1f} レコード/分")
        table.add_row("経過時間", data['elapsed_time'])
        table.add_row("総待機時間", data['total_wait_time'])
        table.add_row("リトライ回数", str(data['retry_count']))
        table.add_row("", "")  # 空行
        table.add_row("残り時間", data['remaining_time'])
        table.add_row("完了予定時刻", data['estimated_completion'])
        table.add_row("予測信頼度", f"{data['confidence']*100:.0f}%")

        console.print(table)

        # API状態テーブル
        api_table = Table(title="📡 API レート制限状態", box=box.SIMPLE)
        api_table.add_column("API", style="cyan")
        api_table.add_column("残り", style="yellow")
        api_table.add_column("リセット", style="magenta")

        for api_name, state in data['api_states'].items():
            reset_str = (
                state['reset_at'].strftime("%H:%M:%S")
                if state['reset_at'] else "---"
            )
            api_table.add_row(
                api_name,
                f"{state['remaining']}/{state['limit']}",
                reset_str
            )

        console.print(api_table)

    def create_live_display(self) -> Panel:
        """リアルタイム表示用パネルを作成"""
        data = self.get_progress_display()

        # プログレスバー
        progress_text = f"[bold cyan]進捗: {data['progress_rate']:.1f}%[/bold cyan]\n"
        progress_bar = "█" * int(data['progress_rate'] / 2) + "░" * (50 - int(data['progress_rate'] / 2))
        progress_text += f"[green]{progress_bar}[/green]\n\n"

        # メトリクス
        metrics_text = (
            f"[yellow]処理済み:[/yellow] {data['processed']}/{data['total']} | "
            f"[green]成功率:[/green] {data['success_rate']:.1f}% | "
            f"[cyan]速度:[/cyan] {data['processing_speed']:.1f} rec/min\n"
            f"[yellow]経過時間:[/yellow] {data['elapsed_time']} | "
            f"[red]待機時間:[/red] {data['total_wait_time']} | "
            f"[magenta]リトライ:[/magenta] {data['retry_count']}回\n\n"
        )

        # 完了予測
        completion_text = (
            f"[bold green]⏱️ 完了予定時刻: {data['estimated_completion']}[/bold green]\n"
            f"[yellow]残り時間: {data['remaining_time']}[/yellow] "
            f"[dim](信頼度: {data['confidence']*100:.0f}%)[/dim]\n"
        )

        # API状態（コンパクト表示）
        api_text = "[dim]API: "
        for api_name, state in data['api_states'].items():
            color = "green" if state['remaining'] > state['limit'] * 0.5 else "yellow"
            if state['remaining'] < state['limit'] * 0.2:
                color = "red"
            api_text += f"[{color}]{api_name[0]}:{state['remaining']}[/{color}] "
        api_text += "[/dim]"

        content = progress_text + metrics_text + completion_text + api_text

        return Panel(
            content,
            title="🎯 知名度評価システム - リアルタイム進捗",
            border_style="blue"
        )


class ProgressMonitor:
    """進捗モニタリングシステム"""

    def __init__(self, tracker: ProgressTracker):
        self.tracker = tracker
        self.running = False
        self.update_interval = 1.0  # 1秒ごとに更新

    async def start_monitoring(self):
        """モニタリング開始"""
        self.running = True

        with Live(self.tracker.create_live_display(), refresh_per_second=1) as live:
            while self.running:
                await asyncio.sleep(self.update_interval)
                live.update(self.tracker.create_live_display())

                # 完了チェック
                if (self.tracker.metrics.processed_records >=
                    self.tracker.metrics.total_records):
                    self.running = False
                    break

    def stop_monitoring(self):
        """モニタリング停止"""
        self.running = False

    def display_final_report(self):
        """最終レポートを表示"""
        console.print("\n" + "="*60)
        console.print("[bold green]✨ 処理完了レポート[/bold green]")
        console.print("="*60)

        metrics = self.tracker.metrics
        elapsed = time.time() - metrics.start_time

        # サマリーテーブル
        summary_table = Table(box=box.DOUBLE_EDGE)
        summary_table.add_column("メトリクス", style="cyan")
        summary_table.add_column("値", style="green")

        summary_table.add_row("総処理レコード", str(metrics.total_records))
        summary_table.add_row("成功レコード", str(metrics.successful_records))
        summary_table.add_row("失敗レコード", str(metrics.failed_records))
        summary_table.add_row("総処理時間", self.tracker._format_time(elapsed))
        summary_table.add_row("総待機時間", self.tracker._format_time(metrics.total_wait_time))
        summary_table.add_row("実処理時間", self.tracker._format_time(
            elapsed - metrics.total_wait_time
        ))
        summary_table.add_row("平均処理速度",
                            f"{metrics.processed_records / max(1, elapsed) * 60:.1f} rec/min")
        summary_table.add_row("総リトライ回数", str(metrics.retry_count))

        console.print(summary_table)

        # API統計テーブル
        if metrics.api_calls:
            api_table = Table(title="API利用統計", box=box.SIMPLE)
            api_table.add_column("API", style="cyan")
            api_table.add_column("呼び出し回数", style="yellow")
            api_table.add_column("待機時間", style="red")
            api_table.add_column("失敗回数", style="magenta")

            for api_name in metrics.api_calls:
                api_table.add_row(
                    api_name,
                    str(metrics.api_calls[api_name]),
                    self.tracker._format_time(metrics.api_waits.get(api_name, 0)),
                    str(metrics.api_failures.get(api_name, 0))
                )

            console.print(api_table)

        # 予測精度
        if metrics.estimated_completion_time:
            actual_completion = datetime.now()
            predicted = metrics.estimated_completion_time
            diff_seconds = abs((actual_completion - predicted).total_seconds())

            console.print(f"\n[bold]予測精度:[/bold]")
            console.print(f"  予測完了時刻: {predicted.strftime('%H:%M:%S')}")
            console.print(f"  実際完了時刻: {actual_completion.strftime('%H:%M:%S')}")
            console.print(f"  誤差: {self.tracker._format_time(diff_seconds)}")
            console.print(f"  精度: {max(0, 100 - (diff_seconds / elapsed * 100)):.1f}%")


# 使用例
async def example_usage():
    """使用例"""
    # 100レコードを処理する例
    tracker = ProgressTracker(total_records=100)
    monitor = ProgressMonitor(tracker)

    # モニタリング開始（別タスク）
    monitor_task = asyncio.create_task(monitor.start_monitoring())

    # 処理シミュレーション
    for i in range(100):
        # API呼び出しシミュレーション
        processing_time = 0.5 + (0.5 * (i % 3))  # 0.5-1.5秒
        wait_time = 0.1 * (i % 10)  # 0-1秒の待機

        # 進捗更新
        tracker.update_record_processed(
            success=i % 10 != 9,  # 90%成功
            processing_time=processing_time,
            wait_time=wait_time,
            retries=1 if i % 5 == 0 else 0
        )

        # API状態更新
        if i % 10 == 0:
            tracker.update_api_limits("Google", 60 - (i % 60))
            tracker.update_api_limits("Twitter", 15 - (i % 15))

        await asyncio.sleep(processing_time + wait_time)

    # モニタリング停止
    monitor.stop_monitoring()
    await monitor_task

    # 最終レポート表示
    monitor.display_final_report()


if __name__ == "__main__":
    asyncio.run(example_usage())
