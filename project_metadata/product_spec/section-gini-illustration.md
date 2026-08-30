# Measuring Data Layout Fitness illustration

Product requirements for the Measuring Data Layout Fitness section of the
demonstration GUI: a static illustration of how a recursive split search
screens a logical grouping. The left pane is text only. The right column
opens with a terminology dictionary and continues with figures. Both sides
scroll independently on the same theme as Problem Statement.

**Authority.** This document is the product spec for Measuring Data Layout
Fitness. [`simulator-spec.md`](simulator-spec.md) governs the application shell, theme, and
layout. [`problem-statement.md`](../../resources/html/problem-statement.md)
remains the authority on the formal model.
[`technical_writing_instruction.md`](../instructions/technical_writing_instruction.md)
is the writing contract for the left pane. Where this document and the product spec
disagree on shell, theme, or layout, the product spec wins. Where they disagree on
this section's content, this document wins.

**No recommendation.** The walkthrough may show that two cuts of the same
instance produce different fitness values, and that a search can stop when
incremental gain falls. It names search routines a real data storage system
can run as a problem-solving pattern. It does not select, rank, or recommend
an assignment strategy, a search method, or a fitness.

---

## 1. Role and reading order

Measuring Data Layout Fitness teaches split search as one ordered chain:

1. **Explore Data Split Trees** — the objective (a partition that maximizes a
   value function, data-skipping potential), the exponential cost of exact
   search, the need for heuristics, then the recursive-split problem:
   scoring a leaf as-is versus solving that leaf, the budgets every leaf
   shares, and the subproblem nature of a leaf;
2. **Practical Consideration** — how a real data storage system balances the
   cost of search against later avoided I/O: a cheap greedy baseline, then
   complementary ways to spend remaining compute and time;
3. **Choosing a Value function to Optimize** — three leaf fitnesses as
   subsections, in this order: group-wide skipping ratio, query-conditional
   skipping ratio, weighted Gini.

- The walkthrough sits on the **left**.
- The right column opens with the **terminology dictionary** and continues
  with the figures below it, the same stack Problem Statement uses (12.3 / 12.8).
- Below the split breakpoint the panes stack in that order: walkthrough,
  terminology, figures.
- Each pane is static and independently scrollable on a wide viewport.
- The left sequence is closed except for wiki definition links at the first
  introduction of a public technical term, and the one arXiv link named in
  §2. It contains no outbound artifact links and no alternate scenario.

The left pane follows the writing contract: each section is mental model,
terms, formula, observations, in that order. Graphics are step 4 of that
flow and live only on the right. Conclusions fold into the last paragraph
of the section; there is no labeled takeaway. A learning graph used to
order the sections is authoring metadata and does not appear in either pane.
The walkthrough does not use the word *production*.

None of the three fitnesses equals aggregate waste ($W(\lambda)$, defined in
Problem Statement's formal statement, §2.5). The benchmark harness remains
the surface that scores a physical layout.

---

## 2. Left pane

Three sections, in this order, with the titles below. Section 3 has three
numbered subsections.

### 2.1 Explore Data Split Trees

The first paragraph opens from Problem Statement's quantified data-skipping
goal. It then starts the research with a split search that identifies a
partition of the input dataset that maximizes a value function,
data-skipping potential. The search grows that partition as a logical tree
and scores each leaf. Exact search is exponential in the corpus, so a
cost-limited solver uses heuristics that return a cheaper, sub-optimal tree.

A following paragraph introduces the recursive split process and the key
concepts. It uses an abstracted objective — not a named solver and not one
of the three later fitnesses as *the* objective.

The paragraphs together establish all of the following:

- A search starts from the corpus as one leaf and grows a grouping by
  cutting a current leaf into two or more children. A cut may be multi-way.
- After a cut, each child is packed into equal-size units of container
  size $s$. Fitness is a number on that packing, or on the tree after the
  leaf is replaced.
- **fitness(leaf)** — written $v(\ell)$ — is the leaf scored as packed,
  with no further cut.
- **OPT(leaf)** — written $\mathrm{OPT}(\ell)$ — is the best score
  obtainable from that leaf if further cuts remain allowed under the
  remaining evaluation budget.
- The recurrence is
  $\mathrm{OPT}(\ell)=\max\bigl(v(\ell),\;\max_{\gamma}\sum_{c\in C(\gamma)}(n_c/n_\ell)\,\mathrm{OPT}(c)\bigr)$.
- Container size $s$ is a **common packing budget**: every leaf packs at
  the same $s$. Compute and wall-clock are **common evaluation budgets**:
  they limit how many cuts are enumerated, not the packing.
- Each leaf is a **subproblem** on its own events plus the shared $s$.
  Two leaves with the same contents are the same subproblem regardless of
  the path that produced them.

A short definition table introduces $v(\ell)$, $\mathrm{OPT}(\ell)$,
cut $\gamma$, children $C(\gamma)$, $s$, and the evaluation budgets at
the moment the paragraph uses them. The paragraph does not choose a
concrete $v$, discuss algorithm data structures, or claim that computing
$\mathrm{OPT}$ is tractable. Exact dynamic programming is named only as
the meaning of the recurrence; the state space is exponential.

### 2.2 Practical Consideration

This section lists tree-search strategies a real data storage system can
run. It does not use the word *production*. It does not discuss algorithm
implementation, neighbourhood design, cooling schedules, or code. It
frames container size $s$, compute, and time as a cost-benefit choice:
extra search work is worth doing only when later avoided I/O is expected
to repay it. The routine is:

1. **Start from a cheap greedy top-down baseline.** Grow the tree one
   accepted cut at a time, taking a locally improving cut while evaluation
   budget remains and incremental gain is large enough.
2. **Spend remaining budget exploring improvement in different directions.**
   The techniques are complementary; they are not mutually exclusive:
   - Balancing exploitation against exploration — [simulated annealing](https://en.wikipedia.org/wiki/Simulated_annealing),
     [evolutionary search](https://en.wikipedia.org/wiki/Evolutionary_algorithm).
   - Maintaining several intermediary solutions — [beam search](https://en.wikipedia.org/wiki/Beam_search)
     or a priority queue.
   - A published query-data tree (qd-tree) study grows a layout tree so
     later queries can skip more of the table. One or two sentences; no
     algorithm walkthrough. Link
     [arXiv:2004.10898](https://arxiv.org/abs/2004.10898)
     (Yang, Ding, Chaudhuri, and Argyraki, *Qd-tree: Learning Data Layouts
     for Big Data Analytics*).
3. **Amortize the learning cost.** The compute and time spent searching
   are paid once (or on a rebuild) and recovered from expected future I/O
   that the layout avoids. Return on that investment is therefore bounded
   by the **data-retention policy** in the deployed environment: a short
   retention window leaves fewer future fetches against which to charge
   the search.

The section does not rank the named techniques, treat any of them as the
shipped assignment strategy, or hand the reader a stop-rule constant.

### 2.3 Choosing a Value function to Optimize

One short parent paragraph: the fitness in §2.1 is left abstract; the three
subsections are candidate value functions; none is selected as the
objective of the recurrence. The parent states that all three screen a
logical grouping and that none equals $W(\lambda)$. Data Skipping
Experiment is where a physical layout is scored by replay.

#### 2.3.1 Group-wide skipping ratio

The leaf fitness is the estimated share of events left unread when each
unit is given one query-averaged selection rate.

Definition table, then the weighted-average formula. The exact form and
its Poisson approximation sit on the **same line**, joined by $\approx$:

$V_{\mathrm{marg}}(S,s)=\sum_i w_i(1-p_{g,i})^s\approx\sum_i w_i e^{-\lambda_i}$

with $p_{g,i}=(\mathrm{avg}_q\,k_{q,i})/n_i$, $w_i=n_i/n$, and
$\lambda_i=n_i p_{g,i}=\mathrm{avg}_q\,k_{q,i}$. The subscript names the
group-wide rate, not an incremental gain. Both forms lie in $[0,1]$.

The subsection states that this fitness collapses every query into one
rate per unit and depends on $s$.

#### 2.3.2 Query-conditional skipping ratio

The empty-container model is the same; the rate is per query.

Definition table, then the weighted-average formula. The exact form and
its Poisson approximation sit on the **same line**, joined by $\approx$:

$V(S,s)=(1/Q)\sum_q\sum_i w_i(1-p_{i,q})^s\approx(1/Q)\sum_q\sum_i w_i e^{-\lambda_{i,q}}$

with $p_{i,q}=k_{q,i}/n_i$ and $\lambda_{i,q}=k_{q,i}$. Both forms lie
in $[0,1]$.

The subsection states that a cut which isolates a block some queries never
enter can raise $V$ even when the group-wide rates are even.

#### 2.3.3 Weighted Gini

The general Gini concept is **one or two sentences**, ending with a wiki
weblink to
[Gini coefficient](https://en.wikipedia.org/wiki/Gini_coefficient).
There is no economics-stage lecture, no Lorenz-curve derivation on the
left, and no warehouse-free first stage.

The rest of the subsection is the **weighted** construction used as a leaf
fitness: $G(S)$ measures how unevenly the group-wide rate $p_{g,i}$ sits
across units. A short definition table introduces $w_i$, usage share
$q_i$, and $G(S)$. The subsection names incremental gain $\Delta G/\Delta k$
as the comparison that charges for extra groups. It states that $G(S)$
screens inequality and is not a skip ratio.

On this page, $\lambda$ in a formula is only the Poisson parameter
(expected selected-event count in the modeled unit). The formal
statement's layout letter is written in words.

---

## 3. Right column

### 3.1 Terminology panel

The right column opens with a top-mounted terminology dictionary, the
same shell treatment as Problem Statement: heading **Terminology**, a
two-column Term / Definition table, independently scrollable in the
upper band of the right stack.

The dictionary is this section's compact symbol list. It does not repeat
Problem Statement's full glossary. It defines every symbol the left pane
relies on after §2.1, in an order that follows the left sequence:

| Term | Definition |
| --- | --- |
| Grouping ($S$) | A partition of the events under consideration into terminal groups. |
| Leaf ($\ell$) | A current uncut group. |
| Cut ($\gamma$) | A partition of one leaf into two or more children $C(\gamma)$. |
| fitness(leaf) ($v(\ell)$) | The leaf scored as packed at size $s$, with no further cut. |
| OPT(leaf) ($\mathrm{OPT}(\ell)$) | The best score obtainable from the leaf if further cuts remain allowed under the remaining evaluation budget. |
| Container size ($s$) | Event count of one packed unit; the common packing budget. |
| Evaluation budget | Compute and wall-clock allowed for enumerating and scoring cuts. |
| Unit ($i$) | One equal-size container after the grouping is packed at size $s$. |
| Population weight ($w_i$) | Unit $i$'s share of the parent population, $n_i/n$. |
| Group-wide rate ($p_{g,i}$) | One selection rate for unit $i$, averaged across training queries. |
| Query-conditional rate ($p_{i,q}$) | Fraction of unit $i$ that query $q$ selected. |
| Poisson parameter ($\lambda$) | Expected selected-event count in the unit being modeled. |
| Group-wide skip ratio ($V_{\mathrm{marg}}(S,s)$) | Estimated skip ratio from the group-wide rates. |
| Query-conditional skip ratio ($V(S,s)$) | Estimated skip ratio that keeps the query index. |
| Weighted Gini ($G(S)$) | Inequality of the group-wide rate across units. |
| Extra groups ($\Delta k$) | How many groups the cut adds. |
| Incremental gain | Fitness change per extra group, $\Delta v/\Delta k$. |

The left pane does not restate this table as a second glossary. It still
introduces a term in adjacent context the first time the prose uses it.

### 3.2 Lower panel

The lower band of the right stack carries figures only: no editorial lede.
Two constructions, in this order:

1. a new animated PNG (APNG) titled *Recursive Partitioning with a Decision Tree*;
2. the three existing Gini drawings, combined as **one continued
   example** under the single shared title *Exploring a Data Tree with
   Gini*.

No other illustration appears.

---

## 4. Medium and visual system

The Gini example lives in one authored fragment under `resources/html/`.
Its medium is semantic HTML, CSS, and inline SVG: not a Cursor
`canvas.tsx`, not an HTML5 `<canvas>`, and not three independent
stage-matched pages.

The APNG is a committed animated raster. The retained prompt is
[`resources/img_prompt/d_tree_split_cycle_prompt.txt`](../../resources/img_prompt/d_tree_split_cycle_prompt.txt).
The figure is
[`resources/img/section_gini_tree_split_cycle.png`](../../resources/img/section_gini_tree_split_cycle.png).
The right panel embeds that file. There is no titled placeholder.

Every drawing uses:

- flat editorial drawing, not photorealism, 3D, or a screenshot;
- the wine-red / warm-rose / dark-green / cool-sage explainer family of
  the Problem Statement illustration prompts (`resources/img_prompt/`),
  not the 12.7 gray series and not orange;
- page sans for labels;
- one restrained repeating palette;
- single-stroke directional arrows;
- text, shape, outline, or pattern in addition to colour for every state.

No figure contains UI chrome, server racks, a spreadsheet grid, a winner
badge, or the words *best*, *optimal*, or *recommended*. Figure labels
stay readable; drawings keep a minimum width.

---

## 5. Shared instance

The continued Gini example uses the auto-parts sales corpus of Data
Skipping Experiment as an authored pedagogical partition of
`feature_category` and `brand_id`, not a live score of that corpus.
The selective-tree beat continues that partition.

Instance arithmetic, not a measurement. Drawn group counts are the
leaves on the figure; Gini per group is $G/k$ on those counts.

- Category beat: six drawn groups, $G=0.04$, $G/k=0.007$, density near 1;
- Brand beat: six drawn groups, $G=0.38$, $G/k=0.063$, a few tenants
  hot, long tail cold;
- Selective-tree beat on that brand split: brands A and B receive
  different binary L2 grains (`category = brakes`, `price_tier > 5`);
  C, D, E, and the rest stay uncut; eight groups, $G=0.41$,
  $G/k=0.051$; from the brand split $\Delta G=0.03$, $\Delta k=2$,
  $\Delta G/\Delta k=0.015$.

The APNG uses its own abstracted instance (named in the prompt) and
does not reuse these auto-parts numbers.

A later figure may change only the relationship its prompt names.

---

## 6. Illustration prompts

### 6.1 APNG — *Recursive Partitioning with a Decision Tree*

The raster carries no title and no subtitle of its own. The figure's
`<h3>` heading is the only place the title appears, so it is never
duplicated inside the image.

One looping animation of an abstracted tree. The cycle has three named
phases, in order, each held long enough to read:

1. **Enumerate** — one parent leaf; several candidate cuts are shown as
   options (a multi-way grain and a local predicate are both visible).
2. **Evaluate** — each candidate carries a fitness number. No crown,
   star, or “best” mark.
3. **Split** — one illustrated cut is applied; the parent is replaced
   by its children. The caption names it as the illustrated cut, not
   the winning cut.

The drawing teaches the step, not a solver and not a recommended
policy. Timing, transitions, and keep-out rules live in the retained
prompt.

### 6.2 Combined example — *Exploring a Data Tree with Gini*

One continued example. The shared title *Exploring a Data Tree with
Gini* appears once, above the three sequential drawings. Each drawing
is a beat of that example, not an independently titled right-pane
stage. Beat titles may name what the beat shows; they do not restart
the example.

#### Beat 1 — Lorenz construction

Former standalone figure `D.lorenz-wealth`.

Two aligned connected-scatter Lorenz diagrams of the same six
neighborhoods N1–N6, ordered poorest to richest. A complete sentence
above the left panel states that it is a perfectly equal distribution;
a complete sentence above the right panel states that the top 10%
controls 90% of the wealth. The vertical axis is “% of wealth”, with
0%, 50%, and 100% ticks on both panels. Each neighborhood is a labelled
marker on the horizontal axis; marker width is cohort size, and
high-income neighborhoods are narrower. An opaque dashed stem joins
each marker to its point; the points are connected. Draw the equality
line on both panels without labelling it “diagonal”. On the left the
path follows that line and is labelled $G=0$. On the right the path
sags then rises; hatch the area between that envelope and the
horizontal axis in light grey, print the exact $G=0.8112$, and do not
overlay “the bow is G”. Below the plots, a table lists neighbour
population % against cumulative wealth % for N1–N6. The figcaption is
a short paragraph of that example: equal density keeps wealth share in
step with population weight, and a narrow rich cohort produces the
bow. This beat uses no warehouse vocabulary, symbols of a fetch, or
technical mapping labels.

#### Beat 2 — two one-level splits

Former standalone figure `D.split-comparison`.

One sentence under the beat heading states that wealth is query
selection rate — how often a stored sale is fetched — not the sale
amount.

Two one-level split trees of the simulator's auto-parts
sales corpus, stacked so each metric table can use the full drawing
width. Each tree has a circular root labelled Original Data, then a
horizontal row of rectangular subsets joined by directed arrows. A
descriptive sentence names the cut — not the provider column — and a
one-line insight sits on the same row under that sentence. Each tree
prints drawn group count, weighted Gini, and Gini per group. Leaf
names and metrics sit in a table under the rectangles; the first
column names the metric (category or brand name, weight %, selection
rate). Nothing is overlaid on a shape. Left: split by product
category, volume follows the provider mix (brakes, filters, batteries,
tires, belts, and the rest combined as nine categories), selection
density nearly even, six groups, $G=0.04$, $G/k=0.007$. Right: split
by tenant brand, five short names plus the rest combined as 35, demand
concentrated, six groups, $G=0.38$, $G/k=0.063$; dashed outline marks
the large cold remainder. Fill plus the printed rate is density —
never colour alone. Numbers are authored pedagogical arithmetic, not a
live catalog score. Do not label either cut as best.

#### Beat 3 — selective tree

Former standalone figure `D.selective-tree`.

One graph, grown from beat 2’s tenant-brand split. Circular root
labelled Original Data, then the L1 brands A–E and Rest combined (35).
Select two brands and add a downstream binary grain at L2; the two L1
nodes use different conditions — `category = brakes` on A,
`price_tier > 5` on B. A grey dashed horizontal line separates each
pair of layers, including the root from L1. Dashed outline means uncut
leaf only. Print eight groups, $G=0.41$, $G/k=0.051$, and the
incremental gain from the brand split ($+2$ groups, $\Delta G=0.03$,
$\Delta G/\Delta k=0.015$). One or two sentences under the graph state
that a split action can be either a multi-way grouping or a local
conditional grouping, and that a custom split tree is easily expressed
as a query. Append a Spark SQL code block that writes the two L2
grains as distinct `CASE WHEN` arms in one `GROUP BY` of named
columns, not ordinal positions. Do not label the construction as best.
Do not draw a second, chain, panel.

---

## 7. Writing contract

The left pane is
[`section-gini-walkthrough.html`](../../simulator/gui/static/section-gini-walkthrough.html).
It is a technical presentation. Each section uses the six-step flow in
[`technical_writing_instruction.md`](../instructions/technical_writing_instruction.md),
except that step 6 is not a labeled takeaway: the conclusion sits in the
last paragraph of the section, without a heading, bold label, or
highlighted closer. A formula, or two or more new terms, is introduced
with a definition table — one row per term.

The first mention of a public technical term is a wiki weblink; the
qd-tree mention uses the arXiv link in §2 instead of a wiki page.
Later emphasis uses the citation form *the concept description*
(`symbol`, defined in §X), naming the document when $X$ is not a
section of this walkthrough. The walkthrough refers to the APNG and to
the continued example by those names and contains no figure markup.

On the left pane, every weighted-average skip-ratio formula prints its
Poisson approximation on the same line, with $\approx$ between them.
The general Gini concept is at most two sentences and carries the wiki
weblink at the end of that account.

---

## 8. Requirements map

| id | requirement |
| --- | --- |
| I1 | Walkthrough on the left; terminology then figures on the right; that order when stacked |
| I2 | Left opens from the quantified data-skipping goal, then states the split-search partition, exponential complexity, and heuristics, then $v(\ell)$ versus $\mathrm{OPT}(\ell)$, shared budgets, subproblem |
| I3 | Left then names how a real data storage system spends limited compute and time: greedy baseline, complementary improvements, retention-bounded ROI; the walkthrough does not use the word *production* |
| I4 | Section 3 presents the three metrics as 3.1, 3.2, 3.3: group-wide skip ratio, query-conditional skip ratio, weighted Gini |
| I5 | Each weighted-average skip formula prints the Poisson form on the same line with $\approx$ |
| I6 | General Gini is one or two sentences with a wiki weblink; no economics-stage lecture |
| I7 | $G(S)$ and both skip ratios screen a grouping and do not equal $W(\lambda)$ |
| I8 | Right lower panel is the APNG, then one continued Gini example; no other illustration |
| I9 | The continued example shares the title *Exploring a Data Tree with Gini* and folds the three existing drawings as sequential beats |
| I10 | Warehouse beats use an authored auto-parts partition and print Gini per group |
| I11 | Left pane follows the writing contract; conclusions fold into the last paragraph; no Takeaway label |
| I12 | Wiki weblink only at first introduction of a public technical term; qd-tree uses the named arXiv link |
| I13 | No assignment strategy, search method, or fitness is selected, ranked, or recommended |
| I14 | Left walkthrough fills the pane; type is one step above Problem Statement |
| I15 | Figures use the wine / sage explainer family, not 12.7 gray |
| I16 | Figure labels stay readable; drawings keep a minimum width |
| I17 | APNG prompt is retained; the right panel embeds `resources/img/section_gini_tree_split_cycle.png` |
