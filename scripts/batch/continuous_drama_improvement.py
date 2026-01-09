#!/usr/bin/env python3
"""
継続的ドラマ品質改善スクリプト

バックグラウンドで継続的にドラマ品質改善バッチを実行します。
目標達成または最大イテレーション数に達するまで自動実行。

使用例:
    # 目標70%まで改善（デフォルト）
    python scripts/continuous_drama_improvement.py

    # 目標80%まで改善、バッチサイズ50
    python scripts/continuous_drama_improvement.py --target 80 --batch-size 50

    # 最大5イテレーションまで
    python scripts/continuous_drama_improvement.py --max-iterations 5

    # バックグラウンド実行
    nohup python scripts/continuous_drama_improvement.py --target 75 > logs/drama_improvement.log 2>&1 &
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# バッファリング無効化
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


def get_drama_quality() -> dict:
    """現在のドラマ品質を取得"""
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    surprise = df["surprise_score"].dropna()
    total = len(surprise)

    high = (surprise >= 7.0).sum()
    mid = ((surprise >= 5.0) & (surprise < 7.0)).sum()
    low = (surprise < 5.0).sum()

    high_rate = high / total * 100
    mid_rate = mid / total * 100
    low_rate = low / total * 100

    drama_quality = high_rate + mid_rate * 0.5

    return {
        "total": total,
        "high": high,
        "mid": mid,
        "low": low,
        "high_rate": high_rate,
        "mid_rate": mid_rate,
        "low_rate": low_rate,
        "drama_quality": drama_quality,
    }


def run_improvement_batch(batch_size: int, threshold: float) -> bool:
    """改善バッチを実行"""
    cmd = [
        "./venv/bin/python",
        "scripts/regenerate_with_surprise.py",
        "--threshold",
        str(threshold),
        "--limit",
        str(batch_size),
        "--execute",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30分タイムアウト
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("  ⚠️ タイムアウト（30分）")
        return False
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="継続的ドラマ品質改善")
    parser.add_argument("--target", type=float, default=70.0, help="目標ドラマ品質スコア（デフォルト: 70%%）")
    parser.add_argument("--batch-size", type=int, default=100, help="1バッチあたりの処理件数（デフォルト: 100）")
    parser.add_argument("--threshold", type=float, default=7.0, help="改善対象閾値（デフォルト: 7.0）")
    parser.add_argument("--max-iterations", type=int, default=20, help="最大イテレーション数（デフォルト: 20）")
    parser.add_argument("--interval", type=int, default=10, help="バッチ間の待機秒数（デフォルト: 10）")
    args = parser.parse_args()

    print("=" * 70)
    print("🔄 継続的ドラマ品質改善")
    print("=" * 70)
    print(f"  目標: {args.target}%")
    print(f"  バッチサイズ: {args.batch_size}")
    print(f"  改善閾値: {args.threshold}")
    print(f"  最大イテレーション: {args.max_iterations}")
    print("=" * 70)

    # ログディレクトリ作成
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    start_time = datetime.now()
    total_improved = 0

    # 初期状態
    initial = get_drama_quality()
    print("\n📊 初期状態:")
    print(f"  ドラマ品質: {initial['drama_quality']:.1f}%")
    print(f"  高品質(>=7.0): {initial['high']}件 ({initial['high_rate']:.1f}%)")
    print(f"  中品質(5-7): {initial['mid']}件 ({initial['mid_rate']:.1f}%)")

    if initial["drama_quality"] >= args.target:
        print(f"\n✅ 既に目標（{args.target}%）を達成しています！")
        return

    for iteration in range(1, args.max_iterations + 1):
        print(f"\n{'='*70}")
        print(f"📦 イテレーション {iteration}/{args.max_iterations}")
        print(f"   開始時刻: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70)

        # バッチ実行
        success = run_improvement_batch(args.batch_size, args.threshold)

        if not success:
            print("  ❌ バッチ実行失敗")
            continue

        # 結果確認
        current = get_drama_quality()
        improved = current["high"] - initial["high"]
        total_improved += max(0, improved - total_improved)

        print("\n📊 現在の状態:")
        print(f"  ドラマ品質: {current['drama_quality']:.1f}%")
        print(f"  高品質(>=7.0): {current['high']}件 ({current['high_rate']:.1f}%)")
        print(f"  改善: +{current['high'] - initial['high']}件 (初期比)")

        # 目標達成チェック
        if current["drama_quality"] >= args.target:
            print(f"\n🎉 目標達成！ドラマ品質 {current['drama_quality']:.1f}%")
            break

        # 改善余地チェック
        if current["mid"] == 0:
            print("\n✅ 中品質エピソードがなくなりました")
            break

        # 次のバッチまで待機
        if iteration < args.max_iterations:
            print(f"\n⏳ {args.interval}秒待機...")
            time.sleep(args.interval)

    # 最終サマリー
    final = get_drama_quality()
    elapsed = datetime.now() - start_time

    print("\n" + "=" * 70)
    print("📊 最終サマリー")
    print("=" * 70)
    print(f"  実行時間: {elapsed}")
    print(f"  イテレーション: {iteration}")
    print(f"  ドラマ品質: {initial['drama_quality']:.1f}% → {final['drama_quality']:.1f}%")
    print(f"  高品質件数: {initial['high']} → {final['high']} (+{final['high'] - initial['high']})")
    print(f"  目標達成: {'✅' if final['drama_quality'] >= args.target else '❌'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
