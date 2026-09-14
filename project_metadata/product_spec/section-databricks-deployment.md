# Go Live on Databricks Lakehouse

Product requirements for the Go Live on Databricks Lakehouse section of the
demonstration GUI: a seven-step engineering process that assembles knowledge
already tabled on the other sections into a Databricks Lakehouse
deployment, beside three figures. The left pane is the process. The right
pane is figures only.

**Authority.** This document is the product spec for this section.
[`simulator-spec.md`](simulator-spec.md) governs the application shell,
theme, and layout. [`section-gini-illustration.md`](section-gini-illustration.md)
governs split search. [`section-budget-illustration.md`](section-budget-illustration.md)
governs the multiple-choice knapsack allocation. Where this document and
the simulator product spec disagree on shell, theme, or layout, the
simulator product spec wins. Where they disagree on this section's
content, this document wins.

**No recommendation.** The process names a beam of candidate trees, a
partition-limit prune, a simplified equal-size holdout, a bottom-layer
ingestion-time split, bucketed `OPTIMIZE` without Z-order, and a two-tier
ingest path as process guidelines. It may say that MCKP ranking on a
training set often fails to transfer. The write path packs each grouping
into approximately capacity-`T` partitions by the tracker method in §2.5.
That method is the ingest realization. The page does not rank MCKP,
equal-size, or the tracker as the shipped assignment, and it does not pick
a time grain.

**Shipped pane.** The right pane is the three titled figures, drawn and
served. The obsolete rasters are gone. Each figure is authored in draw.io
from its retained prompt and exported to PNG. The left pane cites the
three figure titles and states the process in §2.

---

## 1. Role and reading order

Go Live on Databricks Lakehouse introduces one engineering process: deploy a
customized data layout for high-value queries by assembling knowledge
already tabled on the other sections into a solution that can run on a
Databricks Lakehouse.

The process has seven steps, in this order:

1. **Collect query usage statistics.** Build `usage_summary` from
   per-query-per-row boolean flags and name the tradeoff of aggregating
   those flags into time bins. The query-path collector in §2.6 writes
   this store.
2. **Optimize split decision trees.** Grow trees from training samples
   with the techniques in Measuring Data Layout Fitness, under a resource
   monitor and a complexity bound, keep a beam of candidates, and project
   the table partition limit onto stop and prune. On a retry the search
   also reads heuristics of unqualified split conditions.
3. **Optimistic knapsack simulation.** Set the Delta partition limit as
   the global container budget, run MCKP on every beam candidate, keep an
   ingestion-time dimension in the bottom split layer, and describe an
   overlay chart on a log container-count axis. That overlay may sit on
   Figure 1 as a panel on the MCKP spend node.
4. **Experiment simplified assignment on holdout.** Apply the beam and a
   global equal-size container policy to holdout samples, then inspect the
   estimated weighted-average data skipping ratio. Holdout is a gate. A
   passing tree freezes for ingest. A failing tree writes those heuristics
   and returns to §2.2.
5. **Deploy container assignment during Ingestion.** Land the stream in
   `streaming_sink`, then run a CRON-driven consistency checker and a
   specialized writer that splits, allocates, and fans out to the index,
   the tracker, and `partitioned_sink`. Point at §2.7 for consolidation.
6. **Activate data skipping optimization.** Map container-skipping onto
   the Spark activation path: index scan, driver broadcast, worker fetch
   from the event table, durable query output, then the usage statistics
   collector that writes `usage_summary`.
7. **Hybrid table architecture and continuous consolidation.** Name
   `streaming_sink` as the landing copy and `partitioned_sink` as the
   containerized event store. The same CRON fires an optimizer that
   rewrites `partitioned_sink` to one file per partition, without
   Z-order. One schema may sit on complementary layouts.

- The process sits on the **left**. The figures sit on the **right**.
- Below the split breakpoint the panes stack in that order.
- Each pane is independently scrollable on a wide viewport.
- The left sequence cites other sections by their reader-facing names. It
  does not reprint those walkthroughs. The three figures draw §2.1–§2.4,
  §2.5 with §2.7, and §2.6. Figures add no measured engine number.

The left pane is an authored walkthrough of this process. Figure titles
on that pane match the right pane.

---

## 2. Left pane: the go-live process

An opening paragraph before §2.1 hinges from exercised container
assignment: the solution can be deployed to a production data lake such as
Databricks. It takes knowledge already on Problem Statement, Measuring
Data Layout Fitness, and Drawing Storage Boundary and maps that knowledge
onto a Lakehouse write path and a Spark read path. It names the figure
*Deployment Process Flow*.

Seven sections follow, with the titles below.

### 2.1 Collect query usage statistics

The first move is to persist `usage_summary`. Each cell is a boolean flag
for one query and one row: whether that query selected that row. The table
is the wide boolean view of the same history as the two-column selection
log (`record_id`, `query_id`) in simulator-spec 3.1.1. It is the same
corpus, aggregated.

The usage statistics collector on the §2.6 query path writes this store.
Figure 3 draws that write. Figure 1 reads the same named store.

Databricks `system.query.history` records predicates, not selected rows,
so the table is constructed by replay, instrumentation, or sampling
(production-design §6). Aggregating those per-instance flags into time
bins (minute, hour, or date) is an engineering tradeoff: coarser bins
shrink the table and lose resolution.

The analysis on that table is a screening estimate. The benchmark harness
reports exact workload replay. The section does not invent a currency
conversion, a DBU formula, or a stop-rule constant.

### 2.2 Optimize split decision trees

This section uses the techniques introduced in Measuring Data Layout
Fitness to grow split decision trees from **training** samples. The
search needs a resource monitor and a complexity bound. Keep a beam of
candidates so holdout sees several competing trees.

Delta Lake and Iceberg cannot host hundreds of millions of table
partitions. Each leaf occupies at least one table partition, so project
the table's partition limit onto the search stop and prune tests.

When holdout in §2.4 fails, the fail edge writes heuristics of the
unqualified split conditions (the cuts or predicates that did not
transfer). Search then reads those heuristics and skips those
conditions on the next pass.
The inner list, score, and replace cycle stays on Measuring Data Layout
Fitness.

The section cites Measuring Data Layout Fitness by that name. It does not
reprint that walkthrough's recurrences or fitness formulas. It does not
rank search methods.

### 2.3 Optimistic knapsack simulation

This section applies the Multiple-Choice Knapsack Problem introduced in
Drawing Storage Boundary. The first mention of the multiple-choice
knapsack problem links to
[the same external definition](https://en.wikipedia.org/wiki/List_of_knapsack_problems#Multiple-choice_knapsack_problem)
Drawing Storage Boundary uses.

Set the Delta Lake table partition limit as the global container budget.
Run MCKP on every beam candidate from §2.2. MCKP starts at one container
per leaf and spends the budget piecemeal, so estimated skipping ratio and
marginal efficiency appear at each iteration.

Describe an overlay chart on a log container-count axis that continues
past the limit. The chart compares table metadata overhead with skipping
performance and shows what a more granular store could still buy. The
chart may sit on Figure 1 as a panel on the MCKP spend node. Drawing
Storage Boundary keeps the ladders.

Keep an ingestion-time dimension (examples: minute, hour, day, month) in
the bottom split layer. Age commonly tracks usage frequency across
industries, so the last cut should leave that grain on the leaf. The
section does not pick one time grain as the shipped rule.

The estimate is the static leaf benefit of that page. It is not a live
engine number. The section does not reprint Drawing Storage Boundary's
ladders, guardrails, or greedy scan.

### 2.4 Experiment simplified assignment on holdout

MCKP is a maximum-potential analysis on a static dataset. Relative
marginal-efficiency ranking on training can move a long way on a forward
stream, so that ranking is not a pattern to copy onto live data. Holdout
applies the beam from §2.2 and a simplified assignment that ignores the
ranking and enforces one global equal-size container policy.

Set container capacity from the observed compressed record size so the
files are fragmented micro-partitions (example: at least 8 MB on AWS S3),
still inside the global table-partition overhead.

The reader inspects the estimated weighted-average data skipping ratio on
the holdout. That quantity is the check that a training tree transfers.
Holdout is a gate. If the tree transfers, it freezes for ingest
(`tree_frozen`, the input to Figure 2's data splitter). If it does not,
the fail path writes the unqualified-split heuristics of §2.2 and returns
to search.

The section does not treat the ratio as aggregate waste, and it does not
claim a measured engine result.

### 2.5 Deploy container assignment during Ingestion

This section maps the layout onto the write path of a Databricks
Lakehouse. The figure *Ingestion Time Integration*
is the landing path, the writer assembly, and the fan-out. The tracker
method that assigns `partition_id` is stated here; it is not a fourth
figure and no figure prints the `V` / `T` arithmetic. Presentation order
is landing, then the schemas and tracker, then the writer. The section
does not use the label *process concept*.

A transient brand-sales stream is persisted into `streaming_sink` by
Spark Structured Streaming / Auto Loader and a stream writer. That
landing table does not apply the tree-split layout.

One CRON scheduler fires a consistency checker. The checker reads a
custom checkpoint table that records a write-ahead log so a multi-table
write can be idempotent; Delta Lake does not provide that for this
fan-out. The checker may clean partial ingest state, then launches the
specialized writer. The checkpoint sits beside the checker. The launch
edge runs from the checker into the splitter.

The specialized writer is one assembly line: a data splitter reads
`streaming_sink` and the frozen tree from §2.4; a container allocator
reads the tracker and finalizes `partition_id`; a fan-out writes the
narrow index, the tracker, and `partitioned_sink`, then appends a WAL
commit.

An introduction, then three abstracted schemas:

| schema | Databricks realization |
| --- | --- |
| split decision | a grouping or a predicate |
| container assignment | Delta Lake partition assignment (`partition_id`) |
| feature index and events | a narrow Delta table and a wide Delta event table (`partitioned_sink`) |

On each arriving batch (a micro-batch when the stream is incremental),
Spark applies a conditional group-by expression built from the custom
layout decision tree in §2.2. That cut divides the batch into logical
groupings. The brand-sales example groups by `brand_id` and
`pricing_tier`.

A **stateful assignment tracker** is a dedicated table with one row per
logical grouping. It records container fill so the job can assign
`partition_id` without a partition-sort. The bucket-hash-assign is an
approximation: collisions are accepted. A short definition table
introduces the columns at the moment they are used:

| term | symbol | meaning |
| --- | --- | --- |
| grouping identity key | — | the grouping the tree produced |
| container sequence number | `k` | monotonic per grouping, starting at 1 |
| filled count | `s_1` | records already in the one partial container |
| container capacity | `T` | target records per container |
| batch size | `N` | records in this batch for that grouping |
| virtual slot | `V` | the hashed address in `[s_1, s_1 + N)` |

A grouping has only one partially filled container. Every earlier
container in that grouping is full. A partition is identified by its
grouping key and its sequence number.

The job maps the batch onto virtual slots, then reads a sequence number
from the slot. Let the tracker's current sequence be `k` and its filled
count be `s_1` (`s_1 < T`). For each record:

```
V = s_1 + pmod(xxhash64(identity), N)
seq = k + floor(V / T)
```

Identity is the record identity columns. `xxhash64` and `pmod` are the
Spark SQL functions; the first mention names them as such. Two records
may share a `V`; that collision is accepted, so a container's achieved
size may miss `T`.

The grouped, assigned stream is written to two destinations:

1. a **narrow index table** of query-predicate features plus
   `partition_id`;
2. a **wide event table** (`partitioned_sink`) of the full attributes plus
   `partition_id` plus `record_id`.

The index written here has no `record_id` and no non-predicate attribute,
because the §2.6 prescan only collects `partition_id` values.

Continuous ingest into a micro-partition layout creates fragmented new
file objects. Left unattended, tens of millions of small files overwhelm
the catalog metadata system. §2.7 states the detailed solution.

The section does not rank this packing against MCKP, print a skip
ratio, or describe the read path.

### 2.6 Activate data skipping optimization

This section maps container-skipping onto the read path. The figure
*Query Time Integration* is the Spark path:
index scan, driver activation, worker fetch, durable output, then the
usage collector. Tables on that figure are schema only. The section does
not use the label *process concept*.

Spark Dynamic Partition Pruning (DPP) is the out-of-the-box optimization
that realizes granular container skipping. A multi-select query prescans
the narrow index and computes the set of matching `partition_id` values.
Spark DPP broadcasts that set to each Databricks worker as a metadata
filter. Each worker fetches only the activated containers from
`partitioned_sink` (labelled event table on Figure 3) and writes a
durable query result. The usage statistics collector reads that result
and persists aggregated `usage_summary`.

Two conditions:

1. a large driver node to run DPP over millions of internal
   partition-metadata records (example: AWS rgd series, at least 256 GB);
2. a high broadcast threshold (example: 256 MB) so the adaptive query
   planner can inject a broadcast partition filter into the target table
   scan.

The first mention of that threshold is a weblink to
[Spark config: autoBroadcastJoinThreshold](https://spark.apache.org/docs/latest/sql-performance-tuning.html).
The first mention of Dynamic Partition Pruning names it as a Spark
mechanism. The index schema remains the narrow one in §2.5. The section
does not invent a second index, open the event table during the prescan,
or treat a downloaded partition as selected rows. Activation stays at
partition grain. The figure does not rehearse that grain with sample
rows.

### 2.7 Hybrid table architecture and continuous consolidation

`streaming_sink` is the landing copy. `partitioned_sink` is the
containerized event store downstream of that landing.

The same CRON that fires the consistency checker also fires an optimizer.
The optimizer reads `partitioned_sink` and writes it back so each
partition stays one file. It does not apply Z-order and it does not run
the fan-out again.

Do not run one `OPTIMIZE` over the whole table as a single Delta
transaction; that commit is prone to concurrency failures. Bucket
millions of partitions into tasks so disjoint subsets optimize in
parallel and each subset commits on its own, non-conflicting transaction.

For streaming ingest, split on ingestion time. The landing tier takes the
high-frequency stream and does not apply the tree-split layout; that
layout makes small-file fragmentation worse. The specialized writer
periodically copies from the landing at a frequency that can tolerate
granular containerization. Recent rows stay in the unoptimized tier. The
pattern spends maintenance where skipping coverage is worth it.

Rows that share a schema need not share one storage strategy.
Complementary layouts, and different engines or hardware under them, can
sit behind one user-facing table.

---

## 3. Medium and visual system

The right pane is one authored fragment. The three figures share one
visual system, recorded in the prompts:

- flat editorial drawing, not photorealism, 3D, or a screenshot;
- the warm paper ground and ink of the UI tokens (explainer family:
  wine-red `#7A1F2B`, sage `#1B4D3E`, paper `#FCFCFB`);
- Helvetica for labels, Courier New for identifiers;
- one restrained repeating palette;
- dashed outline for a skipped, empty, transient, or carried slot;
- text, shape, outline, or pattern in addition to colour for every state.

The retained prompts are the authority on figure content. Each figure is
a `.drawio` source and a PNG export of it. This document does not require
a pixel size. No figure contains UI chrome or server racks. Diagrams fetch
nothing to render. Every illustration carries a **visible title**, printed by
the right pane above the figure stage; a figure does not draw that title
inside itself. No figure prints a term from the dataset example used
elsewhere in the project — a figure states the shape of a schema, and the
concrete example stays in the left-pane prose. No figure asserts a measured engine number.

---

## 4. Right pane: three figures

Exactly three figures, in walkthrough order. Prompts are the retained
specification. The served pane is those three figures, each a PNG export
of its `.drawio` source. No pane references a missing file.

| id | Visible title | Walkthrough section | Prompt |
| --- | --- | --- | --- |
| `databricks.layout-planning` | *Deployment Process Flow* | §2.1–§2.4 | [`resources/img_prompt/section_databricks_layout_planning_prompt.md`](../../resources/img_prompt/section_databricks_layout_planning_prompt.md) |
| `databricks.ingestion` | *Ingestion Time Integration* | §2.5 and §2.7 | [`resources/img_prompt/section_databricks_ingestion_prompt.md`](../../resources/img_prompt/section_databricks_ingestion_prompt.md) |
| `databricks.query` | *Query Time Integration* | §2.6 | [`resources/img_prompt/section_databricks_query_prompt.md`](../../resources/img_prompt/section_databricks_query_prompt.md) |

Each figure carries a one-line caption naming its construction, and an
alt text describing what the drawing shows. The pane's heading above the
stage carries the figure's title; **no figure draws that title inside
itself**. Shared component ids
(`usage_summary`, `tree_frozen`, `index_table`, `partitioned_sink`) are
minted once and copied; a later pass does not regenerate them.

Each prompt specifies destination as the right pane, screen, light
background, page width, with no raster resolution. A visual change starts
a new authoring pass from its prompt.

### 4.1 *Deployment Process Flow*

`usage_summary` feeds a bounded beam search (resource monitor, complexity
bound, partition-limit prune). Two candidate trees sit inside the search
group as labelled cards. The beam goes to an MCKP spend, which carries a
log-axis overlay panel with a tick at the partition limit, and to an
equal-size holdout. Holdout is a check. A decision gate after holdout
either emits the frozen tree or writes unqualified-split heuristics and
returns to search. There is no self-loop on search. There is no `V` / `T`
formula.

### 4.2 *Ingestion Time Integration*

Three rails. Top: transient stream, Spark Structured Streaming / Auto
Loader, stream writer, persisted `streaming_sink`. Middle: one CRON
fires a consistency checker that cycles with a custom checkpoint WAL,
then launches a specialized writer (data splitter, container allocator,
fan-out) into `index_table`, `container_tracker`, and
`partitioned_sink`, then a WAL commit. Bottom: the same CRON fires an
optimizer that reads `partitioned_sink` and writes it back (`compact`),
one file per partition, no Z-order. Tables are schema only. The
allocator prints a finalized `partition_id` and does not print the
tracker arithmetic.

### 4.3 *Query Time Integration*

Left: `index_table`, schema only, full table scanned. Middle: a
cluster frame, dashed vertical split, about 60% driver and 40%
workers (one driver, `w1` and `w2`). Right: `partitioned_sink` labelled
event table, schema only. Workers fetch activated containers from that
table and write a durable `query_output`. A usage statistics
collector reads that output and persists `usage_summary`. Activation is
labelled edges (scan, activate, fetch, write, persist). The figure has
no body rows and no download/skip glyphs on sample partitions.

### 4.4 Shared schema

Figures 2 and 3 share one schema for the two persisted tables. Figure 3
has no row instance. Figure 1 reads `usage_summary`; it does not invent a
second usage store. These figures are outside 12.6.4's catalog /
manifest / scenario trace.

```
index_columns = ["predicate_1", "predicate_2", "partition_id"]
partitioned_sink_columns = [
  "predicate_1", "predicate_2", "attribute_1", "attribute_2",
  "partition_id", "record_id",
]
```

The column names the figures print are placeholders. What the two schemas
have to carry is their shape: the index holds the query-predicate features
plus `partition_id` and nothing else, and the event table holds those plus
the remaining attributes plus `partition_id` and `record_id`. The
brand-sales column names of §2.5 stay in the left-pane prose, where a
reader meets them as an example.

A later figure may change only the relationship its prompt names.

---

## 5. Writing contract

The left pane is a technical process walkthrough. Each of §2.1–§2.7 is a
section with the title in §2. Conclusions fold into the last paragraph of
the section; there is no labeled takeaway and no heading *Concluding
insights*.

The left-pane rewrite follows
[`.claude/skills/humanizer/SKILL.md`](../../.claude/skills/humanizer/SKILL.md)
in file mode: active voice, no *teach*, no *presented / introduced*, no
*process concept* label. Do not patch flagged phrases one at a time.

The first mention of a public technical term is a weblink (MCKP as in
§2.3; Dynamic Partition Pruning as a Spark mechanism). The first mention
of the broadcast threshold uses the display text
`Spark config: autoBroadcastJoinThreshold` and links to
https://spark.apache.org/docs/latest/sql-performance-tuning.html.
`xxhash64` and `pmod` are named as Spark SQL functions at first mention.
Later emphasis uses the citation form *the concept description*
(`symbol`, defined in §X), naming the document when $X$ is not a
section of this walkthrough. The walkthrough refers to Measuring Data
Layout Fitness, Drawing Storage Boundary, and Problem Statement by those
names.
It refers to the three figures by the titles *Deployment Process Flow*,
*Ingestion Time Integration*, and *Query Time Integration*.
It contains no figure markup.

---

## 6. Requirements map

| id | requirement |
| --- | --- |
| I1 | Process on the left; figures on the right; that order when stacked |
| I5 | The three figures draw §2.1–§2.4, §2.5 with §2.7, and §2.6; they add no measured engine number |
| I10 | Formal terms stay the project's own vocabulary; state is not carried by colour alone |
| I11 | §2.4 states that MCKP is a static max-potential analysis whose training ranking often fails to transfer, and holdout uses a global equal-size policy; §2.5 states the tracker packing method as the ingest realization, not as a ranked planning strategy |
| I12 | An opening paragraph hinges from exercised container assignment, deploys the solution to a production data lake such as Databricks, maps knowledge already on Problem Statement, Measuring Data Layout Fitness, and Drawing Storage Boundary onto a Lakehouse write path and a Spark read path, and names *Deployment Process Flow* |
| I13 | The left pane is seven sections in this order: Collect query usage statistics; Optimize split decision trees; Optimistic knapsack simulation; Experiment simplified assignment on holdout; Deploy container assignment during Ingestion; Activate data skipping optimization; Hybrid table architecture and continuous consolidation |
| I14 | §2.1 persists `usage_summary` as a per-query-per-row boolean usage-statistics table, names the time-bin aggregation tradeoff, treats the analysis as a screening estimate, and states that the §2.6 collector writes the store |
| I15 | §2.2 grows split decision trees from training samples with Measuring Data Layout Fitness techniques, under a resource monitor and a complexity bound, keeps a beam of candidates, projects the table partition limit onto stop and prune, and on retry reads heuristics of unqualified split conditions |
| I16 | §2.3 sets the Delta partition limit as the global container budget, runs MCKP on every beam candidate from a one-container-per-leaf start, exposes skipping ratio and marginal efficiency during iterations, describes a log-scale overlay chart that may sit on Figure 1 as a panel on MCKP, and keeps an ingestion-time dimension in the bottom split layer |
| I17 | §2.4 applies the beam plus a global equal-size assignment sized from compressed record size (example: at least 8 MB on AWS S3) to holdout samples, inspects the estimated weighted-average data skipping ratio, treats holdout as a gate, and on fail returns to §2.2 carrying those heuristics |
| I18 | §2.5 opens with a landing path into `streaming_sink`, a CRON consistency checker and checkpoint WAL, and a specialized writer that splits, allocates, and fans out to the index, the tracker, and `partitioned_sink`; it then states the three abstracted schemas, translates the §2.2 tree into a conditional group-by, packs each grouping into approx-capacity-`T` partitions by the tracker (`V = s_1 + pmod(xxhash64(identity), N)`, `seq = k + floor(V / T)`), collisions accepted, and points at §2.7 for the small-file problem |
| I19 | §2.6 names Spark DPP as the out-of-the-box skip, prescans the index, broadcasts the activated partition_id set, has workers fetch activated containers from `partitioned_sink` and write a durable query result, has a collector persist `usage_summary`, states a large-driver condition (example: AWS rgd series, at least 256 GB) and a high broadcast threshold (example: 256 MB), and links `Spark config: autoBroadcastJoinThreshold` to https://spark.apache.org/docs/latest/sql-performance-tuning.html |
| I20 | The left pane cites other sections by their reader-facing names and does not reprint those walkthroughs |
| I23 | The right pane is exactly the three titled figures, in §2 order; each stage shows the PNG export of that figure's `.drawio` source, with alt text, and no figure draws inside itself the title the pane already prints |
| I24 | Figure 1 is `usage_summary` into a bounded beam search, MCKP with overlay and equal-size holdout, then a gate to a frozen tree or to carried heuristics |
| I25 | Figures 2 and 3 share the §4.4 schema of `index_table` and `partitioned_sink`; Figure 3 has no row instance; they do not read a provider dataset, catalog, or scenario file |
| I26 | Prompts are retained at `section_databricks_layout_planning_prompt.md`, `section_databricks_ingestion_prompt.md`, and `section_databricks_query_prompt.md` |
| I27 | The tracker sequence `seq = k + floor(V / T)` is stated in §2.5; no figure draws it |
| I28 | The overlay chart in §2.3 may sit on Figure 1 as a panel on MCKP; the right pane stays three figures |
| I29 | §2.7 names `streaming_sink` as landing and `partitioned_sink` as the containerized event store, states a CRON optimizer that rewrites `partitioned_sink` to one file per partition without Z-order (disjoint commits), two-tier ingest on ingestion time, and that one schema may sit on complementary layouts, engines, or hardware |
