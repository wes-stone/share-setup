"""Main installer orchestrator — ties all setup phases together."""

from __future__ import annotations

import sys
from pathlib import Path

from copilot_setup.installer.copilot_cli import ensure_copilot_cli
from copilot_setup.installer.extensions import handle_extensions
from copilot_setup.installer.guided import handle_setup_steps
from copilot_setup.installer.mcp import handle_mcp_servers
from copilot_setup.installer.prereqs import handle_prerequisites
from copilot_setup.installer.copilot_config import handle_copilot_config
from copilot_setup.installer.troubleshoot import show_help_options, write_setup_state
from copilot_setup.installer.tui import (
    console,
    prompt_continue,
    show_step_header,
    show_summary,
    show_welcome,
)
from copilot_setup.installer.verify import verify_environment
from copilot_setup.models import Profile


def _has_copilot_assets(profile: Profile, bundle_dir: Path) -> bool:
    """Check if the profile has any Copilot config to apply."""
    if profile.copilot_instructions_file:
        return True
    copilot_dir = bundle_dir / "copilot"
    extensions_dir = bundle_dir / "extensions"
    has_copilot = copilot_dir.exists() and any(copilot_dir.rglob("*"))
    has_extensions = extensions_dir.exists() and any(extensions_dir.rglob("*"))
    return has_copilot or has_extensions


def _build_step_overview(profile: Profile, bundle_dir: Path) -> list[str]:
    """Build a human-readable list of what the wizard will do."""
    steps = ["Set up GitHub Copilot CLI for terminal help"]
    steps.append("Check your system for required tools")
    if profile.prerequisites:
        steps.append("Install any missing tools")
    if profile.extensions:
        steps.append("Set up VS Code extensions")
    if profile.mcp_servers:
        steps.append("Configure AI assistant connections")
    if _has_copilot_assets(profile, bundle_dir):
        steps.append("Install Copilot team configuration (instructions, skills, extensions)")
    if profile.setup_steps:
        steps.append("Walk you through first-time sign-ins")
    steps.append("Verify everything is working")
    return steps


def run_installer(profile_path: Path):
    """Run the full guided installer from a profile TOML file."""
    # Load profile
    try:
        profile = Profile.from_toml_path(profile_path)
    except Exception as exc:
        console.print(f"\n  [error]✗[/]  Could not load profile: {exc}\n")
        sys.exit(1)

    all_succeeded: list[str] = []
    all_skipped: list[str] = []
    all_failed: list[str] = []
    copilot_cli_ok = False

    # Calculate total phases for step numbering
    bundle_dir = profile_path.parent
    phases: list[str] = ["copilot_cli"]  # always first
    if profile.prerequisites:
        phases.append("prereqs")
    if profile.extensions:
        phases.append("extensions")
    if profile.mcp_servers:
        phases.append("mcp")
    if _has_copilot_assets(profile, bundle_dir):
        phases.append("copilot_config")
    if profile.setup_steps:
        phases.append("steps")
    phases.append("verify")
    total = len(phases)
    current = 0

    # ── Welcome ──────────────────────────────────────────────
    overview = _build_step_overview(profile, bundle_dir)
    show_welcome(profile.name, profile.description, profile.author, overview)

    if not prompt_continue("Press Enter to begin setup..."):
        console.print("\n  [muted]Setup cancelled.[/]\n")
        sys.exit(0)

    # ── Copilot CLI Bootstrap ────────────────────────────────
    if "copilot_cli" in phases:
        current += 1
        show_step_header(current, total, "Setting Up Copilot CLI")
        copilot_cli_ok = ensure_copilot_cli()
        if copilot_cli_ok:
            all_succeeded.append("GitHub Copilot CLI")
        else:
            all_skipped.append("GitHub Copilot CLI")

    # ── Prerequisites ────────────────────────────────────────
    if "prereqs" in phases:
        current += 1
        show_step_header(current, total, "Checking Required Tools")
        ok, skip, fail = handle_prerequisites(profile.prerequisites)
        all_succeeded.extend(ok)
        all_skipped.extend(skip)
        all_failed.extend(fail)

        if fail:
            console.print(
                "\n  [warning]Some required tools could not be installed.[/]\n"
                "  You can re-run this wizard after installing them manually.\n"
            )
            if not prompt_continue("Press Enter to continue anyway, or Ctrl-C to stop..."):
                _dump_and_exit(profile, bundle_dir, all_succeeded, all_skipped, all_failed, copilot_cli_ok)

    # ── Extensions ───────────────────────────────────────────
    if "extensions" in phases:
        current += 1
        show_step_header(current, total, "Setting Up VS Code Extensions")
        ok, skip, fail = handle_extensions(profile.extensions)
        all_succeeded.extend(ok)
        all_skipped.extend(skip)
        all_failed.extend(fail)

    # ── MCP Servers ──────────────────────────────────────────
    if "mcp" in phases:
        current += 1
        show_step_header(current, total, "Configuring AI Assistants")
        ok, skip, fail = handle_mcp_servers(profile.mcp_servers)
        all_succeeded.extend(ok)
        all_skipped.extend(skip)
        all_failed.extend(fail)

    # ── Copilot Configuration ────────────────────────────────
    if "copilot_config" in phases:
        current += 1
        show_step_header(current, total, "Copilot Team Configuration")
        ok, skip, fail = handle_copilot_config(
            bundle_dir, profile.copilot_instructions_file
        )
        all_succeeded.extend(ok)
        all_skipped.extend(skip)
        all_failed.extend(fail)

    # ── Guided Steps ─────────────────────────────────────────
    if "steps" in phases:
        current += 1
        show_step_header(current, total, "First-Time Setup")
        ok, skip, fail = handle_setup_steps(profile.setup_steps)
        all_succeeded.extend(ok)
        all_skipped.extend(skip)
        all_failed.extend(fail)

    # ── Verification ─────────────────────────────────────────
    current += 1
    show_step_header(current, total, "Final Verification")
    passed, issues = verify_environment(profile)
    # Don't double-count — verification is a summary
    if issues:
        all_failed.extend([f"Verify: {i}" for i in issues if i not in all_failed])

    # ── Summary ──────────────────────────────────────────────
    show_summary(all_succeeded, all_skipped, all_failed)

    # Dump state when there are failures so users can get help
    if all_failed or all_skipped:
        state_path = write_setup_state(
            profile.name, all_succeeded, all_skipped, all_failed,
            bundle_dir, copilot_cli_ok,
        )
        show_help_options(state_path, copilot_cli_ok)

    sys.exit(1 if all_failed else 0)


def _dump_and_exit(
    profile: Profile,
    bundle_dir: Path,
    succeeded: list[str],
    skipped: list[str],
    failed: list[str],
    copilot_cli_ok: bool,
):
    """Write troubleshooting state and exit early."""
    show_summary(succeeded, skipped, failed)
    state_path = write_setup_state(
        profile.name, succeeded, skipped, failed,
        bundle_dir, copilot_cli_ok,
    )
    show_help_options(state_path, copilot_cli_ok)
    sys.exit(1)
