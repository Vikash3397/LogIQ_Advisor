"""LogIQ Advisor - agent-based log-analysis pipeline.

Deterministic helpers used by the LogIQ Advisor agents:
- ``collector``: parse multi-format logs into structured error context.
- ``schemas``: data contracts shared across the three pipeline stages.
- ``io_utils``: run-directory management and JSON persistence.
- ``synthesizer``: validate and persist the final resolution artifact.
- ``orchestrate``: CLI entry point for the deterministic collector stage.
"""

__version__ = "0.1.0"
