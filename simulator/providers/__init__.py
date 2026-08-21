"""The provider registry.

A provider turns *something* — a generator's parameters, a directory of exported
production CSVs — into a dataset directory satisfying :mod:`simulator.core.contract`.
The simulator selects one by name and knows nothing else about it.

Mirrors ``strategies/registry.py`` deliberately: two plugin points, one shape.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol


class Provider(Protocol):
    def __call__(self, config, out_dir: str | Path) -> Path:
        """Write a contract-satisfying dataset into ``out_dir`` and return its path."""


_REGISTERED_PROVIDERS: dict[str, Callable] = {}


def register(name: str):
    def wrap(provider):
        _REGISTERED_PROVIDERS[name] = provider
        provider.provider_name = name
        return provider

    return wrap


def get(name: str):
    if name not in _REGISTERED_PROVIDERS:
        raise KeyError(
            f"unknown provider {name!r}; registered: {sorted(_REGISTERED_PROVIDERS)}"
        )
    return _REGISTERED_PROVIDERS[name]


def available() -> list[str]:
    return sorted(_REGISTERED_PROVIDERS)


# Registration by import.  Kept at the bottom: each provider imports this module.
from . import external, synthetic  # noqa: E402,F401
