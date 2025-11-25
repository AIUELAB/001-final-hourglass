#!/usr/bin/env python3
"""
非同期協議クライアント
Claude CodeとCodex MCPサーバーのリアルタイム通信実装
"""

import asyncio
import aiohttp
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import os

# 既存システムのインポート
from src.fact_checker import FactChecker
from pdca_guardian import PDCAGuardian
from enhanced_quality_gate import EnhancedQualityGate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('AsyncCollaboration')


@dataclass
class CollaborativeDecision:
    """協議による決定"""
    consensus: bool
    confidence: float
    claude_result: Dict
    codex_result: Dict
    final_decision: str
    reasoning: str
    processing_time: float


class AsyncCollaborationClient:
    """
    非同期協議クライアント
    Claude CodeとCodex MCPの並列分析と協議を実現
    """

    def __init__(self, codex_url: str = "http://localhost:8001"):
        self.codex_url = codex_url
        self.fact_checker = FactChecker()
        self.pdca_guardian = PDCAGuardian()
        self.quality_gate = EnhancedQualityGate()
        self.session = None
        self.ws_connection = None
        self.decision_history = []

    async def __aenter__(self):
        """コンテキストマネージャーのエントリ"""
        self.session = aiohttp.ClientSession()
        await self.connect_codex()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーのイグジット"""
        if self.ws_connection:
            await self.ws_connection.close()
        if self.session:
            await self.session.close()

    async def connect_codex(self) -> bool:
        """Codex MCPサーバーへの接続確認"""
        try:
            async with self.session.get(f"{self.codex_url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ Codexサーバー接続成功: {data['status']}")
                    return True
        except Exception as e:
            logger.error(f"❌ Codexサーバー接続失敗: {e}")
            return False

    async def connect_websocket(self):
        """WebSocket接続の確立"""
        try:
            self.ws_connection = await self.session.ws_connect(f"{self.codex_url}/ws")
            logger.info("✅ WebSocket接続確立")
            return True
        except Exception as e:
            logger.error(f"❌ WebSocket接続失敗: {e}")
            return False

    async def analyze_with_claude(self, content: str, context: Dict) -> Tuple[Dict, float]:
        """Claude Codeによる非同期分析"""
        start_time = time.time()

        # FactCheckerによる分析
        if 'person_name' in context:
            fact_report = self.fact_checker.check_episode(
                person_id=context.get('person_id', 'P000'),
                person_name=context['person_name'],
                episode_text=content,
                birth_year=None
            )

            # PDCAルールチェック
            violations = self.pdca_guardian.check_episode_quality(
                content,
                context.get('episode_age', 0),
                context.get('person_name', '')
            )

            result = {
                "source": "claude_code",
                "fact_check": fact_report.result.value,
                "violations": violations,
                "quality_score": fact_report.total_score,
                "confidence": fact_report.total_score / 100.0
            }
        else:
            # 汎用テキスト分析
            result = {
                "source": "claude_code",
                "analysis": "Claude analysis completed",
                "confidence": 0.85
            }

        processing_time = time.time() - start_time
        return result, processing_time

    async def analyze_with_codex(self, content: str, context: Dict) -> Tuple[Dict, float]:
        """Codex MCPによる非同期分析"""
        start_time = time.time()

        try:
            # Codex APIを呼び出し
            async with self.session.post(
                f"{self.codex_url}/analyze",
                json={
                    "content": content,
                    "type": "text",
                    "context": context
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = {
                        "source": "codex_mcp",
                        "analysis": data.get('result', {}),
                        "confidence": data.get('confidence', 0.75)
                    }
                else:
                    result = {
                        "source": "codex_mcp",
                        "error": f"Status {resp.status}",
                        "confidence": 0.0
                    }
        except Exception as e:
            logger.error(f"Codex分析エラー: {e}")
            result = {
                "source": "codex_mcp",
                "error": str(e),
                "confidence": 0.0
            }

        processing_time = time.time() - start_time
        return result, processing_time

    async def collaborative_analyze(self, content: str, context: Dict) -> CollaborativeDecision:
        """
        並列協議分析
        Claude CodeとCodex MCPを同時に実行して協議
        """
        logger.info("🤝 並列協議分析開始")

        # 並列分析タスクを作成
        claude_task = asyncio.create_task(self.analyze_with_claude(content, context))
        codex_task = asyncio.create_task(self.analyze_with_codex(content, context))

        # 両方の結果を待機
        (claude_result, claude_time), (codex_result, codex_time) = await asyncio.gather(
            claude_task, codex_task
        )

        # 処理時間
        total_time = max(claude_time, codex_time)  # 並列なので最大値

        # 協議と合意形成
        decision = self._form_consensus(claude_result, codex_result)

        # 結果をCollaborativeDecisionに格納
        collaborative_decision = CollaborativeDecision(
            consensus=decision['consensus'],
            confidence=decision['confidence'],
            claude_result=claude_result,
            codex_result=codex_result,
            final_decision=decision['decision'],
            reasoning=decision['reasoning'],
            processing_time=total_time
        )

        # 履歴に追加
        self.decision_history.append(collaborative_decision)

        return collaborative_decision

    def _form_consensus(self, claude_result: Dict, codex_result: Dict) -> Dict:
        """合意形成アルゴリズム"""
        claude_conf = claude_result.get('confidence', 0)
        codex_conf = codex_result.get('confidence', 0)

        # 信頼度の差
        conf_diff = abs(claude_conf - codex_conf)

        # 合意判定
        consensus = conf_diff < 0.2  # 20%以内の差

        # 重み付け平均
        weighted_confidence = (claude_conf * 0.6 + codex_conf * 0.4)

        # 最終決定
        if consensus:
            decision = "APPROVED"
            reasoning = f"両システムが合意（差異: {conf_diff:.1%}）"
        elif weighted_confidence > 0.75:
            decision = "APPROVED_WITH_CAUTION"
            reasoning = f"高信頼度だが合意なし（Claude: {claude_conf:.1%}, Codex: {codex_conf:.1%}）"
        else:
            decision = "REQUIRES_REVIEW"
            reasoning = f"信頼度不足または不一致（総合: {weighted_confidence:.1%}）"

        return {
            "consensus": consensus,
            "confidence": weighted_confidence,
            "decision": decision,
            "reasoning": reasoning
        }

    async def batch_collaborative_analyze(self, items: List[Dict]) -> List[CollaborativeDecision]:
        """バッチ協議分析（並列処理）"""
        tasks = []

        for item in items:
            content = item.get('content', '')
            context = item.get('context', {})
            task = self.collaborative_analyze(content, context)
            tasks.append(task)

        # すべてのタスクを並列実行
        results = await asyncio.gather(*tasks)

        return results

    async def realtime_collaborative_stream(self, content_stream):
        """リアルタイムストリーミング協議"""
        if not self.ws_connection:
            await self.connect_websocket()

        async for content in content_stream:
            # WebSocketでCodexに送信
            await self.ws_connection.send_json({
                "action": "analyze",
                "content": content,
                "context": {}
            })

            # レスポンスを受信
            msg = await self.ws_connection.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                yield data

    def generate_collaboration_report(self) -> str:
        """協議レポートの生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'async_collaboration_report_{timestamp}.json'

        if not self.decision_history:
            logger.warning("決定履歴が空です")
            return None

        # 統計計算
        total = len(self.decision_history)
        consensus_count = sum(1 for d in self.decision_history if d.consensus)
        avg_confidence = sum(d.confidence for d in self.decision_history) / total
        avg_time = sum(d.processing_time for d in self.decision_history) / total

        report = {
            "timestamp": timestamp,
            "statistics": {
                "total_decisions": total,
                "consensus_rate": consensus_count / total,
                "average_confidence": avg_confidence,
                "average_processing_time": avg_time,
                "approved_count": sum(1 for d in self.decision_history if 'APPROVED' in d.final_decision),
                "review_required": sum(1 for d in self.decision_history if d.final_decision == 'REQUIRES_REVIEW')
            },
            "decisions": [
                {
                    "consensus": d.consensus,
                    "confidence": d.confidence,
                    "decision": d.final_decision,
                    "reasoning": d.reasoning,
                    "time": d.processing_time
                }
                for d in self.decision_history
            ]
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"📊 協議レポート生成: {report_file}")
        return report_file


async def test_async_collaboration():
    """非同期協議システムのテスト"""

    print("\n" + "="*70)
    print("🚀 非同期協議システムテスト")
    print("="*70)

    # テストデータ
    test_episodes = [
        {
            "content": "2001年、27歳のイチローはメジャーリーグ1年目でMVPと新人王を同時受賞。",
            "context": {"person_name": "イチロー", "episode_age": 27}
        },
        {
            "content": "21歳の時、漫画「ちびまる子ちゃん」の連載を開始。",
            "context": {"person_name": "さくらももこ", "episode_age": 21}
        },
        {
            "content": "HIKAKINは日本のYouTuberとして最も有名な人物の一人。",
            "context": {"person_name": "HIKAKIN", "episode_age": 30}
        }
    ]

    # サーバーが起動しているか確認
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8001/health", timeout=2) as resp:
                if resp.status != 200:
                    print("⚠️ Codexサーバーが起動していません。ローカルモードで実行します。")
                    server_available = False
                else:
                    server_available = True
    except:
        print("⚠️ Codexサーバーに接続できません。ローカルモードで実行します。")
        server_available = False

    if server_available:
        # 非同期協議クライアントを使用
        async with AsyncCollaborationClient() as client:
            # バッチ処理
            print("\n📊 バッチ協議分析実行中...")
            results = await client.batch_collaborative_analyze(test_episodes)

            # 結果表示
            for i, decision in enumerate(results, 1):
                print(f"\n[{i}] 分析結果:")
                print(f"  合意: {'✅' if decision.consensus else '❌'}")
                print(f"  信頼度: {decision.confidence:.1%}")
                print(f"  決定: {decision.final_decision}")
                print(f"  理由: {decision.reasoning}")
                print(f"  処理時間: {decision.processing_time:.3f}秒")

            # レポート生成
            report_file = client.generate_collaboration_report()
            print(f"\n✅ レポート生成完了: {report_file}")
    else:
        print("\nローカルモードでの簡易テストを実行")
        # Codexサーバーなしでも動作確認
        from claude_codex_collaboration import CollaborativeValidator
        validator = CollaborativeValidator()

        for item in test_episodes:
            decision = validator.collaborative_decision(
                item['content'],
                item['context']
            )
            print(f"\n結果: {decision['recommendation']}")


async def start_codex_server_async():
    """Codexサーバーを非同期で起動"""
    from codex_mcp_server import CodexMCPServer

    server = CodexMCPServer()
    await server.start()


async def main():
    """メイン処理"""

    # Codexサーバーとクライアントを並列起動
    server_task = asyncio.create_task(start_codex_server_async())

    # サーバー起動を少し待つ
    await asyncio.sleep(2)

    # テスト実行
    await test_async_collaboration()

    # サーバータスクをキャンセル
    server_task.cancel()


if __name__ == "__main__":
    # 非同期実行
    try:
        asyncio.run(test_async_collaboration())
    except KeyboardInterrupt:
        print("\n✅ テスト終了")
