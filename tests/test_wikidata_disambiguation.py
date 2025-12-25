#!/usr/bin/env python3
"""
Wikidata曖昧性解消モジュールのテスト。

テストケース:
1. 短い名前が基本概念にマッチしないこと
2. 架空キャラクターが実在の動物/場所にマッチしないこと
3. 確信度閾値が正しく適用されること
4. Q番号ガードレールが機能すること
"""

import pytest

from scripts.fame_score_v3.wikidata_disambiguation import (
    BASIC_CONCEPT_QID_THRESHOLD,
    EXCLUDE_TYPES,
    get_min_confidence_for_name,
    is_basic_concept_qid,
    is_valid_person_type,
)


class TestExcludeTypes:
    """除外タイプのテスト"""

    def test_taxon_in_exclude_types(self):
        """生物学的分類（taxon）が除外対象に含まれる"""
        assert "Q16521" in EXCLUDE_TYPES

    def test_country_in_exclude_types(self):
        """国が除外対象に含まれる"""
        assert "Q6256" in EXCLUDE_TYPES

    def test_animal_in_exclude_types(self):
        """動物が除外対象に含まれる"""
        assert "Q729" in EXCLUDE_TYPES

    def test_band_in_exclude_types(self):
        """バンドが除外対象に含まれる"""
        assert "Q215380" in EXCLUDE_TYPES


class TestIsValidPersonType:
    """is_valid_person_type関数のテスト"""

    def test_human_is_valid_for_real(self):
        """humanタイプは実在人物として有効"""
        is_valid, reason = is_valid_person_type(["Q5"], "REAL")
        assert is_valid is True
        assert reason == ""

    def test_fictional_character_is_valid_for_fictional(self):
        """架空キャラクターは架空タイプとして有効"""
        is_valid, reason = is_valid_person_type(["Q95074"], "FICTIONAL")
        assert is_valid is True
        assert reason == ""

    def test_taxon_is_excluded(self):
        """生物学的分類は除外される"""
        is_valid, reason = is_valid_person_type(["Q16521"], "REAL")
        assert is_valid is False
        assert "excluded_type" in reason

    def test_country_is_excluded(self):
        """国は除外される"""
        is_valid, reason = is_valid_person_type(["Q6256"], "REAL")
        assert is_valid is False
        assert "excluded_type" in reason

    def test_animal_is_excluded(self):
        """動物は除外される"""
        is_valid, reason = is_valid_person_type(["Q729"], "REAL")
        assert is_valid is False
        assert "excluded_type" in reason


class TestBasicConceptQid:
    """基本概念Q番号のテスト"""

    def test_small_qid_is_basic_concept(self):
        """小さいQ番号は基本概念"""
        assert is_basic_concept_qid("Q140") is True  # ライオン
        assert is_basic_concept_qid("Q114") is True  # ケニア
        assert is_basic_concept_qid("Q199") is True  # 数字の1

    def test_large_qid_is_not_basic_concept(self):
        """大きいQ番号は基本概念ではない"""
        assert is_basic_concept_qid("Q1361450") is False  # ken（ミュージシャン）
        assert is_basic_concept_qid("Q18409621") is False  # ONE（漫画家）

    def test_threshold_boundary(self):
        """閾値境界のテスト"""
        assert is_basic_concept_qid(f"Q{BASIC_CONCEPT_QID_THRESHOLD - 1}") is True
        assert is_basic_concept_qid(f"Q{BASIC_CONCEPT_QID_THRESHOLD}") is False

    def test_basic_concept_qid_blocks_non_human(self):
        """基本概念Q番号で非humanは拒否される"""
        # Q140（ライオン）のP31が空リストの場合
        is_valid, reason = is_valid_person_type([], "REAL", qid="Q140")
        assert is_valid is False
        assert "basic_concept" in reason

    def test_basic_concept_qid_allows_human(self):
        """基本概念Q番号でもhumanなら許可"""
        # Q23（ジョージ・ワシントン）のP31がQ5（人間）を含む場合
        is_valid, reason = is_valid_person_type(["Q5"], "REAL", qid="Q23")
        assert is_valid is True


class TestMinConfidenceForName:
    """名前長に基づく最低確信度のテスト"""

    def test_very_short_name_high_threshold(self):
        """2文字以下の名前は85%の閾値"""
        assert get_min_confidence_for_name("ジジ", "FICTIONAL") == 85.0
        assert get_min_confidence_for_name("ON", "REAL") == 85.0

    def test_short_name_high_threshold(self):
        """3文字の名前は75%の閾値"""
        assert get_min_confidence_for_name("ken", "REAL") == 75.0
        assert get_min_confidence_for_name("ONE", "REAL") == 75.0

    def test_normal_name_default_threshold(self):
        """4文字以上の名前は通常の閾値"""
        assert get_min_confidence_for_name("大谷翔平", "REAL") == 50.0

    def test_fictional_character_medium_threshold(self):
        """架空キャラクターは60%の閾値（4文字以上）"""
        assert get_min_confidence_for_name("ハリー・ポッター", "FICTIONAL") == 60.0


class TestJijiCase:
    """ジジのケース再現テスト"""

    def test_lion_qid_blocked_for_fictional(self):
        """Q140（ライオン）は架空キャラクター検索で拒否される"""
        # ライオン（Q140）は基本概念かつP31にQ5がない
        is_valid, reason = is_valid_person_type([], "FICTIONAL", qid="Q140")
        assert is_valid is False
        # basic_conceptまたはnot_characterで拒否
        assert "basic_concept" in reason or "not_character" in reason

    def test_short_fictional_name_high_threshold(self):
        """ジジ（2文字）の確信度閾値は85%"""
        threshold = get_min_confidence_for_name("ジジ", "FICTIONAL")
        assert threshold == 85.0


class TestKenCase:
    """kenのケース再現テスト"""

    def test_kenya_blocked_by_basic_concept_or_exclude(self):
        """Q114（ケニア）は基本概念または国として除外される"""
        # ケニア（Q114）は基本概念Q番号（<1000）なのでbasic_conceptで拒否
        # または国（Q6256）が含まれる場合はexcluded_typeで拒否
        is_valid, reason = is_valid_person_type(["Q6256"], "REAL", qid="Q114")
        assert is_valid is False
        # basic_conceptまたはexcluded_typeのいずれかで拒否されるべき
        assert "basic_concept" in reason or "excluded_type" in reason

    def test_short_real_name_high_threshold(self):
        """ken（3文字）の確信度閾値は75%"""
        threshold = get_min_confidence_for_name("ken", "REAL")
        assert threshold == 75.0


class TestOneCase:
    """ONEのケース再現テスト"""

    def test_number_one_blocked_as_basic_concept(self):
        """Q199（数字の1）は基本概念として拒否される"""
        is_valid, reason = is_valid_person_type([], "REAL", qid="Q199")
        assert is_valid is False
        assert "basic_concept" in reason

    def test_very_short_name_very_high_threshold(self):
        """ONE（3文字だがすべて英字）の確信度閾値"""
        threshold = get_min_confidence_for_name("ONE", "REAL")
        assert threshold == 75.0
