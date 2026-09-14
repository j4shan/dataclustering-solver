# dataclustering-solver

This project presents a data-layout challenge common in very large analytical data lakes,
together with a production mapping to Delta Lake and Spark on Databricks.

Storage engines fetch whole containers—files, blocks, or partitions—even when a query
selects only a few records inside them. The project frames the resulting waste and asks
whether changing which records share containers improves storage locality across an
observed query workload. It presents the problem; it recommends no way of solving it.

## The page

One local page carries the argument in five sections, in the order it runs. The top bar
selects a section, and a link to a section's anchor opens the page on it.

| section | what it is for |
| --- | --- |
| Problem Statement | a medicine-cabinet walkthrough beside a terminology dictionary and the formal framework, pre-rendered with native MathML and its own contents list |
| Measuring Data Layout Fitness | a text-only walkthrough of split-search fitness (skip ratios and weighted Gini) beside a terminology dictionary, an abstracted split-cycle figure, and one continued Gini example on an authored auto-parts partition. It illustrates the measure; it searches for nothing |
| Drawing Storage Boundary | a static multiple-choice-knapsack feasibility walkthrough beside three deferred-visualization placeholders, one per section. It illustrates the constraint; it allocates nothing |
| Go Live on Databricks Lakehouse | the six-step go-live process beside three figures: the process, ingestion into a narrow index and a wide event table, and Spark Dynamic Partition Pruning |
| Business Signal in Cold Data | one scrolling pane: a usage-shaped layout quarantines idle clusters; three deferred Finviz-style maps (advertising, ecommerce, social) name those clusters as KPI-poor spend, stock, or posts |

The formal statement behind the first section is
[problem-statement.md](site/docs/problem-statement.md); the engine mapping behind the
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

## Publishing it

```
python3 tools/publish.py            # writes build/
```

The same page, assembled for static hosting. The step copies `site/` and inlines each
section's fragment into the document that mounts it, so the file a host sends is the whole
argument rather than a shell that fills itself in with script — which is what a link
preview, a search crawler, and a reader without JavaScript all receive. Nothing is
minified, bundled, or rewritten; every other file in the output is committed, byte for
byte.

`build/` uploads as it stands, or a host can run the command itself: on Cloudflare Pages
or Netlify, set the build command to `python3 tools/publish.py` and the output directory
to `build/`. `site/_headers` travels with it and restates the content security policy and
the caching rules that the local server sends as response headers.

## Project structure

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

`site/` is the whole published surface. The directory layout is the URL layout, so the
server maps nothing and a path that resolves in the repository resolves in the browser —
and anything kept out of `site/`, which is what `resources/` is for, cannot be requested.

## Development

```
uv sync --extra dev        # or: pip install -e ".[dev]"
python -m pytest           # testpaths = ["tests"]
```

Plain `uv sync` installs only what serves the page, so it *removes* pytest if it is already
there. Everything under `site/` is authored by hand; pre-rendered fragments
and figures are committed so a default install can serve them. **The page's layout is
checked by opening it**, because pane scrolling and the narrow-viewport breakpoint have no
automated check.
