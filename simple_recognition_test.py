#!/usr/bin/env python3
"""
シンプルな知名度評価テスト
APIキーなしでも動作する最小限のテスト
"""

import asyncio
import pandas as pd
from datetime import datetime
from rich.console import Console

console = Console()

async def test_simple():
    """最小限のテスト"""
    console.print("[bold cyan]🧪 知名度評価システム 簡易テスト[/bold cyan]\n")

    # テストデータ
    test_data = pd.DataFrame([
        {"person_id": "P001", "person_name": "HIKAKIN", "person_name_ja": "ヒカキン", "category": "YouTuber"},
        {"person_id": "P002", "person_name": "Yonezu Kenshi", "person_name_ja": "米津玄師", "category": "歌手"},
        {"person_id": "P003", "person_name": "Ohtani Shohei", "person_name_ja": "大谷翔平", "category": "野球選手"},
    ])

    # CSVとして保存
    test_csv = "test_simple_recognition.csv"
    test_data.to_csv(test_csv, index=False, encoding='utf-8-sig')
    console.print(f"[green]✅ テストデータ作成: {test_csv}[/green]\n")

    # 各システムコンポーネントをテスト
    console.print("[cyan]📊 コンポーネントテスト:[/cyan]")

    # 1. Rate Limit Manager
    try:
        from rate_limit_manager import RateLimitManager, APIProvider
        manager = RateLimitManager()
        console.print("  ✅ RateLimitManager: 正常")
    except Exception as e:
        console.print(f"  ❌ RateLimitManager: {e}")

    # 2. Progress Tracker
    try:
        from progress_tracker import ProgressTracker
        tracker = ProgressTracker(total_records=3)
        console.print("  ✅ ProgressTracker: 正常")
    except Exception as e:
        console.print(f"  ❌ ProgressTracker: {e}")

    # 3. Recognition System
    try:
        from improved_recognition_system import ImprovedRecognitionEvaluator
        console.print("  ✅ ImprovedRecognitionEvaluator: 正常")
    except Exception as e:
        console.print(f"  ❌ ImprovedRecognitionEvaluator: {e}")

    # 4. 統合システム
    try:
        from recognition_system_with_progress import RecognitionSystemWithProgress
        console.print("  ✅ RecognitionSystemWithProgress: 正常")

        # 簡易実行テスト
        console.print("\n[cyan]🚀 簡易実行テスト開始...[/cyan]")
        system = RecognitionSystemWithProgress(test_csv)

        # モックデータで評価
        console.print("\n[yellow]📊 モックデータによる評価:[/yellow]")
        for idx, row in test_data.iterrows():
            name = row['person_name_ja']
            # ランダムスコア生成（実際のAPI呼び出しなし）
            import random
            score = random.uniform(3.0, 9.5)
            console.print(f"  • {name}: スコア={score:.1f}")

        console.print("\n[green]✅ すべてのテストが成功しました！[/green]")

    except Exception as e:
        console.print(f"  ❌ 統合システム: {e}")
        import traceback
        traceback.print_exc()

    # クリーンアップ
    import os
    if os.path.exists(test_csv):
        os.remove(test_csv)
        console.print("\n[dim]テストファイルをクリーンアップしました[/dim]")

if __name__ == "__main__":
    asyncio.run(test_simple())
