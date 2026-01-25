#!/usr/bin/env python3
"""
Codex MCP サーバー起動ラッパー

このモジュールは Codex CLI を用いて MCP サーバー(stdio)を安全に起動/停止するための
ユーティリティを提供する。短時間のスモークテストも可能。

注意: 機密情報(OPENAI_API_KEY など)はログ出力しない。
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess  # nosec B404
import sys
import time
from dataclasses import dataclass
from shutil import which
from typing import List, Optional


# シンプルなログ関数(初心者向けに分かりやすく)
def _log(info: str) -> None:
    """標準出力へ分かりやすいメッセージを出す(日本語)。"""
    print(info, flush=True)


def _find_codex_path() -> str:
    """codex 実行ファイルのパスを検出。見つからなければ例外。

    戻り値:
        codex の実行パス
    """
    codex_path = which("codex")
    if not codex_path:
        raise FileNotFoundError("codex コマンドが見つかりません。`codex --version` が成功する状態にしてください。")
    return codex_path


def _ensure_env_safe() -> None:
    """必要な環境変数の存在をチェック(値は出力しない)。

    Codex は OpenAI などのプロバイダを利用するため、OPENAI_API_KEY が
    必要になるケースが多い。無い場合は警告のみ出す(実行は継続)。
    """
    if not os.getenv("OPENAI_API_KEY"):
        _log("[警告] OPENAI_API_KEY が見つかりません。Codex の一部機能が動作しない可能性があります。")


@dataclass
class CodexMCPLauncher:
    """Codex MCP サーバーの起動/停止を担当するクラス。"""

    codex_path: str
    extra_args: List[str]
    process: Optional[subprocess.Popen] = None

    def start(self) -> None:
        """Codex MCP サーバーを起動する。

        実装方針: `codex mcp serve` を stdio で起動。ログは親プロセスで受け取る。
        例外は上位に伝播し、呼び出し側で扱ってもらう。
        """
        if self.process is not None and self.process.poll() is None:
            _log("[情報] すでに Codex MCP サーバーが起動中です。")
            return

        cmd = [self.codex_path, "mcp", "serve"] + self.extra_args
        _log(f"[起動] 実行コマンド: {' '.join(cmd)}")
        # 実行引数に機密は含めない想定。出力はリアルタイムで親に流す
        self.process = subprocess.Popen(  # nosec B603
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    def stop(self, timeout_seconds: float = 3.0) -> None:
        """Codex MCP サーバーを安全に停止する。

        引数:
            timeout_seconds: 正常終了を待つ最大秒数
        """
        if not self.process:
            return

        if self.process.poll() is None:
            # SIGTERM を送って穏やかに終了を試みる
            try:
                if hasattr(self.process, "terminate"):
                    self.process.terminate()
                else:
                    os.kill(self.process.pid, signal.SIGTERM)
            except Exception:
                # プロセス終了済みの可能性（正常ケース）
                _ = None  # nosec B110

            # 規定時間待つ
            waited = 0.0
            while self.process.poll() is None and waited < timeout_seconds:
                time.sleep(0.1)
                waited += 0.1

            # まだ終了しない場合は kill
            if self.process.poll() is None:
                try:
                    if hasattr(self.process, "kill"):
                        self.process.kill()
                    else:
                        os.kill(self.process.pid, signal.SIGKILL)
                except Exception:
                    # プロセス終了済みの可能性（正常ケース）
                    _ = None  # nosec B110

        self.process = None


def smoke_test(duration_seconds: float = 2.0, extra_args: Optional[List[str]] = None) -> bool:
    """Codex MCP サーバーのスモークテストを実施。

    1) codex が存在するか確認
    2) 環境変数の安全チェック
    3) `codex mcp serve` を起動して指定秒数待機後、停止

    引数:
        duration_seconds: 起動後に待つ秒数(短時間でOK)
        extra_args: 追加の起動引数

    戻り値:
        True: おおむね問題なく起動/停止できた
        False: 起動できなかった
    """
    codex_path = _find_codex_path()
    _ensure_env_safe()

    launcher = CodexMCPLauncher(codex_path=codex_path, extra_args=extra_args or [])
    try:
        launcher.start()
        # 起動直後はプロセスが生きているかを確認
        time.sleep(max(0.2, min(duration_seconds, 0.5)))
        if launcher.process is None or launcher.process.poll() is not None:
            _log("[エラー] Codex MCP サーバーが直後に終了しました。インストールと環境変数を確認してください。")
            return False

        # 指定秒数待機(ログは必要に応じて読み取り可)
        waited = 0.0
        while waited < duration_seconds:
            if launcher.process.poll() is not None:
                _log("[警告] Codex MCP サーバーが早期終了しました。")
                break
            time.sleep(0.1)
            waited += 0.1

        return True
    except FileNotFoundError as e:
        _log(f"[エラー] {e}")
        return False
    except Exception as e:
        _log(f"[エラー] 予期せぬエラー: {e}")
        return False
    finally:
        launcher.stop()


def _build_arg_parser() -> argparse.ArgumentParser:
    """引数パーサーを作成。"""
    p = argparse.ArgumentParser(description="Codex MCP サーバー起動ユーティリティ")
    p.add_argument("--smoke", type=float, default=None, help="スモークテスト秒数。指定すると起動→待機→停止を行う")
    p.add_argument(
        "--arg",
        action="append",
        default=[],
        help="codex mcp serve に渡す追加引数(複数指定可)。例: --arg --verbose",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """エントリーポイント。"""
    args = _build_arg_parser().parse_args(argv)

    if args.smoke is not None:
        ok = smoke_test(duration_seconds=float(args.smoke), extra_args=list(args.arg or []))
        _log("[結果] スモークテスト: 成功" if ok else "[結果] スモークテスト: 失敗")
        return 0 if ok else 1

    # 明示的な指示がない場合はヘルプを表示
    _log("使い方: --smoke <秒数> を指定して短時間の起動確認ができます。例: --smoke 2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
