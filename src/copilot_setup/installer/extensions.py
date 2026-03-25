"""VS Code extension installation."""

from __future__ import annotations

import subprocess

from copilot_setup.installer.tui import (
    show_error,
    show_info,
    show_success,
    show_warning,
)
from copilot_setup.models import Extension


def _get_installed_extensions() -> set[str]:
    """Fetch the full set of installed extensions once (lowercase IDs)."""
    try:
        result = subprocess.run(
            "code --list-extensions",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {ext.strip().lower() for ext in result.stdout.splitlines() if ext.strip()}
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return set()


def install_extension(ext: Extension) -> bool:
    """Install a single VS Code extension. Returns True on success."""
    try:
        result = subprocess.run(
            f"code --install-extension {ext.id} --force",
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def handle_extensions(
    extensions: list[Extension],
) -> tuple[list[str], list[str], list[str]]:
    """
    Install all extensions from the profile.
    Returns (succeeded, skipped, failed) lists of display names.
    """
    succeeded: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    # Fetch installed extensions once instead of per-extension
    installed = _get_installed_extensions()

    for ext in extensions:
        if ext.id.lower() in installed:
            show_success(f"{ext.name} — already installed")
            succeeded.append(ext.name)
            continue

        show_info(f"Installing {ext.name}...")
        if ext.description:
            show_info(f"  {ext.description}")

        if install_extension(ext):
            show_success(f"{ext.name} — installed!")
            succeeded.append(ext.name)
        else:
            if ext.required:
                show_error(f"{ext.name} — installation failed")
                failed.append(ext.name)
            else:
                show_warning(f"{ext.name} — could not install (optional)")
                skipped.append(ext.name)

    return succeeded, skipped, failed
