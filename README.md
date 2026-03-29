# NetImport: Python Project Architecture Analyzer via Import Graphs

NetImport is a static analysis CLI for Python projects. It scans source files, parses `import` statements, resolves those imports into project, standard-library, external, or unresolved dependencies, and then presents the result as either a dependency graph or a deterministic console summary.

It is intended for architecture inspection, refactoring support, and CI-friendly dependency review. The current release is positioned as a beta-stage developer tool: the core workflows are implemented and tested, while known static-analysis limitations are documented explicitly.

## Quick Start

Install NetImport and run it against a project directory:

```bash
pip install netimport
netimport example --show-console-summary --no-show-graph
```

If you are working from this repository locally:

```bash
poetry install
poetry run netimport example --show-console-summary --no-show-graph
```

Remove `--no-show-graph` if you want to open the graph visualization instead of running in summary-only mode.

## Core Features

*   **Import Analysis:** Recursively scans the specified project directory for Python files and parses their `import` statements.
*   **Dependency Graph Construction:** Creates a directed graph where nodes represent project modules/packages, as well as external and standard libraries. Edges depict the imports between them.
*   **Graph Visualization:** Supports an interactive Bokeh view and a static Matplotlib view with explicit backend/layout compatibility.
*   **Console Summary:** Prints a deterministic text report with project-level counts and coupling tables.
*   **Configuration via CLI and TOML files:** Supports CLI overrides plus config from `[tool.netimport]` in `pyproject.toml`, `.netimport.toml`, or an explicit `--config` TOML file.
*   **Dependency Type Identification:** Distinguishes imports of internal project modules, Python standard libraries, and external third-party dependencies.

## Why Use NetImport?

*   **Understand Project Structure:** Gain a clear visual overview of how different parts of your application are interconnected. This is especially useful for new team members or when working with legacy code.
*   **Assess Coupling:** Identify modules that are highly dependent on each other. High coupling can make code harder to change, test, and reuse.
*   **Gauge Cohesion (Indirectly):** While directly calculating cohesion from imports alone is difficult, the graph can provide insights into how logically grouped functionalities are within a module by observing its dependencies.
*   **Aid Refactoring:** Use the graph as a map during refactoring to understand which parts of the system will be affected by changes.
*   **Architectural Oversight:** Helps in maintaining a clean and understandable architecture by making dependencies explicit.

## Current Support Contract

NetImport currently supports:

*   Static analysis of Python source trees based on AST-parsed `import` statements.
*   Deterministic console summaries for headless runs and CI-oriented inspection.
*   Explicit visualizer backend/layout combinations documented in the CLI and README.
*   Configuration from `[tool.netimport]` in `pyproject.toml`, `.netimport.toml`, explicit `--config` files, and CLI overrides.

## Installation

```bash
pip install netimport
```
or 
```bash
poetry add netimport
```

## Usage

NetImport can be used from the command line and is suitable for integration into CI/CD pipelines.

### Command Line Interface
```bash
netimport [OPTIONS] <PROJECT_PATH>
```


### Current CLI Options

`PROJECT_PATH`

Path to the root directory of the Python project to analyze.

`--layout [constrained|spring|circular|shell|planar_layout]`

Choose a layout name for the selected graph backend. If omitted, NetImport uses the backend default.

`--config FILE`

Load an explicit TOML config file and apply it after project config has been loaded from the analyzed project. The file may either contain top-level NetImport keys or a `[tool.netimport]` section.

`--show-graph [bokeh|mpl]`

Select the visualization backend. Current default is `bokeh`.

Supported backend/layout combinations:

- `bokeh`: `constrained` (default)
- `mpl`: `spring` (default), `circular`, `shell`, `planar_layout`

Unsupported combinations are rejected with a clear CLI error instead of silently falling back.

`--no-show-graph`

Disable graph visualization even if a graph backend is configured. This is useful for CI, terminals, or summary-only runs.

`--show-console-summary`

Print a textual dependency report with tables for:

- overall graph counts
- project coupling metrics
- most/least coupled project files
- most depended-on project files
- most dependent project files
- external dependencies
- unresolved imports

`--summary-format [text|json]`

Choose the output format for `--show-console-summary`.

`--fail-on-violation`

Exit with code `1` when configured policy violations are found. This is intended
for CI usage together with summary output.

- `text` keeps the current human-readable table output
- `json` emits a deterministic machine-readable report for CI and automation

`--ignored-dir TEXT`

Ignore a directory name during project file discovery. Can be passed multiple times.

`--ignored-file TEXT`

Ignore a file name during project file discovery. Can be passed multiple times.

`--ignored-node TEXT`

Ignore a graph node by label or id. Can be passed multiple times.

`--ignore-stdlib` / `--include-stdlib`

Override whether standard library modules should be excluded.

`--ignore-external-lib` / `--include-external-lib`

Override whether external libraries should be excluded.

### Examples

Below are the supported launch modes with a short explanation of what each mode is for.

Default interactive mode

Use this when you want the standard interactive graph view with folder grouping and node dragging.

```bash
poetry run netimport example
```

This is equivalent to `--show-graph bokeh --layout constrained`.

Explicit Bokeh mode

Use this when you want to call the default interactive mode explicitly in scripts, docs, or manual checks.

```bash
poetry run netimport example --show-graph bokeh --layout constrained
```

This opens the Bokeh visualizer with the `constrained` layout.

Matplotlib spring mode

Use this as the most universal static Matplotlib layout. It is the safest choice when you want a readable static graph for general-purpose inspection.

```bash
poetry run netimport example --show-graph mpl --layout spring
```

Matplotlib circular mode

Use this when you want a simple ring-like layout that is easy to scan on small or medium graphs.

```bash
poetry run netimport example --show-graph mpl --layout circular
```

Matplotlib shell mode

Use this when you want a layered visual structure with nodes arranged in shells.

```bash
poetry run netimport example --show-graph mpl --layout shell
```

Matplotlib planar mode

Use this only when a planar-style view is useful for the current graph. For dense or non-planar dependency graphs, this mode may be less practical than `spring`.

```bash
poetry run netimport example --show-graph mpl --layout planar_layout
```

Graph plus console summary

Use this when you want both the graph visualization and the textual dependency report in the same run.

```bash
poetry run netimport example --show-console-summary
```

Summary-only mode

Use this in CI, SSH sessions, terminals without GUI support, or when you only need the textual report.

```bash
poetry run netimport example --show-console-summary --no-show-graph
```

JSON summary mode

Use this in CI or scripts when you want a stable machine-readable dependency report.

```bash
poetry run netimport example --show-console-summary --summary-format json --no-show-graph
```

Explicit config file

Use this when you want to keep a reusable analysis profile outside the analyzed project root, or when CI should point NetImport at a dedicated config file.

```bash
poetry run netimport example --config ci/netimport.toml --show-console-summary --no-show-graph
```

Example summary output:

```text
(This report summarizes the project's import graph so a reader can spot hotspots, risky dependencies, isolated files, and missing links.)
(Incoming degree shows how many project files depend on a file; outgoing degree shows how many dependencies a file pulls in. Higher values usually mean higher impact or complexity.)

Dependency Graph Summary
========================
(High-level graph totals. Use this table to quickly size the project and see how much of the graph is project code, stdlib, external libraries, or unresolved imports.)
+--------------------------+-------+
| Metric                   | Value |
+--------------------------+-------+
| Nodes                    | 14    |
| Edges                    | 18    |
| Project files            | 11    |
| Standard library modules | 3     |
| External libraries       | 0     |
| Unresolved imports       | 0     |
+--------------------------+-------+

Project Coupling Metrics
========================
(Aggregate coupling across all project files. Avg and Median describe a typical file, while Min and Max highlight the spread and the biggest extremes.)
+------------------------+------+--------+-----+-----+
| Metric                 | Avg  | Median | Min | Max |
+------------------------+------+--------+-----+-----+
| Project files analyzed | 11   | -      | -   | -   |
| Incoming degree        | 0.91 | 1.00   | 0   | 3   |
| Outgoing degree        | 1.64 | 1.00   | 0   | 5   |
| Total degree           | 2.55 | 2.00   | 0   | 5   |
+------------------------+------+--------+-----+-----+
```


### Configuration

NetImport reads configuration from the analyzed project directory, not from the caller's current working directory.

Supported config files:

- `[tool.netimport]` in `pyproject.toml`
- `.netimport.toml`
- explicit TOML file passed via `--config`

Precedence:

1. built-in defaults
2. `pyproject.toml`
3. `.netimport.toml`
4. explicit `--config` file
5. CLI options

For collection options (`ignored_dirs`, `ignored_files`, `ignored_nodes`), later file-based config replaces earlier file-based values, and CLI values are added on top at the final step. For boolean options (`ignore_stdlib`, `ignore_external_lib`), later config sources replace earlier ones, and explicit CLI flags override file config values.

Supported keys:

- `ignored_dirs`
- `ignored_files`
- `ignore_stdlib`
- `ignore_external_lib`
- `ignored_nodes`
- `fail_on_unresolved_imports`
- `forbidden_external_libs`

`pyproject.toml` example:

```
[tool.netimport]
ignored_dirs = ["venv", ".venv", "tests", "docs", "__pycache__", "node_modules", "migrations"]
ignored_files = ["setup.py", "manage.py"]
ignore_stdlib = true
ignore_external_lib = true
ignored_nodes = []
fail_on_unresolved_imports = true
forbidden_external_libs = ["requests"]
```

`.netimport.toml` example:

```toml
ignored_dirs = ["venv", ".venv"]
ignored_files = ["setup.py"]
ignore_stdlib = false
ignore_external_lib = false
ignored_nodes = []
fail_on_unresolved_imports = false
forbidden_external_libs = []
```

Explicit `--config` example using top-level keys:

```toml
ignored_dirs = ["generated"]
ignored_files = ["bootstrap.py"]
ignore_stdlib = true
ignore_external_lib = false
ignored_nodes = ["requests"]
fail_on_unresolved_imports = true
forbidden_external_libs = ["requests"]
```

Explicit `--config` can also point to a `pyproject.toml`-style file:

```toml
[tool.netimport]
ignored_dirs = ["generated"]
ignore_stdlib = true
```

## Current Limitations

NetImport is intentionally conservative about unsupported cases. Today that means:

*   It is a static analyzer, so runtime imports, plugin loading, and `sys.path` mutations are not modeled.
*   Namespace packages are not part of the supported resolver contract.
*   `from ... import *` is handled conservatively and may remain partial when exports are dynamic.
*   Visualization support is limited to the documented backend/layout combinations instead of silently guessing unsupported modes.

## Roadmap

The items below are future enhancements, not part of the current support contract.

- Architectural Metrics Calculation:
    - Count of incoming/outgoing dependencies for each module (Afferent/Efferent Couplings).
    - Calculation of Instability (I) metric.
    - (Further research needed for A) Calculation of Abstractness (A) and Distance from Main Sequence (D) metrics, potentially with user-assisted annotation for abstract components.
- Defining Layers and Rule Checking: Ability to define architectural layers and validate rules between them (e.g., via a configuration file).
- Advanced Visualization:
  - Interactive HTML reports (e.g., using pyvis or bokeh).
  - Highlighting specific nodes or paths on the graph.
  - Grouping nodes by package or defined layer.
- Plugin for popular IDEs (VSCode, PyCharm).
- CI/CD Integration: Output results in CI-friendly formats (e.g., JUnit XML), allow setting metric thresholds.
- Improved Import Resolution:
  - Better handling of __all__ for more accurate analysis of from ... import *.
  - More precise import resolution considering sys.path modifications and namespace packages.

## Contributing

Contributions are welcome to make NetImport better! If you'd like to help, please check out CONTRIBUTING.md for instructions on setting up your development environment, code style, and the process for submitting Pull Requests.

Key areas for contribution:

- Implementing new features from the Roadmap.
- Improving the existing codebase (refactoring, optimization).
- Writing tests.
- Enhancing documentation.
- Bug fixing.

Feel free to open Issues to discuss new ideas or problems.

## License

This project is licensed under the MIT License. See `LICENSE.txt` for the full text.
