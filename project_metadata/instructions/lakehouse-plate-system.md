# Lakehouse Plate System

**Objective.** One presentation format for the three Go Live on Databricks Lakehouse
figures, so a reader who has learned to read one plate can read the other two without
relearning anything — and so that a reader arriving from Problem Statement does not
have to relearn the colours either.

**Scope.** `section_databricks_layout_planning`,
`section_databricks_ingestion`, and `section_databricks_query`. Each of
those prompts records what its own plate depicts and points here for how it looks. A
change here is a change to all three.

## 1. Where the choices come from

Nothing below is a taste call dressed up as a rule. Each decision has a source.

| Decision | Grounded in |
| --- | --- |
| the two role hues and every substrate tone | the exhibit's house palette, fixed by the Problem Statement figure prompts (`section_problem_cabinet_problem_prompt.txt`, `section_problem_demand_layout_prompt.txt`). One palette across the exhibit, slot for slot |
| every ink / field pair | WCAG 2.2 SC 1.4.3 (text at least 4.5:1) and SC 1.4.11 (meaningful non-text at least 3:1 against adjacent colour) |
| shape and word redundancy | measured greyscale and dichromat collapse of the role inks — see §6. This is load-bearing here, not a courtesy |
| card and panel sizes | measured from the text each one holds; see §7 |
| what is left off the plate | Tufte's data-ink audit: for every mark, is it encoding data or helping interpret it; if neither, it goes |
| three token layers | standard design-token practice — primitive values, semantic roles, component recipes |

Sources are listed at the foot of this file.

## 2. Token layers

Never write a hex into a figure generator. Write a component recipe, which reads a
semantic role, which reads a primitive.

```
primitive   ink.wine = #7A1F2B
semantic    role.operation.ink = ink.wine
component   card.operation.stroke = role.operation.ink
```

In a `.drawio` source, `spec_category` carries the plate's own semantic category from
its prompt's node table — `data_persisted`, `data_carried`, `decision` and so on. Each
prompt's Presentation format section maps those categories onto the roles in §4. The
category says what the thing is; the role says how it is drawn.

## 3. Substrate

| Token | Value | Use |
| --- | --- | --- |
| `paper` | `#FCFCFB` | the canvas, and type on a `store` header bar |
| `ink` | `#0B0B0B` | body type on any light field — 19.2:1 on paper |
| `ink.muted` | `#52514E` | secondary body type, chrome strokes, chart axes — 7.7:1 on paper |
| `rule` | `#DEDEDE` | hairlines, table rules, rail borders. Decorative boundaries only |
| `band` | `#F3F3F3` | the tint behind a numbered rail, a table header row, a chart's shaded region, and the mask behind an edge label |
| `card` | `#FFFFFF` | the body of a store card and of a chart panel |

`rule` on `band` measures 1.21:1. That is deliberate: a rail border groups, it never
carries information. What a rail means is carried by its number badge and its name.

## 4. Roles

Two meaningful hues and one neutral. A third hue is not available. The plates carry
six roles on those two hues, so **shape and word do the separating** and hue only
reinforces — see §6.

| Role | Ink | Field | Ink on paper | Ink on own field | `ink` body on field |
| --- | --- | --- | --- | --- | --- |
| `operation` | wine `#7A1F2B` | rose `#F8EEF0` | 9.94:1 | 8.98:1 | 17.3:1 |
| `attention` | wine `#7A1F2B` | rose `#F8EEF0` | 9.94:1 | 8.98:1 | 17.3:1 |
| `decision` | wine `#7A1F2B` | rose `#F8EEF0` | 9.94:1 | 8.98:1 | 17.3:1 |
| `store` | green `#1B4D3E` | card `#FFFFFF` | 9.40:1 | 9.65:1 | 21.0:1 |
| `accepted` | green `#1B4D3E` | sage `#EEF4F0` | 9.40:1 | 8.65:1 | 17.7:1 |
| `frame` (neutral) | `#52514E` | `#F3F3F3` | 7.74:1 | 7.16:1 | 18.1:1 |

Two derived tones, each used only for the `<type>` half of a title row set on that
role's filled band, one clear step below `paper` so the type reads as subordinate to the
name without dropping below AA: `sage.dim` `#C9DAD2` on green, 6.64:1; `rose.dim`
`#E8C6CB` on wine, 6.50:1. On a neutral band the same job is done by `rule` `#DEDEDE`,
5.90:1 on `ink.muted`. Reversed type itself is `paper`: 9.40:1 on green, 9.94:1 on wine,
7.77:1 on `ink.muted`.

Every stroke clears 3:1 against paper, which is what satisfies SC 1.4.11: the stroke,
not the pale field, is the boundary a reader has to see.

What each role means, across all three plates:

- `operation` — something that runs. The label is a verb or the name of a job.
- `store` — something persisted and addressable by name.
- `accepted` — an object that has passed a check and is being handed on: a frozen tree, a
  durable query result.
- `attention` — state that is in motion or provisional: a transient stream, feedback
  carried back into an earlier step, a ceiling that is not an assignment, a failed check
  returning.
- `decision` — a gate. One question, two labelled exits.
- `frame` — a container, a rail, a legend, a chart panel's furniture. Never a subject.

## 5. Type

One family, `Helvetica`; `Courier New` for identifiers only — store names, column names,
`partition_id`. State `fontFamily` and `fontSize` in every style string, or the figure
renders differently on another machine.

| Step | Size | Weight | Use |
| --- | --- | --- | --- |
| plate title | 20 | bold | once per plate, top left, `ink` on paper |
| heading | 14 | bold | rail name, group heading |
| node name | 12 | bold | the name in a title row; mono 12 for an identifier |
| node type | 11 | regular | the type half of a data card's title row |
| gate answer | 13 | bold | the two exits of a decision — they are answers, not annotations |
| footnote | 11 | italic or regular | legend entry, axis label |
| edge label | 10 | regular | edge labels, card body, table cells, caps tags |

Five steps, each at least 1pt from its neighbours and each doing one job.

**Naming.** A label is written for a reader who has not read the walkthrough section it
comes from. Never print a bare acronym as a name — expand it, and put the short form in
the card body where the method is stated (`optimistic knapsack simulation`, body: "Method:
multiple-choice knapsack (MCKP)"). Never print a lone verb or adjective as a name where it
could be read as a fragment. A decision prints a whole question with its subject in it, not
one word: `Does the skipping ratio hold on held-out queries?`, never `transfers?`.

**Title rows.** Every subject card opens with the same title row at its top: a band 32
tall **filled in the card's own `ink`**, with the name reversed out of it in `paper` at 12
bold, and any caps tag beside the name at the same edge, never pushed to the opposite end.
One construction for every kind of card. Giving a store a filled header bar and an
operation only a rule makes two families out of one system, and a reader reads that
difference as meaning something it does not.

A card that holds *data* names its kind first: `<Type>: <name>` — `DL Table:
usage_summary`, `Split Tree Candidate: A`, `Split Tree: Pre-Built`. The type is the 11pt
half and the name the 12pt bold half, in separate cells so an identifier can stay mono.

A card that *runs* carries its name alone. No `Operation:` prefix — the rounded shape and
the rose field already say it is an operation, and a word that repeats the role is ink
that encodes nothing.

**Names line up with the walkthrough.** A node's name is how a reader finds the detail,
so it is the left pane's own term for that step, in Title Case: `Optimistic Knapsack
Simulation (MCKP)`, `Experiment Simplified Assignment On Holdout`, `Optimize Split
Decision Trees`. A name that paraphrases the section heading instead of matching it makes
the reader search for the paragraph.

## 6. Redundancy is mandatory, not decorative

The two role hues are a dark red and a dark green. That is the classic dichromat
confusion pair: under protanopia and deuteranopia they converge, and converted to
greyscale their inks sit at **1.06:1** against each other — indistinguishable. Six roles
on two hues would not be separable by hue even for a reader with full colour vision.

So hue is never a channel a distinction depends on. Every role carries a shape and a
word, and those two alone must be sufficient:

| Role | Shape | Line | Word |
| --- | --- | --- | --- |
| `operation` | rounded rectangle | solid | its own name, a verb or a job title |
| `attention` | rounded rectangle | **dashed 7-4** | the type half of its title row — `Dynamic Feedback:`, `Transient:` |
| `decision` | **diamond** | solid | the question, printed, under a `DECISION` tag |
| `store` | **square** card, white body | solid | mono name after its kind — `Event Table:` |
| `accepted` | square card, **tinted body**, heavier 2.4 stroke | solid | caps tag `FROZEN` / `DURABLE` beside the name |
| `frame` | large box with a header bar, or a tinted rail | solid | heading in caps or title case |

Read the shape column alone: rounded-solid, rounded-dashed, diamond, white-square,
tinted-square, box. Six distinct answers with no colour at all. That is the test. The
title band is common to all of them and therefore separates nothing — which is the point
of it.

## 7. Component recipes

- **Spacing between layers.** Space is a layer of the composition, not slack to be
  recovered. Rail to rail, rail head to first card, row to row inside a rail, and card to
  card inside a frame each get their own step, and none of them is squeezed to save
  height. A plate that is taller but legible beats one that fits and reads as a thicket.
- **Shared node.** A one-to-many hand-off is drawn as one edge into a small filled node
  and branches out of it, not as many arrows leaving one card. The node is the point where
  the one thing becomes several, so the trunk carries the label and the branches carry
  none. The same node run backwards is a join: several shares into one object. Do not use
  it where the paths are genuinely independent — two consumers reading different data are
  two edges, and a shared node there would draw a channel that does not exist.
- **Components inside a frame** stack down the page with a full card gap between them, so
  an assembly line reads top to bottom like the rest of the plate and every stage gets the
  frame's full width for its sentence.
- **Sizing.** Every card is sized to the text it holds. Measure the wrapped line count
  at the card's own width and set the height from it; never leave a card padded out to a
  round number, and never let a grid cell dictate a height its content does not fill. The
  one thing a layout column fixes is width.
- **Plate header.** There is none. The pane that carries the figure prints its title
  above the stage, so **the plate draws no title of its own** — printing it twice is ink
  that encodes nothing, and a drawn title goes stale the moment the figure is renamed.
  No kicker, no subtitle, no footnote either. The legend strip is the top row of the
  drawing. A reader already knows which section they are in; the plate number is a
  register entry in §10, not a caption. What to notice first is the prompt's job, not the
  drawing's.
- **Legend.** A horizontal strip on the top bar, directly under the title, left-aligned,
  full content width, `band` field with a `rule` border. A `LEGEND` caps label at the
  left, then one 38x22 swatch per distinction the plate actually uses, each drawn with
  the real recipe and followed by an 11pt label. Never list a distinction the plate does
  not draw, and never a second row.
- **Rail.** Rails on one row share that row's width, and every rail is filled by what it
  holds: if a rail's content leaves most of it empty tint, the content is too small or the
  plate is too wide, and one of the two is the defect. A `band` panel with a `rule` border,
  opened by a wine rounded badge 24x24
  carrying the rail number in `paper` mono 13, then the rail name at 14 bold `ink`,
  letter-spaced caps. The name is capped at 230 wide so a vertical lane can cross the
  rail's head without cutting the words.
- **Title band.** The one row every card opens with, 32 tall, filled in the card's own
  `ink`, type reversed out of it. On a rounded card the band is drawn rounded to the same
  arc and squared off at its foot, so only its top corners follow the card. On a diamond
  there is nowhere to put it: the decision is the single exception, and its `DECISION`
  caps tag does that row's work.
- **Operation card.** Rounded 14, `rose`, wine stroke 1.8, wine title band carrying the
  name alone, then **one sentence** at 10 `ink.muted`, inset 14. The sentence says what
  the step does, verb first, and stops: `Spend the table partition limit as a container
  budget, one container at a time, on every candidate tree`.
- **Store card.** Square, `card` body, green stroke 1.6, green title band carrying
  `<Type>: <name>`. Below it a schema list in mono 10, or a sample preview (see §9), then
  one sentence at 10 `ink.muted`.
- **Accepted card.** The store recipe on `sage`, stroke 2.4, with the caps tag beside the
  name in the band.
- **Attention card.** The operation recipe with a dashed 7-4 border. It keeps the
  `<Type>: <name>` form of a data card, because it *is* a thing being carried rather than
  a step that runs — and the type word is what names the role.
- **Decision.** Diamond, `rose`, wine stroke 1.8, a `DECISION` caps tag at 10 bold wine
  over the question at 14 bold `ink`. Its two exits are labelled `Yes` and `No` at 13
  bold — they are the gate's answers and read at the weight of a node label, never at the
  weight of an edge annotation.
- **Group frame.** `card` body with a `rule` header bar, heading 14 bold `ink` set at
  whichever end of the bar no lane crosses — the right end when lanes come down the left,
  the left end when they come down the right. A frame
  means "these run as one thing".
- **Where an outcome sits.** What a decision produces belongs in the decision's own rail,
  beside the exit that produces it, not in the rail that later consumes it. The long edge
  on the plate is then the hand-back, which is the part a reader needs to see travel.
- **Glyph inside a card.** A card may draw a small picture of its own subject where the
  subject has a shape a reader should see — a split tree, an index, a partition run. The
  glyph draws structure only: no values on it, no labels on its parts, no ordering and no
  walkthrough, and at most one centred caption beneath it. It is drawn in its card's own
  `ink`. Any shape distinction the glyph introduces is a distinction the plate draws, so
  it takes a legend key like any other.
- **Chart panel.** `card` body, `ink.muted` stroke 1.4, an `ink.muted` title band like
  any other card, a named axis, and every curve carrying both a colour and a line style plus a named key
  inside the panel. A shaded region is `band` and is labelled in caps.

## 8. Edge lexicon

Five meanings. Each differs from the others in at least two of colour, dash and weight,
and every one but plain data flow is always labelled.

| Meaning | Colour | Line | Weight | Label |
| --- | --- | --- | --- | --- |
| data flow | `ink` | solid | 1.8 | only where the nodes do not say it |
| trigger | wine | dotted 2-3 | 1.8 | always a verb: `schedule`, `launch` |
| ceiling / not binding | wine | dashed 6-4 | 1.6 | always, e.g. `ceiling, not an assignment` |
| fail return, carrying state | wine | solid | 2.2 | always, e.g. `no` |
| containment | `ink.muted` | dashed 4-4, filled diamond at the container end | 1.4 | the relation, e.g. `panel on` |

Edge labels sit on a `band` background so they mask the line they cross.

**Lanes.** A flow edge never crosses a card. Route it through a rail gutter, the margin
outside the rails, or a reserved lane below the last rail — and when a plate wraps onto a
second row of rails, the wrap is drawn like a line break: out of the right of one row,
into the left of the next.

## 9. What never appears

From the data-ink audit. These are not stylistic preferences; each one adds ink that
encodes nothing:

- no drop shadows, gradients, glows, bevels or 3-D;
- no decorative icons, clip art, server-rack or cloud pictures;
- no grid lines outside a chart panel, and no chart panel without a named axis;
- no colour without a recorded meaning, and no second meaning on a colour already spent;
- no legend entry for a distinction the plate does not use;
- no number typed by hand: derive it from the instance data and assert it;
- **no term from the dataset example the project uses elsewhere** — not a source name, not
  a column name, not a grouping key. A figure states the shape of a schema, and the
  placeholder names (`predicate_1`, `attribute_1`, `partition_id`, `record_id`) say that
  shape without tying the drawing to one story. The concrete example lives in the
  walkthrough prose, where a reader sees it introduced as an example.

**Sample rows in a store card.** A store card may print a short preview of its rows when
the shape of the data is the thing the reader has to grasp — a wide boolean table, a
narrow index. When it does: the columns are the vital ones plus a final `…` column, the
rows are followed by a `⋮` row, the block is headed `SAMPLE ROWS` in wine so it is never
read as measured data, and the values are obviously stand-ins. A card whose point is its
schema still prints schema only.

## 10. Plate register

| Plate | Figure | Rails |
| --- | --- | --- |
| 01 | Deployment Process Flow | four rails on three rows: row 1 `1 COLLECT` and `2 SEARCH` side by side, row 2 the `3 SPEND & CHECK` band, row 3 the `4 GATE` band |
| 02 | Ingestion Time Integration | three bands: `1 LAND`, `2 WRITE` (the schedule row, then the writer row — frozen tree, the three stages stacked in the frame, the shared node, the three stores), `3 COMPACT` fitted to its one card |
| 03 | Query Time Integration | two bands: `1 ACTIVATE & FETCH`, `2 FEED THE NEXT LAYOUT` |

Shared objects keep one `spec_id` and one look across plates: `tree_frozen` (01 emits,
02 consumes), `index_table` and `partitioned_sink` (02 writes, 03 reads),
`usage_summary` (03 writes, 01 reads).

**Generators.** The three plates are generated, not hand-placed: `tools/plates/kit.py`
holds the recipes in this file as code — palette, title band, card builders, legend,
rail, edge lexicon — and `plate01.py`, `plate02.py` and `plate03.py` hold only their own
plate's copy, geometry and edges. Card heights are measured from their own text by
`tools/plates/metrics.py`; no height is typed. Change a recipe in `kit.py` and rerun all
three:

```
python3 tools/plates/plate01.py resources/img_src/section_databricks_layout_planning.drawio
python3 tools/plates/plate02.py resources/img_src/section_databricks_ingestion.drawio
python3 tools/plates/plate03.py resources/img_src/section_databricks_query.drawio
```

All three plates are drawn to this file.

## 11. Conformance checklist

Before a plate is called finished:

1. every styled cell states `fontFamily` and `fontSize`;
2. every fill is a `field` from §4 or a substrate token from §3, and every stroke is that
   field's `ink`;
3. every card opens with a filled title band in its own ink, left-aligned, and every
   card's height is measured from its own text;
4. read the shape column of §6 with the colours stripped out: every role is still
   distinct, and every distinction still carries its word;
5. every edge matches one row of §8, every non-flow edge is labelled, and no edge crosses
   a card;
6. the legend is one horizontal row and lists exactly the distinctions drawn;
7. no title, kicker, subtitle or footnote is drawn on the plate, and no card, frame or
   lane carries a note about how to read it;
8. read every name cold: no bare acronym, no lone word in a decision, nothing that needs
   the walkthrough section open beside it, and every operation's name is the left pane's
   own term for that step in Title Case;
9. every card body is one sentence;
10. no term from the dataset example appears anywhere on the plate;
11. the render has been looked at: nothing clipped, every connector lands, and the claim
   in the prompt is what the picture actually says.

## Sources

- House palette: `resources/img_prompt/section_problem_cabinet_problem_prompt.txt` and
  `resources/img_prompt/section_problem_demand_layout_prompt.txt`
- WCAG 2.2 — https://www.w3.org/TR/WCAG22/
- Contrast requirements for WCAG 2.2 Level AA — https://www.makethingsaccessible.com/guides/contrast-requirements-for-wcag-2-2-level-aa/
- Tufte's design principles — https://faculty.cc.gatech.edu/~stasko/7450/16/Notes/tufte.pdf
- Naming tokens in design systems, Nathan Curtis — https://medium.com/eightshapes-llc/naming-tokens-in-design-systems-9e86c7444676
