#!/usr/bin/env python3
"""
集中的なレート制限テスト
実際にレート制限を発生させて待機・リトライの動作を確認
"""

import asyncio
import time
import random
from datetime import datetime, timedelta
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.live import Live
from rich.layout import Layout
from rich import box

console = Console()


class IntensiveAPISimulator:
    """レート制限を強制的に発生させるAPIシミュレーター"""
    
    def __init__(self, name: str, rate_limit: int = 5):
        self.name = name
        self.rate_limit = rate_limit  # より厳しい制限
        self.calls = []
        self.total_wait_time = 0.0
        self.retry_count = 0
        self.forced_waits = []
    
    async def call(self, query: str, index: int):
        """API呼び出しシミュレーション（レート制限強制）"""
        current_time = time.time()
        
        # 過去1分の呼び出しをフィルタ
        self.calls = [t for t in self.calls if current_time - t < 60]
        
        if len(self.calls) >= self.rate_limit:
            # レート制限に達した
            oldest_call = min(self.calls)
            wait_time = 61 - (current_time - oldest_call)
            
            if wait_time > 0:
                self.forced_waits.append({
                    'time': datetime.now(),
                    'wait': wait_time,
                    'index': index
                })
                
                console.print(
                    f"[yellow]⏳ {self.name} API: "
                    f"レート制限 (呼び出し {index+1}) - "
                    f"{wait_time:.1f}秒待機中...[/yellow]"
                )
                
                # 待機時間のカウントダウン表示
                for remaining in range(int(wait_time), 0, -1):
                    console.print(
                        f"[dim]    残り {remaining}秒...[/dim]", 
                        end="\r"
                    )
                    await asyncio.sleep(1)
                
                self.total_wait_time += wait_time
                self.retry_count += 1
                
                # 古い呼び出し記録をクリア
                self.calls = []
        
        # 呼び出し記録
        self.calls.append(time.time())
        
        # 処理時間シミュレーション
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # ランダムな結果
        return random.randint(1000, 1000000)


class EnhancedProgressTracker:
    """拡張進捗トラッカー（リアルタイム更新）"""
    
    def __init__(self, total: int):
        self.total = total
        self.processed = 0
        self.start_time = None
        self.wait_times = []
        self.retry_counts = []
        self.processing_times = []
        self.api_wait_breakdown = {}
    
    def start(self):
        self.start_time = time.time()
        return datetime.now()
    
    def update(self, wait_time: float = 0, retry: int = 0, processing_time: float = 0, api_name: str = None):
        self.processed += 1
        self.wait_times.append(wait_time)
        self.retry_counts.append(retry)
        self.processing_times.append(processing_time)
        
        if api_name and wait_time > 0:
            if api_name not in self.api_wait_breakdown:
                self.api_wait_breakdown[api_name] = []
            self.api_wait_breakdown[api_name].append(wait_time)
    
    def get_detailed_stats(self):
        if not self.start_time:
            return {}
        
        elapsed = time.time() - self.start_time
        progress_rate = (self.processed / self.total) * 100
        
        # 処理速度（移動平均）
        recent_times = self.processing_times[-10:] if self.processing_times else [1]
        avg_processing = sum(recent_times) / len(recent_times)
        
        # 待機時間（移動平均）
        recent_waits = self.wait_times[-10:] if self.wait_times else [0]
        avg_wait = sum(recent_waits) / len(recent_waits)
        
        # 実効処理速度
        total_time_per_record = avg_processing + avg_wait
        if total_time_per_record > 0:
            effective_speed = 60 / total_time_per_record  # rec/min
        else:
            effective_speed = 0
        
        # 残り時間予測（調整版）
        remaining = self.total - self.processed
        if effective_speed > 0:
            # 待機時間を考慮した予測
            base_time = remaining / (effective_speed / 60)
            
            # リトライ率を考慮
            retry_rate = sum(self.retry_counts) / max(len(self.retry_counts), 1)
            adjusted_time = base_time * (1 + retry_rate * 0.3)
            
            eta = datetime.now() + timedelta(seconds=adjusted_time)
        else:
            adjusted_time = 0
            eta = None
        
        return {
            'processed': self.processed,
            'total': self.total,
            'progress_rate': progress_rate,
            'elapsed': elapsed,
            'effective_speed': effective_speed,
            'total_wait': sum(self.wait_times),
            'total_retries': sum(self.retry_counts),
            'avg_wait': avg_wait,
            'remaining_time': adjusted_time,
            'eta': eta,
            'api_breakdown': self.api_wait_breakdown
        }
    
    def create_dashboard(self):
        """ダッシュボード作成"""
        stats = self.get_detailed_stats()
        
        # メイン統計テーブル
        main_table = Table(title="📊 処理統計", box=box.ROUNDED, show_header=False)
        main_table.add_column("項目", style="cyan")
        main_table.add_column("値", style="yellow")
        
        main_table.add_row("進捗", f"{stats['processed']}/{stats['total']} ({stats['progress_rate']:.1f}%)")
        main_table.add_row("経過時間", f"{stats['elapsed']:.1f}秒")
        main_table.add_row("実効速度", f"{stats['effective_speed']:.1f} rec/min")
        main_table.add_row("総待機時間", f"{stats['total_wait']:.1f}秒")
        main_table.add_row("平均待機", f"{stats['avg_wait']:.2f}秒/rec")
        main_table.add_row("総リトライ", f"{stats['total_retries']}回")
        
        if stats['eta']:
            main_table.add_row("完了予定", stats['eta'].strftime('%H:%M:%S'))
            main_table.add_row("残り時間", f"{stats['remaining_time']:.0f}秒")
        
        # API別待機時間
        if stats['api_breakdown']:
            api_table = Table(title="⏱️ API別待機時間", box=box.SIMPLE)
            api_table.add_column("API", style="cyan")
            api_table.add_column("合計", style="yellow")
            api_table.add_column("回数", style="green")
            
            for api, waits in stats['api_breakdown'].items():
                total = sum(waits)
                count = len(waits)
                api_table.add_row(api, f"{total:.1f}秒", f"{count}回")
        else:
            api_table = None
        
        return main_table, api_table


async def intensive_test():
    """集中的なテスト実行"""
    console.print(Panel.fit("🔥 集中的レート制限テスト", style="bold red"))
    
    # 多めのテストデータ（レート制限を強制）
    test_data = [f"Person_{i:03d}" for i in range(1, 21)]  # 20件
    
    # 厳しいレート制限のAPI
    apis = {
        "Twitter": IntensiveAPISimulator("Twitter", rate_limit=3),  # 3回/分
        "YouTube": IntensiveAPISimulator("YouTube", rate_limit=5),  # 5回/分
        "News": IntensiveAPISimulator("News", rate_limit=4),        # 4回/分
    }
    
    # トラッカー初期化
    tracker = EnhancedProgressTracker(len(test_data))
    start_time = tracker.start()
    
    console.print(f"\n[cyan]📅 開始時刻: {start_time.strftime('%H:%M:%S')}[/cyan]")
    console.print(f"[cyan]📊 処理件数: {len(test_data)}件[/cyan]")
    console.print(f"[cyan]⚠️ レート制限: Twitter(3/min), YouTube(5/min), News(4/min)[/cyan]\n")
    
    # 理論的な最小時間計算
    min_api_rate = min(api.rate_limit for api in apis.values())
    theoretical_min = (len(test_data) / min_api_rate) * 60
    console.print(f"[yellow]⏱️ 理論最小時間: {theoretical_min:.0f}秒[/yellow]")
    console.print(f"[yellow]⏱️ 予想時間: {theoretical_min * 1.5:.0f}〜{theoretical_min * 2:.0f}秒[/yellow]\n")
    
    # プログレスバー
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        
        task_id = progress.add_task("[cyan]処理中...", total=len(test_data))
        
        for idx, person in enumerate(test_data):
            progress.update(task_id, description=f"[cyan]処理: {person}")
            record_start = time.time()
            
            # 各APIを並行呼び出し（レート制限が発生する）
            tasks = []
            for api_name, api in apis.items():
                tasks.append(api.call(person, idx))
            
            # 並行実行
            results = await asyncio.gather(*tasks)
            
            # 待機時間集計
            total_wait = sum(api.total_wait_time for api in apis.values())
            total_retry = sum(api.retry_count for api in apis.values())
            processing_time = time.time() - record_start
            
            # トラッカー更新
            for api_name, api in apis.items():
                if api.forced_waits:
                    for wait_info in api.forced_waits:
                        tracker.update(
                            wait_time=wait_info['wait'],
                            retry=1,
                            processing_time=processing_time,
                            api_name=api_name
                        )
                    api.forced_waits = []
            
            if total_wait == 0:
                tracker.update(processing_time=processing_time)
            
            progress.update(task_id, advance=1)
            
            # 定期的な統計表示
            if (idx + 1) % 5 == 0:
                stats = tracker.get_detailed_stats()
                console.print(
                    f"\n[dim]📈 中間報告: "
                    f"速度={stats['effective_speed']:.1f} rec/min, "
                    f"待機={stats['total_wait']:.1f}秒, "
                    f"リトライ={stats['total_retries']}回[/dim]"
                )
    
    # 最終レポート
    console.print("\n" + "=" * 60)
    console.print("[bold green]✅ テスト完了！[/bold green]")
    console.print("=" * 60 + "\n")
    
    # ダッシュボード表示
    main_table, api_table = tracker.create_dashboard()
    console.print(main_table)
    if api_table:
        console.print("\n")
        console.print(api_table)
    
    # 詳細統計
    final_stats = tracker.get_detailed_stats()
    actual_time = final_stats['elapsed']
    efficiency = (theoretical_min / actual_time) * 100 if actual_time > 0 else 0
    
    console.print(f"\n[bold cyan]📊 パフォーマンス分析:[/bold cyan]")
    console.print(f"  理論最小時間: {theoretical_min:.0f}秒")
    console.print(f"  実際の時間: {actual_time:.1f}秒")
    console.print(f"  効率性: {efficiency:.1f}%")
    console.print(f"  オーバーヘッド: {actual_time - theoretical_min:.1f}秒")
    
    # API別統計
    console.print(f"\n[bold cyan]🔧 API別統計:[/bold cyan]")
    for api_name, api in apis.items():
        console.print(
            f"  {api_name}: "
            f"呼び出し={len(api.calls)}, "
            f"待機={api.total_wait_time:.1f}秒, "
            f"リトライ={api.retry_count}"
        )


async def main():
    """メイン処理"""
    console.print("[bold red]=" * 60 + "[/bold red]")
    console.print("[bold red]集中的レート制限テスト - 待機とリトライの検証[/bold red]")
    console.print("[bold red]=" * 60 + "[/bold red]\n")
    
    await intensive_test()
    
    console.print("\n[dim]このテストは意図的にレート制限を発生させて、")
    console.print("待機とリトライ機構の動作を確認しています。[/dim]")


if __name__ == "__main__":
    asyncio.run(main())