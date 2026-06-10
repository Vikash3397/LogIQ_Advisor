"""CLI entry point for the deterministic Collector stage of LogIQ Advisor.

Usage:
    python -m logiq.orchestrate --app-name <name> [--input <path>] [--run-id <id>]
                                [--levels ERROR EXCEPTION CRITICAL ...]

``--input`` is optional and defaults to the repo's ``data/input`` folder.

This runs Agent 1 (Log Collector): it parses the input logs, creates the run
directory ``data/runs/<run_id>/``, and writes ``errors.json``. The Researcher
and Synthesizer stages are agent-driven (the Cursor ``logiq-research`` and
``logiq-synthesize`` agents, or the ``/logiq-run`` orchestration command), and
consume the same ``run_id``.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from typing import List, Optional, Sequence

from . import collector, io_utils
from .schemas import ErrorsDocument, validate_errors_document

# Default input location when no path is provided: the repo's data/input folder.
DEFAULT_INPUT_PATH = str(io_utils.project_root() / "data" / "input")


def run_collector(
    app_name: str,
    input_path: Optional[str] = None,
    run_id: Optional[str] = None,
    levels: Optional[Sequence[str]] = None,
) -> dict:
    """Parse logs and write ``errors.json``. Returns a small run summary.

    ``input_path`` defaults to the repo's ``data/input`` folder when omitted.

    Previous run artifacts under ``data/runs/`` are deleted before writing.
    """
    input_path = input_path or DEFAULT_INPUT_PATH
    io_utils.clear_runs_dir()
    run_id = run_id or io_utils.make_run_id(app_name)
    io_utils.ensure_run_dir(run_id)

    records = collector.parse_path(input_path, levels=levels)
    document = ErrorsDocument(run_id=run_id, app_name=app_name, errors=records)
    payload = validate_errors_document(document.to_dict())
    out_path = io_utils.write_json(io_utils.errors_path(run_id), payload)

    by_level = Counter(r.level for r in records)
    return {
        "run_id": run_id,
        "app_name": app_name,
        "errors_path": str(out_path),
        "error_count": len(records),
        "by_level": dict(by_level),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logiq.orchestrate",
        description="LogIQ Advisor - run the deterministic Log Collector stage.",
    )
    parser.add_argument("--app-name", required=True, help="Application name for this run.")
    parser.add_argument(
        "--input",
        default=None,
        help=(
            "Path to a log file or a directory of logs (.txt/.log/.csv/.xlsx). "
            "Defaults to the repo's data/input folder when omitted."
        ),
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Reuse an existing run id. Defaults to <app-name>-<UTC-timestamp>.",
    )
    parser.add_argument(
        "--levels",
        nargs="*",
        default=None,
        metavar="LEVEL",
        help=(
            "Filter to these levels. Default: ERROR EXCEPTION CRITICAL FATAL "
            "(excludes WARNING and informational messages)."
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        summary = run_collector(
            app_name=args.app_name,
            input_path=args.input,
            run_id=args.run_id,
            levels=args.levels,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"[logiq] collector failed: {exc}", file=sys.stderr)
        return 1

    print("[logiq] Collector stage complete.")
    print(f"  run_id      : {summary['run_id']}")
    print(f"  app_name    : {summary['app_name']}")
    print(f"  errors      : {summary['error_count']} {summary['by_level']}")
    print(f"  errors.json : {summary['errors_path']}")
    print()
    print("Next steps (agent-driven, in Cursor):")
    print(f"  /logiq-research {summary['run_id']}")
    print(f"  /logiq-synthesize {summary['run_id']}")
    print("  or run the whole pipeline with /logiq-run <app-name>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
