# dataclustering-solver

This project presents a data-layout challenge common in very large analytical data lakes,
together with a production mapping to Delta Lake and Spark on Databricks.

Storage engines fetch whole containers—files, blocks, or partitions—even when a query
selects only a few records inside them. The project frames the resulting waste and asks
whether changing which records share containers improves storage locality across an
observed query workload. It presents the problem; it recommends no way of solving it.

## The page

One local page carries the argument in four sections, in the order it runs. The top bar
selects a section, and a link to a section's anchor opens the page on it.

| section | what it is for |
| --- | --- |
| Problem Statement | a medicine-cabinet walkthrough beside a terminology dictionary and the formal framework, pre-rendered with native MathML and its own contents list |
| Measuring Data Layout Fitness | a text-only walkthrough of split-search fitness (skip ratios and weighted Gini) beside a terminology dictionary, an abstracted split-cycle figure, and one continued Gini example on an authored auto-parts partition. It illustrates the measure; it searches for nothing |
| Drawing Storage Boundary | a static multiple-choice-knapsack feasibility walkthrough beside three deferred-visualization placeholders, one per section. It illustrates the constraint; it allocates nothing |
| Go Live on Databricks Lakehouse | the six-step go-live process beside three figures: the process, ingestion into a narrow index and a wide event table, and Spark Dynamic Partition Pruning |

The formal statement behind the first section is
[problem-statement.md](resources/html/problem-statement.md); the engine mapping behind the
fourth is [production-design.md](project_metadata/production-design.md).

## Opening it

Python 3.12 or later. Serving the page needs FastAPI on uvicorn and nothing else.

```
uv sync                                            # or: pip install -e .
source .venv/bin/activate && python -m simulator gui
```

It serves **`http://127.0.0.1:8765/`** and opens a browser. `--port` moves the bind,
`--no-browser` suppresses the opening, Ctrl-C stops it. The server hands over authored
HTML, CSS, and JavaScript directly, with no template engine and no bundler: the page
fetches nothing from a CDN and sends nothing back. Each run writes a log under
`data/logs/`, and nothing prunes them.

## Project structure

```
simulator/
  core/            the dataset contract and the loader
  providers/       dataset construction
  gui/             the server and the page it serves
tests/             the suite
project_metadata/  the product spec, instructions, and the engine mapping
resources/         committed artifacts: the figures, the authored HTML, the formal statement, and the scenario JSON
data/              written at run time and never committed
```

## Development

```
uv sync --extra dev        # or: pip install -e ".[dev]"
python -m pytest           # testpaths = ["tests"]
```

Plain `uv sync` installs only what serves the page, so it *removes* pytest if it is already
there. Everything under `simulator/gui/static/` is authored by hand; pre-rendered fragments
and figures are committed so a default install can serve them. **The page's layout is
checked by opening it**, because pane scrolling and the narrow-viewport breakpoint have no
automated check.
