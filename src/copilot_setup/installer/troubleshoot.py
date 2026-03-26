"""Dump setup state so users can get AI help when something goes wrong."""

from __future__ import annotations

import datetime
from pathlib import Path

from copilot_setup.installer.tui import console, show_info, show_success


def write_setup_state(
    profile_name: str,
    succeeded: list[str],
    skipped: list[str],
    failed: list[str],
    bundle_dir: Path,
    copilot_cli_available: bool = False,
) -> Path:
    """
    Write a troubleshooting context file that describes the setup state.

    Returns the path to the written file.
    """
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    state_path = bundle_dir / "copilot-setup-state.md"

    lines = [
        f"# Copilot Setup State — {profile_name}",
        f"",
        f"Generated: {ts}",
        f"",
        f"## What happened",
        f"",
        f"A team member ran the Copilot Setup Wizard and some steps need attention.",
        f"Help them troubleshoot and fix the issues below.",
        f"",
    ]

    if succeeded:
        lines.append("## ✅ Completed successfully")
        lines.append("")
        for item in succeeded:
            lines.append(f"- {item}")
        lines.append("")

    if skipped:
        lines.append("## ⏭️ Skipped")
        lines.append("")
        for item in skipped:
            lines.append(f"- {item}")
        lines.append("")

    if failed:
        lines.append("## ❌ Failed — needs help")
        lines.append("")
        for item in failed:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("## What to try")
        lines.append("")
        lines.append(
            "Please help me fix the failed items above. I'm setting up my development "
            "environment and the automated wizard couldn't complete these steps. "
            "Give me specific commands to run or steps to follow."
        )
    else:
        lines.append("## ⚠️ No failures, but some steps were skipped")
        lines.append("")
        lines.append(
            "Help me understand if the skipped items matter and how to set them up manually."
        )

    lines.append("")

    state_path.write_text("\n".join(lines), encoding="utf-8")
    return state_path


def show_help_options(
    state_path: Path,
    copilot_cli_available: bool = False,
):
    """Show the user how to get help with their setup issues."""
    console.print()
    console.print(
        "  [step]💡 Need help?[/]  Your setup state has been saved.\n"
    )

    if copilot_cli_available:
        console.print(
            "  [heading]Option 1 — Ask Copilot in your terminal (fastest):[/]\n"
            f"    [info]gh copilot suggest \"fix my copilot setup\"[/]\n"
        )
        console.print(
            "  [heading]Option 2 — Ask Copilot in VS Code:[/]\n"
            f"    Open VS Code → Copilot Chat (Ctrl+Shift+I)\n"
            f"    Paste the contents of [info]{state_path.name}[/]\n"
        )
    else:
        console.print(
            "  [heading]Ask Copilot in VS Code:[/]\n"
            f"    Open VS Code → Copilot Chat (Ctrl+Shift+I)\n"
            f"    Paste the contents of [info]{state_path.name}[/]\n"
        )

    console.print(
        f"  [heading]Or share with your Copilot lead:[/]\n"
        f"    Send them the file: [info]{state_path}[/]\n"
    )

    show_info(f"State saved to {state_path}")
