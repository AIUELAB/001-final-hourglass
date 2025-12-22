#!/usr/bin/env python3
"""playwright_mcp_examples テスト"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from playwright_mcp_examples import BrowserAction, PlaywrightMCPExamples, main


class TestBrowserAction:
    """BrowserActionのテスト"""

    def test_init(self):
        """初期化テスト"""
        action = BrowserAction(
            action_type="navigate",
            description="Navigate to URL",
            mcp_tool="playwright_navigate",
            parameters={"url": "https://example.com"},
        )
        assert action.action_type == "navigate"
        assert action.description == "Navigate to URL"
        assert action.mcp_tool == "playwright_navigate"
        assert action.parameters["url"] == "https://example.com"

    def test_click_action(self):
        """クリックアクション"""
        action = BrowserAction(
            action_type="click",
            description="Click button",
            mcp_tool="playwright_click",
            parameters={"selector": "#submit-btn"},
        )
        assert action.action_type == "click"
        assert action.parameters["selector"] == "#submit-btn"

    def test_type_action(self):
        """入力アクション"""
        action = BrowserAction(
            action_type="type",
            description="Type text",
            mcp_tool="browser_type",
            parameters={"text": "Hello", "selector": "#input"},
        )
        assert action.action_type == "type"
        assert action.parameters["text"] == "Hello"

    def test_empty_parameters(self):
        """空のパラメータ"""
        action = BrowserAction(
            action_type="snapshot",
            description="Get snapshot",
            mcp_tool="browser_snapshot",
            parameters={},
        )
        assert action.parameters == {}


class TestPlaywrightMCPExamples:
    """PlaywrightMCPExamplesのテスト"""

    def test_init(self):
        """初期化テスト"""
        examples = PlaywrightMCPExamples()
        assert examples.actions_log == []

    def test_constant(self):
        """定数テスト"""
        assert PlaywrightMCPExamples.MSG_GET_PAGE_STRUCTURE == "ページ構造を取得"

    def test_actions_log_empty(self):
        """空のアクションログ"""
        examples = PlaywrightMCPExamples()
        assert len(examples.actions_log) == 0

    @patch("playwright_mcp_examples.console")
    def test_show_available_tools(self, mock_console):
        """利用可能なツールを表示"""
        examples = PlaywrightMCPExamples()
        examples.show_available_tools()
        # console.print が呼ばれたことを確認（Tableオブジェクト）
        mock_console.print.assert_called_once()

    @patch("playwright_mcp_examples.console")
    def test_example_basic_navigation_returns_dict(self, mock_console):
        """基本ナビゲーション例が辞書を返す"""
        examples = PlaywrightMCPExamples()
        result = examples.example_basic_navigation()
        assert isinstance(result, dict)
        assert result["example"] == "basic_navigation"
        assert "actions" in result

    @patch("playwright_mcp_examples.console")
    def test_example_basic_navigation_actions_count(self, mock_console):
        """基本ナビゲーション例のアクション数"""
        examples = PlaywrightMCPExamples()
        result = examples.example_basic_navigation()
        assert result["actions"] == 3  # navigate, snapshot, screenshot

    @patch("playwright_mcp_examples.console")
    def test_example_form_interaction_returns_dict(self, mock_console):
        """フォーム操作例が辞書を返す"""
        examples = PlaywrightMCPExamples()
        result = examples.example_form_interaction()
        assert isinstance(result, dict)
        assert result["example"] == "form_interaction"
        assert "actions" in result

    @patch("playwright_mcp_examples.console")
    def test_example_form_interaction_actions_count(self, mock_console):
        """フォーム操作例のアクション数"""
        examples = PlaywrightMCPExamples()
        result = examples.example_form_interaction()
        assert result["actions"] == 6  # navigate, type x2, select, click, wait

    @patch("playwright_mcp_examples.console")
    def test_example_web_scraping_returns_dict(self, mock_console):
        """Webスクレイピング例が辞書を返す"""
        examples = PlaywrightMCPExamples()
        result = examples.example_web_scraping()
        assert isinstance(result, dict)
        assert result["example"] == "web_scraping"
        assert result["actions"] == 4  # navigate, snapshot, evaluate, screenshot

    @patch("playwright_mcp_examples.console")
    def test_example_multi_tab_operation_returns_dict(self, mock_console):
        """マルチタブ操作例が辞書を返す"""
        examples = PlaywrightMCPExamples()
        result = examples.example_multi_tab_operation()
        assert isinstance(result, dict)
        assert result["example"] == "multi_tab"
        assert result["actions"] == 6

    @patch("playwright_mcp_examples.console")
    def test_example_advanced_interaction_returns_dict(self, mock_console):
        """高度なインタラクション例が辞書を返す"""
        examples = PlaywrightMCPExamples()
        result = examples.example_advanced_interaction()
        assert isinstance(result, dict)
        assert result["example"] == "advanced_interaction"
        assert result["actions"] == 7

    @patch("playwright_mcp_examples.console")
    def test_display_actions_updates_log(self, mock_console):
        """_display_actionsがログを更新する"""
        examples = PlaywrightMCPExamples()
        actions = [
            BrowserAction(
                action_type="test",
                description="Test action",
                mcp_tool="test_tool",
                parameters={"key": "value"},
            )
        ]
        examples._display_actions(actions)
        assert len(examples.actions_log) == 1
        assert examples.actions_log[0].action_type == "test"

    @patch("playwright_mcp_examples.console")
    def test_display_actions_multiple_actions(self, mock_console):
        """_display_actionsが複数アクションを処理"""
        examples = PlaywrightMCPExamples()
        actions = [
            BrowserAction("a", "Action 1", "tool1", {}),
            BrowserAction("b", "Action 2", "tool2", {"x": 1}),
            BrowserAction("c", "Action 3", "tool3", {"y": 2, "z": 3}),
        ]
        examples._display_actions(actions)
        assert len(examples.actions_log) == 3

    @patch("playwright_mcp_examples.console")
    def test_display_actions_empty_parameters(self, mock_console):
        """_display_actionsが空パラメータを処理"""
        examples = PlaywrightMCPExamples()
        actions = [
            BrowserAction("test", "Empty params", "tool", {}),
        ]
        examples._display_actions(actions)
        # パラメータが空の場合は console.print が2回（description と tool）
        # パラメータがある場合は3回呼ばれる
        assert len(examples.actions_log) == 1

    @patch("playwright_mcp_examples.console")
    def test_show_usage_instructions(self, mock_console):
        """使用方法を表示"""
        examples = PlaywrightMCPExamples()
        examples.show_usage_instructions()
        mock_console.print.assert_called_once()

    @patch("playwright_mcp_examples.console")
    def test_actions_log_accumulates(self, mock_console):
        """アクションログが蓄積される"""
        examples = PlaywrightMCPExamples()
        examples.example_basic_navigation()
        count1 = len(examples.actions_log)
        examples.example_form_interaction()
        count2 = len(examples.actions_log)
        assert count2 > count1


class TestMain:
    """main関数のテスト"""

    @patch("playwright_mcp_examples.console")
    def test_main_executes_all_examples(self, mock_console):
        """main関数が全ての例を実行"""
        main()
        # console.print が複数回呼ばれることを確認
        assert mock_console.print.call_count > 0

    @patch("playwright_mcp_examples.console")
    def test_main_returns_none(self, mock_console):
        """main関数がNoneを返す"""
        result = main()
        assert result is None

    @patch("playwright_mcp_examples.PlaywrightMCPExamples")
    @patch("playwright_mcp_examples.console")
    def test_main_creates_examples_instance(self, mock_console, mock_class):
        """main関数がインスタンスを作成"""
        mock_instance = MagicMock()
        mock_instance.actions_log = []
        mock_class.return_value = mock_instance
        main()
        mock_class.assert_called_once()

    @patch("playwright_mcp_examples.PlaywrightMCPExamples")
    @patch("playwright_mcp_examples.console")
    def test_main_calls_all_methods(self, mock_console, mock_class):
        """main関数が全メソッドを呼び出す"""
        mock_instance = MagicMock()
        mock_instance.actions_log = []
        mock_class.return_value = mock_instance

        main()

        mock_instance.show_available_tools.assert_called_once()
        mock_instance.example_basic_navigation.assert_called_once()
        mock_instance.example_form_interaction.assert_called_once()
        mock_instance.example_web_scraping.assert_called_once()
        mock_instance.example_multi_tab_operation.assert_called_once()
        mock_instance.example_advanced_interaction.assert_called_once()
        mock_instance.show_usage_instructions.assert_called_once()
