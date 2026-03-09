#!/usr/bin/env python3
"""
PostLLMValidator テストスイート
"""

import pytest

from src.validators.post_llm_validator import (
    PostLLMValidator,
    QualityLevel,
    ValidationResult,
)


class TestPostLLMValidatorInit:
    """初期化テスト"""

    def test_init(self):
        """初期化が正常に完了する"""
        validator = PostLLMValidator()
        assert validator is not None
        assert validator.MIN_CHARS == 100
        assert validator.MAX_CHARS == 500


class TestValidateEmptyInput:
    """空入力テスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_empty_string(self):
        """空文字列でUNACCEPTABLEを返す"""
        result = self.validator.validate("")
        assert not result.is_valid
        assert result.quality_score == 0.0
        assert result.quality_level == QualityLevel.UNACCEPTABLE
        assert "エピソードテキストが空です" in result.errors
        assert result.retryable

    def test_none_input(self):
        """Noneでエラー"""
        result = self.validator.validate(None)  # type: ignore[arg-type]
        assert not result.is_valid
        assert result.quality_score == 0.0

    def test_whitespace_only(self):
        """空白のみでUNACCEPTABLEを返す"""
        result = self.validator.validate("   \n\t  ")
        assert not result.is_valid
        assert result.quality_level == QualityLevel.UNACCEPTABLE


class TestLeadFormatValidation:
    """リード文フォーマット検証テスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_valid_lead_format(self):
        """正しいリード文フォーマットでエラーなし"""
        text = "あなたと同じ25歳のとき、" + "テスト" * 50
        result = self.validator.validate(text, age=25)
        assert "リード文" not in str(result.errors)

    def test_invalid_lead_format_missing(self):
        """リード文が無い場合にエラー"""
        text = "彼は25歳のとき、アルバムをリリースしました。" + "テスト" * 30
        result = self.validator.validate(text, age=25)
        assert any("リード文" in e for e in result.errors)

    def test_age_mismatch(self):
        """年齢不一致でエラー"""
        text = "あなたと同じ30歳のとき、" + "テスト" * 50
        result = self.validator.validate(text, age=25)
        assert any("不一致" in e for e in result.errors)

    def test_age_none_accepted(self):
        """年齢がNoneの場合は不一致チェックをスキップ"""
        text = "あなたと同じ25歳のとき、" + "テスト" * 50
        result = self.validator.validate(text, age=None)
        assert not any("不一致" in e for e in result.errors)


class TestMetaExpressionDetection:
    """メタ表現検出テスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    @pytest.mark.parametrize(
        "meta_word",
        [
            "架空の",
            "フィクション",
            "設定上",
            "作品内では",
            "公式な描写は存在しません",
            "実在しない",
            "申し訳ございませんが",
            "キャラクターです",
            "存在しません",
            "描かれていません",
            "物語の中で",
            "作品世界",
            "著作権の関係",
        ],
    )
    def test_meta_expression_detected_for_fictional(self, meta_word):
        """FICTIONALタイプでメタ表現が検出される"""
        text = f"あなたと同じ20歳のとき、これは{meta_word}に関する内容です。" + "テスト" * 30
        result = self.validator.validate(text, age=20, person_type="FICTIONAL")
        assert any("メタ表現" in e for e in result.errors)

    def test_meta_expression_not_checked_for_real(self):
        """REALタイプではメタ表現チェックをスキップ"""
        text = "あなたと同じ20歳のとき、これは架空の話ではありません。" + "テスト" * 30
        result = self.validator.validate(text, age=20, person_type="REAL")
        assert not any("メタ表現" in e for e in result.errors)

    def test_multiple_meta_expressions(self):
        """複数のメタ表現で複数のエラー"""
        text = "あなたと同じ20歳のとき、架空のフィクション作品世界。" + "テスト" * 30
        result = self.validator.validate(text, age=20, person_type="FICTIONAL")
        meta_errors = [e for e in result.errors if "メタ表現" in e]
        assert len(meta_errors) >= 2


class TestCharCountValidation:
    """文字数バリデーションテスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_below_min_chars(self):
        """最低文字数未満でエラー"""
        text = "あなたと同じ25歳のとき、短い。"  # 約20文字
        result = self.validator.validate(text, age=25)
        assert any("少なすぎ" in e for e in result.errors)

    def test_above_max_chars(self):
        """最大文字数超過でエラー"""
        text = "あなたと同じ25歳のとき、" + "長い文章" * 150  # 約600文字
        result = self.validator.validate(text, age=25)
        assert any("多すぎ" in e for e in result.errors)

    def test_below_recommended_min(self):
        """推奨最低文字数未満で警告"""
        # MIN_CHARS(100) < 文字数 < RECOMMENDED_MIN(150) の範囲
        # 約120文字の文字列を作成
        text = "あなたと同じ25歳のとき、彼は新しいプロジェクトを開始しました。このプロジェクトは成功を収め、多くの人々に影響を与えました。彼の努力が実を結んだ瞬間でした。さらに彼は挑戦を続け、新たな分野へと進出しました。"
        result = self.validator.validate(text, age=25)
        assert any("やや少なめ" in w for w in result.warnings)

    def test_above_recommended_max(self):
        """推奨最大文字数超過で警告"""
        text = "あなたと同じ25歳のとき、" + "テスト" * 100  # 約320文字
        result = self.validator.validate(text, age=25)
        assert any("やや多め" in w for w in result.warnings)

    def test_within_recommended_range(self):
        """推奨範囲内で警告なし"""
        text = "あなたと同じ25歳のとき、" + "テスト" * 60  # 約200文字
        result = self.validator.validate(text, age=25)
        char_warnings = [w for w in result.warnings if "文字" in w]
        assert len(char_warnings) == 0


class TestQualityScoring:
    """品質スコアリングテスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_excellent_quality(self):
        """完璧なエピソードでEXCELLENT"""
        text = "あなたと同じ25歳のとき、" + "良いエピソード内容です。" * 15
        result = self.validator.validate(text, age=25, person_type="REAL")
        assert result.quality_level == QualityLevel.EXCELLENT
        assert result.quality_score >= 0.9

    def test_score_deduction_for_lead_error(self):
        """リード文エラーで0.3減点"""
        text = "彼が25歳のとき、" + "テスト" * 60
        result = self.validator.validate(text, age=25)
        assert result.quality_score <= 0.7

    def test_score_deduction_for_meta_expression(self):
        """メタ表現で0.2減点"""
        text = "あなたと同じ25歳のとき、架空の話ではない内容。" + "テスト" * 50
        result = self.validator.validate(text, age=25, person_type="FICTIONAL")
        assert result.quality_score <= 0.8

    def test_score_min_zero(self):
        """スコアは0未満にならない"""
        text = "架空のフィクション設定上作品内では" + "存在しません" * 10
        result = self.validator.validate(text, age=25, person_type="FICTIONAL")
        assert result.quality_score >= 0.0


class TestQualityLevelMapping:
    """品質レベルマッピングテスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_quality_level_excellent(self):
        """90%以上でEXCELLENT"""
        level = self.validator._get_quality_level(0.95)
        assert level == QualityLevel.EXCELLENT

    def test_quality_level_good(self):
        """70-89%でGOOD"""
        level = self.validator._get_quality_level(0.75)
        assert level == QualityLevel.GOOD

    def test_quality_level_acceptable(self):
        """50-69%でACCEPTABLE"""
        level = self.validator._get_quality_level(0.55)
        assert level == QualityLevel.ACCEPTABLE

    def test_quality_level_poor(self):
        """30-49%でPOOR"""
        level = self.validator._get_quality_level(0.35)
        assert level == QualityLevel.POOR

    def test_quality_level_unacceptable(self):
        """30%未満でUNACCEPTABLE"""
        level = self.validator._get_quality_level(0.2)
        assert level == QualityLevel.UNACCEPTABLE


class TestRetryLogic:
    """リトライロジックテスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_retryable_when_errors_exist(self):
        """エラーがある場合にretryable"""
        text = "短い"  # エラーを発生させる
        result = self.validator.validate(text)
        assert result.retryable

    def test_not_retryable_when_excellent(self):
        """EXCELLENTの場合はretryableでない"""
        text = "あなたと同じ25歳のとき、" + "良いエピソード内容。" * 15
        result = self.validator.validate(text, age=25)
        assert not result.retryable or result.quality_score >= 0.9

    def test_retry_hints_provided(self):
        """エラー時にリトライヒントが提供される"""
        text = "短い"
        result = self.validator.validate(text)
        assert len(result.retry_hints) > 0


class TestRetryPromptGeneration:
    """リトライプロンプト生成テスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_generate_retry_prompt_when_retryable(self):
        """retryable時にプロンプトが強化される"""
        text = "短い"
        result = self.validator.validate(text)
        original = "元のプロンプト"
        enhanced = self.validator.generate_retry_prompt(result, original)
        assert "重要な修正指示" in enhanced
        assert "禁止事項" in enhanced

    def test_no_enhancement_when_not_retryable(self):
        """retryableでない時は元のプロンプトを返す"""
        text = "あなたと同じ25歳のとき、" + "良いエピソード内容。" * 15
        result = self.validator.validate(text, age=25)
        if not result.retryable:
            original = "元のプロンプト"
            enhanced = self.validator.generate_retry_prompt(result, original)
            assert enhanced == original


class TestValidationResultDataclass:
    """ValidationResultデータクラステスト"""

    def test_validation_result_fields(self):
        """ValidationResultが正しいフィールドを持つ"""
        result = ValidationResult(
            is_valid=True,
            quality_score=0.9,
            quality_level=QualityLevel.EXCELLENT,
            errors=[],
            warnings=[],
            retryable=False,
            retry_hints=[],
        )
        assert result.is_valid
        assert result.quality_score == 0.9
        assert result.quality_level == QualityLevel.EXCELLENT


class TestIntegration:
    """統合テスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_real_person_valid_episode(self):
        """実在人物の有効なエピソード"""
        text = "あなたと同じ30歳のとき、彼はバンドを結成し、初のアルバムをリリースしました。このアルバムは後に彼の代表作となり、多くのファンを獲得するきっかけとなりました。音楽活動を本格化させ、国内ツアーを成功させました。"
        result = self.validator.validate(text, age=30, person_type="REAL")
        assert result.is_valid
        assert result.quality_score >= 0.7

    def test_fictional_character_valid_episode(self):
        """架空人物の有効なエピソード"""
        text = "あなたと同じ16歳のとき、悟空は亀仙人の元で修行を開始しました。かめはめ波の習得に挑み、武天老師から戦いの基礎を学びました。天下一武道会への出場を目指し、日々厳しい訓練に励みました。その結果、彼は大きく成長し、仲間たちとの絆も深まりました。"
        result = self.validator.validate(text, age=16, person_type="FICTIONAL")
        assert result.is_valid
        assert result.quality_score >= 0.7

    def test_fictional_with_meta_expression_invalid(self):
        """架空人物でメタ表現を含むと無効"""
        text = "あなたと同じ10歳のとき、このキャラクターは架空の存在であり、作品世界でのみ存在します。" + "テスト" * 30
        result = self.validator.validate(text, age=10, person_type="FICTIONAL")
        assert not result.is_valid
        assert len(result.errors) > 0


class TestFictionalWorkTitleCheck:
    """架空キャラ作品名チェックテスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_work_title_present_and_matching(self):
        """冒頭に正しい作品名がある場合はエラーなし"""
        text = "あなたと同じ16歳のとき、悟空『ドラゴンボール』は修行を開始しました。" + "テスト" * 40
        result = self.validator.validate(text, age=16, person_type="FICTIONAL", work_title="ドラゴンボール")
        # 作品名関連のエラーがないことを確認
        work_errors = [e for e in result.errors if "作品名" in e or "FICTIONAL" in e]
        assert len(work_errors) == 0

    def test_work_title_missing(self):
        """冒頭に作品名がない場合はエラー"""
        text = "あなたと同じ16歳のとき、悟空は修行を開始しました。" + "テスト" * 40
        result = self.validator.validate(text, age=16, person_type="FICTIONAL", work_title="ドラゴンボール")
        work_errors = [e for e in result.errors if "FICTIONAL" in e or "作品名" in e]
        assert len(work_errors) > 0

    def test_work_title_mismatch(self):
        """作品名はあるが期待と異なる場合はエラー"""
        text = "あなたと同じ16歳のとき、悟空『ONE PIECE』は修行を開始しました。" + "テスト" * 40
        result = self.validator.validate(text, age=16, person_type="FICTIONAL", work_title="ドラゴンボール")
        work_errors = [e for e in result.errors if "作品名" in e]
        assert len(work_errors) > 0

    def test_no_work_title_check_when_empty(self):
        """work_titleが空の場合は作品名チェックをスキップ"""
        text = "あなたと同じ16歳のとき、悟空は修行を開始しました。" + "テスト" * 40
        result = self.validator.validate(text, age=16, person_type="FICTIONAL", work_title="")
        work_errors = [e for e in result.errors if "FICTIONAL" in e or "作品名" in e]
        assert len(work_errors) == 0

    def test_no_work_title_check_for_real(self):
        """REALタイプでは作品名チェックを行わない"""
        text = "あなたと同じ30歳のとき、彼は新しいプロジェクトを開始しました。" + "テスト" * 40
        result = self.validator.validate(text, age=30, person_type="REAL", work_title="テスト作品")
        work_errors = [e for e in result.errors if "FICTIONAL" in e or "作品名" in e]
        assert len(work_errors) == 0


class TestEarlyChildhoodQualityCheck:
    """1-5歳エピソード品質チェックテスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_forbidden_pattern_detected(self):
        """幼児には不可能な行動が検出される"""
        text = "あなたと同じ3歳のとき、彼は論文を発表した。" + "テスト" * 30
        result = self.validator.validate(text, age=3, person_type="REAL")
        early_errors = [e for e in result.errors if "幼児エピソード品質違反" in e]
        assert len(early_errors) > 0

    def test_subjective_expression_detected(self):
        """検証不可能な主観表現が検出される"""
        text = "あなたと同じ2歳のとき、彼は情熱を秘めていた才能の片鱗を見せた。" + "テスト" * 30
        result = self.validator.validate(text, age=2, person_type="REAL")
        early_errors = [e for e in result.errors if "幼児エピソード品質違反" in e]
        assert len(early_errors) > 0

    def test_recommended_pattern_warning_when_missing(self):
        """推奨パターンがない場合に警告"""
        # 推奨パターンを一切含まないテキスト
        text = "あなたと同じ4歳のとき、彼は明るい性格だった。" + "テスト" * 30
        result = self.validator.validate(text, age=4, person_type="REAL")
        early_warnings = [w for w in result.warnings if "第三者視点" in w]
        assert len(early_warnings) > 0

    def test_no_warning_with_recommended_pattern(self):
        """推奨パターンがある場合は第三者視点警告なし"""
        text = "あなたと同じ3歳のとき、伝記によると彼は音楽に興味を示したとされている。" + "テスト" * 30
        result = self.validator.validate(text, age=3, person_type="REAL")
        early_warnings = [w for w in result.warnings if "第三者視点" in w]
        assert len(early_warnings) == 0

    def test_no_check_for_age_6(self):
        """6歳以上では幼児品質チェックを行わない"""
        text = "あなたと同じ6歳のとき、彼は論文を執筆した。" + "テスト" * 30
        result = self.validator.validate(text, age=6, person_type="REAL")
        early_errors = [e for e in result.errors if "幼児エピソード品質違反" in e]
        assert len(early_errors) == 0

    def test_no_check_when_age_is_none(self):
        """ageがNoneの場合は幼児品質チェックを行わない"""
        text = "あなたと同じ3歳のとき、彼は論文を発表した。" + "テスト" * 30
        result = self.validator.validate(text, age=None, person_type="REAL")
        early_errors = [e for e in result.errors if "幼児エピソード品質違反" in e]
        assert len(early_errors) == 0


class TestCheckFictionalWorkTitleDirect:
    """_check_fictional_work_title() メソッドの直接テスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_matching_title_returns_no_error(self):
        """正しい作品名がある場合はエラーなし"""
        text = "あなたと同じ16歳のとき、悟空『ドラゴンボール』は修行した。"
        result = self.validator._check_fictional_work_title(text, "ドラゴンボール")
        assert result["error"] is None

    def test_no_title_at_all(self):
        """作品名が全くない場合"""
        text = "あなたと同じ16歳のとき、悟空は修行した。"
        result = self.validator._check_fictional_work_title(text, "ドラゴンボール")
        assert result["error"] is not None
        assert "冒頭にありません" in result["error"]

    def test_different_title_present(self):
        """異なる作品名が含まれている場合"""
        text = "あなたと同じ16歳のとき、悟空『NARUTO』は修行した。"
        result = self.validator._check_fictional_work_title(text, "ドラゴンボール")
        assert result["error"] is not None
        assert "一致しません" in result["error"]


class TestCheckEarlyChildhoodQualityDirect:
    """_check_early_childhood_quality() メソッドの直接テスト"""

    def setup_method(self):
        self.validator = PostLLMValidator()

    def test_clean_text_returns_empty_errors(self):
        """問題のないテキストはエラーなし"""
        text = "伝記によると彼は3歳で初めて音楽に触れたとされている。"
        result = self.validator._check_early_childhood_quality(text, 3)
        assert len(result["errors"]) == 0

    def test_forbidden_action_detected(self):
        """禁止行動を含むテキストでエラー検出"""
        text = "3歳の頃、彼は論文を執筆した。"
        result = self.validator._check_early_childhood_quality(text, 3)
        assert len(result["errors"]) > 0

    def test_multiple_forbidden_patterns(self):
        """複数の禁止パターンが検出される"""
        text = "2歳で制作した作品を発表した。さらに情熱を秘めていた。"
        result = self.validator._check_early_childhood_quality(text, 2)
        assert len(result["errors"]) >= 2

    def test_missing_recommended_pattern_warns(self):
        """推奨パターンなしで警告"""
        text = "彼は3歳で明るく元気だった。"
        result = self.validator._check_early_childhood_quality(text, 3)
        assert len(result["warnings"]) > 0

    def test_has_recommended_pattern_no_warn(self):
        """推奨パターンありで警告なし"""
        text = "家族の証言によると彼は3歳で初めて声を上げた。"
        result = self.validator._check_early_childhood_quality(text, 3)
        assert len(result["warnings"]) == 0


class TestMainFunction:
    """main関数テスト（カバレッジ向上用）"""

    def test_main_function_execution(self, capsys):
        """main関数が正常に実行される"""
        from src.validators.post_llm_validator import main

        main()
        captured = capsys.readouterr()
        # main関数の出力を確認
        assert "=" * 60 in captured.out
        assert "テキスト:" in captured.out
        assert "有効:" in captured.out
        assert "スコア:" in captured.out
        assert "レベル:" in captured.out

    def test_main_function_test_cases(self, capsys):
        """main関数のテストケースが全て処理される"""
        from src.validators.post_llm_validator import main

        main()
        captured = capsys.readouterr()
        # 3つのテストケースが処理されることを確認
        assert captured.out.count("テキスト:") == 3

    def test_main_function_outputs_quality_indicators(self, capsys):
        """main関数が品質インジケータを出力する"""
        from src.validators.post_llm_validator import main

        main()
        captured = capsys.readouterr()
        # 有効/無効のインジケータが出力される
        assert "✅" in captured.out or "❌" in captured.out
