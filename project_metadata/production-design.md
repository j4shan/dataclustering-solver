# A Delta Lake Prototype

This document maps the abstract storage model of
`problem-statement.md` onto one concrete engine: Delta Lake
tables read by Spark on Databricks. It names the mechanism that realizes each formal object,
and it records the places where the engine cannot honour an assumption the formulation makes.

**It is downstream of the formulation and never amends it.** The formulation is stated over
an abstract system precisely so that this exercise can be done afterwards and more than once.
Where Databricks does something the model does not describe, the divergence is written down
in §7 with its cost. Nothing here re-poses the problem to fit the engine, and no requirement
in the formulation is restated in this document's own words.

**Vocabulary is the formulation's.** *Container*, *layout*, *index*, *activation*, *waste*,
*selection*, *support*, *skipping ratio* keep their meanings from §1–§5 there and are not
re-defined here. Engine terms such as file, cluster key and pruning appear beside the formal
object each one realizes, so a reader can always trace an engine word back to the term it
stands for.

---

## 1. The mapping in one table

| formal object | symbol | Databricks / Spark mechanism |
| --- | :-: | --- |
| event | $e$ | a row of a Delta table, identified by the `record_id` column |
| corpus, its size | $E$, $N$ | the table at a given version |
| container, its contents | $c$, $E_c$ | a **Parquet data file** registered as active in the Delta transaction log |
| container count | $K$ | the number of active files |
| the fetch operation | $\texttt{FETCH}(c)$ | one file read task in a Spark file scan |
| the layout, the decision variable | $\lambda$ | **which file each row is written into**: `CLUSTER BY` (liquid clustering), or legacy `PARTITIONED BY` plus `OPTIMIZE … ZORDER BY` |
| the index table | $I$ | per-file **statistics in `_delta_log`** (min, max and null counts per indexed column), plus partition values |
| index width ratio | $\rho$ | statistics bytes per file ÷ data bytes per file |
| pre-scan | phase 1 | transaction-log replay and predicate pruning, before any data file is fetched |
| activation | $a_{c,q}$ | the file survives pruning and is scheduled into the scan |
| materialized volume | $M_q$ | rows (or bytes) read by the scan, before the filter is applied |
| waste | $w_q$ | rows read and then discarded by the filter |
| skipping ratio | $\sigma_q$ | files and bytes pruned, as reported by the query profile |
| the selection log | $L$ | **not natively materialized** (see §6) |
| demand breadth | $d_c$ | how many queries read a given file |

Three of these carry the whole design and are taken in turn: containerization (§2), the
layout that assigns to containers (§3), and the index that decides which containers a query
activates (§4).

---

## 2. Containerization: the container is a file

A Delta table is a set of immutable Parquet files plus a transaction log naming which of them
are currently active. Spark's unit of read scheduling is a file (or a split of one), and the
filter is applied after the read. That is exactly the fetch operation of §2: `FETCH` returns
contents, and cost is charged for what comes back, whatever the caller keeps.

**The container is the file, not the row group.** Parquet subdivides a file into row groups,
and a scan can skip a row group whose own statistics exclude the predicate. The formulation
has no object at that granularity, so the mapping takes the coarser one and treats row-group
skipping as a second-order effect that lowers absolute read volume without changing which
layout wins. §7.2 records the cost of that simplification.

**Container size is a target, not a guarantee.** `delta.targetFileSize`, optimized writes, and
`OPTIMIZE` bin-packing aim for a file size; the achieved size varies with compressibility and
with how the clustering keys divide the data. The sweep axis of the harness, target container
bytes, maps onto this property directly, which is what gives the sweep meaning against a real
engine.

**The floor on container size is real and load-bearing.** The problem statement's §5 permits an
arbitrarily fine partition subject only to a size bound; Databricks does not. Every file costs
a log entry, a task, and an object-store round trip, so a layout of very many small containers
loses to per-file overhead the formulation does not model. The simulator charges for this
separately in `simulator/core/management_cost.py` and is explicit that the charge is its own
construct rather than the formulation's. In production the same force is what makes
high-cardinality Hive partitioning fail.

---

## 3. The layout: how a row reaches a file

$\lambda$ is realized as the write path. Three mechanisms have implemented it, each
superseding the one before.

**`PARTITIONED BY` (Hive-style directories).** Each distinct value of the partition columns
gets a directory, and a query filtering on those columns opens only the matching ones. This
realizes $\lambda$ as a function of declared attributes, which is a strong constraint: it makes
the layout trivially assignable at write time (§2.2 of the problem statement, and the `route`
seam at 7.1.6 of the simulator spec), and equally makes it incapable of expressing any grouping
the schema does not already name. High cardinality drives container count up and container size
down until §2's floor is breached.

**`ZORDER BY` under `OPTIMIZE`.** A rewrite step that orders rows along a Z-order curve over
several columns and bin-packs them into files. It expresses layouts that directory partitioning
cannot, and it pays for that by running as a periodic full rewrite.

**`CLUSTER BY`, liquid clustering.** The current mechanism, which replaces both of the above.
Rows are clustered on the declared keys incrementally as they are written and reclustered in
the background, so the layout is maintained rather than rebuilt, and clustering keys can be
changed without rewriting the table. This is the mechanism a strategy from this project would
target: a strategy's output is a grouping, and liquid clustering is how a grouping becomes a
physical layout that survives ongoing writes.

**`CLUSTER BY AUTO` is the closest thing production has to this problem, and it optimizes a
different objective.** Automatic liquid clustering analyses the table's historical query
workload, identifies candidate clustering columns from **query predicates and join filters**,
and changes keys only when predicted skipping gains outweigh the clustering cost. That is
workload-aware layout, and it is a serious baseline. But the signal it learns from is the
*stated predicate*, whereas the objective of §3.5 is defined over the *observed selection
relation*. §3.3 of the formulation is precisely about that gap: $L$ records which events a
query selected, never why, and nothing requires $S_q$ to coincide with any predicate over
event attributes. Where predicate and demand coincide, `CLUSTER BY AUTO` is close to the right
answer and is cheap. Where they diverge, which is the case this project exists to study, it is
optimizing a proxy, and the residual is exactly the structure §8.5 calls latent.

---

## 4. The index: what decides activation

Phase 1 of §2's two-phase execution is served by the Delta transaction log. For each active
file the log carries per-column statistics (minimum, maximum, null count) for the first 32
columns of the schema by default (`delta.dataSkippingNumIndexedCols`, or a named set via
`delta.dataSkippingStatsColumns`). A query's predicate is evaluated against those ranges, and
a file whose range cannot contain a matching row is pruned. What survives is the set of
activated containers.

Two properties of this index differ from the model's, and both matter enough to count as
design inputs.

**It is per container, not per event.** §2.1 models $I$ as one row per event: a narrow
vertical slice of the corpus, scanned in full, resolving the predicate exactly. Delta's index
holds one entry per *file*, summarising its contents as ranges. It is therefore far smaller
than the model's, since $\rho$ in production shrinks by roughly the number of rows per file,
and it is correspondingly cheaper to scan. The model overstates index cost, in the direction
that is safe for the argument of §2.1.

**It is approximate, and its precision depends on the layout.** A range can overlap a
predicate without any row matching, so pruning admits false positives: production activation
is a *superset* of the model's $a_{c,q}$. The consequence is structural. The formulation drops
the index from the objective because $I$'s row count, width, and scan cost are invariant under
$\lambda$, and that remains true here. Its *precision*, however, is not invariant: changing the
layout changes the min/max ranges themselves, and therefore changes how many files are
activated spuriously. That loss does not appear as index cost. It appears as additional
activation, and so as additional waste, which lands back inside $\mathcal{W}(\lambda)$. The
practical rule follows: **measure waste from what the scan actually read, never from a
recomputed $a_{c,q}$**. A recomputed activation credits the layout with skipping the index
failed to achieve.

Two further mechanisms narrow reads below file granularity without changing which files are
activated: **deletion vectors**, which mark rows deleted without rewriting the file, and
Databricks' **Predictive I/O** for selective reads. Both reduce absolute cost and neither
changes the ordering of layouts under a fixed workload, so both sit outside the model by
choice.

---

## 5. Observing the objective

$\mathcal{W}(\lambda)$ is not a metric the platform emits, but every term of it is
recoverable from the query profile of a scan:

| quantity | where it comes from |
| --- | --- |
| $M_q$ | scan output rows, and bytes read, *before* the filter |
| $\lvert S_q \rvert$ | rows surviving the filter |
| $w_q$ | the difference of the two |
| $\sigma_q$ | files or bytes pruned over the total, reported directly as pruning statistics |
| $d_c$ | files read, accumulated per file across the workload |

The unit deserves care. The formulation counts events, and a Spark scan reports both rows and
bytes. The two rank layouts identically only when event size is independent of the layout, and
it stops being independent once clustering groups similar rows and changes their compression.
Bytes are therefore the honest unit in production, which is why the harness reports both a
record and a byte skipping ratio.

---

## 6. The selection log in production

This is the hardest part of the mapping, and it is a gap rather than a mechanism.

The formulation takes $L$ as observed input: for each query, which events it selected.
Databricks records query *history* (text, predicates, scan statistics and timings, in
`system.query.history`), and Delta records table *history*. Neither records which rows a query
returned. $L$ therefore has to be constructed, and there are three honest ways to do it:

1. **Replay.** Re-run each distinct query's predicate against the table projecting only
   `record_id`, and append the result to the log. Exact, and it costs a scan per query. That is
   affordable as a periodic offline job over a distinct-query set, though not as an online
   mechanism.
2. **Instrument the read path.** Have the application that issues queries emit the identifiers
   it consumed. Exact, cheap, and requires the application's cooperation, which is often the
   thing that cannot be obtained.
3. **Sample.** Reconstruct $L$ over a sampled subset of queries or of the corpus. Cheap and
   approximate; the sampling error lands directly in the objective.

Whichever is chosen, the resulting table is append-only and grows monotonically, which is the
workload evidence accumulated during the fixed study period in §6.3 of the problem statement. It
is also the corpus this project's harness consumes, so the external provider seam is where a real
deployment attaches.

---

## 7. Divergences and their cost

Recorded here and left open, per the standing rule that the engine does not get to restate the
problem.

| # | The formulation assumes | Databricks does | Cost of the divergence |
| --- | --- | --- | --- |
| 7.1 | The index resolves the predicate exactly, one row per event | Per-file min/max ranges over the first 32 columns | Activation is a superset of $a_{c,q}$; the extra reads are real waste. Measure waste from the scan, not from a recomputed activation (§3.4) |
| 7.2 | `FETCH(c)` returns the whole of $E_c$; no per-event addressing | Column projection, row-group skipping, deletion vectors, Predictive I/O | $\mathcal{W}(\lambda)$ overstates absolute volume. It stays a faithful *ranking* only while projections are stable across candidate layouts; measure in bytes with the real projection |
| 7.3 | The index cost is invariant under $\lambda$, so §3.5 may drop it | Its size and scan cost are invariant; its **precision** is not | The invariance argument survives for the objective's form, but the precision loss must be counted as waste rather than as index cost |
| 7.4 | $L$ is observed | Query history records predicates, not selected rows | $L$ must be replayed, instrumented, or sampled (§6). Sampling error enters the objective directly |
| 7.5 | Waste is the only layout-dependent cost | Every container costs a log entry, a task, and a round trip | A layout of many small containers wins on paper and loses in production. The simulator charges this separately and says so |
| 7.6 | One fixed layout is evaluated | `OPTIMIZE`, background reclustering, and deletion vectors change $\lambda$ underneath | Pin measurement to a table version (`VERSION AS OF`); Delta's time travel makes this exact rather than approximate |
| 7.7 | A layout is a function to be evaluated on one event at a time (§2.2 of the problem statement) | Liquid clustering assigns incrementally on write and reclusters asynchronously | Production *does* have the `route` of 7.1.6, but it is approximate and eventually consistent: a row's container is provisional until reclustering settles |

---

## 8. What this document does not settle

- **Which strategy to run.** This project ships none, and mapping the mechanisms changes
  nothing about that. §3 establishes only where a strategy's output would attach.
- **Index design.** The problem statement models predicate resolution in §2.1, while the simulator
  spec excludes index design in 11.2. The statistics described in §4 are the engine's own; nothing here proposes a
  secondary structure over them.
- **Cost in currency.** Exclusion 11.4 keeps the cost model abstract and pluggable, and
  translating tasks and round trips into DBUs is that plugin's job, not this document's.
- **Any claim about how a real table performs.** No figure in this document is measured. The
  quantities of §5 say where a measurement would come from, not what it would say.

---

## Sources

- [Use liquid clustering for tables](https://docs.databricks.com/aws/en/tables/clustering):
  `CLUSTER BY`, `CLUSTER BY AUTO`, and its relationship to partitioning and `ZORDER`
- [Announcing Automatic Liquid Clustering](https://www.databricks.com/blog/announcing-automatic-liquid-clustering):
  key selection from historical query predicates and join filters
- [Data skipping](https://docs.databricks.com/aws/en/tables/data-skipping):
  per-file statistics, `delta.dataSkippingNumIndexedCols`, `delta.dataSkippingStatsColumns`
- [Delta Lake optimizations](https://docs.delta.io/optimizations-oss/): `OPTIMIZE`,
  bin-packing, and Z-ordering in the open-source format

Version-dependent values, such as the 32-column statistics default, target file sizes, and
which mechanisms are generally available, are stated as the documentation above states them.
Check them there before relying on them.
