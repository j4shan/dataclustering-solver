# Problem Statement Appendix

## 1. Terminology

The illustrations accompanying the problem statement use a closet analogy. The following table
maps its informal language to the formal storage problem.

| informal | formal object |
| --- | --- |
| the closet, or wardrobe | the corpus $E$ — every stored event, of size $N$ |
| garment | event $e \in E$, keyed by `record_id` |
| drawer, cabinet | container $c$, with contents $E_c$ |
| a morning's outfit | query $q$, keyed by `query_id`, with selected events $S_q$ |
| the record of what was worn | the selection log $L$ |
| opening a drawer | the `FETCH` operation; the unit of read cost |
| the inventory list, and the tag on each drawer | the index table — one row per garment, scanned before any drawer is fetched |
| garments handled but not worn | waste |
| which garment lives in which drawer | the layout $\lambda$ — the decision variable |

The motivating corpora contain event data, so the problem statement uses *event* for a stored
item. *Record* has the same meaning. A *query* is one observed unit of workload. *Selection*
describes which events the query ultimately needs, while *fetch* describes the physical operation
used to retrieve their containers.

### 1.1 One relation, three views

The statement “query $q$ selected event $e$” can be read from three directions:

| view | name | symbol | meaning |
| --- | --- | --- | --- |
| all observations | selection log | $L$ | every observed query–event selection |
| one query | query selection set | $S_q$ | the events selected by that query |
| one event | event support | $\operatorname{supp}(e)$ | the queries that selected that event |

These are three views of one relation, not three independent inputs. The selection log is the
stored observation; query selection sets and event supports are derived from it.

## 2. Notation

| symbol | reads as | defined |
| --- | --- | --- |
| $E$, $N$, $e$ | the event corpus, its event count, and one event | §1 |
| $\lambda$ | the event-to-container assignment | §1 |
| $c$, $E_c$, $K$ | a container, its contents, and the container count | §1 |
| $\operatorname{size}(e)$, $\operatorname{bytes}(E_c)$ | event size and container byte size | §1 |
| $I$, $\rho$ | the index table and its compressed width ratio | §1.1 |
| $q$, $\mathcal{Q}$, $Q$, $L$ | one query, the query set, the query count, and the selection log | §2.1 |
| $S_q$ | the events selected by query $q$ | §2.2 |
| $\operatorname{supp}(e)$, $\operatorname{supp}(c)$ | the queries selecting an event and fetching a container | §2.2 |
| $u_{e,q}$, $U$ | one selection indicator and the complete selection matrix | §2.2 |
| $a_{c,q}$, $M_q$, $d_c$ | activation, materialized event count, and container demand breadth | §2.4 |
| $\sigma_q$ | the share of the corpus skipped by query $q$ | §2.4 |
| $w_q$, $\mathcal{W}$ | waste for one query and aggregate waste | §2.5 |
| $\tilde{U}$ | the selections after container-level materialization | §2.5 |
| $p$, $X_c$ | random event-selection probability and selected events in one container | §2.6 |
| $m$, $G_g$, $N_g$, $p_g$, $K_g$, $\bar p$ | group count, one group, its event count, selection probability, container allocation, and the corpus-wide selected fraction | §3 |
| $s_{\min}$, $s_{\max}$ | lower and upper container-capacity bounds | §4 |
| $\mathcal{C}$, $s$, $K_s$ | permitted capacities, one capacity, and its resulting container count | §5.1 |
| $T$, $\lambda_{\mathrm{base}}$ | the study period and naive baseline layout | §5.3 |
| $C_{\mathrm{read}}$, $C_{\mathrm{layout}}$, $\operatorname{Advantage}(T)$ | total query-read cost, one-time layout cost, and net study-period advantage | §5.3 |

## 3. Poisson approximation error

The patternless-query model selects each event independently with probability $p$. Let a container
hold $s$ events. Its selected-event count is binomial with mean

$$\mu=sp.$$

The exact binomial activation probability is

$$A_{\mathrm{bin}}=1-(1-p)^s.$$

The Poisson approximation uses

$$A_{\mathrm{pois}}=1-e^{-\mu}.$$

To express the error without the container-size symbol, substitute $s=\mu/p$ into the exact
probability. The difference between exact and approximate activation is then

$$
\Delta_A
=A_{\mathrm{bin}}-A_{\mathrm{pois}}
=e^{-\mu}-(1-p)^{\mu/p}.
$$

To identify its leading term, rewrite the binomial zero-count probability with the exponential
function:

$$
(1-p)^{\mu/p}
=\exp\left(\frac{\mu}{p}\log(1-p)\right).
$$

Apply the Taylor expansion of the natural logarithm about $p=0$:

$$
\log(1-p)
=-p-\frac{p^2}{2}-\frac{p^3}{3}-\cdots.
$$

Substitution gives

$$
\frac{\mu}{p}\log(1-p)
=-\mu-\frac{\mu p}{2}-O(\mu p^2),
$$

and therefore

$$
(1-p)^{\mu/p}
=e^{-\mu}
\,\left(1-\frac{\mu p}{2}+O(p^2)\right).
$$

when $\mu$ remains fixed as $p$ becomes small. The leading activation-probability error is

$$
\boxed{
\Delta_A
\approx
\frac{\mu p}{2}e^{-\mu}
}.
$$

The approximation slightly underestimates activation and, equivalently, slightly overestimates
skipping. The main statement uses only the qualitative conclusion: a highly selective predicate
has a small selected fraction $p$, and the Poisson approximation improves as $p$ decreases.
