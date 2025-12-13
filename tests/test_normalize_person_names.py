#!/usr/bin/env python3
"""
人物名正規化テストスイート

カテゴリ別に25件以上のテストケースを網羅。
ユーザー提供の例に基づいてテストを作成。
"""

import pytest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.normalize_person_names import PersonNameNormalizer


class TestNormalizePersonNames:
    """人物名正規化テスト"""

    @pytest.fixture
    def normalizer(self):
        """テスト用の正規化エンジン"""
        return PersonNameNormalizer(min_confidence=0.80)

    # ========================================
    # 職業・肩書系テスト（6件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name,expected_pattern",
        [
            ("落語家・立川談志", "立川談志", "PROFESSION_PREFIX"),
            ("書道家・金澤翔子", "金澤翔子", "PROFESSION_PREFIX"),
            ("現代美術家・村上隆", "村上隆", "PROFESSION_PREFIX"),
            ("日本画家・上村松園", "上村松園", "PROFESSION_PREFIX"),
            ("華道家・假屋崎省吾", "假屋崎省吾", "PROFESSION_PREFIX"),
            ("能楽師・世阿弥", "世阿弥", "PROFESSION_PREFIX"),
        ],
    )
    def test_profession_prefix_patterns(self, normalizer, input_name, expected_name, expected_pattern):
        """職業・人物 形式のテスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name
        assert result.pattern_type == expected_pattern

    # ========================================
    # 修飾子付き職業テスト（3件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name",
        [
            ("秋葉原系漫画家OKAMA", "OKAMA"),
            ("お笑い声優野沢雅子", "野沢雅子"),  # 修飾子+職業+人物
        ],
    )
    def test_modified_profession_patterns(self, normalizer, input_name, expected_name):
        """修飾子付き職業パターンのテスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name

    # ========================================
    # 役名付き職業テスト（2件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name",
        [
            ("アニメ声優・悟空役野沢雅子", "野沢雅子"),
        ],
    )
    def test_role_suffix_patterns(self, normalizer, input_name, expected_name):
        """役名付き職業パターンのテスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name

    # ========================================
    # 企業・創業者系テスト（5件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name",
        [
            ("豊田織機創業者豊田佐吉", "豊田佐吉"),
            ("ロッキード・マーティンCEOマリリン・ヒューソン", "マリリン・ヒューソン"),
            ("IBM元CEOバージニア・ロメッティ", "バージニア・ロメッティ"),
            ("バークシャー・ハサウェイ会長ウォーレン・バフェット", "ウォーレン・バフェット"),
            ("テスラCEOイーロン・マスク", "イーロン・マスク"),
        ],
    )
    def test_company_founder_patterns(self, normalizer, input_name, expected_name):
        """企業・創業者パターンのテスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name

    # ========================================
    # 関係性系テスト（4件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name",
        [
            ("ヘンリー・フォードの息子エドセル・フォード", "エドセル・フォード"),
            ("ジョン・ロックフェラーの息子ジョン・ロックフェラー・ジュニア", "ジョン・ロックフェラー・ジュニア"),
            ("ベルナール・アルノーの息子アントワーヌ・アルノー", "アントワーヌ・アルノー"),
            ("ココ・シャネルの後継者カール・ラガーフェルド", "カール・ラガーフェルド"),
        ],
    )
    def test_relationship_patterns(self, normalizer, input_name, expected_name):
        """関係性パターンのテスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name
        assert result.pattern_type == "RELATIONSHIP"

    # ========================================
    # アイドルグループ系テスト（4件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name,expected_group",
        [
            ("AKB48指原莉乃", "指原莉乃", "AKB48"),
            ("乃木坂46白石麻衣", "白石麻衣", "乃木坂46"),
            ("嵐大野智", "大野智", "嵐"),
            ("SMAP木村拓哉", "木村拓哉", "SMAP"),
        ],
    )
    def test_idol_group_patterns(self, normalizer, input_name, expected_name, expected_group):
        """アイドルグループパターンのテスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name
        assert result.affiliation == expected_group
        assert result.pattern_type == "IDOL_GROUP"

    # ========================================
    # 音楽グループ系テスト（4件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name,expected_group",
        [
            ("RADWIMPSの野田洋次郎", "野田洋次郎", "RADWIMPS"),
            ("チューリップ・財津和夫", "財津和夫", "チューリップ"),
            ("スキマスイッチ・大橋卓弥", "大橋卓弥", "スキマスイッチ"),
            ("U2のボノ", "ボノ", "U2"),
        ],
    )
    def test_music_group_patterns(self, normalizer, input_name, expected_name, expected_group):
        """音楽グループパターンのテスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name
        assert result.affiliation == expected_group

    # ========================================
    # スポーツ系テスト（4件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name",
        [
            ("競泳萩野公介", "萩野公介"),
            ("柔道山下泰裕", "山下泰裕"),
            ("ラグビー五郎丸歩", "五郎丸歩"),
            ("野球田中将大", "田中将大"),
        ],
    )
    def test_sport_patterns(self, normalizer, input_name, expected_name):
        """スポーツパターンのテスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name
        assert result.pattern_type == "SPORT_PREFIX"

    # ========================================
    # リーグ系テスト（2件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name,expected_league",
        [
            ("NBA・ヤニス・アンテトクンポ", "ヤニス・アンテトクンポ", "NBA"),
            ("F1・マックス・フェルスタッペン", "マックス・フェルスタッペン", "F1"),
        ],
    )
    def test_league_patterns(self, normalizer, input_name, expected_name, expected_league):
        """リーグパターンのテスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name
        assert result.affiliation == expected_league

    # ========================================
    # 代数表記テスト（2件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name",
        [
            ("十四代酒井田柿右衛門", "酒井田柿右衛門"),
            ("三代目林家正蔵", "林家正蔵"),
        ],
    )
    def test_generation_patterns(self, normalizer, input_name, expected_name):
        """代数表記パターンのテスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name
        assert result.pattern_type == "GENERATION_PREFIX"

    # ========================================
    # 西洋人名保護テスト（4件）
    # ========================================

    @pytest.mark.parametrize(
        "input_name",
        [
            "マイケル・ジャクソン",
            "ウォーレン・バフェット",
            "イーロン・マスク",
            "藤子・F・不二雄",
        ],
    )
    def test_western_name_protection(self, normalizer, input_name):
        """西洋人名が誤分割されないことを確認"""
        result = normalizer.normalize(input_name)
        assert result is None, f"「{input_name}」が誤って分割されました"

    # ========================================
    # Idempotent（再実行安全）テスト（1件）
    # ========================================

    def test_idempotent_already_clean(self, normalizer):
        """既に正規化された名前を再正規化しても変更されないこと"""
        clean_names = [
            "野沢雅子",
            "立川談志",
            "野田洋次郎",
            "指原莉乃",
            "村上隆",
            "山下泰裕",
        ]
        for name in clean_names:
            result = normalizer.normalize(name)
            assert result is None, f"クリーンな名前「{name}」が誤って検出されました"

    # ========================================
    # 追加の実例テスト（ユーザー提供例より）
    # ========================================

    @pytest.mark.parametrize(
        "input_name,expected_name",
        [
            # コメディアン系
            ("コメディアン・爆笑問題田中", "爆笑問題田中"),
            # お笑い系（グループ・人物）
            ("野性爆弾くっきー", "くっきー"),
            ("トレンディエンジェル・斎藤", "斎藤"),
            ("ガンバレルーヤ・まひる", "まひる"),
            # 企業系
            ("セコム創業者飯田亮", "飯田亮"),
            ("ニトリ創業者似鳥昭雄", "似鳥昭雄"),
            ("楽天創業者三木谷浩史", "三木谷浩史"),
            # スポーツ系
            ("フィギュア安藤美姫", "安藤美姫"),
            ("体操白井健三", "白井健三"),
            ("陸上桐生祥秀", "桐生祥秀"),
        ],
    )
    def test_additional_user_examples(self, normalizer, input_name, expected_name):
        """ユーザー提供の追加例テスト"""
        result = normalizer.normalize(input_name)
        assert result is not None, f"「{input_name}」がマッチしませんでした"
        assert result.normalized_name == expected_name


class TestNormalizationResultAttributes:
    """正規化結果の属性テスト"""

    @pytest.fixture
    def normalizer(self):
        return PersonNameNormalizer(min_confidence=0.80)

    def test_result_has_required_attributes(self, normalizer):
        """結果オブジェクトが必要な属性を持つこと"""
        result = normalizer.normalize("落語家・立川談志")
        assert result is not None
        assert hasattr(result, "original_name")
        assert hasattr(result, "normalized_name")
        assert hasattr(result, "title")
        assert hasattr(result, "affiliation")
        assert hasattr(result, "pattern_type")
        assert hasattr(result, "confidence")
        assert hasattr(result, "requires_review")
        assert hasattr(result, "match_detail")

    def test_confidence_range(self, normalizer):
        """信頼度が0-1の範囲内であること"""
        result = normalizer.normalize("テスラCEOイーロン・マスク")
        assert result is not None
        assert 0.0 <= result.confidence <= 1.0

    def test_original_name_preserved(self, normalizer):
        """元の名前が保存されること"""
        input_name = "AKB48指原莉乃"
        result = normalizer.normalize(input_name)
        assert result is not None
        assert result.original_name == input_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
