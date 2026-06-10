"""Data contracts shared across the LogIQ Advisor pipeline stages.

Each stage produces one JSON artifact:
- Collector  -> ``errors.json``     (:class:`ErrorsDocument`)
- Researcher -> ``research.json``   (:class:`ResearchDocument`)
- Synthesizer-> ``resolution.json`` (:class:`ResolutionDocument`)

The dataclasses double as serializers (``to_dict``) and the ``validate_*``
functions provide lightweight, dependency-free validation of dict payloads
(e.g. JSON written by an agent rather than by these classes).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

ERROR_LEVELS = {"ERROR", "WARNING", "EXCEPTION", "CRITICAL", "FATAL"}
REFERENCE_TYPES = {"web", "glean", "bmc_helix"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Collector: errors.json
# ---------------------------------------------------------------------------
@dataclass
class ErrorRecord:
    id: str
    level: str
    message: str
    source_file: str
    line_no: int
    timestamp: Optional[str] = None
    module: Optional[str] = None
    stack_trace: Optional[str] = None
    context_lines: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ErrorsDocument:
    run_id: str
    app_name: str
    errors: List[ErrorRecord] = field(default_factory=list)
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "app_name": self.app_name,
            "generated_at": self.generated_at,
            "errors": [e.to_dict() for e in self.errors],
        }


# ---------------------------------------------------------------------------
# Researcher: research.json
# ---------------------------------------------------------------------------
@dataclass
class Reference:
    type: str
    title: str
    url_or_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    error_id: str
    likely_causes: List[str] = field(default_factory=list)
    resolutions: List[str] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    confidence: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "likely_causes": self.likely_causes,
            "resolutions": self.resolutions,
            "references": [r.to_dict() for r in self.references],
            "confidence": self.confidence,
        }


@dataclass
class ResearchDocument:
    run_id: str
    app_name: str
    findings: List[Finding] = field(default_factory=list)
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "app_name": self.app_name,
            "generated_at": self.generated_at,
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Synthesizer: resolution.json (one summary per distinct error pattern)
# ---------------------------------------------------------------------------
@dataclass
class ResolutionSummary:
    error_summary: str
    root_cause: str
    resolution_steps: List[str] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_summary": self.error_summary,
            "root_cause": self.root_cause,
            "resolution_steps": self.resolution_steps,
            "references": [r.to_dict() for r in self.references],
        }


@dataclass
class ResolutionDocument:
    run_id: str
    app_name: str
    summaries: List[ResolutionSummary] = field(default_factory=list)
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "app_name": self.app_name,
            "generated_at": self.generated_at,
            "summaries": [s.to_dict() for s in self.summaries],
        }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class SchemaError(ValueError):
    """Raised when a payload does not satisfy a LogIQ data contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SchemaError(message)


def _require_keys(obj: Dict[str, Any], keys: List[str], where: str) -> None:
    _require(isinstance(obj, dict), f"{where}: expected an object")
    missing = [k for k in keys if k not in obj]
    _require(not missing, f"{where}: missing keys {missing}")


def _validate_references(refs: Any, where: str) -> None:
    _require(isinstance(refs, list), f"{where}.references must be a list")
    for i, ref in enumerate(refs):
        loc = f"{where}.references[{i}]"
        _require_keys(ref, ["type", "title", "url_or_id"], loc)
        _require(
            ref["type"] in REFERENCE_TYPES,
            f"{loc}.type must be one of {sorted(REFERENCE_TYPES)}",
        )


def validate_errors_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(doc, ["run_id", "app_name", "generated_at", "errors"], "errors")
    _require(isinstance(doc["errors"], list), "errors.errors must be a list")
    seen_ids: set = set()
    for i, err in enumerate(doc["errors"]):
        loc = f"errors.errors[{i}]"
        _require_keys(
            err,
            ["id", "level", "message", "source_file", "line_no"],
            loc,
        )
        _require(err["id"] not in seen_ids, f"{loc}.id duplicated: {err['id']}")
        seen_ids.add(err["id"])
        _require(
            err["level"] in ERROR_LEVELS,
            f"{loc}.level must be one of {sorted(ERROR_LEVELS)}",
        )
    return doc


def validate_research_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(doc, ["run_id", "app_name", "generated_at", "findings"], "research")
    _require(isinstance(doc["findings"], list), "research.findings must be a list")
    for i, finding in enumerate(doc["findings"]):
        loc = f"research.findings[{i}]"
        _require_keys(
            finding,
            ["error_id", "likely_causes", "resolutions", "references", "confidence"],
            loc,
        )
        _require(
            finding["confidence"] in CONFIDENCE_LEVELS,
            f"{loc}.confidence must be one of {sorted(CONFIDENCE_LEVELS)}",
        )
        _validate_references(finding["references"], loc)
    return doc


def validate_resolution_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(doc, ["run_id", "app_name", "generated_at", "summaries"], "resolution")
    _require(isinstance(doc["summaries"], list), "resolution.summaries must be a list")
    for i, summary in enumerate(doc["summaries"]):
        loc = f"resolution.summaries[{i}]"
        _require_keys(
            summary,
            ["error_summary", "root_cause", "resolution_steps", "references"],
            loc,
        )
        _require(
            isinstance(summary["resolution_steps"], list),
            f"{loc}.resolution_steps must be a list",
        )
        _validate_references(summary["references"], loc)
    return doc
