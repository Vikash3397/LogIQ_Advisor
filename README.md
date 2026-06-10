# LogIQ Advisor

LogIQ Advisor is a Cursor-native, three-agent pipeline that turns raw log files into
clear, actionable diagnostics: an error summary, a validated root cause, and resolution
steps, persisted as machine-readable JSON.

```
logs + app_name --> [1. Collector] --> errors.json
errors.json      --> [2. Researcher] --> research.json   (web + Glean MCP / BMC Helix)
errors.json + research.json --> [3. Synthesizer] --> resolution.json
```

## Agents

| Stage | Agent | Role | External access |
| ----- | ----- | ---- | --------------- |
| 1 | Log Collector | Parse `.txt/.log/.csv/.xlsx`, extract errors + context | Reads input, writes `errors.json` |
| 2 | Log Researcher | Research causes/resolutions per error | Public web + Glean MCP (incl. BMC Helix ITSM). Read-only |
| 3 | Log Synthesizer | Consolidate into final root cause + resolution | None (no web/Glean/DB), read-only |

Each stage is a custom Cursor agent in [`.cursor/agents/`](.cursor/agents), invocable with
`/<name>`. The `/logiq-run` command in [`.cursor/commands/`](.cursor/commands) orchestrates
all three. Shared data contracts and run conventions live in the always-applied
[`.cursor/rules/logiq-pipeline.mdc`](.cursor/rules/logiq-pipeline.mdc).

## Project layout

```
.cursor/
  agents/       logiq-collect, logiq-research, logiq-synthesize (the 3 agents)
  rules/        logiq-pipeline.mdc (shared contracts + conventions, always applied)
  commands/     logiq-run (full orchestration)
logiq/          deterministic Python helpers (parsing, schemas, persistence)
data/
  input/        sample + your logs
  runs/<run_id> errors.json, research.json, resolution.json
requirements.txt
```

## Setup

```powershell
# from the project root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Glean MCP server

The Researcher agent uses the `glean_default` MCP server. This project relies on the
`glean_default` entry already configured in your global `~/.cursor/mcp.json`, so no
project-local `mcp.json` is needed. Ensure that server is enabled in Cursor (Cursor
handles OAuth on first use).

## Running the pipeline

### Full orchestration (recommended, in Cursor)

```
/logiq-run <app-name>
```

Example: `/logiq-run AcmeOrders`

Logs are read from the default `data/input/` folder, so no input path is needed. This runs
the Collector script, then the Researcher (web + Glean MCP), then the Synthesizer, writing
all three artifacts under `data/runs/<run_id>/`.

### Stage by stage (in Cursor, invoke each agent)

```
/logiq-collect <app-name> <input-path>
/logiq-research <run-id>
/logiq-synthesize <run-id>
```

### Deterministic Collector only (plain Python, no LLM)

```powershell
# --input is optional; defaults to the data/input/ folder
# Collects ERROR, EXCEPTION, CRITICAL, and FATAL only (WARNING/info excluded by default)
python -m logiq.orchestrate --app-name AcmeOrders
# explicit path or override level filter:
python -m logiq.orchestrate --app-name AcmeOrders --input data/input/sample.log --levels ERROR WARNING
```

This prints the generated `run_id` and writes `data/runs/<run_id>/errors.json`.

## Output

`data/runs/<run_id>/resolution.json` is the final output: one entry per distinct error
pattern with error summary, root cause, resolution steps, and references (web / Glean /
BMC Helix). Duplicate log lines are collapsed automatically.

Only the latest run is kept on disk — each new Collector run clears `data/runs/` before writing.
