#!/usr/bin/env python3
"""
Feedback Integration System - ユーザーフィードバック統合と自動学習
Phase 5 - Continuous Learning
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from collections import defaultdict
import logging
from enum import Enum
import uuid
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """フィードバックタイプ"""
    QUALITY_RATING = "quality_rating"
    ERROR_REPORT = "error_report"
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"
    IMPROVEMENT_SUGGESTION = "improvement_suggestion"

class FeedbackPriority(Enum):
    """フィードバック優先度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class UserFeedback:
    """ユーザーフィードバック"""
    feedback_id: str
    episode_id: str
    person_name: str
    user_id: str
    feedback_type: FeedbackType
    rating: Optional[int]  # 1-5
    comment: str
    priority: FeedbackPriority
    timestamp: datetime
    processed: bool = False
    action_taken: Optional[str] = None

@dataclass
class FeedbackMetrics:
    """フィードバックメトリクス"""
    total_feedback: int = 0
    by_type: Dict[str, int] = None
    average_rating: float = 0.0
    satisfaction_score: float = 0.0
    response_time: float = 0.0
    improvement_rate: float = 0.0

@dataclass
class LearningOutcome:
    """学習結果"""
    feedback_count: int
    patterns_identified: List[Dict]
    model_updates: Dict[str, Any]
    accuracy_before: float
    accuracy_after: float
    improvement: float
    timestamp: datetime

class FeedbackIntegrationSystem:
    """フィードバック統合システム"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.feedback_storage: List[UserFeedback] = []
        self.feedback_index: Dict[str, UserFeedback] = {}
        self.pattern_detector = PatternDetector()
        self.learning_pipeline = ContinuousLearningPipeline()

        # メトリクス
        self.metrics = FeedbackMetrics(by_type=defaultdict(int))

        # 学習設定
        self.auto_learn_threshold = self.config.get('auto_learn_threshold', 100)
        self.critical_threshold = self.config.get('critical_threshold', 5)
        self.learning_interval = self.config.get('learning_interval', 3600)  # 1時間

    async def submit_feedback(
        self,
        episode_id: str,
        person_name: str,
        user_id: str,
        feedback_type: FeedbackType,
        rating: Optional[int] = None,
        comment: str = "",
        auto_process: bool = True
    ) -> UserFeedback:
        """フィードバック送信"""
        feedback = UserFeedback(
            feedback_id=str(uuid.uuid4()),
            episode_id=episode_id,
            person_name=person_name,
            user_id=user_id,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
            priority=self._determine_priority(feedback_type, rating),
            timestamp=datetime.now()
        )

        # 保存
        self.feedback_storage.append(feedback)
        self.feedback_index[feedback.feedback_id] = feedback

        # メトリクス更新
        self.metrics.total_feedback += 1
        self.metrics.by_type[feedback_type.value] += 1

        if rating:
            self._update_rating_metrics(rating)

        logger.info(f"📝 フィードバック受信: {feedback_type.value} for {person_name}")

        # 自動処理
        if auto_process:
            await self._process_feedback(feedback)

        # 緊急対応チェック
        if feedback.priority == FeedbackPriority.CRITICAL:
            await self._handle_critical_feedback(feedback)

        return feedback

    def _determine_priority(
        self,
        feedback_type: FeedbackType,
        rating: Optional[int]
    ) -> FeedbackPriority:
        """優先度判定"""
        if feedback_type == FeedbackType.ERROR_REPORT:
            return FeedbackPriority.HIGH

        if feedback_type in [FeedbackType.FALSE_POSITIVE, FeedbackType.FALSE_NEGATIVE]:
            return FeedbackPriority.HIGH

        if rating and rating <= 2:
            return FeedbackPriority.HIGH

        if rating and rating >= 4:
            return FeedbackPriority.LOW

        return FeedbackPriority.MEDIUM

    def _update_rating_metrics(self, rating: int):
        """評価メトリクス更新"""
        # 移動平均で更新
        alpha = 0.1
        self.metrics.average_rating = (
            alpha * rating +
            (1 - alpha) * self.metrics.average_rating
        )

        # 満足度スコア（4以上の割合）
        high_ratings = sum(
            1 for f in self.feedback_storage
            if f.rating and f.rating >= 4
        )
        total_ratings = sum(
            1 for f in self.feedback_storage
            if f.rating is not None
        )

        if total_ratings > 0:
            self.metrics.satisfaction_score = high_ratings / total_ratings

    async def _process_feedback(self, feedback: UserFeedback):
        """フィードバック処理"""
        try:
            # パターン検出
            patterns = self.pattern_detector.detect(feedback)

            if patterns:
                logger.info(f"🔍 パターン検出: {len(patterns)}件")

            # 学習パイプラインへ追加
            self.learning_pipeline.add_feedback(feedback)

            # 自動学習チェック
            if self.learning_pipeline.should_trigger_learning():
                await self.trigger_learning()

            feedback.processed = True
            feedback.action_taken = f"Processed with {len(patterns)} patterns"

        except Exception as e:
            logger.error(f"フィードバック処理エラー: {e}")

    async def _handle_critical_feedback(self, feedback: UserFeedback):
        """緊急フィードバック対応"""
        logger.warning(f"🚨 緊急フィードバック: {feedback.feedback_type.value}")

        # アラート送信（実装では外部システムに通知）
        alert = {
            'type': 'critical_feedback',
            'feedback_id': feedback.feedback_id,
            'episode_id': feedback.episode_id,
            'person_name': feedback.person_name,
            'message': feedback.comment,
            'timestamp': feedback.timestamp.isoformat()
        }

        # 即座に学習トリガー
        if feedback.feedback_type in [
            FeedbackType.FALSE_POSITIVE,
            FeedbackType.FALSE_NEGATIVE
        ]:
            await self.trigger_learning(priority=True)

    async def trigger_learning(
        self,
        priority: bool = False
    ) -> LearningOutcome:
        """学習トリガー"""
        logger.info("🧠 学習パイプライン開始")

        # 未処理フィードバック取得
        unprocessed = [
            f for f in self.feedback_storage
            if not f.processed or priority
        ]

        if not unprocessed:
            logger.info("学習対象のフィードバックがありません")
            return None

        # 学習実行
        outcome = await self.learning_pipeline.execute_learning(
            unprocessed,
            priority=priority
        )

        # 処理済みマーク
        for feedback in unprocessed:
            feedback.processed = True

        # メトリクス更新
        if outcome:
            self.metrics.improvement_rate = outcome.improvement

        logger.info(f"✅ 学習完了: 改善率 {outcome.improvement:.2%}")

        return outcome

    def get_feedback_summary(
        self,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """フィードバックサマリー取得"""
        if time_window:
            cutoff = datetime.now() - time_window
            relevant_feedback = [
                f for f in self.feedback_storage
                if f.timestamp > cutoff
            ]
        else:
            relevant_feedback = self.feedback_storage

        if not relevant_feedback:
            return {}

        # タイプ別集計
        by_type = defaultdict(int)
        by_priority = defaultdict(int)
        ratings = []

        for feedback in relevant_feedback:
            by_type[feedback.feedback_type.value] += 1
            by_priority[feedback.priority.value] += 1
            if feedback.rating:
                ratings.append(feedback.rating)

        return {
            'total': len(relevant_feedback),
            'by_type': dict(by_type),
            'by_priority': dict(by_priority),
            'average_rating': np.mean(ratings) if ratings else 0,
            'rating_distribution': {
                i: ratings.count(i) for i in range(1, 6)
            } if ratings else {},
            'processed_rate': sum(1 for f in relevant_feedback if f.processed) / len(relevant_feedback),
            'time_window': str(time_window) if time_window else 'all_time'
        }

    def export_feedback_data(self, output_file: str):
        """フィードバックデータエクスポート"""
        data = [asdict(f) for f in self.feedback_storage]
        df = pd.DataFrame(data)

        # 型変換
        df['feedback_type'] = df['feedback_type'].apply(lambda x: x.value if isinstance(x, FeedbackType) else x)
        df['priority'] = df['priority'].apply(lambda x: x.value if isinstance(x, FeedbackPriority) else x)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"📊 フィードバックデータエクスポート: {output_file}")

class PatternDetector:
    """パターン検出器"""

    def __init__(self):
        self.patterns = []
        self.pattern_counts = defaultdict(int)

    def detect(self, feedback: UserFeedback) -> List[Dict]:
        """パターン検出"""
        detected = []

        # 低評価パターン
        if feedback.rating and feedback.rating <= 2:
            pattern = {
                'type': 'low_rating',
                'person': feedback.person_name,
                'episode': feedback.episode_id
            }
            detected.append(pattern)
            self.pattern_counts['low_rating'] += 1

        # エラーパターン
        if feedback.feedback_type == FeedbackType.ERROR_REPORT:
            pattern = {
                'type': 'error',
                'description': feedback.comment[:100]
            }
            detected.append(pattern)
            self.pattern_counts['error'] += 1

        # 誤判定パターン
        if feedback.feedback_type in [
            FeedbackType.FALSE_POSITIVE,
            FeedbackType.FALSE_NEGATIVE
        ]:
            pattern = {
                'type': 'misclassification',
                'false_type': feedback.feedback_type.value,
                'episode': feedback.episode_id
            }
            detected.append(pattern)
            self.pattern_counts['misclassification'] += 1

        self.patterns.extend(detected)
        return detected

    def get_top_patterns(self, n: int = 10) -> List[Tuple[str, int]]:
        """頻出パターン取得"""
        return sorted(
            self.pattern_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]

class ContinuousLearningPipeline:
    """継続的学習パイプライン"""

    def __init__(self):
        self.feedback_queue = []
        self.learning_history = []
        self.model_versions = {}
        self.current_accuracy = 0.85  # 初期精度

    def add_feedback(self, feedback: UserFeedback):
        """フィードバック追加"""
        self.feedback_queue.append(feedback)

    def should_trigger_learning(self) -> bool:
        """学習トリガー判定"""
        # 未処理フィードバック数
        unprocessed = sum(1 for f in self.feedback_queue if not f.processed)

        # 閾値超過
        if unprocessed >= 100:
            return True

        # 緊急フィードバック
        critical_count = sum(
            1 for f in self.feedback_queue
            if f.priority == FeedbackPriority.CRITICAL and not f.processed
        )

        if critical_count >= 5:
            return True

        return False

    async def execute_learning(
        self,
        feedback_list: List[UserFeedback],
        priority: bool = False
    ) -> LearningOutcome:
        """学習実行"""
        start_accuracy = self.current_accuracy

        # フィードバックから学習データ生成
        training_data = self._prepare_training_data(feedback_list)

        # モデル更新（シミュレーション）
        model_updates = await self._update_model(training_data, priority)

        # 新しい精度（シミュレーション）
        improvement = np.random.uniform(0.01, 0.05)  # 1-5%の改善
        if any(f.feedback_type == FeedbackType.ERROR_REPORT for f in feedback_list):
            improvement *= 0.5  # エラーレポートの場合は改善率が低い

        self.current_accuracy = min(0.99, self.current_accuracy + improvement)

        # パターン分析
        patterns = self._analyze_patterns(feedback_list)

        outcome = LearningOutcome(
            feedback_count=len(feedback_list),
            patterns_identified=patterns,
            model_updates=model_updates,
            accuracy_before=start_accuracy,
            accuracy_after=self.current_accuracy,
            improvement=self.current_accuracy - start_accuracy,
            timestamp=datetime.now()
        )

        self.learning_history.append(outcome)

        # モデルバージョン保存
        version = f"v{len(self.model_versions) + 1}.{datetime.now().strftime('%Y%m%d')}"
        self.model_versions[version] = {
            'accuracy': self.current_accuracy,
            'timestamp': datetime.now(),
            'feedback_count': len(feedback_list)
        }

        return outcome

    def _prepare_training_data(
        self,
        feedback_list: List[UserFeedback]
    ) -> Dict[str, Any]:
        """訓練データ準備"""
        # フィードバックから特徴量抽出
        features = []
        labels = []

        for feedback in feedback_list:
            # 特徴量（簡略化）
            feature = {
                'type': feedback.feedback_type.value,
                'rating': feedback.rating or 3,
                'text_length': len(feedback.comment),
                'priority': feedback.priority.value
            }
            features.append(feature)

            # ラベル（正解データ）
            if feedback.rating:
                labels.append(1 if feedback.rating >= 4 else 0)
            else:
                labels.append(0 if feedback.feedback_type in [
                    FeedbackType.ERROR_REPORT,
                    FeedbackType.FALSE_POSITIVE,
                    FeedbackType.FALSE_NEGATIVE
                ] else 1)

        return {
            'features': features,
            'labels': labels,
            'count': len(features)
        }

    async def _update_model(
        self,
        training_data: Dict[str, Any],
        priority: bool
    ) -> Dict[str, Any]:
        """モデル更新"""
        # 実際の実装では、ここで機械学習モデルを再訓練
        await asyncio.sleep(0.1 if priority else 1.0)  # シミュレート

        return {
            'updated_weights': True,
            'training_samples': training_data['count'],
            'optimization_method': 'gradient_descent' if not priority else 'quick_update',
            'learning_rate': 0.01 if not priority else 0.1
        }

    def _analyze_patterns(
        self,
        feedback_list: List[UserFeedback]
    ) -> List[Dict]:
        """パターン分析"""
        patterns = []

        # タイプ別集計
        type_counts = defaultdict(int)
        for feedback in feedback_list:
            type_counts[feedback.feedback_type.value] += 1

        # 頻出パターン
        for type_name, count in type_counts.items():
            if count >= 3:  # 3件以上で頻出とする
                patterns.append({
                    'pattern': 'frequent_type',
                    'type': type_name,
                    'count': count
                })

        # 特定人物への偏り
        person_counts = defaultdict(int)
        for feedback in feedback_list:
            person_counts[feedback.person_name] += 1

        for person, count in person_counts.items():
            if count >= 5:  # 5件以上で偏りとする
                patterns.append({
                    'pattern': 'person_bias',
                    'person': person,
                    'count': count
                })

        return patterns

async def test_feedback_system():
    """フィードバックシステムのテスト"""
    system = FeedbackIntegrationSystem()

    print("📝 フィードバックシステムテスト")
    print("="*70)

    # テストフィードバック送信
    test_feedback = [
        ("E001", "大谷翔平", "user1", FeedbackType.QUALITY_RATING, 5, "素晴らしいエピソード"),
        ("E002", "イチロー", "user2", FeedbackType.QUALITY_RATING, 4, "良いです"),
        ("E003", "松井秀喜", "user3", FeedbackType.ERROR_REPORT, None, "年齢が間違っています"),
        ("E004", "田中将大", "user4", FeedbackType.FALSE_POSITIVE, None, "削除すべきでない"),
        ("E005", "ダルビッシュ", "user5", FeedbackType.QUALITY_RATING, 2, "情報が不正確"),
    ]

    for episode_id, person, user, f_type, rating, comment in test_feedback:
        feedback = await system.submit_feedback(
            episode_id=episode_id,
            person_name=person,
            user_id=user,
            feedback_type=f_type,
            rating=rating,
            comment=comment
        )
        print(f"  ✅ {person}: {f_type.value} (優先度: {feedback.priority.value})")

    # サマリー表示
    summary = system.get_feedback_summary()

    print("\n📊 フィードバックサマリー:")
    print(f"  総数: {summary['total']}")
    print(f"  平均評価: {summary['average_rating']:.1f}")
    print(f"  処理率: {summary['processed_rate']:.1%}")

    print("\n  タイプ別:")
    for type_name, count in summary['by_type'].items():
        print(f"    {type_name}: {count}")

    print("\n  優先度別:")
    for priority, count in summary['by_priority'].items():
        print(f"    {priority}: {count}")

    # 学習実行
    outcome = await system.trigger_learning()

    if outcome:
        print("\n🧠 学習結果:")
        print(f"  フィードバック数: {outcome.feedback_count}")
        print(f"  精度向上: {outcome.improvement:.2%}")
        print(f"  最終精度: {outcome.accuracy_after:.1%}")

if __name__ == "__main__":
    asyncio.run(test_feedback_system())
