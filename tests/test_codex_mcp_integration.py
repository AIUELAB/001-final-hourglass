#!/usr/bin/env python3
"""codex_mcp_integration テスト"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from codex_mcp_integration import CodexMCPLauncher, _ensure_env_safe, _find_codex_path, _log


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
