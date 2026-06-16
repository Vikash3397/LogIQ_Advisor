# /logiq-run

Run the full LogIQ Advisor orchestration end-to-end by delegating to the three agents in
`.cursor/agents/` (Collector -> Researcher -> Synthesizer).

Usage: `/logiq-run <app-name>`

The logs are read from the default `data/input/` folder, so no input path is needed.

Follow the `logiq-pipeline` rule for data contracts and run conventions. Carry the same
`run_id` through all three stages.

## Stage 1 - Collect
Hand off to the `logiq-collect` agent with the given `<app-name>`. It runs
`python -m logiq.orchestrate --app-name <app-name>` (input defaults to `data/input/`),
clears any prior artifacts under `data/runs/`, writes `data/runs/<run_id>/errors.json`,
and returns the `run_id` and error count.

## Stage 2 - Research
Hand off to the `logiq-research` agent with the `run_id`. It researches each error via
public web + the Glean MCP server `glean_default` (incl. BMC Helix ITSM) and writes
`data/runs/<run_id>/research.json`. Read-only investigation; no system modifications.

## Stage 3 - Synthesize
Hand off to the `logiq-synthesize` agent with the `run_id`. It consolidates `errors.json`
+ `research.json` into `data/runs/<run_id>/resolution.json` (one summary per distinct error)
and also writes a human-readable `data/runs/<run_id>/resolution.txt` report alongside it.
No web/Glean/DB calls.

## Final report
Print the `run_id`, the artifact paths under `data/runs/<run_id>/` (`errors.json`,
`research.json`, `resolution.json`, and `resolution.txt`), and a concise per-distinct-error
summary from `resolution.json`: error -> root cause -> top resolution step.
