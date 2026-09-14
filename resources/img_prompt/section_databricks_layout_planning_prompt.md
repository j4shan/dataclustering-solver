# Figure prompt — section_databricks_layout_planning

Retained specification for *Deployment Process Flow*.
Source: `resources/img_src/section_databricks_layout_planning.drawio`.
Generator: `tools/plates/plate01.py`.

Shared ids: `usage_summary` (Plate 03 writes it, this figure reads it) and
`tree_frozen` (this figure emits it, Plate 02's splitter consumes it). Do not
regenerate those ids.

## Claim

`usage_summary` feeds a bounded beam search. That beam goes to an optimistic
knapsack spend and to an equal-size holdout check. Holdout gates transfer: a
tree that transfers freezes for ingest; a tree that fails sends search round
again, carrying heuristics of the unqualified split conditions from that
failure.

## Audience

Readers of Go Live on Databricks Lakehouse who have already read Measuring
Data Layout Fitness and Drawing Storage Boundary. They know what a split tree
and MCKP are. They have not seen this page's outer retry or the name
`usage_summary`.

## Destination

Right pane of the demonstration GUI. Screen. Light background. Page width.
No pixel size.

## Emphasis

Notice first: `usage_summary` is the only raw input; holdout is a **gate**;
the fail edge carries state (unqualified-split heuristics), not an empty
return.

Context: the knapsack simulation and the overlay panel attached to it. The frozen
tree is the object that leaves the canvas.

## Exclusions

- No self-pointing loop anywhere. The inner list, score, replace cycle stays on
  Measuring Data Layout Fitness, and the knapsack's piecemeal spend is said in the
  card's own body rather than drawn as an arrow back to itself.
- No footnote and no cross-reference printed on the plate. Everything this figure
  leaves to another page is recorded in this list and nowhere else.
- No recurrences, fitness formulas, or Gini split-cycle animation. The candidate
  glyphs show a tree's shape and nothing else: no predicate text on a branch, no
  Gini value, no cut ordering.
- No knapsack ladders, guardrails, or greedy scan from Drawing Storage Boundary.
- No `V` / `T` arithmetic.
- No measured engine skip ratio, DBU, or currency.
- No step numbers on the boxes. Order is arrows and objects.
- No Delta write path, Auto Loader, or Spark cluster.
- No body rows that look like a scored workload. The `usage_summary` preview is a
  boolean usage table marked `SAMPLE ROWS`; it carries no score, cost or ranking.

## Instance data

Literal. Every printed count is derived from this block by the generator.

```
usage_summary = {
  spec_id: usage_summary,
  role: data_persisted,
  grain: hour,
  kind: aggregated_usage_statistics,
  note: "time-bin aggregation shrinks the table and loses resolution",
  preview_columns: ["record_id", "hour_bin", "q_01", "q_02", "q_03", "…"],
  preview_rows: [
    ["r_004171", "09:00", 1, 0, 1, "…"],
    ["r_004172", "09:00", 0, 0, 1, "…"],
    ["r_004173", "10:00", 1, 1, 0, "…"],
  ],
}

beam = [
  { spec_id: tree_a, role: data_persisted, label: "tree A",
    bottom_layer: ingestion_time, leaves: 4 },
  { spec_id: tree_b, role: data_persisted, label: "tree B",
    bottom_layer: ingestion_time, leaves: 3 },
]

partition_limit = { spec_id: partition_limit, role: chrome,
                    value: 10000, role_on_figure: tick_on_overlay }

mckp    = { spec_id: mckp, role: operation,
            start: one_container_per_leaf, spend: piecemeal }
overlay = { spec_id: overlay, role: overlay_panel, axis: log_container_count,
            continues_past: partition_limit,
            curves: ["metadata_overhead", "skipping_performance"],
            attached_to: mckp }
holdout = { spec_id: holdout, role: operation, assignment: global_equal_size,
            ignores: mckp_ranking, capacity_from: compressed_record_size }
gate    = { spec_id: gate, role: decision, question: "transfers" }
heuristics = { spec_id: heuristics, role: data_carried,
               kind: unqualified_split_conditions,
               written_by: gate_no_exit, read_by: search }
tree_frozen = { spec_id: tree_frozen, role: data_accepted,
                label: "pre-built tree", destination: "Plate 02 data_splitter" }
search = { spec_id: search, role: group,
           bounds: ["resource_monitor", "complexity_bound", "partition_limit_prune"],
           cites: "Measuring Data Layout Fitness" }
```

### Nodes (component ids)

| spec_id | role | label |
| --- | --- | --- |
| usage_summary | data_persisted | usage_summary |
| search | group | Optimize Split Decision Trees |
| bound_resource | chrome | resource monitor |
| bound_complexity | chrome | complexity bound |
| bound_partitions | chrome | partition-limit prune |
| tree_a | data_persisted | tree A |
| tree_b | data_persisted | tree B |
| mckp | operation | Optimistic Knapsack Simulation (MCKP) |
| overlay | overlay_panel | Skipping Gain Against Metadata Cost |
| partition_limit | chrome | partition limit tick |
| holdout | operation | Experiment Simplified Assignment On Holdout |
| gate | decision | Does the skipping ratio hold on held-out queries? |
| heuristics | data_carried | Dynamic Feedback: failed split trees |
| tree_frozen | data_accepted | Pre-Built |
| legend | chrome | (see legend keys) |

`tree_a` and `tree_b` are two labelled cards inside `search`, each drawing its
own candidate as a mini binary split tree: a circle for every split point, a
filled square for every leaf container, plain branches between them. The glyph
is a shape, not a walkthrough — no predicate on a branch, no split cycle, no
ordering, no animation. `leaves` is *drawn* rather than printed, so A appears as
a balanced tree of four containers and B as an uneven tree of three, which is
what makes the two candidates visibly different objects. The three bound badges
sit inside the `search` group. `holdout` is the check; `gate` is the yes/no.

### Edges (component ids)

| spec_id | meaning | from | to | label |
| --- | --- | --- | --- | --- |
| e_usage_search | data flow | usage_summary | search | — |
| e_heuristics_search | carried state | heuristics | search | read before the next pass |
| e_overlay_mckp | containment | overlay | mckp | panel on |
| e_search_mckp | beam into spend | search | mckp | every candidate |
| e_search_holdout | beam into check | search | holdout | beam |
| e_mckp_holdout | ceiling only | mckp | holdout | a ceiling, not an assignment |
| e_holdout_gate | check result | holdout | gate | weighted-average skipping ratio |
| e_gate_tree | pass | gate | tree_frozen | yes |
| e_gate_heuristics | fail, write state | gate | heuristics | no |

No edge from any node to itself.

Declared component ids (one per line for the source check):

id: usage_summary
id: search
id: bound_resource
id: bound_complexity
id: bound_partitions
id: tree_a
id: tree_b
id: tree_a_n0
id: tree_a_n1
id: tree_a_n2
id: tree_a_n3
id: tree_a_n4
id: tree_a_n5
id: tree_a_n6
id: tree_a_e0
id: tree_a_e1
id: tree_a_e2
id: tree_a_e3
id: tree_a_e4
id: tree_a_e5
id: tree_b_n0
id: tree_b_n1
id: tree_b_n2
id: tree_b_n3
id: tree_b_n4
id: tree_b_e0
id: tree_b_e1
id: tree_b_e2
id: tree_b_e3
id: mckp
id: overlay
id: partition_limit
id: ov_past_t
id: beam_lbl
id: holdout
id: gate
id: heuristics
id: tree_frozen
id: legend
id: legend_key_operation
id: legend_key_persisted
id: legend_key_frozen
id: legend_key_heuristics
id: legend_key_decision
id: legend_key_tree
id: legend_key_ceiling
id: e_usage_search
id: e_heuristics_search
id: e_overlay_mckp
id: e_search_mckp
id: e_search_holdout
id: e_mckp_holdout
id: e_holdout_gate
id: e_gate_tree
id: e_gate_heuristics

### Derived (asserted in the generator, not typed into the drawing)

```
beam_size = len(beam)          # 2
assert beam_size >= 2
assert all(t.bottom_layer == ingestion_time for t in beam)
assert {t.leaves for t in beam} == {4, 3}      # the two glyphs must differ
assert all(count_drawn_leaves(t) == t.leaves for t in beam)
assert partition_limit.value > 0
assert not any(e.source == e.target for e in edges)
```

## Presentation format

This plate is drawn in the **Lakehouse Plate System**, recorded in
`project_metadata/instructions/lakehouse-plate-system.md`, and generated by
`tools/plates/plate01.py` on the shared kit in `tools/plates/kit.py`. That file is the single
source for the substrate, the two role hues and their measured contrast, the type
scale, the card recipes, the edge lexicon, the legend, and the list of things that never
appear. It governs all three `section_databricks_*` plates. Never restate a hex
here, and never vary one for this plate alone — a change to the look is a change to that
file and therefore to all three plates.

Plate number: **01**.
Rails: four rails on three rows — `1 COLLECT` and `2 SEARCH` side by side on row 1,
the `3 SPEND & CHECK` band on row 2, the `4 GATE` band on row 3.

Roles on this plate:

| component | role |
| --- | --- |
| `usage_summary`, `tree_a`, `tree_b` | `store` |
| `search` | `frame` |
| `mckp`, `holdout` | `operation` |
| `overlay` | chart panel |
| `heuristics` | `attention`, title row `Dynamic Feedback: failed split trees` |
| `gate` | `decision` |
| `tree_frozen` | `accepted`, caps tag `FROZEN` |
| `bound_*`, `legend` | `frame` / chrome |
| `partition_limit` | tick on the overlay, wine dashed |

Title rows, in the one recipe the plate system fixes — a band filled in the card's own
ink, reversed type, left-aligned, any tag beside the name:
Data cards name their kind first: `DL Table: usage_summary` · `Split Tree Candidate: A` ·
`Split Tree Candidate: B` · `Split Tree: Pre-Built` (tagged `FROZEN`) ·
`Chart: Skipping Gain Against Metadata Cost`.

Operations carry their name alone, with no `Operation:` prefix, and that name is the left
pane's own section title in Title Case so a reader can find the paragraph behind it:
`Optimize Split Decision Trees` (the frame, §2.2) · `Optimistic Knapsack Simulation
(MCKP)` (§2.3) · `Experiment Simplified Assignment On Holdout` (§2.4). The carried-state
card reads `Dynamic Feedback: failed split trees`, left-aligned like every other title
row and with no caps tag, and the gate reads
`DECISION` over the whole question, `Does the skipping ratio hold on held-out queries?`,
answered `Yes` and `No` at 13 bold.

`MCKP` appears only as the parenthetical of the expanded name, never as the name itself.

Only this plate's specialisations belong here, because they are facts about this
figure rather than about the system:

- The overlay is a chart panel tied to `mckp` with a containment edge running straight
  into `mckp`'s right edge, not a third flow out of `usage_summary`. Inside it: a log
  container-count axis, a dashed tick at `partition_limit`, the region past that tick
  shaded in `band` and labelled `PAST LIMIT`, `skipping performance` drawn solid in
  `store` ink and `table metadata overhead` dashed in `operation` ink, with both curves
  named inside the panel. The two curves differ in line style as well as hue.
- `e_mckp_holdout` is the ceiling edge and `e_gate_heuristics` is the fail return: both
  wine, dashed and light for the ceiling, solid and heavier for the fail.
- `usage_summary` carries a small `frame` pill reading `ONLY RAW INPUT`,
  because the first thing to notice is that it is the only raw input.
- `usage_summary` prints the sample preview from the instance data under a wine
  `SAMPLE ROWS · one boolean column per query` heading, closed by a `⋮` row. The wide
  boolean shape is the thing a reader has to grasp, so schema alone would under-say it.
  The screening-estimate caveat is a clause of that card's body sentence, not a note
  hung beneath it.
- The `search` frame heads its two candidate cards `BEAM` and its three bound pills
  `BOUNDED BY`, so the frame explains itself without a sentence underneath. The bound
  pills sit in one row, each fitted to its own text.
- Each candidate card holds a mini binary split tree drawn in `store` ink: split points
  are hollow circles, leaf containers are filled squares, branches are plain 1.3 lines.
  The card's only words are its title row and one centred caption,
  `bottom cut: ingestion time`. The circle-and-square distinction is drawn on the plate,
  so the legend carries it as a key.

## Chart and graph specification

- **Shape per role.** Shapes come from the plate system's role table and are
  not restated here. The one shape this plate owns is `overlay`: a chart
  panel tied beneath `mckp`, carrying a log container-count axis, a dashed
  tick at `partition_limit`, the region past that tick shaded, and the two
  named curves. It is not a third tree and not a knapsack ladder.
- **Edge semantics.** Solid arrow = data flow. Dashed arrow = ceiling only
  (`e_mckp_holdout`) or attachment (`e_overlay_mckp`). The fail edge carries heuristics
  and is heavier than a plain flow. Every edge but `e_usage_search` names what travels
  on it.
- **Layout.** Four numbered rails on three rows, hand-placed, `--no-layout`. Each row
  break is read like a line break: out of the right of one row, into the left of the
  next.
  1. Row 1 left — `COLLECT`: `usage_summary` under its `ONLY RAW INPUT` pill. The rail
     takes its own height and stops; it is not padded down to match its neighbour.
  2. Row 1 right — `SEARCH`: the `search` frame holding `tree_a`, `tree_b` and the three
     bound badges, and nothing else. Both flow edges leave the frame sideways —
     `every candidate` from the left into the rail-1 gutter, `beam` from the right into
     the outer gutter.
  3. Row 2 — the `SPEND & CHECK` band: `mckp`, its `overlay` panel, and `holdout` across
     one row, the two operation cards centred against the taller panel. The ceiling edge
     runs in a lane along the foot of the band, under the panel, so it crosses nothing.
  4. Row 3 — the `GATE` band: `gate` at the left, under the wrap from `holdout`, and the
     two things it produces stacked to the right of its two exits — `tree_frozen` beside
     `Yes`, `heuristics` beside `No`, both sized to the same width. The two exits leave
     different faces of the diamond, so neither stub is drawn in the other's colour. The
     gate is drawn large enough to carry its whole question at 13 bold. `heuristics`
     lives here, where it is written, rather than in rail 2 where it is read; the long
     edge on the plate is therefore `e_heuristics_search`, the hand-back into the next
     pass, which leaves the card's top edge so it never reads as `No` carrying on
     through. "yes" runs right into it; "no" drops to a lane below the band, runs
     out to the right margin, climbs, and re-enters `heuristics` from beneath — an outer
     retry drawn as a circuit around the whole plate.
- **Grouping.** `search` contains `tree_a`, `tree_b`, and the three bound
  badges. The group means "beam under a bound".
- **Legend.** One horizontal row on the top bar, left-aligned, directly under the
  title: persisted table; frozen output; operation; dynamic feedback; decision gate;
  split point · leaf container; dashed = ceiling only.
- **One sentence per card.** No card carries more than one sentence of body. What the
  step does in detail is §2.1–§2.4 of the walkthrough, which the reader reaches through
  the node's name:
  `usage_summary` — "Keep one boolean per query and per row, aggregated into hour bins";
  `mckp` — "Spend the table partition limit as a container budget, one container at a
  time, on every candidate tree";
  `holdout` — "Replay the candidate trees against held-out queries under one global
  equal-size container policy";
  `heuristics` — "Track underperforming decisions to help guide the next search
  iteration";
  `tree_frozen` — "Hand the tree that held up on holdout to the splitter on the write
  path".
- **Encoding redundancy.** Gate yes/no is the diamond plus the words.
  Heuristics are dashed plus the caps tag. Frozen is the caps tag `FROZEN`
  plus the solid accepted field. The gate's answers are set at node-label weight, not at
  edge-label weight, because they are the outcome the plate turns on. Training beam versus holdout is placement plus label.

Title: *Deployment Process Flow*, printed by the pane that carries the figure, **not drawn
inside it** — and no kicker, subtitle or footnote anywhere. The legend strip is
the top row of the drawing. What to notice first is recorded in **Emphasis**
above, and the plate says it by placement.
