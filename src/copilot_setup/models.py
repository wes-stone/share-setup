"""Manifest models for team profiles, prerequisites, extensions, and setup steps."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """How a setup step should be executed."""

    AUTO = "auto"  # Fully automated — no user interaction
    GUIDED = "guided"  # User follows instructions, tool verifies
    INFO = "info"  # Informational only — no action taken


class Prerequisite(BaseModel):
    """A tool or dependency that must be present before setup can proceed."""

    name: str = Field(description="Short machine-friendly identifier (e.g. 'uv')")
    display_name: str = Field(description="Human-friendly name shown to the user")
    description: str = Field(description="Plain-language explanation of what this tool does")
    check_command: str = Field(description="Shell command that succeeds when the tool is installed")
    install_command: Optional[str] = Field(
        default=None, description="Command to auto-install (None if manual only)"
    )
    install_url: Optional[str] = Field(
        default=None, description="URL for manual download/install"
    )
    required: bool = Field(default=True, description="Block setup if missing?")
    guidance: Optional[str] = Field(
        default=None, description="Help text for manual installation"
    )


class Extension(BaseModel):
    """A VS Code extension to install."""

    id: str = Field(description="Marketplace identifier (e.g. 'github.copilot')")
    name: str = Field(description="Display name")
    description: Optional[str] = Field(default=None, description="What this extension does")
    required: bool = Field(default=True, description="Block setup if installation fails?")


class MCPServer(BaseModel):
    """An MCP server to configure in VS Code / Copilot."""

    name: str = Field(description="Server identifier")
    command: str = Field(description="Command to launch the server")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    description: Optional[str] = Field(default=None, description="What this server provides")
    secret_env_keys: list[str] = Field(
        default_factory=list,
        description="Env var keys that are secrets (hidden input). All others use visible input.",
    )


class SetupStep(BaseModel):
    """A step in the guided setup flow."""

    name: str = Field(description="Step identifier")
    description: str = Field(description="Short description shown as the step title")
    step_type: StepType = Field(default=StepType.AUTO, description="Execution mode")
    command: Optional[str] = Field(default=None, description="Command to run (auto/guided)")
    guidance: Optional[str] = Field(
        default=None, description="Instructions shown for guided steps"
    )
    verify_command: Optional[str] = Field(
        default=None, description="Command to verify step completed successfully"
    )
    error_help: Optional[str] = Field(
        default=None, description="Help text shown if the step fails"
    )


class Profile(BaseModel):
    """A complete team setup profile — the top-level manifest."""

    name: str = Field(description="Profile display name")
    version: str = Field(default="1.0.0", description="Semantic version")
    description: str = Field(description="What this profile sets up")
    author: Optional[str] = Field(default=None, description="Who created this profile")

    prerequisites: list[Prerequisite] = Field(default_factory=list)
    extensions: list[Extension] = Field(default_factory=list)
    mcp_servers: list[MCPServer] = Field(default_factory=list)
    setup_steps: list[SetupStep] = Field(default_factory=list)

    copilot_instructions_file: Optional[str] = Field(
        default=None, description="Relative path to a copilot-instructions.md file"
    )

    @classmethod
    def from_toml_path(cls, path: Path) -> Profile:
        """Load a profile from a TOML file."""
        import tomllib

        with open(path, "rb") as f:
            data = tomllib.load(f)
        # The profile section is at root level
        return cls.model_validate(data)
