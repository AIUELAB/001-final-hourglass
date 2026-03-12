"""Step 8: Report - Generate Markdown release report."""
from __future__ import annotations

from datetime import datetime

from ..config import ReleaseConfig


def run_report(
    config: ReleaseConfig,
    *,
    results: dict[str, dict[str, object]],
    release_version: str | None = None,
    dry_run: bool = True,
    total_duration: float = 0.0,
) -> dict[str, object]:
    """Generate a Markdown release report.

    Reports are saved to src/reports/ios/ relative to the repository root.
    Sensitive information (API keys, etc.) is never included.
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    mode_label = "DRY-RUN" if dry_run else "EXECUTE"

    # Find repo root (parent of ios-apps/)
    repo_root = config.project_root.parent.parent
    report_dir = repo_root / "src" / "reports" / "ios"
    report_dir.mkdir(parents=True, exist_ok=True)

    filename = f"release_report_{timestamp}.md"
    report_path = report_dir / filename

    lines: list[str] = []
    lines.append(f"# iOS Release Report ({mode_label})")
    lines.append("")
    lines.append(f"- **Date**: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **Mode**: {mode_label}")
    lines.append(f"- **Version**: {release_version or 'not specified'}")
    lines.append(f"- **Total Duration**: {total_duration:.1f}s")
    lines.append("")

    # Step results
    lines.append("## Step Results")
    lines.append("")
    lines.append("| Step | Status | Duration |")
    lines.append("|------|--------|----------|")

    all_success = True
    for step_name, result in results.items():
        success = result.get("success", False)
        if not success:
            all_success = False
        status = "OK" if success else "FAILED"
        duration = result.get("duration", 0)
        if isinstance(duration, (int, float)):
            duration_str = f"{duration:.1f}s"
        else:
            duration_str = str(duration)
        lines.append(f"| {step_name} | {status} | {duration_str} |")

    lines.append("")

    # Errors section
    has_errors = False
    for step_name, result in results.items():
        step_errors = result.get("errors", [])
        error_msg = result.get("error", "")
        if step_errors or error_msg:
            if not has_errors:
                lines.append("## Errors")
                lines.append("")
                has_errors = True
            lines.append(f"### {step_name}")
            lines.append("")
            if isinstance(step_errors, list):
                for err in step_errors:
                    lines.append(f"- {err}")
            if error_msg:
                lines.append(f"- {error_msg}")
            lines.append("")

    # Warnings section
    has_warnings = False
    for step_name, result in results.items():
        step_warnings = result.get("warnings", [])
        if step_warnings and isinstance(step_warnings, list) and len(step_warnings) > 0:
            if not has_warnings:
                lines.append("## Warnings")
                lines.append("")
                has_warnings = True
            lines.append(f"### {step_name}")
            lines.append("")
            for warn in step_warnings:
                lines.append(f"- {warn}")
            lines.append("")

    # Overall result
    lines.append("## Overall")
    lines.append("")
    if all_success:
        lines.append(f"All steps completed successfully ({mode_label}).")
    else:
        lines.append("Some steps failed. See errors above.")
    lines.append("")

    # Write report
    content = "\n".join(lines)
    report_path.write_text(content, encoding="utf-8")

    return {
        "success": True,
        "report_path": str(report_path),
    }
