# 🗂️ Agent File Organizer

> **An intelligent, safety-first file organizer for Linux & XDG desktops, AI Agent Skills, FastMCP, and CLI.**

Unlike simple scripts that mechanically dump every `.jpg` into Pictures and every `.pdf` into Documents, **Agent File Organizer** sorts files the way a careful human would:
- Distinguishes between screenshots, camera/phone captures (via EXIF), receipts, and unknown images.
- Distinguishes Minecraft mod `.jar` files (`fabric`, `forge`, `quilt`) from generic Java apps.
- Organizes music by artist and album (via ID3 tags or filename semantics) while respecting existing flat libraries.
- Separates screen recordings (OBS, Zoom, screencasts) from video clips and movies.
- **Always dry-runs first** and records append-only logs for 100% reversible undos.

---

## 🚀 3 Ways to Use

### 1. 🤖 As an AI Agent Skill (Claude Code & Antigravity)
This repository includes a drop-in **Agent Skill** compliant with the Agent Skills standard.

- **Antigravity (Global)**:
  ```bash
  cp -r skills/file-organizer ~/.gemini/config/skills/
  ```
- **Antigravity (Project-level)**:
  ```bash
  mkdir -p .agents/skills
  cp -r skills/file-organizer .agents/skills/
  ```
- **Claude Code**:
  ```bash
  mkdir -p ~/.claude/skills
  cp -r skills/file-organizer ~/.claude/skills/
  ```

Once installed, simply ask your agent:
> *"Organize my Downloads folder"* or type `file-organizer`

---

### 2. ⚡ As a Model Context Protocol (MCP) Server
Compatible with **Claude Desktop**, **Cursor**, **Zed**, **Windsurf**, and **Antigravity**.

#### Installation:
```bash
pip install -e ".[mcp,media]"
```

#### Claude Desktop / Cursor Config (`mcpServers`):
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

### 3. 💻 As a Standalone Python CLI Tool

#### Install from source:
```bash
pip install -e .
```

#### Basic Commands:

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

1. **Dry-Run First**: Nothing moves without explicit inspection of the generated plan.
2. **Move, Never Delete**: True duplicates are flagged for manual review; files are never deleted automatically.
3. **No Silent Overwrites**: When filenames collide at destination, a numeric suffix `(1)`, `(2)` is appended.
4. **Append-Only Undo Log**: Every single move is `fsync`ed to `~/.file-organizer/logs/moves-*.log`.
5. **No Dotfile Touching**: Hidden files (`.config`, `.git`, etc.) and in-progress downloads (`.crdownload`, `.part`, `.tmp`) are strictly ignored.
6. **Prior Run Memory**: Files already placed by a previous run will not be re-flagged or churned.

---

## 🌐 How to Publish & Share This Online

Here is your step-by-step guide to releasing this package to the public:

### A. Publish on GitHub
1. **Initialize Git Repository**:
   ```bash
   cd "/home/michael/Documents/File Organiser App"
   git init
   git add .
   git commit -m "feat: initial release of agent-file-organizer (Skill, FastMCP, CLI)"
   ```
2. **Create a GitHub Repository**:
   - Go to [github.com/new](https://github.com/new) and create a public repository (e.g. `agent-file-organizer`).
3. **Push Code**:
   ```bash
   git branch -M main
   git remote add origin https://github.com/<your-username>/agent-file-organizer.git
   git push -u origin main
   ```
4. **Add Topics & Tags**:
   - On GitHub, add topics: `agent-skills`, `claude-code`, `antigravity`, `mcp-server`, `fastmcp`, `file-organizer`, `linux-desktop`.

---

### B. Publish to PyPI (Python Package Index)
This allows anyone to run `pip install agent-file-organizer`:

1. **Install build tools**:
   ```bash
   pip install build twine
   ```
2. **Build package distributions**:
   ```bash
   python3 -m build
   ```
3. **Upload to PyPI**:
   ```bash
   twine upload dist/*
   ```

---

### C. Publish to MCP Registries (Smithery & Glama)
1. **Smithery.ai**:
   - Visit [smithery.ai](https://smithery.ai).
   - Sign in with GitHub and click **"Submit a Server"**.
   - Paste your GitHub repo URL.
2. **Glama.ai**:
   - Visit [glama.ai/mcp/servers](https://glama.ai/mcp/servers).
   - Submit your repository for automated indexing.
3. **PulseMCP / MCP.so**:
   - Submit your repo URL to [pulsemcp.com](https://pulsemcp.com) and [mcp.so](https://mcp.so).

---

## 📁 Repository Structure

```text
├── README.md                      # Master Guide & Documentation
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
