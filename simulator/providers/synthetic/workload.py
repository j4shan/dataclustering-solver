"""The workload — two standing daily reports over six months.

Both run every day, so 180 run days produce 360 queries. Each weights every transaction
that already existed when it ran, by two independent factors:

    profitability   selects ~5%   of the corpus, favours HIGH price
    complaint       selects ~0.5% of the corpus, favours LOW price and SHORT warranty

    both            scaled by recency, half-life 3 months
                    and by the event's brand demand multiplier

``brand_id`` is the strongest single signal in the corpus: each tenant draws a multiplier
on a 1-10 relative scale, so demand concentrates on a handful of brands.  Because the
draw is normalized to hit the target rate, this redistributes demand rather than adding
it — the overall selection rates are unchanged and brand becomes a *clusterable*
structure rather than a volume knob.

**Recency is a decaying weight, not a cutoff.** A transaction 89 days old is somewhat less
likely to be selected than one from yesterday, and one 400 days old is much less likely —
but never categorically excluded. This is the honest model of an analyst's attention:
interest fades, it does not stop at a boundary.

    decay(age) = 0.5 ** (age_days / half_life_days)

The only hard edge is causality: a query cannot select a transaction that had not happened
yet when it ran.

Selection weight is the product of the feature curve and the decay, normalized so the
*expected* count hits the target rate, then drawn Bernoulli — so a query's realized
selection set varies around the rate rather than hitting it exactly, as an observed
workload would.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PROFITABILITY, COMPLAINT = 0, 1

QUERY_TYPE_NAMES = {PROFITABILITY: "profitability", COMPLAINT: "complaint"}


@dataclass
class Workload:
    query_time: np.ndarray  # datetime64[D][queries] — the day the report ran
    query_type: np.ndarray  # int8[queries]
    set_name: np.ndarray  # "training" / "validation"
    half_saturation: np.ndarray  # float32[queries] — generator truth
    selection_sets: list[np.ndarray]  # S_q, as event indices


def _saturating(x: np.ndarray, half: float) -> np.ndarray:
    """Michaelis-Menten. Rises fast, then flattens; ``half`` sets where the knee sits."""
    return x / (x + half)


def recency_decay(age_days: np.ndarray, half_life_days: float) -> np.ndarray:
    """``0.5 ** (age / half_life)`` — 1.0 today, 0.5 at one half-life, never 0."""
    return np.exp2(-age_days / half_life_days)


def _draw(weights: np.ndarray, target_count: float, rng) -> np.ndarray:
    """Bernoulli draw whose expected size is ``target_count``."""
    total = weights.sum()
    if total <= 0:
        return np.empty(0, dtype=np.int64)
    probability = np.clip(weights * (target_count / total), 0.0, 1.0)
    return np.flatnonzero(rng.random(weights.size) < probability)


def generate(config, rng, features: dict[str, np.ndarray]) -> Workload:
    price = features["feature_price_tier"].astype(np.int64)
    warranty = features["feature_warranty_years"].astype(np.int64)

    # feature_transaction_date is generated sorted, so "transactions that already existed"
    # is a prefix and searchsorted finds its end without touching the rest.
    transaction_day = (
        features["feature_transaction_date"]
        - np.datetime64(config.first_transaction_date, "D")
    ).astype(np.int64)

    # Demand by tenant, drawn once in the feature generator.  Folded into the selection
    # weight below, so a brand with a multiplier of 10 has its parts selected ten times as
    # often as a brand with 1 at equal price, warranty and age.
    brand_weight = features["_brand_demand_multiplier"].astype(np.float64)

    price_span = max(config.n_price_tier - 1, 1)
    warranty_span = max(config.max_warranty_years - config.min_warranty_years, 1)

    # The feature curve depends only on (price_tier, warranty_years) — 60 combinations at
    # most — so it is evaluated on the small grid and gathered, not recomputed per event.
    price_levels = np.arange(config.n_price_tier) / price_span
    warranty_levels = 1.0 - (
        np.arange(config.min_warranty_years, config.max_warranty_years + 1)
        - config.min_warranty_years
    ) / warranty_span
    warranty_index = warranty - config.min_warranty_years

    first_run_day = config.n_transaction_days - config.n_query_days
    run_days = np.arange(first_run_day, config.n_transaction_days)
    training_days = int(round(config.n_query_days * (1.0 - config.validation_fraction)))

    def jitter() -> float:
        spread = config.half_saturation * config.half_saturation_jitter
        return float(rng.uniform(config.half_saturation - spread, config.half_saturation + spread))

    query_time, query_type, set_name = [], [], []
    half_saturation, selection_sets = [], []

    first_day = np.datetime64(config.first_transaction_date, "D")
    plan = ((PROFITABILITY, config.profitability_rate), (COMPLAINT, config.complaint_rate))

    for day_index, run_day in enumerate(run_days):
        # Causality: only transactions that had already happened are selectable.
        existing = int(np.searchsorted(transaction_day, run_day + 1))
        age = run_day - transaction_day[:existing]
        decay = recency_decay(age, config.half_life_days)

        for kind, rate in plan:
            half = jitter()
            if kind == PROFITABILITY:
                curve = _saturating(price_levels, half)[price[:existing]]
            else:
                curve = (
                    _saturating(1.0 - price_levels, half)[price[:existing]]
                    * _saturating(warranty_levels, jitter())[warranty_index[:existing]]
                )

            selected = _draw(
                curve * decay * brand_weight[:existing], rate * config.n_events, rng
            )
            if selected.size == 0:  # every query must select something
                selected = rng.integers(0, max(existing, 1), size=1)

            query_time.append(first_day + np.timedelta64(int(run_day), "D"))
            query_type.append(kind)
            half_saturation.append(half)
            selection_sets.append(np.unique(selected).astype(np.int32))
            set_name.append("training" if day_index < training_days else "validation")

    return Workload(
        query_time=np.array(query_time, dtype="datetime64[D]"),
        query_type=np.array(query_type, dtype=np.int8),
        set_name=np.array(set_name),
        half_saturation=np.array(half_saturation, dtype=np.float32),
        selection_sets=selection_sets,
    )
