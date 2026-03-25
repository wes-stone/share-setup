"""Prerequisite detection and installation for Windows."""

from __future__ import annotations

import os
import subprocess

from copilot_setup.installer.tui import (
    console,
    prompt_continue,
    prompt_yes_no,
    show_error,
    show_guidance,
    show_info,
    show_success,
    show_warning,
)
from copilot_setup.models import Prerequisite


def refresh_path():
    """Merge registry PATH updates into the current process environment."""
    try:
        current_dirs = set(os.environ.get("PATH", "").split(";"))
        new_dirs: list[str] = []

        for source in ("HKCU\\Environment", "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"):
            result = subprocess.run(
                f'reg query "{source}" /v Path',
                shell=True, capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "REG_" in line:
                        val = line.split("REG_SZ", 1)[-1].split("REG_EXPAND_SZ", 1)[-1].strip()
                        for d in val.split(";"):
                            d = d.strip()
                            if d and d not in current_dirs:
                                new_dirs.append(d)
                                current_dirs.add(d)

        if new_dirs:
            os.environ["PATH"] = os.environ.get("PATH", "") + ";" + ";".join(new_dirs)
    except Exception:
        pass  # best-effort — failing to refresh PATH is not fatal


def check_installed(prereq: Prerequisite) -> bool:
    """Return True if a prerequisite is already present."""
    try:
        result = subprocess.run(
            prereq.check_command,
            shell=True,
            capture_output=True,
            timeout=15,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def install_prerequisite(prereq: Prerequisite) -> bool:
    """Attempt to install a single prerequisite. Returns True on success."""
    console.print(f"\n  [step]📦[/] Installing [bold]{prereq.display_name}[/]")
    console.print(f"     {prereq.description}\n")

    if prereq.install_command:
        if not prompt_yes_no(f"Install {prereq.display_name} automatically?"):
            if prereq.install_url:
                show_info(f"You can install it manually: {prereq.install_url}")
            return False

        show_info("Installing — this may take a moment...")
        show_info("You may see installer output below.\n")
        try:
            # Use inherited stdio so the user can see progress and respond to prompts
            result = subprocess.run(
                prereq.install_command,
                shell=True,
                timeout=300,
            )
            # Refresh PATH so the new tool is visible immediately
            refresh_path()

            if result.returncode == 0:
                show_success(f"{prereq.display_name} installed successfully!")
                return True
            else:
                show_error("Installation returned an error.")
                if prereq.install_url:
                    show_info(f"Try installing manually: {prereq.install_url}")
                return False
        except subprocess.TimeoutExpired:
            show_error("Installation timed out.")
            if prereq.install_url:
                show_info(f"Try installing manually: {prereq.install_url}")
            return False

    elif prereq.install_url:
        show_info("This tool needs to be installed manually.")
        show_info(f"Download: {prereq.install_url}")
        if prereq.guidance:
            show_guidance(prereq.guidance)
        prompt_continue("Install it now, then press Enter to continue...")
        refresh_path()
        return check_installed(prereq)

    else:
        show_warning(f"No automatic installer available for {prereq.display_name}.")
        if prereq.guidance:
            show_guidance(prereq.guidance)
        return False


def handle_prerequisites(
    prerequisites: list[Prerequisite],
) -> tuple[list[str], list[str], list[str]]:
    """
    Check and install all prerequisites.
    Returns (succeeded, skipped, failed) lists of display names.
    """
    succeeded: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    for prereq in prerequisites:
        if check_installed(prereq):
            show_success(f"{prereq.display_name} — already installed")
            succeeded.append(prereq.display_name)
            continue

        if not prereq.required:
            show_info(f"{prereq.display_name} — optional, not found")
            if prompt_yes_no(f"Would you like to install {prereq.display_name}?", default=False):
                if install_prerequisite(prereq):
                    succeeded.append(prereq.display_name)
                else:
                    skipped.append(prereq.display_name)
            else:
                skipped.append(prereq.display_name)
            continue

        # Required and missing
        show_warning(f"{prereq.display_name} — required but not found")
        if install_prerequisite(prereq):
            succeeded.append(prereq.display_name)
        else:
            # Verify again in case a manual install happened
            refresh_path()
            if check_installed(prereq):
                succeeded.append(prereq.display_name)
            else:
                failed.append(prereq.display_name)

    return succeeded, skipped, failed
