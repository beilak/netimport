# NetImport: Python Project Architecture Analyzer via Import Graphs

NetImport is a static analysis tool for Python projects that helps developers visualize and evaluate their codebase architecture by analyzing `import` statements. It builds a dependency graph between modules and packages, providing a clearer understanding of the project's structure, identifying potential issues with coupling and cohesion, and tracking complex or undesirable relationships.

## Core Features

*   **Import Analysis:** Recursively scans the specified project directory for Python files and parses their `import` statements.
*   **Dependency Graph Construction:** Creates a directed graph where nodes represent project modules/packages, as well as external and standard libraries. Edges depict the imports between them.
*   **Graph Visualization:** Supports an interactive Bokeh view and a static Matplotlib view with explicit backend/layout compatibility.
*   **Console Summary:** Prints a deterministic text report with project-level counts and coupling tables.
*   **Configuration via CLI and TOML files:** Supports CLI overrides plus config from `[tool.netimport]` in `pyproject.toml` or `.netimport.toml`.
*   **Dependency Type Identification:** Distinguishes imports of internal project modules, Python standard libraries, and external third-party dependencies.

## Why Use NetImport?

*   **Understand Project Structure:** Gain a clear visual overview of how different parts of your application are interconnected. This is especially useful for new team members or when working with legacy code.
*   **Assess Coupling:** Identify modules that are highly dependent on each other. High coupling can make code harder to change, test, and reuse.
*   **Gauge Cohesion (Indirectly):** While directly calculating cohesion from imports alone is difficult, the graph can provide insights into how logically grouped functionalities are within a module by observing its dependencies.
*   **Aid Refactoring:** Use the graph as a map during refactoring to understand which parts of the system will be affected by changes.
*   **Architectural Oversight:** Helps in maintaining a clean and understandable architecture by making dependencies explicit.

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

Example summary output:

```text
Dependency Graph Summary
========================
+--------------------------+-------+
| Metric                   | Value |
+--------------------------+-------+
| Nodes                    | 9     |
| Edges                    | 8     |
| Project files            | 9     |
| Standard library modules | 0     |
| External libraries       | 0     |
| Unresolved imports       | 0     |
+--------------------------+-------+

Project Coupling Metrics
========================
+------------------------+------+--------+-----+-----+
| Metric                 | Avg  | Median | Min | Max |
+------------------------+------+--------+-----+-----+
| Project files analyzed | 9    | -      | -   | -   |
| Incoming degree        | 0.89 | 1.00   | 0   | 2   |
| Outgoing degree        | 0.89 | 1.00   | 0   | 4   |
| Total degree           | 1.78 | 2.00   | 0   | 4   |
+------------------------+------+--------+-----+-----+
```


### Configuration

NetImport reads configuration from the analyzed project directory, not from the caller's current working directory.

Supported config files:

- `[tool.netimport]` in `pyproject.toml`
- `.netimport.toml`

Precedence:

1. built-in defaults
2. `pyproject.toml`
3. `.netimport.toml`
4. CLI options

For collection options (`ignored_dirs`, `ignored_files`, `ignored_nodes`), CLI values are added on top of file config values. For boolean options (`ignore_stdlib`, `ignore_external_lib`), explicit CLI flags override file config values.

Supported keys:

- `ignored_dirs`
- `ignored_files`
- `ignore_stdlib`
- `ignore_external_lib`
- `ignored_nodes`

`pyproject.toml` example:

```
[tool.netimport]
ignored_dirs = ["venv", ".venv", "tests", "docs", "__pycache__", "node_modules", "migrations"]
ignored_files = ["setup.py", "manage.py"]
ignore_stdlib = true
ignore_external_lib = true
ignored_nodes = []
```

`.netimport.toml` example:

```toml
ignored_dirs = ["venv", ".venv"]
ignored_files = ["setup.py"]
ignore_stdlib = false
ignore_external_lib = false
ignored_nodes = []
```


## Roadmap

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

License

This project is licensed under the MIT License (you'll need to create this file).

Crafted with ❤️ to help improve Python project architectures.
