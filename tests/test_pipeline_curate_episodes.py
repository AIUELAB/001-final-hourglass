"""
tests/test_pipeline_curate_episodes.py

Stage 3: curate-episodes パイプラインのテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# テスト対象のインポート
from scripts.pipeline.pipeline_curate_episodes import (
    extract_age_from_context,
    convert_to_epup_format,
)
from src.models.curated_episode import CuratedEpisode


class TestAgeExtraction:
    """年齢抽出ロジックのテスト"""

    def test_extract_age_pattern1(self):
        """パターン1: 年齢XX歳時"""
        context = "年齢31歳時の業績"
        age = extract_age_from_context(context)
        assert age == 31

    def test_extract_age_pattern2(self):
        """パターン2: XX歳のとき"""
        context = "40歳のときの発見"
        age = extract_age_from_context(context)
        assert age == 40

    def test_extract_age_pattern3(self):
        """パターン3: XX歳時"""
        context = "23歳時の業績"
        age = extract_age_from_context(context)
        assert age == 23

    def test_extract_age_no_match(self):
        """年齢が含まれていない場合"""
        context = "作品設定"
        age = extract_age_from_context(context)
        assert age is None

    def test_extract_age_empty_string(self):
        """空文字列の場合"""
        context = ""
        age = extract_age_from_context(context)
        assert age is None

    def test_extract_age_multiple_ages(self):
        """複数の年齢が含まれている場合（最初にマッチしたものを返す）"""
        context = "年齢31歳時と40歳時の業績"
        age = extract_age_from_context(context)
        assert age == 31


class TestEPUPConversion:
    """EPUP形式変換のテスト（モック使用）"""

    @patch("scripts.pipeline_curate_episodes.Anthropic")
    def test_convert_to_epup_real_person(self, mock_anthropic):
        """実在人物のEPUP変換テスト"""
        # モックレスポンス設定
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.content = [Mock(text="あなたと同じ31歳のとき、イチローはメジャーリーグ記録を更新しました。")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        # テスト実行
        result = convert_to_epup_format(
            person_name="イチロー",
            person_type="REAL",
            age=31,
            raw_text="2004年シーズン262安打記録を達成",
            context="年齢31歳時の業績",
            evidence_quality="B",
            api_key="test_key",
        )

        # 検証
        assert result.startswith("あなたと同じ")
        assert "イチロー" in result
        mock_client.messages.create.assert_called_once()

    @patch("scripts.pipeline_curate_episodes.Anthropic")
    def test_convert_to_epup_fictional_character(self, mock_anthropic):
        """架空キャラクターのEPUP変換テスト"""
        # モックレスポンス設定
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.content = [Mock(text="あなたと同じ10歳のとき、ドラえもんは22世紀からやってきました。")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        # テスト実行
        result = convert_to_epup_format(
            person_name="ドラえもん",
            person_type="FICTIONAL",
            age=10,
            raw_text="22世紀からやってきた猫型ロボット",
            context="作品設定",
            evidence_quality="A",
            api_key="test_key",
        )

        # 検証
        assert result.startswith("あなたと同じ")
        assert "ドラえもん" in result
        mock_client.messages.create.assert_called_once()

    @patch("scripts.pipeline_curate_episodes.Anthropic")
    def test_convert_to_epup_api_error(self, mock_anthropic):
        """API呼び出しエラーのテスト"""
        # モックエラー設定
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client

        # テスト実行（エラーが発生することを確認）
        with pytest.raises(Exception) as exc_info:
            convert_to_epup_format(
                person_name="テスト",
                person_type="REAL",
                age=30,
                raw_text="テストテキスト",
                context="テストコンテキスト",
                evidence_quality="B",
                api_key="test_key",
            )

        assert "API Error" in str(exc_info.value)


class TestCuratedEpisodeModel:
    """CuratedEpisodeモデルのテスト"""

    def test_curated_episode_creation(self):
        """正常なCuratedEpisodeインスタンス作成"""
        episode = CuratedEpisode(
            person_id="P001",
            person_name="イチロー",
            age=31,
            episode_text="あなたと同じ31歳のとき、イチローはメジャーリーグ記録を更新しました。",
            source_id="SRC-test123",
            source_url="https://example.com",
            evidence_quality="B",
            person_type="REAL",
            category="スポーツ",
        )

        assert episode.person_id == "P001"
        assert episode.person_name == "イチロー"
        assert episode.age == 31
        assert episode.validation_status == "pending"

    def test_curated_episode_validation_invalid_age(self):
        """無効な年齢でのバリデーションエラー"""
        with pytest.raises(ValueError) as exc_info:
            CuratedEpisode(
                person_id="P001",
                person_name="テスト",
                age=200,  # 無効な年齢
                episode_text="テストエピソード",
                source_id="SRC-test",
                source_url="https://example.com",
                evidence_quality="A",
            )

        assert "Invalid age" in str(exc_info.value)

    def test_curated_episode_validation_invalid_quality(self):
        """無効な品質値でのバリデーションエラー"""
        with pytest.raises(ValueError) as exc_info:
            CuratedEpisode(
                person_id="P001",
                person_name="テスト",
                age=30,
                episode_text="テストエピソード",
                source_id="SRC-test",
                source_url="https://example.com",
                evidence_quality="D",  # 無効な品質
            )

        assert "Invalid evidence_quality" in str(exc_info.value)

    def test_curated_episode_to_dict(self):
        """to_dictメソッドのテスト"""
        episode = CuratedEpisode(
            person_id="P001",
            person_name="イチロー",
            age=31,
            episode_text="あなたと同じ31歳のとき、イチローは記録を更新しました。",
            source_id="SRC-test",
            source_url="https://example.com",
            evidence_quality="B",
            category="スポーツ",
        )

        data = episode.to_dict()

        assert data["person_id"] == "P001"
        assert data["age"] == 31
        assert data["evidence_quality"] == "B"
        assert data["category"] == "スポーツ"
        assert "generated_at" in data

    def test_curated_episode_mark_passed(self):
        """バリデーション合格マーク"""
        episode = CuratedEpisode(
            person_id="P001",
            person_name="テスト",
            age=30,
            episode_text="あなたと同じ30歳のとき、テストは成功しました。",
            source_id="SRC-test",
            source_url="https://example.com",
            evidence_quality="A",
        )

        episode.mark_passed()

        assert episode.validation_status == "passed"
        assert episode.validation_issues is None

    def test_curated_episode_mark_failed(self):
        """バリデーション不合格マーク"""
        episode = CuratedEpisode(
            person_id="P001",
            person_name="テスト",
            age=30,
            episode_text="あなたと同じ30歳のとき、テストは失敗しました。",
            source_id="SRC-test",
            source_url="https://example.com",
            evidence_quality="C",
        )

        episode.mark_failed("テンプレート文言検出")

        assert episode.validation_status == "failed"
        assert episode.validation_issues == "テンプレート文言検出"


class TestIntegration:
    """統合テスト"""

    def test_full_workflow_age_extraction_to_episode_creation(self):
        """年齢抽出からエピソード作成までのワークフロー"""
        # 1. 年齢抽出
        context = "年齢31歳時の業績"
        age = extract_age_from_context(context)
        assert age == 31

        # 2. CuratedEpisode作成
        episode = CuratedEpisode(
            person_id="P001",
            person_name="イチロー",
            age=age,
            episode_text="あなたと同じ31歳のとき、イチローはメジャーリーグ記録を更新しました。",
            source_id="SRC-test",
            source_url="https://example.com",
            evidence_quality="B",
        )

        # 3. バリデーション
        assert episode.validation_status == "pending"
        episode.mark_passed()
        assert episode.validation_status == "passed"

    @patch("scripts.pipeline_curate_episodes.Anthropic")
    def test_end_to_end_with_mocked_llm(self, mock_anthropic):
        """モック化したLLMでのエンドツーエンドテスト"""
        # モック設定
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.content = [Mock(text="あなたと同じ40歳のとき、山中伸弥はiPS細胞を発見しました。")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        # 1. 年齢抽出
        context = "年齢40歳時の業績"
        age = extract_age_from_context(context)
        assert age == 40

        # 2. EPUP変換
        episode_text = convert_to_epup_format(
            person_name="山中伸弥",
            person_type="REAL",
            age=age,
            raw_text="iPS細胞を世界で初めて作製",
            context=context,
            evidence_quality="A",
            api_key="test_key",
        )

        assert episode_text.startswith("あなたと同じ")
        assert "山中伸弥" in episode_text

        # 3. CuratedEpisode作成
        episode = CuratedEpisode(
            person_id="P002",
            person_name="山中伸弥",
            age=age,
            episode_text=episode_text,
            source_id="SRC-test",
            source_url="https://example.com",
            evidence_quality="A",
        )

        assert episode.age == 40
        assert episode.evidence_quality == "A"
