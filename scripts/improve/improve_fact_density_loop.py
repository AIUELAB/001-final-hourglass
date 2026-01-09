#!/usr/bin/env python3
"""
factual_density改善ループスクリプト

factual_density3.0-3.5のエピソードがなくなるまで繰り返し改稿

使用方法:
    ANTHROPIC_API_KEY="..." ./venv/bin/python scripts/improve_fact_density_loop.py

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BATCH_SIZE = 100
MAX_ITERATIONS = 10  # 最大10回 = 1000件まで


def count_remaining():
    """残りの低品質エピソード数を取得"""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    low_fact = df[(df["factual_density"] >= 3.0) & (df["factual_density"] < 3.5)]
    return len(low_fact)


def run_batch():
    """1バッチ実行"""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "improve_fact_density.py"),
        "--count",
        str(BATCH_SIZE),
        "--execute",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def main():
    print("=" * 60)
    print("📊 factual_density改善ループ開始")
    print("=" * 60)

    for iteration in range(MAX_ITERATIONS):
        remaining = count_remaining()
        print(f"\n[ループ {iteration + 1}/{MAX_ITERATIONS}] 残り: {remaining}件")

        if remaining == 0:
            print("✅ すべての低品質エピソードが改善されました！")
            break

        print(f"  バッチ実行中（{min(BATCH_SIZE, remaining)}件）...")
        success = run_batch()

        if not success:
            print("  ❌ バッチ実行失敗")
            break

        # 少し待機
        time.sleep(2)

    # 最終結果
    final_remaining = count_remaining()
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    print("\n" + "=" * 60)
    print("📊 ループ完了")
    print("=" * 60)
    print(f"  残り低品質: {final_remaining}件")
    print(f"  factual_density 平均: {df['factual_density'].mean():.2f}")
    print(f"  composite_score 平均: {df['composite_score'].mean():.1f}")


if __name__ == "__main__":
    main()
