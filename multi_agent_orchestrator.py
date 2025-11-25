#!/usr/bin/env python3
"""
マルチエージェント協議オーケストレーター
3つ以上のAIエージェントによる高度な協議システム
"""

import asyncio
import json
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import hashlib
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MultiAgentOrchestrator')


class AgentRole(Enum):
    """エージェントの役割"""
    FACT_CHECKER = "fact_checker"      # 事実検証専門
    CODE_ANALYZER = "code_analyzer"    # コード分析専門
    QUALITY_GUARD = "quality_guard"    # 品質保証専門
    SEMANTICS = "semantics"            # 意味解析専門
    SECURITY = "security"              # セキュリティ専門


class ConsensusMethod(Enum):
    """合意形成方法"""
    MAJORITY = "majority"              # 多数決
    WEIGHTED = "weighted"              # 重み付け投票
    HIERARCHICAL = "hierarchical"     # 階層的決定
    BYZANTINE = "byzantine"            # ビザンチン合意


@dataclass
class AgentVote:
    """エージェントの投票"""
    agent_id: str
    role: AgentRole
    decision: str
    confidence: float
    reasoning: str
    evidence: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConsensusResult:
    """合意結果"""
    final_decision: str
    consensus_method: ConsensusMethod
    agreement_level: float
    votes: List[AgentVote]
    dissenting_opinions: List[AgentVote]
    confidence: float
    processing_time: float


class BaseAgent(ABC):
    """基底エージェントクラス"""

    def __init__(self, agent_id: str, role: AgentRole):
        self.agent_id = agent_id
        self.role = role
        self.decision_history = []
        self.performance_metrics = {
            "accuracy": 0.9,  # 初期精度
            "speed": 1.0,
            "reliability": 0.95
        }

    @abstractmethod
    async def analyze(self, content: str, context: Dict) -> AgentVote:
        """分析を実行して投票を返す"""
        pass

    def update_performance(self, feedback: Dict):
        """パフォーマンスメトリクスを更新"""
        if 'accuracy' in feedback:
            # 指数移動平均で更新
            alpha = 0.2
            self.performance_metrics['accuracy'] = (
                alpha * feedback['accuracy'] +
                (1 - alpha) * self.performance_metrics['accuracy']
            )


class FactCheckerAgent(BaseAgent):
    """事実検証エージェント"""

    def __init__(self):
        super().__init__("fact_checker_001", AgentRole.FACT_CHECKER)
        # 既存のFactCheckerを利用
        from src.fact_checker import FactChecker
        self.fact_checker = FactChecker()

    async def analyze(self, content: str, context: Dict) -> AgentVote:
        """事実検証を実行"""
        await asyncio.sleep(0.1)  # 処理時間シミュレーション

        # FactCheckerを使用
        if 'person_name' in context:
            report = self.fact_checker.check_episode(
                person_id=context.get('person_id', 'P000'),
                person_name=context['person_name'],
                episode_text=content,
                birth_year=None
            )

            confidence = report.total_score / 100.0
            decision = "APPROVE" if confidence > 0.7 else "REJECT"
            reasoning = f"事実検証スコア: {report.total_score}"
            evidence = [v.message for v in report.violations] if report.violations else ["検証済み"]
        else:
            confidence = 0.8
            decision = "APPROVE"
            reasoning = "汎用テキスト検証完了"
            evidence = []

        return AgentVote(
            agent_id=self.agent_id,
            role=self.role,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence
        )


class QualityGuardAgent(BaseAgent):
    """品質保証エージェント"""

    def __init__(self):
        super().__init__("quality_guard_001", AgentRole.QUALITY_GUARD)
        # PDCAガーディアンを利用
        from pdca_guardian import PDCAGuardian
        self.pdca_guardian = PDCAGuardian()

    async def analyze(self, content: str, context: Dict) -> AgentVote:
        """品質チェックを実行"""
        await asyncio.sleep(0.12)

        # PDCAルールチェック
        violations = self.pdca_guardian.check_episode_quality(
            content,
            context.get('episode_age', 0),
            context.get('person_name', '')
        )

        if not violations:
            confidence = 0.95
            decision = "APPROVE"
            reasoning = "PDCAルール違反なし"
            evidence = ["全ルールクリア"]
        else:
            confidence = max(0.3, 1.0 - len(violations) * 0.1)
            decision = "REJECT" if len(violations) > 3 else "REVIEW"
            reasoning = f"PDCAルール違反: {len(violations)}件"
            evidence = violations[:5]  # 最初の5件

        return AgentVote(
            agent_id=self.agent_id,
            role=self.role,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence
        )


class SemanticAnalyzerAgent(BaseAgent):
    """意味解析エージェント"""

    def __init__(self):
        super().__init__("semantic_analyzer_001", AgentRole.SEMANTICS)

    async def analyze(self, content: str, context: Dict) -> AgentVote:
        """意味解析を実行"""
        await asyncio.sleep(0.15)

        # 簡易的な意味解析
        text_length = len(content)
        has_context = bool(context)

        # 文の複雑度計算（簡易版）
        sentences = content.split('。')
        avg_sentence_length = sum(len(s) for s in sentences) / max(len(sentences), 1)

        if text_length < 50:
            confidence = 0.4
            decision = "REJECT"
            reasoning = "内容が不十分"
        elif avg_sentence_length > 100:
            confidence = 0.6
            decision = "REVIEW"
            reasoning = "文が複雑すぎる"
        else:
            confidence = 0.85
            decision = "APPROVE"
            reasoning = "意味構造が適切"

        evidence = [
            f"文字数: {text_length}",
            f"平均文長: {avg_sentence_length:.1f}",
            f"文数: {len(sentences)}"
        ]

        return AgentVote(
            agent_id=self.agent_id,
            role=self.role,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence
        )


class CodeAnalyzerAgent(BaseAgent):
    """コード分析エージェント（コンテンツにコードが含まれる場合）"""

    def __init__(self):
        super().__init__("code_analyzer_001", AgentRole.CODE_ANALYZER)

    async def analyze(self, content: str, context: Dict) -> AgentVote:
        """コード分析を実行"""
        await asyncio.sleep(0.1)

        # コードパターンの検出
        has_code = any(pattern in content for pattern in ['def ', 'class ', 'import ', 'function'])

        if has_code:
            confidence = 0.7
            decision = "REVIEW"
            reasoning = "コードパターン検出"
            evidence = ["技術的内容を含む"]
        else:
            confidence = 0.9
            decision = "APPROVE"
            reasoning = "非技術コンテンツ"
            evidence = ["一般的なテキスト"]

        return AgentVote(
            agent_id=self.agent_id,
            role=self.role,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence
        )


class SecurityAgent(BaseAgent):
    """セキュリティ分析エージェント"""

    def __init__(self):
        super().__init__("security_001", AgentRole.SECURITY)

    async def analyze(self, content: str, context: Dict) -> AgentVote:
        """セキュリティチェック"""
        await asyncio.sleep(0.08)

        # セキュリティパターンチェック
        security_patterns = ['password', 'token', 'api_key', 'secret', 'credential']
        risks = [pattern for pattern in security_patterns if pattern in content.lower()]

        if risks:
            confidence = 0.9
            decision = "REJECT"
            reasoning = f"セキュリティリスク検出: {risks}"
            evidence = risks
        else:
            confidence = 0.95
            decision = "APPROVE"
            reasoning = "セキュリティリスクなし"
            evidence = ["クリア"]

        return AgentVote(
            agent_id=self.agent_id,
            role=self.role,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence
        )


class MultiAgentOrchestrator:
    """マルチエージェントオーケストレーター"""

    def __init__(self):
        self.agents: List[BaseAgent] = []
        self.consensus_history = []
        self.learning_module = LearningModule()
        self._initialize_agents()

    def _initialize_agents(self):
        """エージェントを初期化"""
        self.agents = [
            FactCheckerAgent(),
            QualityGuardAgent(),
            SemanticAnalyzerAgent(),
            CodeAnalyzerAgent(),
            SecurityAgent()
        ]
        logger.info(f"✅ {len(self.agents)}個のエージェントを初期化")

    async def orchestrate(self,
                         content: str,
                         context: Dict,
                         consensus_method: ConsensusMethod = ConsensusMethod.WEIGHTED
                         ) -> ConsensusResult:
        """協議を実行"""
        start_time = time.time()

        logger.info(f"🎯 マルチエージェント協議開始 (方式: {consensus_method.value})")

        # 並列でエージェント分析を実行
        tasks = [agent.analyze(content, context) for agent in self.agents]
        votes = await asyncio.gather(*tasks)

        # 合意形成
        if consensus_method == ConsensusMethod.MAJORITY:
            result = self._majority_consensus(votes)
        elif consensus_method == ConsensusMethod.WEIGHTED:
            result = self._weighted_consensus(votes)
        elif consensus_method == ConsensusMethod.HIERARCHICAL:
            result = self._hierarchical_consensus(votes)
        elif consensus_method == ConsensusMethod.BYZANTINE:
            result = self._byzantine_consensus(votes)
        else:
            result = self._weighted_consensus(votes)  # デフォルト

        # 処理時間を追加
        result.processing_time = time.time() - start_time

        # 学習モジュールで重みを更新
        self.learning_module.update_weights(votes, result)

        # 履歴に追加
        self.consensus_history.append(result)

        return result

    def _majority_consensus(self, votes: List[AgentVote]) -> ConsensusResult:
        """多数決による合意"""
        decision_counts = {}
        for vote in votes:
            decision_counts[vote.decision] = decision_counts.get(vote.decision, 0) + 1

        # 最多票の決定を採用
        final_decision = max(decision_counts, key=decision_counts.get)
        agreement_level = decision_counts[final_decision] / len(votes)

        # 反対意見
        dissenting = [v for v in votes if v.decision != final_decision]

        # 平均信頼度
        avg_confidence = sum(v.confidence for v in votes) / len(votes)

        return ConsensusResult(
            final_decision=final_decision,
            consensus_method=ConsensusMethod.MAJORITY,
            agreement_level=agreement_level,
            votes=votes,
            dissenting_opinions=dissenting,
            confidence=avg_confidence,
            processing_time=0
        )

    def _weighted_consensus(self, votes: List[AgentVote]) -> ConsensusResult:
        """重み付け投票による合意"""
        # エージェントごとの重みを取得
        weights = self.learning_module.get_agent_weights(self.agents)

        # 決定ごとの重み付けスコア
        decision_scores = {}
        total_weight = 0

        for vote, agent in zip(votes, self.agents):
            weight = weights.get(agent.agent_id, 1.0) * vote.confidence
            decision_scores[vote.decision] = decision_scores.get(vote.decision, 0) + weight
            total_weight += weight

        # 最高スコアの決定を採用
        final_decision = max(decision_scores, key=decision_scores.get)
        agreement_level = decision_scores[final_decision] / total_weight if total_weight > 0 else 0

        # 反対意見
        dissenting = [v for v in votes if v.decision != final_decision]

        # 重み付け平均信頼度
        weighted_confidence = sum(
            v.confidence * weights.get(agent.agent_id, 1.0)
            for v, agent in zip(votes, self.agents)
        ) / len(votes)

        return ConsensusResult(
            final_decision=final_decision,
            consensus_method=ConsensusMethod.WEIGHTED,
            agreement_level=agreement_level,
            votes=votes,
            dissenting_opinions=dissenting,
            confidence=weighted_confidence,
            processing_time=0
        )

    def _hierarchical_consensus(self, votes: List[AgentVote]) -> ConsensusResult:
        """階層的決定による合意（役割による優先順位）"""
        # 役割の優先順位
        role_priority = {
            AgentRole.SECURITY: 5,      # 最高優先度
            AgentRole.FACT_CHECKER: 4,
            AgentRole.QUALITY_GUARD: 3,
            AgentRole.SEMANTICS: 2,
            AgentRole.CODE_ANALYZER: 1
        }

        # 最高優先度のREJECTを優先
        for priority_level in sorted(role_priority.values(), reverse=True):
            relevant_votes = [
                v for v in votes
                if role_priority.get(v.role, 0) == priority_level
            ]

            if relevant_votes:
                reject_votes = [v for v in relevant_votes if v.decision == "REJECT"]
                if reject_votes:
                    # 最高優先度でREJECTがあれば採用
                    return ConsensusResult(
                        final_decision="REJECT",
                        consensus_method=ConsensusMethod.HIERARCHICAL,
                        agreement_level=len(reject_votes) / len(votes),
                        votes=votes,
                        dissenting_opinions=[v for v in votes if v.decision != "REJECT"],
                        confidence=max(v.confidence for v in reject_votes),
                        processing_time=0
                    )

        # REJECTがなければ重み付け合意にフォールバック
        return self._weighted_consensus(votes)

    def _byzantine_consensus(self, votes: List[AgentVote]) -> ConsensusResult:
        """ビザンチン合意（フォールトトレラント）"""
        # 1/3以上の故障を許容
        n = len(votes)
        f = n // 3  # 許容故障数

        # 決定ごとの投票数
        decision_counts = {}
        for vote in votes:
            decision_counts[vote.decision] = decision_counts.get(vote.decision, 0) + 1

        # 2/3以上の合意があれば採用
        threshold = n - f
        for decision, count in decision_counts.items():
            if count >= threshold:
                return ConsensusResult(
                    final_decision=decision,
                    consensus_method=ConsensusMethod.BYZANTINE,
                    agreement_level=count / n,
                    votes=votes,
                    dissenting_opinions=[v for v in votes if v.decision != decision],
                    confidence=sum(v.confidence for v in votes if v.decision == decision) / count,
                    processing_time=0
                )

        # 合意に達しない場合は最多票
        return self._majority_consensus(votes)

    def get_performance_report(self) -> Dict:
        """パフォーマンスレポートを生成"""
        if not self.consensus_history:
            return {"status": "no_data"}

        total = len(self.consensus_history)
        avg_agreement = sum(r.agreement_level for r in self.consensus_history) / total
        avg_confidence = sum(r.confidence for r in self.consensus_history) / total
        avg_time = sum(r.processing_time for r in self.consensus_history) / total

        # 決定の分布
        decision_dist = {}
        for result in self.consensus_history:
            decision_dist[result.final_decision] = decision_dist.get(result.final_decision, 0) + 1

        # エージェントごとのパフォーマンス
        agent_performance = {}
        for agent in self.agents:
            agent_performance[agent.agent_id] = agent.performance_metrics

        return {
            "total_decisions": total,
            "average_agreement_level": avg_agreement,
            "average_confidence": avg_confidence,
            "average_processing_time": avg_time,
            "decision_distribution": decision_dist,
            "agent_performance": agent_performance,
            "learning_metrics": self.learning_module.get_metrics()
        }


class LearningModule:
    """機械学習による重み最適化モジュール"""

    def __init__(self):
        self.agent_weights = {}  # エージェントごとの重み
        self.learning_rate = 0.1
        self.history = []

    def get_agent_weights(self, agents: List[BaseAgent]) -> Dict[str, float]:
        """エージェントの重みを取得"""
        weights = {}
        for agent in agents:
            if agent.agent_id not in self.agent_weights:
                # 初期重みは役割に基づく
                initial_weights = {
                    AgentRole.SECURITY: 1.5,
                    AgentRole.FACT_CHECKER: 1.3,
                    AgentRole.QUALITY_GUARD: 1.2,
                    AgentRole.SEMANTICS: 1.0,
                    AgentRole.CODE_ANALYZER: 0.9
                }
                self.agent_weights[agent.agent_id] = initial_weights.get(agent.role, 1.0)

            weights[agent.agent_id] = self.agent_weights[agent.agent_id]

        return weights

    def update_weights(self, votes: List[AgentVote], result: ConsensusResult):
        """投票結果に基づいて重みを更新"""
        # 合意度が高い決定に賛成したエージェントの重みを増やす
        if result.agreement_level > 0.7:
            for vote in votes:
                if vote.decision == result.final_decision:
                    # 正しい判断をしたエージェントの重みを増やす
                    current_weight = self.agent_weights.get(vote.agent_id, 1.0)
                    self.agent_weights[vote.agent_id] = current_weight + self.learning_rate * vote.confidence
                else:
                    # 誤った判断をしたエージェントの重みを減らす
                    current_weight = self.agent_weights.get(vote.agent_id, 1.0)
                    self.agent_weights[vote.agent_id] = max(0.1, current_weight - self.learning_rate * 0.5)

        # 正規化（重みの合計が一定になるように）
        total_weight = sum(self.agent_weights.values())
        if total_weight > 0:
            for agent_id in self.agent_weights:
                self.agent_weights[agent_id] /= (total_weight / len(self.agent_weights))

        # 履歴に追加
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "weights": self.agent_weights.copy(),
            "agreement_level": result.agreement_level
        })

    def get_metrics(self) -> Dict:
        """学習メトリクスを取得"""
        if not self.history:
            return {"status": "no_learning_data"}

        recent_history = self.history[-10:]  # 最近10件
        avg_agreement = sum(h["agreement_level"] for h in recent_history) / len(recent_history)

        return {
            "total_updates": len(self.history),
            "recent_agreement_level": avg_agreement,
            "current_weights": self.agent_weights,
            "weight_variance": np.var(list(self.agent_weights.values())) if self.agent_weights else 0
        }


async def demonstrate_multi_agent():
    """マルチエージェントシステムのデモンストレーション"""

    print("\n" + "="*70)
    print("🤖 マルチエージェント協議システム デモンストレーション")
    print("="*70)

    orchestrator = MultiAgentOrchestrator()

    # テストケース
    test_cases = [
        {
            "content": "2001年、27歳のイチローはメジャーリーグ1年目でMVPと新人王を同時受賞。",
            "context": {"person_name": "イチロー", "episode_age": 27},
            "method": ConsensusMethod.WEIGHTED
        },
        {
            "content": "このコードにはpasswordという変数が含まれています。",
            "context": {"type": "security_check"},
            "method": ConsensusMethod.HIERARCHICAL
        },
        {
            "content": "とても短い文。",
            "context": {"type": "quality_check"},
            "method": ConsensusMethod.BYZANTINE
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n📝 テストケース {i}: {test['method'].value}方式")
        print(f"   内容: {test['content'][:50]}...")

        result = await orchestrator.orchestrate(
            test['content'],
            test['context'],
            test['method']
        )

        print(f"\n   🎯 最終決定: {result.final_decision}")
        print(f"   📊 合意度: {result.agreement_level:.1%}")
        print(f"   🔍 信頼度: {result.confidence:.1%}")
        print(f"   ⏱️ 処理時間: {result.processing_time:.3f}秒")

        # 各エージェントの投票
        print("\n   📋 エージェント投票:")
        for vote in result.votes:
            print(f"      {vote.role.value}: {vote.decision} (信頼度: {vote.confidence:.1%})")

        if result.dissenting_opinions:
            print(f"\n   ⚠️ 反対意見: {len(result.dissenting_opinions)}件")

    # パフォーマンスレポート
    report = orchestrator.get_performance_report()
    print("\n" + "="*70)
    print("📊 パフォーマンスレポート")
    print("="*70)
    print(f"総決定数: {report['total_decisions']}")
    print(f"平均合意度: {report['average_agreement_level']:.1%}")
    print(f"平均信頼度: {report['average_confidence']:.1%}")
    print(f"平均処理時間: {report['average_processing_time']:.3f}秒")

    print("\n🧠 学習モジュール統計:")
    learning_metrics = report['learning_metrics']
    if 'current_weights' in learning_metrics:
        print("   現在の重み:")
        for agent_id, weight in learning_metrics['current_weights'].items():
            print(f"      {agent_id}: {weight:.2f}")


if __name__ == "__main__":
    # デモ実行
    asyncio.run(demonstrate_multi_agent())
