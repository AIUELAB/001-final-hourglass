#!/usr/bin/env python3
"""
意外性スコア自動改善スクリプト

指定バッチ数まで自動で意外性スコア改善を実行する

使用方法:
    # 17バッチ実行（デフォルト）
    ANTHROPIC_API_KEY="..." ./venv/bin/python scripts/auto_surprise_improvement.py

    # バッチ数指定
    ANTHROPIC_API_KEY="..." ./venv/bin/python scripts/auto_surprise_improvement.py --batches 10

    # バッチサイズ指定
    ANTHROPIC_API_KEY="..." ./venv/bin/python scripts/auto_surprise_improvement.py --batch-size 30

    # ドライラン
    ANTHROPIC_API_KEY="..." ./venv/bin/python scripts/auto_surprise_improvement.py --dry-run

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# インポート
from scripts.improve_surprise_score import run_improvement

# パス
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"
SESSION_STATUS = PROJECT_ROOT / ".session" / "STATUS.md"


def get_low_surprise_count() -> int:
    """意外性スコア3.0未満の件数を取得"""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    return len(df[df["意外性スコア"] < 3.0])


def get_score_distribution() -> dict:
    """スコア分布を取得"""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    col = "意外性スコア"
    return {
        "under_3": len(df[df[col] < 3.0]),
        "range_3_5": len(df[(df[col] >= 3.0) & (df[col] < 5.0)]),
        "range_5_7": len(df[(df[col] >= 5.0) & (df[col] < 7.0)]),
        "over_7": len(df[df[col] >= 7.0]),
    }


def run_auto_improvement(max_batches: int, batch_size: int, dry_run: bool, delay: int):
    """自動バッチ実行"""
    print("=" * 60)
    print("🚀 意外性スコア自動改善")
    print("=" * 60)

    initial_count = get_low_surprise_count()
    print(f"  初期状態: 意外性スコア < 3.0 = {initial_count}件")
    print(f"  最大バッチ数: {max_batches}")
    print(f"  バッチサイズ: {batch_size}")
    print(f"  バッチ間隔: {delay}秒")

    if dry_run:
        print("\n⚠️ ドライラン: 実際の改善は行いません")
        return

    total_improved = 0
    total_failed = 0
    batch_results = []

    for batch_num in range(1, max_batches + 1):
        # 残件確認
        remaining = get_low_surprise_count()
        if remaining == 0:
            print("\n✅ 全エピソード改善完了！")
            break

        print(f"\n{'='*60}")
        print(f"📦 Batch {batch_num}/{max_batches} 開始")
        print(f"   残り: {remaining}件")
        print(f"{'='*60}")

        # バッチ実行
        start_time = time.time()
        try:
            results = run_improvement(min(batch_size, remaining), execute=True)

            improved = len(results.get("improved", []))
            partial = len(results.get("partial", []))
            failed = len(results.get("failed", []))

            total_improved += improved + partial
            total_failed += failed

            elapsed = time.time() - start_time

            batch_results.append(
                {
                    "batch": batch_num,
                    "improved": improved,
                    "partial": partial,
                    "failed": failed,
                    "elapsed": elapsed,
                    "remaining": get_low_surprise_count(),
                }
            )

            print(f"\n📊 Batch {batch_num} 結果:")
            print(f"   成功: {improved}件, 部分: {partial}件, 失敗: {failed}件")
            print(f"   所要時間: {elapsed:.1f}秒")

        except Exception as e:
            print(f"\n❌ Batch {batch_num} エラー: {e}")
            batch_results.append({"batch": batch_num, "error": str(e)})
            # エラー時は少し長めに待機
            time.sleep(delay * 2)
            continue

        # 次のバッチ前に待機
        if batch_num < max_batches and get_low_surprise_count() > 0:
            print(f"\n⏳ {delay}秒待機中...")
            time.sleep(delay)

    # 最終サマリー
    final_count = get_low_surprise_count()
    distribution = get_score_distribution()

    print("\n" + "=" * 60)
    print("📊 最終サマリー")
    print("=" * 60)
    print(f"  実行バッチ数: {len(batch_results)}")
    print(f"  総改善数: {total_improved}件")
    print(f"  総失敗数: {total_failed}件")
    print(f"  改善前: {initial_count}件 → 改善後: {final_count}件")
    print("\n  スコア分布:")
    print(f"    < 3.0: {distribution['under_3']}件")
    print(f"    3.0-5.0: {distribution['range_3_5']}件")
    print(f"    5.0-7.0: {distribution['range_5_7']}件")
    print(f"    7.0+: {distribution['over_7']}件")

    # レポート保存
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"auto_surprise_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "max_batches": max_batches,
                "batch_size": batch_size,
                "initial_count": initial_count,
                "final_count": final_count,
                "total_improved": total_improved,
                "total_failed": total_failed,
                "batch_results": batch_results,
                "final_distribution": distribution,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n📝 レポート保存: {report_path}")

    return batch_results


def main():
    parser = argparse.ArgumentParser(description="意外性スコア自動改善スクリプト")
    parser.add_argument("--batches", type=int, default=17, help="最大バッチ数 (default: 17)")
    parser.add_argument("--batch-size", type=int, default=50, help="バッチサイズ (default: 50)")
    parser.add_argument("--delay", type=int, default=5, help="バッチ間隔（秒） (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン")
    args = parser.parse_args()

    # API キー確認
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
        sys.exit(1)

    run_auto_improvement(max_batches=args.batches, batch_size=args.batch_size, dry_run=args.dry_run, delay=args.delay)


if __name__ == "__main__":
    main()
