"""MCP server configuration for VS Code / GitHub Copilot."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from copilot_setup.installer.tui import (
    prompt_secret,
    prompt_yes_no,
    show_error,
    show_info,
    show_success,
    show_warning,
)
from copilot_setup.models import MCPServer

# VS Code stores MCP config in settings.json
VSCODE_SETTINGS_DIR = Path.home() / "AppData" / "Roaming" / "Code" / "User"
VSCODE_SETTINGS_FILE = VSCODE_SETTINGS_DIR / "settings.json"


def _strip_jsonc_comments(text: str) -> str:
    """Remove // and /* */ comments from JSONC, preserving strings containing //."""
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

        # Not inside a string
        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
        elif ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
            # Single-line comment — skip to end of line
            while i < len(text) and text[i] != "\n":
                i += 1
        elif ch == "/" and i + 1 < len(text) and text[i + 1] == "*":
            # Block comment — skip to */
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2  # skip */
        else:
            result.append(ch)
            i += 1

    stripped = "".join(result)
    # Remove trailing commas before } or ]
    stripped = re.sub(r",\s*([}\]])", r"\1", stripped)
    return stripped


def _backup_settings():
    """Create a timestamped backup of settings.json before modifying it."""
    if VSCODE_SETTINGS_FILE.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = VSCODE_SETTINGS_FILE.with_suffix(f".pre-copilot-setup-{stamp}.json")
        shutil.copy2(VSCODE_SETTINGS_FILE, backup)
        show_info(f"Backed up existing settings to {backup.name}")


def _load_vscode_settings() -> dict:
    """Load existing VS Code user settings, handling JSONC (comments/trailing commas)."""
    if not VSCODE_SETTINGS_FILE.exists():
        return {}

    raw = VSCODE_SETTINGS_FILE.read_text(encoding="utf-8")

    # Try standard JSON first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try stripping JSONC features
    try:
        return json.loads(_strip_jsonc_comments(raw))
    except json.JSONDecodeError:
        show_warning("Your VS Code settings.json has an unusual format.")
        show_warning("A backup will be created, but comments may not be preserved.")
        raise


def _save_vscode_settings(settings: dict):
    """Write VS Code user settings back to disk via atomic temp-file rename."""
    VSCODE_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    content = json.dumps(settings, indent=4, ensure_ascii=False) + "\n"

    # Write to a temp file first, then rename for crash safety
    tmp = VSCODE_SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(VSCODE_SETTINGS_FILE)


def _collect_secrets(server: MCPServer) -> dict[str, str]:
    """Prompt the user for any env vars that are empty (i.e. secrets to collect at install time)."""
    collected: dict[str, str] = {}
    empty_keys = [k for k, v in server.env.items() if not v]

    if not empty_keys:
        return server.env.copy()

    result = dict(server.env)
    for key in empty_keys:
        friendly = key.replace("_", " ").title()
        show_info(f"The '{server.name}' server needs a credential: {key}")
        value = prompt_secret(
            friendly,
            description=f"This is used by the {server.name} MCP server. "
            f"Ask your Copilot lead if you're unsure where to find it.",
        )
        if value:
            result[key] = value
        else:
            show_warning(f"Skipped — {server.name} may not work without {key}.")

    return result


def configure_mcp_server(server: MCPServer, settings: dict, env_overrides: dict[str, str]) -> bool:
    """Add a single MCP server to the settings dict. Returns True if added."""
    mcp_key = "github.copilot.chat.mcp.servers"
    if mcp_key not in settings:
        settings[mcp_key] = {}

    entry: dict = {"command": server.command}
    if server.args:
        entry["args"] = server.args

    # Use the collected env (with user-provided secrets)
    populated_env = {k: v for k, v in env_overrides.items() if v}
    if populated_env:
        entry["env"] = populated_env

    settings[mcp_key][server.name] = entry
    return True


def handle_mcp_servers(
    mcp_servers: list[MCPServer],
) -> tuple[list[str], list[str], list[str]]:
    """
    Configure all MCP servers in VS Code settings.
    Returns (succeeded, skipped, failed) lists of display names.
    """
    if not mcp_servers:
        return [], [], []

    succeeded: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    # Back up settings before any modification
    try:
        _backup_settings()
        settings = _load_vscode_settings()
    except Exception as exc:
        show_error(f"Could not read VS Code settings: {exc}")
        if not prompt_yes_no("Continue without configuring MCP servers?", default=False):
            return [], [], [s.name for s in mcp_servers]
        return [], [s.description or s.name for s in mcp_servers], []

    for server in mcp_servers:
        label = server.description or server.name
        show_info(f"Configuring MCP server: {server.name}")
        if server.description:
            show_info(f"  {server.description}")

        try:
            env = _collect_secrets(server)
            configure_mcp_server(server, settings, env)
            show_success(f"{server.name} — configured")
            succeeded.append(label)
        except Exception as exc:
            show_error(f"{server.name} — failed: {exc}")
            failed.append(label)

    try:
        _save_vscode_settings(settings)
        show_success("VS Code settings updated")
    except Exception as exc:
        show_error(f"Could not save VS Code settings: {exc}")
        return [], [], [s.description or s.name for s in mcp_servers]

    return succeeded, skipped, failed
