"""What a strategy takes as parameters, declared as data.

A strategy that wants to be configurable registers an ordered list of `ParamSpec`
alongside itself.  The list is **declarative data, not code** (7.1.7.1): every field is a
JSON-native value, so a caller can render a form over a strategy it has never heard of,
without importing it and without knowing what it does with the answer.  That is what keeps
the harness's promise never to inspect a strategy (7.1.3) compatible with a UI that
configures one.

Nothing here validates.  A spec states the admissible values; deciding whether a
particular mapping falls inside them is the factory's job (7.1.8), and it is the sole
authority on that question so that no rule is written twice (12.4.2.8).

Column-valued parameters carry a `source` rather than a list (7.1.7.2).  Naming the
corpus's columns in a strategy's source would put a provider-chosen column name in shipped
code, which 4.3 forbids; instead the spec says *which family of columns it wants* and
`resolve` fills the choices in from whatever the loaded dataset happens to carry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: One control apiece, except the last two.  `column` is `choice` whose options are not
#: known until a corpus is loaded, and is kept distinct so that an unresolved spec is
#: recognisable as unresolved.
#:
#: `expression_set` and `int_list` carry a **variable-length** value (7.1.7.3), so they
#: have no one-control rendering and a form draws a repeater or a list box for them.  The
#: bound belongs to the parameter rather than to any surface that renders it: a caller
#: reading only the schema still has to learn that at most four are accepted.
KINDS = ("int", "float", "bool", "choice", "column", "expression_set", "int_list")

#: The kinds whose value is a sequence rather than a scalar.
SEQUENCE_KINDS = ("expression_set", "int_list")

#: The column families of `TrainingView`, which a `column` parameter selects from.  They
#: are separate because 7.1.2.2 keeps them separate: a strategy asking to partition on a
#: feature must not be silently offered a byte count.
COLUMN_SOURCES = ("features", "size_columns")

#: What a registered strategy claims to be.  See `StrategyEntry.kind`.
STRATEGY_KINDS = ("baseline", "demonstration")


@dataclass(frozen=True)
class ParamSpec:
    """One parameter of one strategy."""

    name: str
    label: str
    kind: str
    #: A parameter with a default is optional by construction — the default is what the
    #: strategy runs with when the caller says nothing.
    required: bool = True
    default: Any = None
    description: str = ""

    #: `choice` only: the admissible values, in the order they should be offered.
    choices: tuple[Any, ...] | None = None
    #: `column` only: which family of the corpus's columns this parameter names.
    source: str | None = None
    #: `int` and `float` only.  Either end may be left open.
    minimum: float | None = None
    maximum: float | None = None

    #: `expression_set` and `int_list` only: how many entries the parameter accepts.
    #: Required of them, because an unbounded list is a promise this project's surfaces
    #: cannot keep — 12.4.5.1's row count and 12.2.4's bounded request both rest on it.
    maximum_length: int | None = None

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"unknown parameter kind {self.kind!r}; expected one of {KINDS}")
        if self.kind == "choice" and not self.choices:
            raise ValueError(f"{self.name}: a choice parameter must declare its choices")
        if self.kind == "column" and self.source not in COLUMN_SOURCES:
            raise ValueError(
                f"{self.name}: a column parameter must name a source from {COLUMN_SOURCES}"
            )
        if self.kind in SEQUENCE_KINDS and not self.maximum_length:
            raise ValueError(
                f"{self.name}: a {self.kind} parameter must declare its maximum_length"
            )
        if self.maximum_length is not None and self.kind not in SEQUENCE_KINDS:
            raise ValueError(
                f"{self.name}: maximum_length applies to {SEQUENCE_KINDS}, not {self.kind!r}"
            )

    @property
    def resolved(self) -> bool:
        """Whether this spec is ready to be rendered as a form control.

        A `column` spec is not, until a corpus has said what its columns are called.
        """
        return self.kind != "column" or self.choices is not None

    def resolve(self, columns: dict[str, list[str]]) -> "ParamSpec":
        """Fill a `column` spec's choices in from a loaded corpus (7.1.7.2).

        `columns` maps a source name to the column names the corpus carries under it.
        Every other kind is returned unchanged, so a caller resolves a whole schema
        without first asking which specs need it.
        """
        if self.kind != "column":
            return self
        available = tuple(columns.get(self.source, ()))
        default = self.default if self.default in available else None
        return ParamSpec(
            name=self.name,
            label=self.label,
            kind=self.kind,
            required=self.required,
            default=default,
            description=self.description,
            choices=available,
            source=self.source,
        )

    def describe(self) -> dict[str, Any]:
        """This spec as JSON-native data (7.1.7.1).

        Keys whose value is absent are omitted rather than emitted as null, so a form
        builder can test for a constraint's presence instead of its emptiness.
        """
        described: dict[str, Any] = {
            "name": self.name,
            "label": self.label,
            "kind": self.kind,
            "required": self.required,
        }
        if self.default is not None:
            described["default"] = self.default
        if self.description:
            described["description"] = self.description
        if self.choices is not None:
            described["choices"] = list(self.choices)
        if self.source is not None:
            described["source"] = self.source
        if self.minimum is not None:
            described["minimum"] = self.minimum
        if self.maximum is not None:
            described["maximum"] = self.maximum
        if self.maximum_length is not None:
            described["maximum_length"] = self.maximum_length
        return described


@dataclass(frozen=True)
class StrategyEntry:
    """A registered strategy and everything a caller may know about it without running it.

    `kind` is load-bearing rather than cosmetic.  A **baseline** exists to bracket what
    ordering alone is worth and must read no feature (7.1.2.3); a **demonstration** family
    may read features and is a fixture, never a result.  Presenting one as the other would
    misrepresent a number, so the distinction travels with the registration.
    """

    name: str
    call: Any
    label: str
    description: str
    kind: str
    params: tuple[ParamSpec, ...] = field(default_factory=tuple)

    #: Optional per-event routing (7.1.6).  A factory taking the capacity and the
    #: strategy's parameters and returning ``route(features) -> container_id`` — a
    #: function of one event, with no corpus in scope.  A strategy whose layout cannot be
    #: reproduced one event at a time simply declares none.
    route: Any = None

    def __post_init__(self) -> None:
        if self.kind not in STRATEGY_KINDS:
            raise ValueError(
                f"{self.name}: unknown strategy kind {self.kind!r};"
                f" expected one of {STRATEGY_KINDS}"
            )
        seen = [spec.name for spec in self.params]
        if len(set(seen)) != len(seen):
            raise ValueError(f"{self.name}: duplicate parameter name in schema")

    def resolve(self, columns: dict[str, list[str]]) -> "StrategyEntry":
        """This entry with every column-valued parameter resolved against a corpus."""
        return StrategyEntry(
            name=self.name,
            call=self.call,
            label=self.label,
            description=self.description,
            kind=self.kind,
            params=tuple(spec.resolve(columns) for spec in self.params),
            route=self.route,
        )

    def describe(self) -> dict[str, Any]:
        """This entry as JSON-native data (7.1.9) — the callable deliberately absent."""
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "kind": self.kind,
            "params": [spec.describe() for spec in self.params],
        }
