"""Parameters of the synthetic provider.

These live with the generator that owns them, not in the simulator's config package.
Nothing above the provider seam reads this file — the harness learns a corpus's shape
from the corpus, not from the parameters that produced one.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DatasetConfig:
    """A dataset id is a hash over these, so every field here changes the corpus."""

    name: str = "auto-parts"
    seed: int = 20260809

    n_events: int = 600_000

    # Transaction history.  Queries run over the last `n_query_days`.
    #
    # History must be long enough for `half_life_days` to reach a genuinely cold region,
    # or the corpus has no skippable data by construction.  A 1000-row container is only
    # skippable when its expected selection count falls below ~1; at a 5% rate over 1M
    # events that is 50 on average, so decay has to push the oldest data ~50x down, which
    # takes about 12 half-lives.  Three years of history against a three-month half-life
    # is exactly that; one year (4 half-lives) leaves the oldest data still 6% as likely
    # as today's, and nothing is ever cold.
    first_transaction_date: str = "2023-01-01"
    n_transaction_days: int = 1095
    n_query_days: int = 180

    # Features.  Flat, no hierarchy: a price tier, a warranty term, a part category.
    n_price_tier: int = 10
    min_warranty_years: int = 1
    max_warranty_years: int = 6

    #: Tenants.  `brand_id` is the multi-tenant client identifier, and the strongest single
    #: driver of demand in the corpus: each brand draws a multiplier on this relative scale,
    #: so the most-wanted brand's parts are selected ~10x as often as the least-wanted at
    #: equal price, warranty and age.  The overall selection rates are unchanged — the draw
    #: is normalized to hit them — so the multiplier redistributes demand rather than adding
    #: it, which is what makes brand a *clusterable* signal rather than a volume knob.
    n_brands: int = 40
    brand_demand_multiplier_range: tuple[int, int] = (1, 10)

    # Size model: lognormal per event, scaled by category and price tier.  Calibrated so
    # the mean *compressed* event is ~10 KB and a 10 MB container target therefore lands
    # on 1000 rows.  Note the target is compressed bytes, which the compression ratio
    # divides down from this median — hence the gap between the two numbers.
    size_median_bytes: float = 23_200.0
    size_sigma: float = 0.9
    compression_ratio_range: tuple[float, float] = (3.0, 6.0)

    # Workload.  Both query types run every day.
    profitability_rate: float = 0.05
    complaint_rate: float = 0.005

    #: Recency is a decaying weight, not a cutoff.  A transaction's selection probability
    #: is scaled by 0.5 ** (age_days / half_life_days), so demand fades smoothly into the
    #: past and no transaction is ever categorically unreachable.  Three months.
    half_life_days: float = 91.0

    # Michaelis-Menten half-saturation, jittered per query within +/- this fraction.
    half_saturation: float = 0.25
    half_saturation_jitter: float = 0.4

    #: Fraction of run days held out.  The split is temporal: earliest days build.
    validation_fraction: float = 0.5

    def as_dict(self) -> dict:
        return asdict(self)
