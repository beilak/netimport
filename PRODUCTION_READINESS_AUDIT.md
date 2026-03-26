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

These examples are useful for manual testing. They are now treated as demos/fixtures and are excluded from strict release gates so they do not blur product readiness signals.

## Current State Summary

The core idea is implemented and the basic graph-building flow exists:

1. Find Python files.
2. Parse imports from files using AST.
3. Resolve imports to project files / stdlib / external libs.
4. Build a `networkx.DiGraph`.
5. Try to visualize or print a summary.

What is missing is the product layer around that core:

- some config-loading gaps have been closed, but overall product hardening is still incomplete
- some documentation still needs follow-up, but core CLI usage and supported visualizer modes are now documented
- quality gates are now green, including strict typing for product code
- test coverage for product behavior is much better, including stronger visualizer/headless coverage

Practical assessment: this has moved from a loose alpha/prototype toward a much more disciplined developer tool, with most original production-hardening gaps now addressed.

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

- `pytest` now passes: `46 passed`
- `mypy .` now passes in strict mode
- `ruff check .` now passes
- CLI help works
- `netimport example` exits successfully
- `netimport example --show-console-summary` now prints a deterministic console report
- `netimport example --show-console-summary --summary-format json --no-show-graph` now prints a deterministic JSON report
- `python -m netimport_lib.cli --help` now works

## Problems

## DONE. P1. CLI loads config from the target project

### Status

Implemented in `netimport_lib/cli.py` and covered by CLI tests.

### Done

1. Normalized `project_path` early in CLI.
2. Switched config loading from caller cwd to the analyzed project root.
3. Documented precedence between defaults, `pyproject.toml`, `.netimport.toml`, and CLI options.
4. Added a CLI integration test that runs analysis from a different working directory than the target project.

### Acceptance criteria

- `netimport /tmp/target-project` uses `/tmp/target-project` config, not caller cwd config.
- Tests cover this exact scenario.

## DONE. P1. `.netimport.toml` support is implemented

### Status

Implemented in `netimport_lib/config_loader.py` and documented in `README.md`.

### Done

1. Added support for `.netimport.toml`.
2. Defined precedence explicitly:
   - defaults
   - `[tool.netimport]` in `pyproject.toml`
   - `.netimport.toml`
   - CLI options
3. Added tests for:
   - no `[tool.netimport]` section
   - both config files present
4. Updated README to match the actual behavior.

### Acceptance criteria

- `.netimport.toml` is read correctly.
- Conflicts are resolved according to documented precedence.
- README matches behavior exactly.

## DONE. P1. `ignored_files` from config is used by CLI

### Status

Implemented in `netimport_lib/cli.py` and covered by CLI tests.

### Done

1. Passed `loaded_config["ignored_files"]` into file discovery.
2. Added CLI override support for ignored files.
3. Added tests verifying that configured ignored files are excluded from analysis.

### Acceptance criteria

- a file listed in config is excluded from analysis.
- tests verify that exclusion.

## DONE. P1. Summary output is implemented

### Status

Implemented in `netimport_lib/summary_builder.py` and covered by tests.

### Done

1. Added deterministic console summary output.
2. Added numeric tables for:
   - graph overview
   - project coupling metrics
   - most/least coupled project files
   - most depended-on project files
   - most dependent project files
   - external dependencies
   - unresolved imports
3. Added tests for formatter output.
4. Added CLI tests for summary output.
5. Added `--no-show-graph` so summary can be used without opening visualization.

### Acceptance criteria

- `poetry run netimport example --show-console-summary` prints a meaningful report
- output is deterministic
- tests assert exact lines for formatter and CLI output

## DONE. P2. JSON summary output is available for automation

### Status

Implemented in `netimport_lib/summary_builder.py`, `netimport_lib/cli.py`,
`tests/test_summary_builder.py`, `tests/test_cli.py`, and documented in
`README.md`.

### Done

1. Added a structured summary payload builder for machine-readable output.
2. Added deterministic JSON serialization for the summary report.
3. Added CLI support via `--summary-format json` alongside the existing
   `--show-console-summary` flow.
4. Preserved the existing text summary contract as the default behavior.
5. Added unit and CLI tests for JSON summary output.
6. Documented the JSON summary mode for CI and automation use cases.

### Acceptance criteria

- `netimport <project> --show-console-summary --summary-format json --no-show-graph`
  prints valid deterministic JSON
- existing text summary behavior remains unchanged
- tests cover both formatter-level and CLI-level JSON output

## DONE. P1. README and actual CLI contract are aligned

### Status

`README.md` has been updated to reflect the current CLI.

### Done

1. Removed undocumented options from README usage examples.
2. Documented actual supported CLI options:
   - `--layout`
   - `--show-graph`
   - `--no-show-graph`
   - `--show-console-summary`
3. Added real launch examples.
4. Added a real example of console summary output.
5. Updated configuration docs to match the current implementation contract.

### Acceptance criteria

- `README.md` and `netimport --help` describe the same interface for current supported options
- examples reflect the real command behavior

## DONE. P1. Quality gates are not green

### Status

Implemented in `pyproject.toml`, `.github/workflows/ci.yml`, `netimport_lib/`,
`tests/`, and local stub files under `stubs/`.

### Done

1. Made `mypy` pass in strict mode for product code.
2. Added local typing stubs for dependencies that do not provide enough type information for strict checking.
3. Tightened `ruff` configuration and cleaned product code to pass strict linting.
4. Refactored several modules to reduce complexity instead of hiding warnings.
5. Excluded `example/` and `big_example/` from strict release gates and made that policy explicit in config.
6. Aligned CI with the intended product-quality scope.
7. Verified:
   - `poetry run mypy .`
   - `poetry run ruff check .`
   - `poetry run pytest`
   all pass.

### Why it matters

The repository has CI for `ruff`, `mypy`, and `pytest`. A production-ready tool needs these gates green and trustworthy.

### Where

- `.github/workflows/ci.yml`
- `pyproject.toml`
- multiple implementation files

### Evidence from audit

Initial audit state:

- `poetry run mypy .` reported 31 errors
- `poetry run ruff check .` reported 16 issues

Current verified state:

- `poetry run mypy .` passes
- `poetry run ruff check .` passes
- `poetry run pytest` passes

### Consequence

- CI quality gates are now trustworthy again for the maintained product scope
- strict typing now protects graph, config, CLI, and visualizer boundaries more effectively

### Suggested implementation

Implemented.

### Acceptance criteria

- `poetry run mypy .` passes
- `poetry run ruff check .` passes
- CI passes without manual caveats

## DONE. P2. Test suite is too shallow

### Status

Implemented. Core CLI/config/summary coverage exists, resolver edge-case
coverage has been added, and visualizer/headless coverage is now covered in:

- `tests/test_resolver_imports.py`
- `tests/test_graph_builder.py`
- `tests/test_imports_reader.py`
- `tests/test_bokeh_plotter.py`
- `tests/test_mpl_plotter.py`

### Why it matters

Current green tests do not prove product correctness.

### Where

- `tests/`
- `example/tests/`

### Evidence

Current tests no longer only cover happy-path parsing and graph creation.

Coverage added since the original audit:

- CLI behavior
- config precedence
- `.netimport.toml`
- ignored files behavior
- summary output
- unresolved imports
- stdlib vs external import classification
- relative import edge cases
- type-checking import filtering
- visualizer render-preparation behavior
- headless visualizer smoke coverage
- supported layout coverage for each registered MPL backend layout
- empty-graph Bokeh coverage
- non-planar `planar_layout` contract coverage
- non-mutation checks for visualizer draw paths

At audit time, demo tests were weak:

- `example/tests/test_account.py::test_print()` is empty
- some asserts only instantiate dataclasses without validating behavior

### Consequence

- false confidence from green CI
- regressions in product-facing behavior will go unnoticed

### Suggested implementation

Implemented in layers:

1. DONE. Unit tests for config loading.
2. DONE. Unit tests for import resolution edge cases.
3. DONE. Snapshot-like tests for summary output.
4. DONE. CLI integration tests using `click.testing.CliRunner`.
5. DONE. Optional smoke tests for visualizer adapters.

### Acceptance criteria

- CLI and config behavior are covered by tests
- summary and resolver edge cases are covered
- shallow/no-op demo tests are removed or improved

## DONE. P2. Visualizer contract is consistent

### Status

Implemented in `netimport_lib/visualizer/__init__.py`, `netimport_lib/visualizer/mpl_plotter.py`, `netimport_lib/visualizer/bokeh_plotter_v2.py`, `netimport_lib/cli.py`, and documented in `README.md`.

### Done

1. Introduced a central visualizer registry with explicit supported backends and layout lists.
2. Restricted the public CLI contract to actually supported backends:
   - `bokeh`
   - `mpl`
3. Restricted the public CLI contract to actually supported layouts:
   - `bokeh`: `constrained`
   - `mpl`: `spring`, `circular`, `shell`, `planar_layout`
4. Removed unsupported Graphviz-like layouts from the CLI contract.
5. Made CLI layout resolution backend-aware, including backend-specific default layouts.
6. Rejected unsupported backend/layout combinations with a clear CLI error instead of silently falling back.
7. Made Bokeh use an explicit supported layout contract instead of ignoring the `layout` argument.
8. Removed the hidden Plotly backend code path and dropped the unused `plotly` dependency so the shipped package matches the public backend contract.
9. Added CLI and registry tests covering:
   - backend defaults
   - supported combinations
   - rejected combinations
   - `--help` output
10. Updated `README.md` with the actual supported visualization modes and launch examples.

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
- At audit time, `plotly_plotter.py` existed but was not exposed in `GRAPH_VISUALIZERS`.

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

## DONE. P2. `python -m netimport_lib.cli` is a no-op

### Status

Implemented in `netimport_lib/cli.py` and verified manually.

### Done

1. Added `if __name__ == "__main__": main()`.
2. Verified `poetry run python -m netimport_lib.cli --help` works.

### Why it matters

Package entry point `netimport` works, but module execution does nothing because there is no `if __name__ == "__main__": main()`.

### Where

- `netimport_lib/cli.py`

### Consequence

- module execution is now supported explicitly
- developer behavior matches user expectations better

### Suggested implementation

Implemented.

### Acceptance criteria

- either module execution works, or docs clearly say only `netimport` entry point is supported

## DONE. P2. Complex functions need decomposition

### Status

Implemented in `netimport_lib/graph_builder/graph_builder.py`,
`netimport_lib/graph_builder/resolver_imports.py`, and
`netimport_lib/visualizer/bokeh_plotter_v2.py`.

### Done

1. Kept resolver logic split across focused helpers for:
   - relative import resolution
   - absolute import resolution
   - stdlib/external classification
2. Kept graph building split across:
   - source normalization
   - project-node creation
   - target-node/edge insertion
   - metadata enrichment
3. Decomposed the Bokeh visualizer into smaller steps for:
   - constrained layout generation
   - folder overlays
   - node/edge renderer configuration
   - hover and arrow setup
   - drag support
4. Verified the refactored code still passes strict typing, linting, and tests.

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

Implemented.

### Acceptance criteria

- complexity warnings are gone or reduced to an acceptable level
- behavior is preserved by tests

## DONE. P2. Demo code leaks into quality story

### Status

Implemented in `pyproject.toml` and `.github/workflows/ci.yml`.

### Done

1. Chose an explicit policy: `example/` and `big_example/` are demos/fixtures, not release-gated production code.
2. Excluded demo folders from strict `mypy` and `ruff` quality gates.
3. Scoped `pytest` to the maintained product test suite under `tests/`.
4. Aligned CI commands with that same maintenance intent.

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

Implemented with strategy 2:

1. Treat demos as fixtures.
2. Exclude them from strict gates.
3. Keep the release-quality signal focused on maintained product code.

### Acceptance criteria

- repo quality gates reflect actual maintenance intent for demo folders

## DONE. P3. Product positioning and metadata no longer say "alpha"

### Status

Implemented in `pyproject.toml`, `README.md`, `example/tests/test_account.py`,
and `example/tests/test_user.py`.

### Done

1. Updated packaging metadata from alpha to beta to match the current product maturity.
2. Tightened the package description so it describes the shipped CLI behavior directly.
3. Rewrote the README introduction and support contract so it reads like a maintained tool instead of a draft.
4. Added an explicit `Current Limitations` section documenting the supported static-analysis boundaries.
5. Cleaned the README license section so it matches the repository contents.
6. Replaced weak demo tests with small behavior assertions for the example domain models.

### Why it matters

Metadata and documentation should communicate the real maturity of the tool.

### Where

- `pyproject.toml`
- `README.md`

### Evidence

- `pyproject.toml` now uses `Development Status :: 4 - Beta`
- README documents current support boundaries and limitations explicitly

### Suggested implementation

Implemented.

### Acceptance criteria

- docs read like a finished tool, not a draft
- packaging metadata matches real maturity

## Missing Pieces Before Production Ready

This section is the implementation backlog for another LLM or engineer.

## Workstream 1. Make the CLI honest and reliable

### Tasks

1. DONE. Normalize and validate `project_path` at CLI entry.
2. DONE. Load config from target project.
3. DONE. Add `.netimport.toml` support.
4. DONE. Apply `ignored_files`.
5. DONE. Add `--config` support and document explicit config precedence.
6. Decide whether `--show-console-summary` should default to `False` instead of `True`.
7. DONE. Add `__main__` support.

### Files likely to change

- `netimport_lib/cli.py`
- `netimport_lib/config_loader.py`
- `README.md`
- tests to be added under `tests/`

### Notes for implementer

- Keep precedence deterministic and documented.
- Prefer small pure functions in config loading so tests stay simple.
- Use `click.testing.CliRunner` for CLI tests.

### Progress update

Implemented in:

- `netimport_lib/config_loader.py`
- `netimport_lib/cli.py`
- `tests/test_config_loader.py`
- `tests/test_cli.py`
- `README.md`

Done:

1. Added `--config` support for explicit TOML files.
2. Allowed explicit config files to use either top-level NetImport keys or a `[tool.netimport]` section.
3. Defined and documented precedence explicitly:
   - defaults
   - `pyproject.toml`
   - `.netimport.toml`
   - explicit `--config`
   - CLI options
4. Added tests covering:
   - explicit config overriding project config
   - CLI flags overriding explicit config
   - explicit config validation errors

Acceptance criteria:

- `netimport <project> --config <file>` loads and applies explicit config deterministically
- README matches the implemented precedence and file shapes
- tests cover the main precedence and validation paths

## DONE. Workstream 2. Implement useful non-GUI output

### Status

Implemented in:

- `netimport_lib/summary_builder.py`
- `netimport_lib/cli.py`
- `tests/test_summary_builder.py`
- `tests/test_cli.py`
- `README.md`

### Done

1. Finished `summary_builder.py`.
2. Kept unresolved imports visible in the summary output.
3. Added deterministic sorting for printed and structured summary sections.
4. Added integration tests for CLI summary output.
5. Added deterministic JSON summary output for CI and automation.

### Tasks

1. DONE. Finish `summary_builder.py`.
2. DONE. Decide whether unresolved imports should appear in graph and summary.
3. DONE. Add deterministic sorting for all printed sections.
4. DONE. Add integration tests for CLI summary.
5. DONE. Add JSON output for CI and automation.

### Files likely to change

- `netimport_lib/summary_builder.py`
- `netimport_lib/cli.py`
- new tests

### Notes for implementer

- Text output should be stable across runs.
- Avoid output that depends on dict insertion order.
- JSON output may be more useful than text for automation.

## DONE. Workstream 3. Stabilize import resolution

### Status

Implemented in:

- `netimport_lib/imports_reader.py`
- `netimport_lib/graph_builder/resolver_imports.py`
- `netimport_lib/graph_builder/graph_builder.py`
- `tests/test_resolver_imports.py`
- `tests/test_graph_builder.py`
- `tests/test_imports_reader.py`

### Done

1. Added tests for absolute imports, relative imports, package imports, star imports, unresolved imports, and type-checking imports.
2. Reworked resolver behavior for:
   - `from . import *`
   - `from .. import x`
   - unresolved relative imports
   - package `__init__.py`
3. Cleaned up return types and mypy issues in the import-resolution path.
4. Normalized source file ids in graph building and added integration coverage for that contract.
5. Decided that namespace packages are not explicitly supported in the current resolver contract; unsupported cases should remain explicit rather than guessed.

### Tasks

1. DONE. Add tests for absolute imports, relative imports, package imports, star imports, unresolved imports, and type-checking imports.
2. DONE. Revisit the resolver behavior for:
   - `from . import *`
   - `from .. import x`
   - unresolved relative imports
   - package `__init__.py`
3. DONE. Clean up return types and mypy issues.
4. DONE. Decide how much namespace package support is expected.

### Files likely to change

- `netimport_lib/imports_reader.py`
- `netimport_lib/graph_builder/resolver_imports.py`
- `netimport_lib/graph_builder/graph_builder.py`
- new tests

### Notes for implementer

- Preserve deterministic outputs.
- Be explicit about known unsupported cases instead of silently guessing.

## DONE. Workstream 4. Fix visualizer boundaries

### Status

Implemented. Supported backends/layouts are explicit, unsupported combinations
fail clearly, the hidden Plotly backend path has been removed from both the
shipped code and package dependencies, and graph preparation is now separated
from side-effectful rendering.

### Tasks

1. DONE. Decide supported backends: `bokeh`, `mpl`, maybe `plotly`.
2. DONE. Decide supported layouts per backend.
3. DONE. Remove or implement dead/hidden code paths.
4. DONE. Make unsupported layout/backend combinations fail clearly.
5. DONE. Separate graph generation from side-effectful rendering.

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

### Status

Implemented in:

- `pyproject.toml`
- `.github/workflows/ci.yml`
- `stubs/`
- multiple files under `netimport_lib/`
- multiple files under `tests/`

### Tasks

1. DONE. Make `mypy` pass.
2. DONE. Make `ruff check .` pass.
3. DONE. Reduce complexity by refactoring, not by hiding warnings everywhere.
4. DONE. Decide policy for demo folders in lint/type checks.
5. DONE. Keep CI aligned with local developer commands.

### Files likely to change

- implementation files across `netimport_lib/`
- `pyproject.toml`
- `.github/workflows/ci.yml` if needed

### Notes for implementer

- Do not weaken checks blindly.
- If a rule is too strict for the project, document why before relaxing it.

## DONE. Workstream 6. Expand tests to real product behavior

### Status

Implemented. Core product behavior is covered for config loading, CLI behavior,
summary output, resolver edge cases, strict typing, and visualizer behavior in
headless environments. Weak demo tests have been reviewed and replaced with
small behavior assertions.

### Tasks

1. DONE. Add config loader tests.
2. DONE. Add CLI integration tests.
3. DONE. Add summary tests.
4. DONE. Add resolver edge-case tests.
5. DONE. Add visualizer behavior tests for headless environments.
6. DONE. Review or remove weak demo tests.

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
8. Add optional production features such as DOT/Mermaid export and CI-oriented failure modes.

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

1. DOT and Mermaid export.
2. Architecture metrics:
   - afferent coupling
   - efferent coupling
   - instability
3. Layer/rule validation.
4. Exit codes that fail CI based on violations.
5. HTML report output.
6. Performance profiling on large repos.

## Final Assessment

NetImport already contains a usable core for parsing imports and building a dependency graph. The main gap is not "idea feasibility", but product hardening:

- trustworthy config behavior
- honest CLI/docs contract
- meaningful headless output
- green quality gates
- real coverage of user-facing scenarios

Most of those hardening items are now fixed. The project has materially improved:

- quality gates are green
- strict typing is in place for maintained product code
- CLI module execution works
- the demo-folder policy is explicit
- product-facing tests are significantly stronger

Product-positioning gaps from the original audit have now been addressed:

- metadata no longer says alpha
- README reads like a maintained beta-stage tool and documents its boundaries
- docs can still be tightened further
- visualizer/headless coverage is now part of the maintained product test story

This is no longer just a rough prototype. It is a much more disciplined tool
that is approaching production readiness, with a smaller and clearer remaining
backlog.
