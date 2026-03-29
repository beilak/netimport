# NetImport Production Readiness Audit

## What This Project Is

`NetImport` is a Python CLI tool that statically analyzes Python projects by
parsing `import` statements, building a dependency graph, and visualizing or
summarizing the result.

This file now tracks only open production-readiness blockers. Items that were
verified as solved during the audit were removed from this document.

Audit re-verified on 2026-03-29.

## Current State

Core CLI/config/summary behavior is in much better shape than in the original
audit:

- project-local config loading works
- `.netimport.toml` support works
- release gates are green for the maintained scope
- non-project dependency folders are categorized consistently
- summary output exists in text and JSON forms
- `python -m netimport_lib.cli` works
- demo code is excluded from strict release gates
- CLI/backend/layout contracts are now explicit and tested
- default interactive Bokeh launch now degrades gracefully when auto-open is unavailable

At the time of this re-verification, no open production-readiness blockers from
the original audit remain.

## Checks Run

The following checks were re-run during this audit:

- `poetry run pytest tests`
- `poetry run mypy netimport_lib tests`
- `poetry run ruff check netimport_lib tests`
- `poetry run netimport --help`
- `poetry run python -m netimport_lib.cli --help`
- `poetry run netimport example --show-console-summary --no-show-graph`
- `poetry run netimport example --show-console-summary --summary-format json --no-show-graph`
- `poetry run netimport example`

Observed results:

- `pytest` passes: `70 passed`
- `mypy netimport_lib tests` passes
- `ruff check netimport_lib tests` passes
- CLI help works
- module execution help works
- summary-only text output works
- summary-only JSON output works
- default interactive Bokeh launch exits with code `0` and prints a controlled
  manual-open message instead of emitting macOS `osascript` noise

## Open Problems

None at the moment.
