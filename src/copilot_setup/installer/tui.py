"""Rich-based TUI components for a friendly, non-technical user experience."""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.text import Text
from rich.theme import Theme

# Consistent colour theme across all output
THEME = Theme(
    {
        "info": "cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "step": "bold blue",
        "heading": "bold white",
        "muted": "dim",
    }
)

console = Console(theme=THEME)


# ── Reusable display helpers ────────────────────────────────


def show_welcome(profile_name: str, description: str, author: str | None, steps: list[str]):
    """Display the welcome screen with a summary of what will happen."""
    step_lines = "\n".join(f"  [success]✓[/] {s}" for s in steps)
    body = (
        f"\n  Welcome! This wizard will set up your\n"
        f"  development environment step by step.\n\n"
        f"  [heading]Profile:[/]  {profile_name}\n"
    )
    if author:
        body += f"  [heading]Created by:[/]  {author}\n"
    body += f"\n  [heading]What we'll do:[/]\n{step_lines}\n"

    console.print()
    console.print(
        Panel(
            body,
            title="[step]🚀  Copilot Setup Wizard[/]",
            border_style="blue",
            padding=(1, 2),
        )
    )


def show_step_header(step_number: int, total_steps: int, title: str):
    """Display a step header with progress indicator."""
    console.print()
    console.print(
        Rule(
            f"[step]Step {step_number} of {total_steps}[/]  │  {title}",
            style="blue",
        )
    )
    console.print()


def show_info(message: str):
    """Display an informational message."""
    console.print(f"  [info]ℹ[/]  {message}")


def show_success(message: str):
    """Display a success message."""
    console.print(f"  [success]✓[/]  {message}")


def show_warning(message: str):
    """Display a warning message."""
    console.print(f"  [warning]⚠[/]  {message}")


def show_error(message: str):
    """Display an error message."""
    console.print(f"  [error]✗[/]  {message}")


def show_guidance(text: str):
    """Display guidance text in a bordered panel."""
    console.print()
    console.print(
        Panel(
            text.strip(),
            border_style="cyan",
            padding=(1, 3),
        )
    )
    console.print()


def show_summary(
    succeeded: list[str],
    skipped: list[str],
    failed: list[str],
):
    """Display the final setup summary."""
    console.print()

    if not failed:
        title = "[success]🎉  Setup Complete![/]"
        border = "green"
    else:
        title = "[warning]⚠  Setup Finished With Issues[/]"
        border = "yellow"

    body_parts: list[str] = []
    if succeeded:
        items = "\n".join(f"    [success]✓[/] {s}" for s in succeeded)
        body_parts.append(f"  [heading]Completed:[/]\n{items}")
    if skipped:
        items = "\n".join(f"    [muted]–[/] {s}" for s in skipped)
        body_parts.append(f"  [heading]Skipped:[/]\n{items}")
    if failed:
        items = "\n".join(f"    [error]✗[/] {s}" for s in failed)
        body_parts.append(f"  [heading]Needs Attention:[/]\n{items}")

    body = "\n\n".join(body_parts) + "\n"

    console.print(Panel(body, title=title, border_style=border, padding=(1, 2)))

    if not failed:
        console.print("  [success]You're all set![/] Open VS Code to start using Copilot.\n")
    else:
        console.print(
            "  [warning]Some steps need attention.[/] Re-run this wizard to retry,\n"
            "  or contact your team's Copilot lead for help.\n"
        )


def prompt_continue(message: str = "Press Enter to continue...") -> bool:
    """Pause and wait for the user to press Enter. Returns False only if the user confirms quit."""
    try:
        console.input(f"  [muted]{message}[/] ")
        return True
    except (KeyboardInterrupt, EOFError):
        return not _confirm_quit()


def _confirm_quit() -> bool:
    """Ask the user if they really want to quit. Returns True if they confirm."""
    console.print()
    try:
        answer = console.input("  Really quit? You can re-run this wizard later. [y/N] ").strip().lower()
        return answer in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        return True


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Ask a yes/no question with a sensible default. Ctrl-C triggers quit confirmation."""
    hint = "[Y/n]" if default else "[y/N]"
    try:
        answer = console.input(f"  {question} {hint} ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        # Don't silently return default — confirm quit
        if _confirm_quit():
            raise SystemExit(0)
        return default
    if not answer:
        return default
    return answer in ("y", "yes")


def prompt_secret(label: str, description: str | None = None) -> str:
    """Prompt the user for a secret value (e.g., API token) without echoing."""
    import getpass

    console.print()
    if description:
        console.print(f"  [info]ℹ[/]  {description}")
    try:
        value = getpass.getpass(f"  {label}: ")
        return value.strip()
    except (KeyboardInterrupt, EOFError):
        return ""


def prompt_directory(label: str, default: str | None = None) -> str:
    """Prompt the user for a directory path."""
    hint = f" [{default}]" if default else ""
    try:
        answer = console.input(f"  {label}{hint}: ").strip()
        return answer or (default or "")
    except (KeyboardInterrupt, EOFError):
        return default or ""


def create_progress() -> Progress:
    """Create a styled progress bar for long-running operations."""
    return Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        transient=True,
    )
