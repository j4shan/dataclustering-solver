# Figure prompt — section_databricks_query

Retained specification for *Query Time Integration*.
Source: `resources/img_src/section_databricks_query.drawio`.
Generator: `tools/plates/plate03.py`.

Shared ids: `index_table` and `partitioned_sink` (Plate 02 writes them, this
figure reads them) and `usage_summary` (this figure writes it, Plate 01 reads
it). Do not regenerate those ids.

## Claim

Spark scans the narrow index. The driver computes the matching `partition_id`
set and broadcasts it. Two workers fetch only those containers from the event
table and write a durable query result. A usage statistics collector reads that
result and persists aggregated `usage_summary`, which is the store the layout
planning figure reads.

## Audience

Readers of Go Live on Databricks Lakehouse §2.6. They have seen the index and
`partitioned_sink` on Plate 02. The point is the activation path inside Spark,
not a row-level skip story.

## Destination

Right pane of the demonstration GUI. Screen. Light background. Page width.
No pixel size.

## Emphasis

Notice first: the cluster frame split 60% driver / 40% workers, and the path
index -> driver -> workers -> event table -> durable output.

Context: the feedback rail, where `usage_collector` writes the `usage_summary`
that the layout search plans from. Activation stays at partition grain.

## Exclusions

- No body rows. No brand-sales activation rehearsal. No download or skip glyphs
  on individual containers. Both tables are schema only.
- No self-pointing loop anywhere, and no footnote or cross-reference printed on
  the plate. What this figure leaves to another page is recorded in this list
  and nowhere else, and no card names another figure.
- No opening `partitioned_sink` during the index scan. The prescan stays on the
  index.
- No optimizer, Auto Loader, `streaming_sink`, or WAL. Those are Plate 02.
- No `V` / `T` formula.
- No measured skip ratio, DBU, or wall-clock.
- No photoreal server racks. Driver and workers are labelled cards inside the
  cluster frame.
- No second index.
- No title drawn inside the figure. The pane that carries the figure prints the
  title above it, and printing it twice is ink that encodes nothing.
- No term from the dataset example anywhere on the plate — no source name, no
  column name.

## Instance data

Literal. Every printed column and share is derived from this block by the
generator.

```
index_columns = ["predicate_1", "predicate_2", "partition_id"]
partitioned_sink_columns = [
  "predicate_1", "predicate_2", "attribute_1", "attribute_2",
  "partition_id", "record_id",
]
driver_share  = 0.60
workers_share = 0.40
workers       = ["w1", "w2"]
driver_node   = "rgd-class driver, 256 GB or more"
broadcast_threshold = "autoBroadcastJoinThreshold 256 MB"
```

Column names are placeholders on purpose. **No figure prints a term from the
dataset example** — what has to carry is the shape of the two schemas: the index
holds the predicate features plus `partition_id` and nothing else, the event
table holds those plus the remaining attributes plus `record_id`. Plate 02
prints the same two schemas, placeholder for placeholder.

Schema only. Column names on `index_table` and `partitioned_sink`. No record
list. No activated set printed from sample rows. `query_output` and
`usage_summary` print no columns: what each holds is its one sentence.

### Nodes (component ids)

| spec_id | role | label |
| --- | --- | --- |
| index_table | data_persisted | Index Table: index_table |
| cluster | group | DATABRICKS CLUSTER |
| cluster_split | chrome | dashed 60 / 40 rule |
| driver | operation | Driver |
| driver_node | chrome | rgd-class driver, 256 GB or more |
| broadcast_threshold | chrome | autoBroadcastJoinThreshold 256 MB |
| broadcast_bus | chrome | the shared node the broadcast passes through |
| w1 | operation | Worker w1 |
| w2 | operation | Worker w2 |
| partitioned_sink | data_persisted | Event Table: partitioned_sink |
| query_output | data_durable | Query Result: query_output, tagged DURABLE |
| usage_collector | operation | Usage Statistics Collector |
| usage_summary | data_persisted | DL Table: usage_summary |
| write_bus | chrome | the shared node both workers' writes pass through |
| legend | chrome | (see legend keys) |

On this canvas `partitioned_sink` keeps its id and is named by its kind in its
own title row: `Event Table: partitioned_sink`. `usage_summary` is the same
store Plate 01 reads, drawn with the same recipe and the same sentence; this
plate prints no preview of its rows, because here the point is that the store
is written, not what shape it has. `driver_node` and `broadcast_threshold` are
two `REQUIRES` badges inside the driver compartment, which is where §2.6's two
conditions belong — they are not a second sentence on the driver.

### Edges (component ids)

| spec_id | meaning | from | to | label |
| --- | --- | --- | --- | --- |
| e_index_driver | full index scan | index_table | driver | scan |
| e_driver_bus | one broadcast out of the driver | driver | broadcast_bus | activate |
| e_driver_w1 | fan-out | broadcast_bus | w1 | — |
| e_driver_w2 | fan-out | broadcast_bus | w2 | — |
| e_w1_psink | fetch activated containers | partitioned_sink | w1 | fetch |
| e_w2_psink | fetch activated containers | partitioned_sink | w2 | fetch |
| e_w1_qout | one worker's share | w1 | write_bus | — |
| e_w2_qout | one worker's share | w2 | write_bus | — |
| e_bus_qout | one durable result | write_bus | query_output | write |
| e_qout_collector | read durable output | query_output | usage_collector | — |
| e_collector_usage | persist aggregate | usage_collector | usage_summary | persist |

The driver broadcasts **once**: one edge leaves it carrying the activation and
lands on `broadcast_bus`, and the two branches to the workers leave that shared
node, crossing the 60 / 40 rule. Three arrows out of the driver would draw three
broadcasts, which is not what happens. The two writes converge the same way —
each worker writes its own share into `write_bus`, and one edge leaves that node
for `query_output`, because there is one durable result. The fetches are the
exception and stay as two direct edges: each worker fetches a different set of
containers, so a shared node there would draw a shared channel that does not
exist.

Activation is these labelled edges, not highlighted rows. `e_w1_psink` and
`e_w2_psink` run **from** `partitioned_sink` **to** the workers. Never draw
worker -> event table as a data flow; that reads as a write. The only writes
are `w1` and `w2` -> `query_output`. No edge runs from a node to itself.

Declared component ids (one per line for the source check):

id: index_table
id: cluster
id: cluster_split
id: driver
id: driver_node
id: broadcast_threshold
id: broadcast_bus
id: write_bus
id: w1
id: w2
id: partitioned_sink
id: query_output
id: usage_collector
id: usage_summary
id: legend
id: legend_key_operation
id: legend_key_persisted
id: legend_key_durable
id: legend_key_cluster
id: legend_key_split
id: e_index_driver
id: e_driver_bus
id: e_driver_w1
id: e_driver_w2
id: e_w1_psink
id: e_w2_psink
id: e_bus_qout
id: e_w1_qout
id: e_w2_qout
id: e_qout_collector
id: e_collector_usage

### Derived (asserted in the generator, not typed into the drawing)

```
assert set(index_columns) <= set(partitioned_sink_columns)
assert "partition_id" in partitioned_sink_columns
assert "record_id" not in index_columns
assert len(workers) == 2
assert driver_share + workers_share == 1.0
assert not any(e.source == e.target for e in edges)
# the printed shares are rendered from driver_share and workers_share
# no activated set: schema only
```

## Presentation format

This plate is drawn in the **Lakehouse Plate System**, recorded in
`project_metadata/instructions/lakehouse-plate-system.md`, and generated by
`tools/plates/plate03.py` on the shared kit in `tools/plates/kit.py`. That file
is the single source for the substrate, the two role hues and their measured
contrast, the type scale, the card recipes, the edge lexicon, the legend, and
the list of things that never appear. It governs all three
`section_databricks_*` plates. Never restate a hex here, and never vary
one for this plate alone — a change to the look is a change to that file and
therefore to all three plates.

Plate number: **03**.
Rails: two bands — `1 ACTIVATE & FETCH`, `2 FEED THE NEXT LAYOUT`.

Roles on this plate:

| component | role |
| --- | --- |
| `index_table`, `partitioned_sink`, `usage_summary` | `store` |
| `cluster` | `frame` |
| `driver`, `w1`, `w2`, `usage_collector` | `operation` |
| `query_output` | `accepted`, caps tag `DURABLE` |
| `cluster_split`, `driver_node`, `broadcast_threshold`, `broadcast_bus`, `write_bus`, `legend` | chrome |

Title rows, in the one recipe the plate system fixes — a band filled in the
node's own ink, reversed type, left-aligned, any tag beside the name:

Stores name their kind first: `Index Table: index_table` ·
`Event Table: partitioned_sink` · `Query Result: query_output` tagged
`DURABLE` · `DL Table: usage_summary`.

Operations carry their name alone, in Title Case: `Driver` · `Worker w1` ·
`Worker w2` · `Usage Statistics Collector`. `w1` and `w2` are drawn identically
and carry the same sentence, because they are the same thing twice.

Only this plate's specialisations belong here, because they are facts about
this figure rather than about the system:

- The cluster frame is split by a dashed vertical rule at `driver_share` of its
  inner width, with `DRIVER 60%` and `WORKERS 40%` printed in the two
  compartments. The rule plus those two captions is the split; no compartment
  tint carries it, and both percentages are rendered from the instance data.
- `e_w1_psink` and `e_w2_psink` run from `partitioned_sink` to the workers and
  are labelled `fetch`. Worker-to-table would read as a write, and the only
  writes are `w1` and `w2` into `query_output`.
- The two write edges leave the cluster on separate lanes, one per worker, and
  converge on `write_bus` in the gutter between the rails, which is also where
  the plate crosses from the read path into the feedback path. Where a write
  crosses a fetch, the crossing carries a jump arc.
- **`w1` and `w2` are stacked vertically inside the workers compartment, with a
  full card gap between them**, and the driver compartment stacks its card over
  its two `REQUIRES` badges the same way. Components inside a frame stack down
  the page with space between them.
- **Layers are spaced, not packed.** Rail to rail, rail head to first card, and
  card to card each get their own step of space. The plate is wider than the
  other two (1560) because the cluster needs room for a 60 / 40 split that still
  leaves the broadcast a readable fan; height is never bought by crowding.
- Rail 2 runs right to left: `query_output` at the right, then
  `usage_collector`, then `usage_summary` at the left. The feedback direction
  is a direction a reader can see, and `usage_summary` ends up where the next
  figure starts.

## Chart and graph specification

- **Shape per role.** Shapes come from the plate system's role table. The one
  shape this plate owns is `cluster`: a frame divided by the dashed 60 / 40
  rule, with its heading at the right end of its bar.
- **Edge semantics.** Solid flow arrows throughout, labelled scan / activate /
  fetch / write / persist. Those five words are the activation path, and they
  are the only edge labels on the plate. Each word is printed once, on the
  trunk: `activate` on the edge into `broadcast_bus`, `write` on the edge out of
  `write_bus`. Branches off a shared node carry no label, and
  `e_qout_collector` carries none because the two cards it joins already say it.
- **Layout.** Two rail bands, hand-placed, `--no-layout`.
  1. Rail 1 — `ACTIVATE & FETCH`: `index_table` at the left, `cluster` in the
     middle with the 60 / 40 split, `partitioned_sink` at the right as the
     event table. Inside the cluster: `driver` in the left compartment above
     its two `REQUIRES` badges, `w1` and `w2` stacked in the right compartment,
     and `broadcast_bus` on the compartment boundary where the fan begins.
  2. Rail 2 — `FEED THE NEXT LAYOUT`: the feedback lane, read right to left.
- **Grouping.** `cluster` contains `driver` on the left and `w1`, `w2` on the
  right: one driver, two workers.
- **Legend.** One horizontal row on the top bar, left-aligned, directly under
  the title: persisted table, schema only; durable output; operation; cluster
  frame; dashed = driver / workers split.
- **One sentence per card.** No card carries more than one sentence of body.
  The detail is §2.6 of the walkthrough, which the reader reaches through the
  card's name:
  `index_table` — "Carry the query predicate features and partition_id only, so
  a prescan never opens the event table";
  `partitioned_sink` — "Hold the full event attributes under their finalized
  container assignment";
  `driver` — "Prescan the narrow index and broadcast the matching partition_id
  set to every worker";
  `w1` and `w2` — "Fetch only the activated containers and write its share of
  the result";
  `query_output` — "Hold the query result on durable storage for anything
  downstream to read";
  `usage_collector` — "Read the durable result and aggregate one boolean flag
  per query and per row";
  `usage_summary` — "Keep one boolean per query and per row, aggregated into
  hour bins".
  The first two sentences are the ones Plate 02 prints on the same two stores,
  word for word, because they are the same stores.
- **Encoding redundancy.** Driver versus workers: compartment side plus the
  printed shares. Durable versus ordinary table: the caps tag `DURABLE` plus
  the tinted accepted field and its heavier stroke. Activation: edge words and
  arrow direction, never row highlights.

Title: *Query Time Integration*, printed by the pane that carries the figure,
**not drawn inside it** — and no kicker, subtitle or footnote anywhere. The
legend strip is the top row of the drawing. What to notice first is recorded in
**Emphasis** above, and the plate says it by placement.
