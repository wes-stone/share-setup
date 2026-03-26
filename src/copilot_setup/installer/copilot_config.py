"""Apply Copilot configuration files (instructions, prompts, agents)."""

from __future__ import annotations

import shutil
from pathlib import Path

from copilot_setup.installer.tui import (
    prompt_directory,
    prompt_yes_no,
    show_info,
    show_success,
    show_warning,
)


def handle_copilot_config(
    bundle_dir: Path,
    instructions_file: str | None,
) -> tuple[list[str], list[str], list[str]]:
    """
    Copy Copilot configuration files to the user's workspace.
    Returns (succeeded, skipped, failed) lists.
    """
    succeeded: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    # Collect all copilot assets from the bundle
    copilot_dir = bundle_dir / "copilot"
    extensions_dir = bundle_dir / "extensions"
    has_instructions = instructions_file and (bundle_dir / instructions_file).exists()
    has_copilot_assets = copilot_dir.exists() and any(copilot_dir.rglob("*"))
    has_extensions = extensions_dir.exists() and any(extensions_dir.rglob("*"))

    if not has_instructions and not has_copilot_assets and not has_extensions:
        return [], [], []

    show_info("Your team has provided Copilot configuration files.")
    show_info("These customise how the AI assistant works for your team.\n")

    if not prompt_yes_no("Would you like to install Copilot configuration files?"):
        skipped.append("Copilot configuration")
        return succeeded, skipped, failed

    target = prompt_directory(
        "Enter the path to your main project folder",
        default=str(Path.home() / "source"),
    )

    if not target:
        skipped.append("Copilot configuration")
        return succeeded, skipped, failed

    target_path = Path(target)
    github_dir = target_path / ".github"

    try:
        github_dir.mkdir(parents=True, exist_ok=True)

        # Copy instructions file
        if has_instructions:
            src = bundle_dir / instructions_file
            dest = github_dir / "copilot-instructions.md"
            if dest.exists():
                if not prompt_yes_no(
                    f"Copilot instructions already exist at {dest}. Overwrite?",
                    default=False,
                ):
                    skipped.append("Copilot instructions (kept existing)")
                else:
                    backup = dest.with_suffix(f".backup-{dest.suffix}")
                    shutil.copy2(dest, backup)
                    show_info(f"Backed up existing file to {backup.name}")
                    shutil.copy2(src, dest)
                    show_success(f"Copilot instructions → {dest}")
                    succeeded.append("Copilot instructions")
            else:
                shutil.copy2(src, dest)
                show_success(f"Copilot instructions → {dest}")
                succeeded.append("Copilot instructions")

        # Copy prompts, agents, skills, etc.
        if has_copilot_assets:
            for subdir in ("prompts", "agents", "skills"):
                src_sub = copilot_dir / subdir
                if src_sub.exists() and any(src_sub.iterdir()):
                    dest_sub = github_dir / "copilot" / subdir
                    dest_sub.mkdir(parents=True, exist_ok=True)
                    for item in src_sub.iterdir():
                        if item.is_file():
                            dest_file = dest_sub / item.name
                            if dest_file.exists():
                                show_info(f"Overwriting existing {subdir} file: {item.name}")
                            shutil.copy2(item, dest_file)
                    show_success(f"Copilot {subdir} → {dest_sub}")
                    succeeded.append(f"Copilot {subdir}")

        # Copy Copilot CLI extensions (.github/extensions/)
        if has_extensions:
            dest_ext = github_dir / "extensions"
            dest_ext.mkdir(parents=True, exist_ok=True)
            for item in extensions_dir.iterdir():
                if item.is_file():
                    dest_file = dest_ext / item.name
                    if dest_file.exists():
                        show_info(f"Overwriting existing extension: {item.name}")
                    shutil.copy2(item, dest_file)
            show_success(f"Copilot extensions → {dest_ext}")
            succeeded.append("Copilot extensions")

    except Exception as exc:
        show_warning(f"Could not copy Copilot files: {exc}")
        failed.append("Copilot configuration")

    return succeeded, skipped, failed
