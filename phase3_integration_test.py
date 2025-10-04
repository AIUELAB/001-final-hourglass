"""
Phase 3 Integration Test
=========================

SmartIterationEngineを実際のLLMと統合してテスト

実行コマンド:
    python3 phase3_integration_test.py --provider openai --count 10

環境変数:
    OPENAI_API_KEY または ANTHROPIC_API_KEY
"""

import os
import sys
import argparse
import json
from typing import List, Dict
from datetime import datetime

from smart_iteration_engine import SmartIterationEngine, GenerationResult
from instant_quality_gate import InstantQualityGate


# テスト用人物データ（Few-Shot DBから選定）
TEST_PEOPLE = [
    {"name": "新垣結衣", "age": 18, "category": "エンターテインメント"},
    {"name": "松下幸之助", "age": 56, "category": "ビジネス"},
    {"name": "イチロー", "age": 45, "category": "スポーツ"},
    {"name": "大谷翔平", "age": 29, "category": "スポーツ"},
    {"name": "羽生結弦", "age": 19, "category": "スポーツ"},
    {"name": "久保建英", "age": 20, "category": "スポーツ"},
    {"name": "堀江貴文", "age": 24, "category": "ビジネス"},
    {"name": "村上春樹", "age": 30, "category": "文学"},
    {"name": "本田宗一郎", "age": 58, "category": "ビジネス"},
    {"name": "宮崎駿", "age": 46, "category": "アニメ"},
]


class Phase3IntegrationTest:
    """Phase 3統合テストクラス"""

    def __init__(
        self,
        llm_provider: str = "openai",
        model: str = None,
        max_iterations: int = 3,
        target_score: float = 8.0
    ):
        """
        初期化

        Args:
            llm_provider: LLMプロバイダー (openai/anthropic)
            model: モデル名
            max_iterations: 最大反復回数
            target_score: 目標スコア
        """
        self.llm_provider = llm_provider
        self.model = model
        self.max_iterations = max_iterations
        self.target_score = target_score

        # 環境変数チェック
        if llm_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY環境変数が設定されていません")
        elif llm_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")

        # エンジン初期化
        self.engine = SmartIterationEngine(
            max_iterations=max_iterations,
            target_gate_score=target_score,
            llm_provider=llm_provider,
            model=model,
            enable_llm_evaluation=True  # Phase 4: LLM評価を有効化
        )

        self.quality_gate = InstantQualityGate()

    def run_single_test(self, person: Dict) -> Dict:
        """
        単一テストケースを実行

        Args:
            person: {"name": "...", "age": ..., "category": "..."}

        Returns:
            テスト結果の辞書
        """
        print(f"\n{'='*60}")
        print(f"🧪 Testing: {person['name']} ({person['age']}歳)")
        print(f"{'='*60}")

        result = self.engine.generate_episode(
            person_name=person['name'],
            age=person['age'],
            category=person['category']
        )

        # 結果サマリー
        status = "✅ SUCCESS" if result.success else "❌ FAILED"
        print(f"\n{status}")
        print(f"Iterations: {result.total_iterations}")
        print(f"Time: {result.total_time:.2f}s")
        print(f"Gate Score: {result.final_gate_score:.1f}/10.0")
        if result.final_llm_score is not None:
            print(f"LLM Score: {result.final_llm_score:.1f}/30.0")
            print(f"Total Score: {result.final_total_score:.1f}/40.0")
        print(f"Tokens: {result.total_tokens:,}")

        print(f"\n📝 Final Episode ({len(result.final_episode)} chars):")
        print(result.final_episode)

        return {
            'person_name': person['name'],
            'age': person['age'],
            'category': person['category'],
            'success': result.success,
            'iterations': result.total_iterations,
            'time': result.total_time,
            'gate_score': result.final_gate_score,
            'llm_score': result.final_llm_score,
            'total_score': result.final_total_score,
            'tokens': result.total_tokens,
            'episode': result.final_episode,
            'char_count': len(result.final_episode),
            'failure_reason': result.failure_reason
        }

    def run_batch_test(self, people: List[Dict]) -> Dict:
        """
        バッチテストを実行

        Args:
            people: 人物リスト

        Returns:
            テスト結果サマリー
        """
        print(f"\n{'='*60}")
        print(f"🚀 Phase 3 Integration Test - Batch Mode")
        print(f"{'='*60}")
        print(f"Provider: {self.llm_provider}")
        print(f"Model: {self.model}")
        print(f"Test Cases: {len(people)}")
        print(f"Max Iterations: {self.max_iterations}")
        print(f"Target Score: {self.target_score}")

        results = []

        for i, person in enumerate(people, 1):
            print(f"\n[{i}/{len(people)}] Processing...")
            result = self.run_single_test(person)
            results.append(result)

        # サマリー生成
        summary = self._generate_summary(results)

        # 結果表示
        self._print_summary(summary)

        # JSON保存
        self._save_results(results, summary)

        return summary

    def _generate_summary(self, results: List[Dict]) -> Dict:
        """サマリーを生成"""
        total = len(results)
        success = sum(1 for r in results if r['success'])
        failed = total - success

        avg_iterations = sum(r['iterations'] for r in results) / total
        avg_time = sum(r['time'] for r in results) / total
        avg_gate_score = sum(r['gate_score'] for r in results) / total

        # LLMスコアの平均（Noneを除外）
        llm_scores = [r['llm_score'] for r in results if r['llm_score'] is not None]
        avg_llm_score = sum(llm_scores) / len(llm_scores) if llm_scores else 0.0

        # 総合スコアの平均
        total_scores = [r['total_score'] for r in results if r['total_score'] is not None]
        avg_total_score = sum(total_scores) / len(total_scores) if total_scores else avg_gate_score

        total_tokens = sum(r['tokens'] for r in results)

        # スコア分布
        score_dist = {
            "9.0+": sum(1 for r in results if r['gate_score'] >= 9.0),
            "8.0-8.9": sum(1 for r in results if 8.0 <= r['gate_score'] < 9.0),
            "7.0-7.9": sum(1 for r in results if 7.0 <= r['gate_score'] < 8.0),
            "<7.0": sum(1 for r in results if r['gate_score'] < 7.0),
        }

        # 反復回数分布
        iteration_dist = {
            "1": sum(1 for r in results if r['iterations'] == 1),
            "2": sum(1 for r in results if r['iterations'] == 2),
            "3": sum(1 for r in results if r['iterations'] == 3),
        }

        return {
            'total': total,
            'success': success,
            'failed': failed,
            'success_rate': success / total * 100,
            'avg_iterations': avg_iterations,
            'avg_time': avg_time,
            'avg_gate_score': avg_gate_score,
            'avg_llm_score': avg_llm_score,
            'avg_total_score': avg_total_score,
            'total_tokens': total_tokens,
            'score_distribution': score_dist,
            'iteration_distribution': iteration_dist,
            'timestamp': datetime.now().isoformat()
        }

    def _print_summary(self, summary: Dict) -> None:
        """サマリーを表示"""
        print(f"\n{'='*60}")
        print("📊 Test Summary")
        print(f"{'='*60}")

        print(f"\n🎯 Overall Results:")
        print(f"  Total: {summary['total']}")
        print(f"  Success: {summary['success']} ({summary['success_rate']:.1f}%)")
        print(f"  Failed: {summary['failed']}")

        print(f"\n⚡ Performance:")
        print(f"  Avg Iterations: {summary['avg_iterations']:.2f}")
        print(f"  Avg Time: {summary['avg_time']:.2f}s")
        print(f"  Avg Gate Score: {summary['avg_gate_score']:.2f}/10.0")
        if summary['avg_llm_score'] > 0:
            print(f"  Avg LLM Score: {summary['avg_llm_score']:.2f}/30.0")
            print(f"  Avg Total Score: {summary['avg_total_score']:.2f}/40.0")
        print(f"  Total Tokens: {summary['total_tokens']:,}")

        print(f"\n📈 Score Distribution:")
        for range_name, count in summary['score_distribution'].items():
            percentage = count / summary['total'] * 100
            bar = "█" * int(percentage / 5)
            print(f"  {range_name:8s}: {count:2d} ({percentage:5.1f}%) {bar}")

        print(f"\n🔄 Iteration Distribution:")
        for iter_num, count in summary['iteration_distribution'].items():
            percentage = count / summary['total'] * 100
            bar = "█" * int(percentage / 5)
            print(f"  {iter_num} iter: {count:2d} ({percentage:5.1f}%) {bar}")

    def _save_results(self, results: List[Dict], summary: Dict) -> None:
        """結果をJSONで保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"phase3_test_results_{timestamp}.json"

        output = {
            'test_config': {
                'provider': self.llm_provider,
                'model': self.model,
                'max_iterations': self.max_iterations,
                'target_score': self.target_score
            },
            'summary': summary,
            'results': results
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Results saved to: {filename}")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Phase 3 Integration Test")
    parser.add_argument(
        '--provider',
        choices=['openai', 'anthropic'],
        default='openai',
        help='LLM provider (default: openai)'
    )
    parser.add_argument(
        '--model',
        help='Model name (default: gpt-4o for OpenAI, claude-3-5-sonnet for Anthropic)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=3,
        help='Number of test cases (default: 3, max: 10)'
    )
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=3,
        help='Max iterations (default: 3)'
    )
    parser.add_argument(
        '--target-score',
        type=float,
        default=8.0,
        help='Target gate score (default: 8.0)'
    )

    args = parser.parse_args()

    # テストケース数を制限
    test_count = min(args.count, len(TEST_PEOPLE))
    test_people = TEST_PEOPLE[:test_count]

    try:
        # テスト実行
        tester = Phase3IntegrationTest(
            llm_provider=args.provider,
            model=args.model,
            max_iterations=args.max_iterations,
            target_score=args.target_score
        )

        summary = tester.run_batch_test(test_people)

        # 終了ステータス
        if summary['success_rate'] >= 80:
            print(f"\n✅ Test PASSED ({summary['success_rate']:.1f}% success rate)")
            return 0
        else:
            print(f"\n❌ Test FAILED ({summary['success_rate']:.1f}% success rate)")
            return 1

    except Exception as e:
        print(f"\n❌ Test Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
