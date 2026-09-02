# 🗂️ Agent File Organizer

> **An intelligent, safety-first, cross-platform file organizer for Windows, macOS, and Linux.**

[![PyPI version](https://img.shields.io/pypi/v/agent-file-organizer.svg)](https://pypi.org/project/agent-file-organizer/)
[![smithery badge](https://smithery.ai/badge/michaelattah80/file-organizer)](https://smithery.ai/server/michaelattah80/file-organizer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](https://github.com/NerdBlaq/agent-file-organizer)

Organize your Downloads, Documents, Pictures, Videos, and Music folders with one command — or let your AI agent do it for you. Works with **Windows File Explorer**, **macOS Finder**, and **Linux file managers** (Nautilus, Dolphin, Thunar, etc.) without any plugins or special setup.

> 💡 **No AI agent? No problem.** The CLI works completely **offline** with no internet connection, no API keys, and no AI agent required. The intelligence is built in.

---

## ✨ What Makes It Smart

Unlike tools that blindly sort by file extension, Agent File Organizer uses content-aware heuristics:

- 📸 **Smart Photos** — Tells apart screenshots, camera shots (via EXIF), and scanned receipts
- 🎵 **Music Hierarchy** — Sorts by `Artist / Album` using ID3 tags or filename patterns
- 🎥 **Video Classification** — Separates screen recordings (OBS, Zoom) from regular videos
- 🎮 **Game Mod Detection** — Identifies Minecraft mod `.jar` files and keeps them separate from regular apps
- 🔒 **Always Safe** — Dry-run preview before anything moves, full undo support, no silent overwrites

---

## 📦 Install

### Via pip *(works offline, no agent needed)*
```bash
pip install agent-file-organizer
```
👉 [pypi.org/project/agent-file-organizer](https://pypi.org/project/agent-file-organizer/)

### Via Smithery *(for AI agent MCP setup)*
Smithery auto-installs and configures the MCP server for your agent — no manual JSON editing needed.

```bash
# Claude Code / Claude Desktop
npx -y @smithery/cli install michaelattah80/file-organizer --client claude

# Cursor
npx -y @smithery/cli install michaelattah80/file-organizer --client cursor

# Codex
npx -y @smithery/cli install michaelattah80/file-organizer --client codex
```
👉 [smithery.ai/server/michaelattah80/file-organizer](https://smithery.ai/server/michaelattah80/file-organizer)

### Via GitHub *(for the Agent Skill)*
```bash
git clone https://github.com/NerdBlaq/agent-file-organizer.git
```
Or [download as ZIP](https://github.com/NerdBlaq/agent-file-organizer/archive/refs/heads/main.zip) — no git required.

---

## 🚀 3 Ways to Use

### 1. 💻 CLI — Offline, No Agent Required

After `pip install agent-file-organizer`, run these commands directly in your terminal:

**Scan and preview (nothing moves yet):**
```bash
file-organizer scan --targets ~/Downloads --output /tmp/plan.json
```

**Apply the plan:**
```bash
file-organizer apply --plan /tmp/plan.json
```

**Undo any past run:**
```bash
file-organizer undo ~/.file-organizer/logs/moves-<timestamp>.log
```

**Detect existing folder structure first:**
```bash
file-organizer detect --targets ~/Pictures ~/Videos ~/Music
```

---

### 2. 🤖 Agent Skill — For AI Coding Assistants

Drop the skill into your agent and simply say *"Organize my Downloads folder"*.

| Agent | Install Command |
|---|---|
| **Antigravity** (global) | `cp -r agent-file-organizer/skills/file-organizer ~/.gemini/config/skills/` |
| **Antigravity** (project) | `cp -r agent-file-organizer/skills/file-organizer .agents/skills/` |
| **Claude Code** | `cp -r agent-file-organizer/skills/file-organizer ~/.claude/skills/` |
| **Codex / Any agent** | Copy `skills/file-organizer/` into `.agents/skills/` or `.codex/skills/` in your project |

Works with any agent that supports external skills, custom rules, or runbooks (Cursor, Windsurf, Aider, Devin, GitHub Copilot, etc.).

---

### 3. ⚙️ MCP Server — For AI Desktop Apps

Connect Agent File Organizer directly to **Claude Desktop**, **ChatGPT for Desktop**, **Cursor**, **Zed**, or **Windsurf** via the Model Context Protocol.

**Easiest way — use Smithery** (see Install section above).

**Or configure manually** — add this to your MCP settings file (`claude_desktop_config.json`, Cursor MCP config, etc.):
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

**Available MCP tools your agent can call:**

| Tool | What it does |
|---|---|
| `detect_folder_structure` | Detects if a folder is flat, by-year, or custom-organized |
| `generate_organize_plan` | Scans files and builds a dry-run move plan |
| `modify_plan_move` | Adjusts a planned destination before applying |
| `remove_move_from_plan` | Excludes a file from the plan |
| `execute_move_plan` | Applies moves safely with collision protection |
| `undo_past_moves` | Reverses any previous run |

---

## 🛡️ Safety Guarantees

1. **Dry-run first** — nothing moves until you review and confirm the plan
2. **Move, never delete** — duplicates are flagged for your review, never auto-deleted
3. **No silent overwrites** — filename collisions get a suffix: `file (1).jpg`, `file (2).jpg`
4. **Full undo** — every move is logged and 100% reversible
5. **Skips system files** — ignores `.DS_Store`, `Thumbs.db`, `.git`, `.tmp`, `.crdownload`, etc.
6. **Remembers past runs** — files already organized won't be moved again

---

## 📄 License

Released under the [MIT License](LICENSE).
