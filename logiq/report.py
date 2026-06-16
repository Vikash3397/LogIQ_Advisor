"""Human-readable report rendering for the LogIQ Advisor pipeline.

Deterministic, dependency-free formatting of a validated ``resolution.json``
document into an easy-to-read plain-text report (``resolution.txt``) written to
the same run directory. No web/Glean/DB access.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import io_utils

WRAP_WIDTH = 88
RULE_HEAVY = "=" * WRAP_WIDTH
RULE_LIGHT = "-" * WRAP_WIDTH

REFERENCE_TYPE_LABELS = {
    "web": "Web",
    "glean": "Glean",
    "bmc_helix": "BMC Helix ITSM",
}


def _wrap(text: str, indent: str = "") -> List[str]:
    """Wrap a paragraph to ``WRAP_WIDTH``, preserving an optional indent."""
    text = (text or "").strip()
    if not text:
        return [""]
    return textwrap.wrap(
        text,
        width=WRAP_WIDTH,
        initial_indent=indent,
        subsequent_indent=indent,
    ) or [""]


def _section(title: str) -> List[str]:
    return [title, "-" * len(title)]


def _render_summary(index: int, summary: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    lines.append(f"ERROR {index}")
    lines.append(RULE_LIGHT)
    lines.append("")

    lines.extend(_section("ERROR SUMMARY"))
    lines.extend(_wrap(summary.get("error_summary", "")))
    lines.append("")

    lines.extend(_section("ROOT CAUSE"))
    lines.extend(_wrap(summary.get("root_cause", "")))
    lines.append("")

    lines.extend(_section("RESOLUTION STEPS"))
    steps = summary.get("resolution_steps") or []
    if steps:
        for step_no, step in enumerate(steps, start=1):
            prefix = f"  {step_no}. "
            hanging = " " * len(prefix)
            wrapped = textwrap.wrap(str(step).strip(), width=WRAP_WIDTH - len(prefix)) or [""]
            lines.append(prefix + wrapped[0])
            lines.extend(hanging + cont for cont in wrapped[1:])
    else:
        lines.append("  (none provided)")
    lines.append("")

    lines.extend(_section("REFERENCES"))
    refs = summary.get("references") or []
    if refs:
        for ref in refs:
            label = REFERENCE_TYPE_LABELS.get(ref.get("type", ""), ref.get("type", "Reference"))
            title = (ref.get("title") or "").strip()
            url_or_id = (ref.get("url_or_id") or "").strip()
            lines.append(f"  [{label}] {title}")
            if url_or_id:
                lines.append(f"      {url_or_id}")
    else:
        lines.append("  (none provided)")
    lines.append("")
    return lines


def render_resolution_text(doc: Dict[str, Any]) -> str:
    """Render a validated ``resolution.json`` dict as a plain-text report."""
    summaries = doc.get("summaries") or []
    lines: List[str] = []
    lines.append(RULE_HEAVY)
    lines.append("LogIQ Advisor - Resolution Report")
    lines.append(RULE_HEAVY)
    lines.append(f"Application : {doc.get('app_name', '')}")
    lines.append(f"Run ID      : {doc.get('run_id', '')}")
    lines.append(f"Generated   : {doc.get('generated_at', '')}")
    lines.append(f"Distinct errors : {len(summaries)}")
    lines.append("")

    if not summaries:
        lines.append("No errors were synthesized for this run.")
        lines.append("")
    else:
        for index, summary in enumerate(summaries, start=1):
            lines.extend(_render_summary(index, summary))

    lines.append(RULE_HEAVY)
    lines.append("End of report")
    lines.append(RULE_HEAVY)
    return "\n".join(lines) + "\n"


def write_report(
    run_id: str,
    doc: Optional[Dict[str, Any]] = None,
    out_path: Optional[Path] = None,
) -> Path:
    """Render and write ``resolution.txt`` for a run.

    When ``doc`` is omitted, the run's ``resolution.json`` is read from disk.
    """
    if doc is None:
        doc = io_utils.read_json(io_utils.resolution_path(run_id))
    text = render_resolution_text(doc)
    target = out_path or io_utils.resolution_report_path(run_id)
    return io_utils.write_text(target, text)
