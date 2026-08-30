# Section D illustration

Product requirements for Section D of the demonstration GUI: a static
strategy illustration of weighted-Gini split search. The left pane is text
only. The right pane is figures only. Both panes scroll independently on the
same theme as Section A.

**Authority.** This document expands [`ui-spec.md`](ui-spec.md) §12.8 without
changing it. [`problem-statement.md`](../resources/graphics/problem-statement.md)
remains the authority on the formal model.
[`introduction_writing_style.md`](guideline/introduction_writing_style.md) is
the writing contract for the left pane. Where this document and the UI spec
disagree, the UI spec wins and the disagreement is a defect.

**No recommendation.** The walkthrough may show that two splits of the same
instance produce different Gini values, and that a search can stop when
marginal return falls. It does not select, rank, or recommend an assignment
strategy.

---

## 1. Role and reading order

Section D teaches one screening idea in three stages:

1. inequality of wealth across population shares, as a Gini / Lorenz
   construction, without warehouse vocabulary;
2. the same construction on fetch frequency, as a screen for logical splits;
3. a heuristic that grows a group-by-chain or a selective tree and stops
   when the next cut returns too little.

- The walkthrough sits on the **left**. The figures sit on the **right**.
- Below the split breakpoint the panes stack in that order.
- Each pane is static and independently scrollable on a wide viewport.
- The left sequence is closed except for wiki definition links at the first
  introduction of a public technical term. It contains no outbound artifact
  links and no alternate scenario.

The left pane follows the writing contract: each stage is mental model,
terms, formula, observations, takeaway, in that order. Graphics are step 4
of that flow and live only on the right. A learning graph used to order the
stages is authoring metadata and does not appear in either pane.

---

## 2. Vocabulary sequence

### 2.1 Inequality-only stage

The first stage may use only ordinary inequality language: town,
neighborhood, resident, wealth, share, density, unevenness, bow, diagonal,
and the public technical terms **Lorenz curve** and **Gini coefficient**,
each introduced with a wiki weblink. Its reader-facing prose and the first
figure contain none of these technical words: warehouse, container, record,
query, index, materialized, selected, layout, assignment, strategy, skip.

The technical meaning still governs what the later stages will map:

- a resident corresponds to an event;
- wealth corresponds to `used_count`;
- a neighborhood corresponds to a terminal group;
- a poor neighborhood corresponds to a cold group that a query can skip.

Those correspondences are authoring constraints, not labels shown in the
first stage.

### 2.2 Warehouse stage

The second stage repeats the first construction and introduces each
technical term at the moment it replaces a town object:

| inequality account | warehouse account |
| --- | --- |
| resident | event / record |
| wealth | `used_count` (fetch frequency) |
| neighborhood | terminal group of a split |
| wealth density $d_g$ | usage density $U_g / n_g$ |
| a poor neighborhood with many residents | a cold group with large population share |
| the bow $G(S)$ | population-weighted Gini of the split |

The stage states that $G(S)$ screens a logical split and does not equal
the aggregate waste ($W(\lambda)$, defined in §2.5).

### 2.3 Search stage

The third stage names the two constructions that share that fitness — a
group-by-chain and a selective tree — and the stop rule on marginal
efficiency. It hands the reader to the right pane for the four figures
and names Section B as the surface that scores a physical layout. The
handoff does not select, rank, or recommend a chain.

---

## 3. Medium and visual system

All drawings live in one authored fragment under `resources/graphics/`.
The medium is semantic HTML, CSS, and inline SVG: not a Cursor
`canvas.tsx`, not an HTML5 `<canvas>`, and not generated static images.

The four figures use:

- flat editorial drawing, not photorealism, 3D, or a screenshot;
- the wine-red / warm-rose / dark-green / cool-sage explainer family of
  the Section A illustration prompts (`resources/img_prompt/`), not the
  12.7 gray series and not orange;
- page sans for labels;
- one restrained repeating palette;
- single-stroke directional arrows;
- text, shape, outline, or pattern in addition to colour for every state.

No figure contains UI chrome, server racks, or a spreadsheet grid.
The right pane contains no editorial lede. A one-line figcaption may
name what is drawn.

---

## 4. Shared instance

Every warehouse figure depicts the same twelve events as ui-spec
12.5.7.1. The second figure is the first use of that instance; the
third and fourth keep the events, features, and selections fixed and
change only the split construction.

| field | value |
| --- | --- |
| events | `r01`–`r12` |
| features | region, event type |
| containers in the C appendix (not drawn here) | `c1` = `r01`–`r04`, `c2` = `r05`–`r08`, `c3` = `r09`–`r12` |
| queries | `q1` = {`r01`, `r03`}, `q2` = {`r03`, `r06`}, `q3` = {`r10`, `r11`} |
| usage wealth | `used_count` derived from that log: $U=6$; unselected events have `used_count` $0$ |

Rows: `r01` us-east click (1); `r02` us-east click (0); `r03` us-east
view (2); `r04` us-west click (0); `r05` us-west view (0); `r06` eu-west
click (1); `r07` eu-west view (0); `r08` ap-south click (0); `r09`
ap-south view (0); `r10` us-east purchase (1); `r11` us-west purchase
(1); `r12` eu-west purchase (0).

Instance arithmetic, not a measurement:

- event-type split: $G(S)=1/9$, three groups, usage nearly even;
- region split: $G(S)=7/18$, four groups, `us-east` holds $4/6$ of usage,
  `ap-south` holds two events and none of the usage.

A later figure may change only the relationship its prompt names.

---

## 5. Ordered sequence

The left pane carries these three stages, in order:

1. inequality-only prose (`§1` of the walkthrough);
2. warehouse mapping (`§2` of the walkthrough);
3. search trajectory and right-pane handoff (`§3` of the walkthrough).

The right pane carries these four figures, in order, each the graphic
step of the matching stage:

1. `D.lorenz-wealth` — stage 1;
2. `D.split-comparison` — stage 2;
3. `D.selective-tree` — stage 3;
4. `D.search-trajectory` — stage 3.

No other prose stage or illustration appears.

---

## 6. Illustration prompts

### 6.1 `D.lorenz-wealth`

Visible title: *When wealth sits in few hands*.

Lorenz diagram only. Draw the unit square with “population share” on the
horizontal axis and “wealth share” on the vertical axis. Draw the
equality diagonal. Draw one path that stays near the diagonal (even
neighborhoods) and one path that sags then rises (wealth in few
neighborhoods). Label the bow as the Gini coefficient. Use no warehouse
vocabulary, symbols of a fetch, or technical mapping labels.

### 6.2 `D.split-comparison`

Visible title: *The same twelve records, two cuts*.

Place two groupings of the same twelve events side by side. Each group
is a bar whose width is population $n_g$ and whose fill or hatch plus
label is usage density $d_g$ — never colour alone. Left: event type
(click / view / purchase), nearly even usage, $G=1/9$. Right: region
(us-east / us-west / eu-west / ap-south), `us-east` hot, `ap-south`
cold and marked as a skip candidate, $G=7/18$.

### 6.3 `D.selective-tree`

Visible title: *A chain multiplies every branch; a tree need not*.

One root, then the four region children. On the left, split every region
by event type (the full chain). On the right, split only `us-east` by
type (the selective tree). Same twelve events. Do not label either
construction as best.

### 6.4 `D.search-trajectory`

Visible title: *Stop when the next cut returns too little*.

A path of candidate splits on axes “group count” and “Gini”. Mark
$S_0$ (one group, $G=0$), the region cut, then two children: the full
chain and the selective tree. Draw a stop region where further cuts
return little Gini per new group. This is a trajectory, not a
leaderboard. Do not rank the candidates.

---

## 7. Writing contract

The left pane is
[`section-d-walkthrough.md`](section-d-walkthrough.md). It is a technical
presentation. Each stage uses the six-step flow in
[`introduction_writing_style.md`](guideline/introduction_writing_style.md).
A formula, or two or more new terms, is introduced with a definition
table — one row per term. The first mention of Lorenz curve and of Gini
coefficient is a wiki weblink; later emphasis uses the citation form
*the concept description* (`symbol`, defined in §X). The walkthrough
contains no figure markup.

---

## 8. Requirements map

| id | requirement | in the spec |
| --- | --- | --- |
| I1 | Walkthrough on the left; figures on the right; that order when stacked | 12.8 |
| I2 | Inequality-only account precedes warehouse vocabulary | 12.8.1.1 |
| I3 | Warehouse stage maps the same construction onto used_count and splits | 12.8.1.2 |
| I4 | Search stage names chain, tree, trajectory, and the stop rule | 12.8.1.3 |
| I5 | $G(S)$ screens splits and does not equal $W(\lambda)$ | 12.8.1.5 |
| I6 | Exactly four illustrations at their specified locations | 12.8.3 |
| I7 | Every illustration carries its specified visible title | 12.8.3 |
| I8 | One twelve-event instance recurs from the second figure onward | 12.8.4 |
| I9 | Left pane follows the writing contract | 12.8.6 |
| I10 | Wiki weblink only at first introduction of a public technical term | 12.8.6.1 |
| I11 | Static authored HTML and inline SVG; no artifact links or alternate scenario | 12.8.5 |
| I12 | No assignment strategy is selected, ranked, or recommended | 1.2, 12.8.1.4 |
| I13 | Left walkthrough fills the pane; type is one step above Section A | 12.8.1.6, 12.8.7 |
| I14 | Figures use the wine / sage explainer family, not 12.7 gray | 12.8.3 |
