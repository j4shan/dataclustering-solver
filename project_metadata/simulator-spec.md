# Simulator Specification — dataclustering-solver

**Status:** current snapshot. This document states what the project requires *now*.

**What this governs.** The product — the code under `simulator/`, the resources the build
generates and ships, and the public contracts a third party writes against. It states **what
the product does, not how it is built**: capabilities, contracts, architecture style, and
quality attributes, at the altitude of a requirement written before the code exists. A data
structure, an algorithm, a library call, or a file path chosen to satisfy a requirement is an
implementation decision and does not appear here.

**What this does not govern.** The content of an authored document. The formal statement, the
engine mapping, the README and the term dictionary are each their own authority; `AGENTS.md`
names them and says what each is for. Requirements on **generated** resources stay here (§9),
because the build produces them and the product ships them.

**Scope of authority.** Where this document and a source file disagree, one of them is wrong
and the disagreement is a defect.

**Companion document.** The demonstration GUI has its own specification,
[`ui-spec.md`](ui-spec.md), which continues this document's numbering from §12. The split is by
subject, not by authority: **any id of `12` or above lives there, everything below lives here**,
so a bare reference is never ambiguous.

**Numbering.** A superseded requirement is deleted, never annotated with what it used to say. A
deleted id leaves a gap; nothing is renumbered.

| Column | Meaning |
| --- | --- |
| **Type** | `F` functional · `NF` non-functional |

---

## 1. Product scope

The project produces four things: a **problem definition** that states the data-clustering
problem precisely, a **simulator** that scores candidate layouts against it, **explainer
assets** that make both legible to a reader who has not met the problem before, and a
**demonstration GUI** that presents them in one place. The GUI is a presentation
surface: it shows the problem, a benchmark the simulator scored ahead of serving (8.11),
the production design, and a Gini split-search illustration. It does not drive the
harness. It does not produce a solver.

| # | Requirement | Type |
| --- | --- | :-: |
| 1.1 | The problem being solved is the assignment of events to storage containers so as to minimize the volume read but not selected, given an observed selection history. | F |
| 1.2 | The project ships **no assignment strategy** as product. Strategies are third-party plugins; anything shipped exists only to exercise the harness — as a baseline that brackets what ordering is worth (7.1.5), or as a demonstration fixture that feeds the offline catalogue the GUI presents (7.1.7, 8.11). Neither is a recommendation. | F |
| 1.3 | The simulator measures skipping in a *logical* sense — which containers a query would open and what that would cost. It never executes a query against a storage system and never reports wall-clock read time. | NF |
| 1.4 | Outputs are indicative, not predictive. A small margin between two strategies is to be read as no margin. Statistical rigour is not a goal. | NF |
| 1.5 | The system has **two deployment targets and no external service dependency in either**: a local demonstration, where the GUI is served from loopback by a process on a single developer laptop, and a **publicly served instance behind a front door** (10.3.12). Neither reaches a third-party network, and the page itself fetches nothing from off its own origin (12.2.2). | NF |
| 1.6 | The **demonstration GUI** is the project's primary presentation surface: one local page carrying the problem statement, a benchmark of assignment strategies the harness scored ahead of serving (8.11), the production design, and the Gini split-search illustration. It authors no number and states no requirement of its own; its requirements live in [`ui-spec.md`](ui-spec.md) §12–§13. | F |

---

## 3. Domain model

The model is the formulation's. What follows is only what the product must implement in order
to score a layout against it.

| # | Requirement | Type |
| --- | --- | :-: |
| 3.1.1 | Demand is recorded as a **two-column selection log** — `record_id`, `query_id` — positives only and append-only: a row's presence *is* the observation, and absence means not selected. It is the sole workload input; selection sets and supports are projections of it, never independently authored. | F |
| 3.1.4 | Events selected by no query appear in the log **not at all**, and are handled as first-class: real bytes, zero demand breadth, counted in size health. | F |
| 3.2.2 | The objective is **aggregate waste** — materialized volume summed over all queries, less selected volume. A single quantity: no weighted sum of competing cost terms, and no frequency weight on a query. | F |
| 3.3.1 | Container resolution is an **exact per-event index** carrying the filterable features, `container_id`, and `record_id`, so activation equals containment with no false positives or negatives. | F |
| 3.3.4 | Index cost is **λ-invariant** and therefore absent from the objective — excluded because it is constant, not because it is negligible — and stays **visible in reported figures**. | F |
| 3.4.1 | Container size bounds, enforced distributionally rather than pointwise. The lower bound is the binding constraint: refinement never increases waste, so the size floor is the sole force opposing granularity. | F |
| 3.4.3 | Write-time assignability: a layout must be evaluable on a newly arriving event from that event alone, without global state. | F |

---

## 4. Dataset contract and providers

| # | Requirement | Type |
| --- | --- | :-: |
| 4.1 | A dataset is three authored CSV files — `events.csv`, `selections.csv`, `queries.csv` — plus `manifest.json`. Everything else is derived. | F |
| 4.2 | Column roles are decided by **convention, not enumeration**: `record_id` is **identity and arrival sequence** — dense, 0-based, and ascending in the order the provider established (4.6), so a strategy may read a position from it without reference to any other event; `blob_*_compressed_bytes` / `blob_*_decompressed_bytes` are sizes, `_`-prefixed are hidden, everything else is a partitionable feature. The `blob_` prefix is **enforced** — the objective is byte-weighted, so a corpus whose sizes cannot be found is rejected at validation rather than scored wrongly. No other prefix is enforced anywhere: an unrecognised column is still a feature, which is what keeps 4.3 true. | F |
| 4.3 | No provider-chosen column name may appear anywhere in `simulator/core/`. A corpus with unfamiliar column names loads with no code change. | NF |
| 4.4 | Providers are a registry (`register` / `get` / `available`). Adding one requires no change above the seam. | F |
| 4.5 | A `synthetic` provider generates a corpus whose demand structure is known by construction. | F |
| 4.6 | A provider **writes events in arrival order** — by ingest time, tie-broken deterministically — and mints `record_id` from the resulting row position, so the order is resolved once at write time and never reconstructed by a reader. An `external` provider adopts a corpus produced elsewhere from the three CSVs alone, deriving supports and per-query byte totals on ingest, and renumbering keys by row position while preserving the originals. | F |
| 4.7 | A `curated` provider slot for a small committed reference corpus. | F |
| 4.8 | Dataset parameters live with the provider that owns them, never in the simulator's shared config. | NF |
| 4.9 | Hidden (`_`-prefixed) columns are present in the table for analysis but absent from the strategy view unless explicitly unlocked; any run that unlocks them is tagged in the metric table. | F |
| 4.10 | Datasets are **immutable and read-only** — the simulator never writes to one. Regeneration produces a new dataset id, and every metric row is stamped with it so results from different corpora cannot be compared on one chart. | F |
| 4.12 | The manifest carries a **per-feature-column summary** — name, dtype, and a description of its domain. It is what lets a caller offer a column and its admissible values without importing the provider (7.1.7.2) or hardcoding a name (4.3), and the catalog document carries it forward (8.11.1) so the GUI can list the corpus's columns without loading the corpus (12.4.2.3). Hidden, identity and blob-size columns are absent from it. | F |
| 4.13 | Loading **validates that `record_id` is a dense 0-based range** and rejects a corpus that is not, so 4.2's sequence is a checked property of every loaded dataset rather than a claim a provider is trusted on. | F |

---

## 5. Data generation (synthetic provider)

| # | Requirement | Type |
| --- | --- | :-: |
| 5.1 | Fully determined by a seed and a parameter set; the dataset id is a hash over those parameters. | F |
| 5.1.1 | The provider ships **exactly one** dataset configuration, small enough that a reader of the workload generator can predict what a query selects. Size variants are not offered: a second config is a second corpus to keep calibrated, and every result would carry a question about which one produced it. | F |
| 5.3 | Events carry flat features with no implied hierarchy, plus a date axis along which demand decays. Recency is a **decaying weight, not a cutoff** — no event is categorically excluded by age, and the only hard edge is causality. Transaction dates are **generated in ascending order**, modelling a corpus that accumulates in time: event time and ingest time coincide, so arrival order (4.2) carries the recency gradient. | F |
| 5.4 | Verbose payloads are **not materialized** — only each event's compressed and decompressed size, drawn from a skewed distribution. | F |
| 5.4.1 | The corpus carries a **dominant clusterable demand driver**, `brand_id`, the client identifier in a multi-tenant system: the most-wanted brand's events are selected about ten times as often as the least-wanted, and the driver **redistributes demand rather than adding it**, so it is structure to exploit and not a volume knob. The per-event draw is written as a hidden column, analysable without being handed to a strategy. | F |
| 5.8 | The corpus must contain a **substantial never-selected population**, arising by degree rather than by boundary, and a history long enough for the decay to reach a genuinely cold region — without both, it has no skippable data by construction. | F |
| 5.11 | The selection table is immutable observed history — never resampled, reweighted, or perturbed. | F |
| 5.12.1 | `set_name` (`training` / `validation`) is **authored with the dataset** and never derived, so set membership is identical across every strategy and run. | F |
| 5.12.2 | The split is **temporal, not random** — earliest queries build, latest validate, with the boundary checked rather than asserted — and every query type contributes to both halves, so a validation result cannot be an artifact of one type landing entirely on one side. Order is carried by query time, identity by `query_id`; ordering is never inferred from an identifier. | F |
| 5.12.6 | Success criteria are measured on held-out queries; a layout scored on its own construction workload is measuring memorization. | NF |

---

## 6. Simulation behaviour

| # | Requirement | Type |
| --- | --- | :-: |
| 6.1.1 | Each event's support is held as one flag per query packed into machine words, enabling OR-reduce for container support and popcount for demand breadth. | F |
| 6.1.2 | The packed support is a derived artifact, rebuilt from the selection log when absent, hash-linked to the dataset, and never committed. The two-column table remains the source of truth. | F |
| 6.1.3 | Per-query statistics are **accumulated, never materialized**: no dense container × query structure is built, so footprint does not grow with their product. | NF |
| 6.1.4 | Byte-weighted throughout: the formulation's unit-size variant is replaced by compressed bytes per event. | F |
| 6.2.1 | A container is opened exactly when it holds an event the query selected. No index property enters the calculation. | F |
| 6.2.3 | The layout covers all events and is replayed against the **whole** query log; rows are emitted per `training`, `validation`, and `all`. | F |
| 6.2.4 | Validation supports are **physically cleared from the strategy's view**, so leakage is impossible by construction rather than by convention. Events selected only by validation queries therefore appear cold and must still be placed from features alone. | F |
| 6.2.6 | Both compressed and decompressed figures are computed on every run so a chart can switch axis without re-evaluating. | F |
| 6.3.1 | Skipping ratios — record, byte, container — are the headline metrics. Byte skipping leads. | F |
| 6.3.2 | Waste ratio and read amplification are reported because they are the formulation's objective, even though skipping leads the presentation. | F |
| 6.3.3 | Per-query waste distribution (median, p95, max) is reported; an aggregate alone hides catastrophic individual queries. | F |
| 6.3.4 | Baseline lift against a stated reference layout on the same dataset and target size. | F |
| 6.3.5 | Size health: container count, size percentiles, and count below the floor — detecting waste bought by shrinking containers. Percentiles stay byte-denominated; the floor follows the swept capacity's unit (7.2.3). | F |
| 6.3.6 | An end-to-end figure that charges the index scan the layout cannot remove. | NF |
| 6.3.7 | Per-query skipping margin against ρ, flagging any query that would have been cheaper as a plain full scan. | NF |
| 6.3.8 | **Activated volume in both denominations** — the record count and the byte weight of everything the activated containers hold, summed over queries. A layout can activate fewer records and more bytes, or the reverse, so both are reported and neither is derived from the other at read time. 12.4.6.1 plots them as two halves of one comparison. | F |

---

## 7. Extensibility interfaces

### 7.1 Assignment strategy plugin

| # | Requirement | Type |
| --- | --- | :-: |
| 7.1.1 | A strategy is a registered callable taking a read-only view and returning **one container id per event and nothing else**. | F |
| 7.1.2 | The view exposes every feature and blob size column for every event, the supports of training queries only, the training query ids and times, and the swept parameter. Columns are reached by **dynamic name key**, never by an attribute the harness declares per column, so a strategy can be written against a corpus this project has never seen. | F |
| 7.1.2.2 | Blob size columns are exposed **separately from features**, not merged into them, so a strategy that partitions on every feature does not silently begin partitioning on byte counts. The summed totals remain available alongside. | F |
| 7.1.2.3 | `brand_id` is visible to strategies and may be partitioned on, and the two shipped kinds divide on whether they use it. A **baseline** must not read `brand_id` nor any other feature. This constrains what a baseline *reads*, not what its layout is worth: on a corpus that accumulates in time (5.3) arrival order carries the recency gradient, so `insertion_order` represents the **industry-default age-ordered layout** rather than a neutral floor, and a candidate is judged against that. A **demonstration family** (7.1.7) may read features, and is labelled a fixture, never a result. | F |
| 7.1.3 | The harness never inspects what a strategy does. It validates totality, compacts ids to a dense range, and evaluates. | F |
| 7.1.4 | Registration is by decorator into a registry exposing `register` / `get` / `available` — the same shape as the provider seam. | NF |
| 7.1.5 | Shipped strategies exist only to give the harness something to run; they are neither research nor recommendation, and are deterministic so any change in a reported number came from the corpus or the evaluator. The pair spans **floor to industry default** — `random_order` is the layout with no structure at all, `insertion_order` is what a system with no layout policy produces, which on a time-accumulating corpus is the age-ordered default most storage systems apply. A candidate is read against the latter; measurable advantage over it is the result the project is framed to detect. | F |
| 7.1.5.1 | The `insertion_order` baseline **exposes a `route` (7.1.6)**: with `record_id` an arrival sequence (4.2), an event's container is `record_id // capacity`, a function of that event alone. It is the seam's first instance and what makes write-time assignability (3.4.3) a demonstrated property rather than a stated one. | F |
| 7.1.6 | An optional `route(features) -> container_id` callable, verified by the harness against a sample, so that write-time assignability (3.4.3) becomes checkable. | F |
| 7.1.7 | A strategy may register a **parameter schema** alongside itself: an ordered list of parameter specs, each carrying a name, a human label, a type, whether it is required, a default where one exists, and its admissible values. A strategy that declares nothing is a valid strategy with no parameters. | F |
| 7.1.7.1 | The schema is **declarative data, not code**: serializable, and renderable as a form by a caller that never imports the strategy. This is what keeps 7.1.3 true while still letting a UI configure a strategy it has never seen. | F |
| 7.1.7.2 | A parameter whose admissible values are a corpus's column names is declared as such and **resolved against the loaded dataset**, never enumerated in the strategy's source, honouring 4.3. The A.S. family (12.4.1.1) resolves its expressions against the manifest's column summary (4.12). | F |
| 7.1.7.3 | Two parameter kinds carry a **variable-length value** and declare their own bound — a set of column expressions, and a bounded list of integers, at most four of each. The bound is a property of the parameter and not of any surface that renders it, so a caller reading only the schema still learns it. | F |
| 7.1.8 | A **strategy factory** turns *(strategy name, parameter mapping)* into a runnable strategy. It validates the mapping against the schema — rejecting unknown names, missing required values, and values outside the declared domain — and reports every violation at once rather than the first. A strategy is never invoked with parameters that failed validation. | F |
| 7.1.8.1 | A violation is **addressed, not merely described**: it carries the position that produced it — the index within a variable-length parameter, and the caller's own identifier for the candidate at fault. "Unknown column" without a position is not actionable when a request carries sixteen expressions. | F |
| 7.1.9 | The registry can enumerate what it holds as **structured metadata** — name, label, one-line description, kind (`baseline` or `demonstration`), and schema — so a caller can build a selector without a hardcoded list. This is the provider seam's `available()` widened, not a second registry. | F |

### 7.2 Other seams

| # | Requirement | Type |
| --- | --- | :-: |
| 7.2.1 | The management cost model is a registered plugin, replaceable — including with a currency model — without touching another module. | F |
| 7.2.2 | Management cost charges per-container bookkeeping, fragmentation, and rebuild volume, in abstract units with configurable weights. It is the **simulator's own construct**, not the formulation's; results plotted against it are not claims about the formulated problem. | F |
| 7.2.3 | Sweep configuration names the swept variable and its values; the variable is configurable and container size is only the default. | F |
| 7.2.3.1 | The default swept variable is a container capacity **in records**, not in bytes — the unit the bucketer actually uses, which removes a conversion and with it the corpus-dependent surprise of one target producing different container sizes on different corpora. Byte figures survive undiminished as **measures**; only the sweep axis re-denominates. | F |
| 7.2.4 | One primitive operation — *(dataset, strategy, parameters) → metric rows* — underlies sweeps, comparison, and charts. | NF |

---

## 8. Benchmarking and reporting

| # | Requirement | Type |
| --- | --- | :-: |
| 8.1 | A sweep runner executes a strategy across a parameter range and appends to a metric table. | F |
| 8.2 | The metric table is **append-only**, one row per *(strategy, parameters, set)*, with no database and no locking. Rows are never updated or deleted. | F |
| 8.3 | Every row carries dataset id, run id, timestamp, parameters, and a flag marking any run that saw hidden columns. | F |
| 8.3.1 | Every row also carries a **batch id**: the identity of the *request* that produced it, where the run id identifies one evaluation within that request. Without it, twenty rows landing at one timestamp are twenty unrelated runs to anyone reading the table, and the comparison they were produced for cannot be recovered. | F |
| 8.4 | A chart is drawn from the **metric rows of the evaluation that produced them**, in the same invocation; the table is written alongside as the durable record, never re-read to render a figure. This governs the generated report (8.5); the GUI reaches the same rows by its own route (12.4.3.5). | NF |
| 8.5 | Three chart types: skipping against management cost (scatter), skipping against container size (sweep line), skipping against query position (period line). | F |
| 8.6 | Bounded ratios are plotted on a linear 0–1 axis against their ceiling, never log — a strategy that skips nothing must be drawable. | NF |
| 8.7 | The period chart reports no slope and assumes no shape; only the *comparison* between strategies under one fixed query sequence is meaningful. | NF |
| 8.8 | Charts render in light and dark variants, wrapped in a minimal report page carrying title, dataset id, run timestamp, and one title per chart. No prose. The GUI's benchmark report (12.4.3) is a separate surface. | F |
| 8.9 | A CLI drives generation and running, including a reduced-size mode for fast iteration. The CLI is **the only entry point that evaluates a strategy**: the GUI presents what 8.11 computed ahead of time and calls 7.2.4 never. Scoring an arbitrary group-by chain against an arbitrary capacity therefore remains fully available, and remains available *here*. The default invocation, with no subcommand, is an **interactive control plane** (8.9.1) that reaches every operation the CLI already offers. Direct subcommands remain for scripts, CI, and a deployed instance. | F |
| 8.9.1 | **`python -m simulator` with no subcommand opens a numbered menu** when stdin is a terminal. The menu exposes generate, catalog build, the benchmark report, exhibit launch, stop, restart, status, and an atomic **Build & Launch** that finishes the catalog before it may stop or replace a running exhibit. Direct subcommands stay callable and do the same work. With no subcommand and no terminal the command **exits non-zero and names the subcommands**, rather than blocking. Status and stop trust the signed health response (12.2.9), never the mere existence of a listener. | F |
| 8.10 | A **catalogued** evaluation is **the same primitive operation** as a swept one and produces **rows of the same schema**, carrying the same run and batch ids. What differs is where they go: a sweep appends to the metric table, a catalog build writes them into the document 8.11.1 describes. A number shown in the GUI and a number printed by the CLI mean the same thing because 7.2.4 computed both. | F |
| 8.11 | A **catalog generator** turns a *catalog definition* — an ordered list of candidates, each a label, a group-by chain and a capacity sweep — into one **catalog document**. It is a **standalone module driven by the CLI**, runs offline against a loaded corpus, and is never reachable from a serving process. It computes nothing of its own: every figure it emits comes from 7.2.4's primitive, exactly as a sweep's does. | F |
| 8.11.1 | The document carries, in one file: the **corpus provenance** (dataset id, event and query counts, and the manifest's feature-column summary, 4.12); the **candidate entries**, each with its canonical chain, its per-stage split counts (8.11.2) and its capacity sweep; the **baseline** and the capacities it was swept across; and the **metric rows themselves, in `run_one`'s complete schema**. The rows are complete rather than reduced to what any one surface reads: a trimmed row is a third schema to hold level with two others, and 8.10's guarantee is that there is only one. | F |
| 8.11.2 | A group-by family reports the **structure of the split it produces** — for the chain family, the count of distinct groups the corpus stands in after **each prefix** of the chain. It is produced by the family, which is the only thing that knows how a chain divides a corpus, and never by a surface that displays it (12.2.5). It is a property of the chain alone and carries no capacity, so one figure describes a candidate across its whole sweep. | F |
| 8.11.3 | Catalog entries are chosen to **span a structural range** — chain length, split granularity, and the column families a corpus offers — and are ordered by a **structural property, never by score**. The catalog is a fixture set (7.1.2.3, 1.2), and a list sorted best-first is a recommendation whatever text sits above it. What is excluded is a *ranked* catalog, not a measured one: the scores are shown, they just do not decide the order. | F |

---

## 9. Explainer visualization

| # | Requirement | Type |
| --- | --- | :-: |
| 9.1 | A single committed scenario file is the source of truth for every explainer figure that states a quantity, and for the interactive canvas. No such figure hard-codes a number. A figure stating no quantity at all — 9.15 — is outside this rule rather than an exception to it. | F |
| 9.2 | The centrepiece figure is a selection matrix: events as rows grouped into containers, queries as columns, shown under two layouts so the reader sees that only the grouping differs. | F |
| 9.3 | Cell states are **needed / wasted / skipped**, encoded by colour *and* by fill (solid, striped, empty) so the figure survives colour-blindness, greyscale print, and forced-colours. | NF |
| 9.4 | Data colours are validated against both surfaces for lightness band, chroma, CVD separation, and contrast before use. | NF |
| 9.5 | A zoom figure showing the two outcomes available to any container: one activated, with selected and wasted items distinguished; one bypassed, holding nothing selected. | F |
| 9.6 | A tabular view of the index — one row per event, showing features, container, and record id — with the rows matching a chosen query marked. | F |
| 9.7 | Figures are generated by a script, emitted as light and dark pairs, and embedded so a Markdown host switches between them by theme. Generated figures are never hand-edited. | F |
| 9.8 | An interactive canvas lets a reader move an event between containers and see waste recount live, focus a single query, and read the log and index the numbers derive from. Every number it displays comes from the same scenario data as the figures, and must agree with them. | F |
| 9.10 | The canvas is self-contained — no external fonts, scripts, or network access — and renders correctly in light, dark, and unstamped-system themes. | NF |
| 9.11 | Explainer assets illustrate; they are not test fixtures, and the simulator does not load them. | NF |
| 9.12 | The interactive canvas (9.8) survives the GUI and is reachable from it. The GUI's Section A carries a **static** illustration; the canvas is not reimplemented inside the page. | F |
| 9.13 | An **architecture canvas** shows the simulator's components and the data flowing between them, with simulation input and output rendered as data blocks distinct from the code that consumes them. Its purpose is to make two structural lines legible: the **contract line**, above which providers write and below which nothing names a provider's column, and the **layout line**, above which the corpus is invariant and below which it is re-scored once per sweep point. Every component is labelled with its module path and every count it states is derivable, so the diagram can be checked rather than believed; a component specified but not built is marked as such and never drawn as though it exists. | F |
| 9.15 | A **page-anatomy figure** shows the served page's structure: the navigation, the four sections in order, the panes each carries, and the benchmark report's three views. It states no scenario quantity. Its section and navigation labels are the page's own, and a test holds the two in step so the figure cannot drift from what is served. | F |
| 9.16 | Embedded graphical HTML — pane fragments and standalone canvases — is stored under `resources/graphics/` and served through `/figures/`. A pane fragment is named `section-<letter>-illustration.html`, where `<letter>` is the section it mounts into. A standalone canvas is named `*-canvas.html`. `simulator/gui/static/` holds the application shell, styles, scripts, and pre-rendered documents only. Generated figure pairs stay in `resources/img/`. | F |

---

## 10. Engineering and quality

### 10.1 Correctness

| # | Requirement | Type |
| --- | --- | :-: |
| 10.1.3 | **No runtime sidecar**: nothing ships inside `simulator/` whose only purpose is to check other code — no shadow mode, no debug-only parallel path, no self-verifying wrapper. | NF |
| 10.1.4 | Correctness is anchored on properties derivable **without running the evaluator** — the all-in-one-container closed form, zero waste at one container per event, refinement monotonicity — and on invariants holding for any input, among them that training and validation waste sum to total, that materialized ≥ selected per query, and that every event lands in exactly one container. These constrain the extremes and the invariants, not every interior layout, and the exposure is accepted and stated rather than hidden. | F |
| 10.1.5 | **No redundant cases.** Before adding a unit test, check the existing suite for a case that already asserts the same behaviour. Do not add a second case that repeats an existing assertion under a different name, fixture, or file. | NF |

### 10.2 Performance and footprint

| # | Requirement | Type |
| --- | --- | :-: |
| 10.2.1 | A full load, sweep, and report completes in seconds on a laptop, within a single-digit-GB memory guideline. The guideline is met by choosing event and query counts, not by enforcing a runtime limit; runtime and peak memory are printed alongside a run rather than asserted, so drift is a signal and not a build failure. | NF |
| 10.2.3 | Corpus parsing uses a multithreaded CSV reader; the derived support is memory-mapped rather than re-parsed on every run. | NF |

### 10.3 Stack and dependencies

| # | Requirement | Type |
| --- | --- | :-: |
| 10.3.1 | Python in a managed virtualenv, and **two dependency sets that do not overlap**. The **harness** — numpy, pyarrow, matplotlib — is what generates a corpus, scores a layout and renders a report. The **exhibit** is a **named minimal ASGI stack**: FastAPI on uvicorn, and nothing else. Neither set may acquire the other's packages, and there is **no template engine** in either. **The split is a requirement rather than a packaging convenience:** the serving process presents pre-computed figures (8.11) and has no scoring to do, so shipping it a numeric stack would install libraries that exist only to perform an operation the process is forbidden to perform (12.2.5). Keeping them out is what makes that prohibition structural rather than a matter of discipline, and it is what a 24/7 public instance installs, patches and has audited. **The reason both lists are short is where this runs:** a demonstration is opened on someone else's machine, from a clean checkout, minutes before it is needed, and every added dependency is one more way that fails in front of an audience. The ASGI stack is admitted because the GUI is also a **deployed service** (10.3.12), where routing, path containment and static serving are work the standard library would leave hand-rolled at exactly the seam that faces the network. The browser side is unaffected: 10.3.5 still admits no third-party asset and no build step. | NF |
| 10.3.2 | **No database and no query engine.** Persistence is CSV, one derived `.npy`, and numpy arrays. The data is immutable columnar arrays read whole and scored in bulk, which is the shape numpy is fastest at and the shape SQL would add a planning layer over for no gain; and a database is a service to install, start and version, which 10.3.1 has already ruled out of a demonstration's setup. The GUI holds no store of its own — it reads one catalog document (8.11.1), and keeps no session state that survives a reload. | NF |
| 10.3.3 | The retained **SVG** generator for explainer assets has no third-party dependency and runs on a system Python, because those generated pairs must stay regenerable years from now on any machine with Python. Raster-production scripts are temporary authoring tools: after their PNGs pass visual review and are committed, the scripts and private drawing helpers may be removed while the prompt and accepted PNG remain. Those finalized rasters are intentionally not reproducible from the repository. | NF |
| 10.3.4 | Data formats stay inspectable and diffable, accepting size cost to do so. This puts a practical ceiling on any committed corpus. | NF |
| 10.3.5 | The browser side ships **no third-party JavaScript, CSS, font, or icon set**, and there is **no build step** — no bundler, no transpiler, no `node_modules`. What is authored is what is served, which is what makes 12.2.2 checkable by reading the file. | NF |
| 10.3.6 | Tooling needed only to *produce* a committed artifact may take dependencies the runtime does not. It is declared as an optional dependency group, is absent from the default install, and nothing under `simulator/` imports it. | NF |
| 10.3.7 | Every run writes an **execution log**: events and errors to stdout, and the same records to one file per run, named so the directory sorts into the order things happened. The file is a **tee, not a replacement** — the command is one a reader is watching, and moving errors somewhere they must go looking would make a failed demonstration harder to read. **A managed background exhibit is the exception**: its complete output — printed lines and logger records — is written to one named run file that the control plane reports, because there is no foreground terminal to watch. **Interface is not a record**: a prompt, a status line, the served URL and the dataset summary stay on stdout as themselves. Run files are **not pruned, rotated, or capped** — the directory is disposable, and deleting it is the whole retention policy — but a name is never reused, because losing records is the one outcome worse than keeping too many. | F |
| 10.3.7.2 | Records carry **no reader-supplied content** — not a request body, not an expression, not a block name. Identifiers and counts stand in. This keeps 12.2.7.1's rule that operational state is never a channel between readers, and it disposes of log injection by having nothing to inject into rather than by escaping. | NF |
| 10.3.8 | Dependencies are **resolved and locked, and the lock is committed**. Runtime packages carry open-ended lower bounds, so without a lock two checkouts install differently and a demonstration fails where it cannot be debugged. | NF |
| 10.3.9 | **Every tool a documented command needs is a declared dependency**, in a group that command's instructions name. A documented command that cannot run after the documented install is a defect of the packaging, not of the reader. Under 10.3.1's split this binds hardest on the commands that need the harness: `generate`, `run`, the catalog build, and the menu actions that invoke them name the group that carries it, and a command invoked without that group **fails saying which group supplies it** rather than raising an import error naming a package the reader never asked for. Launch, stop, restart and status need only the exhibit set. | NF |
| 10.3.10 | **A committed generated artifact is versioned, and no ignore rule names it.** An ignore rule written for one directory that also matches one of these removes it from the repository silently: every test reading it off the working tree still passes, because the author's disk still has it. So the set is enumerated and checked, rather than recorded as a comment beside the rule. | NF |
| 10.3.11 | **A committed generated artifact whose generator is retained is current with respect to that generator.** Editing a source or generator without rerunning it leaves the repository shipping the older output, and tests reading the committed copy remain self-consistent and wrong. Currency is asserted by running the shipped generator and comparing, never by a second implementation. Finalized raster PNGs whose temporary production tools were removed under 10.3.3 are fixed, visually reviewed assets and are outside this generator-currency check. | NF |
| 10.3.12 | The product ships a **container image definition** as a deployment artifact. **One worker process**, because the catalog document is held in memory for the process's life (12.2.3) and a second worker would duplicate it to serve the same immutable data. **Bind address, port and mount prefix are supplied by the environment**, so one image serves the local demonstration and the public instance with no second code path. **The image carries no corpus and no harness** (10.3.1): what it needs to answer every request it can receive is the catalog document and the static page. | NF |
| 10.3.12.1 | **The corpus never enters the image.** It is a versioned external asset, identified by the dataset id its configuration hashes to (4.10), and it is read by the catalog build (8.11) and by nothing else. The catalog document is therefore a **build input**: produced by a recompute job when the corpus version or the metric schema changes, and consumed by the image build as a file. Recompute and image build are different cadences, and coupling them would pay a full corpus fetch and score on every deploy, restart and crash recovery — plausibly past the platform's own readiness deadline. An absent catalog **fails the image build** rather than producing an instance that serves an empty Section B. Serves 10.3.12. | NF |

---

## 11. Deliberately not required

Recorded so their absence reads as a decision rather than an omission.

| # | Item | Why |
| --- | --- | --- |
| 11.1 | Any assignment strategy offered as a product answer | 1.2 — the project frames and measures the problem; solving it is downstream work |
| 11.2 | Index design of any kind — description language, size, selectivity, maintenance, scan avoidance | Delegated by the formulation. The attachment points are a descriptor field on the layout, a pre-scan mode on the evaluator, and an index-size term in the cost model |
| 11.3 | Rebuilding a layout over successive time periods | Reporting measures how one fixed layout fares as the workload moves; a *sequence* of layouts needs a period loop and a relocation cost model. The query sequence is already the time axis |
| 11.4 | Currency-denominated cost | The cost model is a plugin; swapping abstract units for provider pricing changes one module |
| 11.5 | Feature-clustering reward in the synthetic corpus | Features change the *rate* at which events are wanted, not the reachability of a container. Rewarding feature clustering needs predicates that are hard over features, which changes what the workload means |
| 11.6 | A separate split on the event table | The holdout lives entirely on the query side; cold events supply the write-time placement case without one |
| 11.7 | Statistical significance testing between strategies | 1.4 — results are indicative |
| 11.8 | Measurement against a real storage system | 1.3 — the simulator is logical, not physical |
| 11.9 | A reference or oracle implementation of the objective | 10.1.4 — the anchors constrain the extremes and the invariants, so no test cross-checks the objective on an arbitrary interior layout |
| 11.10 | A second, smaller dataset configuration for fast iteration | 5.1.1 — one corpus, one calibration |
| 11.11 | Requirements on the content of an authored document — what the README, the formal statement, the engine mapping or the term dictionary must contain — and rules on how the project's prose is written | A product specification states what the product must do; it is not a style guide, and it is not the editor of documents it does not build. Each document is its own authority, and `AGENTS.md` names them and what each is for. Rules governing the author rather than the artifact are supplied at user scope and belong to no project |
| 11.12 | Regenerating a chart from the metric table without rerunning the evaluation | 8.2 makes the table append-only, so a re-render would first have to choose *which* rows — a batch selector, and a rule for rows produced against different corpora or different code. That is report versioning, and nothing has asked for it |

Exclusions belonging to the GUI — authentication, remote deployment, a client-side framework,
persisted form state, corpus editing, run cancellation, hover as a required affordance on
controls, a dark theme, a schema-generated form over arbitrary strategy families, partial
success, automatic re-evaluation, within-leaf ordering, and searching for a chain — are recorded
in [`ui-spec.md`](ui-spec.md) §13.
