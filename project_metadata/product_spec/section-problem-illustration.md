# Problem Statement illustration

Product requirements for the graphical illustration in the Problem Statement
section of the demonstration GUI. The left pane starts with one dispensary counter batch in ordinary language, uses
the medicine-cabinet figure to map that retrieval to a data-warehouse fetch, then uses
the smart-organizer figure to show what demand-informed rearrangement can change before
pointing the reader to the definitions and formula in the right pane.

**Authority.** This document is the product spec for Problem Statement.
[`simulator-spec.md`](simulator-spec.md) governs the application shell, theme, and layout.
[`problem-statement.md`](../../resources/html/problem-statement.md) remains the
authority on the formal model. Where this document and the product spec disagree on
shell, theme, or layout, the product spec wins. Where they disagree on this
section's content, this document wins.

**No recommendation.** The walkthrough may identify record assignment as tunable and
show that a different assignment can materialize fewer unselected records. It does not
select, rank, or recommend an assignment strategy.

---

## 1. Role and reading order

The illustration is the reader's first exposure to the problem. It teaches the problem
as one ordered chain:

1. a familiar medicine-cabinet retrieval establishes useful and wasted handling;
2. the first figure places technical names beside those familiar objects and actions;
3. the second figure shows how demand history can inform a different restocking scheme.

- The illustration sits on the **left**. The right column opens with the terminology
  dictionary and the formal statement below it.
- Below the split breakpoint the panes stack in that order.
- The pane is independently scrollable on a wide viewport.
- The sequence is closed: it contains no outbound artifact links or alternate scenario.

---

## 2. Vocabulary sequence

### 2.1 Medicine-cabinet mental model

The opening prose uses ordinary dispensary language: dispensary, medicine cabinet, small
drawer, medicine box, prescriptions, counter batch, prescribed, drawer chart, handling,
putting back unused, and wasted effort. It establishes the complete retrieval before the
first raster introduces technical parentheticals.

The technical meaning still governs what is drawn:

- the wall of small drawers corresponds to the corpus / data warehouse;
- one small drawer corresponds to a storage container;
- the fixed, equal number of boxes per drawer corresponds to container capacity;
- one medicine box corresponds to a record;
- one counter batch of patients' prescriptions corresponds to a query;
- prescribed boxes correspond to selected records;
- the drawer chart corresponds to the index table;
- pulling a named drawer to the counter corresponds to container activation;
- every box that reaches the counter corresponds to materialized volume;
- boxes handled and put back unused correspond to waste;
- a drawer the chart never names corresponds to a skipped container;
- deciding which medicines share a drawer corresponds to the assignment strategy.

Those correspondences govern the story. They become reader-facing labels in the first
figure and adjacent technical prose, after the ordinary account has supplied their
meaning.

### 2.2 Technical stage

The first figure and the prose after it introduce each technical term beside the
medicine-cabinet object or action it replaces:

| medicine-cabinet account | data-warehouse fetch |
| --- | --- |
| dispensary's medicine cabinet — a wall of small drawers | corpus / data warehouse |
| one small drawer | storage container |
| fixed, equal boxes per drawer | container capacity |
| one medicine box | record / event |
| one counter batch of patients' prescriptions | query |
| boxes those prescriptions call for | selected records |
| drawer chart on the cabinet frame | **index table** |
| pharmacist pulls the whole drawer to the counter | storage-container activation |
| one prescribed box pulls the drawer | activation is a max |
| every box that lands on the counter | materialized volume |
| boxes handled and put back unused | waste |
| drawer the chart never names; it stays shut | skipped container |
| deciding which medicines share a drawer | record layout / assignment strategy |

No glossary precedes the scenario. The scenario supplies the meaning first; the
technical term follows in the figure's parenthetical labels or the adjacent prose.

### 2.3 Demand-informed restocking

The second figure broadens from one counter batch to demand history. It may introduce
usage report, average pulls per hour, demand band, threshold, and rearranged drawer. The
adjacent prose maps the new arrangement to record assignment while keeping the cabinet,
equal drawer capacity, and retrieval mechanism fixed.

The displayed demand-band rule is a deliberately simple demonstration fixture. Neither
the figure nor the prose ranks it against another assignment or recommends it.

### 2.4 Right column

The right column opens with the terminology dictionary and continues with the
formal statement. The left pane does not restate that list.

---

## 3. Medium and visual system

The authored fragment lives under `resources/html/` and embeds these committed
raster figures:

- `resources/img/section_a_medical_cabinet.png`;
- `resources/img/section_a_smart_organizer.png`.

The two figures use:

- flat editorial drawing, not photorealism, 3D, or a screenshot;
- the warm paper ground and ink specified by the UI tokens;
- page sans for labels;
- one restrained medicine-box palette;
- directional arrows where process order needs them;
- text, shape, outline, or pattern in addition to colour for every state.

No figure contains UI chrome or server racks. Each raster scales to the pane width
without changing its aspect ratio.

---

## 4. Shared scenario

Both figures retain the same medicine-cabinet setting, medicine inventory, and
equal-capacity small drawers. The first follows one three-prescription counter batch.
The second broadens to demand history for that inventory and rearranges which medicines
share drawers.

This progression is load-bearing: the second figure changes the evidence available and
the drawer arrangement, not the capacity or the whole-drawer retrieval mechanism. It
illustrates a possible restocking rule; it does not claim an observed improvement for
the first figure's particular counter batch.

---

## 5. Ordered sequence

The pane carries these four beats, in order:

1. medicine-cabinet prose describing one counter batch and its wasted effort;
2. `A.medical-cabinet`;
3. technical prose mapping the retrieval and introducing demand-informed restocking;
4. `A.smart-organizer`.

No other prose stage or illustration appears.

---

## 6. Illustration prompts

### 6.1 After (1), before (2): `A.medical-cabinet`

Visible raster title: *Fulfill Prescription Requests*.

Embed `resources/img/section_a_medical_cabinet.png`. It shows one three-prescription
ask, the inventory-catalog lookup, nine equal-capacity drawers, three drawers opened
whole, and the split between three boxes kept and nine boxes put back. Its parenthetical
labels introduce query, lookup table, storage containers, and query response at the
boundary between the ordinary story and the technical explanation.

The caption states the observation: the catalog narrows which drawers to open, but each
opened drawer brings every box inside it to the counter.

### 6.2 After (2), before (3): `A.smart-organizer`

Visible raster title: *Optimize inventory layout by learning from demand history*.

Embed `resources/img/section_a_smart_organizer.png`. It shows the usage report, average
pulls per hour, two demand thresholds, and a new equal-capacity drawer arrangement
grouped into low, medium, and high demand bands.

The prose explains that demand history supplies evidence for changing which medicines
share a drawer. The caption identifies the displayed threshold rule as deliberately
simple and does not rank or recommend it.

---

## 7. Requirements map

| id | requirement |
| --- | --- |
| I1 | Illustration on the left; terminology then formal framework on the right; that order when stacked |
| I2 | Ordinary medicine-cabinet prose establishes the mental model before technical labels |
| I3 | The first raster maps the retrieval at the boundary to the technical explanation |
| I4 | Whole-drawer cost and the assignment opportunity are explicit |
| I5 | The second raster shows demand-informed restocking |
| I6 | The walkthrough does not end on a handoff paragraph |
| I7 | Exactly two committed raster illustrations appear at their specified locations |
| I8 | Every illustration carries its specified visible raster title |
| I9 | Medicine inventory, equal drawer capacity, and retrieval mechanism remain continuous |
| I10 | Technical terms are defined through the scenario, not a preceding glossary |
| I11 | Authored HTML embeds local assets and contains no outbound links or alternate scenario |
| I12 | No assignment strategy is selected, ranked, or recommended |
