"""CLI エントリポイント（Click）。

使い方:
  $ python src/main.py sync-projects --input exported.json --out-dir docs/projects
"""

from __future__ import annotations

from pathlib import Path

import click
from loguru import logger

from .service import sync_from_json


@click.command(name="sync-projects")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="エクスポート JSON のパス",
)
@click.option(
    "--out-dir", "out_dir", required=True, type=click.Path(path_type=Path, file_okay=False), help="出力先ディレクトリ"
)
def cli_sync_projects(input_path: Path, out_dir: Path) -> None:
    """Projects エクスポート JSON を正規化して保存する。"""
    try:
        result = sync_from_json(input_path, out_dir)
        if not result.success:
            raise click.ClickException("同期に失敗しました。ログを確認してください。")
    except Exception as e:
        logger.error(f"sync-projects error: {e}")
        raise click.ClickException(str(e))
