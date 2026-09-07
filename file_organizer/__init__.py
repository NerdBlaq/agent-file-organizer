"""
Agent File Organizer - Intelligent, safety-first file organizer for Windows, macOS, and Linux, Agent Skills, and MCP.
"""
__version__ = "1.0.0"

from file_organizer.core import (
    detect_structure,
    build_plan,
    apply_plan,
    execute_undo,
    load_plan,
    save_plan,
    add_move,
    set_dest_dir,
    drop_move,
)

__all__ = [
    "__version__",
    "detect_structure",
    "build_plan",
    "apply_plan",
    "execute_undo",
    "load_plan",
    "save_plan",
    "add_move",
    "set_dest_dir",
    "drop_move",
]
