"""iOS Release CLI - Local release automation for FinalHourglass."""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import load_config

console = Console()

ALL_STEPS = ["validate", "version", "archive", "export", "upload", "metadata", "submit", "report"]
PHASE1_STEPS = ["validate", "archive", "report"]
PHASE2_STEPS = ["validate", "version", "archive", "export", "upload", "report"]
PHASE3_STEPS = ["validate", "version", "archive", "export", "upload", "metadata", "submit", "report"]


def resolve_project_root() -> Path:
    """Find the ios-apps/final-hourglass project root."""
    # Check if we're already in the project root
    cwd = Path.cwd()
    if (cwd / "FinalHourglass.xcworkspace").exists():
        return cwd
    # Check relative to repo root
    candidates = [
        cwd / "ios-apps" / "final-hourglass",
        cwd.parent / "ios-apps" / "final-hourglass",
    ]
    for candidate in candidates:
        if (candidate / "FinalHourglass.xcworkspace").exists():
            return candidate.resolve()
    raise click.UsageError(
        "Could not find FinalHourglass project root. "
        "Run from the repo root or ios-apps/final-hourglass, or pass --project-root."
    )


def emit_ci_outputs(step_name: str, result: dict[str, Any]) -> None:
    """Emit step results to GITHUB_OUTPUT."""
    from .utils.ci import write_output

    output_map: dict[str, list[str]] = {
        "version": ["new_version", "new_build"],
        "archive": ["archive_path"],
        "export": ["ipa_path", "export_dir"],
        "upload": ["upload_status"],
    }
    keys = output_map.get(step_name, [])
    for key in keys:
        value = result.get(key)
        if value:
            write_output(key, str(value))


@click.command()
@click.option("--dry-run", "mode", flag_value="dry-run", default=True, help="Validate without side effects (default)")
@click.option("--execute", "mode", flag_value="execute", help="Execute release steps")
@click.option("--step", multiple=True, type=click.Choice(ALL_STEPS), help="Run specific steps only")
@click.option("--version", "release_version", default=None, help="Release version (e.g., 1.0.1)")
@click.option("--whats-new", default="", help="What's New text for App Store (required for metadata --execute)")
@click.option("--project-root", default=None, type=click.Path(exists=True), help="Project root path")
@click.option(
    "--export-options-plist", default=None, type=click.Path(exists=True), help="Override ExportOptions.plist path (CI)"
)
@click.option("--build-number", default=None, type=int, help="Build number (CI-generated)")
@click.option("--ci", "ci_mode", is_flag=True, default=False, help="CI output mode (GITHUB_OUTPUT, no color)")
def main(
    mode: str,
    step: tuple[str, ...],
    release_version: str | None,
    whats_new: str,
    project_root: str | None,
    export_options_plist: str | None,
    build_number: int | None,
    ci_mode: bool,
) -> None:
    """iOS Release CLI for FinalHourglass."""
    dry_run = mode == "dry-run"

    # CI mode: suppress rich colors, use plain output
    global console
    if ci_mode:
        console = Console(force_terminal=False, no_color=True)

    # Resolve project root
    if project_root:
        root = Path(project_root)
    else:
        root = resolve_project_root()

    # Determine steps to run
    steps = list(step) if step else PHASE3_STEPS

    # Validate unimplemented steps
    implemented = {"validate", "version", "archive", "export", "upload", "metadata", "submit", "report"}
    unimplemented = [s for s in steps if s not in implemented]
    if unimplemented:
        console.print(f"[yellow]Steps not yet implemented (Phase 3): {', '.join(unimplemented)}[/yellow]")
        steps = [s for s in steps if s in implemented]
        if not steps:
            console.print("[red]No executable steps remaining[/red]")
            sys.exit(1)

    # Display header
    mode_label = "[yellow]DRY-RUN[/yellow]" if dry_run else "[green]EXECUTE[/green]"
    version_label = release_version or "not specified"
    console.print(
        Panel(
            f"Mode: {mode_label}\n" f"Version: {version_label}\n" f"Steps: {', '.join(steps)}\n" f"Project: {root}",
            title="iOS Release CLI",
            border_style="blue",
        )
    )

    # Load config
    config, config_errors, config_warnings = load_config(root, dry_run=dry_run)

    for w in config_warnings:
        console.print(f"  [yellow]WARNING:[/yellow] {w}")
    if config_errors:
        for e in config_errors:
            console.print(f"  [red]ERROR:[/red] {e}")
        console.print("[red]Configuration errors found. Aborting.[/red]")
        sys.exit(1)

    # Execute steps
    results: dict[str, dict[str, Any]] = {}
    start_time = time.time()

    for step_name in steps:
        console.rule(f"Step: {step_name}")
        step_start = time.time()

        result: dict[str, Any] = {}
        try:
            if step_name == "validate":
                from .steps.validate import run_validate

                result = run_validate(config, release_version=release_version)
            elif step_name == "version":
                from .steps.version import run_version

                result = run_version(
                    config,
                    release_version=release_version,
                    build_number=str(build_number) if build_number is not None else None,
                    dry_run=dry_run,
                )
            elif step_name == "archive":
                from .steps.archive import run_archive

                # Pass version info from version step if available
                version_result = results.get("version", {})
                result = run_archive(
                    config,
                    release_version=version_result.get("new_version") or release_version,
                    build_number=str(build_number) if build_number is not None else version_result.get("new_build"),
                    dry_run=dry_run,
                )
            elif step_name == "export":
                from .steps.export_ipa import run_export

                archive_result = results.get("archive", {})
                if not dry_run and "archive" not in results:
                    result = {"success": False, "error": "Export requires archive step to run first"}
                elif not dry_run and not archive_result.get("success"):
                    result = {"success": False, "error": "Cannot export: archive step did not succeed"}
                else:
                    result = run_export(
                        config,
                        archive_path=archive_result.get("archive_path", ""),
                        export_options_override=export_options_plist,
                        dry_run=dry_run,
                    )
            elif step_name == "upload":
                from .steps.upload import run_upload

                export_result = results.get("export", {})
                if not dry_run and "export" not in results:
                    result = {"success": False, "error": "Upload requires export step to run first"}
                elif not dry_run and not export_result.get("success"):
                    result = {"success": False, "error": "Cannot upload: export step did not succeed"}
                else:
                    result = run_upload(
                        config,
                        ipa_path=export_result.get("ipa_path", ""),
                        dry_run=dry_run,
                    )
            elif step_name == "metadata":
                from .steps.metadata import run_metadata

                if not dry_run and "upload" in steps and not results.get("upload", {}).get("success"):
                    result = {"success": False, "error": "Cannot update metadata: upload step did not succeed"}
                else:
                    result = run_metadata(
                        config,
                        whats_new=whats_new,
                        release_version=release_version,
                        dry_run=dry_run,
                    )
            elif step_name == "submit":
                from .steps.submit import run_submit

                if not dry_run and "metadata" in steps and not results.get("metadata", {}).get("success"):
                    result = {"success": False, "error": "Cannot submit: metadata step did not succeed"}
                else:
                    result = run_submit(
                        config,
                        dry_run=dry_run,
                    )
            elif step_name == "report":
                from .steps.report import run_report

                result = run_report(
                    config,
                    results=results,
                    release_version=release_version,
                    dry_run=dry_run,
                    total_duration=time.time() - start_time,
                )
            else:
                result = {"success": False, "error": f"Step '{step_name}' not implemented"}
        except Exception as e:
            tb = traceback.format_exc()
            console.print(f"  [dim]{tb}[/dim]")
            result = {"success": False, "error": f"{type(e).__name__}: {e}"}

        step_duration = time.time() - step_start
        result["duration"] = round(step_duration, 2)
        results[step_name] = result

        if result.get("success"):
            console.print(f"  [green]OK[/green] ({step_duration:.1f}s)")
            # CI output: emit key values to GITHUB_OUTPUT
            if ci_mode:
                emit_ci_outputs(step_name, result)
        else:
            console.print(f"  [red]FAILED[/red]: {result.get('error', 'Unknown error')}")
            console.print("[red]Aborting due to step failure.[/red]")
            sys.exit(1)

    # Summary
    total_duration = time.time() - start_time
    summary = Table(title="Release Summary")
    summary.add_column("Step", style="cyan")
    summary.add_column("Status")
    summary.add_column("Duration")
    for name, res in results.items():
        status = "[green]OK[/green]" if res.get("success") else "[red]FAILED[/red]"
        summary.add_row(name, status, f"{res.get('duration', 0):.1f}s")
    console.print(summary)
    console.print(f"\nTotal duration: {total_duration:.1f}s")

    if "report" in results and results["report"].get("report_path"):
        console.print(f"Report: {results['report']['report_path']}")


if __name__ == "__main__":
    main()
