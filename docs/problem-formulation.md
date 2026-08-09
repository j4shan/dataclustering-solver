# Workload-Aware Container Assignment: A Formal Problem Statement

This document specifies the optimization problem informally introduced in the project
[README](../README.md). It is deliberately confined to a problem statement: it defines an
abstract storage model, a workload representation, an objective function, the structural
properties of that objective, the admissibility constraints, and a complexity analysis. It
proposes no algorithm and evaluates no solution family.

The model is stated over an abstract storage system rather than any concrete engine or
storage service. Mapping the formulation onto a real system — with its particular file
format, index mechanism, and execution model — is a separate exercise that depends on this
one being settled first.

Index design is likewise out of scope. Resolving a query to the set of container identifiers
it must open is treated as a black box, assumed exact and free (§2.1); nothing
below concerns its description language, its size, its selectivity, or its upkeep. The sole
decision variable is the assignment of events to containers.

---

## 1. Terminology

The README develops the problem through a closet analogy. That analogy maps onto the formal
objects as follows, and is not used again below.

| informal | formal object |
| --- | --- |
| garment | event $e \in E$, keyed by `Event_ID` |
| drawer, cabinet | container $c$, with contents $E_c$ |
| a morning's outfit | query $q$, keyed by `Query_ID`, selecting $S_q$ |
| opening a drawer | the `OPEN` primitive; the unit of read cost |
| tag numbers and the summary page | the pre-scan — a black box, assumed exact and free (§2.1) |
| garments handled but not worn | waste |
| which garment lives in which drawer | the layout $\lambda$ — the decision variable |

"Event" is used for the stored item because the motivating corpora are event data; nothing
in the model depends on that reading, and "record" may be substituted throughout. *Query*
denotes a unit of workload; *read* and *open* denote the physical operation that serves it.

---

## 2. Abstract storage model

Let $E$ be a finite set of events, $|E| = N$.

**Containers.** A *layout* is a total assignment

$$\lambda : E \rightarrow \{1, \dots, K\}$$

partitioning $E$ into containers $E_c = \lambda^{-1}(c)$, with $\sum_c |E_c| = N$. Events
are treated as unit-sized throughout; a byte-weighted variant replaces every occurrence of
$|E_c|$ with $\sum_{e \in E_c} \text{size}(e)$ and changes nothing structural.

**Read primitive.** The storage system exposes exactly one read operation,

$$\texttt{OPEN}(c) \rightarrow E_c$$

returning the full contents of a container. There is no per-event addressing. Cost is
charged per event returned by `OPEN`, irrespective of how many of those events the caller
retains. This single restriction is what makes the layout consequential; a system supporting
free per-event access has no problem to solve.

**Two-phase execution.** A query is served in two phases:

1. *pre-scan* — resolve the query predicate to the set of container identifiers it must open;
2. *read* — `OPEN` each of those containers and discard events the query did not select.

### 2.1 The pre-scan is a black box

Phase 1 is out of scope. This document assumes a pre-scan that is

- **exact** — it returns precisely the containers holding at least one event the query
  selects: none is missed, and none is opened for nothing; and
- **free** — its cost is negligible beside the cost of reading the materialized events, and
  is therefore absent from every expression below.

Three consequences follow, and together they are what make the rest of this document a
statement about layout alone.

*Activation is containment.* A container is opened if and only if it holds a selected event,
so which containers are read is fully determined by $\lambda$ and the log.

*Correctness is not a layout concern.* An exact pre-scan serves every layout correctly, so no
choice of $\lambda$ can change a query's result. Result-invariance holds by assumption rather
than by constraint, and never has to be traded against the objective.

*Nothing about the index is designed here.* Its description language, its size, its
selectivity, and its maintenance are all delegated. In a deployed system these are real costs
and a real source of imprecision, and both push realized cost *above* what is derived here —
so every figure below is a lower bound on what a real system pays.

---

## 3. Workload representation

### 3.1 The usage log

The workload is observed, not declared, and is recorded in a single append-only table:

| column | type | meaning |
| --- | --- | --- |
| `Event_ID` | string | the event that was selected |
| `Query_ID` | bigint | the query that selected it |

One row per selection. **A row's presence is the observation**: it states that query
`Query_ID` selected event `Event_ID`. Absence states the converse. There is no boolean
column, so the table stores positives only — its cardinality is the number of selections
rather than $N \times Q$, which matters because the negative space is overwhelmingly the
larger of the two. New observations are appended; no row is ever updated in place.

Formally the log is a relation $L \subseteq E \times \mathcal{Q}$ over the $Q$ distinct
queries in $\mathcal{Q}$. Queries carry no frequency weight: a repeatedly issued query
appears under distinct `Query_ID`s, so repetition is carried by the log rather than by a
weight term.

### 3.2 Derived quantities

Everything the objective needs is a projection of $L$:

$$S_q = \{\, e : (e, q) \in L \,\} \qquad \operatorname{supp}(e) = \{\, q : (e, q) \in L \,\} \qquad |L| = \sum_{q} |S_q|$$

- $S_q$ — the **selection set** of query $q$: the events it needs.
- $\operatorname{supp}(e)$ — the **support** of an event: the queries that need it. Its size
  is the event's demand.
- $\operatorname{supp}(c) = \bigcup_{e \in E_c} \operatorname{supp}(e)$ — the **support of a
  container**: the queries that must open it.

It is convenient to write $u_{e,q} = 1$ when $(e,q) \in L$ and $0$ otherwise, giving a
**usage matrix** $U \in \{0,1\}^{N \times Q}$ with $\lVert U \rVert_1 = |L|$. $U$ is a
notational device only — it is never materialized, and $L$ is its sparse representation.

Two properties of this encoding matter downstream. An event selected by no query has **no
rows at all**: it is present in the corpus and absent from the log, and such events are
simultaneously the cheapest to place well and the easiest to overlook. And because $L$ only
grows, the problem is continually re-posed against a longer log (§8.7).

### 3.3 The log does not explain itself

$L$ records *which* events a query selected, never *why*. Nothing requires $S_q$ to coincide
with any predicate the query states over event attributes; a query may select a list of
events whose shared structure is nowhere expressed in its text. This gap between stated
predicate and observed demand is a load-bearing feature of the problem, revisited in §8.5.

---

## 4. Activation and materialization

A container is **activated** by a query when it holds at least one selected event:

$$a_{c,q} = \max_{e \in E_c} u_{e,q} \in \{0,1\}$$

The **materialized volume** of query $q$ is everything inside its activated containers:

$$M_q(\lambda) = \sum_{c=1}^{K} a_{c,q} \, |E_c|$$

Necessarily $M_q(\lambda) \ge |S_q|$, with equality only when every activated container is
composed exclusively of events that $q$ selected.

The **demand breadth** of a container is the number of queries that activate it:

$$d_c(\lambda) = \sum_{q} a_{c,q} = \bigl| \operatorname{supp}(c) \bigr|$$

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="img/container-zoom.dark.svg">
  <img alt="Two containers during one query: an activated container holding one selected event and two wasted ones, beside a bypassed container that is never read." src="img/container-zoom.light.svg">
</picture>

*Activation is all-or-nothing at the container. One selected event obliges the whole
container; zero selected events cost nothing.*

---

## 5. Objective function

### 5.1 Waste

The waste incurred by query $q$ is the volume it opened but did not select:

$$w_q(\lambda) = M_q(\lambda) - |S_q| \;\;\ge\; 0$$

The objective is aggregate waste over the whole workload:

$$\boxed{\;\; \mathcal{W}(\lambda) \;=\; \sum_{q} w_q(\lambda) \;=\; \sum_{q}\Bigl( M_q(\lambda) - |S_q| \Bigr) \;\;}$$

There is no index term and no pre-scan term. By §2.1 both are delegated, so aggregate waste
is the entirety of the cost the layout governs — the objective is not a weighted sum of
competing costs but a single quantity.

Stated directly against the usage log, the second term is simply its cardinality:

$$\mathcal{W}(\lambda) \;=\; \underbrace{\sum_{c} |E_c| \cdot \Bigl| \bigl\{\, q : (e,q) \in L \text{ for some } e \in E_c \,\bigr\} \Bigr|}_{\text{events opened}} \;-\; \underbrace{\vphantom{\sum_c} |L|}_{\text{events selected}}$$

which is computable in one pass over the log joined to the layout:

```sql
SELECT SUM(size * breadth) - (SELECT COUNT(*) FROM usage_log) AS aggregate_waste
FROM (
    SELECT COUNT(DISTINCT l.Event_ID) AS size,
           COUNT(DISTINCT u.Query_ID) AS breadth   -- NULLs (never-selected events) ignored
    FROM layout l
    LEFT JOIN usage_log u USING (Event_ID)
    GROUP BY l.Container_ID
) c;
```

### 5.2 Interpretation: the objective counts flipped labels

Define the *smeared* usage matrix $\tilde{U}$ by $\tilde{u}_{e,q} = a_{\lambda(e),q}$ — event
$e$ is materialized by query $q$ exactly when its container is activated. Then

$$\mathcal{W}(\lambda) = \lVert \tilde{U} \rVert_1 - \lVert U \rVert_1$$

Since $L$ is fixed input, minimizing waste is minimizing $\lVert \tilde{U} \rVert_1$. The
layout acts on $U$ by propagating every $1$ across all rows sharing a container: within a
container, one selected event in a column forces the whole column entry for that container.
**Aggregate waste is the number of zeros in $U$ that the layout turns into ones** — the rows
the log never recorded but the storage system reads anyway.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="img/usage-matrix.dark.svg">
  <img alt="The usage matrix under two layouts. Rows are events grouped into containers, columns are queries. Under the as-built layout 45 cells are wasted; under the clustered layout, 6." src="img/usage-matrix.light.svg">
</picture>

*The same log and the same containers under two assignments. Nothing about the workload
changed between the panels; only $\lambda$ did.*

### 5.3 Equivalent compact form

Exchanging the order of summation in $\sum_q M_q$ yields the identity used throughout §6:

$$\sum_{q} M_q(\lambda) \;=\; \sum_{q}\sum_{c} a_{c,q}|E_c| \;=\; \sum_{c=1}^{K} |E_c| \cdot d_c(\lambda)$$

Because $|L|$ is layout-invariant, the optimization is equivalent to

$$\min_{\lambda} \;\; \sum_{c=1}^{K} \underbrace{|E_c|}_{\text{container size}} \cdot \underbrace{\Bigl| \textstyle\bigcup_{e \in E_c} \operatorname{supp}(e) \Bigr|}_{\text{demand breadth}}$$

Every container is charged its size multiplied by the breadth of demand it attracts. Waste
remains the preferred reporting unit — it is the quantity that is paid for and returns
nothing — but this product form is the more tractable object of analysis.

---

## 6. Structural properties of the objective

These are consequences of §5, derived rather than assumed. They characterize the problem;
they are not a design.

### 6.1 Insertion is monotone

Adding an event to a container weakly increases both factors of its cost: $|E_c|$ by one, and
$d_c$ by the number of queries the new event introduces. Container cost is therefore monotone
non-decreasing under insertion. There is no repair move — a container can only be improved by
removing events or by the global budget freed elsewhere.

### 6.2 Marginal cost decomposes into two distinct harms

The cost of placing event $e$ into container $c$ is

$$\Delta(e, c) \;=\; \bigl(|E_c| + 1\bigr)\, d_{c \cup e} \;-\; |E_c|\, d_c \;=\; \underbrace{d_{c \cup e}}_{\text{harm to } e} \;+\; \underbrace{|E_c| \cdot \bigl| \operatorname{supp}(e) \setminus \operatorname{supp}(c) \bigr|}_{\text{harm to the incumbents}}$$

The two terms are qualitatively different failures, and they identify the two ways a layout
goes wrong:

- **A low-demand event joining a high-breadth container** contributes almost nothing to the
  second term — it introduces no new queries — but pays $d_c$ in the first. It has been
  conscripted into every query the container already served.
- **A high-demand event joining a low-breadth container** pays little in the first term but
  multiplies the second by the container's whole population. It has conscripted everyone
  else.

Events with *similar* support combine cheaply regardless of whether that demand is high or
low; events with *dissimilar* support are expensive in one direction or the other. The
segregation of frequently and rarely selected events is thus a consequence of the objective,
not an independent heuristic layered on top of it.

### 6.3 Merging is free only under support equality

For disjoint groups $A$ and $B$, the cost of merging them into one container is

$$\Delta_{\text{merge}}(A,B) \;=\; |A|\bigl(d_{A \cup B} - d_A\bigr) + |B|\bigl(d_{A \cup B} - d_B\bigr) \;\ge\; 0$$

which vanishes exactly when $\operatorname{supp}(A) = \operatorname{supp}(B)$. Events with
identical support are perfectly co-locatable at any group size; everything else trades waste
for a shorter index.

### 6.4 The cost is a set function, not a sum of pairwise distances

$\Delta(e,c)$ depends on the size and accumulated support of the container being joined, so
the penalty for co-locating two events is not a property of the pair. Container cost is a
function of the *union* of member supports and admits no decomposition into pairwise terms.
Formulations that require a metric over events — or that assume the cost of a group is
additive in its pairs — are describing a different problem.

### 6.5 The cost is neither submodular nor supermodular

$d_c$ is a monotone submodular set function (it is the coverage function of the supports);
$|E_c|$ is modular. Their product is in general neither submodular nor supermodular, so the
standard approximation guarantees for greedy maximization of coverage do not transfer.

### 6.6 Under equal container sizes, the problem is hypergraph partitioning

The usage log is already an incidence list: read each `Query_ID` as a hyperedge over the
`Event_ID`s appearing beside it. Let $\kappa_q$ denote the number of containers hyperedge
$q$ spans — written $\kappa$ rather than $\lambda$, which already denotes the layout. Then $\sum_c |E_c| d_c = \sum_q \sum_{c \,:\, a_{c,q}=1} |E_c|$, the total *volume*
spanned by each hyperedge. If all containers are constrained to equal size $s$, this
collapses to

$$\sum_{q} s \cdot \kappa_q \;=\; s \sum_{q} \kappa_q$$

— exactly the connectivity metric of balanced hypergraph partitioning. The general
variable-size case is its volume-weighted generalization. This identification is the source
of the hardness result in §8.2, and it also flags a trap: the standard cut-net and
connectivity metrics count *how many* blocks a net spans, whereas the objective here weights
each spanned block by its size. The two coincide only under a size-uniformity constraint that
the real problem does not impose.

---

## 7. Constraints

A layout is admissible only if it satisfies the following. With the pre-scan delegated
(§2.1), there are two. Result-invariance is not among them: under §2.1 it holds for every
layout by assumption, so it constrains nothing.

### 7.1 Container size bounds

$$s_{\min} \le |E_c| \le s_{\max}$$

The lower bound exists because each `OPEN` carries a fixed cost — request overhead and
per-container bookkeeping in the storage layer — amortized only over a sufficiently large
population. The upper bound exists because a container big enough to be activated by nearly
every query cannot contribute skipping regardless of its contents. Both are properties of the
storage system, not of the workload.

$s_{\min}$ carries the whole weight of the problem, because refinement never hurts.
Splitting $E_c$ into $E_{c_1}, E_{c_2}$ changes its cost from $|E_c| d_c$ to
$|E_{c_1}| d_{c_1} + |E_{c_2}| d_{c_2}$, and since $d_{c_i} \le d_c$ while the sizes still sum
to $|E_c|$, the result is at most $|E_c| d_c$. Waste is therefore monotone non-increasing
under refinement, and reaches exactly zero at singleton containers, where every activated
container consists solely of a selected event. With the pre-scan free, nothing penalizes that
layout except the floor. **The size floor is the sole force opposing granularity**, which
reduces the problem to a single clean tension: minimize $\mathcal{W}$ subject to a minimum
block size, and nothing more.

In practice the bound is enforced distributionally — median and tail of $|E_c|$ — rather than
pointwise. Demand is heavy-tailed (§8.6) and the corpus churns, so exact size uniformity is
neither attainable nor desirable.

### 7.2 Write-time assignability

$\lambda$ must be evaluable on a newly arriving event from that event alone —
deterministically, cheaply, and without consulting global state or recomputing the layout. A
layout definable only as the output of a batch computation over the full corpus cannot absorb
ingest.

---

## 8. Complexity

### 8.1 Search space

The candidate set is the set of partitions of $E$ into at most $K$ non-empty blocks, of
cardinality $\sum_{k \le K} S(N,k)$ in Stirling numbers of the second kind — super-
exponential in $N$. The size bound of §7.1 prunes this heavily but does not change its order.

### 8.2 Hardness

With the index delegated, §7.1 leaves the problem in its bare form — minimize $\mathcal{W}$
subject to a minimum block size — which is precisely *Balanced MaxSkip partitioning*, shown
NP-hard [Sun et al., SIGMOD 2014]. The same conclusion arrives independently through §6.6:
the equal-size instance is balanced hypergraph partitioning under the connectivity metric,
itself NP-hard, and the variable-size problem contains it as a special case. Removing the
index from scope simplifies the statement without softening the hardness. Exact optimization
is out of reach for any realistic $N$; the practical target is a heuristic with measurable
distance from the bounds in §8.4.

### 8.3 Evaluation cost

Scoring a single candidate layout requires computing $\operatorname{supp}(c)$ for every
container, which is $\Theta(|L|)$ work, followed by $\Theta(K)$ to accumulate. Linear in the
log — but the log is the entire access history of the corpus, and a search procedure must pay
it per candidate. The cost of *evaluating* the objective, not the cost of computing it once,
is the binding constraint on any search.

### 8.4 Bounds are far apart

The objective is bounded below by $\mathcal{W} = 0$ — every container homogeneous in support,
which is reachable only when the support classes of $L$ happen to admit a partition
respecting $s_{\min}$, and generally they do not — and above by the single-container layout
($\mathcal{W} = QN - |L|$). Neither bound is informative about achievable quality, so progress
must be measured against realized baselines rather than against the theoretical range.

### 8.5 The exploitable structure is latent

The supports in $L$ are observed outcomes, not declared attributes. A grouping that reduces
waste need not align with any attribute the events carry, so the search cannot be reduced to
partitioning on schema columns: the axis that matters may not be an axis the data announces.
What is available instead is $L$ itself — a sparse binary incidence relation over which, by
§6.4, no metric is defined. The search therefore ranges over set-valued supports under a
non-decomposable cost, rather than over points in a space where nearness means anything.

### 8.6 Demand is lopsided

Empirically $|\operatorname{supp}(e)|$ is heavy-tailed across events: a small subset carries
most of the demand mass while the majority is near-zero, and some events appear in $L$ not at
all. By §6.2 this means the marginal cost landscape differs by orders of magnitude between
regions of the event space, so a single uniform container granularity is simultaneously too
coarse for the tail and too fine for the head. Any constraint that forces global uniformity
(§7.1 applied pointwise) is therefore actively harmful, which is why it is stated
distributionally.

### 8.7 The instance is non-stationary

$E$ churns and $L$ grows, so a fixed layout degrades without being touched. Over epochs
$\tau = 1, \dots, H$ with layouts $\lambda_\tau$ and the log increment $L_\tau$ observed in
each, the realized cost is

$$\sum_{\tau=1}^{H} \Bigl[\, \mathcal{W}(\lambda_\tau; L_\tau) \;+\; \Gamma\bigl(\lambda_{\tau-1} \rightarrow \lambda_\tau\bigr) \Bigr]$$

where $\Gamma$ is the cost of physically relocating events. This converts a one-shot
combinatorial problem into an online one, with three additional difficulties:

- **$\Gamma$ must be repaid.** A reorganization that improves $\mathcal{W}$ by less than it
  costs is a loss, so the decision of *whether* to act is as consequential as the choice of
  layout. The natural evaluation criteria are regret against the best static layout in
  hindsight, or competitive ratio against the offline-optimal sequence.
- **Feedback is delayed.** The quality of $\lambda_\tau$ is only observable through the rows
  $L_\tau$ appends, i.e. after the queries have run against it. Layout changes cannot be
  evaluated before they are paid for.
- **The system stays live.** Transitions must be incremental and concurrent with reads and
  writes. Stopping the system to re-partition is not an available move, which excludes any
  formulation whose transition step is a global rebuild.

---

## 9. Success criteria

All quantities are measured on queries held out from those used to construct the layout. A
layout scored on its own construction workload is measuring memorization.

| criterion | definition | why it matters |
| --- | --- | --- |
| waste ratio | $\mathcal{W}(\lambda) \big/ \lvert L \rvert$ | extra events opened per event delivered; the headline number |
| read amplification | $\sum_q M_q \big/ \lvert L \rvert = 1 + \text{waste ratio}$ | the same quantity in the unit systems usually report |
| per-query distribution | median and upper tail of $w_q$ | aggregate waste hides catastrophic individual queries, which dominate perceived behaviour |
| baseline lift | $\mathcal{W}$ relative to a workload-agnostic layout on the same data | isolates the value of using $L$ at all |
| size health | distribution of $\lvert E_c \rvert$ against $[s_{\min}, s_{\max}]$ | the binding constraint (§7.1); detects a layout that bought waste reduction by shrinking containers below the floor |
| container count | $K$, and the share of $E$ in containers at $s_{\min}$ | states where on the granularity axis a layout sits, which is the one dimension the objective alone does not pin down |
| net benefit | read cost avoided less construction and maintenance cost, over a stated horizon | the only criterion that determines whether the layout should exist |
| decay trajectory | waste ratio as a function of epoch, with no intervention | sets the reorganization cadence and bounds the useful life of a layout. Not assumed monotone — demand that recurs seasonally can return to regions a layout already suits, so a single growth rate need not describe it |

---

## 10. Assumptions and non-goals

**Assumed.**

- Containers are immutable; modification is rewrite-and-replace, never in-place edit.
- No per-event addressing; the container is the atomic read (§2).
- The pre-scan is exact and free (§2.1). Index imprecision and index cost are both additive
  losses on top of every result here, so the figures derived are lower bounds.
- The observed log is predictive of future demand. Where it is not, §8.7 governs.
- The log is complete for the queries it covers — a missing row means "not selected", not
  "not observed" (§3.1).

**Out of scope.** Index design — the language containers are summarized in, the size and
selectivity of that summary, and its upkeep (§2.1); caching and storage tiering; query
rewriting and join ordering; compression and encoding choice; execution-level tuning; and the
mapping of this formulation onto any specific storage service or execution engine. These are
complementary concerns. The problem stated here is exactly the choice of $\lambda$ and its
maintenance over time.

---

## Appendix: prior art

Listed for orientation and for the later exercise of mapping this formulation onto a concrete
system. None of it is assumed by the statement above.

**Runtime skipping mechanisms.** The black-box pre-scan of §2.1 — resolve a query to a
candidate container set, then read only those containers — is realized in production systems
as dynamic partition pruning, where a filter built from the small side of a join eliminates
partitions of the large side before its scan begins
([overview](https://www.waitingforcode.com/apache-spark-sql/whats-new-apache-spark-3-dynamic-partition-pruning/read),
[AWS guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/spark-tuning-glue-emr/pruning-dynamic-partitions.html)).

**Layout optimization.**

- Sun et al., *Fine-grained Partitioning for Aggressive Data Skipping*, SIGMOD 2014 — Balanced MaxSkip partitioning and its NP-hardness ([summary](https://www.odbms.org/2014/05/fine-grained-partitioning-aggressive-data-skipping/))
- Sun et al., *Skipping-oriented Partitioning for Columnar Layouts*, VLDB 2017 ([pdf](http://www.vldb.org/pvldb/vol10/p421-sun.pdf))
- Yang et al., *Qd-tree: Learning Data Layouts for Big Data Analytics*, SIGMOD 2020 — predicate trees as a form for $\lambda$ ([pdf](https://arxiv.org/pdf/2004.10898))
- Ding et al., *Instance-Optimized Data Layouts for Cloud Analytics Workloads*, SIGMOD 2021 ([pdf](https://www.microsoft.com/en-us/research/wp-content/uploads/2021/04/msr-mto-sigmod.pdf))
- Sudhir et al., *Pando: Enhanced Data Skipping with Logical Data Partitioning*, VLDB 2023 ([pdf](https://www.vldb.org/pvldb/vol16/p2316-sudhir.pdf))
- Rong et al., *Dynamic Data Layout Optimization with Worst-case Guarantees*, 2024 — the online problem of §8.7 with a competitive-ratio bound ([arXiv](https://arxiv.org/abs/2405.04984))
