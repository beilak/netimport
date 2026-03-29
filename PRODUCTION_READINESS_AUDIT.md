# NetImport Production Readiness Audit

## What This Project Is

`NetImport` is a Python CLI tool that statically analyzes Python projects by
parsing `import` statements, building a dependency graph, and visualizing or
summarizing the result.

This audit tracks both open production blockers and agreed follow-up
improvements requested during the 2026-03-29 review.

Audit re-verified and updated on 2026-03-29.

## Current State

Core CLI, config loading, summary output, and backend selection behavior remain
in solid shape. In addition to the earlier audit fixes, the repository now also
contains:

- stronger deterministic ordering in file discovery, graph building, and Bokeh
  render preparation
- a neutral renderer module name: `netimport_lib.visualizer.bokeh_plotter`
- new `good_example` and `good_big_example` demo projects that illustrate lower
  coupling than the original stress-case samples

## Open Visual Problems

1. Folder rectangles can overlap each other in the constrained Bokeh layout.
   The current folder-box geometry is computed independently from sibling
   folders, so nearby clusters can produce partially or fully intersecting
   folder overlays. This makes folder boundaries hard to read and can hide the
   intended package structure.

2. Large projects still collapse into visual chaos.
   When the dependency graph becomes large, the current spring-based folder and
   node placement strategy does not preserve enough separation. Nodes, labels,
   and folder boxes crowd the same area, so the resulting image stops being a
   usable architectural overview.

3. Nodes can visually overlap folder boxes and appear to belong to the wrong
   folder.
   For larger graphs, a node may land on top of a neighboring folder rectangle
   even when its logical `folder` metadata points elsewhere. The rendered result
   looks like the node belongs to that folder, which is a correctness problem
   for users who rely on the picture as documentation.

## Reproducibility and Maintainability Follow-Ups

4. Rendering determinism must remain a release requirement.
   Status on 2026-03-29: partially addressed in code. Seeds are fixed for the
   spring-based layouts, and traversal order is now normalized in file
   discovery, graph construction, folder placement, node preparation, and arrow
   serialization. Manual screenshot-level verification is still needed on real
   large projects to confirm that repeated runs stay visually identical.

5. The previous renderer filename `bokeh_plotter_v2.py` was a maintainability
   smell.
   Status on 2026-03-29: addressed. The module was renamed to
   `bokeh_plotter.py`, and internal imports/tests were updated. Version suffixes
   in import paths make the code look provisional and encourage future
   `*_v3.py` drift instead of a stable public module name.

6. The repository needed low-coupling sample projects in addition to the
   existing high-coupling stress cases.
   Status on 2026-03-29: addressed. The original `example` and `big_example`
   directories were kept as intentionally noisy samples, and new `good_example`
   and `good_big_example` directories were added. The new samples keep the same
   general domain shape while routing dependencies through a smaller set of
   package-level entry points so the generated graphs better illustrate
   low-coupling design.

## Checks Run

The following checks were run after the 2026-03-29 follow-up changes:

- `poetry run pytest tests`
- `poetry run mypy netimport_lib tests`
- `poetry run ruff check netimport_lib tests`
- `poetry run netimport good_example --show-console-summary --no-show-graph`
- `poetry run netimport good_big_example --show-console-summary --no-show-graph`

Observed results:

- `pytest` passes: `73 passed`
- `mypy netimport_lib tests` passes
- `ruff check netimport_lib tests` passes
- `good_example` summary renders successfully with `0` unresolved imports
- `good_big_example` summary renders successfully with `0` unresolved imports

## Remaining Validation Gap

Automated checks now cover correctness and deterministic data preparation, but
the large-graph Bokeh readability issues above still need manual visual review
against real-world projects before the visualizer can be considered production
ready.
