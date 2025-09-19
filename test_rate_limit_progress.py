#!/usr/bin/env python3
"""
レート制限と進捗表示システムの統合テスト
実際のAPI呼び出しなしでシステムの動作を確認
"""

import asyncio
import time
import random
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich import box

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
console = Console()


class MockAPIClient:
    """APIクライアントのモック"""
    
    def __init__(self, name: str, rate_limit: int = 15):
        self.name = name
        self.rate_limit = rate_limit
        self.calls_made = 0
        self.last_reset = time.time()
        self.total_wait_time = 0.0
        self.retry_count = 0
    
    async def call(self, query: str):
        """API呼び出しのシミュレーション"""
        # レート制限チェック
        current_time = time.time()
        elapsed = current_time - self.last_reset
        
        if elapsed >= 60:
            # 1分経過でリセット
            self.calls_made = 0
            self.last_reset = current_time
        
        if self.calls_made >= self.rate_limit:
            # レート制限に達した場合
            wait_time = 60 - elapsed
            console.print(f"[yellow]⏳ {self.name} API: レート制限により{wait_time:.1f}秒待機[/yellow]")
            self.total_wait_time += wait_time
            await asyncio.sleep(wait_time)
            self.calls_made = 0
            self.last_reset = time.time()
            self.retry_count += 1
        
        # API呼び出し
        self.calls_made += 1
        
        # ランダムな処理時間（0.1〜0.5秒）
        processing_time = random.uniform(0.1, 0.5)
        await asyncio.sleep(processing_time)
        
        # ランダムな結果を返す
        if self.name == "Google":
            return random.randint(10000, 10000000)
        elif self.name == "YouTube":
            return random.randint(1000, 50000000)
        elif self.name == "Twitter":
            return random.randint(10, 100000)
        elif self.name == "News":
            return random.randint(0, 1000)
        else:
            return random.randint(100, 100000)


class ProgressTrackingSystem:
    """進捗追跡システム"""
    
    def __init__(self, total_records: int):
        self.total_records = total_records
        self.processed = 0
        self.start_time = None
        self.total_wait_time = 0.0
        self.total_retry_count = 0
        self.api_stats = {}
    
    def start(self):
        """処理開始"""
        self.start_time = time.time()
        console.print(f"[bold cyan]🚀 処理開始: {datetime.now().strftime('%H:%M:%S')}[/bold cyan]")
    
    def update(self, wait_time: float = 0, retry_count: int = 0):
        """進捗更新"""
        self.processed += 1
        self.total_wait_time += wait_time
        self.total_retry_count += retry_count
    
    def get_stats(self):
        """統計情報を取得"""
        if not self.start_time:
            return {}
        
        elapsed = time.time() - self.start_time
        progress_rate = (self.processed / self.total_records) * 100
        
        # 処理速度計算
        if elapsed > 0:
            processing_speed = (self.processed / elapsed) * 60  # records/min
        else:
            processing_speed = 0
        
        # 残り時間予測
        if self.processed > 0 and processing_speed > 0:
            remaining_records = self.total_records - self.processed
            remaining_time = remaining_records / (processing_speed / 60)
            eta = datetime.now() + timedelta(seconds=remaining_time)
        else:
            remaining_time = 0
            eta = None
        
        return {
            'processed': self.processed,
            'total': self.total_records,
            'progress_rate': progress_rate,
            'elapsed_time': elapsed,
            'processing_speed': processing_speed,
            'total_wait_time': self.total_wait_time,
            'total_retries': self.total_retry_count,
            'remaining_time': remaining_time,
            'eta': eta
        }
    
    def display_summary(self):
        """サマリー表示"""
        stats = self.get_stats()
        
        table = Table(title="📊 処理統計", box=box.ROUNDED)
        table.add_column("項目", style="cyan")
        table.add_column("値", style="yellow")
        
        table.add_row("処理済み", f"{stats['processed']}/{stats['total']} ({stats['progress_rate']:.1f}%)")
        table.add_row("経過時間", f"{stats['elapsed_time']:.1f}秒")
        table.add_row("処理速度", f"{stats['processing_speed']:.1f} rec/min")
        table.add_row("総待機時間", f"{stats['total_wait_time']:.1f}秒")
        table.add_row("総リトライ", f"{stats['total_retries']}回")
        
        if stats['eta']:
            table.add_row("完了予定", stats['eta'].strftime('%H:%M:%S'))
        
        console.print(table)


async def test_with_mock_apis():
    """モックAPIでテスト"""
    console.print(Panel.fit("🧪 レート制限と進捗追跡のテスト", style="bold cyan"))
    
    # テストデータ
    test_people = [
        {"name": "HIKAKIN", "name_ja": "ヒカキン"},
        {"name": "Yonezu Kenshi", "name_ja": "米津玄師"},
        {"name": "Aragaki Yui", "name_ja": "新垣結衣"},
        {"name": "Fujii Sota", "name_ja": "藤井聡太"},
        {"name": "Ohtani Shohei", "name_ja": "大谷翔平"},
    ]
    
    # APIクライアント初期化（異なるレート制限）
    apis = {
        "Google": MockAPIClient("Google", rate_limit=30),
        "YouTube": MockAPIClient("YouTube", rate_limit=20),
        "Twitter": MockAPIClient("Twitter", rate_limit=15),  # 最も厳しい
        "News": MockAPIClient("News", rate_limit=25),
        "Brave": MockAPIClient("Brave", rate_limit=30),
    }
    
    # 進捗トラッキング
    tracker = ProgressTrackingSystem(len(test_people))
    tracker.start()
    
    # 初期時間見積もり表示
    min_rate = min(api.rate_limit for api in apis.values())
    estimated_time = (len(test_people) / min_rate) * 60
    
    console.print(f"\n[cyan]⏱️ 推定処理時間:[/cyan]")
    console.print(f"  理想的: {estimated_time:.1f}秒")
    console.print(f"  現実的: {estimated_time * 1.5:.1f}秒")
    console.print(f"  最悪: {estimated_time * 3:.1f}秒\n")
    
    # Progress表示
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task(
            "[cyan]処理中...", 
            total=len(test_people)
        )
        
        # 各人物を処理
        for idx, person in enumerate(test_people):
            progress.update(task, description=f"[cyan]処理中: {person['name_ja']}")
            
            # 各APIを呼び出し
            api_results = {}
            total_wait = 0
            total_retry = 0
            
            for api_name, api_client in apis.items():
                try:
                    wait_before = api_client.total_wait_time
                    retry_before = api_client.retry_count
                    
                    result = await api_client.call(person['name'])
                    api_results[api_name] = result
                    
                    wait_after = api_client.total_wait_time
                    retry_after = api_client.retry_count
                    
                    total_wait += (wait_after - wait_before)
                    total_retry += (retry_after - retry_before)
                    
                except Exception as e:
                    console.print(f"[red]❌ {api_name} エラー: {e}[/red]")
                    api_results[api_name] = 0
            
            # スコア計算（簡易版）
            score = calculate_simple_score(api_results)
            
            # 進捗更新
            tracker.update(wait_time=total_wait, retry_count=total_retry)
            progress.update(task, advance=1)
            
            # 結果表示（簡潔に）
            if (idx + 1) % 2 == 0 or idx == len(test_people) - 1:
                stats = tracker.get_stats()
                progress.console.print(
                    f"[dim]進捗: {stats['processed']}/{stats['total']} | "
                    f"速度: {stats['processing_speed']:.1f} rec/min | "
                    f"待機: {stats['total_wait_time']:.1f}秒[/dim]"
                )
    
    # 最終サマリー
    console.print("\n")
    tracker.display_summary()
    
    # API統計
    console.print("\n[bold cyan]📊 API統計:[/bold cyan]")
    for api_name, api_client in apis.items():
        console.print(
            f"  {api_name}: "
            f"呼び出し={api_client.calls_made}, "
            f"待機={api_client.total_wait_time:.1f}秒, "
            f"リトライ={api_client.retry_count}"
        )


def calculate_simple_score(api_results: dict) -> float:
    """簡易スコア計算"""
    score = 0.0
    
    # Google結果
    if api_results.get('Google', 0) > 1000000:
        score += 3.0
    elif api_results.get('Google', 0) > 100000:
        score += 2.0
    elif api_results.get('Google', 0) > 10000:
        score += 1.0
    
    # YouTube視聴
    if api_results.get('YouTube', 0) > 10000000:
        score += 2.5
    elif api_results.get('YouTube', 0) > 1000000:
        score += 1.5
    elif api_results.get('YouTube', 0) > 100000:
        score += 0.5
    
    # Twitter言及
    if api_results.get('Twitter', 0) > 10000:
        score += 2.0
    elif api_results.get('Twitter', 0) > 1000:
        score += 1.0
    elif api_results.get('Twitter', 0) > 100:
        score += 0.5
    
    # News記事
    if api_results.get('News', 0) > 100:
        score += 1.5
    elif api_results.get('News', 0) > 10:
        score += 1.0
    elif api_results.get('News', 0) > 0:
        score += 0.5
    
    # Brave結果
    if api_results.get('Brave', 0) > 50000:
        score += 1.0
    elif api_results.get('Brave', 0) > 10000:
        score += 0.5
    
    return min(score, 10.0)


async def main():
    """メイン処理"""
    console.print("[bold cyan]=" * 60 + "[/bold cyan]")
    console.print("[bold cyan]レート制限対応 進捗表示システム テスト[/bold cyan]")
    console.print("[bold cyan]=" * 60 + "[/bold cyan]\n")
    
    await test_with_mock_apis()
    
    console.print("\n[bold green]✨ テスト完了！[/bold green]")
    console.print("[dim]このテストはモックAPIを使用し、実際のAPI呼び出しは行いません[/dim]")


if __name__ == "__main__":
    asyncio.run(main())