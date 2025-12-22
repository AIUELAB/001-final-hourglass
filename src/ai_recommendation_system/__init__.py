#!/usr/bin/env python3
"""AI推奨システム パッケージ

Phase 11.5 - AI-based Recommendation System

機能:
- 過去の実装結果からの学習
- 動的な最適化パラメータ調整
- リアルタイム推奨生成
- 推奨精度の自動評価
"""

from .models import AIRecommendation, ModelPerformanceMetrics, RecommendationFeedback
from .recommender import AIRecommendationSystem, SKLEARN_AVAILABLE, main

__all__ = [
    # Models
    "AIRecommendation",
    "RecommendationFeedback",
    "ModelPerformanceMetrics",
    # Recommender
    "AIRecommendationSystem",
    "SKLEARN_AVAILABLE",
    "main",
]
