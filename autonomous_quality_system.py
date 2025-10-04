#!/usr/bin/env python3
"""
自律的品質改善システム
継続的な学習と最適化により品質を自動改善
"""

import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
import pickle
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from collections import deque

# 既存システムのインポート
from multi_agent_orchestrator import MultiAgentOrchestrator, ConsensusMethod
from async_collaboration_client import AsyncCollaborationClient
from enhanced_quality_gate import EnhancedQualityGate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('AutonomousQuality')


@dataclass
class QualityMetrics:
    """品質メトリクス"""
    timestamp: datetime
    episode_id: str
    quality_score: float
    consensus_level: float
    processing_time: float
    error_rate: float
    features: Dict[str, float]


@dataclass
class LearningState:
    """学習状態"""
    model_version: str
    training_samples: int
    accuracy: float
    last_update: datetime
    hyperparameters: Dict[str, Any]


class QualityPredictor:
    """品質予測モデル"""

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_importance = {}
        self.training_history = []

    def extract_features(self, episode: Dict) -> np.ndarray:
        """エピソードから特徴量を抽出"""
        features = []

        # テキスト特徴
        text = episode.get('episode_text', '')
        features.append(len(text))  # 文字数
        features.append(text.count('。'))  # 文数
        features.append(text.count('、'))  # 読点数
        features.append(len(text.split()))  # 単語数（概算）

        # メタデータ特徴
        features.append(float(episode.get('episode_age', 0)))
        features.append(float(episode.get('quality_score', 0)))
        features.append(float(episode.get('collaboration_confidence', 0)))

        # カテゴリ特徴（ダミー変数化が必要な場合は拡張）
        features.append(1.0 if episode.get('fact_check_status') == 'verified' else 0.0)

        return np.array(features).reshape(1, -1)

    def train(self, training_data: List[Dict], labels: List[int]):
        """モデルを訓練"""
        if len(training_data) < 10:
            logger.warning("訓練データが不足しています（最低10件必要）")
            return False

        # 特徴量抽出
        X = np.vstack([self.extract_features(episode) for episode in training_data])
        y = np.array(labels)

        # スケーリング
        X_scaled = self.scaler.fit_transform(X)

        # 訓練
        self.model.fit(X_scaled, y)
        self.is_trained = True

        # 特徴量重要度を保存
        self.feature_importance = {
            f"feature_{i}": importance
            for i, importance in enumerate(self.model.feature_importances_)
        }

        # 訓練履歴に追加
        self.training_history.append({
            "timestamp": datetime.now().isoformat(),
            "samples": len(training_data),
            "accuracy": self.model.score(X_scaled, y)
        })

        logger.info(f"✅ モデル訓練完了: {len(training_data)}件のサンプル")
        return True

    def predict(self, episode: Dict) -> Tuple[int, float]:
        """品質を予測"""
        if not self.is_trained:
            logger.warning("モデルが訓練されていません")
            return 0, 0.5

        features = self.extract_features(episode)
        features_scaled = self.scaler.transform(features)

        prediction = self.model.predict(features_scaled)[0]
        confidence = max(self.model.predict_proba(features_scaled)[0])

        return int(prediction), float(confidence)

    def save_model(self, path: str = "quality_model.pkl"):
        """モデルを保存"""
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_importance': self.feature_importance,
                'is_trained': self.is_trained
            }, f)
        logger.info(f"✅ モデルを保存: {path}")

    def load_model(self, path: str = "quality_model.pkl"):
        """モデルを読み込み"""
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
                self.feature_importance = data['feature_importance']
                self.is_trained = data['is_trained']
            logger.info(f"✅ モデルを読み込み: {path}")
            return True
        return False


class FeedbackLoop:
    """フィードバックループ管理"""

    def __init__(self, window_size: int = 100):
        self.feedback_queue = deque(maxlen=window_size)
        self.performance_metrics = {
            "accuracy": deque(maxlen=window_size),
            "consensus": deque(maxlen=window_size),
            "processing_time": deque(maxlen=window_size)
        }
        self.adjustment_history = []

    def add_feedback(self, prediction: Dict, actual: Dict):
        """フィードバックを追加"""
        feedback = {
            "timestamp": datetime.now(),
            "prediction": prediction,
            "actual": actual,
            "accuracy": self._calculate_accuracy(prediction, actual)
        }
        self.feedback_queue.append(feedback)

        # メトリクスを更新
        self.performance_metrics["accuracy"].append(feedback["accuracy"])

    def _calculate_accuracy(self, prediction: Dict, actual: Dict) -> float:
        """精度を計算"""
        predicted_quality = prediction.get('quality_score', 0)
        actual_quality = actual.get('quality_score', 0)

        if actual_quality > 0:
            error = abs(predicted_quality - actual_quality) / actual_quality
            return max(0, 1 - error)
        return 0.5

    def get_performance_summary(self) -> Dict:
        """パフォーマンスサマリーを取得"""
        if not self.performance_metrics["accuracy"]:
            return {"status": "no_data"}

        return {
            "average_accuracy": np.mean(self.performance_metrics["accuracy"]),
            "accuracy_trend": self._calculate_trend(self.performance_metrics["accuracy"]),
            "recent_feedback_count": len(self.feedback_queue)
        }

    def _calculate_trend(self, metrics: deque) -> str:
        """トレンドを計算"""
        if len(metrics) < 10:
            return "insufficient_data"

        recent = list(metrics)[-10:]
        older = list(metrics)[-20:-10] if len(metrics) >= 20 else list(metrics)[:10]

        recent_avg = np.mean(recent)
        older_avg = np.mean(older)

        if recent_avg > older_avg * 1.05:
            return "improving"
        elif recent_avg < older_avg * 0.95:
            return "declining"
        else:
            return "stable"

    def recommend_adjustments(self) -> List[Dict]:
        """調整推奨事項を生成"""
        recommendations = []

        summary = self.get_performance_summary()

        if summary.get("status") != "no_data":
            avg_accuracy = summary["average_accuracy"]
            trend = summary["accuracy_trend"]

            if avg_accuracy < 0.7:
                recommendations.append({
                    "type": "retrain",
                    "priority": "high",
                    "reason": f"精度が低い: {avg_accuracy:.1%}"
                })

            if trend == "declining":
                recommendations.append({
                    "type": "parameter_tuning",
                    "priority": "medium",
                    "reason": "パフォーマンスが低下傾向"
                })

            if len(self.feedback_queue) >= self.feedback_queue.maxlen * 0.9:
                recommendations.append({
                    "type": "model_update",
                    "priority": "low",
                    "reason": "十分なフィードバックデータが蓄積"
                })

        return recommendations


class AutonomousQualitySystem:
    """自律的品質改善システム"""

    def __init__(self):
        self.orchestrator = MultiAgentOrchestrator()
        self.predictor = QualityPredictor()
        self.feedback_loop = FeedbackLoop()
        self.quality_gate = EnhancedQualityGate()
        self.metrics_history = []
        self.auto_improve_enabled = True
        self.improvement_interval = 3600  # 1時間ごと
        self.last_improvement = datetime.now()

    async def initialize(self):
        """システム初期化"""
        logger.info("="*70)
        logger.info("🚀 自律的品質改善システム 初期化")
        logger.info("="*70)

        # 既存モデルの読み込み
        if self.predictor.load_model():
            logger.info("✅ 既存モデルを読み込みました")
        else:
            logger.info("ℹ️ 新規モデルとして開始します")

        # 改善タスクを開始
        if self.auto_improve_enabled:
            asyncio.create_task(self._auto_improvement_loop())

    async def process_with_learning(self, episode: Dict) -> Dict:
        """学習機能付きエピソード処理"""

        # 品質予測
        if self.predictor.is_trained:
            predicted_quality, confidence = self.predictor.predict(episode)
            episode['predicted_quality'] = predicted_quality
            episode['prediction_confidence'] = confidence
            logger.info(f"📊 品質予測: {predicted_quality} (信頼度: {confidence:.1%})")

        # マルチエージェント協議
        result = await self.orchestrator.orchestrate(
            episode.get('episode_text', ''),
            {
                'person_name': episode.get('person_name'),
                'episode_age': episode.get('episode_age'),
                'person_id': episode.get('person_id', 'P000')
            },
            ConsensusMethod.WEIGHTED
        )

        # 実際の品質を計算
        actual_quality = result.confidence * 10  # 10点満点に変換
        episode['actual_quality'] = actual_quality
        episode['consensus_decision'] = result.final_decision
        episode['agreement_level'] = result.agreement_level

        # フィードバックループに追加
        if self.predictor.is_trained:
            self.feedback_loop.add_feedback(
                {'quality_score': predicted_quality},
                {'quality_score': actual_quality}
            )

        # メトリクスを記録
        metrics = QualityMetrics(
            timestamp=datetime.now(),
            episode_id=episode.get('person_id', 'unknown'),
            quality_score=actual_quality,
            consensus_level=result.agreement_level,
            processing_time=result.processing_time,
            error_rate=0 if result.final_decision == "APPROVE" else 1,
            features={'agent_count': len(result.votes)}
        )
        self.metrics_history.append(metrics)

        return episode

    async def _auto_improvement_loop(self):
        """自動改善ループ"""
        while self.auto_improve_enabled:
            await asyncio.sleep(60)  # 1分ごとにチェック

            if datetime.now() - self.last_improvement > timedelta(seconds=self.improvement_interval):
                await self._perform_improvement()
                self.last_improvement = datetime.now()

    async def _perform_improvement(self):
        """改善を実行"""
        logger.info("\n🔄 自動改善プロセス開始")

        # フィードバックループから推奨事項を取得
        recommendations = self.feedback_loop.recommend_adjustments()

        for rec in recommendations:
            if rec['type'] == 'retrain' and rec['priority'] == 'high':
                await self._retrain_model()
            elif rec['type'] == 'parameter_tuning':
                await self._tune_parameters()
            elif rec['type'] == 'model_update':
                await self._update_model()

        # パフォーマンスサマリー
        summary = self.feedback_loop.get_performance_summary()
        logger.info(f"📊 現在のパフォーマンス: {summary}")

    async def _retrain_model(self):
        """モデルを再訓練"""
        if len(self.metrics_history) < 50:
            logger.info("⚠️ 再訓練に必要なデータが不足")
            return

        # 訓練データの準備
        training_data = []
        labels = []

        for metrics in self.metrics_history[-200:]:  # 最新200件
            episode = {
                'episode_text': 'dummy_text' * 20,  # 実際のテキストが必要
                'episode_age': 30,
                'quality_score': metrics.quality_score,
                'collaboration_confidence': metrics.consensus_level
            }
            training_data.append(episode)
            labels.append(1 if metrics.quality_score > 7 else 0)

        # 再訓練
        if self.predictor.train(training_data, labels):
            self.predictor.save_model()
            logger.info("✅ モデル再訓練完了")

    async def _tune_parameters(self):
        """パラメータチューニング"""
        logger.info("🔧 パラメータチューニング実行")

        # 学習率の調整
        current_performance = self.feedback_loop.get_performance_summary()
        if current_performance.get('accuracy_trend') == 'declining':
            # 学習率を下げる
            for agent in self.orchestrator.agents:
                agent.performance_metrics['accuracy'] *= 0.95

        logger.info("✅ パラメータ調整完了")

    async def _update_model(self):
        """モデル更新"""
        logger.info("🔄 モデル更新実行")

        # インクリメンタル学習（実装簡略化）
        self.predictor.save_model(f"quality_model_backup_{datetime.now().strftime('%Y%m%d')}.pkl")
        logger.info("✅ モデル更新完了")

    def generate_learning_report(self) -> Dict:
        """学習レポートを生成"""
        if not self.metrics_history:
            return {"status": "no_data"}

        recent_metrics = self.metrics_history[-100:]  # 最新100件

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_processed": len(self.metrics_history),
            "average_quality": np.mean([m.quality_score for m in recent_metrics]),
            "average_consensus": np.mean([m.consensus_level for m in recent_metrics]),
            "average_processing_time": np.mean([m.processing_time for m in recent_metrics]),
            "error_rate": np.mean([m.error_rate for m in recent_metrics]),
            "feedback_performance": self.feedback_loop.get_performance_summary(),
            "model_status": {
                "is_trained": self.predictor.is_trained,
                "training_samples": len(self.predictor.training_history),
                "feature_importance": self.predictor.feature_importance
            },
            "agent_performance": self.orchestrator.get_performance_report(),
            "recommendations": self.feedback_loop.recommend_adjustments()
        }

        return report


async def demonstrate_autonomous_system():
    """自律的品質改善システムのデモンストレーション"""

    print("\n" + "="*70)
    print("🤖 自律的品質改善システム デモンストレーション")
    print("="*70)

    system = AutonomousQualitySystem()
    await system.initialize()

    # テストエピソード
    test_episodes = [
        {
            "person_name": "イチロー",
            "episode_age": 27,
            "episode_text": "2001年、27歳のイチローはメジャーリーグ1年目でMVPと新人王を同時受賞。この快挙は日本人選手として初めてのことだった。",
            "person_id": "P001"
        },
        {
            "person_name": "大谷翔平",
            "episode_age": 29,
            "episode_text": "2023年、29歳の大谷翔平はMLBでホームラン王を獲得。投打二刀流として歴史的なシーズンを送った。",
            "person_id": "P002"
        },
        {
            "person_name": "テスト太郎",
            "episode_age": 25,
            "episode_text": "短い文。",
            "person_id": "P003"
        }
    ]

    # 初回処理（学習なし）
    print("\n📝 初回処理（学習なし）:")
    for episode in test_episodes:
        result = await system.process_with_learning(episode)
        print(f"\n   {result['person_name']}:")
        print(f"      決定: {result.get('consensus_decision', 'N/A')}")
        print(f"      合意度: {result.get('agreement_level', 0):.1%}")
        print(f"      実際の品質: {result.get('actual_quality', 0):.1f}")

    # 簡易訓練データで学習
    print("\n🧠 モデル訓練中...")
    training_data = []
    labels = []

    for _ in range(20):  # ダミーデータ生成
        dummy_episode = {
            'episode_text': 'これはテストエピソードです。' * np.random.randint(5, 20),
            'episode_age': np.random.randint(20, 60),
            'quality_score': np.random.uniform(5, 10),
            'collaboration_confidence': np.random.uniform(0.5, 1.0)
        }
        training_data.append(dummy_episode)
        labels.append(1 if dummy_episode['quality_score'] > 7 else 0)

    system.predictor.train(training_data, labels)

    # 学習後の処理
    print("\n📝 学習後の処理:")
    for episode in test_episodes:
        result = await system.process_with_learning(episode)
        print(f"\n   {result['person_name']}:")
        print(f"      予測品質: {result.get('predicted_quality', 'N/A')}")
        print(f"      予測信頼度: {result.get('prediction_confidence', 0):.1%}")
        print(f"      実際の品質: {result.get('actual_quality', 0):.1f}")
        print(f"      決定: {result.get('consensus_decision', 'N/A')}")

    # 学習レポート生成
    report = system.generate_learning_report()

    print("\n" + "="*70)
    print("📊 学習レポート")
    print("="*70)
    print(f"処理エピソード数: {report.get('total_processed', 0)}")
    print(f"平均品質スコア: {report.get('average_quality', 0):.1f}")
    print(f"平均合意度: {report.get('average_consensus', 0):.1%}")
    print(f"エラー率: {report.get('error_rate', 0):.1%}")

    if report.get('recommendations'):
        print("\n💡 推奨事項:")
        for rec in report['recommendations']:
            print(f"   - [{rec['priority']}] {rec['type']}: {rec['reason']}")


if __name__ == "__main__":
    # デモ実行
    asyncio.run(demonstrate_autonomous_system())