# Drawing Storage Boundary illustration

Product requirements for the Drawing Storage Boundary section of the
demonstration GUI: a static feasibility illustration of turning an
already-chosen logical split into a storage assignment under container-count
and container-size limits. The left pane is text only. The right pane
carries three rasters, one per walkthrough section.

**Authority.** This document is the product spec for Drawing Storage Boundary.
[`simulator-spec.md`](simulator-spec.md) governs the application shell, theme, and layout.
[`problem-statement.md`](../../resources/html/problem-statement.md)
remains the authority on the formal objective.
[`technical_writing_instruction.md`](../instructions/technical_writing_instruction.md)
is the writing contract for the left pane. Where this document and the product spec
disagree on shell, theme, or layout, the product spec wins. Where they disagree on
this section's content, this document wins.

**No recommendation.** The walkthrough may mark a cost-versus-benefit
threshold on a static sample. It does not choose an allocation, run a solver,
score a layout, or ship an assignment strategy.

---

## 1. Role and reading order

Drawing Storage Boundary continues from Measuring Data Layout Fitness in
three sections. Each section has one raster on the right that illustrates
that section's mechanism.

1. **Working with Storage Container Limits** — once split trees exposing
   high value potential are identified, map those terminal groups to a
   storage assignment a real data storage system can keep. Cross-reference
   Problem Statement's medicine-cabinet walkthrough to introduce the
   container-count limit. A storage container may be a local SSD block, a
   file, a partition, or a cloud object. Every system pays metadata to keep
   each container addressable. Most systems expose a container-count ceiling
   (maximum files or partitions per table) and a soft container-size floor
   (minimum byte size per S3 object). The objective is a storage assignment
   that maximizes estimated data skipping inside those limits. This page
   studies that assignment as a multiple-choice knapsack on a static sample.
   The numeric result is tied to that frozen profile and may not transfer to
   a live system. It can still mark a cost-versus-benefit threshold. The leaf
   benefit of a terminal group packed at count $K_g$ is the Poisson empty-unit
   volume $V_g(K_g)=n_g\Pr(X=0)=n_g e^{-\lambda_g}$, with
   $\lambda_g=n_g p_g/K_g$, the same empty-unit model as Measuring Data
   Layout Fitness §3.1.
2. **Problem Generalization: Multiple-choice Knapsack** — map the storage
   allocation onto the multiple-choice knapsack problem: one class per
   terminal group, one option per container count, shared capacity equal to
   the container-count ceiling. Explain the geometric series that keeps each
   group's upgrade chain short, and the predecessor-constrained upgrade
   edge with additional containers $\Delta K$, marginal benefit $\Delta V$,
   and marginal efficiency $e=\Delta V/\Delta K$.
3. **Greedy Optimization** — describe the cheap greedy scan, the condition
   under which it is optimal, the cases where the geometric model fails that
   condition, and the scan's time and extra space. The scan ranks the Poisson
   leaf benefits defined in §1. The section closes with three guardrails:
   a starting count at or above $n_g p_g/2$ so offered steps are concave
   in $K$; the size floor $n_g/K_g>s_{\min}$; and a group-level skip bar
   (a typical engine break-even near 50%) before $K_g>1$ is granted.

- The walkthrough sits on the **left**.
- The three figures sit on the **right**, in section order.
- Below the split breakpoint the panes stack in that order.
- Each pane is static and independently scrollable on a wide viewport.
- The left sequence is closed except for the external definition and theorem
  links at the first introduction of those terms.

The left pane follows the writing contract: each section is mental model,
terms, formula, observations, in that order. Graphics are step 4 of that
flow and live only on the right. Conclusions fold into the last paragraph
of the section; there is no labeled takeaway. The walkthrough does not use the
word *production*.

---

## 2. Model boundary

The input is the terminal grouping produced by an upstream split together
with the observed, query-level selection log. The Gini result in Measuring
Data Layout Fitness motivates looking at that grouping; it does not provide
the per-query evidence needed to estimate container activation.

The allocation floor is one container for every already-formed group, so
each group stays addressable. The remaining count up to the container-count
ceiling is shared globally: an upgrade bought for one group removes those
containers from every other group's feasible choices. The container-size
floor caps how large a group's count can grow.

The model's option value is the leaf benefit
$V_g(K_g)=n_g\Pr(X=0)=n_g e^{-\lambda_g}$, where $X$ is the selected-event
count in one equal-size unit of group $g$ packed at $K_g$ containers,
$p_g$ is the group-wide selection rate from the static query sample, and
$\lambda_g=n_g p_g/K_g$. On this page $\lambda$ is only that Poisson
parameter. It is not:

- the per-query skipping ratio $\sigma_q$;
- aggregate waste $W(\lambda)$;
- an upper bound on either quantity;
- a score obtained by constructing and replaying a physical layout.

The benchmark harness remains the surface that reports exact workload replay.

---

## 3. Greedy claim

The cheap procedure is a greedy scan of currently exposed upgrade edges.
The values it ranks are the Poisson leaf benefits $V_g(K_g)=n_g\Pr(X=0)$.
It is optimal when resource can be added in unit or divisible increments
and each activity's available marginal gains are non-increasing. The
walkthrough links that claim to Federgruen and Groenevelt's treatment of
greedy resource allocation and does not include a proof.

After the option values are known, let $m$ be the number of terminal groups
and $E$ the number of upgrade edges. A heap of the $m$ currently exposed
edges makes each accept $O(\log m)$. At most $E$ accepts occur, so the scan
is $O(E\log m)$ time and $O(m)$ extra space, plus $O(E)$ to hold the
ladders.

The restricted geometric model does not guarantee the optimality
conditions:

- an upgrade may consume several containers as one indivisible step;
- intermediate container counts are absent;
- a later upgrade can have higher efficiency than its predecessor, so it is
  hidden until a weaker step is accepted;
- ratio order can leave budget that a different combination would use.

The conclusion is a cheap static estimate of skipping potential, useful as
a cost-versus-benefit threshold, without a general optimality guarantee.

Section 3 then states three guardrails that restore the greedy region and
respect storage cost:

- starting count $K_{g,0}$ at or above $n_g p_g/2$ (inflection, skip
  $e^{-2}\approx 13.5\%$); a group that cannot reach it stays at $K_g=1$;
- size floor $n_g/K_g>s_{\min}$;
- grant $K_g>1$ only when the group's $\Pr(X=0)$ clears a group-level skip
  bar. A typical engine break-even is about 50% ($\lambda_g=\ln 2$). That
  bar is a cost-versus-benefit threshold, not a shipped constant.

The three cuts do not coincide. A group can clear the starting count and
miss the skip bar, or clear both and still hit the size floor.

---

## 4. Right-pane visualizations

The right pane contains exactly three figures, in walkthrough-section
order:

| id | Visible title | Walkthrough section |
| --- | --- | --- |
| `E.storage-limits` | *The Container Assignment Problem* | §1 Working with Storage Container Limits |
| `E.knapsack-ladder` | *Convert to Multiple-Choice Knapsack Problem (MCKP)* | §2 Problem Generalization: Multiple-choice Knapsack |
| `E.greedy-guardrails` | *Greedy Optimality relies on Decaying Marginal Efficiency* | §3 Greedy Optimization |

Each figure carries a one-line caption naming its construction. No pane
references a missing file.

Each figure is authored from its retained prompt:

- [`resources/img_prompt/e_storage_limits_prompt.txt`](../../resources/img_prompt/e_storage_limits_prompt.txt)
- [`resources/img_prompt/e_knapsack_ladder_prompt.txt`](../../resources/img_prompt/e_knapsack_ladder_prompt.txt)
- [`resources/img_prompt/e_greedy_guardrails_prompt.txt`](../../resources/img_prompt/e_greedy_guardrails_prompt.txt)

Each prompt names the accepted PNG's path and is the authority on that
figure's content. Two authoring routes are in use, and each prompt states
which one its figure takes:

- **Python renderer** — figure 1. The prompt specifies one
  1920 × 1080 deterministic raster, drawn once at 3840 × 2160 and
  downsampled with LANCZOS. The supersample is needed because the
  rasterizer antialiases small type and hairlines poorly. The renderer
  was removed after acceptance (10.3.3).
- **draw.io** — figures 2 and 3. The accepted sources are
  [`resources/img/section_e_knapsack_ladder.drawio`](../../resources/img/section_e_knapsack_ladder.drawio)
  and
  [`resources/img/section_e_greedy_guardrails.drawio`](../../resources/img/section_e_greedy_guardrails.drawio);
  the accepted PNG is exported from that source with the draw.io desktop
  CLI at the target width. No supersample, because draw.io renders through
  a browser engine that antialiases correctly at any size. The one-time
  generator that emitted the XML was removed after acceptance (10.3.3).

A visual change starts a new authoring pass from the prompt.

---

## 5. Hypothesized instances

The three right-pane rasters do not use a provider dataset, the Data
Skipping Experiment catalog, or the committed scenario file. Group
states and printed metrics are hypothesized: they exist to teach the
mechanism, not to report a scored workload. This section's figures are
outside 12.6.4's catalog / manifest / scenario trace.

Each figure owns its instance; none is shared. Figure 1 uses its own
price-tier instance, Figure 2 the price split from the Gini split-cycle
figure, and Figure 3 one geographic group. Every number printed in a
raster is derived from the dictionary that figure names. None is a typed-in
display constant.

**Figure 1**

```
column = "Price"
groups = {
  "T1": { "lower": 20, "upper": None, "records":   500_000,
          "n_id": "n1", "K_id": "K1", "p_id": "pg1", "F_id": "F1" },
  "T0": { "lower":  0, "upper":   20, "records": 3_300_000,
          "n_id": "n2", "K_id": "K2", "p_id": "pg2", "F_id": "F2" },
}
container_budget = 1000
```

The two groups are a hypothesized price-tier cut. They are not a
partition of a provider corpus. $N=3{,}800{,}000$. The two bounds tile
the price line and both the CASE ladder and the printed edge ranges —
`[Price] > $20` and `[Price] <= $20` — are derived from them, so the arms
visibly cover the whole line. A column reference is capitalized and
bracketed everywhere it appears. Each leaf is designated a record count
$n_i$, a container count $K_i$, a group-wide rate $p_{g,i}$, and a
skipping-ratio function $F_i$ (T1: $n_1$, $K_1$, $p_{g,1}$, $F_1$;
T0: $n_2$, $K_2$, $p_{g,2}$, $F_2$). Those symbols are not bound to
numbers, and no record count is printed. The leaf's expected data
skipping ratio is $F_i(K_i)=e^{-n_i p_{g,i}/K_i}$, and its marginal
benefit is the change in skipping volume per container,
$\Delta(n_iF_i)/\Delta K_i$. The budget constraint is $K_1+K_2=1000$.

**Figure 2**

```
split = { "column": "price_tier", "op": ">", "value": 5, "records": 1200 }
groups = {
  "Yes": { "records":  200, "selected_per_query": [1, 0, 0, 1, 0, 0], "holds": 1 },
  "No":  { "records": 1000, "selected_per_query": [3, 0, 2, 1, 3, 0], "holds": 4 },
}
query_ids = ["q1", "q2", "q3", "q4", "q5", "q6"]
container_options = [1, 4, 16, 64]
container_budget = 96
size_floor = 3
```

The two chains are the children of the price predicate in the Gini
split-cycle figure, named for the answer to the condition, and their
record counts sum to the split's 1,200. `holds` is the count each chain
currently stands at. Both chains satisfy $n_gp_g\le 2$, so the marginal
benefit of $n_ge^{-n_gp_g/K}$ is falling from $K=1$ and every chain is
strictly diminishing. The size floor does not bind on this instance:
both chains offer the whole ladder and no blocked slot is drawn.

**Figure 3**

```
predicate = "Price > 20"
branch = "Yes"
records = 1600
selected_per_query = [32, 24, 18, 40, 0, 12]
query_ids = ["q1", "q2", "q3", "q4", "q5", "q6"]
size_floor = 80
typical_skip_bar = 0.50
```

One hypothesized group, the Yes branch of a price predicate written in the
same form as figure 2's split, sized so that both curvature regions of
$V_g(K_g)$ and all three guardrails are visible on a single container
chain. It is not a partition of a provider corpus. The figure carries no
geometric option ladder and no container budget: the chain is every
integer count the size floor allows, which is what puts the inflection
inside the drawing.

Derived checks the renderer asserts (rounded only for display):

- $p_g=\mathrm{mean}(\texttt{selected\_per\_query})/n_g$, $\lambda_g=n_g p_g/K_g$,
  $V_g(K_g)=n_g e^{-\lambda_g}$; $n_gp_g=21.0$.
- Chain $K_g=1\ldots K_{g,\max}$ with size cap
  $K_{g,\max}=\lfloor n_g/s_{\min}\rfloor=20$.
- Marginal efficiency over one unit step,
  $e(K_g)=\Delta V/\Delta K=V_g(K_g+1)-V_g(K_g)$ with $\Delta K=1$.
- Curvature $\mathrm{d}^2V/\mathrm{d}K^2=V_g(K_g)\,(n_gp_g/K_g^3)(\lambda_g-2)$,
  so the sign flips at the inflection $K_{g,0}=n_gp_g/2=10.5$. The tallest
  step is $K_g=10\to K_g=11$ at $e=41.2$, and it straddles that inflection.
- $V_g(1)=0.0$, $V_g(11)=237.1$, $V_g(20)=559.9$.
- Skip-bar count $K\approx n_gp_g/\ln 2=30.3$ at a typical 50% bar. It
  exceeds $K_{g,\max}$, so no surviving count reaches break-even:
  $\Pr(X=0)=14.8\%$ at $K_g=11$ and $35.0\%$ at $K_g=20$.
- After the three cuts the offered chain is $K_g=11\to K_g=20$.

A later figure may change only the relationship its prompt names.

---

## 6. Visual content

Every drawing uses the wine-red / warm-rose / dark-green / cool-sage
explainer family of the Problem Statement illustration prompts, not the
12.7 gray series and not orange. State is carried by fill, shape, and a
word. No figure contains a winning allocation, recommendation badge,
shipped engine constant, or claim of optimality. Each figure states that
it is demonstration arithmetic.

### 6.1 *The Container Assignment Problem* (§1)

The composition states the assignment problem on an already-chosen
price-tier split:

1. a circular root labelled Original Data, cut by
   `CASE WHEN price > $20 THEN T2 ELSE WHEN price > $10 THEN T1 ELSE T0 END`
   into three leaves T2, T1, T0 with 500K, 1.2M, and 2.1M records;
2. each leaf designated its pair $(K_i,p_{g,i})$ and labelled
   `size = …` on the first line and the Poisson skip-ratio percent
   $e^{-n_i p_{g,i}/K_i}$ on the second;
3. a storage-bin glyph in the lower centre labelled 1,000 buckets, with
   one outbound arrow to each leaf tagged $K_1$, $K_2$, $K_3$;
4. a bottom-left sentence: maximize the weighted-average data-skipping
   ratio while satisfying $K_1+K_2+K_3=1000$.

It does not bind $K_i$ or $p_{g,i}$ to a number, draw upgrade edges, or
apply the §3 guardrails.

### 6.2 *Convert to Multiple-Choice Knapsack Problem (MCKP)* (§2)

The composition teaches the multiple-choice knapsack mapping:

1. one class per leaf of the price split, one option per geometric count
   $K\in\{1,4,16,64\}$, drawn as two chains of four nodes and three edges;
2. a predecessor-constrained upgrade edge labelled with $\Delta K$ and
   $e=\Delta V/\Delta K$, where $K=1$ is the naive initial state every
   chain starts from;
3. node state carried by border style — solid for an activated count,
   dashed for one not selected — with one chain still at $K=1$ while the
   other has advanced to $K=4$;
4. the diminishing case: on both chains each step buys less per added
   container than the step before it;
5. a dashed curve joining the step each chain could take next, and a
   verdict naming the larger of the two.

The verdict names one pending step, not an allocation. The figure does
not rank all six edges or apply the §3 guardrails.

### 6.3 *Greedy Optimality relies on Decaying Marginal Efficiency* (§3)

The composition teaches the condition and the three guardrails on one
container chain, $K_g=1\ldots K_{g,\max}$:

1. one chart with one horizontal axis — number of containers $K_g$, one
   tick per integer count — and two vertical axes, so the level and its
   rate of change are read against the same counts. Absolute magnitudes
   are not the subject; each series is scaled to its own axis;
2. on the left axis, the expected data skipping volume $V_g(K_g)$ as a
   marked line;
   on the right axis, the marginal efficiency $e=\Delta V/\Delta K$ as one
   bar per unit step, rising over the convex half and decaying over the
   concave half;
3. the inflection $K_{g,0}=n_gp_g/2$ as a dashed rule splitting the plot
   into a named convex half, where marginal efficiency still rises and the
   greedy condition does not hold, and a named concave half, which is the
   region the theorem needs. The tallest step straddles that rule;
4. a panel stating the model: $V_g(K_g)$, the $\Delta V/\Delta K$ step, and
   $\mathrm{d}^2V/\mathrm{d}K^2$ as the expression whose sign turns at
   $n_gp_g/K_g=2$. That expression is written in $n$ and $p$; the figure does
   not use the $\lambda$ symbol;
5. the three cuts applied to that one chain: starting count $K_{g,0}$,
   size floor, and a typical 50% skip bar. The figure labels 50% as a
   typical engine bar, not a constant the page ships;
6. the same chain redrawn after the cuts, one token per count, each cut
   count struck through.

An axis title names its quantity and never says which side it is on. The
raster carries no subtitle under the title, no legend, and no caption line:
the region banners, the verdict tokens and the struck counts each carry
their own word or mark, so nothing needs a key. The closing sentence under
the chain strip is the last element on the page.

It does not announce a chosen allocation, and it does not rank groups
against one another or draw a container budget.

---

## 7. Writing contract

The left pane is
[`section-budget-walkthrough.html`](../../simulator/gui/static/section-budget-walkthrough.html).
It is a technical presentation. Each section uses the
six-step flow in
[`technical_writing_instruction.md`](../instructions/technical_writing_instruction.md),
except that step 6 is not a labeled takeaway: the conclusion sits in the
last paragraph of the section, without a heading, bold label, or
highlighted closer. A formula,
or two or more new terms, is introduced with a definition table — one row
per term.

The first mention of the multiple-choice knapsack problem links to an external
definition. The first mention of Poisson links to the wiki definition.
The conditional greedy claim links to an external technical
reference. Later emphasis uses the citation form *the concept description*
(`symbol`, defined in §X), naming the document when $X$ is not a
section of this walkthrough. The walkthrough contains no figure markup.
The walkthrough refers to Measuring Data Layout Fitness and to Problem
Statement's medicine-cabinet walkthrough by those names. On the left pane,
$\lambda$ is only the Poisson parameter; aggregate waste is written in words
and cited to Problem Statement §2.5.

---

## 8. Requirements map

| id | requirement |
| --- | --- |
| E1 | Walkthrough on the left; three figures on the right in §1, §2, §3 order; that order when stacked |
| E2 | Left opens once split trees exposing high value potential are identified, then Problem Statement's medicine-cabinet walkthrough, then states $B$ and $s_{\min}$ |
| E3 | Leaf benefit is $V_g(K_g)=n_g\Pr(X=0)=n_g e^{-\lambda_g}$ with $\lambda_g=n_g p_g/K_g$; $\lambda$ is only that Poisson parameter |
| E4 | Section 2 maps the allocation onto MCKP with a geometric option ladder and predecessor-constrained upgrade edges |
| E5 | Section 3 states the greedy scan, $O(E\log m)$ time, $O(m)$ extra space, and the cases where the geometric model fails the theorem |
| E6 | Section 3 closes with three guardrails: $K_{g,0}\ge n_g p_g/2$, $n_g/K_g>s_{\min}$, and a typical ~50% group-level skip bar before $K_g>1$ |
| E7 | No labeled takeaway; the walkthrough does not use the word *production* |
| E8 | Right pane carries the three titled figures, each with a one-line caption; no `<img>` to a missing file |
| E9 | Figure 1 uses the §5 price-tier instance; figure 2 the §5 price split; figure 3 the §5 single-group geographic instance; they do not read a provider dataset, catalog, or scenario file; every printed number is derived from the dictionary that figure names |
| E10 | Figures use the wine / sage explainer family; state is never colour alone |
| E11 | No winning allocation, recommendation badge, shipped engine constant, or claim of optimality |
| E12 | Wiki / DOI links only at first introduction of those terms |
| E13 | Left walkthrough fills the pane; type is one step above Problem Statement |
| E14 | Figure 3 carries one terminal group as a single container chain $K_g=1\ldots K_{g,\max}$ on one horizontal axis, with $V_g(K_g)$ and $e=\Delta V/\Delta K$ on two vertical axes, and marks the inflection $K_{g,0}=n_gp_g/2$ where $\mathrm{d}^2V/\mathrm{d}K^2$ changes sign; it carries no subtitle, legend or caption |
