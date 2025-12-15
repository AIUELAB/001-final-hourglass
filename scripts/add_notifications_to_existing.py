#!/usr/bin/env python3
"""
Add Notifications to Existing Scripts

Automatically adds notification functionality to existing data quality
and automation scripts in the project.
"""

import ast
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


class NotificationIntegrator:
    """Integrates notification functionality into existing Python scripts."""

    def __init__(self, project_root: Path) -> None:
        """Initialize the integrator."""
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.backup_dir = project_root / "backups" / "pre_notification_integration"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Scripts to integrate notifications into
        self.target_scripts = [
            "data_quality_audit.py",
            "data_quality_audit_improved.py",
            "auto_quality_check.py",
            "quality_monitor.py",
            "comprehensive_fix_all.py",
            "final_data_integrator.py",
            "advanced_data_collector.py",
        ]

        # Integration patterns
        self.notification_imports = [
            "from src.notification_integration import (",
            "    notification_context,",
            "    notify_data_quality_check,",
            "    notify_data_processing,",
            "    quick_notify_error,",
            "    quick_notify_success,",
            "    quick_notify_warning,",
            "    quick_notify_progress,",
            ")",
        ]

    def find_scripts_to_modify(self) -> List[Path]:
        """Find scripts that should be modified."""
        scripts_to_modify = []

        # Check root directory
        for script_name in self.target_scripts:
            script_path = self.project_root / script_name
            if script_path.exists():
                scripts_to_modify.append(script_path)

        # Check src directory
        if self.src_dir.exists():
            for script_name in self.target_scripts:
                script_path = self.src_dir / script_name
                if script_path.exists():
                    scripts_to_modify.append(script_path)

        return scripts_to_modify

    def backup_script(self, script_path: Path) -> Path:
        """Create a backup of the script."""
        backup_path = self.backup_dir / script_path.name
        shutil.copy2(script_path, backup_path)
        print(f"📦 Backed up {script_path.name} to {backup_path}")
        return backup_path

    def has_notification_imports(self, content: str) -> bool:
        """Check if script already has notification imports."""
        return "notification_integration" in content or "notification_system" in content

    def add_notification_imports(self, content: str) -> str:
        """Add notification imports to the script."""
        lines = content.split("\n")

        # Find the best place to insert imports (after existing imports)
        import_insert_idx = 0
        in_import_section = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            if (
                stripped.startswith("import ")
                or stripped.startswith("from ")
                or stripped.startswith("#")
                or not stripped
            ):
                in_import_section = True
                if stripped and not stripped.startswith("#"):
                    import_insert_idx = i + 1
            elif in_import_section and stripped:
                break

        # Insert notification imports
        import_lines = self.notification_imports + [""]
        lines[import_insert_idx:import_insert_idx] = import_lines

        return "\n".join(lines)

    def find_main_functions(self, content: str) -> List[Tuple[str, int, int]]:
        """Find main functions and their line ranges."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        main_functions = []
        lines = content.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Look for functions that seem like main entry points
                if (
                    node.name in ["main", "run", "execute", "process"]
                    or node.name.endswith("_main")
                    or "main" in node.name.lower()
                ):
                    start_line = node.lineno - 1
                    end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line + 10
                    main_functions.append((node.name, start_line, end_line))

        return main_functions

    def add_function_decorator(self, content: str, func_name: str, decorator: str) -> str:
        """Add a decorator to a specific function."""
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if line.strip().startswith(f"def {func_name}("):
                # Check if already has decorators
                decorator_line = i
                while decorator_line > 0 and (
                    lines[decorator_line - 1].strip().startswith("@") or not lines[decorator_line - 1].strip()
                ):
                    decorator_line -= 1

                # Add decorator
                lines.insert(decorator_line, f"@{decorator}")
                break

        return "\n".join(lines)

    def add_context_manager_wrapper(self, content: str, func_name: str) -> str:
        """Wrap function body with notification context manager."""
        lines = content.split("\n")
        modified = False

        for i, line in enumerate(lines):
            if line.strip().startswith(f"def {func_name}("):
                # Find function body start
                func_start = i
                indent_level = len(line) - len(line.lstrip())

                # Find first line of function body
                body_start = None
                for j in range(i + 1, len(lines)):
                    if (
                        lines[j].strip()
                        and not lines[j].strip().startswith('"""')
                        and not lines[j].strip().startswith("'''")
                    ):
                        body_start = j
                        break

                if body_start:
                    # Add context manager
                    body_indent = "    " * ((indent_level // 4) + 1)
                    context_indent = body_indent + "    "

                    # Insert context manager
                    context_line = f'{body_indent}with notification_context(task_name="{func_name}") as progress:'
                    lines.insert(body_start, context_line)

                    # Indent existing function body
                    j = body_start + 1
                    while j < len(lines):
                        if lines[j].strip() == "":
                            j += 1
                            continue

                        current_indent = len(lines[j]) - len(lines[j].lstrip())
                        if current_indent <= indent_level:
                            break

                        if lines[j].strip():
                            lines[j] = "    " + lines[j]
                        j += 1

                    modified = True
                    break

        return "\n".join(lines) if modified else content

    def add_progress_notifications(self, content: str) -> str:
        """Add progress notifications to loops and key operations."""
        lines = content.split("\n")

        # Pattern for adding progress notifications to loops
        loop_patterns = [
            (r"for\s+\w+\s+in\s+.*:", 'quick_notify_progress("Processing items...")'),
            (r"while\s+.*:", 'quick_notify_progress("Processing...")'),
        ]

        for i, line in enumerate(lines):
            for pattern, notification in loop_patterns:
                if re.search(pattern, line.strip()):
                    indent = "    " * (len(line) - len(line.lstrip()) + 4) // 4 + 4
                    lines.insert(i + 1, f"{indent}{notification}")
                    break

        return "\n".join(lines)

    def add_error_notifications(self, content: str) -> str:
        """Add error notifications to exception handling."""
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if "except" in line.strip() and ":" in line:
                # Find the except block
                indent = "    " * (len(line) - len(line.lstrip()) + 4) // 4 + 4

                # Look for the next non-empty line in the except block
                for j in range(i + 1, len(lines)):
                    if lines[j].strip():
                        # Add error notification
                        error_line = f'{indent}quick_notify_error(f"Error occurred: {{str(e)[:50]}}...")'
                        lines.insert(j, error_line)
                        break

        return "\n".join(lines)

    def integrate_notifications_into_script(self, script_path: Path) -> bool:
        """Integrate notifications into a single script."""
        print(f"🔧 Integrating notifications into {script_path.name}...")

        try:
            # Read the script
            with open(script_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            # Skip if already has notifications
            if self.has_notification_imports(original_content):
                print(f"   ⚠️  {script_path.name} already has notification imports - skipping")
                return True

            # Create backup
            self.backup_script(script_path)

            # Start modifying content
            content = original_content

            # Add imports
            content = self.add_notification_imports(content)

            # Find main functions to decorate
            main_functions = self.find_main_functions(content)

            if main_functions:
                for func_name, start_line, end_line in main_functions:
                    print(f"   📎 Adding notifications to function: {func_name}")

                    # Add appropriate decorator based on function name
                    if "quality" in func_name.lower():
                        content = self.add_function_decorator(content, func_name, "notify_data_quality_check")
                    elif "process" in func_name.lower() or "collect" in func_name.lower():
                        content = self.add_function_decorator(content, func_name, "notify_data_processing")
                    else:
                        # Use context manager wrapper
                        content = self.add_context_manager_wrapper(content, func_name)

            # Add progress and error notifications
            content = self.add_progress_notifications(content)
            content = self.add_error_notifications(content)

            # Write the modified script
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"   ✅ Successfully integrated notifications into {script_path.name}")
            return True

        except Exception as e:
            print(f"   ❌ Error integrating {script_path.name}: {e}")
            return False

    def create_notification_wrapper_scripts(self) -> None:
        """Create wrapper scripts for common tasks."""
        wrappers = {
            "run_with_notifications.py": '''#!/usr/bin/env python3
"""
Universal Notification Wrapper

Runs any Python script with audio notifications for start, success, and error.
Usage: python run_with_notifications.py script_name.py [args...]
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from notification_integration import (
    quick_notify_success,
    quick_notify_error,
    quick_notify_info,
)


def main():
    """Main wrapper function."""
    if len(sys.argv) < 2:
        print("Usage: python run_with_notifications.py script_name.py [args...]")
        sys.exit(1)

    script_path = sys.argv[1]
    script_args = sys.argv[2:]

    # Start notification
    quick_notify_info(f"Starting {script_path}")

    try:
        # Run the script
        result = subprocess.run(
            [sys.executable, script_path] + script_args,
            check=True,
            capture_output=False
        )

        # Success notification
        quick_notify_success(f"Completed {script_path}")
        sys.exit(result.returncode)

    except subprocess.CalledProcessError as e:
        # Error notification
        quick_notify_error(f"Failed {script_path} (exit code {e.returncode})")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        quick_notify_error(f"Interrupted {script_path}")
        sys.exit(1)
    except Exception as e:
        quick_notify_error(f"Error running {script_path}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
''',
            "notify_data_quality.py": '''#!/usr/bin/env python3
"""
Data Quality Notification Wrapper

Specialized wrapper for data quality scripts with detailed progress tracking.
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from notification_integration import (
    notification_context,
    quick_notify_progress,
    quick_notify_success,
    quick_notify_error,
)


def main():
    """Main data quality wrapper."""
    if len(sys.argv) < 2:
        print("Usage: python notify_data_quality.py quality_script.py [args...]")
        sys.exit(1)

    script_path = sys.argv[1]
    script_args = sys.argv[2:]

    with notification_context(task_name=f"data quality check - {script_path}") as progress:
        progress("Initializing quality check")

        try:
            # Run the script with progress monitoring
            process = subprocess.Popen(
                [sys.executable, script_path] + script_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            # Monitor output for progress indicators
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())

                    # Look for progress indicators in output
                    lower_output = output.lower()
                    if any(word in lower_output for word in ['processing', 'checking', 'validating']):
                        progress(output.strip()[:50] + "...")

            # Wait for completion
            return_code = process.poll()

            if return_code == 0:
                progress("Quality check completed successfully")
            else:
                raise subprocess.CalledProcessError(return_code, script_path)

        except subprocess.CalledProcessError as e:
            raise Exception(f"Quality check failed with exit code {e.returncode}")
        except Exception as e:
            raise Exception(f"Error during quality check: {e}")


if __name__ == "__main__":
    main()
''',
        }

        for filename, content in wrappers.items():
            wrapper_path = self.project_root / filename
            with open(wrapper_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Make executable
            wrapper_path.chmod(0o755)
            print(f"📝 Created notification wrapper: {filename}")

    def generate_integration_report(self, results: Dict[str, bool]) -> None:
        """Generate a report of the integration process."""
        report_path = self.project_root / "notification_integration_report.md"

        report_content = f"""# Audio Notification Integration Report

Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Summary

Total scripts processed: {len(results)}
Successfully integrated: {sum(1 for success in results.values() if success)}
Failed integrations: {sum(1 for success in results.values() if not success)}

## Integration Results

"""

        for script_name, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            report_content += f"- **{script_name}**: {status}\n"

        report_content += f"""

## Files Created

- `src/notification_system.py` - Core notification system
- `src/notification_integration.py` - Integration utilities
- `examples/notification_examples.py` - Usage examples
- `test_notifications.py` - Comprehensive tests
- `scripts/setup_notifications.sh` - Setup script
- `.env.notifications.example` - Configuration template
- `run_with_notifications.py` - Universal wrapper
- `notify_data_quality.py` - Data quality wrapper

## Backups

Original scripts backed up to: `{self.backup_dir}`

## Usage

### Quick Start
```bash
# Setup notifications
./scripts/setup_notifications.sh

# Test the system
python test_notifications.py

# Run any script with notifications
python run_with_notifications.py your_script.py
```

### In Python Code
```python
from src.notification_integration import quick_notify_success
quick_notify_success("Task completed!")
```

### Configuration
Copy `.env.notifications.example` to `.env.notifications` and customize settings.

## Next Steps

1. Run the setup script to install dependencies
2. Test the notification system
3. Configure notification preferences in `.env.notifications`
4. Review and test the modified scripts
5. Add custom sound files to the `sounds/` directory if desired

## Troubleshooting

If notifications don't work:
1. Check audio system with `./scripts/setup_notifications.sh`
2. Verify configuration in `.env.notifications`
3. Test with `python test_notifications.py`
4. Check logs for error messages

For platform-specific issues, see the notification system documentation.
"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"📊 Generated integration report: {report_path}")

    def run_integration(self) -> None:
        """Run the complete integration process."""
        print("🎵 Audio Notification Integration Tool")
        print("=" * 60)
        print("This will add audio notifications to your existing scripts.")
        print(f"Backups will be created in: {self.backup_dir}")

        # Find scripts to modify
        scripts_to_modify = self.find_scripts_to_modify()

        if not scripts_to_modify:
            print("⚠️  No target scripts found to modify.")
            print("Target scripts:", ", ".join(self.target_scripts))
            return

        print(f"\n📋 Found {len(scripts_to_modify)} scripts to modify:")
        for script in scripts_to_modify:
            print(f"  - {script.name}")

        # Confirm with user
        response = input("\nProceed with integration? [y/N]: ").strip().lower()
        if response not in ["y", "yes"]:
            print("❌ Integration cancelled.")
            return

        # Integrate notifications into each script
        results = {}
        for script_path in scripts_to_modify:
            results[script_path.name] = self.integrate_notifications_into_script(script_path)

        # Create wrapper scripts
        print("\n📝 Creating notification wrapper scripts...")
        self.create_notification_wrapper_scripts()

        # Generate report
        self.generate_integration_report(results)

        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)

        print("\n🎉 Integration completed!")
        print(f"   Successfully modified: {successful}/{total} scripts")
        print(f"   Backups created in: {self.backup_dir}")
        print("   Report generated: notification_integration_report.md")

        print("\n📋 Next steps:")
        print("   1. Run: ./scripts/setup_notifications.sh")
        print("   2. Test: python test_notifications.py")
        print("   3. Configure: cp .env.notifications.example .env.notifications")
        print("   4. Test modified scripts")


def main() -> None:
    """Main function."""
    project_root = Path.cwd()
    integrator = NotificationIntegrator(project_root)
    integrator.run_integration()


if __name__ == "__main__":
    main()
