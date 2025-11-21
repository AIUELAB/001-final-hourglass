"""同期サービス: JSON の読み込み、検証、出力保存。

想定フロー:
1) エクスポートした Projects JSON を読み取り
2) `ProjectModel` に変換
3) リポジトリ内の出力先へ正規化 JSON と Markdown を保存
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from loguru import logger
from rich.console import Console
from rich.panel import Panel

from .models import ParseResult, ProjectModel, coerce_to_project

console = Console()


def load_json(path: Path) -> Dict:
    """JSON ファイルを厳格に読み込む。

    エラーは例外として送出。上位でハンドリングする。
    """
    if not path.exists():
        raise FileNotFoundError(f"JSON not found: {path}")
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def render_markdown(project: ProjectModel) -> str:
    """`ProjectModel` から簡易ドキュメントを Markdown 生成。"""
    lines: list[str] = []
    lines.append(f"# {project.name}")
    if project.description:
        lines.append("")
        lines.append(project.description)
    lines.append("")
    lines.append("## Items")
    for item in project.items:
        title = item.title or item.id
        lines.append(f"- [{item.type}] {title}")
    if project.resources:
        lines.append("")
        lines.append("## Resources")
        for res in project.resources:
            title = res.title or res.id
            if res.url:
                lines.append(f"- {title}: {res.url}")
            else:
                lines.append(f"- {title}")
    return "\n".join(lines) + "\n"


def save_outputs(project: ProjectModel, out_dir: Path) -> Tuple[Path, Path, Path]:
    """正規化 JSON、Markdown、raw JSON を保存する。"""
    out_dir.mkdir(parents=True, exist_ok=True)

    normalized_path = out_dir / f"{project.id}__normalized.json"
    markdown_path = out_dir / f"{project.id}.md"
    raw_path = out_dir / f"{project.id}__raw.json"

    normalized_path.write_text(project.model_dump_json(indent=2, by_alias=False, exclude_none=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(project), encoding="utf-8")
    raw_path.write_text(json.dumps(project.raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return normalized_path, markdown_path, raw_path


def sync_from_json(input_json: Path, output_dir: Path) -> ParseResult:
    """エクスポート JSON から同期処理を実行。"""
    console.print(Panel.fit(f"Sync start: {input_json}", title="Projects Sync"))
    data = load_json(input_json)
    result = coerce_to_project(data)

    if not result.success or not result.project:
        logger.error("Project parse failed")
        for err in result.errors:
            logger.error(err)
        # Return early with failure result
        return result

    project = result.project
    normalized_path, markdown_path, raw_path = save_outputs(project, output_dir)
    console.print(f"[green]✓ Saved[/green] {normalized_path}")
    console.print(f"[green]✓ Saved[/green] {markdown_path}")
    console.print(f"[green]✓ Saved[/green] {raw_path}")

    for warn in result.warnings:
        logger.warning(warn)

    # Return success result with project
    return ParseResult(success=True, project=project, errors=result.errors, warnings=result.warnings)
