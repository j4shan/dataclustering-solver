"""Management cost — the simulator's own construct, not the formulation's.

The formulation delegates index cost entirely and lets a container size floor be the
only force opposing fine granularity.  The simulator charges for container count so the
scatter chart has a second axis.  Results plotted against it are not claims about the
formulated problem.

Named ``management_cost`` throughout to keep it distinct from *read* cost, which is what
"cost" means in the formulation.  Units are abstract by design: the weights below are
arbitrary, and what the model is for is the shape of the trade-off and the seam that
lets it be replaced.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_MODELS: dict[str, "ManagementCostModel"] = {}


@dataclass(frozen=True)
class CostWeights:
    per_container: float = 1.0  # bookkeeping charged for each container held
    fragmentation: float = 1.0  # penalty for containers short of the target record count
    per_gigabyte_rebuilt: float = 0.0  # one-off construction, bytes moved


class ManagementCostModel:
    name = "abstract"

    def __call__(
        self,
        container_bytes: np.ndarray,
        container_records: np.ndarray,
        target_container_rows: int,
        weights: CostWeights,
    ) -> dict[str, float]:
        """Charge a layout for the containers it holds and how far each falls short.

        Fragmentation is measured in **records against the swept capacity** (7.2.3.1) —
        the shortfall has to share a unit with the target it is short of.  The rebuild
        term stays in bytes, because bytes are what actually move.
        """
        container_count = int(container_bytes.size)
        shortfall = np.clip(target_container_rows - container_records, 0, None)
        fragmentation = (
            float((shortfall / target_container_rows).sum()) if target_container_rows else 0.0
        )
        gigabytes_rebuilt = float(container_bytes.sum()) / 1e9

        return {
            "management_cost": (
                weights.per_container * container_count
                + weights.fragmentation * fragmentation
                + weights.per_gigabyte_rebuilt * gigabytes_rebuilt
            ),
            "management_cost_container_term": weights.per_container * container_count,
            "management_cost_fragmentation_term": weights.fragmentation * fragmentation,
            "management_cost_rebuild_term": weights.per_gigabyte_rebuilt * gigabytes_rebuilt,
        }


def register(model: ManagementCostModel) -> ManagementCostModel:
    _MODELS[model.name] = model
    return model


def get(name: str = "abstract") -> ManagementCostModel:
    return _MODELS[name]


register(ManagementCostModel())
