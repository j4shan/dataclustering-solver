# dataclustering-solver

This project presents a data-layout challenge common in very large analytical data lakes and
provides a framework for measuring heuristic assignments learned from what expensive OLAP queries
fetch, together with a production mapping to Delta Lake and Spark on Databricks.

Storage engines fetch whole containers—files, blocks, or partitions—even when a query selects only
a few records inside them. The project measures the resulting waste and tests whether changing
which records share containers improves storage locality across an observed query workload.

The repository includes a formal [problem statement](resources/graphics/problem-statement.md), an
offline simulator for scoring third-party assignment strategies, a pre-scored demonstration, and
an engine mapping. It provides the measurement and deployment framework without recommending a
particular clustering strategy.

## A worked example

Picture a closet. It has the three properties that make data layout hard, and you can see
all of them at once.

- **You retrieve by the drawer, not by the garment.** Everything folded in with what you
  wanted gets lifted out and put back for nothing.
- **A list tells you which drawers to open.** Taped inside the door is one line per garment
  saying what it is and which drawer holds it. Reading twelve lines costs nothing; lifting
  out twelve garments is the whole morning. The list is exact, so you never open a drawer
  for nothing — but it cannot tell you what *else* you will find once a drawer is open.
- **The closet keeps changing.** Garments come and go, the weather turns, and an arrangement
  that suited March is mediocre by September. There is no way to close the closet while you
  fix it.

One number carries the whole problem: the garments handled but not worn.

| in the closet | in a storage system |
| --- | --- |
| a garment | an **event**, the stored item |
| a drawer or cabinet | a **container**, the smallest thing that can be opened |
| this morning's outfit | a **query**, and the events it selects |
| garments handled, not worn | **waste**, work paid for at value zero |
| which garment lives in which drawer | the **layout**, the one thing under our control |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="resources/img/selection-matrix.dark.svg">
  <img alt="The selection matrix under two layouts. Rows are events grouped into containers, columns are queries. Under the as-built layout 45 cells are wasted; under the clustered layout, 6." src="resources/img/selection-matrix.light.svg">
</picture>

Each row above is a garment, each column a morning, and a filled cell means that morning
called for that garment. The boxes are the drawers. **The two panels differ in one respect
only: which garments were put in which drawer.** The closet, the mornings and the record of
what was worn are identical between them. Blue is what you wanted and red is what you
handled anyway; inside a drawer, a column is either all filled or all empty, because one
garment you want obliges the whole drawer. On the left, 45 garments were handled for
nothing. On the right, 6.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="resources/img/container-zoom.dark.svg">
  <img alt="Two containers during one query. The activated container holds one selected event and two wasted ones. No index row points at the bypassed container, so it is never read." src="resources/img/container-zoom.light.svg">
</picture>

Zooming in on a single morning shows why the arrangement is worth so much. A drawer meets
one of two fates. If it holds something you want, you open it and pay for everything
inside; if it holds nothing you want, you never touch it, and it costs nothing at all —
not a partial read, not a filtered read. Skipping is the only free operation in the
system, which is why the whole exercise is about causing more of it.

> **[Open the interactive version →](https://claude.ai/code/artifact/bc148f2d-9ed7-4959-9aca-f1fa715f64f4)**
> Twelve garments and eight mornings, with one garment you can move between drawers to
> watch the waste recount. Source: [closet-canvas.html](resources/graphics/closet-canvas.html),
> which is self-contained and opens in a browser with no install.

More details about the search space, assignment-evaluation cost, and changing query patterns are
available in the problem statement’s
[Problem Complexity Analysis](resources/graphics/problem-statement.md#5-problem-complexity-analysis).

## Project Content

The repository brings four parts together.

**A problem definition** states the storage model, the objective, the constraints and the
complexity, in
[problem-statement.md](resources/graphics/problem-statement.md).

**A static exhibit** is the primary presentation surface. It is one local page with three
sections: the problem, a benchmark of assignment strategies the simulator scored ahead of
serving, and the engine mapping. Every number it displays comes from a precomputed artifact.

**A simulator** turns a layout into numbers. It takes a dataset — synthetic, or a CSV
export you adopt — together with a strategy registered against the plugin seam, and
evaluates the resulting layout across a sweep of container sizes. Queries are split
temporally, so a strategy sees the training half while every reported number is measured
on held-out queries it never had. Results land beside a workload-agnostic baseline,
because that comparison is what decides whether a rewrite is worth doing. Alongside the
read cost, the harness charges what the read cost hides: a layout of many tiny containers
wins on waste and loses in production, once every container costs a log entry, a task and
a round trip. The report gives that cost its own axis so both halves of the trade-off stay
visible. The requirements, seam by seam, are in
[simulator-spec.md](project_metadata/simulator-spec.md).

**Explainer assets** make the same instance visible as figures, an interactive closet, and
an architecture canvas. They illustrate; they are not a second scorer.

**No clustering strategy ships as a recommendation.** Strategies are third-party plugins.
The included group-by chains with capacity bucketing are demonstration fixtures, scored
offline to give the exhibit a range of layouts to compare. They make the objective
legible; they are not advice about how to lay out data.

The page carries four sections in the order the argument runs and shows one at a time.
The top bar selects a section, and a link to a section's anchor opens the page on it.

| section | what it is for |
| --- | --- |
| **A · Problem Statement** | a medicine-cabinet walkthrough beside the formal framework, pre-rendered with native MathML and its own contents list |
| **B · Data Skipping Experiment** | select up to four pre-scored catalogue entries and read them against the industry-default baseline |
| **C · Spark + Delta Lake Implementation** | the engine mapping, at Section A's parity, beside three diagrams of the mechanisms it names and the twelve-event table illustrations |
| **D · Gini Split Search** | a text-only walkthrough of weighted-Gini screening beside four figures of the same twelve-event instance; not a solver and not a recommendation |

Section B is where the simulator earns its keep, but not while you are looking. A candidate is a
chain of group-by expressions over the dataset's feature columns, and each resulting subset is cut
into containers of at most a given record count. The expressions come from a closed grammar—a
column, one operator, and a literal—parsed to data and evaluated by an interpreter over the column,
never by executing text.

**The page presents a catalogue rather than a form.** Six candidates are scored ahead of serving,
each swept across four container capacities and measured against the baseline on both the training
and held-out query sets. The left panel lists their chains, splits, and container counts. Choosing
up to four candidates redraws three views: **P1**, the process diagram; **P2**, the summary table;
and **P3**, paired scatter plots showing how the scores trade off.

The catalogue entries are demonstration fixtures ordered by structural coarseness, not ranked by
performance. Scoring a custom chain remains available through the CLI.

The server reads one catalogue document at startup and serves authored HTML, CSS, and JavaScript
directly. It uses no template engine or bundler, and the page fetches nothing from a CDN. Selecting
catalogue entries sends no reader input to the server.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="resources/img/page-anatomy.dark.svg">
  <img alt="The anatomy of the demonstration page: a top bar with four section links, and the four sections they select, each split into a left and a right pane." src="resources/img/page-anatomy.light.svg">
</picture>

## Quickstart

Python 3.12 or later. The dependencies come in **two sets that do not overlap**. Serving
the page needs FastAPI on uvicorn and nothing else. Building the benchmark catalogue and
reports needs the harness: numpy, pyarrow and matplotlib.

```
uv sync --extra harness          # the harness, pinned from uv.lock
source .venv/bin/activate && python -m simulator  # open the control plane
```

`pip install -e ".[harness]"` works as well. There is no console script, by design, so
`python -m simulator` is the only invocation form.

The menu is the unified control plane. Choose **Build & Launch** for the shortest path:
it bootstraps a corpus if you do not have one, scores the catalogue Section B presents,
starts the exhibit in the background, and opens the page when the instance reports ready.
The page is served at **`http://127.0.0.1:8765/`**. Loopback and port 8765 are the
defaults.

The other numbered choices are Status, Launch, Stop, Restart, Generate corpus, Build
catalogue, and Run benchmark report. Quitting the menu leaves a running exhibit alone.

With no terminal, `python -m simulator` refuses rather than blocking, and names the
subcommands a script can call instead.

**The corpus never leaves your machine, and the page never reads it.** `generate` writes
it under `data/generated/`, `catalog` reads it once and writes a document of a few hundred
kilobytes under `data/catalog/`, and the exhibit serves that document. Neither the corpus
nor the harness reaches a deployed instance: an install without the `harness` extra can
serve the page and cannot score anything, which is what keeps a 24/7 instance at tens of
megabytes rather than hundreds. A harness action run without that extra says so and names
it.

A managed background exhibit writes its complete output to one named run file under
`data/logs/`. The menu prints that path when the instance becomes ready.

Launching twice is safe. Before binding, the control plane asks the port who is holding
it. An instance of itself is reported rather than collided with; a listener that is not
this server is left alone.

### CLI reference

The menu is the everyday surface. The same operations remain callable as subcommands, for
scripts, CI, and a deployed instance that must stay in the foreground.

```
python -m simulator generate     # bootstrap a corpus  (once, a few minutes)
python -m simulator catalog      # score the strategies Section B presents  (~8s)
python -m simulator gui          # serve the page in the foreground
python -m simulator run          # full capacity sweep and static report under data/
```

`gui` is the foreground launch a container image already waits on. `--port` moves the
bind, `--no-browser` suppresses the opening, and `--stop` / `--restart` settle a running
instance without a prompt. A deployed instance differs only in what the environment tells
it: where to bind, what path prefix it is mounted under, and the secret its front door
presents.

`run` is also where you go to score **your own** group-by chain against your own corpus —
the page presents a fixed catalogue, and composing a new strategy is command-line work by
design.

### Project structure

```
simulator/
  core/            the dataset contract, the layout, and the metric primitive
  providers/       corpus generation behind that contract: synthetic, or an adopted export
  strategies/      the plugin registry, the expression seam, the demonstration family
  config/          the capacities the sweep and the catalogue run across
  bench/           the sweep, the catalogue generator, and the metric table
  report/          static charts and the report page `run` writes
  gui/             the exhibit server and the page it serves
  menu.py          the numbered control plane
tests/             the suite, plus a DOM stand-in for the page's ES modules
tools/             the two generators for committed artifacts
project_metadata/  the engine mapping and the two specs
resources/         committed artifacts: the figures, the graphics, the formal statement, and the scenario JSON
data/              written at run time and never committed: corpora, metrics, reports, logs
```

### Development

The build backend is setuptools and the package needs Python 3.12 or later. Two additional
extras support development: `dev` installs the test suite, and `docs` installs the tools
that re-render the two long documents.

```
uv sync --extra dev        # or: pip install -e ".[dev]"
python -m pytest           # testpaths = ["tests"]
```

Plain `uv sync` installs only the exhibit dependency set, so it *removes* pytest if it is
already there. The `dev` extra is what makes the second line work; it pulls in `docs` as
well, since the pre-render tests import that tooling.

The suite asserts the harness, the JSON interface, the control plane, and the page's
JavaScript against a DOM stand-in. **The page's layout is checked by opening it**, because
pane scrolling, the narrow-viewport breakpoint and the plots' shared width have no
automated check, by decision (12.6.3.1).

Static resources under `simulator/gui/static/` are authored by hand, with two exceptions.
The pre-rendered document pages come from `python -m tools.render_formulation` and are
committed so that a default install can serve them, and the figures under `resources/img/`
come from `python3 tools/render_figures.py` and are never hand-edited.

Every run writes an execution log to `data/logs/`, one file per run. Nothing prunes them,
so `rm -rf data/logs` when they are in the way.

Display the complete CLI instructions with:

```
source .venv/bin/activate && python -m simulator -h
```
