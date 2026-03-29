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
- deterministic folder-box geometry in the constrained Bokeh layout, so nodes
  stay inside their assigned folders and sibling folder overlays do not collide
- adaptive spacing, section splitting, and larger Bokeh canvas dimensions for
  bigger graphs, so large folder trees get more visual separation on first open

## Reproducibility Follow-Up

1. Rendering determinism must remain a release requirement.
   Status on 2026-03-29: partially addressed in code. Seeds are fixed for the
   spring-based layouts, and traversal order is now normalized in file
   discovery, graph construction, folder placement, node preparation, arrow
   serialization, and folder-box packing. Manual screenshot-level verification
   is still needed on real large projects to confirm that repeated runs stay
   visually identical.

## Checks Run

The following checks were run after the 2026-03-29 follow-up changes:

- `poetry run pytest tests`
- `poetry run mypy netimport_lib tests`
- `poetry run ruff check netimport_lib tests`
- `poetry run netimport good_example --show-console-summary --no-show-graph`
- `poetry run netimport good_big_example --show-console-summary --no-show-graph`

Observed results:

- `pytest` passes: `77 passed`
- `mypy netimport_lib tests` passes
- `ruff check netimport_lib tests` passes
- `good_example` summary renders successfully with `0` unresolved imports
- `good_big_example` summary renders successfully with `0` unresolved imports

## Remaining Validation Gap

Automated checks now cover correctness, deterministic data preparation,
folder-membership constraints, and large-graph spacing improvements in the
constrained Bokeh renderer. Manual screenshot-level determinism review against
real-world projects is still needed before the visualizer can be considered
production ready.
