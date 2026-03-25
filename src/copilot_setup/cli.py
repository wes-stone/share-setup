"""Lead-facing CLI — build bundles, validate profiles, run the installer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="copilot-setup",
    help="Package and deliver curated GitHub Copilot environments for your team.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def build(
    profile: Path = typer.Argument(
        ...,
        help="Path to a profile directory (must contain profile.toml)",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    output: Path = typer.Option(
        Path("dist"),
        "--output", "-o",
        help="Output directory for the generated bundle",
    ),
    version_tag: Optional[str] = typer.Option(
        None,
        "--version", "-v",
        help="Override the version tag (default: from profile.toml)",
    ),
):
    """Build a distributable setup bundle from a profile directory."""
    from copilot_setup.packager import build_bundle

    profile_toml = profile / "profile.toml"
    if not profile_toml.exists():
        console.print(f"[error]✗[/]  No profile.toml found in {profile}")
        raise typer.Exit(1)

    try:
        result = build_bundle(profile, output, version_tag)
        console.print(f"\n[success]✓[/]  Bundle created: [bold]{result}[/]\n")
    except Exception as exc:
        console.print(f"\n[error]✗[/]  Build failed: {exc}\n")
        raise typer.Exit(1)


@app.command()
def validate(
    profile: Path = typer.Argument(
        ...,
        help="Path to a profile directory",
        exists=True,
    ),
):
    """Validate a profile without building a bundle."""
    from copilot_setup.models import Profile

    profile_toml = profile / "profile.toml"
    if not profile_toml.exists():
        console.print(f"[error]✗[/]  No profile.toml found in {profile}")
        raise typer.Exit(1)

    try:
        p = Profile.from_toml_path(profile_toml)
        console.print(f"[success]✓[/]  Profile valid: {p.name} v{p.version}")
        console.print(f"   {len(p.prerequisites)} prerequisites")
        console.print(f"   {len(p.extensions)} extensions")
        console.print(f"   {len(p.mcp_servers)} MCP servers")
        console.print(f"   {len(p.setup_steps)} setup steps")
    except Exception as exc:
        console.print(f"[error]✗[/]  Validation failed: {exc}")
        raise typer.Exit(1)


@app.command()
def install(
    profile: Path = typer.Argument(
        ...,
        help="Path to a profile directory or profile.toml file",
        exists=True,
    ),
):
    """Run the guided installer directly from a profile (for testing)."""
    from copilot_setup.installer.main import run_installer

    if profile.is_dir():
        profile = profile / "profile.toml"

    if not profile.exists():
        console.print(f"[error]✗[/]  Profile not found: {profile}")
        raise typer.Exit(1)

    run_installer(profile)


if __name__ == "__main__":
    app()
