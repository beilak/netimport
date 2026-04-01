from _pytest.capture import CaptureFixture

from netimport_lib.summary_builder import format_summary, print_summary
from tests.summary_builder_support import SummaryNames, build_demo_graph


def test_format_summary_coupling_metrics() -> None:
    graph = build_demo_graph()

    assert format_summary(graph) == [
        (
            "(This report summarizes the project's import graph so a reader or "
            "LLM can spot hotspots, risky dependencies, isolated files, and "
            "missing links.)"
        ),
        (
            "(Incoming degree shows how many project files depend on a file; "
            "outgoing degree shows how many dependencies a file pulls in. "
            "Higher values usually mean higher impact or complexity.)"
        ),
        "",
        "Dependency Graph Summary",
        "========================",
        (
            "(High-level graph totals. Use this table to quickly size the "
            "project and see how much of the graph is project code, stdlib, "
            "external libraries, or unresolved imports.)"
        ),
        "+--------------------------+-------+",
        "| Metric                   | Value |",
        "+--------------------------+-------+",
        "| Nodes                    | 7     |",
        "| Edges                    | 6     |",
        "| Project files            | 4     |",
        "| Standard library modules | 1     |",
        "| External libraries       | 1     |",
        "| Unresolved imports       | 1     |",
        "+--------------------------+-------+",
        "",
        "Project Coupling Metrics",
        "========================",
        (
            "(Aggregate coupling across all project files. Avg and Median "
            "describe a typical file, while Min and Max highlight the spread "
            "and the biggest extremes.)"
        ),
        "+------------------------+------+--------+-----+-----+",
        "| Metric                 | Avg  | Median | Min | Max |",
        "+------------------------+------+--------+-----+-----+",
        "| Project files analyzed | 4    | -      | -   | -   |",
        "| Incoming degree        | 0.75 | 0.50   | 0   | 2   |",
        "| Outgoing degree        | 1.50 | 1.00   | 0   | 4   |",
        "| Total degree           | 2.25 | 2.50   | 0   | 4   |",
        "+------------------------+------+--------+-----+-----+",
        "",
        "Most Coupled Project Files",
        "==========================",
        (
            "(Files with the highest total degree. Higher totals mean a file "
            "is highly connected overall, so changes here are more likely to "
            "ripple across the project.)"
        ),
        SummaryNames.rank_table_border,
        SummaryNames.rank_table_header,
        SummaryNames.rank_table_border,
        "| 1    | main.py     | 0        | 4        | 4     |",
        "| 2    | helper.py   | 2        | 1        | 3     |",
        "| 3    | service.py  | 1        | 1        | 2     |",
        "| 4    | isolated.py | 0        | 0        | 0     |",
        SummaryNames.rank_table_border,
        "",
        "Least Coupled Project Files",
        "===========================",
        (
            "(Files with the lowest total degree. Very low values can indicate "
            "isolated utilities, unfinished integration, or code paths that "
            "deserve a second look.)"
        ),
        SummaryNames.rank_table_border,
        SummaryNames.rank_table_header,
        SummaryNames.rank_table_border,
        "| 1    | isolated.py | 0        | 0        | 0     |",
        "| 2    | service.py  | 1        | 1        | 2     |",
        "| 3    | helper.py   | 2        | 1        | 3     |",
        "| 4    | main.py     | 0        | 4        | 4     |",
        SummaryNames.rank_table_border,
        "",
        "Most Depended-On Project Files",
        "==============================",
        (
            "(Files with the highest incoming degree. These are reuse hubs: "
            "the more incoming links a file has, the more carefully it should "
            "usually be changed.)"
        ),
        SummaryNames.rank_table_border,
        SummaryNames.rank_table_header,
        SummaryNames.rank_table_border,
        "| 1    | helper.py   | 2        | 1        | 3     |",
        "| 2    | service.py  | 1        | 1        | 2     |",
        "| 3    | main.py     | 0        | 4        | 4     |",
        "| 4    | isolated.py | 0        | 0        | 0     |",
        SummaryNames.rank_table_border,
        "",
        "Most Dependent Project Files",
        "============================",
        (
            "(Files with the highest outgoing degree. High outgoing values "
            "often point to orchestration code, complex workflows, or modules "
            "with many responsibilities.)"
        ),
        SummaryNames.rank_table_border,
        SummaryNames.rank_table_header,
        SummaryNames.rank_table_border,
        "| 1    | main.py     | 0        | 4        | 4     |",
        "| 2    | helper.py   | 2        | 1        | 3     |",
        "| 3    | service.py  | 1        | 1        | 2     |",
        "| 4    | isolated.py | 0        | 0        | 0     |",
        SummaryNames.rank_table_border,
        "",
        "External Dependencies",
        "=====================",
        (
            "(Third-party libraries imported by the project. Review this list "
            "for dependency sprawl, standardization opportunities, and policy "
            "or supply-chain checks.)"
        ),
        "+------+------------+",
        "| Rank | Dependency |",
        "+------+------------+",
        "| 1    | requests   |",
        "+------+------------+",
        "",
        "Unresolved Imports",
        "==================",
        (
            "(Imports NetImport could not resolve. These often point to broken "
            "imports, missing files, excluded paths, or dynamic import "
            "patterns.)"
        ),
        "+------+----------+---------------------+",
        "| Rank | Import   | Type                |",
        "+------+----------+---------------------+",
        "| 1    | .missing | unresolved_relative |",
        "+------+----------+---------------------+",
        "",
        "Policy Violations",
        "=================",
        (
            "(Configured rule violations found during analysis. A non-empty "
            "table means the graph is valid to inspect, but not fully "
            "compliant with the active policy.)"
        ),
        "+------+---------+",
        "| Rule | Message |",
        "+------+---------+",
        "| None | -       |",
        "+------+---------+",
    ]


def test_print_summary_writes_formatted_lines(capsys: CaptureFixture[str]) -> None:
    graph = build_demo_graph()

    print_summary(graph)

    captured = capsys.readouterr()

    assert "Dependency Graph Summary" in captured.out
    assert "This report summarizes the project's import graph" in captured.out
    assert "| Total degree           | 2.25 | 2.50   | 0   | 4   |" in captured.out
    assert "| 1    | main.py     | 0        | 4        | 4     |" in captured.out
