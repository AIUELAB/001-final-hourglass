#!/usr/bin/env python3
"""
バッチ高品質エピソード生成システム

機能:
1. 100エピソードの一括高品質化
2. 並列処理によるレート制限対応
3. 進捗表示とエラーハンドリング
4. 詳細なレポート生成
"""

import csv
import json
import time
import concurrent.futures
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from high_quality_episode_generator import (
    HighQualityEpisodeGenerator,
    GenerationResult
)


@dataclass
class BatchResult:
    """バッチ処理結果"""
    total_episodes: int
    successful: int
    failed: int
    avg_score: float
    avg_iterations: float
    pass_rate: float
    grade_distribution: Dict[str, int]
    total_cost: float
    processing_time: float
    results: List[GenerationResult]


class BatchHighQualityGenerator:
    """バッチ高品質エピソード生成システム"""

    def __init__(
        self,
        provider: str = "openai",
        mode: str = "iterative",
        max_workers: int = 3,
        max_iterations: int = 3,
        pass_threshold: int = 60
    ):
        """
        Args:
            provider: LLMプロバイダー
            mode: 生成モード
            max_workers: 並列ワーカー数
            max_iterations: 最大反復回数
            pass_threshold: 合格スコア閾値
        """
        self.provider = provider
        self.mode = mode
        self.max_workers = max_workers
        self.max_iterations = max_iterations
        self.pass_threshold = pass_threshold

        self.generator = HighQualityEpisodeGenerator(
            provider=provider,
            mode=mode,
            max_iterations=max_iterations,
            pass_threshold=pass_threshold
        )

    def process_from_csv(
        self,
        input_csv: str,
        output_csv: str,
        limit: Optional[int] = None,
        verbose: bool = True
    ) -> BatchResult:
        """
        CSVファイルからエピソードを読み込んで一括処理

        Args:
            input_csv: 入力CSVファイル
            output_csv: 出力CSVファイル
            limit: 処理件数制限（テスト用）
            verbose: 進捗表示

        Returns:
            BatchResult: バッチ処理結果
        """
        start_time = time.time()

        # CSV読み込み
        episodes = []
        with open(input_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            episodes = list(reader)

        if limit:
            episodes = episodes[:limit]

        if verbose:
            print(f"{'='*80}")
            print(f"バッチ高品質エピソード生成")
            print(f"{'='*80}")
            print(f"入力: {input_csv}")
            print(f"件数: {len(episodes)}件")
            print(f"モード: {self.mode}")
            print(f"並列数: {self.max_workers}")
            print(f"{'='*80}\n")

        # 並列処理
        results = self._process_parallel(episodes, verbose)

        # 結果の保存
        self._save_results(results, output_csv)

        # 統計計算
        processing_time = time.time() - start_time
        batch_result = self._calculate_statistics(results, processing_time)

        if verbose:
            self._print_report(batch_result, output_csv)

        return batch_result

    def process_episodes_list(
        self,
        episodes: List[Dict],
        output_csv: str,
        verbose: bool = True
    ) -> BatchResult:
        """
        エピソードリストを直接処理

        Args:
            episodes: エピソードリスト
            output_csv: 出力CSVファイル
            verbose: 進捗表示

        Returns:
            BatchResult: バッチ処理結果
        """
        start_time = time.time()

        if verbose:
            print(f"{'='*80}")
            print(f"バッチ高品質エピソード生成")
            print(f"{'='*80}")
            print(f"件数: {len(episodes)}件")
            print(f"モード: {self.mode}")
            print(f"{'='*80}\n")

        # 並列処理
        results = self._process_parallel(episodes, verbose)

        # 結果の保存
        self._save_results(results, output_csv)

        # 統計計算
        processing_time = time.time() - start_time
        batch_result = self._calculate_statistics(results, processing_time)

        if verbose:
            self._print_report(batch_result, output_csv)

        return batch_result

    def _process_parallel(
        self,
        episodes: List[Dict],
        verbose: bool
    ) -> List[GenerationResult]:
        """並列処理を実行"""

        results = []
        completed = 0
        total = len(episodes)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # タスクを投入
            future_to_episode = {
                executor.submit(self._process_single_episode, ep): ep
                for ep in episodes
            }

            # 完了を待機
            for future in concurrent.futures.as_completed(future_to_episode):
                episode = future_to_episode[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1

                    if verbose:
                        print(f"\r進捗: {completed}/{total} ({completed/total*100:.1f}%) - "
                              f"{result.person_name}: {result.score}点 "
                              f"{'✅' if result.passed else '❌'}", end="")

                except Exception as e:
                    print(f"\nエラー: {episode.get('person_name', 'Unknown')} - {str(e)}")
                    completed += 1

                # レート制限対策
                time.sleep(0.5)

        if verbose:
            print("\n")

        return results

    def _process_single_episode(self, episode_data: Dict) -> GenerationResult:
        """1エピソードを処理"""

        person_name = episode_data.get('person_name', episode_data.get('display_name', 'Unknown'))
        age = int(episode_data.get('episode_age', episode_data.get('age', 30)))
        episode_id = episode_data.get('episode_id', f"EP_{person_name}_{age}")
        wikipedia_data = episode_data.get('wikipedia_summary', None)

        return self.generator.generate(
            person_name=person_name,
            age=age,
            wikipedia_data=wikipedia_data,
            episode_id=episode_id
        )

    def _save_results(self, results: List[GenerationResult], output_csv: str):
        """結果をCSVファイルに保存"""

        with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # ヘッダー
            writer.writerow([
                'episode_id',
                'person_name',
                'age',
                'episode_text',
                'score',
                'grade',
                'iterations',
                'passed',
                'mode',
                'cost_estimate',
                'character_count'
            ])

            # データ
            for result in results:
                writer.writerow([
                    result.episode_id,
                    result.person_name,
                    result.age,
                    result.episode_text,
                    result.score,
                    result.grade,
                    result.iterations,
                    result.passed,
                    result.mode,
                    f"${result.cost_estimate:.4f}",
                    len(result.episode_text)
                ])

        # JSON形式でも保存
        json_file = output_csv.replace('.csv', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=2)

    def _calculate_statistics(
        self,
        results: List[GenerationResult],
        processing_time: float
    ) -> BatchResult:
        """統計情報を計算"""

        total = len(results)
        successful = sum(1 for r in results if r.passed)
        failed = total - successful

        avg_score = sum(r.score for r in results) / total if total > 0 else 0
        avg_iterations = sum(r.iterations for r in results) / total if total > 0 else 0
        pass_rate = successful / total if total > 0 else 0

        # グレード分布
        grade_distribution = {}
        for result in results:
            grade_distribution[result.grade] = grade_distribution.get(result.grade, 0) + 1

        # 総コスト
        total_cost = sum(r.cost_estimate for r in results)

        return BatchResult(
            total_episodes=total,
            successful=successful,
            failed=failed,
            avg_score=avg_score,
            avg_iterations=avg_iterations,
            pass_rate=pass_rate,
            grade_distribution=grade_distribution,
            total_cost=total_cost,
            processing_time=processing_time,
            results=results
        )

    def _print_report(self, batch_result: BatchResult, output_csv: str):
        """レポートを表示"""

        print(f"""
{'='*80}
バッチ処理完了
{'='*80}

【処理結果】
総エピソード数: {batch_result.total_episodes}件
成功: {batch_result.successful}件 ({batch_result.pass_rate*100:.1f}%)
失敗: {batch_result.failed}件 ({batch_result.failed/batch_result.total_episodes*100:.1f}%)

【品質指標】
平均スコア: {batch_result.avg_score:.1f}点
平均反復回数: {batch_result.avg_iterations:.1f}回

【グレード分布】
""")
        for grade in ['S', 'A', 'B', 'C', 'D']:
            count = batch_result.grade_distribution.get(grade, 0)
            percentage = count / batch_result.total_episodes * 100 if batch_result.total_episodes > 0 else 0
            print(f"{grade}評価: {count}件 ({percentage:.1f}%)")

        print(f"""
【コスト・時間】
処理時間: {batch_result.processing_time:.1f}秒 ({batch_result.processing_time/60:.1f}分)
総コスト: ${batch_result.total_cost:.3f}
1エピソード平均: ${batch_result.total_cost/batch_result.total_episodes:.4f}

【出力】
CSV: {output_csv}
JSON: {output_csv.replace('.csv', '.json')}

{'='*80}
""")

        # トップ5とワースト5を表示
        sorted_results = sorted(batch_result.results, key=lambda x: x.score, reverse=True)

        print("【トップ5エピソード】")
        for i, result in enumerate(sorted_results[:5], 1):
            print(f"{i}. {result.person_name}（{result.age}歳）: {result.score}点（{result.grade}）")
            print(f"   {result.episode_text[:100]}...\n")

        print("\n【ワースト5エピソード】")
        for i, result in enumerate(sorted_results[-5:], 1):
            print(f"{i}. {result.person_name}（{result.age}歳）: {result.score}点（{result.grade}）")
            print(f"   {result.episode_text[:100]}...\n")


def test_batch_generator():
    """バッチ生成システムのテスト"""

    print("="*80)
    print("バッチ高品質エピソード生成 - テスト")
    print("="*80)

    # テストデータ作成
    test_episodes = [
        {
            'person_name': '新垣結衣',
            'age': 18,
            'episode_id': 'EP052',
            'wikipedia_summary': None
        },
        {
            'person_name': 'Ado',
            'age': 21,
            'episode_id': 'EP001',
            'wikipedia_summary': None
        },
        {
            'person_name': '川端康成',
            'age': 27,
            'episode_id': 'EP003',
            'wikipedia_summary': None
        },
        {
            'person_name': '又吉直樹',
            'age': 35,
            'episode_id': 'EP010',
            'wikipedia_summary': None
        },
        {
            'person_name': '室伏広治',
            'age': 38,
            'episode_id': 'EP020',
            'wikipedia_summary': None
        }
    ]

    # プロンプト改善モードでテスト
    print("\n【モード: prompt_optimized】")
    batch_gen = BatchHighQualityGenerator(
        provider="openai",
        mode="prompt_optimized",
        max_workers=3
    )

    result = batch_gen.process_episodes_list(
        test_episodes,
        output_csv="test_batch_prompt_optimized.csv",
        verbose=True
    )

    # 反復改善モードでテスト
    print("\n\n【モード: iterative】")
    batch_gen2 = BatchHighQualityGenerator(
        provider="openai",
        mode="iterative",
        max_workers=2,  # 反復モードは負荷が高いので並列数を減らす
        max_iterations=3
    )

    result2 = batch_gen2.process_episodes_list(
        test_episodes[:3],  # 3件のみでテスト
        output_csv="test_batch_iterative.csv",
        verbose=True
    )


if __name__ == '__main__':
    test_batch_generator()
