"""Bundle builder — assembles a distributable zip for team members."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console

from copilot_setup.models import Profile

console = Console()

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
powershell -ExecutionPolicy Bypass -File "%~dp0setup.ps1"

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

    # Copy profile.toml
    shutil.copy2(profile_toml, staging / "profile.toml")

    # Copy copilot/ and assets/ directories
    for subdir in ("copilot", "assets"):
        src = profile_dir / subdir
        if src.exists():
            shutil.copytree(src, staging / subdir, dirs_exist_ok=True)

    # Write launcher scripts
    (staging / "setup.bat").write_text(SETUP_BAT_CONTENT, encoding="utf-8")
    (staging / "setup.ps1").write_text(SETUP_PS1_CONTENT, encoding="utf-8")
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
