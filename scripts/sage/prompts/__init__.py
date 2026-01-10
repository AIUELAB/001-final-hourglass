"""
SAGE Prompts Package - Phase 7D

カテゴリ別プロンプト最適化と人物特性分析。
"""

from .category_prompts import (
    AGE_GUIDANCE,
    CATEGORY_PROMPTS,
    CategoryPromptManager,
    PromptTemplate,
    get_age_guidance,
)
from .persona_analyzer import (
    PersonaAnalyzer,
    PersonaProfile,
)

__all__ = [
    "AGE_GUIDANCE",
    "CATEGORY_PROMPTS",
    "CategoryPromptManager",
    "PromptTemplate",
    "PersonaAnalyzer",
    "PersonaProfile",
    "get_age_guidance",
]
