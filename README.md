# NetImport: Python Project Architecture Analyzer via Import Graphs

NetImport is a static analysis tool for Python projects that helps developers visualize and evaluate their codebase architecture by analyzing `import` statements. It builds a dependency graph between modules and packages, providing a clearer understanding of the project's structure, identifying potential issues with coupling and cohesion, and tracking complex or undesirable relationships.

## Core Features

*   **Import Analysis:** Recursively scans the specified project directory for Python files and parses their `import` statements.
*   **Dependency Graph Construction:** Creates a directed graph where nodes represent project modules/packages, as well as external and standard libraries. Edges depict the imports between them.
*   **Graph Visualization:** Integrates with Matplotlib to generate visual representations of the dependency graph, facilitating easier analysis.
*   **Flexible Configuration:** Allows customization of ignored directories and files via the command line, an `.netimport.toml` file, or `pyproject.toml`.
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


### Key Options:

<PROJECT_PATH>: Path to the root directory of your Python project to be analyzed.

--output-graph FILENAME.PNG: Save the graph visualization to the specified file (e.g., dependencies.png).

--show-graph: Display the graph using Matplotlib (requires a GUI environment).

--config FILEPATH: Path to a custom configuration file (instead of .netimport.toml or pyproject.toml).

--ignored-dirs DIR1,DIR2: Comma-separated list of directories to ignore, overrides configuration files.

--ignored-files FILE1,FILE2: Comma-separated list of files to ignore.

--show-console-summary: Print a textual summary of the graph to the console.

--export-dot FILENAME.DOT: Export the graph in DOT format for use with Graphviz.

--export-mermaid FILENAME.MD: Export the graph in Mermaid syntax.

--layout ALGORITHM_NAME: Choose a graph layout algorithm for visualization (e.g., spring, kamada_kawai, circular; or dot, neato if Graphviz is used).


### Example:

```bash
netimport ./my_python_project --output-graph project_deps.png --layout spring
```


### Configuration

NetImport looks for configuration files in the following order of precedence:

- Command-line arguments.
- An .netimport.toml file in the project root.
- The [tool.netimport] section in a pyproject.toml file in the project root.
- Default values. (Maybe. I'm still thinking.)

Example .netimport.toml or pyproject.toml ([tool.netimport]):

```
ignored_dirs = ["venv", ".venv", "tests", "docs", "__pycache__", "node_modules", "migrations"]
ignored_files = ["setup.py", "manage.py"]
ignore_stdlib = true
ignore_external_lib = true
ignored_nodes = []
# Other planned or potential settings:
# default_layout_algorithm = "spring"
# exclude_std_lib_from_graph = false
# exclude_external_libs_from_graph = false
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