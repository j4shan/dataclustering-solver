# dataclustering-solver

## Purpose

This project presents a data-layout challenge common in very large analytical data lakes,
together with a production mapping to Delta Lake and Spark on Databricks.

Storage engines fetch whole containers (files, blocks, or partitions) even when a query
selects only a few records inside them. The project frames the resulting waste and asks
whether changing which records share containers improves storage locality across an
observed query workload. The repository states that problem and ships no assignment
strategy.

## Page layout

The local page has five sections, listed in the order they appear. The top bar
selects a section. A link to a section's anchor opens the page on that section.

| section | content |
| --- | --- |
| Problem Statement | a medicine-cabinet walkthrough beside a terminology dictionary and the formal framework, pre-rendered with native MathML and its own contents list |
| Measuring Data Layout Fitness | a text-only walkthrough of split-search fitness (skip ratios and weighted Gini) beside a terminology dictionary, an abstracted split-cycle figure, and one continued Gini example on an authored auto-parts partition. The walkthrough stops at the measure. It runs no search. |
| Drawing Storage Boundary | a static multiple-choice-knapsack feasibility walkthrough beside three deferred-visualization placeholders, one per section. The walkthrough illustrates the constraint. It allocates no storage. |
| Go Live on Databricks Lakehouse | the six-step go-live process beside three figures: the process, ingestion into a narrow index and a wide event table, and Spark Dynamic Partition Pruning |
| Business Insights as Byproduct | two independently scrolling panes (text 30%, figures 70%): the layout pass already collects the selection log and counts per-group demand, so reading those same counts as a statement about the catalog costs nothing extra; one ecommerce map, and the limits of what it can be asked |

The formal statement behind the first section is
[problem-statement.md](site/docs/problem-statement.md). The engine mapping behind the
fourth is [production-design.md](project_metadata/production-design.md).

## Local deployment

Python 3.12 or later. Serve the page at `http://127.0.0.1:8765/` with FastAPI on uvicorn.
Serving needs nothing else.

```
uv sync                                            # or: pip install -e .
source .venv/bin/activate && python -m simulator gui
```

The command binds to that address and opens a browser. Pass `--port` to change the port.
Pass `--no-browser` to skip opening a window. Press Ctrl-C to stop the server. The server
serves authored HTML, CSS, and JavaScript directly, with no template engine and no bundler.
The page fetches nothing from a CDN and sends nothing back. Each run writes a log under
`data/logs/`. The repository never prunes those logs.

## Static hosting

The hosted copy is `site/` as it sits, the same tree the local server hands over. Point
the host's assets directory at `site/`. `site/_headers` restates the content security
policy and the caching rules that the local server sends as response headers.

## Repository layout

```
site/               the page, served as it sits and published as it sits
  figures/html/     the illustration fragments each section mounts
  figures/img/      the figures
  docs/             the formal problem statement and its appendix
simulator/
  core/             the dataset contract and the loader
  providers/        dataset construction
  gui/              the server that hands over site/
tests/              the suite
project_metadata/   the product spec, instructions, and the engine mapping
resources/          authoring material, never served: diagram sources, figure prompts, the scenario JSON
data/               written at run time and never committed
```

`site/` is the whole published surface. The directory layout is the URL layout, so a path
that resolves in the repository resolves in the browser. The server does not remap paths.
Keep authoring material out of `site/` (that is what `resources/` is for) so a browser
cannot request it.

## Tests

```
uv sync --extra dev        # or: pip install -e ".[dev]"
python -m pytest           # testpaths = ["tests"]
```

Plain `uv sync` installs only what serves the page, so it *removes* pytest if it is already
there. Everything under `site/` is authored by hand. The repository commits pre-rendered
fragments and figures so a default install can serve them. Check the page layout by
opening it: pane scrolling and the narrow-viewport breakpoint have no automated check.
  