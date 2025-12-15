#!/usr/bin/env python3
"""
統合エピソード評価器（Integrated Episode Evaluator）
配分チェック + 感情的インパクト評価 + ルール準拠 + 定番度判定を統合

評価フロー:
1. Phase 1: ルール準拠チェック（CONTENT_005, FORMAT_CHECK）
2. Phase 2: 配分チェック（年齢時点70%以上）
3. Phase 3: 感情的インパクト評価（40点以上）
4. Phase 4: 定番度判定（60点以上）
"""

import csv
import sys
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from content_distribution_checker import ContentDistributionChecker, DistributionAnalysis
from hybrid_impact_evaluator import HybridImpactEvaluator, HybridImpactScore
from episode_guardian import create_episode_guardian, ValidationResult
from episode_relevance_checker import EpisodeRelevanceChecker, RelevanceScore


@dataclass
class IntegratedEvaluationResult:
    """統合評価結果"""
    episode_id: str
    person_name: str
    episode_age: int
    episode_text: str

    # Phase 1: ルール準拠
    compliance_passed: bool
    compliance_message: str

    # Phase 2: 配分チェック
    distribution_passed: bool
    age_specific_percentage: float
    subsequent_percentage: float

    # Phase 3: 感情的インパクト（ハイブリッド）
    impact_passed: bool
    impact_score: int
    impact_details: Dict[str, int]
    impact_keyword_score: int
    impact_llm_score: Optional[int]
    impact_llm_used: bool
    impact_evaluation_method: str

    # Phase 4: 定番度判定
    relevance_passed: bool
    relevance_score: float
    is_iconic: bool
    top_rank: int

    # 総合判定
    overall_passed: bool
    recommendation: str


class IntegratedEpisodeEvaluator:
    """感情的インパクト + 配分チェック + ルール準拠 + 定番度判定の統合評価システム"""

    def __init__(self, mcp_search_function: Optional[Callable] = None):
        """
        Args:
            mcp_search_function: Brave Search MCP関数（オプション）
                                指定しない場合はPhase 4をスキップ
        """
        self.guardian = create_episode_guardian()
        self.distribution_checker = ContentDistributionChecker()
        self.impact_evaluator = HybridImpactEvaluator(llm_provider="openai")
        self.relevance_checker = EpisodeRelevanceChecker()
        self.mcp_search_function = mcp_search_function

    def evaluate(self, episode: Dict) -> IntegratedEvaluationResult:
        """
        完全評価

        Args:
            episode: エピソードデータ

        Returns:
            IntegratedEvaluationResult: 統合評価結果
        """
        episode_id = episode['episode_id']
        person_name = episode['person_name']
        episode_age = int(episode['episode_age'])
        episode_text = episode['episode_text']

        # Phase 1: ルール準拠チェック（必須）
        compliance_result = self.guardian.validate_episode(episode)
        compliance_passed = compliance_result.is_valid
        compliance_message = compliance_result.message if not compliance_passed else "合格"

        if not compliance_passed:
            return IntegratedEvaluationResult(
                episode_id=episode_id,
                person_name=person_name,
                episode_age=episode_age,
                episode_text=episode_text,
                compliance_passed=False,
                compliance_message=compliance_message,
                distribution_passed=False,
                age_specific_percentage=0.0,
                subsequent_percentage=0.0,
                impact_passed=False,
                impact_score=0,
                impact_details={},
                impact_keyword_score=0,
                impact_llm_score=None,
                impact_llm_used=False,
                impact_evaluation_method="",
                relevance_passed=False,
                relevance_score=0.0,
                is_iconic=False,
                top_rank=100,
                overall_passed=False,
                recommendation="Phase 1: ルール準拠違反 - 修正が必要"
            )

        # Phase 2: 配分チェック（必須）
        distribution = self.distribution_checker.analyze_distribution(episode_text, episode_age)
        distribution_passed = distribution.compliant

        if not distribution_passed:
            return IntegratedEvaluationResult(
                episode_id=episode_id,
                person_name=person_name,
                episode_age=episode_age,
                episode_text=episode_text,
                compliance_passed=True,
                compliance_message="合格",
                distribution_passed=False,
                age_specific_percentage=distribution.age_specific_percentage,
                subsequent_percentage=distribution.subsequent_percentage,
                impact_passed=False,
                impact_score=0,
                impact_details={},
                impact_keyword_score=0,
                impact_llm_score=None,
                impact_llm_used=False,
                impact_evaluation_method="",
                relevance_passed=False,
                relevance_score=0.0,
                is_iconic=False,
                top_rank=100,
                overall_passed=False,
                recommendation=f"Phase 2: 配分違反 - 年齢時点{distribution.age_specific_percentage:.1f}%（70%以上必要）"
            )

        # Phase 3: 感情的インパクト評価（ハイブリッド）
        impact = self.impact_evaluator.evaluate(episode_text, person_name, episode_age)
        impact_passed = impact.passed
        impact_keyword_score = impact.keyword_score
        impact_llm_score = impact.llm_score
        impact_llm_used = impact.llm_used
        impact_evaluation_method = impact.evaluation_method

        # Phase 4: 定番度判定（オプション - MCP関数が提供されている場合のみ）
        relevance_passed = True  # デフォルトでは合格扱い
        relevance_score = 100.0
        is_iconic = True
        top_rank = 1

        if self.mcp_search_function:
            # エピソードからキーワードを抽出
            keywords = self.relevance_checker.extract_keywords_from_episode(episode_text)
            if keywords:
                relevance = self.relevance_checker.check_relevance(
                    person_name, keywords, self.mcp_search_function
                )
                relevance_passed = relevance.is_iconic
                relevance_score = relevance.relevance_score
                is_iconic = relevance.is_iconic
                top_rank = relevance.top_rank

        # 推奨事項の決定
        if compliance_passed and distribution_passed and impact_passed and relevance_passed:
            recommendation = "✅ すべての基準を満たしています"
        elif not relevance_passed:
            recommendation = f"Phase 4: 定番度不足 - {relevance_score:.1f}/100点（60点以上必要）、より定番のエピソードへの変更を検討"
        elif not impact_passed:
            percentage = (impact.total_score / 50) * 100
            recommendation = f"Phase 3: インパクト不足 - {impact.total_score}/50点（{percentage:.0f}%）、30点以上（60%）必要"
        else:
            recommendation = "✅ すべての基準を満たしています"

        return IntegratedEvaluationResult(
            episode_id=episode_id,
            person_name=person_name,
            episode_age=episode_age,
            episode_text=episode_text,
            compliance_passed=True,
            compliance_message="合格",
            distribution_passed=True,
            age_specific_percentage=distribution.age_specific_percentage,
            subsequent_percentage=distribution.subsequent_percentage,
            impact_passed=impact_passed,
            impact_score=impact.total_score,
            impact_details={
                'turning_point': impact.keyword_details['turning_point'],
                'surprise': impact.keyword_details['surprise'],
                'risk_taking': impact.keyword_details['risk_taking'],
                'relatability': impact.keyword_details['relatability'],
                'sensational': impact.keyword_details['sensational']
            },
            impact_keyword_score=impact_keyword_score,
            impact_llm_score=impact_llm_score,
            impact_llm_used=impact_llm_used,
            impact_evaluation_method=impact_evaluation_method,
            relevance_passed=relevance_passed,
            relevance_score=relevance_score,
            is_iconic=is_iconic,
            top_rank=top_rank,
            overall_passed=compliance_passed and distribution_passed and impact_passed and relevance_passed,
            recommendation=recommendation
        )

    def evaluate_all(self, csv_path: str) -> List[IntegratedEvaluationResult]:
        """
        CSVファイルから全エピソードを読み込んで評価

        Args:
            csv_path: CSVファイルパス

        Returns:
            List[IntegratedEvaluationResult]: 評価結果リスト
        """
        episodes = self._load_episodes(csv_path)
        results = []

        for episode in episodes:
            result = self.evaluate(episode)
            results.append(result)

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

    def get_summary_report(self, results: List[IntegratedEvaluationResult]) -> str:
        """
        評価結果のサマリーレポートを生成

        Args:
            results: 評価結果リスト

        Returns:
            str: サマリーレポート
        """
        total = len(results)
        overall_passed = sum(1 for r in results if r.overall_passed)
        compliance_failed = sum(1 for r in results if not r.compliance_passed)
        distribution_failed = sum(1 for r in results if r.compliance_passed and not r.distribution_passed)
        impact_failed = sum(1 for r in results if r.compliance_passed and r.distribution_passed and not r.impact_passed)
        relevance_failed = sum(1 for r in results if r.compliance_passed and r.distribution_passed and
                              r.impact_passed and not r.relevance_passed)

        report = f"""
{'='*80}
統合評価サマリー（Phase 1-4）
{'='*80}

総エピソード数: {total}
全基準合格: {overall_passed} ({overall_passed/total*100:.1f}%)

Phase別の問題:
  Phase 1 - ルール準拠違反: {compliance_failed}件
  Phase 2 - 配分違反: {distribution_failed}件
  Phase 3 - インパクト不足: {impact_failed}件
  Phase 4 - 定番度不足: {relevance_failed}件

{'='*80}
"""

        # Phase 3のインパクト不足を詳細表示
        if impact_failed > 0:
            report += f"\nインパクト不足エピソード（{impact_failed}件）:\n\n"
            impact_issues = [r for r in results if r.compliance_passed and
                           r.distribution_passed and not r.impact_passed]

            for r in sorted(impact_issues, key=lambda x: x.impact_score):
                report += f"  {r.episode_id} {r.person_name}（{r.episode_age}歳）: {r.impact_score}/50点\n"
                report += f"    - 人生の転換点: {r.impact_details['turning_point']}/10\n"
                report += f"    - 意外性: {r.impact_details['surprise']}/10\n"
                report += f"    - リスクテイキング: {r.impact_details['risk_taking']}/10\n"
                report += f"    - 共感性: {r.impact_details['relatability']}/10\n"
                report += f"    - センセーショナル度: {r.impact_details['sensational']}/10\n"
                report += f"    推奨: エピソードを「原点」に変更\n\n"

        # Phase 4の定番度不足を詳細表示
        if relevance_failed > 0:
            report += f"\n定番度不足エピソード（{relevance_failed}件）:\n\n"
            relevance_issues = [r for r in results if r.compliance_passed and
                              r.distribution_passed and r.impact_passed and not r.relevance_passed]

            for r in sorted(relevance_issues, key=lambda x: x.relevance_score):
                report += f"  {r.episode_id} {r.person_name}（{r.episode_age}歳）: {r.relevance_score:.1f}/100点\n"
                report += f"    - トップ順位: {r.top_rank}位\n"
                report += f"    - 定番判定: {'✅ 定番' if r.is_iconic else '❌ マイナー'}\n"
                report += f"    推奨: より定番のエピソードへの変更を検討\n\n"

        return report

    def save_results(self, results: List[IntegratedEvaluationResult], output_path: str):
        """
        評価結果をCSVに保存

        Args:
            results: 評価結果リスト
            output_path: 出力CSVパス
        """
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = [
                'episode_id', 'person_name', 'episode_age',
                'overall_passed', 'compliance_passed', 'distribution_passed', 'impact_passed', 'relevance_passed',
                'age_specific_pct', 'subsequent_pct', 'impact_score',
                'impact_keyword_score', 'impact_llm_score', 'impact_llm_used', 'impact_evaluation_method',
                'turning_point', 'surprise', 'risk_taking', 'relatability', 'sensational',
                'relevance_score', 'is_iconic', 'top_rank',
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
                    'relevance_passed': r.relevance_passed,
                    'age_specific_pct': f"{r.age_specific_percentage:.1f}",
                    'subsequent_pct': f"{r.subsequent_percentage:.1f}",
                    'impact_score': r.impact_score,
                    'impact_keyword_score': r.impact_keyword_score,
                    'impact_llm_score': r.impact_llm_score if r.impact_llm_score is not None else "",
                    'impact_llm_used': r.impact_llm_used,
                    'impact_evaluation_method': r.impact_evaluation_method,
                    'turning_point': r.impact_details.get('turning_point', 0),
                    'surprise': r.impact_details.get('surprise', 0),
                    'risk_taking': r.impact_details.get('risk_taking', 0),
                    'relatability': r.impact_details.get('relatability', 0),
                    'sensational': r.impact_details.get('sensational', 0),
                    'relevance_score': f"{r.relevance_score:.1f}",
                    'is_iconic': r.is_iconic,
                    'top_rank': r.top_rank,
                    'recommendation': r.recommendation
                })


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法: python3 integrated_episode_evaluator.py <episodes.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_path = csv_path.replace('.csv', '_integrated_evaluation.csv')

    print(f"{'='*80}")
    print(f"統合エピソード評価システム")
    print(f"{'='*80}")
    print(f"入力: {csv_path}")
    print(f"出力: {output_path}")
    print(f"{'='*80}\n")

    evaluator = IntegratedEpisodeEvaluator()

    # 全エピソード評価
    print("評価中...")
    results = evaluator.evaluate_all(csv_path)

    # サマリー表示
    print(evaluator.get_summary_report(results))

    # 結果を保存
    evaluator.save_results(results, output_path)
    print(f"✅ 評価結果を保存: {output_path}")


if __name__ == '__main__':
    main()
