"""Post-install verification to confirm the environment is working."""

from __future__ import annotations

import subprocess

from copilot_setup.installer.prereqs import refresh_path
from copilot_setup.installer.tui import show_error, show_info, show_success, show_warning
from copilot_setup.models import Profile


def _check(label: str, command: str) -> bool:
    """Run a check command and report the result."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, timeout=15)
        if result.returncode == 0:
            show_success(f"{label} — OK")
            return True
        show_warning(f"{label} — not responding")
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        show_warning(f"{label} — not found")
        return False


def verify_environment(profile: Profile) -> tuple[list[str], list[str]]:
    """
    Run a final verification pass over all installed components.
    Returns (passed, issues) lists of check descriptions.
    """
    passed: list[str] = []
    issues: list[str] = []

    show_info("Running final checks...\n")

    # Refresh PATH so tools installed during this session are visible
    refresh_path()

    # Verify prerequisites
    for prereq in profile.prerequisites:
        if _check(prereq.display_name, prereq.check_command):
            passed.append(prereq.display_name)
        elif prereq.required:
            issues.append(prereq.display_name)

    # Verify setup steps that have verify_commands
    for step in profile.setup_steps:
        if step.verify_command:
            if _check(step.description, step.verify_command):
                passed.append(step.description)
            else:
                issues.append(step.description)

    return passed, issues
