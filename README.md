# Copilot Setup

**Package and deliver curated GitHub Copilot environments for your team.**

A Copilot team lead uses this repo to assemble a polished setup bundle.  
Team members double-click `setup.bat` and follow a friendly wizard — no
technical knowledge required.

---

## How It Works

```
┌──────────────────────┐       ┌─────────────────┐       ┌──────────────────────┐
│   Copilot Lead       │       │   Zip Bundle     │       │   Team Member        │
│                      │       │                  │       │                      │
│  1. Edit profile     │──────▶│  profile.toml    │──────▶│  1. Extract zip      │
│  2. Run build        │       │  setup.bat       │       │  2. Double-click      │
│  3. Share zip        │       │  setup.ps1       │       │     setup.bat         │
│                      │       │  installer code  │       │  3. Follow wizard     │
│                      │       │  copilot config  │       │  4. Open VS Code      │
└──────────────────────┘       └─────────────────┘       └──────────────────────┘
```

**The lead** curates a profile (tools, extensions, MCP servers, auth steps)
and runs `copilot-setup build` to produce a versioned zip.

**The team member** extracts the zip, double-clicks `setup.bat`, and the
wizard handles everything: installing prerequisites, configuring VS Code,
setting up AI assistants, and walking through first-time sign-ins.

The wizard is **idempotent** — re-running it skips steps that are already
done, so there's no penalty for running it again if something went wrong.

---

## Quick Start — For the Copilot Lead

### 1. Install prerequisites

```
pip install uv          # if you don't already have it
uv sync                 # installs project dependencies
```

### 2. Edit your team profile

Open `profiles/default/profile.toml` and customise each section:

#### Prerequisites

Tools your team needs installed. Each prerequisite has:

| Field | Purpose |
|-------|---------|
| `name` | Machine identifier (e.g. `"uv"`) |
| `display_name` | What the user sees (e.g. `"Visual Studio Code"`) |
| `description` | Plain-language explanation — **avoid jargon** |
| `check_command` | How to detect it (e.g. `"code --version"`) |
| `install_command` | Auto-install command (optional — omit for manual-only) |
| `install_url` | Manual download link (shown if auto-install fails) |
| `guidance` | Step-by-step help for manual installation |
| `required` | `true` = blocks setup, `false` = optional, user chooses |

#### Extensions

VS Code extensions to install automatically:

```toml
[[extensions]]
id          = "github.copilot"
name        = "GitHub Copilot"
description = "AI pair programmer that suggests code as you type."
required    = true
```

#### MCP Servers

Model Context Protocol servers that extend what Copilot can access:

```toml
[[mcp_servers]]
name    = "github"
command = "npx"
args    = ["-y", "@modelcontextprotocol/server-github"]
description = "Gives Copilot access to your GitHub repositories."

[mcp_servers.env]
GITHUB_PERSONAL_ACCESS_TOKEN = ""
```

> **Secret handling:** Leave env values empty (`""`) and the installer will
> securely prompt each team member for their own token at install time.
> **Never put real tokens in the profile** — the bundle is not encrypted.

#### Setup Steps

Guided flows for awkward first-time experiences (auth, tenant selection, etc.):

```toml
[[setup_steps]]
name           = "azure-login"
description    = "Sign in to Azure"
step_type      = "guided"      # "auto", "guided", or "info"
command        = "az login"
verify_command = "az account show"
error_help     = "If the browser didn't open, copy the URL from the terminal."
guidance       = """
A browser window will open. Please:
  1. Sign in with your work email
  2. Choose your organisation if prompted
  3. Come back here when the browser confirms you're signed in
"""
```

- **`auto`** — runs silently, reports success/failure
- **`guided`** — shows instructions, runs the command, verifies the result
- **`info`** — displays text only, no action taken

The wizard **pre-verifies** each step: if `verify_command` already passes
(e.g. the user is already signed in), the step is skipped automatically.

#### Copilot Configuration

Place team files in the profile's `copilot/` directory:

```
profiles/default/
└── copilot/
    ├── instructions/
    │   └── copilot-instructions.md   # → .github/copilot-instructions.md
    ├── prompts/                      # → .github/copilot/prompts/
    └── agents/                       # → .github/copilot/agents/
```

Set the instructions file path in `profile.toml`:

```toml
copilot_instructions_file = "copilot/instructions/copilot-instructions.md"
```

The installer will ask the team member where their main project folder is
and copy these files into the appropriate `.github/` locations.

### 3. Test locally

Before sharing, validate and test your profile:

```bash
copilot-setup validate profiles/default     # check for errors
copilot-setup install profiles/default      # run the wizard yourself
```

### 4. Build a bundle

```
copilot-setup build profiles/default
```

This creates a versioned zip in `dist/` (e.g.
`copilot-setup-engineering-team-v1.0.0.zip`) containing:

| File | Purpose |
|------|---------|
| `setup.bat` | Double-clickable launcher |
| `setup.ps1` | PowerShell bootstrap (installs uv if needed) |
| `run_installer.py` | Python entry point (uses uv for dependencies) |
| `profile.toml` | Your team profile |
| `copilot/` | Copilot instructions, prompts, agents |
| `lib/` | The installer code |
| `manifest.json` | Bundle metadata with SHA-256 checksums |

### 5. Share the bundle

Send the zip to your team however you normally share files (email, Teams,
SharePoint, etc.). They extract it, double-click `setup.bat`, done.

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

> **Something go wrong?** Just run `setup.bat` again — it picks up where
> you left off and skips steps that are already complete.

---

## Creating Custom Profiles

Copy `profiles/default/` to a new directory and edit `profile.toml`:

```
profiles/
├── default/          # General engineering team
├── data-science/     # Data science team (adds Jupyter, pandas, etc.)
└── frontend/         # Frontend team (adds Prettier, ESLint, etc.)
```

Build any profile by name:

```
copilot-setup build profiles/data-science
copilot-setup build profiles/frontend
```

Each profile is fully self-contained — you can maintain profiles for
different teams, roles, or projects in the same repo.

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
│       ├── copilot_config.py    # Copilot instructions/prompts/agents
│       ├── guided.py            # Guided auth/setup steps
│       └── verify.py            # Post-install verification
├── tests/                       # Smoke tests
├── pyproject.toml               # Python project config
└── dist/                        # Generated bundles (gitignored)
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `copilot-setup build <profile-dir>` | Build a distributable zip bundle |
| `copilot-setup validate <profile-dir>` | Validate a profile without building |
| `copilot-setup install <profile-dir>` | Run the installer locally (for testing) |

## License

MIT — see [LICENSE](LICENSE) for details.
