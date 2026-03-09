"""
tests/test_episode_generator.py - episode_generator.py ユニットテスト
"""

from unittest.mock import MagicMock, patch

import pytest


class TestAgePrompts:
    """AGE_PROMPTS定数テスト"""

    def test_age_prompts_exists(self):
        """AGE_PROMPTSが定義されている"""
        from src.episode_generator import AGE_PROMPTS

        assert AGE_PROMPTS is not None
        assert isinstance(AGE_PROMPTS, dict)

    def test_age_prompts_keys(self):
        """AGE_PROMPTSに必要なキーがある"""
        from src.episode_generator import AGE_PROMPTS

        expected_keys = ["30s", "40s", "50s", "60s", "70s", "80s", "90s"]
        for key in expected_keys:
            assert key in AGE_PROMPTS

    def test_age_prompt_structure(self):
        """AGE_PROMPTSの各エントリに必要なフィールドがある"""
        from src.episode_generator import AGE_PROMPTS

        for key, value in AGE_PROMPTS.items():
            assert "life_stage_tag" in value
            assert "description" in value
            assert "themes" in value


class TestEpisodeGeneratorInit:
    """EpisodeGenerator初期化テスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_init_with_api_key(self, mock_anthropic):
        """APIキーで初期化"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test-key")

        assert generator.model == "claude-sonnet-4-5"
        mock_anthropic.assert_called_once_with(api_key="test-key")

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_init_custom_model(self, mock_anthropic):
        """カスタムモデルで初期化"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test-key", model="claude-opus-4")

        assert generator.model == "claude-opus-4"


class TestGetAgeRangeKey:
    """_get_age_range_keyメソッドテスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_age_30s(self, mock_anthropic):
        """30代の年代キー"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_age_range_key(30) == "30s"
        assert generator._get_age_range_key(35) == "30s"
        assert generator._get_age_range_key(39) == "30s"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_age_40s(self, mock_anthropic):
        """40代の年代キー"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_age_range_key(40) == "40s"
        assert generator._get_age_range_key(49) == "40s"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_age_90s(self, mock_anthropic):
        """90代以上の年代キー"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_age_range_key(90) == "90s"
        assert generator._get_age_range_key(100) == "90s"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_age_default(self, mock_anthropic):
        """範囲外の年齢はデフォルト"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_age_range_key(20) == "70s"  # デフォルト


class TestGetNendai:
    """_get_nendaiメソッドテスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_nendai_10s(self, mock_anthropic):
        """10代"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_nendai(15) == "10代"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_nendai_20s(self, mock_anthropic):
        """20代"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_nendai(25) == "20代"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_nendai_60plus(self, mock_anthropic):
        """60歳以上"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_nendai(65) == "60歳以上"
        assert generator._get_nendai(80) == "60歳以上"


class TestDetermineAwardLevel:
    """_determine_award_levelメソッドテスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_nobel(self, mock_anthropic):
        """ノーベル賞"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._determine_award_level("ノーベル物理学賞") == "NOBEL"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_international_top(self, mock_anthropic):
        """国際トップ賞"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._determine_award_level("フィールズ賞") == "INTERNATIONAL_TOP"
        assert generator._determine_award_level("チューリング賞") == "INTERNATIONAL_TOP"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_international(self, mock_anthropic):
        """国際賞"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._determine_award_level("アカデミー賞") == "INTERNATIONAL"
        assert generator._determine_award_level("文化勲章") == "INTERNATIONAL"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_national(self, mock_anthropic):
        """国民栄誉賞"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._determine_award_level("国民栄誉賞") == "NATIONAL"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_award(self, mock_anthropic):
        """その他の賞"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._determine_award_level("芥川賞") == "AWARD"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_no_award(self, mock_anthropic):
        """賞なし"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._determine_award_level(None) == ""


class TestGeneratePersonId:
    """_generate_person_idメソッドテスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_generate_person_id_format(self, mock_anthropic):
        """person_idのフォーマット"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        person_id = generator._generate_person_id("山中伸弥")

        assert person_id.startswith("P")
        assert len(person_id) == 8  # P + 7文字

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_generate_person_id_deterministic(self, mock_anthropic):
        """同じ名前から同じIDが生成される"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        id1 = generator._generate_person_id("山中伸弥")
        id2 = generator._generate_person_id("山中伸弥")

        assert id1 == id2

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_generate_person_id_different(self, mock_anthropic):
        """異なる名前から異なるIDが生成される"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        id1 = generator._generate_person_id("山中伸弥")
        id2 = generator._generate_person_id("大谷翔平")

        assert id1 != id2


class TestGeneratePrompt:
    """generate_promptメソッドテスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_prompt_contains_person_name(self, mock_anthropic):
        """プロンプトに人物名が含まれる"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        prompt = generator.generate_prompt(person_name="山中伸弥", category="科学・技術", age=47)

        assert "山中伸弥" in prompt

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_prompt_contains_age(self, mock_anthropic):
        """プロンプトに年齢が含まれる"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        prompt = generator.generate_prompt(person_name="山中伸弥", category="科学・技術", age=47)

        assert "47歳" in prompt

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_prompt_with_award(self, mock_anthropic):
        """業績付きプロンプト"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        prompt = generator.generate_prompt(
            person_name="山中伸弥",
            category="科学・技術",
            age=47,
            award_name="iPS細胞発見",
            award_year="2007",
        )

        assert "iPS細胞発見" in prompt
        assert "2007" in prompt

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_prompt_excludes_posthumous_award(self, mock_anthropic):
        """死後の業績年は含めない"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        prompt = generator.generate_prompt(
            person_name="テスト人物",
            category="文化・芸術",
            age=50,
            award_name="テスト賞",
            award_year="2020",
            death_year=2015,  # 2020年は死後
        )

        # 業績名は含まれるが、死後の年は含まれない
        assert "テスト賞" in prompt
        assert "2020年" not in prompt


class TestCalculateScores:
    """calculate_scoresメソッドテスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_scores_structure(self, mock_anthropic):
        """スコア辞書の構造"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        scores = generator.calculate_scores("これはテストエピソードです。" * 10)

        assert "memorability_score" in scores
        assert "empathy_score" in scores
        assert "composite_score" in scores

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_short_text_penalty(self, mock_anthropic):
        """短いテキストにはペナルティ"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        short_scores = generator.calculate_scores("短い")  # 150文字未満
        long_scores = generator.calculate_scores("長いエピソード" * 50)  # 200文字以上

        assert short_scores["memorability_score"] < long_scores["memorability_score"]

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_long_text_bonus(self, mock_anthropic):
        """長いテキストにはボーナス"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        normal_scores = generator.calculate_scores("通常の長さ" * 30)  # 約150-300文字
        long_scores = generator.calculate_scores("とても長いエピソード" * 50)  # 300文字以上

        assert long_scores["memorability_score"] >= normal_scores["memorability_score"]


class TestCallAnthropicAPI:
    """call_anthropic_apiメソッドテスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_api_call(self, mock_anthropic):
        """API呼び出し"""
        from src.episode_generator import EpisodeGenerator

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_text_block = MagicMock()
        mock_text_block.text = "Generated episode text"
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_client.messages.create.return_value = mock_response

        generator = EpisodeGenerator(api_key="test")
        result = generator.call_anthropic_api("Test prompt")

        assert result == "Generated episode text"
        mock_client.messages.create.assert_called_once()


class TestGenerate:
    """generateメソッドテスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_generate_missing_field(self, mock_anthropic):
        """必須フィールド不足でエラー"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")

        with pytest.raises(KeyError, match="person_name"):
            generator.generate(person_data={"category": "科学・技術", "person_type": "REAL"}, age=47)

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_generate_success(self, mock_anthropic):
        """正常なエピソード生成"""
        from src.episode_generator import EpisodeGenerator

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_text_block = MagicMock()
        mock_text_block.text = "あなたと同じ47歳のとき、山中伸弥はiPS細胞を発見しました。"
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_client.messages.create.return_value = mock_response

        generator = EpisodeGenerator(api_key="test")
        episode = generator.generate(
            person_data={
                "person_name": "山中伸弥",
                "category": "科学・技術",
                "person_type": "REAL",
            },
            age=47,
        )

        assert episode["person_name"] == "山中伸弥"
        assert episode["age"] == 47
        assert episode["category"] == "科学・技術"
        assert "episode_text" in episode
        assert episode["person_id"].startswith("P")


# ============================================================================
# Phase 4: 未カバー行を網羅するテスト追加
# ============================================================================


class TestAwardYearValueError:
    """award_year が数値でない場合の ValueError テスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_invalid_award_year_passes_gracefully(self, mock_anthropic):
        """award_year='invalid' で ValueError が発生しても pass される（L108-109）"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        prompt = generator.generate_prompt(
            person_name="テスト人物",
            category="テスト",
            age=50,
            award_name="テスト賞",
            award_year="invalid_year",
            death_year=2020,
        )
        # award_year が数値でないため ValueError → pass → award_year が含まれる
        assert "テスト賞" in prompt
        assert "invalid_year" in prompt


class TestGetAgeRangeKey60s70s80s:
    """_get_age_range_key 60s/70s/80s テスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_age_60s(self, mock_anthropic):
        """60代の年代キー（L333）"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_age_range_key(60) == "60s"
        assert generator._get_age_range_key(65) == "60s"
        assert generator._get_age_range_key(69) == "60s"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_age_70s(self, mock_anthropic):
        """70代の年代キー（L335）"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_age_range_key(70) == "70s"
        assert generator._get_age_range_key(75) == "70s"
        assert generator._get_age_range_key(79) == "70s"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_age_80s(self, mock_anthropic):
        """80代の年代キー（L337）"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_age_range_key(80) == "80s"
        assert generator._get_age_range_key(85) == "80s"
        assert generator._get_age_range_key(89) == "80s"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_age_50s(self, mock_anthropic):
        """50代の年代キー"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_age_range_key(50) == "50s"
        assert generator._get_age_range_key(59) == "50s"


class TestGetNendai30s50s:
    """_get_nendai 30代/50代 テスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_nendai_30s(self, mock_anthropic):
        """30代（L350）"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_nendai(30) == "30代"
        assert generator._get_nendai(35) == "30代"
        assert generator._get_nendai(39) == "30代"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_nendai_40s(self, mock_anthropic):
        """40代"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_nendai(40) == "40代"
        assert generator._get_nendai(49) == "40代"

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_nendai_50s(self, mock_anthropic):
        """50代（L354）"""
        from src.episode_generator import EpisodeGenerator

        generator = EpisodeGenerator(api_key="test")
        assert generator._get_nendai(50) == "50代"
        assert generator._get_nendai(55) == "50代"
        assert generator._get_nendai(59) == "50代"


class TestEpisodeTextNameResubstitution:
    """episode_text の re.sub 名前修正テスト"""

    @patch("src.episode_generator.anthropic.Anthropic")
    def test_name_mismatch_auto_correction(self, mock_anthropic):
        """名前不一致時に自動修正される（L263）"""
        from src.episode_generator import EpisodeGenerator

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # LLMが間違った名前を返す
        mock_text_block = MagicMock()
        mock_text_block.text = "あなたと同じ47歳のとき、ヤマナカシンヤは研究を始めました。"
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_client.messages.create.return_value = mock_response

        generator = EpisodeGenerator(api_key="test")

        # validate_episode_name をモックして MISMATCH を返す
        with patch("src.validators.episode_name_validator.validate_episode_name") as mock_validate:
            from src.validators.episode_name_validator import ValidationResult

            mock_result = MagicMock()
            mock_result.result = ValidationResult.MISMATCH
            mock_result.text_name = "ヤマナカシンヤ"
            mock_validate.return_value = mock_result

            episode = generator.generate(
                person_data={
                    "person_name": "山中伸弥",
                    "category": "科学・技術",
                    "person_type": "REAL",
                },
                age=47,
            )
            assert episode["person_name"] == "山中伸弥"
