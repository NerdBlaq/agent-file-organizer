# 🗂️ Agent File Organizer

> **An intelligent, safety-first, cross-platform file organizer for Windows, macOS, and Linux — powered by AI Agent Skills, FastMCP, and CLI.**

[![PyPI version](https://img.shields.io/pypi/v/agent-file-organizer.svg)](https://pypi.org/project/agent-file-organizer/)
[![smithery badge](https://smithery.ai/badge/michaelattah80/file-organizer)](https://smithery.ai/server/michaelattah80/file-organizer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](https://github.com/NerdBlaq/agent-file-organizer)

Whether you use **Windows File Explorer**, **macOS Finder**, or **Linux desktop managers** (Nautilus, Dolphin, Thunar, etc.), **Agent File Organizer** works directly at the filesystem level. It delivers the careful, nuanced organization a human would do, rather than mechanically dumping files into broad buckets by extension alone.

---

## ⚡ Quick Install

### 🐍 pip (Python package)
```bash
pip install agent-file-organizer
```
👉 [pypi.org/project/agent-file-organizer](https://pypi.org/project/agent-file-organizer/)

---

### 🤖 MCP via Smithery (for AI Agents — Claude, Codex, Cursor, etc.)
Smithery installs and auto-configures the MCP server for your agent client:

**Claude Code / Claude Desktop:**
```bash
npx -y @smithery/cli install michaelattah80/file-organizer --client claude
```

**Cursor:**
```bash
npx -y @smithery/cli install michaelattah80/file-organizer --client cursor
```

**Codex:**
```bash
npx -y @smithery/cli install michaelattah80/file-organizer --client codex
```

**Or browse & install via the web UI:**
👉 [smithery.ai/server/michaelattah80/file-organizer](https://smithery.ai/server/michaelattah80/file-organizer)

---

### 📦 Agent Skill — Install from GitHub
For agents that support external skills (Antigravity, Claude Code, Codex, Cursor, etc.):

**Clone the full repository:**
```bash
git clone https://github.com/NerdBlaq/agent-file-organizer.git
```

**Then copy the skill to your agent's skills folder:**

| Agent | Command |
|---|---|
| **Antigravity (global)** | `cp -r agent-file-organizer/skills/file-organizer ~/.gemini/config/skills/` |
| **Claude Code** | `cp -r agent-file-organizer/skills/file-organizer ~/.claude/skills/` |
| **Any agent (project-level)** | `cp -r agent-file-organizer/skills/file-organizer .agents/skills/` |

**Or download just the skill folder (no git required):**
👉 [Download skills/file-organizer as ZIP](https://github.com/NerdBlaq/agent-file-organizer/archive/refs/heads/main.zip)

---

## 🌟 Why Agent File Organizer?

Traditional file organizers blindly sort by file extension (e.g. all `.jpg`s to Pictures). **Agent File Organizer** uses semantic understanding and content heuristics:

- 📸 **Smart Image Sorting**: Distinguishes between screenshots, camera/phone captures (via EXIF metadata), receipts/invoices, and ambiguous images.
- 🎮 **Minecraft & Mod Support**: Identifies Minecraft mod `.jar` files (`fabric`, `forge`, `quilt`, `neoforge`, `optifine`, `sodium`) and routes them cleanly away from generic application JARs.
- 🎵 **Music & Audio Hierarchy**: Organizes music by `<Artist>/<Album>` using ID3 tags or filename patterns, while respecting existing flat music folders.
- 🎥 **Video Classification**: Separates screen recordings (OBS, Zoom, screencasts) from clips and movies.
- 💻 **Universal Compatibility**: Works natively on **Windows**, **macOS**, and **Linux** without requiring any proprietary file-manager plugins or APIs.
- 🔒 **100% Reversible & Safe**: Every run performs a dry-run plan first, prevents accidental overwrites with collision suffixing, and writes append-only undo logs.

---

## 🚀 3 Ways to Use

### 1. 🤖 As an AI Agent Skill (Antigravity, Claude Code, OpenAI Codex, & More)
This repository includes a drop-in **Agent Skill** compliant with the Agent Skills standard (`SKILL.md`).

#### 🪐 Antigravity
- **Global (All Projects)**:
  ```bash
  cp -r skills/file-organizer ~/.gemini/config/skills/
  ```
- **Project-Level**:
  ```bash
  mkdir -p .agents/skills
  cp -r skills/file-organizer .agents/skills/
  ```

#### 🧠 Claude Code
```bash
mkdir -p ~/.claude/skills
cp -r skills/file-organizer ~/.claude/skills/
```

#### ⚡ OpenAI Codex / ChatGPT Developer Mode
- Place `skills/file-organizer` in your repository root under `.agents/skills/` or `.codex/skills/`.
- Alternatively, include `skills/file-organizer/SKILL.md` in your agent's system prompt or workspace instructions.

#### 🌐 Other AI Agents (Cursor, Windsurf, Aider, Devin, etc.)
This skill works seamlessly with **any AI agent or coding assistant** that supports external skills, custom rules, or runbooks. Simply copy the `skills/file-organizer` directory into your project's `.agents/skills/` folder or reference `SKILL.md`.

Once installed, simply prompt your agent:
> *"Organize my Downloads folder"* or type `/file-organizer`

---

### 2. ⚡ As a Model Context Protocol (MCP) Server
Compatible with **ChatGPT for Desktop**, **Claude Desktop**, **Cursor**, **Zed**, **Windsurf**, and **Antigravity** across Windows, macOS, and Linux.

#### Option A — Install via Smithery (one-click, no setup):
👉 **[smithery.ai/server/agent-file-organizer](https://smithery.ai/server/agent-file-organizer)**

Smithery auto-configures the MCP server for your client — no manual JSON editing needed.

#### Option B — Install via pip:
```bash
pip install agent-file-organizer
```
Or install from source with optional extras:
```bash
pip install -e ".[mcp,media]"
```

#### Client Configuration (`mcpServers`):
Add the following to your MCP settings file (e.g. `claude_desktop_config.json`, ChatGPT Desktop MCP settings, or Cursor MCP config):

```json
{
  "mcpServers": {
    "file-organizer": {
      "command": "file-organizer-mcp",
      "args": []
    }
  }
}
```

#### Available MCP Tools:
- `detect_folder_structure` — Detects whether target directories are flat, by-year, or custom-organized.
- `generate_organize_plan` — Scans files and produces a dry-run move plan with confidence ratings.
- `modify_plan_move` — Interactively alters or resolves a planned destination.
- `remove_move_from_plan` — Drops a move to keep a file untouched.
- `execute_move_plan` — Safely applies confirmed moves with collision protection and creates an undo log.
- `undo_past_moves` — Reverses moves from any previous run log.

---

### 3. 💻 As a Standalone CLI Tool

#### Install from PyPI:
```bash
pip install agent-file-organizer
```

#### Or install from source:
```bash
pip install -e .
```

#### Cross-Platform Commands:

**1. Quick Sort (Fresh-only mode with safe defaults):**
```bash
file-organizer scan --targets ~/Downloads --quick --output /tmp/plan.json
```

**2. Detect Existing Schemes Before Organizing:**
```bash
file-organizer detect --targets ~/Pictures ~/Videos ~/Music
```

**3. Apply Confirmed Plan:**
```bash
file-organizer apply --plan /tmp/plan.json
```

**4. Undo Any Past Run:**
```bash
file-organizer undo ~/.file-organizer/logs/moves-<timestamp>.log
```

---

## 🛡️ Non-Negotiable Safety Rails

1. **Dry-Run First**: Nothing moves without explicit inspection and confirmation of the plan.
2. **Move, Never Delete**: True duplicates are flagged for your manual review; files are never deleted automatically.
3. **No Silent Overwrites**: When filenames collide at destination, a numeric suffix `(1)`, `(2)` is appended.
4. **Append-Only Undo Log**: Every single move is safely recorded and can be reversed with one command (`file-organizer undo`).
5. **No System / Hidden Files**: Hidden files (`.config`, `.git`, `Thumbs.db`, `.DS_Store`) and in-progress downloads (`.crdownload`, `.part`, `.tmp`) are strictly ignored.
6. **Prior Run Memory**: Files already placed by a previous run will not be re-flagged or churned.

---

## 📁 Repository Structure

```text
├── README.md                      # Master Guide & Documentation
├── SKILL.md                       # Agent Skill definition (root)
├── pyproject.toml                 # Package definition & CLI/MCP entrypoints
├── LICENSE                        # MIT License
├── .gitignore                     # Git ignore rules
├── file_organizer/                # Python Core Package
│   ├── __init__.py                # Package version & API
│   ├── cli.py                     # CLI entrypoint (`file-organizer`)
│   ├── server.py                  # FastMCP server (`file-organizer-mcp`)
│   ├── taxonomy.py                # File rules, extensions, regexes
│   └── core/
│       ├── scanner.py             # Classification engine & planner
│       ├── structure.py           # Existing scheme detector
│       ├── applier.py             # Safe move executor with undo logger
│       ├── undo.py                # Undo engine
│       └── plan_editing.py        # Plan editor functions
├── skills/                        # Drop-in Agent Skill
│   └── file-organizer/
│       ├── SKILL.md               # Agent guide with YAML frontmatter
│       ├── scripts/               # Standalone runner scripts
│       ├── references/            # Taxonomy & behavior specs
│       └── assets/                # Example YAML config
└── tests/                         # Unit tests
    ├── test_scanner.py
    ├── test_structure.py
    └── test_applier_undo.py
```

---

## 📄 License
Released under the [MIT License](LICENSE).
