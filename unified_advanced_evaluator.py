#!/usr/bin/env python3
"""
統合次世代評価システム

機能:
1. キーワード評価（高速・無料）
2. Chain-of-Thought LLM評価（20-29点のボーダーラインのみ）
3. 自動改善提案
4. バッチ処理対応
"""

import csv
import os
import time
from typing import List, Dict, Optional
from dataclasses import dataclass

from impact_evaluator import ImpactEvaluator
from advanced_llm_evaluator import AdvancedLLMEvaluator
from episode_improvement_engine import EpisodeImprovementEngine


@dataclass
class UnifiedEvaluationResult:
    """統合評価結果"""
    episode_id: str
    person_name: str
    age: int
    episode_text: str

    # Phase 1: キーワード評価
    keyword_score: int
    keyword_passed: bool

    # Phase 2: LLM評価（ボーダーラインのみ）
    llm_used: bool
    llm_score: Optional[int]
    llm_grade: Optional[str]
    llm_passed: Optional[bool]

    # Phase 3: 改善提案
    has_improvements: bool
    improvement_count: int

    # 最終判定
    final_score: int
    final_passed: bool
    cost_saved: bool


class UnifiedAdvancedEvaluator:
    """統合次世代評価システム"""

    def __init__(
        self,
        provider: str = "openai",
        borderline_min: int = 20,
        borderline_max: int = 59,
        enable_llm: bool = True
    ):
        """
        Args:
            provider: LLMプロバイダー
            borderline_min: LLM評価を実施する最小スコア
            borderline_max: LLM評価を実施する最大スコア
            enable_llm: LLM評価の有効化
        """
        self.keyword_evaluator = ImpactEvaluator()
        self.llm_evaluator = AdvancedLLMEvaluator(provider=provider) if enable_llm else None
        self.improvement_engine = EpisodeImprovementEngine(provider=provider) if enable_llm else None

        self.borderline_min = borderline_min
        self.borderline_max = borderline_max
        self.enable_llm = enable_llm

        # 統計情報
        self.stats = {
            'total': 0,
            'keyword_pass': 0,
            'keyword_fail': 0,
            'borderline': 0,
            'llm_calls': 0,
            'cost_saved': 0
        }

    def evaluate(
        self,
        episode_text: str,
        person_name: str,
        age: int,
        episode_id: str = "Unknown"
    ) -> UnifiedEvaluationResult:
        """
        統合評価を実施

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名
            age: 年齢
            episode_id: エピソードID

        Returns:
            UnifiedEvaluationResult: 統合評価結果
        """
        self.stats['total'] += 1

        # Step 1: キーワード評価（必須）
        keyword_result = self.keyword_evaluator.evaluate(episode_text, person_name, age)
        keyword_score = keyword_result.total

        # コスト最適化判定
        if keyword_score >= self.borderline_max + 1:
            # 高スコア → LLM不要
            self.stats['keyword_pass'] += 1
            self.stats['cost_saved'] += 1
            return UnifiedEvaluationResult(
                episode_id=episode_id,
                person_name=person_name,
                age=age,
                episode_text=episode_text,
                keyword_score=keyword_score,
                keyword_passed=True,
                llm_used=False,
                llm_score=None,
                llm_grade=None,
                llm_passed=None,
                has_improvements=False,
                improvement_count=0,
                final_score=keyword_score,
                final_passed=True,
                cost_saved=True
            )

        elif keyword_score < self.borderline_min:
            # 低スコア → LLM不要（不合格）
            self.stats['keyword_fail'] += 1
            self.stats['cost_saved'] += 1
            return UnifiedEvaluationResult(
                episode_id=episode_id,
                person_name=person_name,
                age=age,
                episode_text=episode_text,
                keyword_score=keyword_score,
                keyword_passed=False,
                llm_used=False,
                llm_score=None,
                llm_grade=None,
                llm_passed=None,
                has_improvements=False,
                improvement_count=0,
                final_score=keyword_score,
                final_passed=False,
                cost_saved=True
            )

        # Step 2: ボーダーライン → LLM評価
        if not self.enable_llm or not self.llm_evaluator:
            # LLM無効時はキーワードスコアのみ
            return UnifiedEvaluationResult(
                episode_id=episode_id,
                person_name=person_name,
                age=age,
                episode_text=episode_text,
                keyword_score=keyword_score,
                keyword_passed=keyword_score >= 30,
                llm_used=False,
                llm_score=None,
                llm_grade=None,
                llm_passed=None,
                has_improvements=False,
                improvement_count=0,
                final_score=keyword_score,
                final_passed=keyword_score >= 30,
                cost_saved=True
            )

        self.stats['borderline'] += 1
        self.stats['llm_calls'] += 1

        # LLM評価実施
        llm_result = self.llm_evaluator.evaluate(episode_text, person_name, age)

        # Step 3: 改善提案（不合格の場合のみ）
        has_improvements = False
        improvement_count = 0

        if llm_result.total_score < 60 and self.improvement_engine:
            improvement_plan = self.improvement_engine.generate_improvement_plan(
                llm_result, episode_id
            )
            has_improvements = True
            improvement_count = len(improvement_plan.improvements)

        return UnifiedEvaluationResult(
            episode_id=episode_id,
            person_name=person_name,
            age=age,
            episode_text=episode_text,
            keyword_score=keyword_score,
            keyword_passed=keyword_score >= 30,
            llm_used=True,
            llm_score=llm_result.total_score,
            llm_grade=llm_result.grade,
            llm_passed=llm_result.passed,
            has_improvements=has_improvements,
            improvement_count=improvement_count,
            final_score=llm_result.total_score,
            final_passed=llm_result.passed,
            cost_saved=False
        )

    def evaluate_batch(
        self,
        episodes: List[Dict],
        output_csv: str = "unified_advanced_evaluation.csv",
        verbose: bool = True
    ):
        """
        バッチ評価を実施

        Args:
            episodes: エピソードリスト
            output_csv: 出力CSVファイル
            verbose: 進捗表示
        """
        results = []
        start_time = time.time()

        for i, episode in enumerate(episodes, 1):
            if verbose:
                print(f"\r評価中: {i}/{len(episodes)} ({i/len(episodes)*100:.1f}%)", end="")

            result = self.evaluate(
                episode['episode_text'],
                episode['person_name'],
                int(episode['episode_age']),
                episode['episode_id']
            )
            results.append(result)

            # レート制限対策
            if result.llm_used:
                time.sleep(1)

        elapsed_time = time.time() - start_time

        if verbose:
            print(f"\n\n完了: {len(episodes)}件を{elapsed_time:.2f}秒で評価")
            self.print_statistics()

        # CSV出力
        self._export_to_csv(results, output_csv)

        return results

    def print_statistics(self):
        """統計情報を表示"""
        total = self.stats['total']
        if total == 0:
            return

        print(f"""
{'='*80}
統計情報
{'='*80}
総評価数: {total}件

【コスト最適化】
- 高スコア（即合格）: {self.stats['keyword_pass']}件 ({self.stats['keyword_pass']/total*100:.1f}%)
- 低スコア（即不合格）: {self.stats['keyword_fail']}件 ({self.stats['keyword_fail']/total*100:.1f}%)
- ボーダーライン（LLM評価）: {self.stats['borderline']}件 ({self.stats['borderline']/total*100:.1f}%)

【LLM使用状況】
- LLM呼び出し数: {self.stats['llm_calls']}回
- コスト削減数: {self.stats['cost_saved']}回 ({self.stats['cost_saved']/total*100:.1f}%)
- コスト削減率: {self.stats['cost_saved']/total*100:.1f}%

【推定コスト】
- OpenAI GPT-4o-mini: 約${self.stats['llm_calls'] * 0.001:.3f}
- Anthropic Claude-3.5-sonnet: 約${self.stats['llm_calls'] * 0.015:.3f}
""")

    def _export_to_csv(self, results: List[UnifiedEvaluationResult], filepath: str):
        """結果をCSVファイルにエクスポート"""
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # ヘッダー
            writer.writerow([
                'episode_id',
                'person_name',
                'episode_age',
                'keyword_score',
                'llm_used',
                'llm_score',
                'llm_grade',
                'final_score',
                'final_passed',
                'cost_saved',
                'has_improvements',
                'improvement_count'
            ])

            # データ
            for result in results:
                writer.writerow([
                    result.episode_id,
                    result.person_name,
                    result.age,
                    result.keyword_score,
                    result.llm_used,
                    result.llm_score or '',
                    result.llm_grade or '',
                    result.final_score,
                    result.final_passed,
                    result.cost_saved,
                    result.has_improvements,
                    result.improvement_count
                ])


def test_unified_evaluator():
    """統合評価システムのテスト"""

    print("="*80)
    print("統合次世代評価システム - テスト")
    print("="*80)

    evaluator = UnifiedAdvancedEvaluator(
        provider="openai",
        borderline_min=0,   # すべてのケースでLLM評価を試す（テスト用）
        borderline_max=100,
        enable_llm=True
    )

    # テストケース1: 高スコア（LLM不要）
    print("\nテストケース1: Ado（高スコア期待）")
    ado_episode = """あなたと同じ21歳のとき、Adoはロサンゼルス公演で3000人の会場を完売させ、海外進出に成功した。「うっせぇわ」で顔を公開せずに紅白歌合戦出場とBillboardJapan年間1位を獲得し、匿名アーティストという新しい成功モデルを確立した。YouTubeでの楽曲は若者を中心に広範な支持を集め、新時代の音楽シーンを象徴する存在となった。"""

    result1 = evaluator.evaluate(ado_episode, "Ado", 21, "EP001")
    print(f"キーワード: {result1.keyword_score}点")
    print(f"LLM使用: {result1.llm_used}")
    print(f"最終スコア: {result1.final_score}点")
    print(f"判定: {'✅ 合格' if result1.final_passed else '❌ 不合格'}")
    print(f"コスト削減: {'✅' if result1.cost_saved else '❌'}")

    # テストケース2: ボーダーライン（LLM必要）
    print("\n" + "="*80)
    print("テストケース2: 新垣結衣（ボーダーライン期待）")
    aragaki_episode = """あなたと同じ18歳のとき、新垣結衣は江崎グリコのポッキーCM「ポッキーダンス」に出演し、芸能界でのブレイクを果たした。沖縄から上京してわずか3年、無名の新人モデルだった彼女は「本当にこの子で大丈夫？」という制作側の不安の中、笑顔とダンスで日本中を魅了した。CM放送後、ネット上で「ガッキー」の愛称が広まり、検索数が急上昇。この年7回のCM出演契約が決定し、翌年には映画『恋空』で興行収入39億円を記録する大女優への階段を駆け上がった。"""

    result2 = evaluator.evaluate(aragaki_episode, "新垣結衣", 18, "EP052")
    print(f"キーワード: {result2.keyword_score}点")
    print(f"LLM使用: {result2.llm_used}")
    if result2.llm_used:
        print(f"LLMスコア: {result2.llm_score}点（グレード: {result2.llm_grade}）")
    print(f"最終スコア: {result2.final_score}点")
    print(f"判定: {'✅ 合格' if result2.final_passed else '❌ 不合格'}")
    print(f"コスト削減: {'✅' if result2.cost_saved else '❌'}")
    if result2.has_improvements:
        print(f"改善提案: {result2.improvement_count}件")

    # テストケース3: 低スコア（LLM不要）
    print("\n" + "="*80)
    print("テストケース3: 川端康成（低スコア期待）")
    kawabata_episode = """あなたと同じ27歳のとき、川端康成は『伊豆の踊子』発表、青春文学の金字塔この作品は時代を超えて読み継がれ、多くの読者の心に深い感動を与え続けている。"""

    result3 = evaluator.evaluate(kawabata_episode, "川端康成", 27, "EP003")
    print(f"キーワード: {result3.keyword_score}点")
    print(f"LLM使用: {result3.llm_used}")
    print(f"最終スコア: {result3.final_score}点")
    print(f"判定: {'✅ 合格' if result3.final_passed else '❌ 不合格'}")
    print(f"コスト削減: {'✅' if result3.cost_saved else '❌'}")

    # 統計表示
    evaluator.print_statistics()


if __name__ == '__main__':
    test_unified_evaluator()
