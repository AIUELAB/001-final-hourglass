#!/usr/bin/env python3
"""superclaude_project_config テスト"""

import sys
from pathlib import Path


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

    def test_with_custom_rules(self):
        """カスタムルール設定"""
        config = ProjectConfig(
            project_name="test",
            project_path="/path",
            custom_rules=[{"rule": "no_console_log"}],
            validation_rules=["lint", "test"],
        )
        assert len(config.custom_rules) == 1
        assert len(config.validation_rules) == 2

    def test_with_env_vars(self):
        """環境変数設定"""
        config = ProjectConfig(
            project_name="test",
            project_path="/path",
            env_vars={"API_KEY": "secret", "DEBUG": "true"},
        )
        assert config.env_vars["API_KEY"] == "secret"

    def test_version(self):
        """バージョン設定"""
        config = ProjectConfig(project_name="test", project_path="/path")
        assert config.version == "1.0.0"


class TestProjectConfigManager:
    """ProjectConfigManagerのテスト"""

    def test_init(self):
        """初期化テスト"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            assert manager.global_config_dir.exists()

    def test_config_filenames(self):
        """設定ファイル名リスト"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            assert ".superclaude.json" in manager.CONFIG_FILENAMES
            assert ".superclaude.yaml" in manager.CONFIG_FILENAMES

    def test_projects_config_dir_creation(self):
        """プロジェクト設定ディレクトリ作成"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            assert (manager.global_config_dir / "projects").exists()

    def test_project_configs_cache(self):
        """プロジェクト設定キャッシュ"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            assert isinstance(manager.project_configs, dict)

    def test_current_project_init(self):
        """現在プロジェクト初期化"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            assert manager.current_project is None

    def test_global_config_loaded(self):
        """グローバル設定読み込み"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            assert isinstance(manager.global_config, dict)

    def test_create_project_config(self):
        """プロジェクト設定作成"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            config = manager.create_project_config(tmpdir, {"default_mode": "test"})
            # macOS: /var -> /private/var symlink対応
            assert Path(config.project_path).resolve() == Path(tmpdir).resolve()
            assert config.default_mode == "test"

    def test_get_active_config_no_project(self):
        """プロジェクトなしのアクティブ設定"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            config = manager.get_active_config()
            assert isinstance(config, dict)

    def test_get_project_summary_not_found(self):
        """存在しないプロジェクトのサマリー"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            summary = manager.get_project_summary("/nonexistent/path")
            assert summary["status"] == "No configuration found"

    def test_get_timestamp(self):
        """タイムスタンプ取得"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            ts = manager._get_timestamp()
            assert "T" in ts  # ISO format
