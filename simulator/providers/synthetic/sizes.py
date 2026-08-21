"""The size model.

The blob is never materialized — only its size is.  A lognormal scaled by category gives
the spread that matters: a wiper-blade sale record is a few kilobytes, a drivetrain
assembly carries fitment tables and supersession history into the hundreds.

The blob is the corpus.  Everything else on the row — the ids, the four feature columns —
is scalar and rounds to nothing beside it, so it carries no byte column of its own and
the objective is weighted by blob bytes alone.

Calibrated so the **mean compressed event is ~10 KB**, which is what makes the container
target readable: 10 MB is 1000 rows, and every sweep point is a round row count.
"""

from __future__ import annotations

import numpy as np

#: Multiplies the lognormal draw.  Heavy assemblies carry far more attached detail than
#: consumables do.
CATEGORY_MULTIPLIER = {
    "brakes": 1.0,
    "batteries": 0.7,
    "filters": 0.5,
    "tires": 1.2,
    "suspension": 1.6,
    "belts_and_hoses": 0.6,
    "lighting": 0.8,
    "exhaust": 1.5,
    "cooling": 1.1,
    "steering": 1.7,
    "sensors": 0.9,
    "wipers": 0.4,
    "body": 2.2,
    "drivetrain": 2.6,
}

# Premium parts carry more documentation, but price is a much weaker driver than
# category: a tier-9 filter is still a small record.
PRICE_TIER_SIZE_SLOPE = 0.06


def generate(cfg, rng, features: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    n = cfg.n_events

    category_mult = np.ones(n)
    for category, multiplier in CATEGORY_MULTIPLIER.items():
        category_mult[features["feature_category"] == category] = multiplier

    price_mult = 1.0 + PRICE_TIER_SIZE_SLOPE * features["feature_price_tier"].astype(
        np.float64
    )

    base = rng.lognormal(mean=np.log(cfg.size_median_bytes), sigma=cfg.size_sigma, size=n)
    blob_decompressed = np.maximum(base * category_mult * price_mult, 64.0)

    lo, hi = cfg.compression_ratio_range
    blob_compressed = np.maximum(blob_decompressed / rng.uniform(lo, hi, size=n), 32.0)

    return {
        "blob_detail_compressed_bytes": blob_compressed.astype(np.int64),
        "blob_detail_decompressed_bytes": blob_decompressed.astype(np.int64),
    }
