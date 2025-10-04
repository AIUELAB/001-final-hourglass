#!/usr/bin/env python3
"""
Quality Gate Orchestrator - SubAgent統括システム

複数の専門SubAgentを統括し、並列処理で効率的に品質検証を行います。
各Agentは特定の品質側面に特化し、独立して動作可能です。
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from datetime import datetime

# 既存モジュールのインポート
from pdca_guardian import PDCAGuardian
from quality_gate_api import QualityGateAPI


class AgentStatus(Enum):
    """エージェントステータス"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentResult:
    """エージェント実行結果"""
    agent_name: str
    status: AgentStatus
    score: float
    passed: bool
    violations: List[str]
    suggestions: List[str]
    execution_time: float
    details: Dict[str, Any]


class BaseAgent(ABC):
    """基底エージェントクラス"""

    def __init__(self, name: str):
        self.name = name
        self.status = AgentStatus.IDLE

    @abstractmethod
    async def execute(self, episode_data: Dict) -> AgentResult:
        """エージェント実行（サブクラスで実装）"""
        pass

    async def run(self, episode_data: Dict) -> AgentResult:
        """エージェント実行のラッパー"""
        self.status = AgentStatus.RUNNING
        start_time = datetime.now()

        try:
            result = await self.execute(episode_data)
            self.status = AgentStatus.COMPLETED
            result.execution_time = (datetime.now() - start_time).total_seconds()
            return result

        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                score=0.0,
                passed=False,
                violations=[f"エラー: {str(e)}"],
                suggestions=["エラーを解決してください"],
                execution_time=(datetime.now() - start_time).total_seconds(),
                details={"error": str(e)}
            )


class ValidationAgent(BaseAgent):
    """PDCA ルール検証エージェント"""

    def __init__(self):
        super().__init__("ValidationAgent")
        self.pdca_guardian = PDCAGuardian()

    async def execute(self, episode_data: Dict) -> AgentResult:
        """PDCAルール156項目を検証"""
        violations = []
        suggestions = []

        episode_text = episode_data.get('episode_content', '')
        age = episode_data.get('episode_age', 0)
        person_name_display = episode_data.get('person_name_display', episode_data.get('person_name', ''))

        # PDCAガーディアンによる検証 - エピソード品質
        quality_results = self.pdca_guardian.check_episode_quality(episode_text, age, person_name_display)
        for violation in quality_results:
            violations.append(f"RULE_{violation.get('rule_number', '000')}: {violation.get('message', '')}")
            suggestions.append(violation.get('suggestion', '改善してください'))

        # 感情的価値チェック
        emotional_results = self.pdca_guardian.check_emotional_value(episode_data)
        for violation in emotional_results:
            violations.append(f"感情価値: {violation.get('message', '')}")
            suggestions.append(violation.get('suggestion', ''))

        # センセーショナル価値チェック
        sensational_results = self.pdca_guardian.check_sensational_value(episode_data)
        for violation in sensational_results:
            violations.append(f"センセーショナル: {violation.get('message', '')}")
            suggestions.append(violation.get('suggestion', ''))

        # スコア計算（違反数に基づく）
        score = max(0, 10.0 - len(violations) * 0.5)
        passed = len(violations) == 0

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            score=score,
            passed=passed,
            violations=violations,
            suggestions=suggestions,
            execution_time=0,
            details={
                'total_rules': 156,
                'violations_count': len(violations),
                'compliance_rate': (156 - len(violations)) / 156 * 100
            }
        )


class FactCheckAgent(BaseAgent):
    """事実確認エージェント"""

    def __init__(self):
        super().__init__("FactCheckAgent")
        self.api = QualityGateAPI()

    async def execute(self, episode_data: Dict) -> AgentResult:
        """事実の正確性を検証"""
        violations = []
        suggestions = []

        # 人物の実在性確認
        person_name = episode_data.get('person_name', '')
        validation_result = await self.api.validate_person(person_name)

        if not validation_result['exists']:
            violations.append(f"人物 '{person_name}' の実在性が確認できません")
            suggestions.append("実在の人物名を使用してください")

        # 節目の妥当性確認
        milestone_result = await self.api.validate_milestone(
            person_name,
            episode_data.get('episode_age', 0),
            episode_data.get('episode_content', '')
        )

        if not milestone_result['valid']:
            violations.append("節目情報が不正確です")
            if milestone_result.get('suggestion'):
                suggestions.append(milestone_result['suggestion'])

        # スコア計算
        confidence = validation_result.get('confidence_score', 0)
        milestone_score = milestone_result.get('score', 0)
        score = (confidence + milestone_score) / 2
        passed = len(violations) == 0

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            score=score,
            passed=passed,
            violations=violations,
            suggestions=suggestions,
            execution_time=0,
            details={
                'person_exists': validation_result['exists'],
                'confidence': confidence,
                'milestone_valid': milestone_result['valid'],
                'milestone_score': milestone_score
            }
        )


class MilestoneAgent(BaseAgent):
    """節目重要度評価エージェント"""

    def __init__(self):
        super().__init__("MilestoneAgent")

    async def execute(self, episode_data: Dict) -> AgentResult:
        """節目の重要度を評価"""
        violations = []
        suggestions = []

        content = episode_data.get('episode_content', '')
        episode_type = episode_data.get('episode_type', '')
        age = episode_data.get('episode_age', 0)

        # 重要度評価
        importance_score = self._evaluate_importance(content, episode_type)

        # デビュー・開始の優先度チェック
        is_debut = any(keyword in content for keyword in ['デビュー', '開始', '初', '誕生'])
        is_continuation = any(keyword in content for keyword in ['周年', '継続', '記念'])

        if is_continuation and not is_debut:
            if importance_score < 7.0:
                violations.append("RULE_153: 継続的な節目より開始・デビューを優先すべきです")
                suggestions.append("デビューや開始時点のエピソードを選択してください")

        # 年齢の適切性チェック
        if age < 0 or age > 100:
            violations.append(f"年齢が不適切: {age}歳")
            suggestions.append("適切な年齢を設定してください")

        score = importance_score
        passed = len(violations) == 0 and score >= 7.0

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            score=score,
            passed=passed,
            violations=violations,
            suggestions=suggestions,
            execution_time=0,
            details={
                'is_debut': is_debut,
                'is_continuation': is_continuation,
                'importance_score': importance_score,
                'age': age
            }
        )

    def _evaluate_importance(self, content: str, episode_type: str) -> float:
        """重要度スコアを計算"""
        score = 5.0

        # 高重要度キーワード
        high_importance = ['開始', 'デビュー', '誕生', '初', '創業', '結成', '最年少', '最年長']
        medium_importance = ['達成', '受賞', '優勝', '完成', '発表', '記録']
        low_importance = ['周年', '継続', '記念', '現在', 'その後']

        for keyword in high_importance:
            if keyword in content or keyword in episode_type:
                score += 2.0

        for keyword in medium_importance:
            if keyword in content or keyword in episode_type:
                score += 1.0

        for keyword in low_importance:
            if keyword in content or keyword in episode_type:
                score -= 1.0

        return min(10.0, max(0.0, score))


class EmpathyAgent(BaseAgent):
    """共感度評価エージェント"""

    def __init__(self):
        super().__init__("EmpathyAgent")

    async def execute(self, episode_data: Dict) -> AgentResult:
        """共感度を評価"""
        violations = []
        suggestions = []

        content = episode_data.get('episode_content', '')
        user_age = episode_data.get('user_age', 0)
        episode_age = episode_data.get('episode_age', 0)
        empathy_score = episode_data.get('empathy_score', 0)

        # 年齢差による共感度チェック
        age_diff = abs(user_age - episode_age)
        age_penalty = min(age_diff * 0.1, 3.0)

        # 感情的要素の分析
        emotional_keywords = [
            '感動', '挑戦', '努力', '成功', '失敗', '克服',
            '夢', '希望', '勇気', '友情', '愛', '家族'
        ]
        emotional_count = sum(1 for keyword in emotional_keywords if keyword in content)
        emotional_bonus = min(emotional_count * 0.5, 2.0)

        # 最終スコア計算
        calculated_score = 5.0 - age_penalty + emotional_bonus
        final_score = (calculated_score + empathy_score) / 2

        if final_score < 6.0:
            violations.append("共感度が低すぎます")
            suggestions.append("より感情的な要素や普遍的なテーマを含めてください")

        passed = len(violations) == 0 and final_score >= 6.0

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            score=final_score,
            passed=passed,
            violations=violations,
            suggestions=suggestions,
            execution_time=0,
            details={
                'age_difference': age_diff,
                'emotional_elements': emotional_count,
                'calculated_score': calculated_score,
                'provided_score': empathy_score
            }
        )


class UniquenessAgent(BaseAgent):
    """独自性評価エージェント"""

    def __init__(self):
        super().__init__("UniquenessAgent")
        self.known_episodes = set()  # 既知のエピソードを記録

    async def execute(self, episode_data: Dict) -> AgentResult:
        """独自性と新規性を評価"""
        violations = []
        suggestions = []

        person_name = episode_data.get('person_name', '')
        content = episode_data.get('episode_content', '')

        # エピソードのハッシュを作成
        episode_hash = f"{person_name}:{content[:50]}"

        # 重複チェック
        if episode_hash in self.known_episodes:
            violations.append("類似のエピソードが既に存在します")
            suggestions.append("異なる視点や年齢のエピソードを選択してください")
            score = 3.0
        else:
            self.known_episodes.add(episode_hash)
            score = 8.0

        # 一般的すぎるエピソードのチェック
        generic_phrases = [
            'として知られる', '有名な', '活躍した', '人気の',
            'として活動', '現在も'
        ]
        generic_count = sum(1 for phrase in generic_phrases if phrase in content)

        if generic_count >= 2:
            score -= 2.0
            violations.append("エピソードが一般的すぎます")
            suggestions.append("より具体的で特徴的なエピソードを使用してください")

        # 具体的な数字や固有名詞のチェック
        import re
        numbers = re.findall(r'\d+', content)
        if len(numbers) > 0:
            score += 1.0  # 具体的な数字があれば加点

        passed = len(violations) == 0 and score >= 6.0

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            score=score,
            passed=passed,
            violations=violations,
            suggestions=suggestions,
            execution_time=0,
            details={
                'is_duplicate': episode_hash in self.known_episodes,
                'generic_level': generic_count,
                'specificity': len(numbers),
                'total_known_episodes': len(self.known_episodes)
            }
        )


class QualityGateOrchestrator:
    """SubAgent統括システム"""

    def __init__(self, parallel_execution: bool = True):
        """
        初期化

        Args:
            parallel_execution: 並列実行を有効にするか
        """
        self.parallel_execution = parallel_execution
        self.agents = {
            'validation': ValidationAgent(),
            'fact_check': FactCheckAgent(),
            'milestone': MilestoneAgent(),
            'empathy': EmpathyAgent(),
            'uniqueness': UniquenessAgent()
        }
        self.execution_history = []

    async def process_episode(self, episode_data: Dict) -> Dict[str, Any]:
        """
        エピソードを全エージェントで処理

        Args:
            episode_data: エピソードデータ

        Returns:
            処理結果
        """
        start_time = datetime.now()

        if self.parallel_execution:
            # 並列実行
            results = await self._process_parallel(episode_data)
        else:
            # 順次実行
            results = await self._process_sequential(episode_data)

        # 結果を集約
        aggregated = self._aggregate_results(results)
        aggregated['total_execution_time'] = (datetime.now() - start_time).total_seconds()

        # 履歴に記録
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'episode': episode_data.get('person_name', 'unknown'),
            'result': aggregated['final_status'],
            'score': aggregated['final_score']
        })

        return aggregated

    async def _process_parallel(self, episode_data: Dict) -> List[AgentResult]:
        """並列処理"""
        tasks = []
        for agent in self.agents.values():
            tasks.append(agent.run(episode_data))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # エラーをAgentResultに変換
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                agent_name = list(self.agents.keys())[i]
                processed_results.append(AgentResult(
                    agent_name=agent_name,
                    status=AgentStatus.FAILED,
                    score=0.0,
                    passed=False,
                    violations=[f"実行エラー: {str(result)}"],
                    suggestions=["エラーを解決してください"],
                    execution_time=0,
                    details={"error": str(result)}
                ))
            else:
                processed_results.append(result)

        return processed_results

    async def _process_sequential(self, episode_data: Dict) -> List[AgentResult]:
        """順次処理"""
        results = []

        for agent in self.agents.values():
            result = await agent.run(episode_data)
            results.append(result)

            # 致命的な違反があれば早期終了
            if not result.passed and result.score < 3.0:
                print(f"⚠️ {agent.name} で致命的な違反を検出。処理を中断します。")
                break

        return results

    def _aggregate_results(self, results: List[AgentResult]) -> Dict[str, Any]:
        """結果を集約"""
        all_violations = []
        all_suggestions = []
        scores = []
        failed_agents = []
        passed_agents = []

        for result in results:
            scores.append(result.score)
            all_violations.extend(result.violations)
            all_suggestions.extend(result.suggestions)

            if result.passed:
                passed_agents.append(result.agent_name)
            else:
                failed_agents.append(result.agent_name)

        # 最終スコア（加重平均）
        weights = {
            'ValidationAgent': 0.25,  # PDCAルール
            'FactCheckAgent': 0.25,   # 事実確認
            'MilestoneAgent': 0.20,   # 節目重要度
            'EmpathyAgent': 0.15,     # 共感度
            'UniquenessAgent': 0.15   # 独自性
        }

        weighted_score = 0
        total_weight = 0
        for result in results:
            weight = weights.get(result.agent_name, 0.1)
            weighted_score += result.score * weight
            total_weight += weight

        final_score = weighted_score / total_weight if total_weight > 0 else 0

        # 最終判定
        if len(failed_agents) == 0:
            final_status = "APPROVED"
        elif len(failed_agents) <= 2 and final_score >= 6.0:
            final_status = "NEEDS_REVISION"
        else:
            final_status = "REJECTED"

        return {
            'final_status': final_status,
            'final_score': round(final_score, 2),
            'passed_agents': passed_agents,
            'failed_agents': failed_agents,
            'total_violations': len(all_violations),
            'violations': all_violations[:10],  # 上位10件
            'suggestions': list(set(all_suggestions))[:5],  # 重複を除いて上位5件
            'agent_results': {result.agent_name: result.__dict__ for result in results}
        }

    def generate_report(self) -> str:
        """実行レポートを生成"""
        if not self.execution_history:
            return "実行履歴がありません"

        total = len(self.execution_history)
        approved = sum(1 for h in self.execution_history if h['result'] == 'APPROVED')
        rejected = sum(1 for h in self.execution_history if h['result'] == 'REJECTED')
        needs_revision = total - approved - rejected

        avg_score = sum(h['score'] for h in self.execution_history) / total if total > 0 else 0

        report = f"""
========================================
Quality Gate Orchestrator Report
========================================
総処理数: {total}
承認: {approved} ({approved/total*100:.1f}%)
要修正: {needs_revision} ({needs_revision/total*100:.1f}%)
却下: {rejected} ({rejected/total*100:.1f}%)
平均スコア: {avg_score:.2f}/10.0

最近の処理:
"""
        for history in self.execution_history[-5:]:
            report += f"- {history['timestamp']}: {history['episode']} → {history['result']} (Score: {history['score']:.2f})\n"

        return report


async def test_orchestrator():
    """オーケストレーターのテスト"""
    orchestrator = QualityGateOrchestrator(parallel_execution=True)

    # テストエピソード
    test_episode = {
        'person_name': '大谷翔平',
        'user_age': 30,
        'episode_age': 23,
        'episode_type': 'achievement',
        'episode_content': 'メジャーリーグにデビューし、二刀流選手として活躍を開始',
        'empathy_score': 8.5,
        'memory_score': 9.0,
        'record_score': 9.5,
        'weighted_score': 8.8
    }

    # 処理実行
    result = await orchestrator.process_episode(test_episode)

    # 結果表示
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n" + orchestrator.generate_report())


if __name__ == "__main__":
    asyncio.run(test_orchestrator())