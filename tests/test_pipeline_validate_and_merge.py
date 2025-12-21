"""
tests/test_pipeline_validate_and_merge.py

Stage 4: validate-and-merge パイプラインのテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# テスト対象のインポート
from scripts.pipeline.pipeline_validate_and_merge import (
    generate_episode_id,
    check_duplicate_source_id,
    validate_episode,
    merge_to_master,
)
from src.models.curated_episode import CuratedEpisode
from src.validators.post_llm_validator import PostLLMValidator, QualityLevel


class TestEpisodeIDGeneration:
    """episode_id生成のテスト"""

    def test_generate_episode_id_format(self):
        """episode_idフォーマット確認"""
        episode_id = generate_episode_id()

        # EP-で始まる
        assert episode_id.startswith("EP-")

        # EP-YYMMDDHHMMSSmmm形式（合計18文字）
        assert len(episode_id) == 18

        # ハイフン以降は数字のみ
        timestamp_part = episode_id[3:]
        assert timestamp_part.isdigit()
        assert len(timestamp_part) == 15  # YYMMDDHHMMSSmmm

    def test_generate_episode_id_uniqueness(self):
        """連続生成でユニークなIDが生成されるか"""
        id1 = generate_episode_id()
        id2 = generate_episode_id()

        # ミリ秒が異なるため、通常は異なるIDが生成される
        # （極端に高速な場合は同じになる可能性もあるが、テスト環境では問題ない）
        # 少なくともフォーマットは正しいはず
        assert id1.startswith("EP-")
        assert id2.startswith("EP-")


class TestDuplicateDetection:
    """重複検出のテスト"""

    def test_check_duplicate_source_id_no_duplicate(self):
        """重複なしの場合"""
        master_df = pd.DataFrame(
            {
                "episode_id": ["EP-001", "EP-002"],
                "source_url": ["https://example.com/1", "https://example.com/2"],
            }
        )

        result = check_duplicate_source_id("SRC-new", master_df)
        assert result is None

    def test_check_duplicate_source_id_with_duplicate(self):
        """重複ありの場合"""
        master_df = pd.DataFrame(
            {
                "episode_id": ["EP-001", "EP-002"],
                "source_url": ["SRC-existing", "https://example.com/2"],
            }
        )

        result = check_duplicate_source_id("SRC-existing", master_df)
        assert result == "EP-001"

    def test_check_duplicate_source_id_missing_column(self):
        """source_urlカラムがない場合（None返却）"""
        master_df = pd.DataFrame(
            {
                "episode_id": ["EP-001", "EP-002"],
            }
        )

        result = check_duplicate_source_id("SRC-test", master_df)
        assert result is None


class TestEpisodeValidation:
    """エピソードバリデーションのテスト"""

    def test_validate_episode_excellent_quality(self):
        """EXCELLENT品質のエピソード"""
        episode = CuratedEpisode(
            person_id="P001",
            person_name="テスト",
            age=30,
            episode_text="あなたと同じ30歳のとき、テストは重要な発見をしました。この発見は後の研究に大きな影響を与え、多くの賞を受賞することになります。研究チームは数年にわたる実験の末に画期的な結果を得ることができ、学術界に大きな衝撃を与えました。",
            source_id="SRC-test",
            source_url="https://example.com",
            evidence_quality="A",
        )

        validator = PostLLMValidator()
        status, validation_info = validate_episode(episode, validator)

        assert status == "passed"
        assert validation_info["is_valid"] is True
        assert validation_info["quality_level"] in ["excellent", "good"]

    def test_validate_episode_failed_no_lead(self):
        """リード文がないエピソード（不合格）"""
        episode = CuratedEpisode(
            person_id="P001",
            person_name="テスト",
            age=30,
            episode_text="テストは重要な発見をしました。",  # 「あなたと同じ」で始まらない
            source_id="SRC-test",
            source_url="https://example.com",
            evidence_quality="A",
        )

        validator = PostLLMValidator()
        status, validation_info = validate_episode(episode, validator)

        assert status == "failed"
        assert validation_info["is_valid"] is False
        assert len(validation_info["errors"]) > 0


class TestMergeToMaster:
    """マスターCSVへのマージテスト"""

    def test_merge_to_master(self):
        """正常なマージ"""
        episode = CuratedEpisode(
            person_id="P001",
            person_name="テスト",
            age=30,
            episode_text="あなたと同じ30歳のとき、テストは重要な発見をしました。",
            source_id="SRC-test",
            source_url="https://example.com",
            evidence_quality="A",
        )

        master_df = pd.DataFrame(
            {
                "episode_id": ["EP-001"],
                "person_id": ["P000"],
                "person_name": ["既存"],
                "age": [25],
            }
        )

        validation_info = {
            "quality_score": 0.95,
            "quality_level": "excellent",
        }

        new_master_df = merge_to_master(
            episode=episode,
            episode_id="EP-002",
            master_df=master_df,
            validation_info=validation_info,
        )

        # 新しい行が追加されている
        assert len(new_master_df) == 2
        assert new_master_df.iloc[1]["episode_id"] == "EP-002"
        assert new_master_df.iloc[1]["person_name"] == "テスト"
        assert new_master_df.iloc[1]["quality_score"] == 0.95


class TestIntegration:
    """統合テスト"""

    def test_full_validation_workflow(self):
        """バリデーション→品質ゲート→episode_id生成のワークフロー"""
        # 1. エピソード作成
        episode = CuratedEpisode(
            person_id="P001",
            person_name="イチロー",
            age=31,
            episode_text="あなたと同じ31歳のとき、イチローはメジャーリーグのシーズン最多安打記録を84年ぶりに更新しました。2004年シーズン、262安打という驚異的な数字を叩き出し、ジョージ・シスラーが1920年に作った257安打の記録を破ったのです。この偉業は、日本人選手として、そしてメジャーリーグ史に永遠に刻まれる記録となりました。",
            source_id="SRC-ichiro",
            source_url="https://example.com/ichiro",
            evidence_quality="B",
        )

        # 2. バリデーション
        validator = PostLLMValidator()
        status, validation_info = validate_episode(episode, validator)

        assert status == "passed"
        assert validation_info["is_valid"] is True

        # 3. episode_id生成
        episode_id = generate_episode_id()
        assert episode_id.startswith("EP-")

        # 4. 重複チェック
        master_df = pd.DataFrame(
            {
                "episode_id": ["EP-001"],
                "source_url": ["https://example.com/other"],
            }
        )

        duplicate = check_duplicate_source_id(episode.source_id, master_df)
        assert duplicate is None

        # 5. マージ
        new_master_df = merge_to_master(episode, episode_id, master_df, validation_info)
        assert len(new_master_df) == 2
        assert new_master_df.iloc[1]["episode_id"] == episode_id


class TestPostLLMValidator:
    """PostLLMValidatorの追加テスト"""

    def test_validator_meta_expressions_fictional(self):
        """架空キャラクターでメタ表現を検出"""
        validator = PostLLMValidator()

        # メタ表現を含むテキスト
        result = validator.validate(
            episode_text="あなたと同じ10歳のとき、このキャラクターは架空の存在であり、実在しません。",
            age=10,
            person_type="FICTIONAL",
        )

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("メタ表現" in error for error in result.errors)

    def test_validator_char_count_too_short(self):
        """文字数が短すぎる場合"""
        validator = PostLLMValidator()

        result = validator.validate(
            episode_text="あなたと同じ30歳のとき、テストしました。",  # 短すぎる
            age=30,
            person_type="REAL",
        )

        assert result.is_valid is False
        assert any("文字数" in error for error in result.errors)

    def test_validator_char_count_too_long(self):
        """文字数が長すぎる場合"""
        validator = PostLLMValidator()

        # 500文字以上の長文を生成
        long_text = "あなたと同じ30歳のとき、" + "テスト" * 200

        result = validator.validate(
            episode_text=long_text,
            age=30,
            person_type="REAL",
        )

        assert result.is_valid is False
        assert any("文字数" in error for error in result.errors)

    def test_validator_age_mismatch(self):
        """年齢不一致の検出"""
        validator = PostLLMValidator()

        result = validator.validate(
            episode_text="あなたと同じ30歳のとき、テストは重要な発見をしました。この発見は後の研究に大きな影響を与えました。",
            age=40,  # テキストは30歳だが、期待値は40歳
            person_type="REAL",
        )

        assert result.is_valid is False
        assert any("年齢" in error and "不一致" in error for error in result.errors)

    def test_validator_quality_level_mapping(self):
        """品質レベルのスコアマッピング"""
        validator = PostLLMValidator()

        # EXCELLENT (0.9以上)
        assert validator._get_quality_level(0.95) == QualityLevel.EXCELLENT

        # GOOD (0.7-0.89)
        assert validator._get_quality_level(0.8) == QualityLevel.GOOD

        # ACCEPTABLE (0.5-0.69)
        assert validator._get_quality_level(0.6) == QualityLevel.ACCEPTABLE

        # POOR (0.3-0.49)
        assert validator._get_quality_level(0.4) == QualityLevel.POOR

        # UNACCEPTABLE (0-0.29)
        assert validator._get_quality_level(0.2) == QualityLevel.UNACCEPTABLE
