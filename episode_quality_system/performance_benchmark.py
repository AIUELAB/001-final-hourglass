#!/usr/bin/env python3
"""
パフォーマンスベンチマーク
システムの性能を測定し、ボトルネックを特定
"""

import time
import json
import statistics
from typing import List, Dict, Tuple
from dataclasses import dataclass
import concurrent.futures
from unified_episode_factory_v2 import UnifiedEpisodeFactory, EpisodeGenerationRequest

@dataclass
class BenchmarkResult:
    """ベンチマーク結果"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_second: float
    success_rate: float
    avg_quality_score: float

class PerformanceBenchmark:
    """パフォーマンスベンチマーク"""

    def __init__(self):
        self.factory = UnifiedEpisodeFactory(use_optimized=True)

    def measure_single_request(self, person_name: str, age: int, category: str) -> Tuple[float, bool, float]:
        """
        単一リクエストの測定

        Returns:
            (レスポンスタイム[ms], 成功フラグ, 品質スコア)
        """
        start_time = time.time()

        request = EpisodeGenerationRequest(
            person_name=person_name,
            age=age,
            category=category,
            min_quality_score=70.0,
            use_optimized=True
        )

        response = self.factory.generate(request)

        elapsed_time_ms = (time.time() - start_time) * 1000
        success = response.success
        quality_score = response.quality_score if response.success else 0.0

        return elapsed_time_ms, success, quality_score

    def run_sequential_benchmark(self, test_cases: List[Tuple[str, int, str]],
                                iterations: int = 10) -> BenchmarkResult:
        """
        逐次実行ベンチマーク

        Args:
            test_cases: テストケースのリスト
            iterations: 各ケースの実行回数

        Returns:
            ベンチマーク結果
        """
        print("\n🔄 逐次実行ベンチマーク開始...")

        response_times = []
        successful_count = 0
        quality_scores = []

        total_start = time.time()

        for _ in range(iterations):
            for person_name, age, category in test_cases:
                response_time, success, quality_score = self.measure_single_request(
                    person_name, age, category
                )
                response_times.append(response_time)
                if success:
                    successful_count += 1
                    quality_scores.append(quality_score)

        total_time = time.time() - total_start
        total_requests = len(test_cases) * iterations

        return self._calculate_results(
            response_times, successful_count, total_requests,
            total_time, quality_scores
        )

    def run_concurrent_benchmark(self, test_cases: List[Tuple[str, int, str]],
                                iterations: int = 10,
                                max_workers: int = 4) -> BenchmarkResult:
        """
        並行実行ベンチマーク

        Args:
            test_cases: テストケースのリスト
            iterations: 各ケースの実行回数
            max_workers: 最大並行ワーカー数

        Returns:
            ベンチマーク結果
        """
        print(f"\n⚡ 並行実行ベンチマーク開始（ワーカー数: {max_workers}）...")

        response_times = []
        successful_count = 0
        quality_scores = []

        total_start = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for _ in range(iterations):
                for person_name, age, category in test_cases:
                    future = executor.submit(
                        self.measure_single_request, person_name, age, category
                    )
                    futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                response_time, success, quality_score = future.result()
                response_times.append(response_time)
                if success:
                    successful_count += 1
                    quality_scores.append(quality_score)

        total_time = time.time() - total_start
        total_requests = len(test_cases) * iterations

        return self._calculate_results(
            response_times, successful_count, total_requests,
            total_time, quality_scores
        )

    def _calculate_results(self, response_times: List[float],
                          successful_count: int,
                          total_requests: int,
                          total_time: float,
                          quality_scores: List[float]) -> BenchmarkResult:
        """結果を計算"""
        sorted_times = sorted(response_times)

        return BenchmarkResult(
            total_requests=total_requests,
            successful_requests=successful_count,
            failed_requests=total_requests - successful_count,
            avg_response_time_ms=statistics.mean(response_times),
            min_response_time_ms=min(response_times),
            max_response_time_ms=max(response_times),
            median_response_time_ms=statistics.median(response_times),
            p95_response_time_ms=sorted_times[int(len(sorted_times) * 0.95)],
            p99_response_time_ms=sorted_times[int(len(sorted_times) * 0.99)],
            requests_per_second=total_requests / total_time,
            success_rate=(successful_count / total_requests) * 100,
            avg_quality_score=statistics.mean(quality_scores) if quality_scores else 0.0
        )

    def print_results(self, result: BenchmarkResult, title: str):
        """結果を表示"""
        print(f"\n{'=' * 60}")
        print(f"📊 {title}")
        print('=' * 60)

        print(f"総リクエスト数: {result.total_requests}")
        print(f"成功: {result.successful_requests} | 失敗: {result.failed_requests}")
        print(f"成功率: {result.success_rate:.1f}%")
        print(f"平均品質スコア: {result.avg_quality_score:.1f}/100")

        print(f"\nレスポンスタイム:")
        print(f"  平均: {result.avg_response_time_ms:.2f}ms")
        print(f"  中央値: {result.median_response_time_ms:.2f}ms")
        print(f"  最小: {result.min_response_time_ms:.2f}ms")
        print(f"  最大: {result.max_response_time_ms:.2f}ms")
        print(f"  95パーセンタイル: {result.p95_response_time_ms:.2f}ms")
        print(f"  99パーセンタイル: {result.p99_response_time_ms:.2f}ms")

        print(f"\nスループット: {result.requests_per_second:.2f} req/s")

def main():
    """メイン処理"""
    print("=" * 60)
    print("⚡ パフォーマンスベンチマーク")
    print("=" * 60)

    # テストケース
    test_cases = [
        ("大谷翔平", 29, "sports"),
        ("新垣結衣", 28, "entertainment"),
        ("山中伸弥", 50, "science"),
        ("孫正義", 33, "business"),
        ("村上春樹", 40, "literature")
    ]

    benchmark = PerformanceBenchmark()

    # 逐次実行ベンチマーク
    sequential_result = benchmark.run_sequential_benchmark(test_cases, iterations=5)
    benchmark.print_results(sequential_result, "逐次実行結果")

    # 並行実行ベンチマーク（2ワーカー）
    concurrent_2_result = benchmark.run_concurrent_benchmark(test_cases, iterations=5, max_workers=2)
    benchmark.print_results(concurrent_2_result, "並行実行結果（2ワーカー）")

    # 並行実行ベンチマーク（4ワーカー）
    concurrent_4_result = benchmark.run_concurrent_benchmark(test_cases, iterations=5, max_workers=4)
    benchmark.print_results(concurrent_4_result, "並行実行結果（4ワーカー）")

    # 結果を保存
    results = {
        "sequential": sequential_result.__dict__,
        "concurrent_2": concurrent_2_result.__dict__,
        "concurrent_4": concurrent_4_result.__dict__,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n✅ ベンチマーク結果を benchmark_results.json に保存しました")

    # パフォーマンス判定
    print("\n" + "=" * 60)
    print("🎯 パフォーマンス判定")
    print("=" * 60)

    if sequential_result.avg_response_time_ms < 100:
        print("✅ 優秀: 平均レスポンスタイム < 100ms")
    elif sequential_result.avg_response_time_ms < 500:
        print("⚠️ 良好: 平均レスポンスタイム < 500ms")
    else:
        print("❌ 要改善: 平均レスポンスタイム >= 500ms")

    if sequential_result.success_rate >= 99:
        print("✅ 優秀: 成功率 >= 99%")
    elif sequential_result.success_rate >= 95:
        print("⚠️ 良好: 成功率 >= 95%")
    else:
        print("❌ 要改善: 成功率 < 95%")

if __name__ == "__main__":
    main()
