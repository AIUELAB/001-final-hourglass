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


# ============================================
# Phase 3: Master CSV Mock Fixtures
# ============================================


@pytest.fixture
def mock_master_episodes_df():
    """CI環境用マスターCSVモックデータ

    MASTER_EPISODES_CURRENT.csvと同じカラム構造を持つ
    テスト用サンプルデータ。
    """
    return pd.DataFrame(
        {
            # PRレビュー#14: エッジケースデータを追加（NaN, Inf, 空文字, 10000文字テキスト）
            "episode_id": ["EP-001", "EP-002", "EP-003", "EP-004", "EP-005", "EP-EDGE-NAN", "EP-EDGE-LONG"],
            "person_id": ["P001", "P002", "P003", "P004", "P005", "P-EDGE-1", "P-EDGE-2"],
            "person_name": [
                "織田信長",
                "豊臣秀吉",
                "徳川家康",
                "スティーブ・ジョブズ",
                "ナウシカ",
                "テスト用NaN人物",
                "テスト用長文人物",
            ],
            "episode_count": [10, 8, 12, 5, 3, 1, 2],
            "age": [30, 45, 50, 25, 16, 20, 35],
            "category": [
                "政治・リーダーシップ",
                "政治・リーダーシップ",
                "政治・リーダーシップ",
                "ビジネス・経営",
                "冒険・探検",
                "テスト",  # EP-EDGE-NAN
                "テスト",  # EP-EDGE-LONG
            ],
            "episode_text": [
                "あなたと同じ30歳のとき、織田信長は桶狭間の戦いで今川義元を破った。",
                "あなたと同じ45歳のとき、豊臣秀吉は天下統一を達成した。",
                "あなたと同じ50歳のとき、徳川家康は関ヶ原の戦いで勝利した。",
                "あなたと同じ25歳のとき、スティーブ・ジョブズはAppleを創業した。",
                "あなたと同じ16歳のとき、ナウシカは腐海を探索し始めた。",
                "",  # EP-EDGE-NAN: 空文字テスト
                "あ" * 10000,  # EP-EDGE-LONG: 極長テキストテスト
            ],
            "episode_type": ["達成", "達成", "達成", "挑戦", "冒険", "テスト", "テスト"],
            "group_name": ["", "", "", "", "", "", ""],
            "is_group_member": [False, False, False, False, False, False, False],
            "person_type": ["REAL", "REAL", "REAL", "REAL", "FICTIONAL", "REAL", "REAL"],
            "source": ["WIKIPEDIA", "WIKIPEDIA", "WIKIPEDIA", "WIKIPEDIA", "FICTIONAL", "TEST", "TEST"],
            "work_title": ["", "", "", "", "風の谷のナウシカ", "", ""],
            "generation_timestamp": [
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
            ],
            "fame_tier": [5, 5, 5, 4, 3, 1, 1],
            "composite_score": [950.0, 920.0, 980.0, 850.0, 700.0, float("nan"), float("inf")],  # NaN/Infテスト
            "episode_importance_score": [9.5, 9.0, 9.8, 8.5, 7.0, 1.0, 1.0],
            "impressiveness_score": [9.0, 8.5, 9.5, 8.0, 7.5, 1.0, 1.0],
            "generated_at": [
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
            ],
            "verification_status": ["verified", "verified", "verified", "verified", "unverified", "test", "test"],
            "evidence_quality": ["high", "high", "high", "high", "fictional", "test", "test"],
            "総合品質": [9.5, 9.0, 9.8, 8.5, 7.0, 1.0, 1.0],
            "感情インパクト": [9.0, 8.5, 9.5, 8.0, 8.0, 1.0, 1.0],
            "composite_score_5axis": [9.2, 8.8, 9.5, 8.2, 7.5, 1.0, 1.0],
            "memorability_score": [9.5, 9.0, 9.8, 8.5, 8.0, 1.0, 1.0],
            "empathy_score": [8.0, 8.5, 8.0, 9.0, 9.0, 1.0, 1.0],
            "surprise_score": [9.0, 8.0, 9.5, 8.5, 7.5, 1.0, 1.0],
            "generation_quality_score": [9.0, 8.5, 9.5, 8.0, 7.0, 1.0, 1.0],
            "educational_value": [9.5, 9.0, 9.5, 8.5, 6.5, 1.0, 1.0],
            "storytelling_quality": [9.0, 8.5, 9.0, 8.0, 8.5, 1.0, 1.0],
            "factual_density": [9.0, 8.5, 9.0, 8.0, 5.0, 1.0, 1.0],
            "llm_evaluated_at": [
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
            ],
            "wikipedia_pv": [1000000, 800000, 1200000, 500000, 0, 0, 0],
            "fame_score_v3": [950.0, 900.0, 980.0, 700.0, 500.0, float("nan"), 100.0],  # NaNテスト
            "fame_rank_v3": [1, 2, 3, 100, 500, 9999, 9998],
            "multi_lang_pv": [5000000, 4000000, 6000000, 3000000, 100000, 0, 0],
            "sitelinks_count": [200, 180, 220, 150, 50, 0, 0],
            "google_hits": [50000000, 40000000, 60000000, 30000000, 5000000, 0, 0],
            "is_japanese": [True, True, True, False, False, True, True],
            "celebrity_score_v2": [980.0, 950.0, 990.0, 850.0, 600.0, 1.0, 1.0],
            "celebrity_rank_v2": [1, 2, 3, 50, 200, 9999, 9998],
            "episode_fame_v6": [95.0, 90.0, 98.0, 80.0, 70.0, 1.0, 1.0],
            "episode_fame_tier_v6": [5, 5, 5, 4, 3, 1, 1],
            "episode_fame_v6_updated_at": [
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
            ],
            "super_total_score": [1000000.0, 900000.0, 1100000.0, 700000.0, 500000.0, 1.0, 1.0],
            "iconic_score": [9.5, 9.0, 9.8, 8.0, 6.0, 1.0, 1.0],
            "model": ["gpt-4", "gpt-4", "gpt-4", "gpt-4", "gpt-4", "test", "test"],
            "generator_type": ["standard", "standard", "standard", "standard", "fictional", "test", "test"],
            "cost_usd": [0.01, 0.01, 0.01, 0.01, 0.01, 0.0, 0.0],
            "story_quality": [9.0, 8.5, 9.5, 8.0, 8.0, 1.0, 1.0],
            "episode_fame_score": [95.0, 90.0, 98.0, 80.0, 70.0, 1.0, 1.0],
            "birth_year": [1534, 1537, 1543, 1955, None, None, None],
            "death_year": [1582, 1598, 1616, 2011, None, None, None],
            "is_fictional": [False, False, False, False, True, False, False],
        }
    )


@pytest.fixture
def mock_csv_path(tmp_path, mock_master_episodes_df):
    """一時的なCSVファイルを作成してパスを返すフィクスチャ"""
    csv_path = tmp_path / "MASTER_EPISODES_CURRENT.csv"
    mock_master_episodes_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return csv_path


@pytest.fixture
def mock_fact_checker():
    """ファクトチェッカーAPIのモック

    外部API呼び出しを回避するためのモック。
    """
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.check_fact.return_value = {
        "is_verified": True,
        "confidence": 0.95,
        "sources": ["Wikipedia", "公式記録"],
        "evidence": "歴史的事実として確認済み",
    }
    mock.batch_check.return_value = [
        {"episode_id": "EP-001", "is_verified": True, "confidence": 0.95},
        {"episode_id": "EP-002", "is_verified": True, "confidence": 0.90},
    ]
    return mock


@pytest.fixture
def mock_external_api():
    """外部API（Wikipedia、Google等）のモック"""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.get_wikipedia_pv.return_value = 1000000
    mock.get_google_hits.return_value = 50000000
    mock.get_wikidata_info.return_value = {
        "sitelinks_count": 200,
        "multi_lang_pv": 5000000,
    }
    return mock
