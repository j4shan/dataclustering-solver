# Section A illustration

Product requirements for the graphical illustration in Section A of the demonstration
GUI. The left pane starts with one closet retrieval in ordinary language, repeats that
same retrieval as a data-warehouse fetch, then points the reader to the definitions,
formula, and configurable solution pattern in the right pane.

**Authority.** This document expands [`ui-spec.md`](ui-spec.md) §§12.3.5–12.3.6.1
without changing them. [`problem-statement.md`](problem-statement.md) remains the
authority on the formal model. Where this document and the UI spec disagree, the UI spec
wins and the disagreement is a defect.

**No recommendation.** The walkthrough may identify record assignment as tunable and
show that a different assignment can materialize fewer unselected records. It does not
select, rank, or recommend an assignment strategy.

---

## 1. Role and reading order

The illustration is the reader's first exposure to the problem. It teaches one scenario
twice:

1. as a familiar closet retrieval without database vocabulary;
2. as the corresponding fetch process with the technical mapping made explicit.

A final comparison isolates what a **smart organizer** can change, then the prose hands
the reader to the right pane for the formal model, objective, and effect of data
clustering.

- The illustration sits on the **left**. The problem statement sits on the **right**.
- Below the split breakpoint the panes stack in that order.
- The pane is static and independently scrollable on a wide viewport.
- The sequence is closed: it contains no outbound artifact links or alternate scenario.

---

## 2. Vocabulary sequence

### 2.1 Closet-only stage

The first stage may use only ordinary closet language: closet, drawer, garment,
inventory list, morning, outfit, handling, putting back, wasted effort, and **smart
organizer**. Its reader-facing prose and drawing contain none of these technical words:
data, warehouse, storage, container, record, row, query, index, materialized, selected,
layout, assignment, strategy.

The technical meaning still governs what is drawn:

- drawer corresponds to storage container;
- closet corresponds to data warehouse;
- wasted effort corresponds to records materialized but not selected.

Those correspondences are authoring constraints, not labels shown in the first stage.
The stage ends with a question asking what a **smart organizer** could change.

### 2.2 Technical stage

The second stage repeats the first scene and introduces each technical term at the
moment it replaces a closet object or action:

| closet account | data-warehouse fetch |
| --- | --- |
| closet | data warehouse |
| drawer | storage container |
| garment | record |
| morning's outfit request | query |
| inventory list | **index table** |
| pulling out a drawer | activating a storage container |
| garments lifted | records materialized |
| garment kept for the outfit | record selected |
| garments lifted and put back | records materialized but not selected |
| deciding which garments share drawers | record layout / assignment strategy |

No glossary precedes the scenario. The scenario supplies the meaning first; the
technical term follows.

### 2.3 Right-panel handoff

The final prose tells the reader that the right panel presents:

- definitions of the key concepts;
- the objective formula;
- the system-wide data-skipping model and the effect of data clustering.

The handoff does not select, rank, or recommend an assignment strategy.

---

## 3. Medium and visual system

All drawings live in one authored fragment under `resources/graphics/`. The medium is
semantic HTML, CSS, and inline SVG: not a Cursor `canvas.tsx`, not an HTML5 `<canvas>`,
and not generated static images.

The three figures use:

- flat editorial drawing, not photorealism, 3D, or a screenshot;
- the warm paper ground and ink specified by the UI tokens;
- page sans for labels;
- one restrained, repeating garment/record palette;
- single-stroke directional arrows;
- text, shape, outline, or pattern in addition to colour for every state.

No figure contains UI chrome, server racks, or a spreadsheet grid.

---

## 4. Shared scenario

Every figure depicts the same request, object set, and initial grouping. The second
figure repeats the first figure's composition with technical labels. The third keeps
the query, records, selected records, **index table** result, and storage-container
capacity fixed; only record assignment changes.

This continuity is load-bearing. A later figure may change only the relationship named
by its prompt, so a reader never has to determine whether an apparent improvement came
from a different request or different data.

---

## 5. Ordered sequence

The pane carries these six beats, in order:

1. closet-only prose describing one morning's retrieval and its wasted effort;
2. `A.closet-problem`;
3. technical prose walking through the same retrieval as a data-warehouse fetch;
4. `A.fetch-process`;
5. `A.smart-organizer`;
6. a short handoff to the detailed framework in the right pane.

No other prose stage or illustration appears.

---

## 6. Illustration prompts

### 6.1 After (1), before (2): `A.closet-problem`

Visible title: *One outfit, one whole drawer*.

Show one morning's outfit request beside a closet with an inventory list on its door.
The list points to one drawer, and the whole drawer has been pulled out. Separate the
wanted garment from the other garments that were lifted and must be put back. Make the
wasted effort visibly larger than the useful effort.

The figure contains no database vocabulary, symbols, formulas, code, or technical
mapping labels. The prose after the figure asks: what would a **smart organizer**
change?

### 6.2 After (2): `A.fetch-process`

Visible title: *The same fetch in a warehouse*.

Repeat `A.closet-problem` as one left-to-right process:

`query request → index table lookup → storage-container activation → records
materialized → records selected / records materialized but not selected`.

Map the closet objects and actions using §2.2. Selected and unselected materialized
records differ by label and visual treatment, never by colour alone. Accompanying prose
states the shared challenge: both scenarios pay for the whole containing unit. It then
identifies record assignment as the opportunity for improvement.

### 6.3 Between (2) and (3): `A.smart-organizer`

Visible title: *What a smart organizer can change*.

Place two versions of the same warehouse fetch side by side. Hold the query, records,
selected records, **index table** result, and storage-container capacity fixed. Change
only which records share storage containers. The second version materializes fewer
unselected records.

The comparison introduces the assignment effect that the right panel formalizes. It
does not label either assignment as best and does not recommend a strategy.

---

## 7. Requirements map

| id | requirement | in the spec |
| --- | --- | --- |
| I1 | Illustration on the left; formal framework on the right; that order when stacked | 12.3.1, 12.3.5 |
| I2 | Closet-only account precedes every technical term | 12.3.5.1, 12.3.6 |
| I3 | Closet stage ends with the **smart organizer** question | 12.3.5.1.1 |
| I4 | Technical stage repeats and maps the same scenario | 12.3.5.1.2, 12.3.5.3 |
| I5 | Shared challenge and improvement opportunity are explicit | 12.3.5.1.2 |
| I6 | Final prose points to the formal problem statement on the right | 12.3.5.1.3 |
| I7 | Exactly three illustrations at their specified locations | 12.3.5.2, 12.3.5.3 |
| I8 | Every illustration carries its specified visible title | 12.3.5.2 |
| I9 | One scenario and composition recur throughout | 12.3.5.3 |
| I10 | The third figure changes record assignment and nothing else | 12.3.5.3 |
| I11 | Technical terms are defined through the scenario, not a preceding glossary | 12.3.6.1 |
| I12 | Static authored HTML and inline SVG; no outbound links or alternate scenario | 12.3.5 |
| I13 | No assignment strategy is selected, ranked, or recommended | 1.2 |
