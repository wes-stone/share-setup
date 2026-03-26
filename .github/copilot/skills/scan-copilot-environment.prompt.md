---
name: scan-copilot-environment
description: >
  Scans the Copilot lead's local machine for installed VS Code extensions,
  MCP server configurations, developer tools, Copilot config files, skills,
  and extensions — then generates a ready-to-use profile.toml for the
  share-setup project.
---

You are an environment scanner that helps a Copilot team lead quickly generate
a `profile.toml` by discovering what's already configured on their machine.

Run the following scans **in order**, collect the results, and then generate
a complete profile. Use the terminal tool to execute commands.

---

## ⚠️ REQUIRED FIELDS — Schema Reference

Every block in profile.toml must include ALL required fields or the build
will fail. Check this table before generating any TOML:

### `[[prerequisites]]` — required fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Machine-friendly ID (e.g. `"git"`) |
| `display_name` | string | ✅ | Human-friendly name (e.g. `"Git"`) |
| `description` | string | ✅ | Plain-language explanation |
| `check_command` | string | ✅ | Shell command that succeeds when installed |
| `install_command` | string | optional | Auto-install command |
| `install_url` | string | optional | Manual download URL |
| `required` | bool | optional | Default `true` |
| `guidance` | string | optional | Help text for manual install |

### `[[extensions]]` — required fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Marketplace ID (e.g. `"github.copilot-chat"`) |
| `name` | string | ✅ | Display name (e.g. `"GitHub Copilot Chat"`) |
| `description` | string | optional | What this extension does |
| `required` | bool | optional | Default `true` |

### `[[mcp_servers]]` — required fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Server identifier key |
| `command` | string | ✅ | Launch command |
| `args` | list[string] | optional | Command arguments |
| `description` | string | optional | What this server provides |
| `secret_env_keys` | list[string] | optional | Keys that use hidden input |
| `[mcp_servers.env]` | key-value | optional | Environment variables |

### `[[setup_steps]]` — required fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Step identifier |
| `description` | string | ✅ | Short title shown in the wizard |
| `step_type` | string | optional | `"auto"`, `"guided"`, or `"info"` |
| `command` | string | optional | Command to run |
| `guidance` | string | optional | Instructions for guided steps |
| `verify_command` | string | optional | Command to verify completion |
| `error_help` | string | optional | Help text shown on failure |

---

## Step 1 — Scan installed VS Code extensions

Run this command and capture the full output:

```
code --list-extensions
```

For each extension found, look up its display name. Focus on extensions that
are useful for team productivity — skip themes, icon packs, and purely
personal preference extensions unless the user asks to include them.

Categorise each as `required = true` (essential for the team) or
`required = false` (nice to have). Use your judgement, but always mark
GitHub Copilot and Copilot Chat as required.

**Every extension block MUST have both `id` and `name`:**
```toml
[[extensions]]
id          = "github.copilot-chat"
name        = "GitHub Copilot Chat"
description = "Chat with AI about your code directly in the editor."
required    = true
```

---

## Step 2 — Scan VS Code settings for MCP servers

Read the user's VS Code settings file:

- **Windows:** `%APPDATA%\Code\User\settings.json`
- **macOS:** `~/Library/Application Support/Code/User/settings.json`
- **Linux:** `~/.config/Code/User/settings.json`

Look for the key `github.copilot.chat.mcp.servers` (or `mcp.servers` or
similar MCP configuration blocks). For each server found, extract:

- `name` — the server key
- `command` — the launch command
- `args` — command arguments
- `env` — environment variables
- Write a plain-language `description` explaining what the server does

### Classifying env vars — secrets vs shareable values

For each env var, decide whether it's a **secret** or a **shareable value**:

- **Shareable values** (URIs, database names, directory paths, base URLs) —
  leave the value as `""` in the profile. During `copilot-setup build`, the
  lead will be prompted to share their actual values with the team. Team
  members who receive the bundle won't need to enter these.
- **Secrets** (personal access tokens, API keys, passwords) — leave as `""`
  AND add the key to `secret_env_keys` so the installer uses hidden input.

Example:

```toml
[[mcp_servers]]
name            = "fabric-rti-mcp"
command         = "uvx"
args            = ["microsoft-fabric-rti-mcp"]
description     = "Connects Copilot to Microsoft Fabric."
secret_env_keys = []

[mcp_servers.env]
KUSTO_SERVICE_URI        = ""
KUSTO_SERVICE_DEFAULT_DB = ""
FABRIC_API_BASE_URL      = "https://api.fabric.microsoft.com/v1"

[[mcp_servers]]
name            = "github"
command         = "npx"
args            = ["-y", "@modelcontextprotocol/server-github"]
description     = "Gives Copilot access to your GitHub repositories."
secret_env_keys = ["GITHUB_PERSONAL_ACCESS_TOKEN"]

[mcp_servers.env]
GITHUB_PERSONAL_ACCESS_TOKEN = ""
```

Keys in `secret_env_keys` will use hidden input (like a password prompt).
Everything else uses visible input so users can see what they're typing.

---

## Step 3 — Scan for installed developer tools

Check for each of these tools by running their version commands. Only
include tools that are actually installed:

| Tool | Check command |
|------|--------------|
| uv | `uv --version` |
| Python | `python --version` |
| Node.js | `node --version` |
| Git | `git --version` |
| Azure CLI | `az --version` |
| GitHub CLI | `gh --version` |
| Docker | `docker --version` |
| kubectl | `kubectl version --client` |
| Terraform | `terraform --version` |
| .NET SDK | `dotnet --version` |
| Java | `java --version` |
| Go | `go version` |
| Rust | `rustc --version` |

For each installed tool, generate a `[[prerequisites]]` block with ALL
required fields — **especially `display_name`** (the build will fail without it):

```toml
[[prerequisites]]
name            = "git"
display_name    = "Git"
description     = "Version control — tracks changes to your code."
check_command   = "git --version"
install_command = "winget install --id Git.Git -e --source winget"
install_url     = "https://git-scm.com/downloads"
guidance        = "Download and run the installer. Accept the defaults."
required        = true
```

- `display_name` — Human-friendly name (Git, Python, Azure CLI, etc.)
- `description` — **jargon-free**, a non-technical person should understand it
- `check_command` — the command that succeeds when the tool is installed
- `install_command` using `winget` (Windows) or `brew` (macOS) where possible
- `install_url` as fallback
- `required = true` for essential tools, `false` for optional ones

---

## Step 4 — Scan for Copilot configuration files

Search the current workspace and common project directories for:

- `.github/copilot-instructions.md` — Copilot instructions
- `.github/copilot/prompts/` — prompt files (`.prompt.md`)
- `.github/copilot/agents/` — custom agent configs
- `.github/copilot/skills/` — skill files (`.prompt.md`)
- `.github/extensions/` — Copilot CLI extension files

If found, list them and ask the user which ones to include in the profile.

**Important:** Skills and extensions are new additions to the bundler:

- **Skills** go in the profile's `copilot/skills/` directory and get
  installed to `<workspace>/.github/copilot/skills/` on the team member's
  machine.
- **Extensions** go in the profile's `extensions/` directory and get
  installed to `<workspace>/.github/extensions/` on the team member's machine.

---

## Step 5 — Ask about guided setup steps

Ask the user:

> "I found [Azure CLI / GitHub CLI / other auth tools] installed. Would you
> like to include guided sign-in steps for these in your team's setup wizard?
> These walk new users through first-time authentication with plain-language
> instructions."

For each tool the user confirms, generate a `[[setup_steps]]` block with
`step_type = "guided"`, a friendly `guidance` message, and a `verify_command`.

---

## Step 6 — Generate the profile

Combine everything into a complete, well-commented `profile.toml` following
this structure:

```toml
name        = "<team name — ask the user>"
version     = "1.0.0"
description = "<one-line description — ask the user>"
author      = "<user's name — ask>"

copilot_instructions_file = "copilot/instructions/copilot-instructions.md"

# ── Prerequisites ────────────────────────────────────────────
# Every block MUST have: name, display_name, description, check_command
[[prerequisites]]
name            = "git"
display_name    = "Git"
description     = "Version control — tracks changes to your code."
check_command   = "git --version"
install_command = "winget install --id Git.Git -e --source winget"
install_url     = "https://git-scm.com/downloads"
guidance        = "Download and run the installer. Accept the defaults."
required        = true

# ── VS Code Extensions ──────────────────────────────────────
# Every block MUST have: id, name
[[extensions]]
id          = "github.copilot-chat"
name        = "GitHub Copilot Chat"
description = "Chat with AI about your code directly in the editor."
required    = true

# ── MCP Servers ──────────────────────────────────────────────
# Every block MUST have: name, command
# Include secret_env_keys = ["KEY"] for actual secrets (tokens, passwords)
# Leave env values as "" — the lead shares them during `copilot-setup build`
[[mcp_servers]]
name            = "azure-mcp"
command         = "npx"
args            = ["-y", "@azure/mcp@latest", "server", "start"]
description     = "Gives Copilot access to Azure resources."

# ── Guided Setup Steps ──────────────────────────────────────
# Every block MUST have: name, description
[[setup_steps]]
name           = "azure-login"
description    = "Sign in to Azure"
step_type      = "guided"
command        = "az login"
verify_command = "az account show"
guidance       = "A browser window will open. Sign in with your work email."
```

---

## Step 7 — Set up the profile directory

After the user confirms the profile, create the full profile directory
structure:

```
profiles/<name>/
├── profile.toml
├── copilot/
│   ├── instructions/
│   │   └── copilot-instructions.md    (if found)
│   ├── prompts/                        (if found)
│   │   └── *.prompt.md
│   ├── agents/                         (if found)
│   │   └── *.md
│   └── skills/                         (if found)
│       └── *.prompt.md
└── extensions/                         (if found)
    └── *.md / *.js / etc.
```

Copy all the Copilot files the user selected into this structure.

---

## Step 8 — Explain the build and sharing workflow

Tell the user:

> **Your profile is ready!** Here's what happens next:
>
> 1. **Build the bundle:** Run `copilot-setup build profiles/<name>`
>    - During the build, you'll be asked which MCP configuration values
>      (URLs, database names, paths) to share with your team. Values you
>      share get baked into the bundle so your team doesn't need to enter
>      them.
>    - Actual secrets (tokens, passwords) marked in `secret_env_keys` are
>      NEVER included — each team member enters their own.
>
> 2. **Share the zip:** Send the generated `.zip` file to your team.
>    It contains `Click-Here-To-Setup.bat` — they just double-click it.
>
> 3. **What they get:** Your exact MCP servers, VS Code extensions, Copilot
>    skills, extensions, prompts, and agent configs — all installed
>    automatically with a friendly step-by-step wizard.

---

## Important rules

- **Never include real secrets, tokens, or passwords in the profile.**
  Replace them with `""` and add the key name to `secret_env_keys`.
- **Shareable config values** (URIs, DB names, paths) should also be `""`
  in the profile — the lead will share them during `copilot-setup build`.
- **Write descriptions for a non-technical audience.** Avoid jargon.
- **Ask before including** anything that seems personal or team-specific.
- **Show the user the generated profile** and ask if they'd like to adjust
  anything before saving.
- When the user confirms, save to `profiles/<name>/profile.toml` and copy
  all selected Copilot files into the profile directory.

### Pre-save validation checklist

Before saving the profile, verify every block has its required fields:

- [ ] Every `[[prerequisites]]` has `name`, `display_name`, `description`, `check_command`
- [ ] Every `[[extensions]]` has `id` and `name`
- [ ] Every `[[mcp_servers]]` has `name` and `command`
- [ ] Every `[[setup_steps]]` has `name` and `description`
- [ ] No real secrets or tokens appear as values — only `""`
- [ ] Secret keys are listed in `secret_env_keys`

If any required field is missing, the `copilot-setup build` command will
fail with a validation error. Double-check before saving.
