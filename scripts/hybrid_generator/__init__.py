"""
Hybrid Episode Generation System

EPGEN と既存 Final Hourglass 生成システムを統合したハイブリッド生成システム。
"""

__version__ = "1.0.0"

from .config import (
    DIVERSITY_TARGETS,
    FABRICATION_SIGNALS,
    GENERATION_RULES,
    QUALITY_THRESHOLDS,
    REQUIRED_EVIDENCE,
    HybridConfig,
)

__all__ = [
    "GENERATION_RULES",
    "QUALITY_THRESHOLDS",
    "DIVERSITY_TARGETS",
    "FABRICATION_SIGNALS",
    "REQUIRED_EVIDENCE",
    "HybridConfig",
]
