"""xcodebuild subprocess wrapper."""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

console = Console()


@dataclass
class XcodebuildResult:
    """Result of an xcodebuild invocation."""
    success: bool
    return_code: int
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    command: list[str] = field(default_factory=list)


def run_xcodebuild(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 600,
    stream_output: bool = True,
) -> XcodebuildResult:
    """Run xcodebuild with the given arguments.

    Args:
        args: Arguments to pass to xcodebuild.
        cwd: Working directory.
        timeout: Timeout in seconds (default 10 minutes).
        stream_output: Whether to stream stdout in real-time.

    Returns:
        XcodebuildResult with success status, output, and duration.
    """
    cmd = ["xcodebuild"] + args
    start = time.time()

    try:
        if stream_output:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout_lines: list[str] = []
            assert process.stdout is not None
            for line in process.stdout:
                stdout_lines.append(line)
                # Show key build events
                stripped = line.strip()
                if any(
                    marker in stripped
                    for marker in [
                        "Build Succeeded",
                        "Build Failed",
                        "ARCHIVE SUCCEEDED",
                        "ARCHIVE FAILED",
                        "** ARCHIVE",
                        "** BUILD",
                        "error:",
                        "warning:",
                    ]
                ):
                    console.print(f"  [dim]{stripped}[/dim]")

            process.wait(timeout=timeout)
            stderr = process.stderr.read() if process.stderr else ""
            stdout = "".join(stdout_lines)
            return_code = process.returncode
        else:
            completed = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            return_code = completed.returncode

        duration = time.time() - start

        return XcodebuildResult(
            success=return_code == 0,
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            command=cmd,
        )

    except subprocess.TimeoutExpired:
        try:
            process.kill()  # type: ignore[possibly-undefined]
            process.communicate()
        except (NameError, OSError):
            pass
        duration = time.time() - start
        return XcodebuildResult(
            success=False,
            return_code=-1,
            stderr=f"xcodebuild timed out after {timeout}s (process killed)",
            duration=duration,
            command=cmd,
        )
    except OSError as e:
        err_msg = f"xcodebuild not found. Is Xcode installed?" if isinstance(e, FileNotFoundError) else f"OS error running xcodebuild: {e}"
        return XcodebuildResult(
            success=False,
            return_code=-1,
            stderr=err_msg,
            duration=time.time() - start,
            command=cmd,
        )
