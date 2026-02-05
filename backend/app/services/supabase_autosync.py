"""
Supabase 自動同期（CSV保存 → Supabase upsert）

目的:
  ローカルのマスターCSVが保存されたタイミングで、Supabase の `episodes` テーブルへ同期する。

重要:
  - 外部DBへ書き込みが発生するため、環境変数で明示的にONにした場合のみ動作する
  - 同期は重い処理になり得るため、デバウンス/スロットリング/多重実行防止を入れる

使い方（例）:
  ENABLE_SUPABASE_CSV_AUTOSYNC=1 SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python ...
"""

from __future__ import annotations

import hashlib
import importlib.util
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def _is_truthy_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("環境変数 %s が整数ではありません: %r（default=%d）", name, raw, default)
        return default


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("環境変数 %s が数値ではありません: %r（default=%.2f）", name, raw, default)
        return default


@dataclass(frozen=True)
class SupabaseAutosyncConfig:
    """Supabase自動同期の設定（環境変数から取得）"""

    enabled: bool
    batch_size: int
    throttle_seconds: float
    stable_wait_seconds: float
    stable_window_seconds: float

    @classmethod
    def from_env(cls) -> "SupabaseAutosyncConfig":
        return cls(
            enabled=_is_truthy_env(os.getenv("ENABLE_SUPABASE_CSV_AUTOSYNC")),
            batch_size=_get_int_env("SUPABASE_AUTOSYNC_BATCH_SIZE", 500),
            throttle_seconds=_get_float_env("SUPABASE_AUTOSYNC_THROTTLE_SECONDS", 60.0),
            stable_wait_seconds=_get_float_env("SUPABASE_AUTOSYNC_STABLE_WAIT_SECONDS", 10.0),
            stable_window_seconds=_get_float_env("SUPABASE_AUTOSYNC_STABLE_WINDOW_SECONDS", 1.0),
        )


_lock = threading.Lock()
_sync_in_progress = False
_sync_pending = False
_last_sync_started_at = 0.0
_last_synced_sha256: str | None = None


def maybe_schedule_supabase_autosync(csv_path: Path) -> None:
    """
    CSV変更検知時に呼び出すエントリポイント。

    - 環境変数で有効化されていない場合は何もしない
    - 多重実行を防ぎ、変更が連続しても最後に1回は同期されるようにする
    """
    config = SupabaseAutosyncConfig.from_env()
    if not config.enabled:
        return

    # 必須の環境変数（キーはログに出さない）
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        logger.warning(
            "Supabase自動同期が有効ですが、SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY が未設定のため同期をスキップします"
        )
        return

    # supabase依存がない環境でも落ちないように、事前チェックして分かりやすくログ
    if importlib.util.find_spec("supabase") is None:
        logger.error(
            "Supabase自動同期が有効ですが Python パッケージ 'supabase' が見つかりません。"
            " ルートの requirements.txt をインストールしてください。"
        )
        return

    now = time.time()
    delay_seconds = 0.0

    with _lock:
        global _sync_in_progress, _sync_pending, _last_sync_started_at
        if _sync_in_progress:
            _sync_pending = True
            return
        if config.throttle_seconds > 0 and (now - _last_sync_started_at) < config.throttle_seconds:
            # 連続保存でも無限同期にならないようにスロットリング
            # ただし「後で必ず同期」するため、残り時間だけ遅延してワーカーを起動する
            delay_seconds = config.throttle_seconds - (now - _last_sync_started_at)
        _sync_in_progress = True
        _last_sync_started_at = now

    thread = threading.Thread(
        target=_run_supabase_autosync_worker,
        kwargs={"csv_path": csv_path, "config": config, "delay_seconds": delay_seconds},
        daemon=True,
        name="supabase-autosync",
    )
    thread.start()


def _run_supabase_autosync_worker(
    *, csv_path: Path, config: SupabaseAutosyncConfig, delay_seconds: float = 0.0
) -> None:
    """
    同期本体（別スレッドで実行）
    """
    try:
        if delay_seconds > 0:
            logger.info(
                "Supabase自動同期: スロットリングにより %.1f秒 待機します",
                delay_seconds,
            )
            time.sleep(delay_seconds)

        if not csv_path.exists():
            logger.warning("Supabase自動同期: CSVが見つかりません: %s", csv_path)
            return

        _wait_for_file_stable(
            csv_path,
            max_wait_seconds=config.stable_wait_seconds,
            stable_window_seconds=config.stable_window_seconds,
        )

        # 内容が変わっていない場合は同期しない（無駄なUpsertを避ける）
        sha256 = _sha256_file(csv_path)
        with _lock:
            global _last_synced_sha256
            if _last_synced_sha256 == sha256:
                logger.info("Supabase自動同期: 変更なし（sha256一致）のためスキップ")
                return

        project_root = Path(__file__).resolve().parents[3]  # backend/app/services -> repo root
        migrate_script = project_root / "scripts" / "supabase" / "migrate_csv_to_supabase.py"

        if not migrate_script.exists():
            logger.error("Supabase自動同期: 移行スクリプトが見つかりません: %s", migrate_script)
            return

        cmd = [
            sys.executable,
            str(migrate_script),
            "--csv",
            str(csv_path),
            "--batch-size",
            str(config.batch_size),
        ]

        logger.info("Supabase自動同期: 開始（batch_size=%d）", config.batch_size)
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # 秘密情報が含まれないように、出力は先頭のみログ（必要ならファイルへ保存して運用）
            out = (result.stdout or "") + "\n" + (result.stderr or "")
            logger.error("Supabase自動同期: 失敗（exit=%d）\n%s", result.returncode, out[:2000])
            return

        # 成功時のみ「同期済み」として記録する（失敗時に誤ってスキップしないため）
        with _lock:
            _last_synced_sha256 = sha256

        logger.info("Supabase自動同期: 完了")
    except Exception as e:
        logger.error("Supabase自動同期: 例外発生: %s", e, exc_info=True)
    finally:
        pending = False
        with _lock:
            global _sync_in_progress, _sync_pending
            _sync_in_progress = False
            pending = _sync_pending
            _sync_pending = False

        # 同期中にさらに変更が入っていたら、最後にもう一度だけ実行して追従する
        if pending:
            maybe_schedule_supabase_autosync(csv_path)


def _wait_for_file_stable(path: Path, *, max_wait_seconds: float, stable_window_seconds: float) -> None:
    """
    保存直後の中途半端状態（書き込み中）を避けるため、サイズが安定するまで少し待つ。
    """
    if not path.exists():
        return

    start = time.time()
    last_size = -1
    last_change = time.time()

    while time.time() - start < max_wait_seconds:
        try:
            size = path.stat().st_size
        except OSError:
            time.sleep(0.2)
            continue

        if size != last_size:
            last_size = size
            last_change = time.time()
        else:
            if time.time() - last_change >= stable_window_seconds:
                return

        time.sleep(0.2)


def _sha256_file(path: Path) -> str:
    """
    ファイルのsha256を計算（大きいCSVでもメモリに載せない）
    """
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
