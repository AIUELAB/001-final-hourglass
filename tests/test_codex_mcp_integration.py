#!/usr/bin/env python3
"""codex_mcp_integration テスト"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from codex_mcp_integration import (
    CodexMCPLauncher,
    _ensure_env_safe,
    _find_codex_path,
    _log,
    _build_arg_parser,
    main,
    smoke_test,
)


class TestCodexMCPIntegration:
    """codex_mcp_integrationの基本テスト"""

    def test_log(self, capsys):
        """_log関数テスト"""
        _log("テストメッセージ")
        captured = capsys.readouterr()
        assert "テストメッセージ" in captured.out

    @patch("codex_mcp_integration.which")
    def test_find_codex_path_found(self, mock_which):
        """codexが見つかる場合"""
        mock_which.return_value = "/usr/local/bin/codex"
        result = _find_codex_path()
        assert result == "/usr/local/bin/codex"

    @patch("codex_mcp_integration.which")
    def test_find_codex_path_not_found(self, mock_which):
        """codexが見つからない場合"""
        mock_which.return_value = None
        with pytest.raises(FileNotFoundError):
            _find_codex_path()

    @patch.dict("os.environ", {}, clear=True)
    def test_ensure_env_safe_no_key(self, capsys):
        """OPENAI_API_KEYがない場合の警告"""
        _ensure_env_safe()
        captured = capsys.readouterr()
        assert "警告" in captured.out

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_ensure_env_safe_with_key(self, capsys):
        """OPENAI_API_KEYがある場合"""
        _ensure_env_safe()
        captured = capsys.readouterr()
        assert "警告" not in captured.out

    def test_launcher_init(self):
        """CodexMCPLauncher初期化テスト"""
        launcher = CodexMCPLauncher(codex_path="/usr/bin/codex", extra_args=["--arg1"])
        assert launcher.codex_path == "/usr/bin/codex"
        assert launcher.extra_args == ["--arg1"]
        assert launcher.process is None

    def test_launcher_init_empty_args(self):
        """空の追加引数でLauncher初期化"""
        launcher = CodexMCPLauncher(codex_path="/usr/bin/codex", extra_args=[])
        assert launcher.extra_args == []

    def test_launcher_stop_no_process(self):
        """プロセスなしでstop呼び出し"""
        launcher = CodexMCPLauncher(codex_path="/usr/bin/codex", extra_args=[])
        launcher.process = None
        launcher.stop()  # エラーなく完了
        assert launcher.process is None


class TestCodexArgParser:
    """引数パーサーのテスト"""

    def test_build_arg_parser(self):
        """パーサー構築テスト"""
        from codex_mcp_integration import _build_arg_parser

        parser = _build_arg_parser()
        assert parser is not None

    def test_parse_smoke_arg(self):
        """--smokeオプションパース"""
        from codex_mcp_integration import _build_arg_parser

        parser = _build_arg_parser()
        args = parser.parse_args(["--smoke", "2.5"])
        assert args.smoke == 2.5

    def test_parse_arg_option(self):
        """--argオプションパース"""
        from codex_mcp_integration import _build_arg_parser

        parser = _build_arg_parser()
        args = parser.parse_args(["--arg", "verbose", "--arg", "debug"])
        assert "verbose" in args.arg
        assert "debug" in args.arg

    def test_parse_no_args(self):
        """引数なしパース"""
        from codex_mcp_integration import _build_arg_parser

        parser = _build_arg_parser()
        args = parser.parse_args([])
        assert args.smoke is None
        assert args.arg == []


class TestCodexMain:
    """main関数のテスト"""

    def test_main_no_args(self, capsys):
        """引数なしでmain呼び出し"""
        result = main([])
        assert result == 0
        captured = capsys.readouterr()
        assert "使い方" in captured.out

    @patch("codex_mcp_integration.smoke_test")
    def test_main_with_smoke_success(self, mock_smoke, capsys):
        """--smoke成功時"""
        mock_smoke.return_value = True
        result = main(["--smoke", "2.0"])
        assert result == 0
        captured = capsys.readouterr()
        assert "成功" in captured.out

    @patch("codex_mcp_integration.smoke_test")
    def test_main_with_smoke_failure(self, mock_smoke, capsys):
        """--smoke失敗時"""
        mock_smoke.return_value = False
        result = main(["--smoke", "1.0"])
        assert result == 1
        captured = capsys.readouterr()
        assert "失敗" in captured.out

    @patch("codex_mcp_integration.smoke_test")
    def test_main_with_extra_args(self, mock_smoke):
        """--argオプション付き"""
        mock_smoke.return_value = True
        result = main(["--smoke", "1", "--arg", "verbose"])
        assert result == 0
        mock_smoke.assert_called_once()
        call_args = mock_smoke.call_args
        assert "verbose" in call_args.kwargs.get("extra_args", [])


class TestCodexMCPLauncherStart:
    """CodexMCPLauncher.startメソッドのテスト"""

    @patch("codex_mcp_integration.subprocess.Popen")
    def test_start_creates_process(self, mock_popen, capsys):
        """start()がプロセスを作成"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # プロセス実行中
        mock_popen.return_value = mock_process

        launcher = CodexMCPLauncher(codex_path="/usr/bin/codex", extra_args=[])
        launcher.start()

        assert launcher.process is not None
        mock_popen.assert_called_once()
        captured = capsys.readouterr()
        assert "起動" in captured.out

    @patch("codex_mcp_integration.subprocess.Popen")
    def test_start_with_extra_args(self, mock_popen):
        """追加引数付きでstart()"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        launcher = CodexMCPLauncher(
            codex_path="/usr/bin/codex", extra_args=["--verbose", "--debug"]
        )
        launcher.start()

        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert "--verbose" in cmd
        assert "--debug" in cmd

    @patch("codex_mcp_integration.subprocess.Popen")
    def test_start_already_running(self, mock_popen, capsys):
        """既に起動中の場合は何もしない"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # 実行中

        launcher = CodexMCPLauncher(codex_path="/usr/bin/codex", extra_args=[])
        launcher.process = mock_process  # 既にプロセスあり

        launcher.start()

        mock_popen.assert_not_called()
        captured = capsys.readouterr()
        assert "起動中" in captured.out

    @patch("codex_mcp_integration.subprocess.Popen")
    def test_start_after_terminated(self, mock_popen):
        """終了後に再起動"""
        old_process = MagicMock()
        old_process.poll.return_value = 0  # 終了済み

        new_process = MagicMock()
        new_process.poll.return_value = None
        mock_popen.return_value = new_process

        launcher = CodexMCPLauncher(codex_path="/usr/bin/codex", extra_args=[])
        launcher.process = old_process

        launcher.start()

        mock_popen.assert_called_once()
        assert launcher.process is new_process


class TestCodexMCPLauncherStop:
    """CodexMCPLauncher.stopメソッドのテスト"""

    def test_stop_with_running_process(self):
        """実行中プロセスを停止"""
        mock_process = MagicMock()
        # poll()が最初はNone（実行中）、その後0（終了）を繰り返す
        poll_returns = [None, None, None, 0] + [0] * 50  # 十分な回数
        mock_process.poll.side_effect = poll_returns

        launcher = CodexMCPLauncher(codex_path="/usr/bin/codex", extra_args=[])
        launcher.process = mock_process

        launcher.stop(timeout_seconds=0.3)

        mock_process.terminate.assert_called_once()
        assert launcher.process is None

    def test_stop_process_already_terminated(self):
        """既に終了済みのプロセス"""
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # 終了済み

        launcher = CodexMCPLauncher(codex_path="/usr/bin/codex", extra_args=[])
        launcher.process = mock_process

        launcher.stop()

        mock_process.terminate.assert_not_called()
        assert launcher.process is None

    def test_stop_requires_kill(self):
        """terminateで終了しないためkillが必要"""
        mock_process = MagicMock()
        # poll()が常にNone（終了しない）
        mock_process.poll.return_value = None

        launcher = CodexMCPLauncher(codex_path="/usr/bin/codex", extra_args=[])
        launcher.process = mock_process

        launcher.stop(timeout_seconds=0.1)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert launcher.process is None

    def test_stop_terminate_exception(self):
        """terminate時に例外が発生"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.terminate.side_effect = OSError("Permission denied")
        mock_process.kill.return_value = None

        launcher = CodexMCPLauncher(codex_path="/usr/bin/codex", extra_args=[])
        launcher.process = mock_process

        # 例外が発生しても停止処理は完了する
        launcher.stop(timeout_seconds=0.1)
        assert launcher.process is None


class TestSmokeTest:
    """smoke_test関数のテスト"""

    @patch("codex_mcp_integration._find_codex_path")
    @patch("codex_mcp_integration._ensure_env_safe")
    @patch("codex_mcp_integration.CodexMCPLauncher")
    def test_smoke_test_success(self, mock_launcher_class, mock_env, mock_find):
        """スモークテスト成功"""
        mock_find.return_value = "/usr/bin/codex"

        mock_launcher = MagicMock()
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # 実行中
        mock_launcher.process = mock_process
        mock_launcher_class.return_value = mock_launcher

        result = smoke_test(duration_seconds=0.1)

        assert result is True
        mock_launcher.start.assert_called_once()
        mock_launcher.stop.assert_called_once()

    @patch("codex_mcp_integration._find_codex_path")
    def test_smoke_test_codex_not_found(self, mock_find):
        """codexが見つからない場合（_find_codex_pathの例外は伝播）"""
        mock_find.side_effect = FileNotFoundError("codex not found")

        # _find_codex_pathはtryブロックの外で呼ばれるため例外が伝播
        with pytest.raises(FileNotFoundError):
            smoke_test(duration_seconds=0.1)

    @patch("codex_mcp_integration._find_codex_path")
    @patch("codex_mcp_integration._ensure_env_safe")
    @patch("codex_mcp_integration.CodexMCPLauncher")
    def test_smoke_test_process_dies_immediately(
        self, mock_launcher_class, mock_env, mock_find, capsys
    ):
        """プロセスが即座に終了"""
        mock_find.return_value = "/usr/bin/codex"

        mock_launcher = MagicMock()
        mock_launcher.process = None  # プロセスがない状態
        mock_launcher_class.return_value = mock_launcher

        result = smoke_test(duration_seconds=0.1)

        assert result is False
        captured = capsys.readouterr()
        assert "エラー" in captured.out

    @patch("codex_mcp_integration._find_codex_path")
    @patch("codex_mcp_integration._ensure_env_safe")
    @patch("codex_mcp_integration.CodexMCPLauncher")
    def test_smoke_test_process_terminates_early(
        self, mock_launcher_class, mock_env, mock_find, capsys
    ):
        """プロセスが早期終了"""
        mock_find.return_value = "/usr/bin/codex"

        mock_launcher = MagicMock()
        mock_process = MagicMock()
        # 最初は実行中、その後終了
        mock_process.poll.side_effect = [None, 0, 0]
        mock_launcher.process = mock_process
        mock_launcher_class.return_value = mock_launcher

        result = smoke_test(duration_seconds=0.5)

        # 早期終了でもTrueを返す（警告は出る）
        assert result is True

    @patch("codex_mcp_integration._find_codex_path")
    @patch("codex_mcp_integration._ensure_env_safe")
    @patch("codex_mcp_integration.CodexMCPLauncher")
    def test_smoke_test_unexpected_exception(
        self, mock_launcher_class, mock_env, mock_find, capsys
    ):
        """予期せぬ例外"""
        mock_find.return_value = "/usr/bin/codex"
        mock_launcher = MagicMock()
        mock_launcher.start.side_effect = RuntimeError("Unexpected error")
        mock_launcher_class.return_value = mock_launcher

        result = smoke_test(duration_seconds=0.1)

        assert result is False
        captured = capsys.readouterr()
        assert "エラー" in captured.out

    @patch("codex_mcp_integration._find_codex_path")
    @patch("codex_mcp_integration._ensure_env_safe")
    @patch("codex_mcp_integration.CodexMCPLauncher")
    def test_smoke_test_with_extra_args(self, mock_launcher_class, mock_env, mock_find):
        """追加引数付きスモークテスト"""
        mock_find.return_value = "/usr/bin/codex"

        mock_launcher = MagicMock()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_launcher.process = mock_process
        mock_launcher_class.return_value = mock_launcher

        result = smoke_test(duration_seconds=0.1, extra_args=["--verbose"])

        assert result is True
        mock_launcher_class.assert_called_once_with(
            codex_path="/usr/bin/codex", extra_args=["--verbose"]
        )

    @patch("codex_mcp_integration._find_codex_path")
    @patch("codex_mcp_integration._ensure_env_safe")
    @patch("codex_mcp_integration.CodexMCPLauncher")
    def test_smoke_test_finally_calls_stop(
        self, mock_launcher_class, mock_env, mock_find
    ):
        """例外発生時もstopが呼ばれる"""
        mock_find.return_value = "/usr/bin/codex"

        mock_launcher = MagicMock()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_launcher.process = mock_process
        mock_launcher.start.side_effect = ValueError("test error")
        mock_launcher_class.return_value = mock_launcher

        result = smoke_test(duration_seconds=0.1)

        assert result is False
        mock_launcher.stop.assert_called_once()


class TestBuildArgParser:
    """_build_arg_parser関数の追加テスト"""

    def test_parser_description(self):
        """パーサーの説明文"""
        parser = _build_arg_parser()
        assert "Codex MCP" in parser.description

    def test_smoke_default_none(self):
        """--smokeデフォルトはNone"""
        parser = _build_arg_parser()
        args = parser.parse_args([])
        assert args.smoke is None

    def test_arg_default_empty_list(self):
        """--argデフォルトは空リスト"""
        parser = _build_arg_parser()
        args = parser.parse_args([])
        assert args.arg == []

    def test_multiple_args(self):
        """複数の--arg"""
        parser = _build_arg_parser()
        args = parser.parse_args(["--arg", "a", "--arg", "b", "--arg", "c"])
        assert len(args.arg) == 3
        assert "a" in args.arg
        assert "b" in args.arg
        assert "c" in args.arg

    def test_combined_options(self):
        """複合オプション"""
        parser = _build_arg_parser()
        args = parser.parse_args(["--smoke", "5.0", "--arg", "verbose"])
        assert args.smoke == 5.0
        assert "verbose" in args.arg


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_launcher_dataclass_defaults(self):
        """dataclassのデフォルト値"""
        launcher = CodexMCPLauncher(codex_path="/bin/codex", extra_args=[])
        assert launcher.process is None

    @patch("codex_mcp_integration.which")
    def test_find_codex_path_error_message(self, mock_which):
        """エラーメッセージの確認"""
        mock_which.return_value = None
        with pytest.raises(FileNotFoundError) as exc_info:
            _find_codex_path()
        assert "codex" in str(exc_info.value)

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_ensure_env_safe_empty_key(self, capsys):
        """空のOPENAI_API_KEY"""
        _ensure_env_safe()
        captured = capsys.readouterr()
        # 空文字列はFalsyなので警告が出る
        assert "警告" in captured.out

    def test_log_flush(self, capsys):
        """_logがflushする"""
        _log("test message")
        captured = capsys.readouterr()
        assert "test message" in captured.out

    def test_log_japanese(self, capsys):
        """_logで日本語出力"""
        _log("日本語メッセージ")
        captured = capsys.readouterr()
        assert "日本語メッセージ" in captured.out
