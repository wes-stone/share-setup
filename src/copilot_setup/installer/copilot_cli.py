"""Bootstrap GitHub Copilot CLI so team members can get AI help from the terminal."""

from __future__ import annotations

import subprocess

from copilot_setup.installer.prereqs import refresh_path
from copilot_setup.installer.tui import (
    prompt_continue,
    prompt_yes_no,
    show_error,
    show_info,
    show_success,
    show_warning,
)


def _cmd_ok(command: str, timeout: int = 15) -> bool:
    """Return True if *command* exits 0."""
    try:
        return subprocess.run(
            command, shell=True, capture_output=True, timeout=timeout
        ).returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _install_gh() -> bool:
    """Install GitHub CLI via winget."""
    show_info("Installing GitHub CLI — this may take a moment...")
    show_info("You may see installer output below.\n")
    try:
        result = subprocess.run(
            "winget install GitHub.cli --accept-package-agreements --accept-source-agreements",
            shell=True,
            timeout=300,
        )
        refresh_path()
        return result.returncode == 0 and _cmd_ok("gh --version")
    except subprocess.TimeoutExpired:
        show_error("GitHub CLI installation timed out.")
        return False


def _install_copilot_extension() -> bool:
    """Install the gh-copilot extension."""
    show_info("Installing GitHub Copilot CLI extension...")
    try:
        result = subprocess.run(
            "gh extension install github/gh-copilot",
            shell=True,
            capture_output=True,
            timeout=120,
        )
        if result.returncode == 0:
            return True
        # May already be installed — check directly
        return _cmd_ok("gh copilot --version")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def ensure_copilot_cli() -> bool:
    """
    Make sure GitHub CLI + Copilot extension are available.

    Runs early in the wizard so users can get AI help if anything
    goes wrong later.  Returns True if Copilot CLI is ready.
    """
    # ── 1. GitHub CLI ───────────────────────────────────────
    if _cmd_ok("gh --version"):
        show_success("GitHub CLI — ready")
    else:
        show_warning("GitHub CLI (gh) is not installed.")
        show_info("The GitHub CLI lets you get AI help from your terminal.")
        if not prompt_yes_no("Install GitHub CLI now?"):
            show_warning("Skipped — you can install it later from https://cli.github.com")
            return False
        if not _install_gh():
            show_error("Could not install GitHub CLI.")
            show_info("Install manually: https://cli.github.com")
            prompt_continue("Press Enter to continue setup anyway...")
            return False
        show_success("GitHub CLI — installed!")

    # ── 2. Auth ─────────────────────────────────────────────
    if _cmd_ok("gh auth status"):
        show_success("GitHub auth — signed in")
    else:
        show_info("You need to sign in to GitHub CLI.")
        show_info("A browser window will open — follow the prompts to sign in.\n")
        if not prompt_continue("Press Enter to sign in to GitHub..."):
            show_warning("Skipped GitHub sign-in — some features may not work.")
        else:
            try:
                subprocess.run("gh auth login --web", shell=True, timeout=300)
                refresh_path()
            except (subprocess.TimeoutExpired, OSError):
                pass

            if _cmd_ok("gh auth status"):
                show_success("GitHub auth — signed in!")
            else:
                show_warning("GitHub sign-in could not be verified. Continuing anyway.")

    # ── 3. Copilot extension ────────────────────────────────
    if _cmd_ok("gh copilot --version"):
        show_success("GitHub Copilot CLI — ready")
        return True

    show_info("Installing GitHub Copilot CLI extension (one-time setup)...")
    if _install_copilot_extension():
        show_success("GitHub Copilot CLI — ready!")
        return True

    show_warning(
        "Could not install the Copilot CLI extension. "
        "You can install it later with: gh extension install github/gh-copilot"
    )
    return False
