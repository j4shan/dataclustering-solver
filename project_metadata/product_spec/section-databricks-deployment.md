# Go Live on Databricks Lakehouse

Product requirements for the Go Live on Databricks Lakehouse section of the
demonstration GUI: a six-step engineering process that assembles knowledge
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

**No recommendation.** The process names a cheap search, a multiple-choice
knapsack estimate, and a simple fixed-capacity assignment as available
planning moves. The write path packs each grouping into approximately
capacity-`T` partitions by the tracker method in §2.5. That method is
the ingest realization, not a ranking of planning strategies.

---

## 1. Role and reading order

Go Live on Databricks Lakehouse teaches one engineering process: deploy a
customized data layout optimized for high-value queries by assembling
knowledge already tabled on the other sections into a solution that can
run on a Databricks Lakehouse.

The process has six steps, in this order:

1. **Collect a target sample** — take a sample of the target dataset
   together with fetch query statistics, then run a preliminary analysis
   that quantifies data-skipping potential and cost-saving potential;
2. **Identify split decision trees** — grow trees from training samples
   with the techniques in Measuring Data Layout Fitness, starting from a
   cost-effective search and using business insight to narrow the remaining
   space;
3. **Estimate leaf skipping potential** — apply the Multiple-Choice
   Knapsack Problem (MCKP) to every leaf of those trees;
4. **Inspect the holdout** — apply the trees from step 2 and a container
   assignment (MCKP or simple fixed capacity) to holdout samples, then
   inspect the estimated weighted-average data skipping ratio;
5. **Implement data ingestion** — map split decisions, container
   assignment, and the feature index onto the Lakehouse write path;
6. **Implement query optimization** — map container-skipping onto an
   index-table lookup plus Spark Dynamic Partition Pruning.

- The process sits on the **left**. The figures sit on the **right**.
- Below the split breakpoint the panes stack in that order.
- Each pane is independently scrollable on a wide viewport.
- The left sequence cites other sections by their reader-facing names. It
  does not reprint those walkthroughs. The three figures draw the process,
  §2.5, and §2.6. Figures add no claim of their own.

The left pane is an authored walkthrough of this process.

---

## 2. Left pane — the go-live process

An opening paragraph before §2.1 hinges from exercised container
assignment: the solution can be deployed to a production data lake such as
Databricks. It takes knowledge already on Problem Statement, Measuring
Data Layout Fitness, and Drawing Storage Boundary and maps that knowledge
onto a Lakehouse write path and a Spark read path. It names the figure
*The go-live process*: six numbered actions, one per section below.

Six sections follow, with the titles below.

### 2.1 Collect a target sample

The first move is to collect a sample of the target dataset together with
fetch query statistics for that sample. A preliminary analysis on that
pair quantifies two potentials: how much data skipping the workload can
expose, and the cost saving that skipping would represent.

The section names those two inputs and those two outputs. The analysis is
a screening estimate on the sample. It is not a scored physical layout.
The benchmark harness remains the surface that reports exact workload
replay. The section does not invent a currency conversion, a DBU formula,
or a stop-rule constant.

### 2.2 Identify split decision trees

This section uses the techniques taught in Measuring Data Layout Fitness
to grow split decision trees from **training** samples. The search starts
with a cost-effective algorithm: the cheap greedy top-down baseline named
there. Business insight then narrows the remaining search space: columns,
grains, and predicates a practitioner already treats as load-bearing.

The section cites Measuring Data Layout Fitness by that name. It does not
reprint that walkthrough's recurrences or fitness formulas. It does not
rank search methods.

### 2.3 Estimate leaf skipping potential

This section applies the Multiple-Choice Knapsack Problem taught in
Drawing Storage Boundary to the leaf nodes of the trees from §2.2, and
reports an estimated data-skipping potential on every leaf. The first
mention of the multiple-choice knapsack problem links to
[the same external definition](https://en.wikipedia.org/wiki/List_of_knapsack_problems#Multiple-choice_knapsack_problem)
Drawing Storage Boundary uses.

The estimate is the static leaf benefit of that page. It is not a live
engine number. The section does not reprint Drawing Storage Boundary's
ladders, guardrails, or greedy scan.

### 2.4 Inspect the holdout

This section applies the split decision trees from §2.2 and a container
assignment strategy to **holdout** samples. The assignment strategy may be
the MCKP allocation from §2.3 or a simple fixed-capacity assignment
(every leaf packed at one shared container size). Both are named; neither
is selected.

The reader inspects the estimated weighted-average data skipping ratio on
the holdout. That quantity is the check that the training tree transfers.
The section does not treat the ratio as aggregate waste, and it does not
claim a measured engine result.

### 2.5 Implement data ingestion

This section maps the abstract layout onto the write path of a Databricks
Lakehouse. The figure *Ingestion writes two tables* is the fan-out.
The tracker method that assigns `partition_id` is stated here; it is
not a fourth figure.

A mapping table states:

| process concept | Databricks realization |
| --- | --- |
| split decision | a grouping or a predicate |
| container assignment | Delta Lake partition assignment (`partition_id`) |
| feature index | an independent narrow Delta table |
| events | a wide Delta event table |

On each arriving batch (a micro-batch when the stream is incremental),
Spark applies a group-by expression built from the custom layout
decision tree in §2.2. That cut divides the batch into logical
groupings. The brand-sales example groups by `brand_id` and
`pricing_tier`.

The ingest objective is then to split every grouping into approximately
fixed-size containers (Delta partitions). Container capacity is `T`.
Size is approximate because hash collisions are accepted.

A **stateful assignment tracker** is a dedicated table with one row per
logical grouping. A short definition table introduces the columns at the
moment they are used:

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
2. a **wide event table** of the full attributes plus `partition_id` plus
   `record_id`.

The index written here has no `record_id` and no non-predicate attribute,
because the §2.6 prescan only collects `partition_id` values.

The section does not rank this packing against MCKP, print a skip
ratio, or describe the read path.

### 2.6 Implement query optimization

This section maps container-skipping onto the read path. The figure
*Spark DPP skips from the index* is the worked example: it uses the same
brand-sales index that §2.5 wrote.

A mapping table states:

| process concept | Databricks realization |
| --- | --- |
| container-skipping | an index-table prescan plus Spark Dynamic Partition Pruning (DPP) |

The prose states three moves, in this order. A multi-select query
prescans the narrow index and computes the set of matching
`partition_id` values. Spark Dynamic Partition Pruning broadcasts that
set to each Databricks worker as a metadata filter. Each worker trims
its cloud-object download targets to the activated partitions.

The first mention of Dynamic Partition Pruning names it as a Spark
mechanism. The index schema remains the narrow one in §2.5. The section
does not invent a second index, open the event table during the prescan,
or treat a downloaded partition as selected rows. Activation stays at
partition grain.

---

## 3. Medium and visual system

The right pane is one authored fragment. The three figures share one
visual system:

- flat editorial drawing, not photorealism, 3D, or a screenshot;
- the warm paper ground and ink of the UI tokens;
- page sans for labels, mono for identifiers;
- one restrained repeating palette;
- dashed outline for a skipped or empty slot;
- text, shape, outline, or pattern in addition to colour for every state.

No figure contains UI chrome or server racks. Diagrams fetch nothing to
render. Every illustration carries a **visible title**, not only an
accessible one. No figure asserts a measured engine number.

---

## 4. Right pane — three figures

Exactly three figures, in walkthrough order:

| id | Visible title | Walkthrough section |
| --- | --- | --- |
| `C.process-flow` | *The go-live process* | opening and §2.1–§2.6 |
| `C.data-ingestion` | *Ingestion writes two tables* | §2.5 |
| `C.dpp-skipping` | *Spark DPP skips from the index* | §2.6 |

Each figure carries a one-line caption naming its construction. No pane
references a missing file.

Each figure is authored from its retained prompt:

- [`resources/img_prompt/c_go_live_process_prompt.txt`](../../resources/img_prompt/c_go_live_process_prompt.txt)
- [`resources/img_prompt/c_data_ingestion_prompt.txt`](../../resources/img_prompt/c_data_ingestion_prompt.txt)
- [`resources/img_prompt/c_dpp_skipping_prompt.txt`](../../resources/img_prompt/c_dpp_skipping_prompt.txt)

Each prompt specifies one 1920 × 1080 deterministic raster, names the
accepted PNG's path, and is the authority on that figure's content. A
figure is drawn by a temporary Python renderer; the renderer is removed
once the PNG is accepted, so a visual change starts a new authoring pass
from its prompt.

### 4.1 *The go-live process*

Six rounded rectangles in one vertical chain, joined by directed arrows.
A small circle at the top-left corner of each rectangle holds the
sequence number 1 through 6. The action text is the matching left-pane
section title. No side branch and no extra step.

### 4.2 *Ingestion writes two tables*

A brand-sales stream runs left to right through grouping and a
partition-assignment step, then fans out to two tables. Grouping is by
`brand_id` and `pricing_tier`. The assignment box prints "detailed
later"; it does not draw the hash or the sequence formula. The upper
table is the narrow index (`brand_id`, `pricing_tier`, `partition_id`).
The lower table is the wide event table (those columns plus `sku`,
`amount`, `record_id`). Four hypothesized rows, one per group. No query
and no download.

### 4.3 *Spark DPP skips from the index*

The same four index rows. A multi-select query
`brand_id IN (A, B) AND pricing_tier = 1` prescans that table, so `p1`
and `p3` are the activated set. Spark DPP broadcasts that set to two
worker cards as a metadata filter. Four cloud-object glyphs follow:
`p1` and `p3` marked download, `p2` and `p4` marked skip. Workers are
flat labelled cards. The event table is not drawn.

### 4.4 Shared instance

Figures 2 and 3 share one hypothesized brand-sales dictionary, written
in both prompts. It is not a provider corpus, a catalog score, or a
measured workload. These figures are outside 12.6.4's catalog /
manifest / scenario trace. Figure 1 has no row instance.

```
stream = "brand sales"
group_keys = ["brand_id", "pricing_tier"]
records = [
  {record_id: r01, brand_id: A, pricing_tier: 1, sku: brk-12, amount: 40, partition_id: p1},
  {record_id: r02, brand_id: A, pricing_tier: 2, sku: flt-03, amount: 18, partition_id: p2},
  {record_id: r03, brand_id: B, pricing_tier: 1, sku: brk-08, amount: 55, partition_id: p3},
  {record_id: r04, brand_id: B, pricing_tier: 2, sku: tyr-21, amount: 22, partition_id: p4},
]
query = brand_id IN (A, B) AND pricing_tier = 1
match(r) = r.brand_id in {A, B} and r.pricing_tier == 1
activated = {p1, p3}
trimmed = {p2, p4}
```

The query matches r01 and r03 only. A later figure may change only the
relationship its prompt names.

---

## 5. Writing contract

The left pane is a technical process walkthrough. Each of §2.1–§2.6 is a
section with the title in §2. Conclusions fold into the last paragraph of
the section; there is no labeled takeaway.

The first mention of a public technical term is a weblink (MCKP as in
§2.3; Dynamic Partition Pruning as a Spark mechanism). `xxhash64` and
`pmod` are named as Spark SQL functions at first mention. Later emphasis
uses the citation form *the concept description* (`symbol`, defined in
§X), naming the document when $X$ is not a section of this walkthrough.
The walkthrough refers to Measuring Data Layout Fitness, Drawing Storage
Boundary, and Problem Statement by those names.
It refers to the three figures by the titles *The go-live process*,
*Ingestion writes two tables*, and *Spark DPP skips from the index*.
It contains no figure markup.

---

## 6. Requirements map

| id | requirement |
| --- | --- |
| I1 | Process on the left; figures on the right; that order when stacked |
| I5 | The three figures draw the process, §2.5, and §2.6; they add no claim of their own |
| I10 | Formal terms stay the project's own vocabulary; state is not carried by colour alone |
| I11 | §2.4 names MCKP and simple fixed capacity without ranking them; §2.5 states the tracker packing method as the ingest realization, not as a ranked planning strategy |
| I12 | An opening paragraph hinges from exercised container assignment, deploys the solution to a production data lake such as Databricks, maps knowledge already on Problem Statement, Measuring Data Layout Fitness, and Drawing Storage Boundary onto a Lakehouse write path and a Spark read path, and names *The go-live process* |
| I13 | The left pane is six sections in this order: Collect a target sample; Identify split decision trees; Estimate leaf skipping potential; Inspect the holdout; Implement data ingestion; Implement query optimization |
| I14 | §2.1 collects a dataset sample plus fetch query statistics and quantifies data-skipping potential and cost-saving potential as a screening estimate |
| I15 | §2.2 grows split decision trees from training samples with Measuring Data Layout Fitness techniques, starting from a cheap search and using business insight to narrow the space |
| I16 | §2.3 applies MCKP to estimate data-skipping potential on every leaf |
| I17 | §2.4 applies the trees plus MCKP or simple fixed-capacity assignment to holdout samples and inspects the estimated weighted-average data skipping ratio |
| I18 | §2.5 groups each batch with a group-by from the §2.2 tree, packs each grouping into approx-capacity-`T` partitions by the tracker (`V = s_1 + pmod(xxhash64(identity), N)`, `seq = k + floor(V / T)`), collisions accepted, then writes the narrow index and the wide event table |
| I19 | §2.6 prescans that index for a multi-select query, broadcasts the activated partition_id set with Spark DPP, and trims cloud-object downloads |
| I20 | The left pane cites other sections by their reader-facing names and does not reprint those walkthroughs |
| I23 | The right pane is exactly the three titled figures, in §2 order |
| I24 | Figure 1 is a numbered rounded-rectangle chain of the six left-pane actions |
| I25 | Figures 2 and 3 share the §4.4 brand-sales instance; they do not read a provider dataset, catalog, or scenario file |
| I26 | Prompts are retained at `c_go_live_process_prompt.txt`, `c_data_ingestion_prompt.txt`, and `c_dpp_skipping_prompt.txt` |
| I27 | The tracker sequence `seq = k + floor(V / T)` is stated in §2.5; no figure draws it |
