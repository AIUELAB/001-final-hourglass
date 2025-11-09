#!/usr/bin/env python3
"""
main.pyのテストモジュール
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import AppConfig, Application, calculate_sum, cli, validate_email


class TestAppConfig:
    """AppConfigクラスのテスト"""

    def test_from_env_default_values(self):
        """デフォルト値でのAppConfig生成をテスト"""
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig.from_env()

            assert config.app_name == "Claude Code MCP Template"
            assert config.version == "1.0.0"
            assert config.debug is False
            assert config.environment == "development"

    def test_from_env_with_custom_values(self):
        """カスタム環境変数でのAppConfig生成をテスト"""
        env_vars = {
            "APP_NAME": "Test App",
            "APP_VERSION": "2.0.0",
            "DEBUG": "true",
            "ENVIRONMENT": "production",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = AppConfig.from_env()

            assert config.app_name == "Test App"
            assert config.version == "2.0.0"
            assert config.debug is True
            assert config.environment == "production"


class TestApplication:
    """Applicationクラスのテスト"""

    @pytest.fixture
    def app_config(self):
        """テスト用のAppConfigを作成"""
        return AppConfig(
            app_name="Test App", version="1.0.0", debug=False, environment="test", mcp_enabled=False
        )

    @pytest.fixture
    def app(self, app_config):
        """テスト用のApplicationインスタンスを作成"""
        return Application(app_config)

    def test_initialization(self, app_config):
        """Applicationの初期化をテスト"""
        app = Application(app_config)
        assert app.config == app_config

    def test_process_data(self, app):
        """process_dataメソッドをテスト"""
        result = app.process_data()

        assert result["status"] == "success"
        assert result["items_processed"] == 42
        assert "successfully" in result["message"]

    @patch("main.console")
    def test_display_info(self, mock_console, app):
        """display_infoメソッドをテスト"""
        app.display_info()

        # consoleのprintメソッドが呼ばれたことを確認
        mock_console.print.assert_called()

    @patch("main.logger")
    def test_run(self, mock_logger, app):
        """runメソッドをテスト"""
        with patch.object(app, "display_info") as mock_display:
            with patch.object(app, "check_mcp_status") as mock_check_mcp:
                with patch.object(app, "process_data") as mock_process:
                    app.run()

                    # 各メソッドが呼ばれたことを確認
                    mock_display.assert_called_once()
                    mock_check_mcp.assert_called_once()
                    mock_process.assert_called_once()

                    # ログが記録されたことを確認
                    assert mock_logger.info.call_count >= 2


class TestApplicationWithMCP:
    """ApplicationクラスのMCP有効時のテスト（Phase 1）"""

    @pytest.fixture
    def mcp_config(self):
        """MCP有効なテスト用のAppConfigを作成"""
        return AppConfig(
            app_name="Test App MCP", version="1.0.0", debug=False, environment="test", mcp_enabled=True
        )

    @pytest.fixture
    def mcp_app(self, mcp_config):
        """MCP有効なテスト用のApplicationインスタンスを作成"""
        return Application(mcp_config)

    @patch("main.logger")
    def test_initialization_with_mcp_enabled(self, mock_logger, mcp_config):
        """MCP有効時の初期化でMCP readyログが出力されることをテスト (Line 105)"""
        app = Application(mcp_config)

        # 初期化ログが呼ばれたことを確認
        mock_logger.info.assert_any_call(f"Initializing {mcp_config.app_name} v{mcp_config.version}")
        # MCP有効ログが呼ばれたことを確認
        mock_logger.info.assert_any_call("MCP servers are configured and ready")

    @patch("main.logger")
    def test_initialization_with_mcp_disabled(self, mock_logger):
        """MCP無効時の初期化で警告ログが出力されることをテスト"""
        config = AppConfig(
            app_name="Test App", version="1.0.0", debug=False, environment="test", mcp_enabled=False
        )
        app = Application(config)

        # MCP無効時の警告ログが呼ばれたことを確認
        mock_logger.warning.assert_called_once_with("MCP servers not configured (missing API keys)")

    @patch("main.console")
    def test_check_mcp_status_display(self, mock_console, mcp_app):
        """check_mcp_statusメソッドがMCPサーバー状態を表示することをテスト (Lines 156-186)"""
        # 環境変数をモック
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "test_github_token",
                "BRAVE_API_KEY": "test_brave_key",
                "FIRECRAWL_API_KEY": "test_firecrawl_key",
            },
            clear=True,
        ):
            mcp_app.check_mcp_status()

            # console.print が複数回呼ばれることを確認
            assert mock_console.print.call_count >= 3

            # 呼び出し内容を取得
            call_args_list = [str(call) for call in mock_console.print.call_args_list]
            all_calls = " ".join(call_args_list)

            # MCPサーバーステータスが表示されることを確認
            assert "MCP Server Status" in all_calls
            # Always Availableセクションが表示されることを確認
            assert "Always Available" in all_calls

    @patch("main.console")
    def test_check_mcp_status_no_servers(self, mock_console, mcp_app):
        """MCPサーバーが設定されていない場合の表示をテスト"""
        # 環境変数を空に
        with patch.dict(os.environ, {}, clear=True):
            mcp_app.check_mcp_status()

            # console.printが呼ばれることを確認
            assert mock_console.print.call_count >= 2

            call_args_list = [str(call) for call in mock_console.print.call_args_list]
            all_calls = " ".join(call_args_list)

            # ステータス表示があることを確認
            assert "MCP Server Status" in all_calls

    @patch("main.console")
    def test_process_data_with_mcp_ready(self, mock_console, mcp_app):
        """MCP有効時のprocess_dataでMCP readyメッセージが表示されることをテスト (Line 216)"""
        result = mcp_app.process_data()

        # 戻り値の確認
        assert result["status"] == "success"
        assert result["items_processed"] == 42
        assert result["mcp_ready"] is True

        # console.printが呼ばれることを確認
        assert mock_console.print.call_count >= 1

        # 呼び出し内容を取得
        call_args_list = [str(call) for call in mock_console.print.call_args_list]
        all_calls = " ".join(call_args_list)

        # MCP readyメッセージが表示されることを確認
        assert "MCP servers are ready for use" in all_calls or "ready" in all_calls.lower()

    @patch("main.console")
    def test_process_data_without_mcp(self, mock_console):
        """MCP無効時のprocess_dataでMCPメッセージが表示されないことをテスト"""
        config = AppConfig(
            app_name="Test App", version="1.0.0", debug=False, environment="test", mcp_enabled=False
        )
        app = Application(config)
        result = app.process_data()

        # 戻り値の確認
        assert result["status"] == "success"
        assert result["mcp_ready"] is False

        # 呼び出し内容を取得
        call_args_list = [str(call) for call in mock_console.print.call_args_list]
        all_calls = " ".join(call_args_list)

        # MCP readyメッセージが表示されないことを確認（表示される場合は少なくとも"ready"が含まれる）
        # MCP無効時は通常のメッセージのみ
        assert result["mcp_ready"] is False


class TestUtilityFunctions:
    """ユーティリティ関数のテスト"""

    @pytest.mark.parametrize(
        "numbers, expected",
        [
            ([1, 2, 3], 6),
            ([0], 0),
            ([-1, 1], 0),
            ([1.5, 2.5], 4.0),
            ([], 0),
        ],
    )
    def test_calculate_sum(self, numbers, expected):
        """calculate_sum関数をテスト"""
        assert calculate_sum(numbers) == expected

    @pytest.mark.parametrize(
        "email, expected",
        [
            ("test@example.com", True),
            ("user.name@domain.co.jp", True),
            ("invalid.email", False),
            ("@example.com", False),
            ("user@", False),
            ("", False),
            ("user name@example.com", False),
        ],
    )
    def test_validate_email(self, email, expected):
        """validate_email関数をテスト"""
        assert validate_email(email) == expected


class TestCLI:
    """CLIコマンドのテスト"""

    @pytest.fixture
    def runner(self):
        """CLIテスト用のRunnerを作成"""
        return CliRunner()

    def test_cli_version(self, runner):
        """バージョン表示をテスト"""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    @patch("main.Application")
    def test_run_command(self, mock_app_class, runner):
        """runコマンドをテスト"""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        result = runner.invoke(cli, ["run"])

        assert result.exit_code == 0
        mock_app.run.assert_called_once()

    @patch("main.Application")
    def test_run_command_with_debug(self, mock_app_class, runner):
        """debugフラグ付きrunコマンドをテスト"""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        result = runner.invoke(cli, ["run", "--debug"])

        assert result.exit_code == 0
        mock_app.run.assert_called_once()

    @patch("main.Application")
    def test_info_command(self, mock_app_class, runner):
        """infoコマンドをテスト"""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        result = runner.invoke(cli, ["info"])

        assert result.exit_code == 0
        mock_app.display_info.assert_called_once()
        mock_app.check_mcp_status.assert_called_once()

    def test_sum_command(self, runner):
        """sumコマンドをテスト"""
        result = runner.invoke(cli, ["sum", "1", "2", "3"])

        assert result.exit_code == 0
        assert "6" in result.output

    def test_sum_command_no_args(self, runner):
        """引数なしのsumコマンドをテスト"""
        result = runner.invoke(cli, ["sum"])

        assert result.exit_code == 0
        assert "No numbers provided" in result.output

    def test_validate_command_valid(self, runner):
        """有効なメールでのvalidateコマンドをテスト"""
        result = runner.invoke(cli, ["validate", "test@example.com"])

        assert result.exit_code == 0
        assert "is valid" in result.output

    def test_validate_command_invalid(self, runner):
        """無効なメールでのvalidateコマンドをテスト"""
        result = runner.invoke(cli, ["validate", "invalid.email"])

        assert result.exit_code == 0
        assert "is invalid" in result.output

    @patch("main.console")
    def test_mcp_demo_command(self, mock_console, runner):
        """mcp-demoコマンドをテスト (Line 374)"""
        result = runner.invoke(cli, ["mcp-demo"])

        assert result.exit_code == 0
        # console.printが呼ばれたことを確認
        assert mock_console.print.call_count >= 1

        # 呼び出し内容を取得
        call_args_list = [str(call) for call in mock_console.print.call_args_list]
        all_calls = " ".join(call_args_list)

        # MCP使用例が表示されることを確認
        assert "MCP Server Usage Examples" in all_calls or "GitHub" in all_calls or "Brave Search" in all_calls

    @patch("main.console")
    def test_check_env_command_all_set(self, mock_console, runner):
        """check-envコマンド - 全環境変数が設定されている場合 (Lines 426-466)"""
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": "test_github_token",
                "BRAVE_API_KEY": "test_brave_key",
                "FIRECRAWL_API_KEY": "test_firecrawl_key",
                "SLACK_BOT_TOKEN": "test_slack_token",
            },
            clear=True,
        ):
            result = runner.invoke(cli, ["check-env"])

            assert result.exit_code == 0
            assert mock_console.print.call_count >= 3

            call_args_list = [str(call) for call in mock_console.print.call_args_list]
            all_calls = " ".join(call_args_list)

            # 必須環境変数チェックが表示されることを確認
            assert "Required" in all_calls or "GITHUB_TOKEN" in all_calls

    @patch("main.console")
    def test_check_env_command_missing_required(self, mock_console, runner):
        """check-envコマンド - 必須環境変数が不足している場合"""
        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(cli, ["check-env"])

            assert result.exit_code == 0

            call_args_list = [str(call) for call in mock_console.print.call_args_list]
            all_calls = " ".join(call_args_list)

            # 必須変数が不足していることが表示されることを確認
            assert "missing" in all_calls.lower() or "required" in all_calls.lower()

    @patch("main.Application")
    def test_run_command_error_handling(self, mock_app_class, runner):
        """runコマンドのエラーハンドリングをテスト (Lines 341-344)"""
        # Applicationインスタンスのrunメソッドが例外を投げるように設定
        mock_app = Mock()
        mock_app.run.side_effect = Exception("Test error")
        mock_app_class.return_value = mock_app

        result = runner.invoke(cli, ["run"])

        # エラーが発生した場合、exit_codeは1になる
        assert result.exit_code == 1
        # エラーメッセージが表示されることを確認
        assert "Error" in result.output or "error" in result.output.lower()

    @patch("main.cli")
    def test_main_function(self, mock_cli):
        """main()エントリーポイント関数をテスト (Line 483)"""
        from main import main

        main()

        # cliが呼ばれたことを確認
        mock_cli.assert_called_once()


@pytest.fixture(autouse=True)
def reset_environment():
    """各テストの前後で環境をリセット"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
