# Business Insights as Byproduct illustration

Product requirements for the Business Insights as Byproduct section
of the demonstration GUI: a left walkthrough that states how tuning a
layout from query usage packs idle records for skipping and names which
records are useful, beside a right pane that shows that reading on one
domain map.

**Authority.** This document is the product spec for Business Insights as
Byproduct. [`simulator-spec.md`](simulator-spec.md) governs the
application shell, theme, and layout.
[`problem-statement.md`](../../site/docs/problem-statement.md)
remains the authority on the formal model. Where this document and the
product spec disagree on shell, theme, or layout, the product spec wins.
Where they disagree on this section's content, this document wins.

**No recommendation.** The pane may show that unused clusters on a usage
map are the same populations a skip layout would quarantine, and it may
argue that this second reading is a by-product of layout work already
paid for. It does not select, rank, or recommend an assignment strategy,
a search method, or a fitness. It reports no measured outcome, and
12.6.4 continues to bar it from asserting a number of its own.

---

## 1. Role and reading order

Business Insights as Byproduct is the fifth section. It sits after
Go Live on Databricks Lakehouse. The section heading is the navigation
label.

Two panes, each independently scrollable on a wide viewport. The
walkthrough sits on the **left**; figure `signal.ecommerce` sits on the
**right**. On a wide viewport the left pane is **30%** of the split and
the right pane is **70%**. Below the split breakpoint the panes stack in
that order and the page scrolls once.

Sequence:

1. the two paragraphs of §2.2, on the left;
2. figure `signal.ecommerce`, on the right.

The pane does not use the word *teach*. The pane does not use the word
*production*. Conclusions stay in the last sentence of each paragraph.
There is no labeled takeaway.

---

## 2. Reader-facing prose

### 2.1 Source

The prose is the author's own statement of the argument, used directly. Only
grammatical corrections have been applied to it: `querie` to `queries`,
`decision tree based` to `decision-tree-based`, `insights` to `insight` after
`this type of`, `KPI` to `KPIs` after `different types of`, `such layout` to
`such a layout`, `trend` to `trends`, and `&` to `and`.

The fragment copies §2.2 as written. A change to the argument is the author's to
make here first.

### 2.2 Prose

In this micro-container architecture, a data layout minimizes record materialization waste by clustering together data points selected by future queries. The research process constructs a decision-tree-based model to predict query density conditioned on record features. Depending on the query context, this type of query density insight can reveal different types of business KPIs. For instance, a data layout optimized for ecommerce queries showing warehouse shipment can reveal high volume SKUs; the evolution history of such a layout, provided it adapts continuously to the latest query patterns, can reflect product seasonal sales trends.

A heatmap is a handy visualization tool to identify major hot and cold spots with regard to data usefulness.

### 2.3 Terms the prose introduces

Three terms in §2.2 are not defined by the formal statement. They stand as the
author wrote them; this note records what they correspond to, for a reader
arriving from the other sections.

| in the prose | in the formal statement |
| --- | --- |
| micro-container architecture | the container model, and the whole-container `FETCH` |
| record materialization waste | waste, and materialized volume |
| query density | per-group selection rate over partitionable features |

*Heatmap* names the instrument. The figure specified in §3 is the Finviz-style
treemap that serves as one.

The prose asserts no number and contains no digit.

## 3. Figures

The right pane contains exactly one figure. Its raster is rendered and mounted
at `site/figures/img/section_kpi_ecommerce.png`. The figure is a title
and the stage carrying that raster. The prompt is the authority on what
the raster shows.

| id | Visible title | Prompt |
| --- | --- | --- |
| `signal.ecommerce` | Ecommerce warehouse usage map | [`section_kpi_ecommerce_prompt.txt`](../../resources/img_prompt/section_kpi_ecommerce_prompt.txt) |

The map is a subdivided treemap in the Finviz market-map language:

- group = product department;
- tile = product line;
- area = on-hand inventory;
- fill colour = selection rate, green at a low rate and red at a high one.

The map reads selection rate as query demand over a two-week ingestion
window, on a 0%-25% axis. It is built five levels deep: level 1
is the map, level 2 the department, levels 3-5 product lines. Below level
2 the depth is probabilistic, each cell continuing with probability 0.75,
and a scan-and-mutate pass then cuts again in any department that did not
reach level 4, so no department is drawn as a titled empty box. That puts
16 departments and about 80 leaves on the map. Every rectangle is
labelled: the department at level 2, and each leaf with its subcategory.

Fill runs green to red: a low rate is the pale green `#EEF4F0` end, a
high rate the wine `#7A1F2B` end, with lightness falling along the ramp
so the green end is also the pale end. Fill is the only channel the map
carries — no stroke, halo or pattern stands for a band, because the axis
measures the rate continuously and a threshold would assert a cliff the
data does not have. Every rectangle is a plain square-cornered shape
with a solid border. Each department is named in a light-orange title
cell inside a visible border, and each leaf carries its subcategory
name; no figure is printed beside either. The rate is read from the
legend, which is the colour axis and nothing else: no area note and no
band key. Green and wine are the only hues that carry a value, and a
light orange is admitted for the title cell chrome alone. Light surface
only.

A visual change starts a new authoring pass from that prompt.

---

## 4. Hypothesized instances

The map does not use a provider dataset, the Data Skipping
Experiment catalog, or the committed scenario file. Tile states are
hypothesized. They exist to present the reading, not to report a scored
workload. This section's figure is outside 12.6.4's catalog / manifest
/ scenario trace.

The figure owns its instance. Every number the raster is built from is
taken from its prompt table. The column contract for those
tables is `group`, `tile_id`, `label`, `size`, `kpi`, `band`, where
`band` is `hot`, `warm`, or `cold`. A visible cold pocket is present by
construction.

---

## 5. Requirements map

| id | requirement |
| --- | --- |
| I1 | Two independently scrolling panes; left 30% / right 70% on a wide viewport |
| I2 | The two paragraphs of §2.2 on the left; figure `signal.ecommerce` on the right |
| I3 | The walkthrough copies §2.2 verbatim. The figure title in §3 stays fixed |
| I3.1 | No paragraph or title instructs the reader in decoding a figure; the map carries its own legend |
| I3.2 | The prose contains no digit |
| I4 | Figure id `signal.ecommerce` |
| I5 | The map is a Finviz-style treemap: area is on-hand inventory, fill colour is selection rate |
| I5.1 | Every department contains level 3 and level 4; none is drawn as a titled box with no substructure |
| I5.2 | Every rectangle is labelled: the department at level 2 in a light-orange title cell with a visible border, each leaf with its subcategory |
| I6 | Fill runs green (low rate) to red (high rate) and is the only channel; no band marking; square corners throughout |
| I7 | Hypothesized instance; columns `group,tile_id,label,size,kpi,band` |
| I8 | No assignment strategy, search method, or fitness is selected or recommended |
| I9 | The pane does not use *teach* or *production* |
| I10 | The raster is rendered and mounted from `site/figures/img/` |
| I11 | Type is the 15px walkthrough size; the walkthrough fills the left pane |
