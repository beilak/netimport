# NetImport: Python Project Architecture Analyzer via Import Graphs

NetImport is a static analysis tool for Python projects that helps developers visualize and evaluate their codebase architecture by analyzing `import` statements. It builds a dependency graph between modules and packages, providing a clearer understanding of the project's structure, identifying potential issues with coupling and cohesion, and tracking complex or undesirable relationships.

## Core Features

*   **Import Analysis:** Recursively scans the specified project directory for Python files and parses their `import` statements.
*   **Dependency Graph Construction:** Creates a directed graph where nodes represent project modules/packages, as well as external and standard libraries. Edges depict the imports between them.
*   **Graph Visualization:** Integrates with Matplotlib to generate visual representations of the dependency graph, facilitating easier analysis.
*   **Console Summary:** Prints a deterministic text report with project-level counts and coupling tables.
*   **Configuration via `pyproject.toml`:** Supports `[tool.netimport]` settings for ignored directories, ignored files, stdlib filtering, external library filtering, and ignored nodes.
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

`--layout [planar_layout|spring|kamada_kawai|circular|spectral|shell|dot|neato|fdp|sfdp]`

Choose a layout name for the graph backend.

`--show-graph [bokeh|mpl]`

Select the visualization backend. Current default is `bokeh`.

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

### Examples

Open the graph for a project using the default backend:

```bash
poetry run netimport example
```

Print only the console summary and do not open the browser:

```bash
poetry run netimport example --show-console-summary --no-show-graph
```

Use the Matplotlib backend explicitly:

```bash
poetry run netimport example --show-graph mpl
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

Current implementation reads configuration from the `[tool.netimport]` section in `pyproject.toml` in the current working directory.

Supported keys:

- `ignored_dirs`
- `ignored_files`
- `ignore_stdlib`
- `ignore_external_lib`
- `ignored_nodes`

Example:

```
[tool.netimport]
ignored_dirs = ["venv", ".venv", "tests", "docs", "__pycache__", "node_modules", "migrations"]
ignored_files = ["setup.py", "manage.py"]
ignore_stdlib = true
ignore_external_lib = true
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
