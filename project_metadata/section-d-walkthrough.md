# Where usage concentrates

## 1. A familiar kind of unevenness

Picture a town divided into neighborhoods of different sizes. The town has a fixed
amount of wealth. In one arrangement every neighborhood holds about the same wealth
per resident. In another, most of the wealth sits in one or two neighborhoods, and
the remaining neighborhoods hold many residents but almost none of the wealth.

That second picture is a mental model of inequality: not “some people are richer,”
but “a large share of the population lives where little of the wealth is.” The
question is how to *measure* that bow between population and wealth.

Line the neighborhoods up from poorest to richest. Walk along the population from
the poorest end, and at each step keep two running totals: what share of the
residents you have passed, and what share of the town’s wealth they hold. Plot
population share on the horizontal axis and wealth share on the vertical axis.
The resulting path is a [Lorenz curve](https://en.wikipedia.org/wiki/Lorenz_curve).
If every neighborhood is equally wealthy, the path is the diagonal. If wealth
piles into the last neighborhoods, the path sags below the diagonal and rises
steeply at the rich end. The bow between the diagonal and that path *is* the
inequality.

The size of that bow is the [Gini coefficient](https://en.wikipedia.org/wiki/Gini_coefficient).
For a grouping $S$ of the town into neighborhoods, write $G(S)$ for that
coefficient. The symbols below are defined together because the formula uses
them as a set.

| term | symbol | meaning |
| --- | --- | --- |
| neighborhood population | $n_g$ | number of residents in neighborhood $g$ |
| neighborhood wealth | $U_g$ | total wealth held in neighborhood $g$ |
| wealth density | $d_g$ | mean wealth per resident, $U_g / n_g$ |
| population share | $p_g$ | $n_g / N$, where $N$ is the town population |
| wealth share | $q_g$ | $U_g / U$, where $U$ is total wealth |
| cumulative wealth share | $\mathrm{CumQ}_g$ | sum of $q_j$ from the poorest neighborhood through $g$ |
| Gini coefficient of the grouping | $G(S)$ | the bow between the diagonal and the Lorenz curve |

Sort neighborhoods by ascending wealth density $d_g$. Then

$$
G(S)
=
1
-
\sum_{g}
p_g \bigl(2\cdot\mathrm{CumQ}_g - q_g\bigr).
$$

The first figure on the right draws this construction: the equality diagonal, a
nearly even path, and a bowed path.

Three observations follow from the formula.

When every neighborhood has the same density $d_g$, each $q_g$ equals its $p_g$,
the path is the diagonal, and $G(S)=0$. The grouping reveals no concentration.

When $G(S)$ is high, a small *population* share holds a large *wealth* share.
A large share of residents then live in poor neighborhoods.

The population weight $p_g$ is essential. Without it, a tiny rich neighborhood
could dominate the score. The formula rewards a grouping that isolates wealth
while leaving a *substantial* share of residents in poor neighborhoods.

**Takeaway.** Inequality, as $G(S)$ measures it, is a property of how wealth sits
across population shares — not a property of any one rich neighborhood.

## 2. The same unevenness in a warehouse

The same mental model applies to a data warehouse. Each stored event is a
resident. The wealth of an event is how often it was fetched across the observed
workload: its `used_count`. A feature column — a *feature grain* — cuts the
corpus into neighborhoods. Those neighborhoods are the terminal groups of a
split. A group that holds many events and almost no usage is the warehouse
counterpart of a poor neighborhood: when a query never names it, its storage
containers can stay shut.

The symbols of §1 keep their meanings, with residents read as events and wealth
read as fetch frequency.

| term | symbol | meaning |
| --- | --- | --- |
| feature grain | — | a feature column used to divide events |
| terminal group | $g$ | one population produced by a split $S$ |
| group population | $n_g$ | event count in group $g$ |
| group usage | $U_g$ | sum of `used_count` in group $g$ |
| usage density | $d_g$ | $U_g / n_g$ |
| split | $S$ | a grouping of the corpus into terminal groups $\mathcal{G}(S)$ |
| efficiency | $\eta(S)$ | inequality delivered per maintained group |

The population-weighted Gini coefficient ($G(S)$, defined in §1) is computed on
those groups exactly as in the town. A second quantity asks what that inequality
costs to keep. Every extra terminal group adds metadata, planning, and
file-management work. Taking that cost as proportional to the group count,

$$
\eta(S)
=
\frac{G(S)}{\lvert\mathcal{G}(S)\rvert}.
$$

High $G(S)$ with few groups is a strong screen. High $G(S)$ bought by a huge
group count is a weak one.

The twelve-event instance used in Section C makes the contrast concrete. Twelve
events (`r01`–`r12`) carry a region and an event type. Three queries select
$\{r01, r03\}$, $\{r03, r06\}$, and $\{r10, r11\}$. The implied usage wealth is
$U=6$; events that no query selected have `used_count` $0$. These figures are
the instance’s own arithmetic, not a measurement of a production corpus.

Cut the twelve events by event type and $G(S)=1/9$: usage is nearly even across
types. Cut the same events by region and $G(S)=7/18$: `us-east` holds four of
the six units of usage, and `ap-south` holds two events and none of the usage.
The second figure on the right draws those two cuts side by side. The cold
`ap-south` group is a skip candidate — a group a later query can leave unopened
when it selects nothing there.

The same contrast is the effect of clustering ($p_g$ by subgroup, defined in
§3.1 of the formal statement): a split does not create demand; it exposes that
demand is already uneven.

Two limits follow, and both matter.

`used_count` adds fetch frequency across queries. It forgets which events were
fetched *together*. The population-weighted Gini coefficient ($G(S)$, defined in
§1) therefore cannot equal the aggregate waste ($W(\lambda)$, defined in §2.5).
$G(S)$ screens a *logical* split. Waste is a property of a *physical* assignment
of events to containers. Scoring that assignment is a workload replay — the
job of Section B — and this page does not perform it.

**Takeaway.** A high-Gini split is a screen for groups that concentrate usage
and leave a large cold population that a query can skip. It is not a layout
score and not a recommendation.

## 3. A search that evolves the split

A useful split is grown one decision at a time, the way a search grows a
candidate rather than enumerating every grouping of the corpus. The starting
point $S_0$ is no split: one group, $G(S_0)=0$. Each step adds a feature grain,
either everywhere or only on some leaves, and produces a new grouping $S_t$.

Two constructions share the same fitness.

| term | symbol | meaning |
| --- | --- | --- |
| group-by-chain | — | a compound key built by adding feature grains in order, applied to every group |
| selective tree | — | a multi-way tree that splits only chosen leaves |
| trajectory | $S_0,S_1,\ldots,S_L$ | the sequence of groupings a search actually evaluates |
| maintenance cost | $C(S)$ | burden of keeping the split; commonly $c_{\mathrm{split}}\cdot\lvert\mathcal{G}(S)\rvert$ |
| marginal efficiency | $\Delta G_t / \Delta C_t$ | inequality gained per unit of extra cost at step $t$ |

A chain is simple and deterministic:

```text
region
→ region × type
```

Every added grain applies to every existing group, so cardinality can grow as a
product. A selective tree evaluates candidate grains only on chosen leaves — for
this instance, splitting only the hot `us-east` leaf by type — and can isolate
usage without multiplying every branch. The third figure on the right draws
that contrast on the same twelve events.

At each step the search records

$$
G_t = G(S_t),
\qquad
C_t = C(S_t),
\qquad
\eta_t = \frac{G_t}{C_t},
\qquad
\frac{\Delta G_t}{\Delta C_t}
=
\frac{G_t - G_{t-1}}{C_t - C_{t-1}}.
$$

The stop rule is operational, not aesthetic. The search stops when marginal
efficiency falls below the return the extra groups are worth, when a cardinality
budget is exhausted, or when no remaining candidate improves $G(S)$ enough to
justify its cost. Candidates above the budget are pruned; a small set of
high-value parents is kept for the next expansion. The fourth figure on the
right is that trajectory: $S_0$, then the region cut, then the chain and the
tree, with a stop region where the next cut returns too little.

This walkthrough describes a screening search. It does not run one. It does not
assign events to containers. It does not select, rank, or recommend a chain.
Section B is where a *layout* — a physical assignment — is scored against the
observed workload. The figures on the right are the four constructions just
named, in this order.

**Takeaway.** A heuristic search can evolve a group-by-chain or a selective
tree by keeping cuts that raise the population-weighted Gini coefficient
($G(S)$, defined in §1) per unit of maintenance cost, and by stopping when the
next cut does not. That search is a screen. The score that decides a layout
remains the aggregate waste ($W(\lambda)$, defined in §2.5).
