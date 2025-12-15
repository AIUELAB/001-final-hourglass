#!/usr/bin/env python3
"""
統合品質管理システム
Enhanced Quality Gate + Claude Code & Codex MCP協議システム
"""

import asyncio
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
import sys

# 既存システム
from enhanced_quality_gate import EnhancedQualityGate, safe_csv_write
from async_collaboration_client import AsyncCollaborationClient
from src.fact_checker import FactChecker
from pdca_guardian import PDCAGuardian


class IntegratedQualitySystem:
    """
    統合品質管理システム
    すべてのエピソード処理を協議システム経由で実行
    """

    def __init__(self, enable_collaboration: bool = True):
        self.enable_collaboration = enable_collaboration
        self.quality_gate = EnhancedQualityGate()
        self.fact_checker = FactChecker()
        self.pdca_guardian = PDCAGuardian()
        self.collaboration_client = None
        self.processing_log = []

    async def initialize(self):
        """システム初期化"""
        print("="*70)
        print("🚀 統合品質管理システム 起動")
        print("="*70)

        if self.enable_collaboration:
            try:
                self.collaboration_client = AsyncCollaborationClient()
                await self.collaboration_client.__aenter__()
                print("✅ 協議システム: 有効")
            except Exception as e:
                print(f"⚠️ 協議システム接続失敗: {e}")
                print("   単独モードで動作します")
                self.enable_collaboration = False
        else:
            print("ℹ️ 協議システム: 無効（単独モード）")

    async def shutdown(self):
        """システムシャットダウン"""
        if self.collaboration_client:
            await self.collaboration_client.__aexit__(None, None, None)
        print("✅ システムシャットダウン完了")

    async def process_episode(self, episode: Dict) -> Dict:
        """
        エピソードの処理
        協議システムを使用して品質チェック
        """
        person_name = episode.get('person_name', '')
        episode_text = episode.get('episode_text', '')
        episode_age = episode.get('episode_age', 0)

        print(f"\n処理中: {person_name} ({episode_age}歳)")

        # Quality Gate基本チェック
        gate_result = self.quality_gate.check_episode(episode)

        if self.enable_collaboration and self.collaboration_client:
            # 協議システムによる高度な検証
            context = {
                'person_name': person_name,
                'episode_age': episode_age,
                'person_id': episode.get('person_id', 'P000')
            }

            decision = await self.collaboration_client.collaborative_analyze(
                episode_text, context
            )

            # 協議結果を統合
            episode['collaboration_consensus'] = decision.consensus
            episode['collaboration_confidence'] = decision.confidence
            episode['collaboration_decision'] = decision.final_decision

            # 最終判定
            if decision.final_decision == "REQUIRES_REVIEW":
                episode['quality_status'] = 'review_required'
                print(f"  ⚠️ レビュー必要: {decision.reasoning}")
            elif decision.final_decision == "APPROVED_WITH_CAUTION":
                episode['quality_status'] = 'approved_with_caution'
                print(f"  ✅ 条件付き承認: {decision.reasoning}")
            else:
                episode['quality_status'] = 'approved'
                print(f"  ✅ 承認: 信頼度 {decision.confidence:.1%}")
        else:
            # 単独モード
            if gate_result.score >= 80:
                episode['quality_status'] = 'approved'
                print(f"  ✅ 承認: スコア {gate_result.score:.1f}")
            else:
                episode['quality_status'] = 'review_required'
                print(f"  ⚠️ レビュー必要: スコア {gate_result.score:.1f}")

        # Quality Gateの結果も保存
        episode['quality_score'] = gate_result.score
        episode['quality_issues'] = json.dumps(gate_result.violations, ensure_ascii=False)

        # ログに記録
        self.processing_log.append({
            'person_name': person_name,
            'status': episode['quality_status'],
            'score': gate_result.score,
            'timestamp': datetime.now().isoformat()
        })

        return episode

    async def batch_process_episodes(self, csv_file: str) -> pd.DataFrame:
        """
        CSVファイルのバッチ処理
        協議システムによる並列処理
        """
        print(f"\n📂 ファイル読み込み: {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        print(f"  エピソード数: {len(df)}")

        processed_episodes = []

        if self.enable_collaboration and self.collaboration_client:
            # 協議システムでバッチ処理
            items = []
            for _, row in df.iterrows():
                items.append({
                    'content': row.get('episode_text', ''),
                    'context': {
                        'person_name': row.get('person_name', ''),
                        'episode_age': row.get('episode_age', 0),
                        'person_id': row.get('person_id', 'P000')
                    }
                })

            # 並列協議分析
            print("\n🤝 協議システムによる並列分析中...")
            decisions = await self.collaboration_client.batch_collaborative_analyze(items)

            # 結果をDataFrameに統合
            for i, (_, row) in enumerate(df.iterrows()):
                episode = row.to_dict()
                decision = decisions[i]

                episode['collaboration_consensus'] = decision.consensus
                episode['collaboration_confidence'] = decision.confidence
                episode['collaboration_decision'] = decision.final_decision

                # Quality Gateチェックも実行
                gate_result = self.quality_gate.check_episode(episode)
                episode['quality_score'] = gate_result.score
                episode['quality_issues'] = json.dumps(gate_result.violations, ensure_ascii=False)

                # 最終ステータス決定
                if decision.final_decision == "APPROVED":
                    episode['quality_status'] = 'approved'
                elif decision.final_decision == "APPROVED_WITH_CAUTION":
                    episode['quality_status'] = 'approved_with_caution'
                else:
                    episode['quality_status'] = 'review_required'

                processed_episodes.append(episode)

                # 進捗表示
                if (i + 1) % 10 == 0:
                    print(f"  進捗: {i+1}/{len(df)} 完了")
        else:
            # 単独モード処理
            for idx, row in df.iterrows():
                episode = await self.process_episode(row.to_dict())
                processed_episodes.append(episode)

        return pd.DataFrame(processed_episodes)

    def generate_quality_report(self) -> str:
        """品質レポートの生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'integrated_quality_report_{timestamp}.json'

        # 統計計算
        total = len(self.processing_log)
        if total == 0:
            print("⚠️ 処理ログが空です")
            return None

        approved = sum(1 for log in self.processing_log if 'approved' in log['status'])
        review_required = sum(1 for log in self.processing_log if log['status'] == 'review_required')
        avg_score = sum(log['score'] for log in self.processing_log) / total

        report = {
            'timestamp': timestamp,
            'statistics': {
                'total_episodes': total,
                'approved': approved,
                'review_required': review_required,
                'approval_rate': approved / total if total > 0 else 0,
                'average_score': avg_score,
                'collaboration_enabled': self.enable_collaboration
            },
            'processing_log': self.processing_log
        }

        # 協議システムのレポートも含める
        if self.collaboration_client and self.collaboration_client.decision_history:
            collaboration_report = {
                'total_decisions': len(self.collaboration_client.decision_history),
                'consensus_rate': sum(1 for d in self.collaboration_client.decision_history if d.consensus) /
                                 len(self.collaboration_client.decision_history),
                'average_confidence': sum(d.confidence for d in self.collaboration_client.decision_history) /
                                     len(self.collaboration_client.decision_history)
            }
            report['collaboration_statistics'] = collaboration_report

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📊 品質レポート生成: {report_file}")

        # サマリー表示
        print("\n" + "="*70)
        print("📈 品質管理サマリー")
        print("="*70)
        print(f"  処理エピソード: {total}")
        print(f"  承認: {approved} ({approved/total*100:.1f}%)")
        print(f"  レビュー必要: {review_required}")
        print(f"  平均スコア: {avg_score:.1f}")

        if 'collaboration_statistics' in report:
            print(f"\n  協議システム統計:")
            print(f"    合意率: {report['collaboration_statistics']['consensus_rate']:.1%}")
            print(f"    平均信頼度: {report['collaboration_statistics']['average_confidence']:.1%}")

        return report_file


async def test_integrated_system():
    """統合システムのテスト"""

    print("="*70)
    print("🎯 統合品質管理システムテスト")
    print("="*70)

    # システム初期化
    system = IntegratedQualitySystem(enable_collaboration=True)
    await system.initialize()

    # テストデータ準備
    test_file = 'episodes_fact_checked_20250923_080224.csv'

    if os.path.exists(test_file):
        # 実データでテスト
        print(f"\n実データでテスト: {test_file}")
        result_df = await system.batch_process_episodes(test_file)

        # 結果保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'episodes_quality_integrated_{timestamp}.csv'

        with open(output_file, 'w', encoding='utf-8-sig') as f:
            result_df.to_csv(f, index=False)

        print(f"\n✅ 処理済みファイル: {output_file}")
    else:
        # テストデータで実行
        print("\nテストデータで実行")
        test_episode = {
            'person_name': 'テスト太郎',
            'episode_age': 30,
            'episode_text': 'これはテストエピソードです。' * 15,
            'person_id': 'P999'
        }

        result = await system.process_episode(test_episode)
        print(f"\n結果: {result['quality_status']}")

    # レポート生成
    report_file = system.generate_quality_report()

    # シャットダウン
    await system.shutdown()

    return report_file


async def main():
    """メイン処理"""
    try:
        report = await test_integrated_system()
        print(f"\n✅ テスト完了")
        if report:
            print(f"   レポート: {report}")
    except KeyboardInterrupt:
        print("\n⚠️ 処理中断")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
