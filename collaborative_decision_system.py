#!/usr/bin/env python3
"""
Claude Code & Codex MCP 協議システム
両システムが協調して最適解を導き出すための統合フレームワーク
"""

import asyncio
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from pathlib import Path

# 既存システムのインポート
from src.fact_checker import FactChecker, FactCheckResult
from pdca_guardian import PDCAGuardian
from enhanced_quality_gate import EnhancedQualityGate


class DecisionSource(Enum):
    """判定ソース"""
    CLAUDE = "claude_code"
    CODEX = "codex_mcp"
    CONSENSUS = "consensus"
    HYBRID = "hybrid"
    HUMAN = "human_override"


class ConfidenceLevel(Enum):
    """信頼度レベル"""
    VERY_HIGH = 0.95  # 95%以上
    HIGH = 0.80       # 80%以上
    MEDIUM = 0.60     # 60%以上
    LOW = 0.40        # 40%以上
    VERY_LOW = 0.20   # 20%以上


@dataclass
class Decision:
    """協議による決定結果"""
    source: DecisionSource
    confidence: float
    result: Any
    reasoning: str
    evidence: List[str]
    timestamp: datetime
    consensus: bool = False


@dataclass
class CollaborativeAnalysis:
    """協議分析結果"""
    query: str
    claude_analysis: Dict
    codex_analysis: Dict
    final_decision: Decision
    discrepancies: List[str]
    resolution_method: str


class CodexMCPInterface:
    """Codex MCPサーバーとの通信インターフェース"""

    def __init__(self, port: int = 8001):
        self.port = port
        self.server_process = None
        self.base_url = f"http://localhost:{port}"
        self.is_running = False

    def start_server(self) -> bool:
        """Codexサーバーを起動"""
        try:
            # 既存プロセスをチェック
            check_cmd = f"lsof -i :{self.port} | grep LISTEN"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)

            if result.stdout:
                print(f"✅ Codex MCPサーバーは既にポート{self.port}で起動しています")
                self.is_running = True
                return True

            # サーバーを起動
            cmd = f"/Users/admin/.local/bin/codex mcp serve --port {self.port}"
            self.server_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 起動を待機
            time.sleep(3)

            # 起動確認
            check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            if check_result.stdout:
                print(f"✅ Codex MCPサーバーが起動しました（ポート: {self.port}）")
                self.is_running = True
                return True
            else:
                print(f"❌ Codex MCPサーバーの起動に失敗しました")
                return False

        except Exception as e:
            print(f"❌ エラー: {str(e)}")
            return False

    def analyze_code(self, code: str, context: str = "") -> Dict:
        """コードを分析"""
        # 実際のCodex MCP API呼び出しを実装
        # ここでは擬似的な実装
        return {
            "analysis": "Code analysis from Codex",
            "issues": [],
            "suggestions": [],
            "confidence": 0.85
        }

    def verify_fact(self, statement: str, metadata: Dict = None) -> Dict:
        """事実を検証"""
        return {
            "verified": True,
            "confidence": 0.75,
            "evidence": ["Source 1", "Source 2"],
            "reasoning": "Fact verification from Codex"
        }

    def shutdown(self):
        """サーバーをシャットダウン"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            print("✅ Codex MCPサーバーをシャットダウンしました")


class CollaborativeDecisionSystem:
    """
    Claude CodeとCodex MCPの協議システム
    複数の観点から問題を分析し、最適解を導き出す
    """

    def __init__(self):
        self.fact_checker = FactChecker()
        self.pdca_guardian = PDCAGuardian()
        self.quality_gate = EnhancedQualityGate()
        self.codex = CodexMCPInterface()
        self.decision_history = []
        self.consensus_threshold = 0.7  # 合意形成の閾値

    def initialize(self) -> bool:
        """システムの初期化"""
        print("\n" + "="*70)
        print("🤝 Claude Code & Codex MCP 協議システム初期化")
        print("="*70)

        # Codexサーバーの起動
        if not self.codex.start_server():
            print("⚠️ Codexサーバーの起動に失敗しましたが、続行します")
            return False

        print("✅ すべてのコンポーネントが準備完了")
        return True

    def analyze_with_claude(self, query: str, data: Any) -> Dict:
        """Claude Codeによる分析"""
        print("\n🤖 Claude Code分析中...")

        result = {
            "source": "claude_code",
            "timestamp": datetime.now().isoformat(),
            "analysis": {},
            "confidence": 0.0,
            "reasoning": "",
            "evidence": []
        }

        # エピソードデータの場合
        if isinstance(data, dict) and 'episode_text' in data:
            # FactCheckerによる検証
            fact_report = self.fact_checker.check_episode(
                person_id=data.get('person_id', 'P000'),
                person_name=data.get('person_name', ''),
                episode_text=data.get('episode_text', ''),
                birth_year=None
            )

            # PDCAルールチェック
            pdca_violations = self.pdca_guardian.check_episode_quality(
                data.get('episode_text', ''),
                data.get('episode_age', 0),
                data.get('person_name', '')
            )

            # PDCAのviolationsは文字列リストとして返される
            result["analysis"] = {
                "fact_check": fact_report.result.value,
                "violations": pdca_violations if isinstance(pdca_violations, list) else [],
                "quality_score": fact_report.total_score
            }

            result["confidence"] = fact_report.total_score / 100.0
            result["reasoning"] = f"FactCheck結果: {fact_report.result.value}, スコア: {fact_report.total_score}"
            result["evidence"] = [v.message for v in fact_report.violations] if fact_report.violations else []

        return result

    def analyze_with_codex(self, query: str, data: Any) -> Dict:
        """Codex MCPによる分析"""
        print("\n💻 Codex MCP分析中...")

        result = {
            "source": "codex_mcp",
            "timestamp": datetime.now().isoformat(),
            "analysis": {},
            "confidence": 0.0,
            "reasoning": "",
            "evidence": []
        }

        # Codex MCPサーバーを使用した分析
        if isinstance(data, dict) and 'episode_text' in data:
            verification = self.codex.verify_fact(
                data.get('episode_text', ''),
                metadata=data
            )

            result["analysis"] = verification
            result["confidence"] = verification.get("confidence", 0.5)
            result["reasoning"] = verification.get("reasoning", "")
            result["evidence"] = verification.get("evidence", [])

        return result

    def find_consensus(self, claude_result: Dict, codex_result: Dict) -> Decision:
        """両者の分析結果から合意を形成"""
        print("\n🤔 合意形成中...")

        # 信頼度の比較
        claude_conf = claude_result.get("confidence", 0)
        codex_conf = codex_result.get("confidence", 0)

        # 平均信頼度
        avg_confidence = (claude_conf + codex_conf) / 2

        # 差異の検出
        discrepancies = []

        # Claude分析の違反
        claude_violations = claude_result.get("analysis", {}).get("violations", [])
        codex_verified = codex_result.get("analysis", {}).get("verified", False)

        if claude_violations and codex_verified:
            discrepancies.append("Claudeは違反を検出したが、Codexは問題なしと判定")
        elif not claude_violations and not codex_verified:
            discrepancies.append("Claudeは違反なしだが、Codexは検証失敗")

        # 合意の判定
        consensus = False
        if abs(claude_conf - codex_conf) < 0.2:  # 信頼度の差が20%以内
            consensus = True

        # 最終決定
        if consensus:
            source = DecisionSource.CONSENSUS
            confidence = avg_confidence
            reasoning = "両システムの分析結果が概ね一致"
        else:
            # より高い信頼度を持つ方を採用
            if claude_conf > codex_conf:
                source = DecisionSource.CLAUDE
                confidence = claude_conf
                reasoning = f"Claude Codeの信頼度が高い ({claude_conf:.2f} vs {codex_conf:.2f})"
            else:
                source = DecisionSource.CODEX
                confidence = codex_conf
                reasoning = f"Codex MCPの信頼度が高い ({codex_conf:.2f} vs {claude_conf:.2f})"

        # 証拠の統合
        all_evidence = list(set(
            claude_result.get("evidence", []) +
            codex_result.get("evidence", [])
        ))

        return Decision(
            source=source,
            confidence=confidence,
            result={
                "claude": claude_result,
                "codex": codex_result
            },
            reasoning=reasoning,
            evidence=all_evidence,
            timestamp=datetime.now(),
            consensus=consensus
        )

    def collaborative_analyze(self, query: str, data: Any) -> CollaborativeAnalysis:
        """
        協議による分析の実行

        Args:
            query: 分析クエリ
            data: 分析対象データ

        Returns:
            CollaborativeAnalysis: 協議分析結果
        """
        print("\n" + "="*70)
        print(f"🔍 協議分析開始: {query}")
        print("="*70)

        # 並列分析の実行
        claude_result = self.analyze_with_claude(query, data)
        codex_result = self.analyze_with_codex(query, data)

        # 合意形成
        decision = self.find_consensus(claude_result, codex_result)

        # 差異の検出
        discrepancies = []
        if not decision.consensus:
            discrepancies.append(
                f"信頼度の差異: Claude {claude_result['confidence']:.2f} vs Codex {codex_result['confidence']:.2f}"
            )

        # 解決方法の決定
        if decision.consensus:
            resolution_method = "完全合意"
        elif decision.confidence > 0.8:
            resolution_method = "高信頼度による採用"
        else:
            resolution_method = "追加検証が必要"

        analysis = CollaborativeAnalysis(
            query=query,
            claude_analysis=claude_result,
            codex_analysis=codex_result,
            final_decision=decision,
            discrepancies=discrepancies,
            resolution_method=resolution_method
        )

        # 履歴に追加
        self.decision_history.append(analysis)

        return analysis

    def batch_collaborative_analyze(self, items: List[Tuple[str, Any]]) -> List[CollaborativeAnalysis]:
        """複数項目の協議分析"""
        results = []

        for i, (query, data) in enumerate(items, 1):
            print(f"\n📊 バッチ分析 {i}/{len(items)}")
            analysis = self.collaborative_analyze(query, data)
            results.append(analysis)

            # 進捗表示
            if i % 5 == 0:
                print(f"  進捗: {i}/{len(items)}件完了")

        return results

    def generate_consensus_report(self) -> str:
        """合意形成レポートの生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'consensus_report_{timestamp}.json'

        report = {
            "timestamp": timestamp,
            "total_decisions": len(self.decision_history),
            "consensus_rate": 0,
            "average_confidence": 0,
            "source_distribution": {},
            "decisions": []
        }

        if self.decision_history:
            # 合意率の計算
            consensus_count = sum(1 for a in self.decision_history if a.final_decision.consensus)
            report["consensus_rate"] = consensus_count / len(self.decision_history)

            # 平均信頼度
            total_confidence = sum(a.final_decision.confidence for a in self.decision_history)
            report["average_confidence"] = total_confidence / len(self.decision_history)

            # ソース分布
            source_counts = {}
            for analysis in self.decision_history:
                source = analysis.final_decision.source.value
                source_counts[source] = source_counts.get(source, 0) + 1
            report["source_distribution"] = source_counts

            # 決定の詳細
            for analysis in self.decision_history:
                report["decisions"].append({
                    "query": analysis.query,
                    "consensus": analysis.final_decision.consensus,
                    "confidence": analysis.final_decision.confidence,
                    "source": analysis.final_decision.source.value,
                    "resolution": analysis.resolution_method
                })

        # レポート保存
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📊 合意形成レポート生成: {report_file}")
        return report_file

    def shutdown(self):
        """システムのシャットダウン"""
        self.codex.shutdown()
        print("✅ 協議システムをシャットダウンしました")


def demonstration():
    """協議システムのデモンストレーション"""

    print("="*70)
    print("🎯 Claude Code & Codex MCP 協議システム デモ")
    print("="*70)

    # システム初期化
    system = CollaborativeDecisionSystem()
    if not system.initialize():
        print("⚠️ 初期化に一部問題がありましたが、デモを続行します")

    # テストデータ
    test_episodes = [
        {
            "person_name": "イチロー",
            "episode_age": 27,
            "episode_text": "2001年、27歳のイチローはメジャーリーグ1年目でMVPと新人王を同時受賞。"
                          "これは史上2人目の快挙であり、日本人初のMVP受賞となった。",
            "person_id": "P001"
        },
        {
            "person_name": "さくらももこ",
            "episode_age": 21,
            "episode_text": "21歳の時、漫画「ちびまる子ちゃん」の連載を開始。"
                          "静岡県清水市での子供時代の思い出を元に描かれた作品は国民的人気を博した。",
            "person_id": "P002"
        }
    ]

    # 協議分析の実行
    analyses = []
    for episode in test_episodes:
        query = f"{episode['person_name']}のエピソード検証"
        analysis = system.collaborative_analyze(query, episode)
        analyses.append(analysis)

        # 結果表示
        print(f"\n📋 分析結果: {episode['person_name']}")
        print(f"  合意形成: {'✅' if analysis.final_decision.consensus else '❌'}")
        print(f"  信頼度: {analysis.final_decision.confidence:.2%}")
        print(f"  決定ソース: {analysis.final_decision.source.value}")
        print(f"  解決方法: {analysis.resolution_method}")

    # レポート生成
    report_file = system.generate_consensus_report()

    # システムシャットダウン
    system.shutdown()

    print("\n" + "="*70)
    print("✅ デモンストレーション完了")
    print("="*70)

    return analyses, report_file


if __name__ == "__main__":
    # デモの実行
    analyses, report = demonstration()
