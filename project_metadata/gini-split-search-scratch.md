# Gini Split Search — measurement scratch pad

Research working note. Not a product spec, not a layout score, and not a
recommendation.

---

## 1. Mental model

A split search grows a grouping of the table, one cut at a time. It scores
the **logical grouping**, not a physical assignment of events to containers.
The first grouping is the whole table as one group. Each later cut partitions
one current group. The events stay the same; the cut only **exposes** that
selection already differs across the children.

After a cut, each child is modeled as equal-size containers. The search
compares candidate cuts by a fitness on those containers. Aggregate waste
(formal statement §2.5) is applied later, once a physical assignment exists
and the workload is replayed.

---

## 2. Terminology

| term | symbol | meaning |
| --- | --- | --- |
| grouping | *S* | a partition of the events under consideration into terminal groups |
| start grouping | *S*<sub>0</sub> | no split: the corpus as one group |
| parent | — | the current group a candidate cut partitions |
| unit | *i* | one equal-size container after the grouping is packed at size *s*; containers from the same subset share a rate |
| event count of a unit | *n<sub>i</sub>* | events in unit *i*; equal-size packing means *n<sub>i</sub>* = *s* |
| parent event count | *n* | Σ<sub>*i*</sub> *n<sub>i</sub>* |
| query | *q* | one **training** query |
| query count | *Q* | number of training queries |
| per-query selected count | *k<sub>q,i</sub>* | how many events query *q* selected in unit *i* |
| query-conditional rate | *p<sub>i,q</sub>* = *k<sub>q,i</sub>* / *n<sub>i</sub>* | fraction of unit *i* that query *q* selected |
| group-wide rate | *p<sub>g,i</sub>* = (avg<sub>*q*</sub> *k<sub>q,i</sub>*) / *n<sub>i</sub>* | one rate for unit *i*, averaged across queries; equals avg<sub>*q*</sub> *p<sub>i,q</sub>* |
| Poisson parameter | λ | expected selected-event count in the unit being modeled. *X* ~ Poisson(λ) and Pr(*X* = 0) = *e*<sup>−λ</sup> |
| group-wide Poisson parameter | λ<sub>*i*</sub> = *n<sub>i</sub>* *p<sub>g,i</sub>* = avg<sub>*q*</sub> *k<sub>q,i</sub>* | λ for unit *i* under the group-wide rate |
| per-query Poisson parameter | λ<sub>*i,q*</sub> = *n<sub>i</sub>* *p<sub>i,q</sub>* = *k<sub>q,i</sub>* | λ for unit *i* and query *q* |
| selected count in a unit | *X<sub>i</sub>* | random selected-event count in unit *i*; skipped when *X<sub>i</sub>* = 0 |
| population weight | *w<sub>i</sub>* = *n<sub>i</sub>* / *n* | unit *i*'s share of the parent population |
| usage share | *q<sub>i</sub>* = *n<sub>i</sub>* *p<sub>g,i</sub>* / Σ<sub>*j*</sub> *n<sub>j</sub>* *p<sub>g,j</sub>* | unit *i*'s share of parent usage, from the same per-query counts as *p<sub>g,i</sub>* |
| cumulative usage share | cumulative_qg<sub>*i*</sub> | sum of usage shares from the poorest unit through *i*, after sorting by *p<sub>g,i</sub>* |
| container size | *s* | event count of one container; packing size for the iterator *i* |
| extra groups | Δ*k* | how many groups the cut adds; a binary cut has Δ*k* = 1 |
| incremental gain | Δ*G* / Δ*k*, Δ*V* / Δ*k* | fitness change per extra group. This is an increment, not a derivative against *s* or a container budget. |

*Q* is only the query count. The cumulative usage share (cumulative_qg<sub>*i*</sub>,
defined in this section) is the running sum of usage shares *q<sub>i</sub>*.
It is not a sum over the *Q* queries.

In this note λ is only the [Poisson](https://en.wikipedia.org/wiki/Poisson_distribution)
parameter: the expected number of selected events in one unit. The formal
statement uses the same letter for the event-to-container assignment; that
assignment is written in words here.

There is no separate group-total *U*. Every usage figure is an aggregation
over *q* of the per-query selected count (*k<sub>q,i</sub>*, defined in this
section), or the group-wide rate (*p<sub>g,i</sub>*, defined in this
section) built from that average.

---

## 3. Evaluation method

The start grouping (*S*<sub>0</sub>, defined in §2) is one group. A binary
cut produces two subsets. A grain such as brand can produce more than two.
After the cut, each subset is packed into equal-size containers of size *s*.
The iterator *i* runs over those containers. Containers that came from the
same subset share the same per-query selected counts and therefore the same
rates.

1. **Start.** One rate on the whole table, so the weighted Gini coefficient
   *G*(*S*) is *G*(*S*<sub>0</sub>) = 0. Skip potential is whatever the
   unsplit table can skip at container size *s*.
2. **Cut.** Partition one current group by a feature grain or a predicate.
   Pack the children into equal-size units *i*.
3. **Score.** Each fitness is a number on the units {*i*}, or on the whole
   tree after that leaf is replaced. Keep the cut when its incremental
   gain (Δ fitness / Δ*k*, defined in §2) is large enough.
4. **Stop or continue.** Held-out waste (formal statement §2.5) is not a
   fitness at this step. It is applied after a physical assignment exists.

The inputs are the per-query selected counts *k<sub>q,i</sub>* and the unit
sizes *n<sub>i</sub>*. The two skip fitnesses also take the packing size
*s*, with *n<sub>i</sub>* = *s* under equal-size packing.

---

## 4. Weighted Gini *G*(*S*)

The [Gini coefficient](https://en.wikipedia.org/wiki/Gini_coefficient)
*G*(*S*) measures how unevenly the group-wide rate (*p<sub>g,i</sub>*,
defined in §2) sits across units. A unit with a smaller *p<sub>g,i</sub>*
is poorer.

Sort units poorer-then-richer by *p<sub>g,i</sub>*. Then

> *w<sub>i</sub>* = *n<sub>i</sub>* / *n*
>
> *q<sub>i</sub>* = *n<sub>i</sub>* *p<sub>g,i</sub>* / Σ<sub>*j*</sub> *n<sub>j</sub>* *p<sub>g,j</sub>*
>
> cumulative_qg<sub>*i*</sub> = Σ *q<sub>j</sub>* from the poorest unit through *i*
>
> *G*(*S*) = 1 − Σ<sub>*i*</sub> *w<sub>i</sub>* (2 · cumulative_qg<sub>*i*</sub> − *q<sub>i</sub>*)

On *S*<sub>0</sub> every unit shares one rate, so *G* = 0. After a cut, *G*
is large when a small population share holds most of the usage: a large
cold block of units next to a hot one.

A search that charges for extra groups compares the incremental Gini gain
Δ*G* / Δ*k*. A binary cut has Δ*k* = 1, so the increment equals the gain
in *G*. Two units with the same *p<sub>g,i</sub>* receive the same *G*
whether each query hits only one subset or both. The container size *s*
packs the iterator; it is not a skip threshold in this fitness.

**Takeaway.** *G*(*S*) screens inequality of the query-average rate. It
does not equal a skip ratio and it does not equal waste.

---

## 5. Group-wide skip potential *V*<sub>marg</sub>(*S*, *s*)

Each unit is given one selection probability, the group-wide rate
(*p<sub>g,i</sub>*, defined in §2):

> *p<sub>g,i</sub>* = (avg<sub>*q*</sub> *k<sub>q,i</sub>*) / *n<sub>i</sub>*

A container of size *s* is skipped when it holds no selected event. Write
*X<sub>i</sub>* for the selected-event count in unit *i*. Under independent
selection the count is binomial,

> *X<sub>i</sub>* ~ Binomial(*n<sub>i</sub>*, *p<sub>g,i</sub>*)
>
> Pr(*X<sub>i</sub>* = 0) = (1 − *p<sub>g,i</sub>*)<sup>*n<sub>i</sub>*</sup>

The Poisson parameter (λ, defined in §2) is that binomial’s expectation.
On unit *i* it is

> λ<sub>*i*</sub> = *n<sub>i</sub>* *p<sub>g,i</sub>* = avg<sub>*q*</sub> *k<sub>q,i</sub>*

When the rate is small, the formal statement’s Poisson approximation
(§2.6 and the appendix) replaces the binomial zero count:

> Pr(*X<sub>i</sub>* = 0) ≈ *e*<sup>−λ<sub>*i*</sub></sup>
>
> Pr(*X<sub>i</sub>* ≥ 1) ≈ 1 − *e*<sup>−λ<sub>*i*</sub></sup>

Under equal-size packing (*n<sub>i</sub>* = *s*), the exact and
approximate skip ratios — the estimated share of events left unread — are

> *V*<sub>marg</sub>(*S*, *s*) = (1 / *n*) Σ<sub>*i*</sub> *n<sub>i</sub>* (1 − *p<sub>g,i</sub>*)<sup>*s*</sup>
> = Σ<sub>*i*</sub> *w<sub>i</sub>* (1 − *p<sub>g,i</sub>*)<sup>*s*</sup>
>
> *V*<sub>marg</sub>(*S*, *s*) ≈ Σ<sub>*i*</sub> *w<sub>i</sub>* *e*<sup>−λ<sub>*i*</sub></sup>

The subscript names the group-wide rate, not an incremental gain. Both
forms lie in [0, 1]. When every unit has size *s*, this is also the
container-skipping ratio of the formal statement §2.6.

This fitness uses the same query-average as *G*(*S*), passed through the
skip curve. Unlike *G*(*S*), it depends on *s*. A density split cannot
decrease *V*<sub>marg</sub> relative to the parent (one rate on *n*).
Isolating a near-zero *p<sub>g,i</sub>* raises the ratio most; splitting
two equally hot blocks leaves it unchanged. Two workloads that share the
same *p<sub>g,i</sub>* values receive the same *V*<sub>marg</sub>,
including a brand-exclusive workload and a category-nibbling workload
that happen to match on the averages.

A search that charges for extra groups compares the incremental skip-ratio
gain Δ*V*<sub>marg</sub> / Δ*k*.

**Takeaway.** *V*<sub>marg</sub>(*S*, *s*) is Gini’s average, read as an
estimated skip ratio. It still collapses every query into one rate per
unit.

---

## 6. Query-conditional skip potential *V*(*S*, *s*)

The empty-container model is the same. The rate is now per query. Query
*q* selects *k<sub>q,i</sub>* events in unit *i*, so the query-conditional
rate (*p<sub>i,q</sub>*, defined in §2) and the per-query Poisson mean
(λ<sub>*i,q*</sub>, defined in §2) are

> *p<sub>i,q</sub>* = *k<sub>q,i</sub>* / *n<sub>i</sub>*
>
> λ<sub>*i,q*</sub> = *n<sub>i</sub>* *p<sub>i,q</sub>* = *k<sub>q,i</sub>*
>
> *V*(*S*, *s*) = (1 / (*n Q*)) Σ<sub>*q*</sub> Σ<sub>*i*</sub> *n<sub>i</sub>* (1 − *p<sub>i,q</sub>*)<sup>*s*</sup>
> = (1 / *Q*) Σ<sub>*q*</sub> Σ<sub>*i*</sub> *w<sub>i</sub>* (1 − *p<sub>i,q</sub>*)<sup>*s*</sup>
>
> *V*(*S*, *s*) ≈ (1 / *Q*) Σ<sub>*q*</sub> Σ<sub>*i*</sub> *w<sub>i</sub>* *e*<sup>−λ<sub>*i,q*</sub></sup>

The group-wide Poisson mean is that family’s average:
λ<sub>*i*</sub> = avg<sub>*q*</sub> λ<sub>*i,q*</sub>. The group-wide skip
fitness substitutes λ<sub>*i*</sub> (equivalently *p<sub>g,i</sub>*) before
summing over *q*. This fitness does not.

When unit *i* is only a few containers, the hypergeometric empty-bin
probability replaces both (1 − *p<sub>i,q</sub>*)<sup>*s*</sup> and
*e*<sup>−λ<sub>*i,q*</sub></sup>.

A query that never touches unit *i* has *p<sub>i,q</sub>* = 0, so
λ<sub>*i,q*</sub> = 0, and that unit contributes its full weight
*w<sub>i</sub>* to that query’s skip ratio. A query that hits every unit
contributes little from any of them. A cut that isolates a block some
queries never enter therefore raises the ratio even when *p<sub>g,i</sub>*
is even across units.

A search that charges for extra groups compares the incremental skip-ratio
gain Δ*V* / Δ*k*.

*V* does not use residual co-selection inside a unit — which of those
*k<sub>q,i</sub>* events travel together — and it does not use a physical
assignment beyond equal-size packing. That is why *V* screens and
replayed waste scores.

**Takeaway.** *V*(*S*, *s*) is the skip-ratio estimate that keeps the
query index. It is still an analytical screen, not a layout score.

---

## 7. Comparison

*G*(*S*) and *V*<sub>marg</sub>(*S*, *s*) both read the group-wide rate
(*p<sub>g,i</sub>*, defined in §2), or equivalently the group-wide Poisson
mean (λ<sub>*i*</sub>, defined in §2). *V*(*S*, *s*) reads the *Q*-long
vector of query-conditional rates (*p<sub>i,q</sub>*, defined in §2) on
each unit. The two skip fitnesses are estimated skip ratios in [0, 1]
and take *s* as a skip threshold. *G*(*S*) uses *s* only to pack the
iterator *i*. Cuts are ranked by incremental gain per extra group, not
by a derivative against *s*.

**Takeaway.** Rank cuts with *V*(*S*, *s*). Use *G*(*S*) only to drop
hopeless grains cheaply. Do not treat *V*<sub>marg</sub>(*S*, *s*) as a
substitute for *V*(*S*, *s*). None of the three is a shipping decision;
held-out waste (formal statement §2.5) remains the score of a layout.
