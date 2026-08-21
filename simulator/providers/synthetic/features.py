"""Event columns — one auto part sale, described four ways plus a date.

Columns are grouped by role, and the group is visible in the name:

    record_id            the unique key, a dense bigint
    brand_id             the client identifier in a multi-tenant system

    feature_price_tier       0-9, ten buckets, low tier = cheap part
    feature_warranty_years   1-6
    feature_category         a common top-level auto parts label
    feature_transaction_date the axis every query scopes on

``brand_id`` is an entity id rather than a descriptive feature, but it is the single
strongest driver of demand in this corpus — see ``brand_demand_multipliers`` — so it
reaches strategies alongside the ``feature_`` columns and can be partitioned on.

Deliberately small.  You should be able to read this file and predict what a query will
select.
"""

from __future__ import annotations

import numpy as np

#: Top-level labels of the kind a parts catalogue actually uses.  Flat: no parent
#: system column, so a layout can only group on exact category equality.
CATEGORIES = (
    "brakes",
    "batteries",
    "filters",
    "tires",
    "suspension",
    "belts_and_hoses",
    "lighting",
    "exhaust",
    "cooling",
    "steering",
    "sensors",
    "wipers",
    "body",
    "drivetrain",
)

# Fast-moving consumables outsell heavy assemblies, so the mix is uneven.
CATEGORY_WEIGHTS = np.array(
    [0.14, 0.11, 0.13, 0.10, 0.06, 0.07, 0.06, 0.04, 0.05, 0.04, 0.06, 0.06, 0.04, 0.04]
)

# Cheap parts are sold constantly; expensive ones are rarer.  A mild decreasing skew
# over the ten tiers, not a heavy tail.
PRICE_TIER_DECAY = 0.85


#: Brand names are generated rather than listed: a tenant identifier in a real system is
#: an opaque key, and inventing forty plausible-looking aftermarket brands would suggest
#: the label carries meaning the model does not give it.
BRAND_KEY_FORMAT = "brand-{:03d}"

#: Catalogue share per brand.  A few large tenants and a long tail of small ones, which
#: is what a multi-tenant system actually looks like — and what makes brand-clustered
#: containers differ in size rather than all landing at the mean.
BRAND_SHARE_DECAY = 0.93


def brand_keys(n_brands: int) -> np.ndarray:
    return np.array([BRAND_KEY_FORMAT.format(i) for i in range(n_brands)])


def brand_share_weights(n_brands: int) -> np.ndarray:
    weights = BRAND_SHARE_DECAY ** np.arange(n_brands)
    return weights / weights.sum()


def brand_demand_multipliers(cfg, rng) -> np.ndarray:
    """One demand multiplier per brand, on the configured relative scale.

    Drawn from the seeded generator like everything else, so the corpus stays
    reproducible from seed and parameters alone.  The scale is *relative*: the workload
    normalizes its draw to hit the configured selection rate, so these redistribute
    demand across brands without changing how much of it there is.
    """
    low, high = cfg.brand_demand_multiplier_range
    return rng.integers(low, high + 1, size=cfg.n_brands).astype(np.float64)


def price_tier_weights(n_price_tier: int) -> np.ndarray:
    weights = PRICE_TIER_DECAY ** np.arange(n_price_tier)
    return weights / weights.sum()


def warranty_weights(n_terms: int) -> np.ndarray:
    """Short warranties dominate; six-year terms are the premium exception."""
    weights = np.linspace(1.0, 0.35, n_terms)
    return weights / weights.sum()


def generate(cfg, rng) -> dict[str, np.ndarray]:
    n = cfg.n_events

    warranty_terms = cfg.max_warranty_years - cfg.min_warranty_years + 1
    day_offset = rng.integers(0, cfg.n_transaction_days, size=n)
    first_day = np.datetime64(cfg.first_transaction_date, "D")

    brand_index = rng.choice(cfg.n_brands, size=n, p=brand_share_weights(cfg.n_brands))

    return {
        # The tenant this sale belongs to.  Kept as its own column rather than folded in
        # with the feature_ group: it identifies a client, it does not describe the part.
        "brand_id": brand_keys(cfg.n_brands)[brand_index],
        # Sorted so record_id order is arrival order: a real corpus accumulates in time,
        # and the shipped strategy's insertion order should mean something.
        "feature_transaction_date": (
            first_day + np.sort(day_offset).astype("timedelta64[D]")
        ),
        "feature_price_tier": rng.choice(
            cfg.n_price_tier, size=n, p=price_tier_weights(cfg.n_price_tier)
        ).astype(np.uint8),
        "feature_warranty_years": (
            cfg.min_warranty_years
            + rng.choice(warranty_terms, size=n, p=warranty_weights(warranty_terms))
        ).astype(np.uint8),
        "feature_category": np.asarray(CATEGORIES)[
            rng.choice(len(CATEGORIES), size=n, p=CATEGORY_WEIGHTS / CATEGORY_WEIGHTS.sum())
        ],
        # Generator truth, drawn here so there is exactly one draw: the workload weights
        # its selection by this column, and the provider writes it as a hidden column.
        # Deriving it twice from the seed would desync the two the moment anything else
        # consumed a random number in between.
        "_brand_demand_multiplier": brand_demand_multipliers(cfg, rng)[brand_index],
    }
