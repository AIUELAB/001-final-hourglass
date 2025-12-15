#!/usr/bin/env python3
"""
メモリ最適化版 統合エピソード評価器
- バッチ処理でメモリ使用を制限
- ガベージコレクション強化
- LLM評価をオプション化
- 進捗状況のリアルタイム表示
"""

import csv
import gc
import sys
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

from content_distribution_checker import ContentDistributionChecker
from hybrid_impact_evaluator import HybridImpactEvaluator
from episode_guardian import create_episode_guardian
from episode_relevance_checker import EpisodeRelevanceChecker


@dataclass
class OptimizedEvaluationResult:
    """最適化された評価結果（メモリ効率重視）"""
    episode_id: str
    person_name: str
    episode_age: int

    # Phase 1-2: 基本チェック
    compliance_passed: bool
    distribution_passed: bool
    age_specific_percentage: float

    # Phase 3: インパクト評価（簡略版）
    impact_passed: bool
    impact_score: int
    impact_keyword_score: int

    # 総合判定
    overall_passed: bool
    recommendation: str


class OptimizedEpisodeEvaluator:
    """メモリ最適化版エピソード評価システム"""

    def __init__(self, use_llm: bool = False, batch_size: int = 10):
        """
        Args:
            use_llm: LLM評価を使用するか（デフォルト: False）
            batch_size: バッチサイズ（デフォルト: 10）
        """
        self.guardian = create_episode_guardian()
        self.distribution_checker = ContentDistributionChecker()
        self.impact_evaluator = HybridImpactEvaluator(llm_provider="openai")
        self.use_llm = use_llm
        self.batch_size = batch_size

        # 統計情報
        self.stats = {
            'total': 0,
            'processed': 0,
            'compliance_failed': 0,
            'distribution_failed': 0,
            'impact_failed': 0,
            'overall_passed': 0
        }

    def evaluate_lightweight(self, episode: Dict) -> OptimizedEvaluationResult:
        """
        軽量版評価（メモリ効率重視）

        Args:
            episode: エピソードデータ

        Returns:
            OptimizedEvaluationResult: 最適化された評価結果
        """
        episode_id = episode['episode_id']
        person_name = episode['person_name']
        episode_age = int(episode['episode_age'])
        episode_text = episode['episode_text']

        # Phase 1: ルール準拠チェック
        compliance_result = self.guardian.validate_episode(episode)
        compliance_passed = compliance_result.is_valid

        if not compliance_passed:
            self.stats['compliance_failed'] += 1
            return OptimizedEvaluationResult(
                episode_id=episode_id,
                person_name=person_name,
                episode_age=episode_age,
                compliance_passed=False,
                distribution_passed=False,
                age_specific_percentage=0.0,
                impact_passed=False,
                impact_score=0,
                impact_keyword_score=0,
                overall_passed=False,
                recommendation="Phase 1: ルール準拠違反"
            )

        # Phase 2: 配分チェック
        distribution = self.distribution_checker.analyze_distribution(episode_text, episode_age)
        distribution_passed = distribution.compliant

        if not distribution_passed:
            self.stats['distribution_failed'] += 1
            return OptimizedEvaluationResult(
                episode_id=episode_id,
                person_name=person_name,
                episode_age=episode_age,
                compliance_passed=True,
                distribution_passed=False,
                age_specific_percentage=distribution.age_specific_percentage,
                impact_passed=False,
                impact_score=0,
                impact_keyword_score=0,
                overall_passed=False,
                recommendation=f"Phase 2: 配分違反（{distribution.age_specific_percentage:.1f}%）"
            )

        # Phase 3: 感情的インパクト評価（キーワードベースのみ）
        if not self.use_llm:
            # LLM無効時は簡易評価
            impact = self.impact_evaluator.evaluate(episode_text, person_name, episode_age)
            impact_passed = impact.keyword_score >= 30  # キーワードスコアのみで判定
            impact_score = impact.keyword_score
        else:
            # LLM有効時は完全評価
            impact = self.impact_evaluator.evaluate(episode_text, person_name, episode_age)
            impact_passed = impact.passed
            impact_score = impact.total_score

        if not impact_passed:
            self.stats['impact_failed'] += 1

        overall_passed = compliance_passed and distribution_passed and impact_passed

        if overall_passed:
            self.stats['overall_passed'] += 1
            recommendation = "✅ すべての基準を満たしています"
        elif not impact_passed:
            recommendation = f"Phase 3: インパクト不足（{impact_score}/50点）"
        else:
            recommendation = "✅ すべての基準を満たしています"

        return OptimizedEvaluationResult(
            episode_id=episode_id,
            person_name=person_name,
            episode_age=episode_age,
            compliance_passed=True,
            distribution_passed=True,
            age_specific_percentage=distribution.age_specific_percentage,
            impact_passed=impact_passed,
            impact_score=impact_score,
            impact_keyword_score=impact.keyword_score,
            overall_passed=overall_passed,
            recommendation=recommendation
        )

    def evaluate_all_batched(self, csv_path: str) -> List[OptimizedEvaluationResult]:
        """
        バッチ処理で全エピソードを評価

        Args:
            csv_path: CSVファイルパス

        Returns:
            List[OptimizedEvaluationResult]: 評価結果リスト
        """
        episodes = self._load_episodes(csv_path)
        self.stats['total'] = len(episodes)
        results = []

        print(f"\n{'='*80}")
        print(f"評価開始: {len(episodes)}件のエピソード")
        print(f"バッチサイズ: {self.batch_size}")
        print(f"LLM評価: {'有効' if self.use_llm else '無効（キーワードのみ）'}")
        print(f"{'='*80}\n")

        start_time = time.time()

        for i in range(0, len(episodes), self.batch_size):
            batch = episodes[i:i+self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(episodes) + self.batch_size - 1) // self.batch_size

            print(f"[バッチ {batch_num}/{total_batches}] 処理中... ", end='', flush=True)
            batch_start = time.time()

            # バッチ内の各エピソードを評価
            for episode in batch:
                result = self.evaluate_lightweight(episode)
                results.append(result)
                self.stats['processed'] += 1

            batch_time = time.time() - batch_start
            print(f"完了 ({batch_time:.1f}秒)")

            # バッチごとにガベージコレクション
            gc.collect()

            # 進捗表示
            elapsed = time.time() - start_time
            processed = self.stats['processed']
            remaining = self.stats['total'] - processed
            rate = processed / elapsed if elapsed > 0 else 0
            eta = remaining / rate if rate > 0 else 0

            print(f"  進捗: {processed}/{self.stats['total']} "
                  f"({processed/self.stats['total']*100:.1f}%) "
                  f"残り約{eta:.0f}秒\n")

        total_time = time.time() - start_time
        print(f"\n{'='*80}")
        print(f"評価完了: {total_time:.1f}秒")
        print(f"{'='*80}\n")

        return results

    def _load_episodes(self, csv_path: str) -> List[Dict]:
        """CSVファイルからエピソードを読み込み"""
        episodes = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                episodes.append({
                    'episode_id': row['episode_id'],
                    'person_name': row['person_name'],
                    'episode_age': int(row['episode_age']),
                    'episode_text': row['episode_text'],
                    'category': row.get('category', '')
                })
        return episodes

    def get_summary_report(self, results: List[OptimizedEvaluationResult]) -> str:
        """評価結果のサマリーレポート"""
        report = f"""
{'='*80}
最適化版評価サマリー
{'='*80}

総エピソード数: {self.stats['total']}
処理完了: {self.stats['processed']}
全基準合格: {self.stats['overall_passed']} ({self.stats['overall_passed']/self.stats['total']*100:.1f}%)

Phase別の問題:
  Phase 1 - ルール準拠違反: {self.stats['compliance_failed']}件
  Phase 2 - 配分違反: {self.stats['distribution_failed']}件
  Phase 3 - インパクト不足: {self.stats['impact_failed']}件

{'='*80}
"""

        # インパクト不足エピソードの詳細
        if self.stats['impact_failed'] > 0:
            report += f"\nインパクト不足エピソード（{self.stats['impact_failed']}件）:\n\n"
            impact_issues = [r for r in results if r.compliance_passed and
                           r.distribution_passed and not r.impact_passed]

            for r in sorted(impact_issues, key=lambda x: x.impact_score)[:10]:  # 上位10件のみ
                report += f"  {r.episode_id} {r.person_name}（{r.episode_age}歳）: "
                report += f"{r.impact_keyword_score}/50点\n"

        return report

    def save_results(self, results: List[OptimizedEvaluationResult], output_path: str):
        """評価結果をCSVに保存"""
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = [
                'episode_id', 'person_name', 'episode_age',
                'overall_passed', 'compliance_passed', 'distribution_passed',
                'impact_passed', 'age_specific_pct', 'impact_keyword_score',
                'recommendation'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for r in results:
                writer.writerow({
                    'episode_id': r.episode_id,
                    'person_name': r.person_name,
                    'episode_age': r.episode_age,
                    'overall_passed': r.overall_passed,
                    'compliance_passed': r.compliance_passed,
                    'distribution_passed': r.distribution_passed,
                    'impact_passed': r.impact_passed,
                    'age_specific_pct': f"{r.age_specific_percentage:.1f}",
                    'impact_keyword_score': r.impact_keyword_score,
                    'recommendation': r.recommendation
                })


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法: python3 optimized_episode_evaluator.py <episodes.csv> [--use-llm] [--batch-size N]")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_path = csv_path.replace('.csv', '_optimized_evaluation.csv')

    # オプション解析
    use_llm = '--use-llm' in sys.argv
    batch_size = 10
    if '--batch-size' in sys.argv:
        idx = sys.argv.index('--batch-size')
        if idx + 1 < len(sys.argv):
            batch_size = int(sys.argv[idx + 1])

    print(f"{'='*80}")
    print(f"メモリ最適化版 統合エピソード評価システム")
    print(f"{'='*80}")
    print(f"入力: {csv_path}")
    print(f"出力: {output_path}")
    print(f"LLM評価: {'有効' if use_llm else '無効（推奨）'}")
    print(f"バッチサイズ: {batch_size}")
    print(f"{'='*80}\n")

    # 評価器初期化
    evaluator = OptimizedEpisodeEvaluator(use_llm=use_llm, batch_size=batch_size)

    # 全エピソード評価（バッチ処理）
    results = evaluator.evaluate_all_batched(csv_path)

    # サマリー表示
    print(evaluator.get_summary_report(results))

    # 結果を保存
    evaluator.save_results(results, output_path)
    print(f"✅ 評価結果を保存: {output_path}\n")


if __name__ == '__main__':
    main()
