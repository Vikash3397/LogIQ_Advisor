"""Run-directory management and JSON persistence for LogIQ Advisor.

All artifacts for a single run live under ``data/runs/<run_id>/``. ``run_id``
defaults to ``<app_name>-<UTC-timestamp>``.

Each new Collector run clears ``data/runs/`` first so only the current run's
artifacts remain on disk.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ERRORS_FILE = "errors.json"
RESEARCH_FILE = "research.json"
RESOLUTION_FILE = "resolution.json"
RESOLUTION_REPORT_FILE = "resolution.txt"


def project_root() -> Path:
    """Return the repository root (parent of the ``logiq`` package)."""
    return Path(__file__).resolve().parent.parent


def runs_dir() -> Path:
    return project_root() / "data" / "runs"


def _remove_readonly(func, path, _exc_info) -> None:
    """Clear the read-only bit on Windows and retry a failed rmtree/unlink."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clear_runs_dir() -> None:
    """Remove all files and subdirectories under ``data/runs/``.

    Called at the start of each Collector run so a new pipeline execution
    replaces the previous run's artifacts instead of accumulating them.
    The placeholder ``.gitkeep`` file is preserved so the directory stays in git.
    """
    root = runs_dir()
    root.mkdir(parents=True, exist_ok=True)
    for child in root.iterdir():
        if child.name == ".gitkeep":
            continue
        try:
            if child.is_dir():
                shutil.rmtree(child, onerror=_remove_readonly)
            else:
                child.unlink()
        except OSError as exc:
            raise RuntimeError(
                f"Could not clear prior run artifact '{child.name}' under data/runs/. "
                "Close any open files in that folder and retry."
            ) from exc


def slugify(value: str) -> str:
    """Make a filesystem-safe slug from an arbitrary string."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return slug or "app"


def make_run_id(app_name: str) -> str:
    """Build a default run id: ``<app-slug>-<UTC timestamp>``."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{slugify(app_name)}-{stamp}"


def run_path(run_id: str) -> Path:
    return runs_dir() / run_id


def ensure_run_dir(run_id: str) -> Path:
    """Create (if needed) and return the run directory for ``run_id``."""
    path = run_path(run_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Dict[str, Any]) -> Path:
    """Write ``payload`` as UTF-8 JSON (``ensure_ascii=False``)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_text(path: Path, text: str) -> Path:
    """Write ``text`` as a UTF-8 file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def errors_path(run_id: str) -> Path:
    return run_path(run_id) / ERRORS_FILE


def research_path(run_id: str) -> Path:
    return run_path(run_id) / RESEARCH_FILE


def resolution_path(run_id: str) -> Path:
    return run_path(run_id) / RESOLUTION_FILE


def resolution_report_path(run_id: str) -> Path:
    return run_path(run_id) / RESOLUTION_REPORT_FILE
