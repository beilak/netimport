# NetImport Production Readiness Audit

## What This Project Is

`NetImport` is a Python CLI tool that statically analyzes Python projects by parsing `import` statements, building a dependency graph, and visualizing the result.

Current implementation lives mainly in:

- `netimport_lib/cli.py`
- `netimport_lib/project_file_reader.py`
- `netimport_lib/imports_reader.py`
- `netimport_lib/config_loader.py`
- `netimport_lib/graph_builder/graph_builder.py`
- `netimport_lib/graph_builder/resolver_imports.py`
- `netimport_lib/summary_builder.py`
- `netimport_lib/visualizer/`

The repository also contains demo projects:

- `example/`
- `big_example/`

These examples are useful for manual testing, but they currently blur the line between library code and demo code in CI and quality checks.

## Current State Summary

The core idea is implemented and the basic graph-building flow exists:

1. Find Python files.
2. Parse imports from files using AST.
3. Resolve imports to project files / stdlib / external libs.
4. Build a `networkx.DiGraph`.
5. Try to visualize or print a summary.

What is missing is the product layer around that core:

- config behavior is not trustworthy yet
- CLI contract does not match README
- summary output is effectively not implemented
- type checks and lints are not green
- test coverage is too shallow for a production CLI tool
- visualizer behavior is only partially aligned with CLI options

Practical assessment: this is a useful alpha/prototype, not yet a production-ready tool.

## Checks Already Run

The following checks were run during audit:

- `poetry install`
- `poetry run pytest`
- `poetry run mypy .`
- `poetry run ruff check .`
- `poetry run netimport --help`
- `poetry run netimport example`
- `poetry run netimport example --show-console-summary`

Observed results:

- `pytest` passed: `6 passed`
- `mypy` failed with 31 errors
- `ruff` failed with 16 findings
- CLI help works
- `netimport example` exits successfully
- `netimport example --show-console-summary` exits successfully but prints nothing

## Problems

### P1. CLI loads config from the wrong place

### Why it matters

When a user runs `netimport /path/to/other/project`, the tool should use the analyzed project's config. Right now CLI loads config from the current working directory instead.

### Where

- `netimport_lib/cli.py`

### Evidence

`main()` calls:

```python
loaded_config: NetImportConfigMap = load_config(".")
```

This should likely be based on `project_path`, not `"."`.

### Consequence

- wrong directories/files may be ignored
- wrong stdlib/external settings may be applied
- analyzing another repo from outside that repo becomes misleading

### Suggested implementation

1. Load config from the analyzed project root.
2. Normalize `project_path` early.
3. Decide and document precedence rules clearly:
   - CLI arguments
   - `.netimport.toml`
   - `[tool.netimport]` in `pyproject.toml`
   - defaults
4. Add tests that run analysis from a different working directory than the target project.

### Acceptance criteria

- `netimport /tmp/target-project` uses `/tmp/target-project` config, not caller cwd config.
- Tests cover this exact scenario.

## P1. `.netimport.toml` is promised but not supported

### Why it matters

README promises both `.netimport.toml` and `pyproject.toml`, but loader only checks `pyproject.toml`.

### Where

- `README.md`
- `netimport_lib/config_loader.py`

### Evidence

`load_config()` only checks:

- `pyproject.toml`

It ignores:

- `.netimport.toml`

### Consequence

- documentation is incorrect
- users can create a valid-looking config file that has zero effect

### Suggested implementation

1. Add support for `.netimport.toml`.
2. Define precedence explicitly.
3. Add tests for:
   - only `.netimport.toml`
   - only `pyproject.toml`
   - both present
   - malformed config

### Acceptance criteria

- `.netimport.toml` is read correctly.
- Conflicts are resolved according to documented precedence.
- README matches behavior exactly.

## P1. `ignored_files` from config is not used by CLI

### Why it matters

Config model supports `ignored_files`, but CLI passes an empty set to file discovery.

### Where

- `netimport_lib/cli.py`
- `netimport_lib/config_loader.py`
- `netimport_lib/project_file_reader.py`

### Evidence

CLI currently calls:

```python
find_python_files(
    project_path,
    ignored_dirs=loaded_config["ignored_dirs"],
    ignored_files=set(),
)
```

### Consequence

- users cannot actually exclude configured files
- behavior disagrees with config model and README

### Suggested implementation

1. Pass `loaded_config["ignored_files"]`.
2. Add CLI override support if desired.
3. Add tests for ignored file behavior.

### Acceptance criteria

- a file listed in config is excluded from analysis
- tests verify that exclusion

## P1. Summary output is not implemented

### Why it matters

The CLI exposes `--show-console-summary`, but users currently get no useful report.

### Where

- `netimport_lib/summary_builder.py`

### Evidence

Several functions are placeholders:

- `print_header()`
- `print_external_dependencies()` loop body
- "top 10" functions compute values but do not print them
- link statistics function computes degrees but outputs nothing

### Consequence

- one of the main non-GUI use cases is effectively broken
- CI/headless environments get no value from summary mode

### Suggested implementation

Implement a stable textual summary format, for example:

1. Header with project stats:
   - total nodes
   - project files
   - stdlib nodes
   - external libs
   - edges
2. Top incoming links
3. Top outgoing links
4. External dependencies list
5. Unresolved imports list

Use deterministic sorting so output is testable.

### Acceptance criteria

- `poetry run netimport example --show-console-summary` prints a meaningful report
- output is deterministic
- tests assert exact or near-exact lines

## P1. README and actual CLI contract do not match

### Why it matters

Users trust `README.md` as the product contract.

### Where

- `README.md`
- `netimport_lib/cli.py`

### Evidence

README documents options that do not exist:

- `--output-graph`
- `--config`
- `--ignored-dirs`
- `--ignored-files`
- `--export-dot`
- `--export-mermaid`

Actual CLI help currently exposes:

- `--layout`
- `--show-graph`
- `--show-console-summary`

### Consequence

- first-run user experience is broken
- generated support burden increases
- it becomes unclear what the intended roadmap vs current feature set is

### Suggested implementation

Choose one of two paths:

1. Minimal honesty path:
   - remove undocumented/unimplemented options from README
   - document only current behavior
2. Product path:
   - implement the promised options
   - add tests and examples

Recommendation: take the product path if production readiness is the goal.

### Acceptance criteria

- `README.md` and `netimport --help` describe the same interface
- every documented option has implementation and tests

## P1. Quality gates are not green

### Why it matters

The repository has CI for `ruff`, `mypy`, and `pytest`. A production-ready tool needs these gates green and trustworthy.

### Where

- `.github/workflows/ci.yml`
- `pyproject.toml`
- multiple implementation files

### Evidence from audit

`poetry run mypy .` reported 31 errors, including:

- `netimport_lib/imports_reader.py`
- `netimport_lib/config_loader.py`
- `netimport_lib/graph_builder/resolver_imports.py`
- `netimport_lib/visualizer/bokeh_plotter_v2.py`

`poetry run ruff check .` reported 16 issues, including:

- complexity warnings in graph building / resolver / visualizer code
- broad exception swallowing
- unused arguments
- commented-out code in demo files

### Consequence

- CI will fail or cannot be trusted as a release gate
- type regressions can slip into graph and visualizer logic

### Suggested implementation

1. Fix genuine code issues first.
2. Revisit `mypy` configuration for third-party stubs if needed.
3. Reduce complexity in large functions instead of silencing rules blindly.
4. Decide whether demo folders belong in the strict quality path.

### Acceptance criteria

- `poetry run mypy .` passes
- `poetry run ruff check .` passes
- CI passes without manual caveats

## P2. Test suite is too shallow

### Why it matters

Current green tests do not prove product correctness.

### Where

- `tests/`
- `example/tests/`

### Evidence

Current tests mostly cover happy-path parsing and graph creation.

Missing tests include:

- CLI behavior
- config precedence
- `.netimport.toml`
- ignored files behavior
- summary output
- unresolved imports
- stdlib vs external import classification
- relative import edge cases
- visualizer behavior
- headless environments

Also, demo tests are weak:

- `example/tests/test_account.py::test_print()` is empty
- some asserts only instantiate dataclasses without validating behavior

### Consequence

- false confidence from green CI
- regressions in product-facing behavior will go unnoticed

### Suggested implementation

Add tests in layers:

1. Unit tests for config loading.
2. Unit tests for import resolution edge cases.
3. Snapshot-like tests for summary output.
4. CLI integration tests using `click.testing.CliRunner`.
5. Optional smoke tests for visualizer adapters.

### Acceptance criteria

- CLI and config behavior are covered by tests
- summary and resolver edge cases are covered
- shallow/no-op demo tests are removed or improved

## P2. Visualizer contract is inconsistent

### Why it matters

Users choose layouts and visualization mode from CLI. Those options should behave predictably.

### Where

- `netimport_lib/visualizer/mpl_plotter.py`
- `netimport_lib/visualizer/bokeh_plotter_v2.py`
- `netimport_lib/visualizer/__init__.py`
- `netimport_lib/cli.py`

### Evidence

- Bokeh visualizer ignores the `layout` argument entirely.
- CLI offers graphviz-like layout names (`dot`, `neato`, `fdp`, `sfdp`), but MPL path does not implement those layouts and silently falls back to `spring_layout`.
- `plotly_plotter.py` exists but is not exposed in `GRAPH_VISUALIZERS`.

### Consequence

- user-selected options may do nothing
- behavior is surprising and hard to debug

### Suggested implementation

1. Decide supported visualization backends.
2. Decide supported layout engines per backend.
3. Reject unsupported combinations explicitly instead of silently ignoring them.
4. If Graphviz layouts are intended, implement them properly and document dependencies.
5. If Plotly is intended, either expose it or remove it.

### Acceptance criteria

- each CLI layout option is either supported or rejected with a clear message
- visualizer backend list matches actual implementation

## P2. `python -m netimport_lib.cli` is a no-op

### Why it matters

Package entry point `netimport` works, but module execution does nothing because there is no `if __name__ == "__main__": main()`.

### Where

- `netimport_lib/cli.py`

### Consequence

- not a blocker for packaged entry point
- but confusing for developers and tests

### Suggested implementation

Add:

```python
if __name__ == "__main__":
    main()
```

Only do this if module execution is intended to be supported.

### Acceptance criteria

- either module execution works, or docs clearly say only `netimport` entry point is supported

## P2. Complex functions need decomposition

### Why it matters

The graph builder, resolver, and Bokeh visualizer have high complexity and are getting hard to maintain.

### Where

- `netimport_lib/graph_builder/graph_builder.py`
- `netimport_lib/graph_builder/resolver_imports.py`
- `netimport_lib/visualizer/bokeh_plotter_v2.py`

### Consequence

- change risk is high
- future feature work will be slower and more error-prone

### Suggested implementation

Refactor into smaller units, for example:

- resolver: split relative import resolution, absolute import resolution, stdlib/external classification
- graph builder: split node initialization, edge insertion, node metadata enrichment
- Bokeh plotter: split layout generation, node styling, edge styling, hover config

### Acceptance criteria

- complexity warnings are gone or reduced to an acceptable level
- behavior is preserved by tests

## P2. Demo code leaks into quality story

### Why it matters

`example/` and `big_example/` are demos, but they currently contribute lint/type noise and muddy release readiness.

### Where

- `example/`
- `big_example/`
- `pyproject.toml`

### Evidence

Ruff findings include demo files such as:

- `big_example/main.py`
- `big_example/utils.py`
- `big_example/complex_logic/data_processor.py`

### Suggested implementation

Choose one strategy:

1. Treat demos as production-quality examples:
   - lint/type/test them fully
2. Treat demos as fixtures:
   - exclude them from strict gates
   - keep them simple and intentionally non-production

Recommendation: decide explicitly and encode the choice in config.

### Acceptance criteria

- repo quality gates reflect actual maintenance intent for demo folders

## P3. Product positioning and metadata still say "alpha"

### Why it matters

Metadata and documentation still communicate an unfinished state.

### Where

- `pyproject.toml`
- `README.md`

### Evidence

- classifier includes `Development Status :: 3 - Alpha`
- README contains placeholder wording like `Default values. (Maybe. I'm still thinking.)`

### Suggested implementation

After functional gaps are closed:

1. update maturity classifier
2. clean README wording
3. make docs task-oriented and precise

### Acceptance criteria

- docs read like a finished tool, not a draft
- packaging metadata matches real maturity

## Missing Pieces Before Production Ready

This section is the implementation backlog for another LLM or engineer.

## Workstream 1. Make the CLI honest and reliable

### Tasks

1. Normalize and validate `project_path` at CLI entry.
2. Load config from target project.
3. Add `.netimport.toml` support.
4. Apply `ignored_files`.
5. Add `--config` support if the README contract should be preserved.
6. Decide whether `--show-console-summary` should default to `False` instead of `True`.
7. Add `__main__` support if desired.

### Files likely to change

- `netimport_lib/cli.py`
- `netimport_lib/config_loader.py`
- `README.md`
- tests to be added under `tests/`

### Notes for implementer

- Keep precedence deterministic and documented.
- Prefer small pure functions in config loading so tests stay simple.
- Use `click.testing.CliRunner` for CLI tests.

## Workstream 2. Implement useful non-GUI output

### Tasks

1. Finish `summary_builder.py`.
2. Decide whether unresolved imports should appear in graph and summary.
3. Add deterministic sorting for all printed sections.
4. Add integration tests for CLI summary.
5. If production CI use is a goal, strongly consider adding JSON output.

### Files likely to change

- `netimport_lib/summary_builder.py`
- `netimport_lib/cli.py`
- new tests

### Notes for implementer

- Text output should be stable across runs.
- Avoid output that depends on dict insertion order.
- JSON output may be more useful than text for automation.

## Workstream 3. Stabilize import resolution

### Tasks

1. Add tests for absolute imports, relative imports, package imports, star imports, unresolved imports, and type-checking imports.
2. Revisit the resolver behavior for:
   - `from . import *`
   - `from .. import x`
   - unresolved relative imports
   - package `__init__.py`
3. Clean up return types and mypy issues.
4. Decide how much namespace package support is expected.

### Files likely to change

- `netimport_lib/imports_reader.py`
- `netimport_lib/graph_builder/resolver_imports.py`
- new tests

### Notes for implementer

- Preserve deterministic outputs.
- Be explicit about known unsupported cases instead of silently guessing.

## Workstream 4. Fix visualizer boundaries

### Tasks

1. Decide supported backends: `bokeh`, `mpl`, maybe `plotly`.
2. Decide supported layouts per backend.
3. Remove or implement dead/hidden code paths.
4. Make unsupported layout/backend combinations fail clearly.
5. Consider separating graph generation from side-effectful rendering.

### Files likely to change

- `netimport_lib/visualizer/__init__.py`
- `netimport_lib/visualizer/mpl_plotter.py`
- `netimport_lib/visualizer/bokeh_plotter_v2.py`
- `netimport_lib/visualizer/plotly_plotter.py`
- `README.md`

### Notes for implementer

- For tests, prefer validating prepared renderer data rather than GUI side effects.
- Headless compatibility matters for CI.

## Workstream 5. Restore trust in quality gates

### Tasks

1. Make `mypy` pass.
2. Make `ruff check .` pass.
3. Reduce complexity by refactoring, not by hiding warnings everywhere.
4. Decide policy for demo folders in lint/type checks.
5. Keep CI aligned with local developer commands.

### Files likely to change

- implementation files across `netimport_lib/`
- `pyproject.toml`
- `.github/workflows/ci.yml` if needed

### Notes for implementer

- Do not weaken checks blindly.
- If a rule is too strict for the project, document why before relaxing it.

## Workstream 6. Expand tests to real product behavior

### Tasks

1. Add config loader tests.
2. Add CLI integration tests.
3. Add summary tests.
4. Add resolver edge-case tests.
5. Review or remove weak demo tests.

### Files likely to change

- `tests/`
- `example/tests/`

### Notes for implementer

- Focus first on behavior users depend on, not internal implementation detail.
- Snapshot testing can help for summary output if kept readable.

## Suggested Implementation Order

Recommended order for another LLM:

1. Fix config loading and config precedence.
2. Implement summary output and tests.
3. Align README with actual CLI or implement missing CLI options.
4. Clean up resolver typing and edge-case tests.
5. Refactor and type-fix visualizers.
6. Make `mypy` and `ruff` green.
7. Revisit demo-folder policy.
8. Add optional production features such as JSON/DOT/Mermaid export and CI-oriented failure modes.

This order reduces rework because config + summary + tests create the base contract first.

## Production Readiness Checklist

The project can be reconsidered as production-ready only when all of the following are true:

- `poetry run pytest` passes with meaningful coverage
- `poetry run mypy .` passes
- `poetry run ruff check .` passes
- README matches actual CLI exactly
- config precedence is documented and tested
- `.netimport.toml` support works if documented
- console summary is useful and tested
- visualizer options are explicit and deterministic
- unsupported behaviors are documented instead of silently ignored
- demo code policy is explicit
- release metadata no longer describes the tool as alpha unless that remains intentional

## Optional Product Enhancements After Stabilization

These are not the first blockers, but they would materially improve the tool:

1. JSON export for CI tooling.
2. DOT and Mermaid export.
3. Architecture metrics:
   - afferent coupling
   - efferent coupling
   - instability
4. Layer/rule validation.
5. Exit codes that fail CI based on violations.
6. HTML report output.
7. Performance profiling on large repos.

## Final Assessment

NetImport already contains a usable core for parsing imports and building a dependency graph. The main gap is not "idea feasibility", but product hardening:

- trustworthy config behavior
- honest CLI/docs contract
- meaningful headless output
- green quality gates
- real coverage of user-facing scenarios

Once those are fixed, the project can move from alpha prototype toward a dependable developer tool.
