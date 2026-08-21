"""Sweep configuration.

Dataset parameters are *not* here.  They belong to whichever provider owns them —
``providers/synthetic/config.py`` for the generator, nothing at all for an external
corpus — because the simulator learns a corpus's shape by reading the corpus.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The four capacities the GUI's benchmark sweeps the baseline across, and prefills every
#: new strategy block with (12.4.2.7, 12.4.5.1).  Four rather than the eight below because
#: the summary table reserves four rows for the baseline and no more.
INTERACTIVE_CAPACITIES = (1000, 2000, 4000, 8000)


@dataclass(frozen=True)
class SweepConfig:
    """The parameter swept along the x-axis of the line chart.

    Denominated in **records, not bytes** (7.2.3.1).  Containers have always held a fixed
    row count — a byte target was converted to one on the way in, against the corpus mean
    — so naming the unit the bucketer actually uses removes the conversion, and removes
    with it the surprise of one target producing different containers on different
    corpora.  Byte figures survive as *measures* throughout: size percentiles, skipping,
    and the objective itself are all still bytes.
    """

    variable: str = "target_container_rows"
    values: tuple[int, ...] = (100, 200, 500, 1000, 2000, 5000, 10_000, 20_000)
    strategies: tuple[str, ...] = ("insertion_order", "random_order")

    #: The shipped operating point, and the one the period chart is drawn at.  Against the
    #: synthetic corpus's ~10 KB mean event this is the ~10 MB container the byte-denominated
    #: sweep used to name directly.
    default_rows: int = 1000
