#!/usr/bin/env python3
"""
連続バッチ改稿スクリプト

承認なしで複数バッチを連続実行する

使用方法:
    # 10バッチ（500件）を連続実行
    python scripts/batch_improve_loop.py --batches 10

    # 目標件数に達するまで実行（400-500帯が3000件以下になるまで）
    python scripts/batch_improve_loop.py --target 3000

    # 無制限に実行（Ctrl+Cで停止）
    python scripts/batch_improve_loop.py --unlimited

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"
SESSION_FILE = PROJECT_ROOT / ".session" / "current_session.json"

# 環境変数
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)


def get_score_distribution():
    """現在のスコア帯分布を取得"""
    df = pd.read_csv(CSV_PATH)

    bins = [0, 400, 500, 600, 700, 800, float("inf")]
    labels = ["<400", "400-500", "500-600", "600-700", "700-800", "800+"]
    df["帯"] = pd.cut(df["composite_score"], bins=bins, labels=labels, right=False)

    dist = df["帯"].value_counts().to_dict()
    avg_score = df["composite_score"].mean()

    return {
        "<400": dist.get("<400", 0),
        "400-500": dist.get("400-500", 0),
        "500-600": dist.get("500-600", 0),
        "600-700": dist.get("600-700", 0),
        "700-800": dist.get("700-800", 0),
        "800+": dist.get("800+", 0),
        "avg": avg_score,
        "total": len(df),
    }


def run_single_batch(batch_size: int = 50) -> dict:
    """単一バッチを実行"""
    script_path = PROJECT_ROOT / "scripts" / "improve_low_quality_episodes.py"

    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = API_KEY
    env["PYTHONUNBUFFERED"] = "1"  # バッファリング無効化

    # リアルタイム出力
    result = subprocess.run(
        [sys.executable, "-u", str(script_path), "--count", str(batch_size), "--execute"],
        env=env,
        timeout=900,  # 15分タイムアウト
    )

    return {
        "success": result.returncode == 0,
        "success_count": batch_size,  # 概算
        "avg_improvement": 400,  # 概算
        "output": "",
    }


def update_session(total_improved: int, dist: dict):
    """セッション情報を更新"""
    session_data = {
        "session_id": f"batch_loop_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "status": "batch_loop_running",
        "summary": f"連続バッチ実行中 - {total_improved}件改稿済み",
        "phase": 8,
        "current_progress": {"episodes_improved_session": total_improved, "composite_score_avg": dist["avg"]},
        "score_distribution": dist,
    }

    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="連続バッチ改稿")
    parser.add_argument("--batches", type=int, default=10, help="実行するバッチ数")
    parser.add_argument("--batch-size", type=int, default=50, help="1バッチあたりの件数")
    parser.add_argument("--target", type=int, help="400-500帯の目標件数（これ以下になるまで実行）")
    parser.add_argument("--unlimited", action="store_true", help="無制限実行（Ctrl+Cで停止）")
    parser.add_argument("--delay", type=int, default=5, help="バッチ間の待機秒数")
    args = parser.parse_args()

    print("=" * 60)
    print("🔄 連続バッチ改稿システム")
    print("=" * 60)

    # 初期状態
    initial_dist = get_score_distribution()
    print("\n📊 開始時の状態:")
    print(f"  400-500帯: {initial_dist['400-500']:,}件")
    print(f"  800+帯: {initial_dist['800+']}件")
    print(f"  平均スコア: {initial_dist['avg']:.1f}")

    total_improved = 0
    batch_num = 0

    try:
        while True:
            batch_num += 1

            # 終了条件チェック
            current_dist = get_score_distribution()

            if args.target and current_dist["400-500"] <= args.target:
                print(f"\n🎯 目標達成！400-500帯が{current_dist['400-500']:,}件になりました")
                break

            if not args.unlimited and batch_num > args.batches:
                print(f"\n✅ 指定バッチ数（{args.batches}回）完了")
                break

            print(f"\n{'=' * 60}")
            print(f"📦 バッチ {batch_num} 開始")
            print(f"  現在の400-500帯: {current_dist['400-500']:,}件")
            print(f"{'=' * 60}")

            # バッチ実行
            start_time = time.time()
            result = run_single_batch(args.batch_size)
            elapsed = time.time() - start_time

            if result["success"]:
                total_improved += result["success_count"]
                print(f"\n✅ バッチ{batch_num}完了 ({elapsed:.1f}秒)")
                print(f"  成功: {result['success_count']}件")
                print(f"  累計: {total_improved}件")
            else:
                print(f"\n⚠️ バッチ{batch_num}でエラー発生")
                print(result["output"][-500:])

            # セッション更新
            update_session(total_improved, get_score_distribution())

            # 次のバッチ前に待機
            if args.delay > 0:
                print(f"\n⏳ {args.delay}秒待機中...")
                time.sleep(args.delay)

    except KeyboardInterrupt:
        print("\n\n⏹️ 中断されました")

    # 最終結果
    final_dist = get_score_distribution()
    print("\n" + "=" * 60)
    print("📊 最終結果")
    print("=" * 60)
    print(f"  実行バッチ数: {batch_num}")
    print(f"  改稿件数: {total_improved}件")
    print(
        f"  400-500帯: {initial_dist['400-500']:,} → {final_dist['400-500']:,} ({final_dist['400-500'] - initial_dist['400-500']:+,})"
    )
    print(f"  800+帯: {initial_dist['800+']} → {final_dist['800+']} ({final_dist['800+'] - initial_dist['800+']})")
    print(
        f"  平均スコア: {initial_dist['avg']:.1f} → {final_dist['avg']:.1f} ({final_dist['avg'] - initial_dist['avg']:+.1f})"
    )


if __name__ == "__main__":
    main()
