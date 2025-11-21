#!/usr/bin/env python3
"""superclaude_project_config テスト"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from superclaude_project_config import ProjectConfig


class TestProjectConfig:
    """ProjectConfigのテスト"""

    def test_init_minimal(self):
        """最小構成の初期化"""
        config = ProjectConfig(project_name="test_project", project_path="/path/to/project")
        assert config.project_name == "test_project"
        assert config.project_path == "/path/to/project"

    def test_default_flags(self):
        """デフォルトフラグ"""
        config = ProjectConfig(project_name="test", project_path="/path")
        assert config.default_flags == []
        assert config.disabled_flags == []

    def test_default_performance(self):
        """デフォルトパフォーマンス設定"""
        config = ProjectConfig(project_name="test", project_path="/path")
        assert config.max_parallel_tasks == 10
        assert config.token_limit == 100000
        assert config.auto_token_efficiency is True

    def test_default_automation(self):
        """デフォルト自動化設定"""
        config = ProjectConfig(project_name="test", project_path="/path")
        assert config.auto_sync is True
        assert config.auto_test is True
        assert config.auto_commit is False
        assert config.auto_format is True

    def test_with_mcp_servers(self):
        """MCPサーバー設定付き"""
        config = ProjectConfig(
            project_name="test",
            project_path="/path",
            enabled_mcp_servers=["context7", "serena"],
            disabled_mcp_servers=["playwright"],
        )
        assert len(config.enabled_mcp_servers) == 2
        assert len(config.disabled_mcp_servers) == 1

    def test_with_code_style(self):
        """コードスタイル設定付き"""
        config = ProjectConfig(
            project_name="test",
            project_path="/path",
            code_style={"indent": 4, "quotes": "double"},
            naming_conventions={"functions": "snake_case"},
        )
        assert config.code_style["indent"] == 4
        assert config.naming_conventions["functions"] == "snake_case"

    def test_default_mode(self):
        """デフォルトモード設定"""
        config = ProjectConfig(project_name="test", project_path="/path", default_mode="orchestrate")
        assert config.default_mode == "orchestrate"
