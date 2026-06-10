"""Agent 3 - Log Synthesizer: validation and persistence helpers.

The synthesis *reasoning* (root cause, resolution steps) is performed by the
Synthesizer agent. This module performs the deterministic parts: joining the
two upstream artifacts, deduplicating to distinct error patterns, validating
the agent-produced resolution against the ``resolution.json`` contract, and
persisting it. No web/Glean/DB access.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import io_utils
from .schemas import (
    Reference,
    ResolutionDocument,
    ResolutionSummary,
    utc_now_iso,
    validate_errors_document,
    validate_research_document,
    validate_resolution_document,
)


def load_inputs(run_id: str) -> Dict[str, Any]:
    """Load and validate ``errors.json`` and ``research.json`` for a run."""
    errors = validate_errors_document(io_utils.read_json(io_utils.errors_path(run_id)))
    research = validate_research_document(io_utils.read_json(io_utils.research_path(run_id)))
    return {"errors": errors, "research": research}


def build_join_index(run_id: str) -> Dict[str, Dict[str, Any]]:
    """Return a per-error view joining error context with its research finding.

    Useful scaffolding for the Synthesizer agent: it gets, per ``error_id``, the
    original error record and the matching research finding (or ``None``).
    """
    inputs = load_inputs(run_id)
    findings_by_id = {f["error_id"]: f for f in inputs["research"]["findings"]}
    joined: Dict[str, Dict[str, Any]] = {}
    for err in inputs["errors"]["errors"]:
        eid = err["id"]
        joined[eid] = {"error": err, "finding": findings_by_id.get(eid)}
    return joined


def _coerce_reference(ref: Any) -> Reference:
    if isinstance(ref, Reference):
        return ref
    return Reference(
        type=ref.get("type", "web"),
        title=ref.get("title", ""),
        url_or_id=ref.get("url_or_id", ""),
    )


def distinct_error_key(message: str) -> str:
    """Normalize an error message so duplicate log lines collapse to one key."""
    key = re.sub(r"@[0-9a-fA-F]+", "@#", message)
    return re.sub(r"\d+", "#", key).strip()


def _dedupe_summaries(
    run_id: str,
    results: List[Dict[str, Any]],
) -> List[ResolutionSummary]:
    """Collapse per-error-id results into one summary per distinct error pattern."""
    errors_doc = validate_errors_document(io_utils.read_json(io_utils.errors_path(run_id)))
    results_by_id = {r["error_id"]: r for r in results}

    seen_keys: List[str] = []
    summaries: List[ResolutionSummary] = []
    for err in errors_doc["errors"]:
        key = distinct_error_key(err["message"])
        if key in seen_keys:
            continue
        seen_keys.append(key)
        result = results_by_id[err["id"]]
        summaries.append(
            ResolutionSummary(
                error_summary=result.get("error_summary", ""),
                root_cause=result.get("root_cause", ""),
                resolution_steps=list(result.get("resolution_steps", [])),
                references=[_coerce_reference(x) for x in result.get("references", [])],
            )
        )
    return summaries


def build_resolution_document(
    run_id: str,
    app_name: str,
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Assemble a validated resolution document from per-error-id agent results."""
    doc = ResolutionDocument(
        run_id=run_id,
        app_name=app_name,
        generated_at=utc_now_iso(),
        summaries=_dedupe_summaries(run_id, results),
    )
    return validate_resolution_document(doc.to_dict())


def persist_resolution(
    run_id: str,
    app_name: str,
    results: List[Dict[str, Any]],
    out_path: Optional[Path] = None,
) -> Path:
    """Validate ``results``, dedupe to distinct errors, and write ``resolution.json``."""
    payload = build_resolution_document(run_id, app_name, results)
    target = out_path or io_utils.resolution_path(run_id)
    return io_utils.write_json(target, payload)
