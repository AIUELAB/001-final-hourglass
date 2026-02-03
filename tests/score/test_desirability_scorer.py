"""
desirability_scorer ユニットテスト

テスト対象:
- scripts/score/desirability/event_magnitude.py
- scripts/score/desirability/config.py

テストカテゴリ:
1. event_magnitude計算テスト（Tier検出、複数キーワードボーナス）
2. who_factor計算テスト（スーパースターブースト）
3. when_factor計算テスト（recency_boost）
4. 統合テスト（大谷翔平 vs 竹内結子）
"""

import math
import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))

from scripts.score.desirability import (
    DESIRABILITY_WEIGHTS,
    RECENCY_BOOST,
    SUPERSTARS,
    TIER_A_KEYWORDS,
    TIER_B_KEYWORDS,
    TIER_C_KEYWORDS,
    TIER_MAGNITUDE,
    TIER_S_KEYWORDS,
    calculate_event_magnitude,
    normalize_magnitude,
)


# ============================================================
# ヘルパー関数（scorer.py が存在しない場合のスタブ実装）
# ============================================================


def calculate_who_factor(
    celebrity_score_v2: float,
    multi_lang_pv: int,
    person_name: str,
    superstar_boost: float = 1.15,
) -> float:
    """
    人物の知名度に基づくwho_factorを計算

    Args:
        celebrity_score_v2: 人物の知名度スコア (0-1000程度)
        multi_lang_pv: 多言語ページビュー数
        person_name: 人物名
        superstar_boost: スーパースター人物へのブースト倍率

    Returns:
        who_factor (0.0-1.0)
    """
    # celebrity_scoreを正規化 (最大値を1000と仮定)
    normalized_celebrity = min(1.0, celebrity_score_v2 / 1000.0)

    # multi_lang_pvを正規化 (対数スケール、最大1000万PV)
    if multi_lang_pv > 0:
        normalized_pv = min(1.0, math.log10(multi_lang_pv + 1) / 7.0)  # log10(10M) ≈ 7
    else:
        normalized_pv = 0.0

    # 基本who_factor（celebrity_scoreとPVの加重平均）
    who_factor = normalized_celebrity * 0.7 + normalized_pv * 0.3

    # スーパースターブースト
    if any(star in person_name for star in SUPERSTARS):
        who_factor = min(1.0, who_factor * superstar_boost)

    return who_factor


def calculate_when_factor(
    event_year: int,
    current_year: int = 2026,
) -> float:
    """
    イベント発生年に基づくwhen_factorを計算

    Args:
        event_year: イベント発生年
        current_year: 現在の年（デフォルト2026）

    Returns:
        when_factor (0.0-1.0)
    """
    if event_year >= 2020:
        boost = RECENCY_BOOST["2020s"]
    elif event_year >= 2010:
        boost = RECENCY_BOOST["2010s"]
    elif event_year >= 2000:
        boost = RECENCY_BOOST["2000s"]
    elif event_year >= 1990:
        boost = RECENCY_BOOST["1990s"]
    else:
        boost = RECENCY_BOOST["older"]

    # 基本のwhen_factor（新しいほど高い）
    years_ago = current_year - event_year
    base_factor = max(0.3, 1.0 - (years_ago * 0.01))  # 年あたり1%減衰、下限0.3

    return min(1.0, base_factor * boost)


def calculate_desirability_score(episode_data: dict) -> dict:
    """
    エピソードデータからdesirabilityスコアを計算

    Args:
        episode_data: エピソードデータ辞書
            - person_name: 人物名
            - celebrity_score_v2: 知名度スコア
            - multi_lang_pv: 多言語PV
            - episode_text: エピソードテキスト
            - episode_importance_score: 重要度スコア
            - episode_fame_v6: v6スコア
            - age: 年齢
            - birth_year: 生年

    Returns:
        計算結果辞書
    """
    # event_magnitude計算
    episode_text = episode_data.get("episode_text", "")
    magnitude, tier, keywords = calculate_event_magnitude(episode_text)
    normalized_mag = normalize_magnitude(magnitude)

    # who_factor計算
    who_factor = calculate_who_factor(
        celebrity_score_v2=episode_data.get("celebrity_score_v2", 0),
        multi_lang_pv=episode_data.get("multi_lang_pv", 0),
        person_name=episode_data.get("person_name", ""),
    )

    # when_factor計算
    birth_year = episode_data.get("birth_year", 1990)
    age = episode_data.get("age", 30)
    event_year = birth_year + age
    when_factor = calculate_when_factor(event_year)

    # 重み付き合計スコア
    weights = DESIRABILITY_WEIGHTS
    desirability_score = (
        normalized_mag * weights["event_magnitude"]
        + who_factor * weights["person_fame"]
        + when_factor * weights["recency"]
        + 0.5 * weights["diversity"]  # 多様性は固定0.5（単体計算時）
    ) * 100  # 0-100スケール

    return {
        "desirability_score": desirability_score,
        "event_magnitude": magnitude,
        "event_magnitude_normalized": normalized_mag,
        "event_tier": tier,
        "matched_keywords": keywords,
        "who_factor": who_factor,
        "when_factor": when_factor,
        "event_year": event_year,
    }


# ============================================================
# 1. event_magnitude計算テスト
# ============================================================


class TestEventMagnitude:
    """event_magnitude計算のテスト"""

    def test_tier_s_detection_nobel_physics(self):
        """Tier Sキーワード（ノーベル物理学賞）の検出"""
        text = "ノーベル物理学賞を受賞した"
        magnitude, tier, keywords = calculate_event_magnitude(text)

        assert tier == "S"
        assert magnitude == TIER_MAGNITUDE["S"]  # 50
        assert "ノーベル物理学賞" in keywords

    def test_tier_s_detection_nobel_general(self):
        """Tier Sキーワード（ノーベル賞一般）の検出"""
        text = "ノーベル賞の栄誉に輝いた"
        magnitude, tier, keywords = calculate_event_magnitude(text)

        assert tier == "S"
        assert magnitude == 50
        assert "ノーベル賞" in keywords

    def test_tier_s_detection_world_first(self):
        """Tier Sキーワード（世界初）の検出"""
        text = "世界初の快挙を成し遂げた"
        result = calculate_event_magnitude(text)
        tier = result[1]
        keywords = result[2]

        assert tier == "S"
        assert "世界初" in keywords

    def test_tier_s_detection_historic_first(self):
        """Tier Sキーワード（史上初）の検出"""
        text = "史上初の二刀流選手として活躍"
        result = calculate_event_magnitude(text)
        tier = result[1]
        keywords = result[2]

        assert tier == "S"
        assert "史上初" in keywords

    def test_tier_a_detection_mvp(self):
        """Tier Aキーワードではないがmvpの検出（Tier Bにある）"""
        text = "MVPを獲得した"
        magnitude, tier, keywords = calculate_event_magnitude(text)

        # MVPはTier Bに分類されている
        assert tier == "B"
        assert "MVP" in keywords
        assert magnitude == TIER_MAGNITUDE["B"]  # 30

    def test_tier_a_detection_academy_award(self):
        """Tier Aキーワード（アカデミー賞）の検出"""
        text = "アカデミー賞で栄誉を得た"  # 「受賞」を避けて単一キーワードに
        magnitude, tier, keywords = calculate_event_magnitude(text)

        assert tier == "A"
        assert magnitude == TIER_MAGNITUDE["A"]  # 40
        assert "アカデミー賞" in keywords

    def test_tier_a_detection_olympic_gold(self):
        """Tier Aキーワード（オリンピック金メダル）の検出"""
        text = "オリンピック金メダルを獲得した"
        result = calculate_event_magnitude(text)
        tier = result[1]
        keywords = result[2]

        assert tier == "A"
        assert "オリンピック金メダル" in keywords

    def test_tier_a_detection_grammy(self):
        """Tier Aキーワード（グラミー賞）の検出"""
        text = "グラミー賞を受賞した"
        result = calculate_event_magnitude(text)
        tier = result[1]
        keywords = result[2]

        assert tier == "A"
        assert "グラミー賞" in keywords

    def test_tier_b_detection_domestic_first(self):
        """Tier Bキーワード（日本初）の検出"""
        text = "日本初の快挙を果たした"  # 「達成」を避けて単一キーワードに
        magnitude, tier, keywords = calculate_event_magnitude(text)

        assert tier == "B"
        assert magnitude == TIER_MAGNITUDE["B"]  # 30
        assert "日本初" in keywords

    def test_tier_b_detection_championship(self):
        """Tier Bキーワード（優勝）の検出"""
        text = "リーグ優勝を果たした"
        result = calculate_event_magnitude(text)
        tier = result[1]
        keywords = result[2]

        assert tier == "B"
        assert "優勝" in keywords

    def test_tier_c_detection_debut(self):
        """Tier Cキーワード（デビュー）の検出"""
        text = "歌手としてデビューした"
        magnitude, tier, keywords = calculate_event_magnitude(text)

        assert tier == "C"
        assert magnitude == TIER_MAGNITUDE["C"]  # 20
        assert "デビュー" in keywords

    def test_tier_c_detection_release(self):
        """Tier Cキーワード（リリース）の検出"""
        text = "新アルバムをリリースした"
        result = calculate_event_magnitude(text)
        tier = result[1]
        keywords = result[2]

        assert tier == "C"
        assert "リリース" in keywords

    def test_default_tier_no_keywords(self):
        """キーワードなしの場合はDEFAULT"""
        text = "平凡な一日を過ごした"
        magnitude, tier, keywords = calculate_event_magnitude(text)

        assert tier == "DEFAULT"
        assert magnitude == TIER_MAGNITUDE["DEFAULT"]  # 10
        assert len(keywords) == 0

    def test_empty_text(self):
        """空テキストの場合はDEFAULT"""
        result = calculate_event_magnitude("")
        magnitude = result[0]
        tier = result[1]

        assert tier == "DEFAULT"
        assert magnitude == TIER_MAGNITUDE["DEFAULT"]

    def test_none_text(self):
        """Noneテキストの場合はDEFAULT"""
        result = calculate_event_magnitude(None)
        magnitude = result[0]
        tier = result[1]

        assert tier == "DEFAULT"
        assert magnitude == TIER_MAGNITUDE["DEFAULT"]

    def test_multiple_keywords_bonus_two(self):
        """複数キーワードマッチボーナス（2キーワード）"""
        # 正確に2キーワードのみマッチするテキスト（重複を避ける）
        text = "アカデミー賞で画期的な快挙を収めた"
        magnitude, tier, keywords = calculate_event_magnitude(text)

        # 2キーワード（アカデミー賞 + 画期的）で+2ボーナス
        assert tier == "A"
        assert len(keywords) == 2
        assert magnitude == TIER_MAGNITUDE["A"] + 2  # 40 + 2 = 42

    def test_multiple_keywords_bonus_three_or_more(self):
        """複数キーワードマッチボーナス（3キーワード以上）"""
        text = "オリンピック金メダルを獲得し、世界記録を樹立、さらに画期的な技術を披露した"
        result = calculate_event_magnitude(text)
        magnitude = result[0]
        keywords = result[2]

        # 3キーワード以上で+5ボーナス
        assert len(keywords) >= 3
        assert magnitude == TIER_MAGNITUDE["A"] + 5  # 40 + 5 = 45

    def test_tier_priority_s_over_a(self):
        """Tier SがTier Aより優先される"""
        text = "ノーベル賞を受賞し、アカデミー賞も獲得した"
        result = calculate_event_magnitude(text)
        tier = result[1]
        keywords = result[2]

        assert tier == "S"  # Sが最優先
        assert "ノーベル賞" in keywords
        assert "アカデミー賞" in keywords

    def test_tier_priority_a_over_b(self):
        """Tier AがTier Bより優先される"""
        text = "アカデミー賞を受賞し、MVPも獲得した"
        result = calculate_event_magnitude(text)
        tier = result[1]

        assert tier == "A"  # Aが優先


class TestNormalizeMagnitude:
    """normalize_magnitude関数のテスト"""

    def test_normalize_max(self):
        """最大値の正規化"""
        assert normalize_magnitude(50) == 1.0

    def test_normalize_min(self):
        """最小値の正規化"""
        assert normalize_magnitude(0) == 0.0

    def test_normalize_middle(self):
        """中間値の正規化"""
        assert normalize_magnitude(25) == 0.5

    def test_normalize_over_max(self):
        """最大値超過時は1.0に制限"""
        assert normalize_magnitude(100) == 1.0

    def test_normalize_negative(self):
        """負の値は0.0に制限"""
        assert normalize_magnitude(-10) == 0.0

    def test_normalize_custom_max(self):
        """カスタム最大値での正規化"""
        assert normalize_magnitude(50, max_value=100.0) == 0.5

    def test_normalize_zero_max(self):
        """最大値0の場合は0.0を返す"""
        assert normalize_magnitude(50, max_value=0) == 0.0


# ============================================================
# 2. who_factor計算テスト
# ============================================================


class TestWhoFactor:
    """who_factor計算のテスト"""

    def test_superstar_boost_ohtani(self):
        """スーパースターブースト（大谷翔平）"""
        who = calculate_who_factor(
            celebrity_score_v2=821.26,
            multi_lang_pv=5_000_000,
            person_name="大谷翔平",
        )

        # 高いスコアを期待
        assert who > 0.9

    def test_superstar_boost_einstein(self):
        """スーパースターブースト（アインシュタイン）"""
        who = calculate_who_factor(
            celebrity_score_v2=900,
            multi_lang_pv=10_000_000,
            person_name="アルベルト・アインシュタイン",
        )

        # 高いスコアを期待
        assert who > 0.9

    def test_superstar_boost_jobs(self):
        """スーパースターブースト（スティーブ・ジョブズ）"""
        who = calculate_who_factor(
            celebrity_score_v2=800,
            multi_lang_pv=3_000_000,
            person_name="スティーブ・ジョブズ",
        )

        assert who > 0.8

    def test_normal_person_moderate_score(self):
        """一般的な人物（中程度スコア）"""
        who = calculate_who_factor(
            celebrity_score_v2=450,
            multi_lang_pv=500_000,
            person_name="田中太郎",
        )

        # 中程度のスコアを期待
        assert 0.3 < who < 0.7

    def test_normal_person_low_score(self):
        """一般的な人物（低スコア）"""
        who = calculate_who_factor(
            celebrity_score_v2=100,
            multi_lang_pv=10_000,
            person_name="山田花子",
        )

        # 低いスコアを期待
        assert who < 0.3

    def test_zero_pv(self):
        """PVがゼロの場合"""
        who = calculate_who_factor(
            celebrity_score_v2=500,
            multi_lang_pv=0,
            person_name="無名の人",
        )

        # celebrity_scoreのみで計算
        assert 0.2 < who < 0.5

    def test_high_pv_low_celebrity(self):
        """高PV・低知名度スコアの場合"""
        who = calculate_who_factor(
            celebrity_score_v2=100,
            multi_lang_pv=5_000_000,
            person_name="バズった人",
        )

        # PVの寄与を確認
        assert who > 0.2

    def test_who_factor_upper_bound(self):
        """who_factorは1.0を超えない"""
        who = calculate_who_factor(
            celebrity_score_v2=2000,  # 異常に高い値
            multi_lang_pv=100_000_000,  # 異常に高い値
            person_name="大谷翔平",
        )

        assert who <= 1.0


# ============================================================
# 3. when_factor計算テスト
# ============================================================


class TestWhenFactor:
    """when_factor計算のテスト"""

    def test_recent_event_boost_2025(self):
        """直近イベント（2025年）のブースト"""
        when_2025 = calculate_when_factor(2025, current_year=2026)
        when_2015 = calculate_when_factor(2015, current_year=2026)  # 2010年代

        # 2020年代は2010年代より高い
        assert when_2025 > when_2015

    def test_2020s_decade_boost(self):
        """2020年代のブースト確認"""
        when_2023 = calculate_when_factor(2023, current_year=2026)
        when_2015 = calculate_when_factor(2015, current_year=2026)

        # 2020年代は2010年代より高いブースト
        assert when_2023 > when_2015

    def test_2010s_decade_boost(self):
        """2010年代のブースト確認"""
        when_2015 = calculate_when_factor(2015, current_year=2026)
        when_2005 = calculate_when_factor(2005, current_year=2026)

        # 2010年代は2000年代より高いブースト
        assert when_2015 > when_2005

    def test_older_events_penalty(self):
        """古いイベントのペナルティ"""
        when_1980 = calculate_when_factor(1980, current_year=2026)
        when_2000 = calculate_when_factor(2000, current_year=2026)

        # 1980年は2000年より低い
        assert when_1980 < when_2000

    def test_very_old_event(self):
        """非常に古いイベント"""
        when_1900 = calculate_when_factor(1900, current_year=2026)

        # 下限値を持つ
        assert when_1900 > 0.0

    def test_recency_boost_values(self):
        """recency_boost値の確認"""
        assert RECENCY_BOOST["2020s"] == 1.2
        assert RECENCY_BOOST["2010s"] == 1.1
        assert RECENCY_BOOST["2000s"] == 1.0
        assert RECENCY_BOOST["1990s"] == 0.95
        assert RECENCY_BOOST["older"] == 0.90

    def test_when_factor_upper_bound(self):
        """when_factorは1.0を超えない"""
        when_future = calculate_when_factor(2030, current_year=2026)

        assert when_future <= 1.0


# ============================================================
# 4. 統合テスト
# ============================================================


class TestDesirabilityScoreIntegration:
    """desirabilityスコアの統合テスト"""

    def test_ohtani_vs_takeuchi(self):
        """計画の期待値検証：大谷翔平WBC > 竹内結子アカデミー賞"""
        ohtani_wbc = {
            "person_name": "大谷翔平",
            "celebrity_score_v2": 821.26,
            "multi_lang_pv": 5_000_000,
            "episode_text": "WBC優勝に貢献し、MVPを獲得した",
            "episode_importance_score": 85,
            "episode_fame_v6": 85.50,
            "age": 28,
            "birth_year": 1994,
        }

        takeuchi_academy = {
            "person_name": "竹内結子",
            "celebrity_score_v2": 450,
            "multi_lang_pv": 500_000,
            "episode_text": "アカデミー賞の助演女優賞を受賞した",
            "episode_importance_score": 80,
            "episode_fame_v6": 78,
            "age": 35,
            "birth_year": 1980,
        }

        ohtani_score = calculate_desirability_score(ohtani_wbc)
        takeuchi_score = calculate_desirability_score(takeuchi_academy)

        # 大谷翔平 > 竹内結子 が期待値
        assert ohtani_score["desirability_score"] > takeuchi_score["desirability_score"]

        # スコアの詳細確認
        assert ohtani_score["who_factor"] > takeuchi_score["who_factor"]

    def test_ohtani_wbc_details(self):
        """大谷翔平WBCエピソードの詳細確認"""
        ohtani_wbc = {
            "person_name": "大谷翔平",
            "celebrity_score_v2": 821.26,
            "multi_lang_pv": 5_000_000,
            "episode_text": "WBC優勝に貢献し、MVPを獲得した",
            "episode_importance_score": 85,
            "episode_fame_v6": 85.50,
            "age": 28,
            "birth_year": 1994,
        }

        result = calculate_desirability_score(ohtani_wbc)

        # MVPはTier B
        assert result["event_tier"] == "B"
        assert "MVP" in result["matched_keywords"]

        # スーパースターブースト確認
        assert result["who_factor"] > 0.9

        # 2022年のイベント（1994 + 28）
        assert result["event_year"] == 2022

    def test_takeuchi_academy_details(self):
        """竹内結子アカデミー賞エピソードの詳細確認"""
        takeuchi_academy = {
            "person_name": "竹内結子",
            "celebrity_score_v2": 450,
            "multi_lang_pv": 500_000,
            "episode_text": "アカデミー賞の助演女優賞を受賞した",
            "episode_importance_score": 80,
            "episode_fame_v6": 78,
            "age": 35,
            "birth_year": 1980,
        }

        result = calculate_desirability_score(takeuchi_academy)

        # アカデミー賞はTier A
        assert result["event_tier"] == "A"
        assert "アカデミー賞" in result["matched_keywords"]

        # 2015年のイベント（1980 + 35）
        assert result["event_year"] == 2015

    def test_historic_achievement(self):
        """歴史的達成のスコア計算"""
        einstein = {
            "person_name": "アルベルト・アインシュタイン",
            "celebrity_score_v2": 950,
            "multi_lang_pv": 10_000_000,
            "episode_text": "相対性理論を発表し、物理学に革命をもたらした",
            "episode_importance_score": 100,
            "episode_fame_v6": 100,
            "age": 26,
            "birth_year": 1879,
        }

        result = calculate_desirability_score(einstein)

        # Tier Sを期待
        assert result["event_tier"] == "S"
        assert "相対性理論" in result["matched_keywords"]

        # 高いwho_factorを期待
        assert result["who_factor"] > 0.9

    def test_modern_vs_historic_recency(self):
        """現代 vs 歴史的イベントのrecency比較"""
        modern = {
            "person_name": "現代の人",
            "celebrity_score_v2": 500,
            "multi_lang_pv": 500_000,
            "episode_text": "デビューした",
            "age": 25,
            "birth_year": 2000,
        }

        historic = {
            "person_name": "歴史的人物",
            "celebrity_score_v2": 500,
            "multi_lang_pv": 500_000,
            "episode_text": "デビューした",
            "age": 25,
            "birth_year": 1900,
        }

        modern_result = calculate_desirability_score(modern)
        historic_result = calculate_desirability_score(historic)

        # 現代の方がwhen_factorが高い
        assert modern_result["when_factor"] > historic_result["when_factor"]


# ============================================================
# 5. config検証テスト
# ============================================================


class TestConfig:
    """config設定の検証テスト"""

    def test_tier_magnitude_values(self):
        """Tier magnitude値の確認"""
        assert TIER_MAGNITUDE["S"] == 50
        assert TIER_MAGNITUDE["A"] == 40
        assert TIER_MAGNITUDE["B"] == 30
        assert TIER_MAGNITUDE["C"] == 20
        assert TIER_MAGNITUDE["DEFAULT"] == 10

    def test_tier_s_keywords_exist(self):
        """Tier Sキーワードの存在確認"""
        assert len(TIER_S_KEYWORDS) > 0
        assert "ノーベル賞" in TIER_S_KEYWORDS
        assert "世界初" in TIER_S_KEYWORDS
        assert "史上初" in TIER_S_KEYWORDS

    def test_tier_a_keywords_exist(self):
        """Tier Aキーワードの存在確認"""
        assert len(TIER_A_KEYWORDS) > 0
        assert "アカデミー賞" in TIER_A_KEYWORDS
        assert "オリンピック金メダル" in TIER_A_KEYWORDS
        assert "グラミー賞" in TIER_A_KEYWORDS

    def test_tier_b_keywords_exist(self):
        """Tier Bキーワードの存在確認"""
        assert len(TIER_B_KEYWORDS) > 0
        assert "MVP" in TIER_B_KEYWORDS
        assert "優勝" in TIER_B_KEYWORDS
        assert "日本初" in TIER_B_KEYWORDS

    def test_tier_c_keywords_exist(self):
        """Tier Cキーワードの存在確認"""
        assert len(TIER_C_KEYWORDS) > 0
        assert "デビュー" in TIER_C_KEYWORDS
        assert "受賞" in TIER_C_KEYWORDS

    def test_superstars_list(self):
        """スーパースターリストの確認"""
        assert len(SUPERSTARS) > 0
        assert "大谷翔平" in SUPERSTARS
        assert "アインシュタイン" in SUPERSTARS
        assert "スティーブ・ジョブズ" in SUPERSTARS

    def test_desirability_weights_sum(self):
        """重み配分の合計確認"""
        total = sum(DESIRABILITY_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01  # 合計が1.0に近い

    def test_desirability_weights_keys(self):
        """重み配分のキー確認"""
        assert "event_magnitude" in DESIRABILITY_WEIGHTS
        assert "person_fame" in DESIRABILITY_WEIGHTS
        assert "recency" in DESIRABILITY_WEIGHTS
        assert "diversity" in DESIRABILITY_WEIGHTS


# ============================================================
# 6. エッジケーステスト
# ============================================================


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_episode_data(self):
        """空のエピソードデータ"""
        result = calculate_desirability_score({})

        assert "desirability_score" in result
        assert result["event_tier"] == "DEFAULT"

    def test_missing_celebrity_score(self):
        """celebrity_scoreが欠損"""
        data = {
            "person_name": "テスト",
            "episode_text": "デビューした",
            "age": 25,
            "birth_year": 2000,
        }
        result = calculate_desirability_score(data)

        assert "desirability_score" in result

    def test_negative_values(self):
        """負の値を含むデータ"""
        data = {
            "person_name": "テスト",
            "celebrity_score_v2": -100,
            "multi_lang_pv": -1000,
            "episode_text": "テスト",
            "age": 25,
            "birth_year": 2000,
        }
        result = calculate_desirability_score(data)

        # エラーにならずスコアが計算される
        assert "desirability_score" in result
        assert result["desirability_score"] >= 0

    def test_very_long_episode_text(self):
        """非常に長いエピソードテキスト"""
        long_text = "ノーベル賞を受賞した" + "。" * 10000
        result = calculate_event_magnitude(long_text)
        tier = result[1]
        keywords = result[2]

        assert tier == "S"
        assert "ノーベル賞" in keywords

    def test_special_characters_in_text(self):
        """特殊文字を含むテキスト"""
        text = "【特報】ノーベル賞★受賞！！！"
        result = calculate_event_magnitude(text)
        tier = result[1]
        keywords = result[2]

        assert tier == "S"
        assert "ノーベル賞" in keywords

    def test_unicode_text(self):
        """Unicode文字を含むテキスト"""
        text = "アカデミー賞🏆を受賞した"
        result = calculate_event_magnitude(text)
        tier = result[1]
        keywords = result[2]

        assert tier == "A"
        assert "アカデミー賞" in keywords


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
