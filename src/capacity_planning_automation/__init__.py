#!/usr/bin/env python3
"""容量計画自動化システム パッケージ

Phase 11.3 - Capacity Planning Automation System

機能:
- リソース使用量予測（CPU、メモリ、ディスク）
- 将来の容量需要予測
- スケーリング推奨事項の生成
- 容量不足アラートの自動生成
- 最適な容量計画の提案
- 成長トレンド分析
"""

from .models import CapacityForecast, CapacityPlan, ResourceMetrics, ScalingRecommendation
from .planner import SKLEARN_AVAILABLE, CapacityPlanningAutomation, main

__all__ = [
    # Models
    "ResourceMetrics",
    "CapacityForecast",
    "ScalingRecommendation",
    "CapacityPlan",
    # Planner
    "CapacityPlanningAutomation",
    "SKLEARN_AVAILABLE",
    "main",
]
