#!/usr/bin/env python3
"""playwright_mcp_examples テスト"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from playwright_mcp_examples import BrowserAction, PlaywrightMCPExamples


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
