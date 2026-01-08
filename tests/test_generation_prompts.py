#!/usr/bin/env python3
"""
生成プロンプト品質テスト

バッチ生成プロンプトが丁寧語・私は禁止ルールを含んでいることを検証。
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sage.prompts.category_prompts import (
    SYSTEM_PROMPT_TEMPLATE,
    get_system_prompt,
)
from scripts.generate.mass_production.generator import (
    GenerationInput,
    PromptBuilder,
)


class TestSystemPrompt:
    """システムプロンプトのテスト"""

    def test_system_prompt_contains_polite_form_instruction(self):
        """システムプロンプトに丁寧語指示が含まれること"""
        assert "丁寧語" in SYSTEM_PROMPT_TEMPLATE
        assert "です・ます調" in SYSTEM_PROMPT_TEMPLATE

    def test_system_prompt_contains_polite_examples(self):
        """システムプロンプトに丁寧語の例が含まれること"""
        assert "しました" in SYSTEM_PROMPT_TEMPLATE
        assert "でした" in SYSTEM_PROMPT_TEMPLATE
        assert "です" in SYSTEM_PROMPT_TEMPLATE
        assert "ます" in SYSTEM_PROMPT_TEMPLATE

    def test_system_prompt_prohibits_watashi(self):
        """システムプロンプトに「私は」禁止が含まれること"""
        assert "私は" in SYSTEM_PROMPT_TEMPLATE
        assert "私の" in SYSTEM_PROMPT_TEMPLATE
        assert "私が" in SYSTEM_PROMPT_TEMPLATE
        assert "絶対に使用しない" in SYSTEM_PROMPT_TEMPLATE

    def test_system_prompt_prohibits_plain_form(self):
        """システムプロンプトに常体禁止が含まれること"""
        assert "常体" in SYSTEM_PROMPT_TEMPLATE
        assert "だ・である調" in SYSTEM_PROMPT_TEMPLATE

    def test_get_system_prompt_formats_correctly(self):
        """get_system_prompt()が正しくフォーマットすること"""
        result = get_system_prompt("田中太郎", 30)

        assert "田中太郎" in result
        assert "30" in result
        assert "{person_name}" not in result
        assert "{age}" not in result

    def test_get_system_prompt_contains_opening_rule(self):
        """システムプロンプトに冒頭ルールが含まれること"""
        result = get_system_prompt("山田花子", 25)

        assert "あなたと同じ25歳のとき、山田花子は" in result


class TestPromptBuilder:
    """PromptBuilderのテスト"""

    def setup_method(self):
        """各テストの前に実行"""
        self.builder = PromptBuilder()

    def test_writing_rules_contains_polite_form(self):
        """WRITING_RULESに丁寧語ルールが含まれること"""
        assert "丁寧語" in PromptBuilder.WRITING_RULES
        assert "です・ます調" in PromptBuilder.WRITING_RULES

    def test_writing_rules_prohibits_watashi(self):
        """WRITING_RULESに私は禁止ルールが含まれること"""
        assert "私は" in PromptBuilder.WRITING_RULES
        assert "私の" in PromptBuilder.WRITING_RULES
        assert "私が" in PromptBuilder.WRITING_RULES

    def test_writing_rules_prohibits_plain_endings(self):
        """WRITING_RULESに常体文末禁止が含まれること"""
        assert "〜だ。" in PromptBuilder.WRITING_RULES
        assert "〜である。" in PromptBuilder.WRITING_RULES
        assert "常体禁止" in PromptBuilder.WRITING_RULES

    def test_build_includes_writing_rules(self):
        """build()が文体ルールを含むこと"""
        input_data = GenerationInput(
            person_id="P001",
            person_name="テスト太郎",
            age=30,
            category="科学・技術",
        )

        prompt = self.builder.build(input_data)

        assert "丁寧語" in prompt
        assert "私は" in prompt  # 禁止ルールとして含まれる
        assert "テスト太郎は" in prompt  # 主語指示

    def test_build_includes_opening_format(self):
        """build()が冒頭フォーマットを含むこと"""
        input_data = GenerationInput(
            person_id="P001",
            person_name="山田花子",
            age=25,
            category="芸術・文化",
        )

        prompt = self.builder.build(input_data)

        assert "あなたと同じ25歳のとき、山田花子は" in prompt

    def test_build_prohibits_plain_endings(self):
        """build()が常体文末禁止を含むこと"""
        input_data = GenerationInput(
            person_id="P001",
            person_name="鈴木一郎",
            age=35,
            category="スポーツ",
        )

        prompt = self.builder.build(input_data)

        assert "〜だ。" in prompt or "常体" in prompt

    def test_build_requires_polite_endings(self):
        """build()が丁寧語文末を要求すること"""
        input_data = GenerationInput(
            person_id="P001",
            person_name="佐藤次郎",
            age=40,
            category="政治・経済",
        )

        prompt = self.builder.build(input_data)

        # 丁寧語文末の要求
        assert "です" in prompt or "ます" in prompt or "でした" in prompt or "ました" in prompt


class TestStylesTone:
    """STYLESトーンのテスト"""

    def test_factual_style_includes_polite(self):
        """factualスタイルが丁寧語を含むこと"""
        style = PromptBuilder.STYLES["factual"]
        assert "丁寧語" in style["tone"]

    def test_narrative_style_includes_polite(self):
        """narrativeスタイルが丁寧語を含むこと"""
        style = PromptBuilder.STYLES["narrative"]
        assert "丁寧語" in style["tone"] or "丁寧語" in style["instruction"]

    def test_inspirational_style_includes_polite(self):
        """inspirationalスタイルが丁寧語を含むこと"""
        style = PromptBuilder.STYLES["inspirational"]
        assert "丁寧語" in style["tone"] or "丁寧語" in style["instruction"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
