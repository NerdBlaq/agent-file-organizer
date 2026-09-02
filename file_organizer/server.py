"""
FastMCP Server for File Organizer.
Exposes MCP tools for AI agents (Claude Desktop, Cursor, Zed, Windsurf, Antigravity).
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from mcp.server.fastmcp import FastMCP
    HAVE_FASTMCP = True
except ImportError:
    HAVE_FASTMCP = False

from file_organizer.core.structure import detect_structure, render_structure_markdown
from file_organizer.core.scanner import build_plan, render_plan_markdown
from file_organizer.core.applier import apply_plan
from file_organizer.core.undo import execute_undo
from file_organizer.core.plan_editing import add_move, set_dest_dir, drop_move


def create_mcp_server():
    if not HAVE_FASTMCP:
        return None

    mcp = FastMCP(
        name="file-organizer",
        instructions="Intelligent, safety-first file organizer toolset for classifying, sorting, and uncluttering files.",
    )

    @mcp.tool()
    def detect_folder_structure(targets: List[str]) -> str:
        """Detect existing organizational schemes (by-year, custom, default taxonomy, flat) in target directories.
        
        Args:
            targets: List of directory paths (e.g. ["~/Pictures", "~/Music"])
        """
        report = detect_structure(targets)
        return json.dumps(report, indent=2)

    @mcp.tool()
    def generate_organize_plan(
        targets: List[str],
        include: Optional[List[str]] = None,
        recursive: bool = False,
        quick: bool = False,
        structure_mode: Optional[str] = None,
        ambiguous_cap: int = 30,
    ) -> str:
        """Scan directories and build a dry-run move plan without touching any files.
        
        Args:
            targets: List of directory paths to scan (e.g. ["~/Downloads"])
            include: Additional directories to reorganize (e.g. ["~/Pictures"])
            recursive: Whether to recurse into subdirectories
            quick: Fast mode using safe defaults and fresh-only mode
            structure_mode: 'extend' (default), 'reorganize', or 'fresh-only'
            ambiguous_cap: Maximum ambiguous images to flag for review (default 30)
        """
        plan = build_plan(
            targets=targets,
            include=include or [],
            recursive=recursive,
            quick=quick,
            structure_mode=structure_mode,
            ambiguous_cap=ambiguous_cap,
        )
        return json.dumps(plan, indent=2)

    @mcp.tool()
    def modify_plan_move(
        plan_json: str,
        src: str,
        dest_dir: str,
        reason: str = "manual edit"
    ) -> str:
        """Modify or resolve a destination in an existing plan before applying it.
        
        Args:
            plan_json: The current plan as a JSON string
            src: Full source path of the file to modify
            dest_dir: Target folder (e.g. "Pictures/People" or "Downloads/Mods")
            reason: Explanation for this destination choice
        """
        plan = json.loads(plan_json)
        updated = add_move(plan, src=src, dest_dir=dest_dir, reason=reason, confidence="high")
        return json.dumps(updated, indent=2)

    @mcp.tool()
    def remove_move_from_plan(
        plan_json: str,
        src: str
    ) -> str:
        """Remove a planned move so the file remains untouched in its original location.
        
        Args:
            plan_json: The current plan as a JSON string
            src: Full source path of the file to leave in place
        """
        plan = json.loads(plan_json)
        updated = drop_move(plan, src=src)
        return json.dumps(updated, indent=2)

    @mcp.tool()
    def execute_move_plan(
        plan_json: str,
        dry_run: bool = False,
        base_dir: str = "~"
    ) -> str:
        """Apply a confirmed organization plan. Moves files safely with collision handling.
        
        Args:
            plan_json: The plan JSON string to apply
            dry_run: If True, simulates moves without touching the filesystem
            base_dir: Base directory (defaults to home directory '~')
        """
        plan = json.loads(plan_json)
        result = apply_plan(plan=plan, base_dir=base_dir, dry_run=dry_run)
        return json.dumps(result, indent=2)

    @mcp.tool()
    def undo_past_moves(
        log_path: str,
        dry_run: bool = False,
        limit: Optional[int] = None
    ) -> str:
        """Reverse moves from a previous run using its append-only undo log.
        
        Args:
            log_path: Path to the moves-*.log file
            dry_run: If True, previews reversal without moving files
            limit: Optional limit to undo only the last N moves
        """
        result = execute_undo(log_path=log_path, dry_run=dry_run, limit=limit)
        return json.dumps(result, indent=2)

    return mcp


# Standalone stdio JSON-RPC fallback for environments without mcp package installed
def run_stdio_jsonrpc():
    """Lightweight stdio JSON-RPC loop handling basic MCP / RPC requests."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {"name": "detect_folder_structure", "description": "Detect existing organizational schemes."},
                            {"name": "generate_organize_plan", "description": "Scan and build a dry-run organize plan."},
                            {"name": "execute_move_plan", "description": "Apply a confirmed organization plan."},
                            {"name": "undo_past_moves", "description": "Reverse past moves from an undo log."},
                        ]
                    }
                }
            elif method == "ping":
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
            else:
                resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method {method} not found"}}
            
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"RPC Error: {e}\n")


def main():
    if HAVE_FASTMCP:
        server = create_mcp_server()
        if server:
            server.run()
            return
    run_stdio_jsonrpc()


if __name__ == "__main__":
    main()
