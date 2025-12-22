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


class TestLoadConfigFile:
    """_load_config_fileテスト"""

    def test_load_json_config(self):
        """JSONファイル読み込み"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # JSONファイル作成
            config_file = Path(tmpdir) / "config.json"
            config_data = {"project_name": "test", "default_mode": "orchestrate"}
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            result = manager._load_config_file(config_file)
            assert result is not None
            assert result["project_name"] == "test"
            assert result["default_mode"] == "orchestrate"

    def test_load_yaml_config(self):
        """YAMLファイル読み込み"""
        import tempfile

        import yaml

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # YAMLファイル作成
            config_file = Path(tmpdir) / "config.yaml"
            config_data = {"project_name": "test_yaml", "auto_test": False}
            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            result = manager._load_config_file(config_file)
            assert result is not None
            assert result["project_name"] == "test_yaml"

    def test_load_invalid_file(self, caplog):
        """無効なファイル読み込み"""
        import logging
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # 壊れたJSONファイル作成
            config_file = Path(tmpdir) / "broken.json"
            with open(config_file, "w") as f:
                f.write("{invalid json")

            with caplog.at_level(logging.WARNING):
                result = manager._load_config_file(config_file)
            assert result is None
            assert "設定ファイル読み込みエラー" in caplog.text

    def test_load_unsupported_extension(self):
        """未対応の拡張子"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # .txt ファイル作成
            config_file = Path(tmpdir) / "config.txt"
            config_file.write_text("test content")

            result = manager._load_config_file(config_file)
            assert result is None


class TestDetectProjectConfig:
    """detect_project_configテスト"""

    def test_detect_existing_json_config(self):
        """JSON設定ファイル検出"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # プロジェクトディレクトリ作成
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()

            # .superclaude.json作成
            config_file = project_dir / ".superclaude.json"
            config_data = {"project_name": "detected_project", "default_mode": "brainstorm"}
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            result = manager.detect_project_config(str(project_dir))
            assert result is not None
            assert result.default_mode == "brainstorm"

    def test_detect_uses_cache(self):
        """キャッシュ使用"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # プロジェクト設定作成
            project_dir = Path(tmpdir) / "cached_project"
            project_dir.mkdir()

            config_file = project_dir / ".superclaude.json"
            with open(config_file, "w") as f:
                json.dump({"project_name": "cached"}, f)

            # 最初の呼び出し
            result1 = manager.detect_project_config(str(project_dir))

            # ファイルを削除
            config_file.unlink()

            # キャッシュから取得
            result2 = manager.detect_project_config(str(project_dir))

            assert result1 is result2

    def test_detect_returns_none_no_config(self):
        """設定ファイルなしでNone"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # 空のプロジェクトディレクトリ
            project_dir = Path(tmpdir) / "empty_project"
            project_dir.mkdir()

            result = manager.detect_project_config(str(project_dir))
            assert result is None


class TestGetActiveConfig:
    """get_active_configテスト"""

    def test_merges_project_with_global(self):
        """プロジェクトとグローバル設定のマージ"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # プロジェクト設定作成
            project_dir = Path(tmpdir) / "merge_project"
            project_dir.mkdir()

            config_file = project_dir / ".superclaude.json"
            with open(config_file, "w") as f:
                json.dump({"project_name": "merge_test", "auto_test": False}, f)

            result = manager.get_active_config(str(project_dir))

            # プロジェクト設定が優先
            assert result.get("auto_test") is False

    def test_disabled_flags_filtered(self):
        """無効化フラグがフィルタリングされる"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)
            # グローバル設定にフラグを設定
            manager.global_config["default_flags"] = ["--think", "--orchestrate", "--delegate"]

            # プロジェクト設定作成
            project_dir = Path(tmpdir) / "filter_project"
            project_dir.mkdir()

            config_file = project_dir / ".superclaude.json"
            with open(config_file, "w") as f:
                json.dump({"project_name": "filter", "disabled_flags": ["--think"]}, f)

            result = manager.get_active_config(str(project_dir))

            assert "--think" not in result.get("default_flags", [])
            assert "--orchestrate" in result.get("default_flags", [])


class TestUpdateProjectConfig:
    """update_project_configテスト"""

    def test_update_existing_config(self):
        """既存設定の更新"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # プロジェクト設定作成
            project_dir = Path(tmpdir) / "update_project"
            project_dir.mkdir()

            config_file = project_dir / ".superclaude.json"
            with open(config_file, "w") as f:
                json.dump({"project_name": "original", "auto_test": True}, f)

            # 設定を検出
            manager.detect_project_config(str(project_dir))

            # 更新
            updated = manager.update_project_config(str(project_dir), {"auto_test": False})

            assert updated.auto_test is False

    def test_update_creates_new_if_not_exists(self):
        """存在しない場合は新規作成"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # 空のプロジェクトディレクトリ
            project_dir = Path(tmpdir) / "new_project"
            project_dir.mkdir()

            # 更新（新規作成）
            created = manager.update_project_config(str(project_dir), {"auto_format": True})

            assert created.auto_format is True


class TestExportImportConfig:
    """export_config/import_configテスト"""

    def test_export_config(self):
        """設定エクスポート"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # プロジェクト設定作成
            project_dir = Path(tmpdir) / "export_project"
            project_dir.mkdir()

            config_file = project_dir / ".superclaude.json"
            with open(config_file, "w") as f:
                json.dump({"project_name": "export_test", "auto_test": True}, f)

            # エクスポート
            output_file = Path(tmpdir) / "exported.json"
            result = manager.export_config(str(project_dir), str(output_file))

            assert output_file.exists()
            with open(output_file) as f:
                exported = json.load(f)
                assert exported["auto_test"] is True

    def test_export_config_not_found(self):
        """存在しないプロジェクトでエラー"""
        import tempfile

        import pytest

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            with pytest.raises(ValueError, match="No configuration found"):
                manager.export_config("/nonexistent/path")

    def test_import_config(self):
        """設定インポート"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # インポート用ファイル作成 (default_modeはグローバル設定で上書きされない)
            import_file = Path(tmpdir) / "import.json"
            with open(import_file, "w") as f:
                json.dump({"project_name": "imported", "default_mode": "custom_mode"}, f)

            # プロジェクトディレクトリ
            project_dir = Path(tmpdir) / "import_project"
            project_dir.mkdir()

            result = manager.import_config(str(project_dir), str(import_file))

            # default_modeはグローバル設定で上書きされないため、保持される
            assert result.default_mode == "custom_mode"

    def test_import_invalid_config(self):
        """無効な設定ファイルでエラー"""
        import tempfile

        import pytest

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # 壊れたファイル作成
            bad_file = Path(tmpdir) / "bad.json"
            bad_file.write_text("{invalid")

            with pytest.raises(ValueError, match="Invalid configuration file"):
                manager.import_config(str(tmpdir), str(bad_file))


class TestAddCustomRule:
    """add_custom_ruleテスト"""

    def test_add_rule_to_existing_config(self):
        """既存設定にルール追加"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # プロジェクト設定作成
            project_dir = Path(tmpdir) / "rule_project"
            project_dir.mkdir()

            config_file = project_dir / ".superclaude.json"
            with open(config_file, "w") as f:
                json.dump({"project_name": "rules", "custom_rules": []}, f)

            manager.detect_project_config(str(project_dir))

            new_rule = {"pattern": "console.log", "action": "warn"}
            # add_custom_ruleはNoneを返す（void）
            manager.add_custom_rule(str(project_dir), new_rule)

            # 再度設定を取得して確認
            config = manager.detect_project_config(str(project_dir))
            assert new_rule in config.custom_rules


class TestSetToolShortcut:
    """set_tool_shortcutテスト"""

    def test_set_shortcut(self):
        """ショートカット設定"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # プロジェクト設定作成
            project_dir = Path(tmpdir) / "shortcut_project"
            project_dir.mkdir()

            config_file = project_dir / ".superclaude.json"
            with open(config_file, "w") as f:
                json.dump({"project_name": "shortcuts", "tool_shortcuts": {}}, f)

            manager.detect_project_config(str(project_dir))

            # set_tool_shortcutはNoneを返す（void）
            manager.set_tool_shortcut(str(project_dir), "test", "run pytest")

            # 再度設定を取得して確認
            config = manager.detect_project_config(str(project_dir))
            assert config.tool_shortcuts["test"] == "run pytest"


class TestSaveAndLoadConfig:
    """_save_project_config/_load_saved_configテスト"""

    def test_save_and_load_round_trip(self):
        """保存と読み込みのラウンドトリップ"""
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # macOS: /var -> /private/var symlink対応
            # create_project_configはパスをresolve()するため、
            # _load_saved_configにも同じ解決済みパスを渡す必要がある
            resolved_path = str(Path(tmpdir).resolve())

            # 設定作成
            config = manager.create_project_config(resolved_path, {"default_mode": "roundtrip"})

            # キャッシュをクリア
            manager.project_configs.clear()

            # 保存された設定を読み込み（解決済みパスを使用）
            loaded = manager._load_saved_config(resolved_path)

            assert loaded is not None
            assert loaded.default_mode == "roundtrip"


class TestGetProjectSummary:
    """get_project_summaryテスト"""

    def test_summary_for_existing_project(self):
        """既存プロジェクトのサマリー"""
        import json
        import tempfile

        from superclaude_project_config import ProjectConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProjectConfigManager(global_config_dir=tmpdir)

            # プロジェクト設定作成
            project_dir = Path(tmpdir) / "summary_project"
            project_dir.mkdir()

            config_file = project_dir / ".superclaude.json"
            with open(config_file, "w") as f:
                json.dump({"project_name": "summary_test"}, f)

            summary = manager.get_project_summary(str(project_dir))

            assert summary["project_name"] == "summary_test"
            assert "status" not in summary or summary["status"] != "No configuration found"
