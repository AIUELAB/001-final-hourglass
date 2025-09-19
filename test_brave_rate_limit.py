#!/usr/bin/env python3
"""
Brave Search APIのレート制限を徹底的に調査
様々な間隔でテストを実行し、最適な待機時間を特定
"""

import requests
import time
from datetime import datetime
import json
import statistics

def test_brave_api(api_key, query="test"):
    """Brave Search APIをテスト"""
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": query,
        "count": 1
    }

    try:
        start = time.time()
        response = requests.get(url, headers=headers, params=params, timeout=10)
        elapsed = time.time() - start

        return {
            'status': response.status_code,
            'elapsed': elapsed,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'status': -1,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def test_interval(api_key, interval_seconds, test_count=20):
    """特定の間隔でAPIをテスト"""
    results = []
    success_count = 0
    error_429_count = 0
    other_error_count = 0

    print(f"\n{'='*60}")
    print(f"🧪 テスト: {interval_seconds}秒間隔で{test_count}回実行")
    print(f"{'='*60}")

    start_time = time.time()

    for i in range(test_count):
        # API呼び出し
        result = test_brave_api(api_key, query=f"test_{i}")
        results.append(result)

        # 結果をカウント
        if result['status'] == 200:
            success_count += 1
            print("✅", end="", flush=True)
        elif result['status'] == 429:
            error_429_count += 1
            print("⚠️", end="", flush=True)
        else:
            other_error_count += 1
            print("❌", end="", flush=True)

        # 5回ごとに改行
        if (i + 1) % 5 == 0:
            print(f" [{i+1}/{test_count}]")

        # 指定された間隔で待機（最後のリクエスト後は待機しない）
        if i < test_count - 1:
            time.sleep(interval_seconds)

    total_time = time.time() - start_time

    # 統計を計算
    print(f"\n\n📊 結果:")
    print(f"  成功: {success_count}/{test_count} ({success_count/test_count*100:.1f}%)")
    print(f"  レート制限(429): {error_429_count}/{test_count} ({error_429_count/test_count*100:.1f}%)")
    print(f"  その他エラー: {other_error_count}/{test_count}")
    print(f"  総時間: {total_time:.1f}秒")
    print(f"  実効レート: {test_count/total_time*60:.1f}リクエスト/分")

    return {
        'interval': interval_seconds,
        'test_count': test_count,
        'success_count': success_count,
        'error_429_count': error_429_count,
        'success_rate': success_count / test_count * 100,
        'total_time': total_time,
        'requests_per_minute': test_count / total_time * 60
    }

def find_optimal_interval(api_key):
    """最適な間隔を見つける"""
    print("=" * 80)
    print("🔬 Brave Search API レート制限調査")
    print("=" * 80)

    # テストする間隔のリスト（秒）
    test_intervals = [
        0.1,   # 600req/min - 超高速（制限確実）
        0.2,   # 300req/min - 高速（現在の設定）
        0.5,   # 120req/min - 中速
        1.0,   # 60req/min - 標準
        1.5,   # 40req/min - やや遅い
        2.0,   # 30req/min - 遅い
        3.0,   # 20req/min - かなり遅い
        5.0,   # 12req/min - 非常に遅い
    ]

    all_results = []

    for interval in test_intervals:
        # 各間隔でテスト
        result = test_interval(api_key, interval, test_count=20)
        all_results.append(result)

        # レート制限に引っかかった場合は回復を待つ
        if result['error_429_count'] > 0:
            print(f"\n⏳ レート制限検出。30秒待機...")
            time.sleep(30)

    # 結果をまとめて表示
    print("\n" + "=" * 80)
    print("📈 総合結果")
    print("=" * 80)
    print(f"{'間隔(秒)':>10} | {'成功率(%)':>10} | {'429エラー':>10} | {'実効req/min':>12}")
    print("-" * 55)

    for r in all_results:
        print(f"{r['interval']:10.1f} | {r['success_rate']:10.1f} | {r['error_429_count']:10d} | {r['requests_per_minute']:12.1f}")

    # 最適な間隔を判定
    print("\n" + "=" * 80)
    print("🎯 分析結果")
    print("=" * 80)

    # 成功率100%の中で最速のものを探す
    perfect_results = [r for r in all_results if r['success_rate'] == 100]
    if perfect_results:
        optimal = min(perfect_results, key=lambda x: x['interval'])
        print(f"✅ 最適な間隔: {optimal['interval']}秒")
        print(f"   - 成功率: 100%")
        print(f"   - 実効速度: {optimal['requests_per_minute']:.1f}リクエスト/分")
    else:
        # 成功率が最も高いものを選ぶ
        optimal = max(all_results, key=lambda x: x['success_rate'])
        print(f"⚠️ 完全な成功は得られませんでした")
        print(f"   最良の間隔: {optimal['interval']}秒")
        print(f"   - 成功率: {optimal['success_rate']:.1f}%")
        print(f"   - 実効速度: {optimal['requests_per_minute']:.1f}リクエスト/分")

    # 結果を保存
    report = {
        'test_date': datetime.now().isoformat(),
        'test_intervals': test_intervals,
        'results': all_results,
        'optimal_interval': optimal['interval'],
        'optimal_success_rate': optimal['success_rate'],
        'optimal_requests_per_minute': optimal['requests_per_minute']
    }

    with open('brave_rate_limit_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📁 詳細レポート保存: brave_rate_limit_report.json")

    return optimal['interval']

def main():
    # APIキーを読み込み
    with open('/Users/admin/Documents/key/Brave Search API Key 2.txt', 'r') as f:
        api_key = f.read().strip()

    print("🔑 APIキー読み込み完了")

    # 最適な間隔を見つける
    optimal_interval = find_optimal_interval(api_key)

    # 推奨設定を表示
    print("\n" + "=" * 80)
    print("💡 推奨設定")
    print("=" * 80)
    print(f"time.sleep({optimal_interval})")
    print(f"これにより、レート制限を回避しながら最速で処理が可能です。")

    # 全3,569件の処理時間を予測
    total_records = 3569
    estimated_time = (total_records * optimal_interval) / 60
    print(f"\n⏱️ 全{total_records}件の推定処理時間: {estimated_time:.1f}分")

if __name__ == "__main__":
    main()