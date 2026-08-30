"""Turning `(strategy name, parameter mapping)` into something runnable (7.1.8).

This module is the **sole authority on admissibility**.  A caller — the CLI, a test, the
GUI's server — hands over a name and a mapping that came from somewhere untrusted, and
gets back either a runnable strategy or every reason it is not runnable.  No surface
above this one re-checks a domain rule: a browser checks that a field is filled in, and
that is a property of the form, not of the domain.

Two rules shape the errors it produces.

*Every violation at once.*  Reporting the first and stopping turns a four-block form into
four round trips.  So validation collects.

*Every violation addressed* (7.1.8.1).  A message is only actionable if it says which
thing it is about.  A violation therefore carries the parameter it concerns, the index
within that parameter when the value is a list, and the caller's own name for the
strategy when several are being built together — the triple the GUI renders as
"AS-3, expressions, stage 2".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .expressions import ExpressionError, compile_chain
from .registry import entry
from .schema import SEQUENCE_KINDS, ParamSpec, StrategyEntry


@dataclass(frozen=True)
class Violation:
    """One reason a parameter mapping cannot be run, and where it lives."""

    message: str
    #: Which parameter is at fault.  ``None`` when the whole strategy is.
    parameter: str | None = None
    #: Position within a variable-length value (7.1.7.3), zero-based.
    index: int | None = None
    #: The caller's own identifier for this strategy, when several are built at once.
    block: str | None = None

    def addressed(self) -> str:
        """The message with its address in front, as a reader would want to read it."""
        where = [part for part in (self.block, self.parameter) if part]
        if self.index is not None:
            where.append(f"stage {self.index + 1}")
        return f"{', '.join(where)}: {self.message}" if where else self.message

    def describe(self) -> dict[str, Any]:
        """JSON-native, so the address survives the trip to a form field."""
        described: dict[str, Any] = {"message": self.message}
        for name in ("parameter", "index", "block"):
            if getattr(self, name) is not None:
                described[name] = getattr(self, name)
        return described

    def within(self, block: str | None) -> "Violation":
        return self if block is None else Violation(
            self.message, self.parameter, self.index, block
        )


class FactoryError(ValueError):
    """Every violation in one mapping, reported together."""

    def __init__(self, violations: Sequence[Violation]):
        self.violations = tuple(violations)
        super().__init__("; ".join(v.addressed() for v in self.violations))

    def describe(self) -> dict[str, Any]:
        return {"violations": [v.describe() for v in self.violations]}


@dataclass(frozen=True)
class BuiltStrategy:
    """A validated strategy, ready to run and ready to be recorded.

    `params` is deliberately JSON-native and canonical rather than a bag of live objects:
    it is what lands in a metric row's `Params` (8.3), so it has to round-trip through
    CSV, and two configurations that produce one layout have to produce one `Params`.
    """

    name: str
    params: dict[str, Any] = field(default_factory=dict)
    block: str | None = None

    def __call__(self, view, **overrides) -> np.ndarray:
        return entry(self.name).call(view, **{**self.params, **overrides})


def build(
    name: str,
    params: Mapping[str, Any] | None = None,
    *,
    features: Mapping[str, np.ndarray] | None = None,
    block: str | None = None,
) -> BuiltStrategy:
    """Validate a parameter mapping and return the strategy it configures.

    `features` is the corpus's partitionable columns.  Given them, a column reference
    inside an expression is checked here rather than at run time — which is what 12.4.1.2
    means by "rejected before anything runs".  Without them the mapping is still checked
    for everything that does not need a corpus, so a caller can validate a form before a
    dataset finishes loading.
    """
    try:
        registered = entry(name)
    except KeyError as unknown:
        raise FactoryError([Violation(str(unknown.args[0]), block=block)]) from None

    coerced, violations = _check(registered, dict(params or {}), features)
    if violations:
        raise FactoryError([v.within(block) for v in violations])
    return BuiltStrategy(name=name, params=coerced, block=block)


def build_all(requests: Iterable[Mapping[str, Any]]) -> list[BuiltStrategy]:
    """Build several strategies, reporting every violation across all of them at once.

    All-or-nothing (12.4.2.11): one bad expression in the fourth block means nothing
    runs, and the caller learns about the first block's problems in the same breath.
    """
    built, violations = [], []
    for request in requests:
        try:
            built.append(
                build(
                    request["name"],
                    request.get("params"),
                    features=request.get("features"),
                    block=request.get("block"),
                )
            )
        except FactoryError as failure:
            violations.extend(failure.violations)
    if violations:
        raise FactoryError(violations)
    return built


# -- validation ---------------------------------------------------------------------


def _check(
    registered: StrategyEntry,
    params: dict[str, Any],
    features: Mapping[str, np.ndarray] | None,
) -> tuple[dict[str, Any], list[Violation]]:
    by_name = {spec.name: spec for spec in registered.params}
    violations: list[Violation] = []
    coerced: dict[str, Any] = {}

    for name in params:
        if name not in by_name:
            offered = ", ".join(sorted(by_name)) or "no parameters at all"
            violations.append(
                Violation(
                    f"unknown parameter {name!r}; {registered.name} takes {offered}",
                    parameter=name,
                )
            )

    for spec in registered.params:
        if spec.name not in params:
            if spec.required and spec.default is None:
                violations.append(
                    Violation(f"{spec.label} is required", parameter=spec.name)
                )
            elif spec.default is not None:
                coerced[spec.name] = spec.default
            continue
        value, failures = _check_one(spec, params[spec.name], features)
        violations.extend(failures)
        if not failures:
            coerced[spec.name] = value

    return coerced, violations


def _check_one(
    spec: ParamSpec, value: Any, features: Mapping[str, np.ndarray] | None
) -> tuple[Any, list[Violation]]:
    if spec.kind in SEQUENCE_KINDS:
        return _check_sequence(spec, value, features)

    checker = {
        "int": _check_int,
        "float": _check_float,
        "bool": _check_bool,
        "choice": _check_choice,
        "column": _check_choice,
    }[spec.kind]
    return checker(spec, value)


def _check_sequence(
    spec: ParamSpec, value: Any, features: Mapping[str, np.ndarray] | None
) -> tuple[Any, list[Violation]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return value, [
            Violation(f"{spec.label} is a list of values", parameter=spec.name)
        ]
    if len(value) > spec.maximum_length:
        return value, [
            Violation(
                f"{spec.label} takes at most {spec.maximum_length} entries,"
                f" and {len(value)} were given",
                parameter=spec.name,
            )
        ]
    if spec.kind == "int_list":
        return _check_int_list(spec, value)
    return _check_expression_set(spec, value, features)


def _check_int_list(spec: ParamSpec, value: Sequence) -> tuple[Any, list[Violation]]:
    coerced, violations = [], []
    for index, item in enumerate(value):
        entry_value, failures = _check_int(spec, item)
        violations.extend(
            Violation(failure.message, spec.name, index) for failure in failures
        )
        coerced.append(entry_value)
    # `not violations` first, and the short-circuit is the point: a rejected entry may be
    # unhashable, so asking whether the entries repeat before knowing they are sound
    # raises where it should have reported. Complaining about repeats among values that
    # are already wrong would be noise anyway.
    if not violations and len(set(coerced)) != len(coerced):
        violations.append(
            Violation(f"{spec.label} repeats a value", parameter=spec.name)
        )
    return coerced, violations


def _check_expression_set(
    spec: ParamSpec, value: Sequence, features: Mapping[str, np.ndarray] | None
) -> tuple[Any, list[Violation]]:
    try:
        parsed = compile_chain([str(item) for item in value], features)
    except ExpressionError as failure:
        return value, _as_violations(spec, failure)

    # Canonical text, so two orderings of one chain are one configuration (12.4.1.3) and
    # therefore one `Params` in the metric table.
    return sorted(str(expression) for expression in parsed), []


def _as_violations(spec: ParamSpec, failure: ExpressionError) -> list[Violation]:
    failures = getattr(failure, "failures", (failure,))
    return [
        Violation(
            # The stage is carried in `index`; repeating it in the text would render as
            # "stage 2: stage 2: ...".
            item.message.split(": ", 1)[-1] if item.stage is not None else item.message,
            parameter=spec.name,
            index=item.stage,
        )
        for item in failures
    ]


def _check_int(spec: ParamSpec, value: Any) -> tuple[Any, list[Violation]]:
    if isinstance(value, bool) or not isinstance(value, int):
        return value, [Violation(f"{value!r} is not a whole number", spec.name)]
    return value, _check_bounds(spec, value)


def _check_float(spec: ParamSpec, value: Any) -> tuple[Any, list[Violation]]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value, [Violation(f"{value!r} is not a number", spec.name)]
    return float(value), _check_bounds(spec, value)


def _check_bounds(spec: ParamSpec, value) -> list[Violation]:
    if spec.minimum is not None and value < spec.minimum:
        return [Violation(f"{value} is below the minimum of {spec.minimum}", spec.name)]
    if spec.maximum is not None and value > spec.maximum:
        return [Violation(f"{value} is above the maximum of {spec.maximum}", spec.name)]
    return []


def _check_bool(spec: ParamSpec, value: Any) -> tuple[Any, list[Violation]]:
    if not isinstance(value, bool):
        return value, [Violation(f"{value!r} is not true or false", spec.name)]
    return value, []


def _check_choice(spec: ParamSpec, value: Any) -> tuple[Any, list[Violation]]:
    if spec.choices is None:
        return value, [
            Violation(
                f"{spec.label} cannot be checked until a dataset says what its"
                f" {spec.source} are called",
                spec.name,
            )
        ]
    if value not in spec.choices:
        offered = ", ".join(str(choice) for choice in spec.choices) or "nothing"
        return value, [Violation(f"{value!r} is not one of {offered}", spec.name)]
    return value, []
