"""
CLI entrypoint for file-organizer.
"""
import argparse
import json
import sys
from pathlib import Path

from file_organizer.core.structure import detect_structure, render_structure_markdown
from file_organizer.core.scanner import build_plan, render_plan_markdown, load_config
from file_organizer.core.applier import apply_plan
from file_organizer.core.undo import execute_undo
from file_organizer.core.verify import verify_recovery, render_verify_text
from file_organizer.core.session_log import log_session, read_sessions
from file_organizer.core.plan_editing import (
    load_plan, save_plan, add_move, set_dest_dir, drop_move
)


def cmd_detect(args):
    report = detect_structure(args.targets)
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(report, indent=2))
        md_path = out_path.with_suffix(".md")
        md_path.write_text(render_structure_markdown(report))
        print(f"Structure report written to {out_path} and {md_path}")
    else:
        print(render_structure_markdown(report))


def cmd_scan(args):
    config = load_config(args.config) if args.config else {}
    structure_report = None
    if args.structure_report:
        structure_report = json.loads(Path(args.structure_report).read_text())

    plan = build_plan(
        targets=args.targets,
        include=args.include,
        config=config,
        recursive=args.recursive,
        ambiguous_cap=args.ambiguous_cap,
        structure_report=structure_report,
        structure_mode=args.structure_mode,
        quick=args.quick,
        log_dir=args.log_dir,
    )

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(plan, indent=2))
        md_path = out_path.with_suffix(".md")
        md_path.write_text(render_plan_markdown(plan))
        print(f"Plan written to {out_path} and {md_path}")
    else:
        print(render_plan_markdown(plan))


def cmd_apply(args):
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"ERROR: Plan file not found: {plan_path}", file=sys.stderr)
        sys.exit(1)

    plan = json.loads(plan_path.read_text())
    result = apply_plan(
        plan=plan,
        base_dir=args.base,
        dry_run=args.dry_run,
        log_dir=args.log_dir,
        allow_cross_filesystem=args.allow_cross_filesystem,
    )

    if result.get("aborted"):
        print(f"ABORTED before moving anything: {result['abort_reason']}", file=sys.stderr)
        for v in result.get("cross_filesystem_violations", [])[:10]:
            print(f"  {v}", file=sys.stderr)
        sys.exit(1)

    print(f"Base: {result['base']}")
    if args.dry_run:
        print(f"--dry-run: No files moved. Log path would be: {result['log_path']}")
        for act in result.get("actions", []):
            if act.get("status") == "would_move":
                print(f"  WOULD MOVE: {act['src']} -> {act['dest']}")
    else:
        print(f"Moved {result['moved']} file(s) ({result['failed']} failed, {result['skipped_noop']} no-op, "
              f"{result.get('protected_skipped', 0)} protected-directory item(s) skipped).")
        print(f"Undo log written to: {result['log_path']}")
        if result.get("collisions"):
            print(f"Note: {len(result['collisions'])} name collision(s) resolved with numeric suffixes.")


def cmd_verify(args):
    try:
        result = verify_recovery(args.log_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    print(render_verify_text(result))
    if not result["complete"]:
        sys.exit(1)


def cmd_log_session(args):
    path = log_session(
        event=args.event,
        log_dir=args.log_dir,
        user_request=args.user_request,
        mode=args.mode,
        structure_mode=args.structure_mode,
        targets=args.targets,
        confirmation=args.confirmation,
        notes=args.notes,
    )
    print(f"Logged to {path}")


def cmd_show_sessions(args):
    entries = read_sessions(args.log_dir)
    if not entries:
        print("No session log entries found.")
        return
    for e in entries:
        print(json.dumps(e, indent=2))


def cmd_undo(args):
    try:
        res = execute_undo(log_path=args.log_path, dry_run=args.dry_run, limit=args.limit)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Log: {res['log_path']}")
    print(f"Total entries: {res['total_lines']}")
    print(f"Would revert / Reverted: {res['reverted_count']} file(s)")

    if res.get("to_revert"):
        for src, dest in res["to_revert"]:
            print(f"  {dest} -> {src}")
    if res.get("conflicts"):
        print(f"\n{len(res['conflicts'])} conflict(s) skipped:")
        for src, dest, reason in res["conflicts"]:
            print(f"  {dest} -/-> {src} ({reason})")
    if res.get("already_gone"):
        print(f"\n{len(res['already_gone'])} entry(ies) destination gone:")
        for src, dest, reason in res["already_gone"]:
            print(f"  {dest} ({reason})")

    if args.dry_run:
        print("\n--dry-run: Nothing was moved.")


def main():
    parser = argparse.ArgumentParser(
        prog="file-organizer",
        description="Intelligent file organizer for Windows, macOS, and Linux, Agent Skills, and MCP."
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    # detect
    p_detect = subparsers.add_parser("detect", help="Detect existing organizational structure")
    p_detect.add_argument("--targets", nargs="+", required=True, help="Target directories to check")
    p_detect.add_argument("--output", "-o", help="Optional output JSON path")

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan directories and generate a dry-run plan")
    p_scan.add_argument("--targets", nargs="+", required=True, help="Target directories to organize")
    p_scan.add_argument("--include", nargs="*", default=[], help="Additional directories to include")
    p_scan.add_argument("--config", help="YAML config file")
    p_scan.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    p_scan.add_argument("--ambiguous-cap", type=int, default=30, help="Max ambiguous photos to flag")
    p_scan.add_argument("--structure-report", help="JSON report from detect command")
    p_scan.add_argument("--structure-mode", help="extend|reorganize|fresh-only")
    p_scan.add_argument("--quick", action="store_true", help="Quick mode (fresh-only, sensible defaults)")
    p_scan.add_argument("--log-dir", default="~/.file-organizer/logs", help="Undo log directory")
    p_scan.add_argument("--output", "-o", help="Output plan.json path (plan.md written alongside)")

    # apply
    p_apply = subparsers.add_parser("apply", help="Apply a confirmed plan")
    p_apply.add_argument("--plan", required=True, help="Path to plan.json")
    p_apply.add_argument("--base", default=None,
                          help="Base directory that dest_dir entries are relative to. If omitted, derived from "
                               "the plan's own 'targets' field instead of defaulting to home (v1.1.2).")
    p_apply.add_argument("--dry-run", action="store_true", help="Simulate without moving")
    p_apply.add_argument("--log-dir", default="~/.file-organizer/logs", help="Undo log directory")
    p_apply.add_argument("--allow-cross-filesystem", action="store_true",
                          help="Permit moves whose destination resolves onto a different filesystem/drive than "
                               "the base. Off by default — this is the exact failure mode from a real incident "
                               "where files moved from an external drive onto the OS partition unintentionally.")

    # undo
    p_undo = subparsers.add_parser("undo", help="Reverse a past run from its undo log")
    p_undo.add_argument("log_path", help="Path to moves-*.log")
    p_undo.add_argument("--dry-run", action="store_true", help="Preview undo without moving")
    p_undo.add_argument("--limit", type=int, help="Only undo last N moves")

    # verify (v1.1.2)
    p_verify = subparsers.add_parser("verify", help="Check a moves log against actual filesystem state — run this before declaring a recovery complete")
    p_verify.add_argument("log_path", help="Path to moves-*.log")

    # log-session (v1.1.3)
    p_log = subparsers.add_parser("log-session", help="Record a structured entry about this run — what was asked, what was chosen, what was confirmed")
    p_log.add_argument("--event", required=True, help="Short label: run_started, mode_chosen, plan_built, confirmed, applied, recovery, etc.")
    p_log.add_argument("--user-request", help="The user's own request, verbatim or faithfully summarized")
    p_log.add_argument("--mode", help="quick / guided / autonomous")
    p_log.add_argument("--structure-mode", help="extend / reorganize / fresh-only")
    p_log.add_argument("--targets", nargs="*", help="Directories involved in this run")
    p_log.add_argument("--confirmation", help="What the user actually said to approve this action, verbatim where practical")
    p_log.add_argument("--notes", help="Anything else worth recording (errors, surprises, protected dirs found)")
    p_log.add_argument("--log-dir", default="~/.file-organizer/logs")

    # show-sessions (v1.1.3)
    p_show = subparsers.add_parser("show-sessions", help="Print the recorded session log")
    p_show.add_argument("--log-dir", default="~/.file-organizer/logs")

    # Quick shortcut at top level if no subcommand given but --targets provided
    if len(sys.argv) > 1 and sys.argv[1] not in ("detect", "scan", "apply", "undo", "verify", "log-session", "show-sessions", "-h", "--help"):
        # Default to scan command
        sys.argv.insert(1, "scan")

    args = parser.parse_args()

    if args.subcommand == "detect":
        cmd_detect(args)
    elif args.subcommand == "scan":
        cmd_scan(args)
    elif args.subcommand == "apply":
        cmd_apply(args)
    elif args.subcommand == "undo":
        cmd_undo(args)
    elif args.subcommand == "verify":
        cmd_verify(args)
    elif args.subcommand == "log-session":
        cmd_log_session(args)
    elif args.subcommand == "show-sessions":
        cmd_show_sessions(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
