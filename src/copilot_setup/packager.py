"""Bundle builder — assembles a distributable zip for team members."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import tomli_w
from rich.console import Console
from rich.prompt import Confirm

from copilot_setup.models import Profile

console = Console()

# The lead's VS Code settings path (Windows)
_VSCODE_SETTINGS_FILE = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "settings.json"

# Files inside the profile directory that get bundled
PROFILE_GLOB_INCLUDE = [
    "profile.toml",
    "copilot/**/*",
    "assets/**/*",
]

SETUP_BAT_CONTENT = r"""@echo off
title Copilot Setup Wizard
echo.
echo  ======================================
echo   Copilot Setup Wizard
echo  ======================================
echo.
echo  Starting setup...
echo.

:: Run the PowerShell bootstrap
powershell -ExecutionPolicy Bypass -File "%~dp0_bootstrap.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  Setup encountered an issue. Please contact your Copilot lead.
    echo.
)

pause
"""

SETUP_PS1_CONTENT = r"""#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host ""
Write-Host "  Preparing setup environment..." -ForegroundColor Cyan
Write-Host ""

# Check for uv, install if missing
$uvPath = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvPath) {
    Write-Host "  Installing uv (Python package manager)..." -ForegroundColor Yellow
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        # Add the default uv install location to this session's PATH
        $uvHome = Join-Path $env:USERPROFILE ".local\bin"
        if (Test-Path $uvHome) {
            $env:PATH = "$uvHome;$env:PATH"
        }
    } catch {
        Write-Host "  Could not install uv automatically." -ForegroundColor Red
        Write-Host "  Please visit: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Yellow
        exit 1
    }
}

# Run the installer using uv (handles Python + dependencies automatically)
Write-Host "  Launching setup wizard..." -ForegroundColor Cyan
Write-Host ""

uv run --with pydantic --with rich --with tomli-w "$scriptDir\run_installer.py" "$scriptDir\profile.toml"
exit $LASTEXITCODE
"""

RUN_INSTALLER_PY_CONTENT = r'''# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0",
#     "rich>=13.0",
#     "tomli-w>=1.0",
# ]
# ///
"""Standalone installer entry point — bundled inside the setup zip."""

from __future__ import annotations

import sys
from pathlib import Path

# Add the bundled source to the path
bundle_dir = Path(__file__).parent
sys.path.insert(0, str(bundle_dir / "lib"))

from copilot_setup.installer.main import run_installer

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run_installer.py <profile.toml>")
        sys.exit(1)
    run_installer(Path(sys.argv[1]))
'''


def _sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_source_lib(staging: Path):
    """Copy the copilot_setup package into the bundle's lib/ folder."""
    import copilot_setup

    src_root = Path(copilot_setup.__file__).parent
    dest = staging / "lib" / "copilot_setup"
    shutil.copytree(src_root, dest, dirs_exist_ok=True)


def _strip_jsonc_comments(text: str) -> str:
    """Remove // and /* */ comments from JSONC, preserving strings."""
    result: list[str] = []
    i = 0
    in_string = False
    escape_next = False
    while i < len(text):
        ch = text[i]
        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue
        if in_string:
            result.append(ch)
            if ch == "\\":
                escape_next = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
        elif ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
            while i < len(text) and text[i] != "\n":
                i += 1
        elif ch == "/" and i + 1 < len(text) and text[i + 1] == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
        else:
            result.append(ch)
            i += 1
    stripped = "".join(result)
    stripped = re.sub(r",\s*([}\]])", r"\1", stripped)
    return stripped


def _load_lead_mcp_config() -> dict[str, dict]:
    """Read the lead's VS Code settings and return their MCP server configs.

    Returns a dict mapping server name → server config (with 'env', 'command', 'args').
    """
    if not _VSCODE_SETTINGS_FILE.exists():
        return {}

    raw = _VSCODE_SETTINGS_FILE.read_text(encoding="utf-8")
    try:
        settings = json.loads(raw)
    except json.JSONDecodeError:
        try:
            settings = json.loads(_strip_jsonc_comments(raw))
        except json.JSONDecodeError:
            return {}

    return settings.get("github.copilot.chat.mcp.servers", {})


def _capture_mcp_values(profile: Profile) -> Profile:
    """Ask the lead which MCP env values to share with the team.

    Reads the lead's VS Code MCP config, matches servers from the profile,
    and offers to bake env values into the profile so team members skip prompts.
    Returns a new Profile with updated env values.
    """
    if not profile.mcp_servers:
        return profile

    lead_config = _load_lead_mcp_config()
    if not lead_config:
        console.print("  [info]ℹ[/]  No MCP servers found in your VS Code settings — skipping value capture.")
        return profile

    console.print()
    console.print("  [bold]Share your MCP configuration with the team?[/]")
    console.print("  [muted]Values you share will be baked into the bundle so your team[/]")
    console.print("  [muted]doesn't have to enter them. You can skip any you want to keep private.[/]")
    console.print()

    updated_servers = []
    for server in profile.mcp_servers:
        lead_server = lead_config.get(server.name, {})
        lead_env = lead_server.get("env", {})

        if not lead_env:
            updated_servers.append(server)
            continue

        # Find empty keys in the profile that the lead has configured
        empty_keys = [k for k, v in server.env.items() if not v]
        shareable_keys = [k for k in empty_keys if lead_env.get(k)]

        if not shareable_keys:
            updated_servers.append(server)
            continue

        console.print(f"  [step]─── {server.name} ───[/]")
        new_env = dict(server.env)
        for key in shareable_keys:
            lead_value = lead_env[key]
            # Truncate display for long values
            display_val = lead_value if len(lead_value) <= 60 else lead_value[:57] + "..."
            console.print(f"    {key} = [info]{display_val}[/]")

            share = Confirm.ask(f"    Share this with your team?", default=True, console=console)
            if share:
                new_env[key] = lead_value
                console.print(f"    [success]✓[/] Will be shared")
            else:
                console.print(f"    [muted]– Skipped (team will be prompted)[/]")

        updated_server = server.model_copy(update={"env": new_env})
        updated_servers.append(updated_server)
        console.print()

    return profile.model_copy(update={"mcp_servers": updated_servers})


def _write_profile_toml(profile: Profile, dest: Path, original: Path):
    """Write a profile to TOML, preserving the original if no MCP values changed.

    If MCP env values were updated, re-serializes the full profile.
    Otherwise copies the original file to preserve formatting and comments.
    """
    import tomllib

    # Check if any MCP env values were actually changed
    with open(original, "rb") as f:
        original_data = tomllib.load(f)

    original_profile = Profile.model_validate(original_data)
    mcp_changed = False
    for orig_server, new_server in zip(original_profile.mcp_servers, profile.mcp_servers):
        if orig_server.env != new_server.env:
            mcp_changed = True
            break

    if not mcp_changed:
        # No changes — preserve original formatting
        shutil.copy2(original, dest)
        return

    # Re-serialize with updated values
    data = profile.model_dump(exclude_none=True)

    # Convert mcp_servers back to the TOML-friendly format
    if "mcp_servers" in data:
        for server in data["mcp_servers"]:
            # Move env to [mcp_servers.env] section style
            env = server.pop("env", {})
            if env:
                server["env"] = env
            # Remove empty secret_env_keys to keep TOML clean
            if not server.get("secret_env_keys"):
                server.pop("secret_env_keys", None)

    dest.write_bytes(tomli_w.dumps(data).encode("utf-8"))


def build_bundle(
    profile_dir: Path,
    output_dir: Path,
    version_override: Optional[str] = None,
) -> Path:
    """
    Build a distributable zip bundle from a profile directory.
    Returns the path to the generated zip file.
    """
    profile_toml = profile_dir / "profile.toml"
    profile = Profile.from_toml_path(profile_toml)
    version = version_override or profile.version
    bundle_name = f"copilot-setup-{profile.name.lower().replace(' ', '-')}-v{version}"

    # Prepare staging directory
    staging = output_dir / f".staging-{bundle_name}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    console.print(f"  [info]ℹ[/]  Assembling bundle: {bundle_name}")

    # Offer to capture the lead's MCP env values for the team
    profile = _capture_mcp_values(profile)

    # Write the (possibly updated) profile.toml to staging
    _write_profile_toml(profile, staging / "profile.toml", profile_toml)

    # Copy copilot/, extensions/, and assets/ directories
    for subdir in ("copilot", "extensions", "assets"):
        src = profile_dir / subdir
        if src.exists():
            shutil.copytree(src, staging / subdir, dirs_exist_ok=True)

    # Write launcher scripts
    (staging / "Click-Here-To-Setup.bat").write_text(SETUP_BAT_CONTENT, encoding="utf-8")
    (staging / "_bootstrap.ps1").write_text(SETUP_PS1_CONTENT, encoding="utf-8")
    (staging / "run_installer.py").write_text(RUN_INSTALLER_PY_CONTENT, encoding="utf-8")

    # Copy the installer library
    _copy_source_lib(staging)

    # Generate manifest with checksums
    file_checksums = {}
    for file in sorted(staging.rglob("*")):
        if file.is_file() and file.name != "manifest.json":
            rel = file.relative_to(staging).as_posix()
            file_checksums[rel] = _sha256(file)

    manifest = {
        "name": profile.name,
        "version": version,
        "created": datetime.now(timezone.utc).isoformat(),
        "author": profile.author,
        "description": profile.description,
        "files": file_checksums,
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Create the zip
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = shutil.make_archive(
        str(output_dir / bundle_name), "zip", root_dir=str(staging)
    )

    # Clean up staging
    shutil.rmtree(staging)

    console.print(f"  [success]✓[/]  {len(file_checksums)} files bundled")
    return Path(zip_path)
