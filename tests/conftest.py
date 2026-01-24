"""
pytest configuration file.

This file is automatically loaded by pytest before running tests.
It adds the src/ directory to the Python path so that tests can import modules.
"""

import sys
from pathlib import Path

# Add src/ to Python path for test imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Also add project root for imports like 'from src.xxx import yyy'
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add scripts/ and scripts/generate for mass_production imports
scripts_path = project_root / "scripts"
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))

generate_path = project_root / "scripts" / "generate"
if str(generate_path) not in sys.path:
    sys.path.insert(0, str(generate_path))


# ============================================
# Test Fixtures
# ============================================

import pandas as pd
import pytest


@pytest.fixture
def mock_deletion_df():
    """CI環境用モックデータ（世界的偉人の削除防止テスト用）

    PROTECTED_PERSONS（13名）全員を含む完全なモックデータ。
    """
    protected_persons = [
        "アルベルト・アインシュタイン",
        "マリー・キュリー",
        "スティーブ・ジョブズ",
        "イーロン・マスク",
        "ジェフ・ベゾス",
        "ビル・ゲイツ",
        "マーク・ザッカーバーグ",
        "レオナルド・ダ・ヴィンチ",
        "アイザック・ニュートン",
        "ガリレオ・ガリレイ",
        "マーティン・ルーサー・キング・ジュニア",
        "ネルソン・マンデラ",
        "マハトマ・ガンジー",
    ]
    return pd.DataFrame(
        {
            "人物名": protected_persons + ["テスト削除対象"],
            "ステータス": ["保持"] * len(protected_persons) + ["削除済み"],
            "削除理由": [""] * len(protected_persons) + ["架空キャラクター"],
        }
    )
