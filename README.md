# Copilot Setup

**Package and deliver curated GitHub Copilot environments for your team.**

A Copilot team lead uses this repo to assemble a polished setup bundle.  
Team members double-click `setup.bat` and follow a friendly wizard — no
technical knowledge required.

---

## Quick Start — For the Copilot Lead

### 1. Install prerequisites

```
pip install uv          # if you don't already have it
uv sync                 # installs project dependencies
```

### 2. Edit your team profile

Open `profiles/default/profile.toml` and customise:

- **Prerequisites** — tools your team needs (VS Code, Node.js, Azure CLI, …)
- **Extensions** — VS Code extensions to install (Copilot, Copilot Chat, …)
- **MCP Servers** — AI assistant connections (GitHub, Azure, custom servers)
- **Setup Steps** — guided first-time sign-in flows (Azure login, GitHub auth, …)
- **Copilot Instructions** — edit `copilot/instructions/copilot-instructions.md`

### 3. Build a bundle

```
copilot-setup build profiles/default
```

This creates a versioned zip in `dist/` containing everything your team needs.

### 4. Share the bundle

Send the zip to your team. They extract it, double-click `setup.bat`, and
follow the wizard.

---

## Quick Start — For Team Members

1. Extract the zip you received from your Copilot lead
2. Double-click **`setup.bat`**
3. Follow the on-screen instructions
4. Open VS Code — you're ready to go!

The wizard will:
- ✓ Check your system for required tools
- ✓ Install anything that's missing
- ✓ Set up your VS Code extensions
- ✓ Configure AI assistant connections
- ✓ Walk you through first-time sign-ins
- ✓ Verify everything is working

---

## Project Structure

```
share-setup-1/
├── profiles/                    # Team setup profiles
│   └── default/
│       ├── profile.toml         # Main profile manifest
│       └── copilot/             # Copilot instructions, prompts, agents
├── src/copilot_setup/           # Source code
│   ├── cli.py                   # Lead-facing CLI
│   ├── models.py                # Profile data models
│   ├── packager.py              # Bundle builder
│   └── installer/               # Team member guided installer
│       ├── main.py              # Installer orchestrator
│       ├── tui.py               # Rich TUI components
│       ├── prereqs.py           # Prerequisite management
│       ├── extensions.py        # VS Code extension installer
│       ├── mcp.py               # MCP server configuration
│       ├── guided.py            # Guided auth/setup steps
│       └── verify.py            # Post-install verification
├── pyproject.toml               # Python project config
└── dist/                        # Generated bundles (gitignored)
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `copilot-setup build <profile-dir>` | Build a distributable zip bundle |
| `copilot-setup validate <profile-dir>` | Validate a profile without building |
| `copilot-setup install <profile-dir>` | Run the installer locally (for testing) |

## Creating Custom Profiles

Copy `profiles/default/` to a new directory and edit `profile.toml`.  
Each profile is self-contained — you can maintain profiles for different
teams, roles, or projects in the same repo.

## License

MIT — see [LICENSE](LICENSE) for details.
