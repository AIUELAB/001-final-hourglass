#!/usr/bin/env python3
"""
知名度評価システム（進捗表示統合版）
リアルタイムで完了時間を予測し、待機・リトライ状況を可視化
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich import box
from rich.layout import Layout
from rich.columns import Columns
from rich.text import Text

# 必要なモジュールをインポート
from improved_recognition_system import ImprovedRecognitionEvaluator
from progress_tracker import ProgressTracker, ProgressMonitor
from rate_limit_manager import RateLimitManager, APIProvider

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()


class RecognitionSystemWithProgress(ImprovedRecognitionEvaluator):
    """進捗表示付き知名度評価システム"""
    
    def __init__(self, csv_path: str):
        super().__init__(csv_path)
        self.progress_tracker = None
        self.monitor = None
        self.console = Console()
    
    async def process_database_with_progress(self, test_mode: bool = False):
        """データベース処理（進捗表示付き）"""
        
        # データ読み込み
        self.console.print("[bold cyan]📂 データベース読み込み中...[/bold cyan]")
        df = pd.read_csv(self.csv_path, encoding='utf-8-sig')
        
        if test_mode:
            df = df.head(10)
            self.console.print(f"[yellow]⚠️ テストモード: 最初の10件のみ処理[/yellow]")
        
        total_records = len(df)
        self.console.print(f"[green]✅ {total_records}件のレコードを読み込みました[/green]\n")
        
        # 進捗トラッカー初期化
        self.progress_tracker = ProgressTracker(total_records=total_records)
        self.monitor = ProgressMonitor(self.progress_tracker)
        
        # 処理時間予測を表示
        self._display_initial_estimate(total_records)
        
        # モニタリング開始（別タスク）
        monitor_task = asyncio.create_task(self.monitor.start_monitoring())
        
        # 処理開始
        all_scores = []
        
        try:
            for idx, row in df.iterrows():
                record_start = time.time()
                wait_time_start = 0.0
                
                # 現在処理中の人物を表示
                name = row.get('person_name_ja', row.get('person_name', ''))
                self.console.print(f"[dim]処理中: {name}[/dim]", end="\r")
                
                # 評価実行
                score = await self.evaluate_person_with_tracking(row, idx + 1)
                all_scores.append(score)
                
                # 進捗更新
                processing_time = time.time() - record_start
                wait_time = score.api_wait_time if hasattr(score, 'api_wait_time') else 0.0
                retry_count = score.api_retry_count if hasattr(score, 'api_retry_count') else 0
                
                self.progress_tracker.update_record_processed(
                    success=score.final_score > 0,
                    processing_time=processing_time,
                    wait_time=wait_time,
                    retries=retry_count
                )
                
                # API状態更新
                self._update_api_states()
                
                # 定期的な詳細レポート（10件ごと）
                if (idx + 1) % 10 == 0:
                    await self._display_interim_report(idx + 1, total_records)
            
        finally:
            # モニタリング停止
            self.monitor.stop_monitoring()
            if not monitor_task.done():
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
        
        # 結果をDataFrameに追加
        self._apply_scores_to_dataframe(df, all_scores)
        
        # 最終レポート表示
        self._display_final_report(df)
        
        # 結果保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f"recognition_with_progress_{timestamp}.csv"
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        self.console.print(f"\n[bold green]✅ 結果を保存: {output_path}[/bold green]")
        
        # 詳細な完了レポート
        self.monitor.display_final_report()
        
        return df
    
    async def evaluate_person_with_tracking(self, row: pd.Series, index: int):
        """個人評価（追跡機能付き）"""
        # 基本の評価を実行
        score = await self.evaluate_person(row)
        
        # API呼び出し統計を記録
        if score.google_results is not None:
            self.progress_tracker.update_api_call("Google", 0, True)
        if score.youtube_views is not None:
            self.progress_tracker.update_api_call("YouTube", 0, True)
        if score.twitter_mentions is not None:
            self.progress_tracker.update_api_call("Twitter", 0, True)
        if score.news_articles is not None:
            self.progress_tracker.update_api_call("News", 0, True)
        if score.brave_results is not None:
            self.progress_tracker.update_api_call("Brave", 0, True)
        
        return score
    
    def _display_initial_estimate(self, total_records: int):
        """初期見積もりを表示"""
        # 各APIのレート制限から理論的な処理時間を計算
        apis = [APIProvider.GOOGLE, APIProvider.YOUTUBE, APIProvider.TWITTER, 
                APIProvider.NEWS, APIProvider.BRAVE]
        
        # 最も制限の厳しいAPIを基準に計算
        min_rate_per_minute = 15  # Twitter API (最も厳しい)
        
        # 理想的な処理時間（待機なし）
        ideal_time = (total_records / min_rate_per_minute) * 60
        
        # 現実的な処理時間（待機・リトライ考慮）
        realistic_time = ideal_time * 1.5  # 50%のオーバーヘッド
        worst_case_time = ideal_time * 3.0  # 最悪ケース
        
        table = Table(title="⏱️ 処理時間見積もり", box=box.ROUNDED)
        table.add_column("シナリオ", style="cyan")
        table.add_column("予測時間", style="yellow")
        table.add_column("完了予定", style="green")
        
        now = datetime.now()
        
        table.add_row(
            "理想的（待機なし）",
            self._format_seconds(ideal_time),
            (now + timedelta(seconds=ideal_time)).strftime("%H:%M:%S")
        )
        table.add_row(
            "現実的（通常）",
            self._format_seconds(realistic_time),
            (now + timedelta(seconds=realistic_time)).strftime("%H:%M:%S")
        )
        table.add_row(
            "最悪ケース",
            self._format_seconds(worst_case_time),
            (now + timedelta(seconds=worst_case_time)).strftime("%H:%M:%S")
        )
        
        self.console.print(table)
        self.console.print("")
    
    def _format_seconds(self, seconds: float) -> str:
        """秒を読みやすい形式に変換"""
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            return f"{seconds/60:.1f}分"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) / 60
            return f"{int(hours)}時間{int(minutes)}分"
    
    def _update_api_states(self):
        """API状態を更新"""
        # レート制限マネージャーから状態を取得
        for provider in APIProvider:
            status = self.rate_manager.get_rate_limit_status(provider)
            
            # プログレストラッカーに反映
            self.progress_tracker.update_api_limits(
                provider.value.capitalize(),
                status["usage"]["per_minute"]["remaining"],
                None  # リセット時刻は別途計算
            )
    
    async def _display_interim_report(self, processed: int, total: int):
        """中間レポートを表示"""
        self.console.print("\n" + "="*60)
        self.console.print(f"[bold cyan]📊 中間レポート ({processed}/{total})[/bold cyan]")
        
        # 現在の統計
        stats = self.rate_manager.get_statistics()
        progress_data = self.progress_tracker.get_progress_display()
        
        # 進捗状況
        self.console.print(f"進捗率: {progress_data['progress_rate']:.1f}%")
        self.console.print(f"成功率: {progress_data['success_rate']:.1f}%")
        self.console.print(f"処理速度: {progress_data['processing_speed']:.1f} レコード/分")
        
        # 時間情報
        self.console.print(f"\n⏱️ 時間統計:")
        self.console.print(f"  経過時間: {progress_data['elapsed_time']}")
        self.console.print(f"  待機時間: {progress_data['total_wait_time']}")
        self.console.print(f"  残り時間: {progress_data['remaining_time']}")
        self.console.print(f"  完了予定: {progress_data['estimated_completion']}")
        
        # 推奨事項
        if stats['success_rate'] < 0.5:
            self.console.print(f"\n[yellow]⚠️ 成功率が低いです。APIキーを確認してください。[/yellow]")
        
        if float(progress_data['total_wait_time'].split('秒')[0] if '秒' in progress_data['total_wait_time'] else 0) > 60:
            self.console.print(f"[yellow]⚠️ 待機時間が長いです。処理を分散することを検討してください。[/yellow]")
        
        self.console.print("="*60 + "\n")
    
    def _apply_scores_to_dataframe(self, df: pd.DataFrame, scores: List):
        """スコアをDataFrameに適用"""
        for idx, score in enumerate(scores):
            df.loc[idx, 'recognition_score_final'] = score.final_score
            df.loc[idx, 'data_completeness'] = score.data_completeness
            df.loc[idx, 'confidence_level'] = score.confidence_level
            df.loc[idx, 'api_success_count'] = score.api_success_count
            df.loc[idx, 'api_wait_time'] = score.api_wait_time
            
            # 削除推奨
            if score.confidence_level == "LOW":
                df.loc[idx, 'deletion_recommendation'] = "要再評価"
            elif score.final_score < 3.0:
                df.loc[idx, 'deletion_recommendation'] = "削除候補"
            elif score.final_score < 5.0:
                df.loc[idx, 'deletion_recommendation'] = "要検討"
            elif score.final_score < 7.0:
                df.loc[idx, 'deletion_recommendation'] = "保持（中）"
            else:
                df.loc[idx, 'deletion_recommendation'] = "保持（高）"
    
    def _display_final_report(self, df: pd.DataFrame):
        """最終レポートを表示"""
        self.console.print("\n" + "="*70)
        self.console.print("[bold green]✨ 処理完了サマリー[/bold green]")
        self.console.print("="*70)
        
        # 削除推奨統計
        recommendation_stats = df['deletion_recommendation'].value_counts()
        
        table = Table(title="判定結果分布", box=box.SIMPLE)
        table.add_column("判定", style="cyan")
        table.add_column("件数", style="yellow")
        table.add_column("割合", style="green")
        
        total = len(df)
        for category, count in recommendation_stats.items():
            percentage = (count / total) * 100
            table.add_row(category, str(count), f"{percentage:.1f}%")
        
        self.console.print(table)
        
        # データ品質統計
        avg_completeness = df['data_completeness'].mean()
        confidence_dist = df['confidence_level'].value_counts()
        
        self.console.print(f"\n📊 データ品質:")
        self.console.print(f"  平均完全性: {avg_completeness:.1%}")
        self.console.print(f"  HIGH信頼度: {confidence_dist.get('HIGH', 0)}件")
        self.console.print(f"  MEDIUM信頼度: {confidence_dist.get('MEDIUM', 0)}件")
        self.console.print(f"  LOW信頼度: {confidence_dist.get('LOW', 0)}件")


async def main():
    """メイン処理"""
    console.print("[bold cyan]🚀 知名度評価システム（進捗表示版）起動[/bold cyan]\n")
    
    # CSVファイルパス
    csv_path = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    
    if not Path(csv_path).exists():
        # テストデータ作成
        console.print("[yellow]テストデータを作成中...[/yellow]")
        test_data = pd.DataFrame([
            {"person_id": f"P{i:03d}", 
             "person_name": f"Person {i}", 
             "person_name_ja": f"人物{i}", 
             "category": ["YouTuber", "歌手", "俳優", "その他"][i % 4]}
            for i in range(1, 21)  # 20件のテストデータ
        ])
        csv_path = "test_recognition_progress.csv"
        test_data.to_csv(csv_path, index=False, encoding='utf-8-sig')
        console.print(f"[green]✅ テストデータを作成: {csv_path}[/green]\n")
    
    # システム初期化
    system = RecognitionSystemWithProgress(csv_path)
    
    # 処理実行
    try:
        await system.process_database_with_progress(test_mode=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ ユーザーによる中断[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ エラー: {e}[/red]")
        raise
    
    console.print("\n[bold green]✨ 全処理完了！[/bold green]")


if __name__ == "__main__":
    # Rich のログ表示を無効化（進捗表示と競合するため）
    logging.getLogger("rich").setLevel(logging.WARNING)
    
    # 実行
    asyncio.run(main())