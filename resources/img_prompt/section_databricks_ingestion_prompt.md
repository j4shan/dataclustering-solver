# Figure prompt — section_databricks_ingestion

Retained specification for *Ingestion Time Integration*.
Source: `resources/img_src/section_databricks_ingestion.drawio`.
Generator: `tools/plates/plate02.py`.

Shared ids: `tree_frozen` (Plate 01 emits it, this figure consumes it) and
`index_table` and `partitioned_sink` (this figure writes them, Plate 03 reads
them). Do not regenerate those ids.

## Claim

A transient stream lands in `streaming_sink` unsplit. One CRON scheduler fires
a consistency checker that cycles with a write-ahead log and launches a
specialized writer. The writer splits each batch with the frozen tree,
finalizes a `partition_id`, and fans out to the index, the tracker and the
event table before committing. The same CRON fires an optimizer that rewrites
`partitioned_sink` to one file per partition.

## Audience

Readers of Go Live on Databricks Lakehouse §2.5 and §2.7. They hold the frozen
tree from Plate 01. They have not seen Auto Loader, `streaming_sink`, the
checkpoint WAL, or the named optimizer on `partitioned_sink`.

## Destination

Right pane of the demonstration GUI. Screen. Light background. Page width.
No pixel size.

## Emphasis

Notice first: landing (`streaming_sink`) is not tree-split; the specialized
writer is one assembly line inside one frame; the optimizer is a separate rail
that only compacts `partitioned_sink`.

Context: CRON as the one scheduler behind both the checker and the optimizer.
The checkpoint WAL as the reason the fan-out can be idempotent.

## Exclusions

- No `V = s_1 + pmod(xxhash64(identity), N)` and no `seq = k + floor(V / T)`.
  The allocator names a finalized `partition_id` and nothing else.
- No self-pointing loop anywhere. What a step repeats is said in that step's
  own sentence, never drawn as an arrow back to itself.
- No footnote and no cross-reference printed on the plate. Everything this
  figure leaves to another page is recorded in this list and nowhere else, and
  no card names another figure.
- No Spark query, DPP, driver/worker cluster, or `usage_summary`. Those belong
  to Plate 03.
- No Z-order on the optimizer.
- No body rows on any store. Schema — title row plus column list — only.
- No measured skip ratio, DBU, or file-count score.
- No UI chrome, notebook, or server-rack photorealism. The cluster is not on
  this canvas.
- No reprint of Measuring Data Layout Fitness or the knapsack ladders.
- No step numbers on the cards. Order is arrows, rails and objects.
- No title drawn inside the figure. The pane that carries the figure prints the
  title above it, and printing it twice is ink that encodes nothing.
- No term from the dataset example anywhere on the plate — no source name, no
  column name, no grouping key from it.

## Instance data

Literal. Every printed column is derived from this block by the generator.

```
index_columns = ["predicate_1", "predicate_2", "partition_id"]
partitioned_sink_columns = [
  "predicate_1", "predicate_2", "attribute_1", "attribute_2",
  "partition_id", "record_id",
]
group_keys  = ["predicate_1", "predicate_2"]
source_name = "an event stream"
optimizer   = { target: one_file_per_partition, zorder: false }
```

Column names are placeholders on purpose. **No figure prints a term from the
dataset example** — not a source name, not a column name. What the figure has
to carry is the *shape* of the two schemas: the index holds the predicate
features plus `partition_id` and nothing else, the event table holds those
plus the remaining attributes plus `record_id`. Any concrete example belongs in
the walkthrough prose, where a reader can see it named as an example.

`index_table` and `partitioned_sink` are schema only. `streaming_sink`,
`checkpoint` and `container_tracker` print no columns: what each holds is its
one sentence.

### Nodes (component ids)

| spec_id | role | label |
| --- | --- | --- |
| stream | data_transient | Data Source: an event stream |
| auto_loader | operation | Spark Structured Streaming / Auto Loader |
| stream_writer | operation | Stream Writer |
| streaming_sink | data_persisted | Landing Table: streaming_sink |
| cron | operation | CRON Scheduler |
| consistency_checker | operation | Consistency Checker |
| checkpoint | data_persisted | Write-Ahead Log: checkpoint |
| specialized_writer | group | SPECIALIZED WRITER |
| data_splitter | operation | Data Splitter |
| container_allocator | operation | Container Allocator |
| fanout_distributor | operation | Fanout Distributor |
| container_tracker | data_persisted | Assignment Tracker: container_tracker |
| index_table | data_persisted | Index Table: index_table |
| partitioned_sink | data_persisted | Event Table: partitioned_sink |
| tree_frozen | data_accepted | Split Tree: Pre-Built, tagged FROZEN |
| optimizer | operation | Continuous Consolidation Optimizer |
| legend | chrome | (see legend keys) |

`tree_frozen` is the object Plate 01 emitted: same id, same role, same recipe.
One `cron` node only — never mint `cron_2`. Two trigger edges leave it,
`e_cron_checker` and `e_cron_optimizer`. The optimizer reads
`partitioned_sink` and writes it back; it does not run the fan-out. Optional
cleanup is a clause of `consistency_checker`'s sentence, not a fourth inner
node.

### Edges (component ids)

| spec_id | meaning | from | to | label |
| --- | --- | --- | --- | --- |
| e_stream_loader | data flow | stream | auto_loader | — |
| e_loader_writer | call | auto_loader | stream_writer | — |
| e_writer_sink | persist | stream_writer | streaming_sink | write |
| e_cron_checker | schedule | cron | consistency_checker | schedule |
| e_checker_wal | read WAL | consistency_checker | checkpoint | read |
| e_wal_checker | WAL state | checkpoint | consistency_checker | offsets |
| e_checker_writer | launch after optional cleanup | consistency_checker | data_splitter | launch |
| e_sink_splitter | read landing | streaming_sink | data_splitter | landed rows |
| e_tree_splitter | grouping key | tree_frozen | data_splitter | grouping rule |
| e_splitter_alloc | groupings | data_splitter | container_allocator | groupings |
| e_tracker_alloc | read fill | container_tracker | container_allocator | read fill |
| e_alloc_fanout | partition_id finalized | container_allocator | fanout_distributor | partition_id |
| e_fanout_bus | one write out of the writer | fanout_distributor | fanout_bus | assigned batch |
| e_fanout_index | fan-out | fanout_bus | index_table | — |
| e_fanout_tracker | fan-out | fanout_bus | container_tracker | — |
| e_fanout_psink | fan-out | fanout_bus | partitioned_sink | — |
| e_fanout_wal | append commit | fanout_distributor | checkpoint | commit |
| e_cron_optimizer | schedule | cron | optimizer | schedule |
| e_psink_opt | read | partitioned_sink | optimizer | read |
| e_opt_psink | write back | optimizer | partitioned_sink | compact |

The writer does not reach for the three stores separately. One edge leaves it
carrying the assigned batch, lands on `fanout_bus` — a shared node — and the
fan-out happens there, as three branches off one trunk. That is what a fan-out
is, and drawing it as three independent arrows out of one card says something
weaker. The three branches carry no label: `fanout_distributor`'s own sentence
names the index, the tracker and the event table, so a third printing of
"write" would be ink that encodes nothing. Do not draw
`checkpoint -> specialized_writer`; the checker owns that cycle. No edge runs
from a node to itself.

Declared component ids (one per line for the source check):

id: stream
id: auto_loader
id: stream_writer
id: streaming_sink
id: cron
id: consistency_checker
id: checkpoint
id: specialized_writer
id: data_splitter
id: container_allocator
id: fanout_distributor
id: container_tracker
id: index_table
id: partitioned_sink
id: tree_frozen
id: optimizer
id: fanout_bus
id: legend
id: legend_key_operation
id: legend_key_persisted
id: legend_key_transient
id: legend_key_frozen
id: legend_key_assembly
id: legend_key_dash
id: e_stream_loader
id: e_loader_writer
id: e_writer_sink
id: e_cron_checker
id: e_checker_wal
id: e_wal_checker
id: e_checker_writer
id: e_sink_splitter
id: e_tree_splitter
id: e_splitter_alloc
id: e_alloc_fanout
id: e_tracker_alloc
id: e_fanout_bus
id: e_fanout_index
id: e_fanout_tracker
id: e_fanout_psink
id: e_fanout_wal
id: e_cron_optimizer
id: e_psink_opt
id: e_opt_psink

### Derived (asserted in the generator, not typed into the drawing)

```
assert set(index_columns) <= set(partitioned_sink_columns)
assert "partition_id" in index_columns
assert "partition_id" in partitioned_sink_columns
assert "record_id" not in index_columns
assert group_keys == index_columns[:2]
assert not any(e.source == e.target for e in edges)
```

## Presentation format

This plate is drawn in the **Lakehouse Plate System**, recorded in
`project_metadata/instructions/lakehouse-plate-system.md`, and generated by
`tools/plates/plate02.py` on the shared kit in `tools/plates/kit.py`. That file
is the single source for the substrate, the two role hues and their measured
contrast, the type scale, the card recipes, the edge lexicon, the legend, and
the list of things that never appear. It governs all three
`section_databricks_*` plates. Never restate a hex here, and never vary
one for this plate alone — a change to the look is a change to that file and
therefore to all three plates.

Plate number: **02**.
Rails: three bands — `1 LAND`, `2 WRITE`, `3 COMPACT`.

Roles on this plate:

| component | role |
| --- | --- |
| `stream` | `attention`, title row `Data Source: an event stream` |
| `auto_loader`, `stream_writer`, `cron`, `consistency_checker`, `data_splitter`, `container_allocator`, `fanout_distributor`, `optimizer` | `operation` |
| `streaming_sink`, `checkpoint`, `container_tracker`, `index_table`, `partitioned_sink` | `store` |
| `tree_frozen` | `accepted`, caps tag `FROZEN` |
| `specialized_writer` | `frame` |
| `legend`, `fanout_bus` | chrome |

Title rows, in the one recipe the plate system fixes — a band filled in the
node's own ink, reversed type, left-aligned, any tag beside the name:

Stores name their kind first, and the kind is the walkthrough's own word for
it: `Landing Table: streaming_sink` · `Write-Ahead Log: checkpoint` ·
`Assignment Tracker: container_tracker` · `Index Table: index_table` ·
`Event Table: partitioned_sink` · `Split Tree: Pre-Built` tagged `FROZEN`.

Operations carry their name alone, with no `Operation:` prefix, in Title Case:
`Spark Structured Streaming / Auto Loader` · `Stream Writer` ·
`CRON Scheduler` · `Consistency Checker` · `Data Splitter` ·
`Container Allocator` · `Fanout Distributor` ·
`Continuous Consolidation Optimizer`. The last of those is §2.7's own term, so
a reader who wants the disjoint-commit detail knows which section to open.

Only this plate's specialisations belong here, because they are facts about
this figure rather than about the system:

- Rail 2 carries the whole write path in two internal rows: the schedule
  (`cron`, `consistency_checker`, `checkpoint`) across the top, then the writer
  row — `tree_frozen`, the `specialized_writer` frame, the shared node, and the
  three stores the fan-out writes. Everything §2.5 describes sits in the rail
  named for it.
- **The three writer stages are stacked vertically inside the frame, with a
  full card gap between them.** The assembly line reads top to bottom like the
  rest of the plate, and each stage gets the full frame width for its sentence.
- **Layers are spaced, not packed.** Rail to rail, row to row, and card to card
  inside a frame each get their own step of space, and no layer is squeezed to
  save height. A crowded column is harder to read than a tall plate.
- The three destination stores are stacked to the right of the writer, in the
  order the fan-out names them, so the fan reads down the page.
- Sub-row 1 of rail 2 stops short of the rail's right edge. That free column is
  a reserved lane: `e_sink_splitter` comes down it from rail 1, so the landing
  copy reaches the splitter without crossing a card.
- `e_checker_writer` drops straight from the checker into the splitter's top,
  and the frame's heading sits at the **left** end of its bar, because the lanes
  that enter this frame come down its right. The heading always takes the end of
  the bar no lane crosses.
- Both edges out of `cron` are triggers, so both are wine dotted and labelled
  `schedule`; the checker's `launch` is the third trigger. `e_cron_optimizer`
  runs out of the rails entirely, down the left margin and along the foot of
  rail 2, which is what shows one scheduler behind two rails.
- Rail 3 is only as wide as the card it holds and sits under
  `partitioned_sink`, the last store in the stack, because compaction is a step
  on that one table. Its two
  edges are a read down and a `compact` write back.
- Where two edges must cross, the crossing carries a jump arc.

## Chart and graph specification

- **Shape per role.** Shapes come from the plate system's role table. The one
  shape this plate owns is `specialized_writer`: a frame drawn around the three
  writer stages with its heading at the right end of its bar, so a lane
  entering from above never crosses the words.
- **Edge semantics.** From the plate system's edge lexicon. Only `cron`'s two
  edges and the checker's launch are triggers, so only those three are dotted
  and verb-labelled. `e_opt_psink` is labelled `compact` so it cannot read as a
  second fan-out. Every other edge is a solid flow, labelled only where the two
  cards it joins do not already say what travels.
- **Layout.** Three rails, hand-placed, `--no-layout`.
  1. Rail 1 — `LAND`: `stream` -> `auto_loader` -> `stream_writer` ->
     `streaming_sink`, one row, left to right.
  2. Rail 2 — `WRITE`: the schedule row, then the writer row. The assembly line
     runs top to bottom inside the frame — splitter, allocator, fan-out — with a
     card gap between stages. `tree_frozen` sits immediately left of the
     splitter that consumes it. One edge leaves the fan-out stage into the
     shared node, and three branches leave that node for the three stores
     stacked at the right, which is the fan drawn as a fan.
  3. Rail 3 — `COMPACT`: the optimizer under `partitioned_sink`.
- **Grouping.** `specialized_writer` contains `data_splitter`,
  `container_allocator`, `fanout_distributor`. The frame means "these run as
  one thing".
- **Legend.** One horizontal row on the top bar, left-aligned, directly under
  the title: persisted table; frozen input; operation; transient source;
  assembly line frame; dotted = CRON trigger.
- **One sentence per card.** No card carries more than one sentence of body.
  The detail is §2.5 and §2.7 of the walkthrough, which the reader reaches
  through the card's name:
  `stream` — "Carry events as they arrive, under no layout of their own";
  `auto_loader` — "Persist the arriving stream and hand each micro-batch to the
  stream writer";
  `stream_writer` — "Append every micro-batch to the landing table as it
  arrives";
  `streaming_sink` — "Hold the landing copy unsplit, so high-frequency arrivals
  never fragment the container layout";
  `cron` — "Fire the consistency checker and the consolidation optimizer on one
  schedule";
  `consistency_checker` — "Read the write-ahead log, clear any partial ingest
  state, then launch the writer";
  `checkpoint` — "Record every multi-table write so a repeated fan-out stays
  idempotent";
  `tree_frozen` — "Carry the split decision that held up on holdout into the
  splitter";
  `data_splitter` — "Divide each batch into logical groupings with a
  conditional group-by built from the frozen tree";
  `container_allocator` — "Read container fill from the tracker and finalize a
  partition_id for every record";
  `fanout_distributor` — "Write the assigned batch to the index, the tracker
  and the event table, then commit";
  `container_tracker` — "Keep one row for every grouping, recording how full
  its open container is";
  `index_table` — "Carry the query predicate features and partition_id only, so
  a prescan never opens the event table";
  `partitioned_sink` — "Hold the full event attributes under their finalized
  container assignment";
  `optimizer` — "Rewrite each partition back to one file on disjoint commits,
  without Z-order".
- **Encoding redundancy.** Transient versus persisted: the dashed border plus
  the type word `Data Source:`. Optimizer versus writer: its own rail plus
  the word `compact` on the edge. WAL: the type word `Write-Ahead Log:` plus
  `commit` on the edge into it. Frozen input: the caps tag `FROZEN` plus the
  tinted accepted field and its heavier stroke.

Title: *Ingestion Time Integration*, printed by the pane that carries the figure, **not drawn
inside it** — and no kicker, subtitle or footnote anywhere. The legend strip is
the top row of the drawing. What to notice first is recorded in **Emphasis**
above, and the plate says it by placement.
