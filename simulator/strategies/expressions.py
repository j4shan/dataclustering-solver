"""The group-by expression grammar (12.4.1.2).

An Assignment Strategy splits the corpus by expressions a *reader typed into a browser*,
which makes this module the project's only untrusted-input boundary.  It is closed by
construction:

    expression := column
                | column operator operand

    operator   := ==  !=  <  <=  >  >=  in  not in  +  -  *  /  %
    operand    := number | string | [ literal, ... ]

There is exactly one column reference, it is always on the left, and the right-hand side
is always a literal.  There is no nesting, no function call, no second column, and no
name that resolves to anything but a column of the loaded corpus.  Nothing here calls
`eval`, `exec`, or `ast.literal_eval`: the tokenizer below is the whole language, so what
the grammar cannot express cannot be smuggled through it.

**An expression produces a group key per event, not a filter.**  A comparison keys events
by a boolean, splitting two ways; a bare column keys them by its value, splitting as many
ways as the column has values; arithmetic keys them by the bucket the operation lands in.
That is why `/` is *floor* division — `price / 10` means "group into tens", and a group-by
key has to be discrete to group anything.

Errors carry the character offset of what went wrong, so a caller assembling several
expressions can say which one and where (7.1.8.1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from ..core.contract import NUMERIC, TEMPORAL, TEXT, dtype_family

#: Longest first, so `>=` never tokenizes as `>` and `not in` never as a bare column.
OPERATORS = ("not in", "in", ">=", "<=", "==", "!=", ">", "<", "+", "-", "*", "/", "%")

COMPARISONS = frozenset({"==", "!=", "<", "<=", ">", ">="})
MEMBERSHIPS = frozenset({"in", "not in"})
ARITHMETIC = frozenset({"+", "-", "*", "/", "%"})

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_OPERATOR = re.compile("|".join(re.escape(symbol) for symbol in OPERATORS))


#: 12.6.5.2 — the grammar is a column reference, one operator and a literal, so a valid
#: expression is short.  The bound is on the seam rather than on the parser's appetite.
MAX_EXPRESSION_CHARS = 200


class ExpressionError(ValueError):
    """A group-by expression that will not parse, or will not fit its corpus.

    Carries where the trouble is as well as what it is.  A reader looking at four blocks
    of four stages needs the position; a message alone sends them hunting.
    """

    def __init__(
        self,
        message: str,
        *,
        text: str = "",
        position: int | None = None,
        stage: int | None = None,
    ):
        self.message = message
        self.text = text
        self.position = position
        #: Which stage of a chain this came from, once a chain has said (7.1.8.1).
        self.stage = stage
        super().__init__(self.rendered())

    def rendered(self) -> str:
        if self.position is None:
            return f"{self.message} in {self.text!r}" if self.text else self.message
        return f"{self.message} at character {self.position} of {self.text!r}"

    def describe(self) -> dict[str, Any]:
        """This failure as JSON-native data, for a caller reporting it in a form."""
        described: dict[str, Any] = {"message": self.message, "expression": self.text}
        if self.position is not None:
            described["position"] = self.position
        if self.stage is not None:
            described["stage"] = self.stage
        return described


@dataclass(frozen=True)
class Expression:
    """One group-by stage: a column, optionally transformed by one operator.

    Immutable and JSON-native — `describe` round-trips through `from_data`, which is what
    lets a chain travel in a metric row's `Params` and come back the same expression.
    """

    column: str
    operator: str | None = None
    operand: Any = None
    #: The text this was parsed from, kept only so an error can quote it back.
    text: str = ""

    # -- parsing ---------------------------------------------------------------

    @classmethod
    def parse(cls, text: str) -> "Expression":
        """Read one expression. Syntax only — `validate` is what checks it against a corpus."""
        source = text.strip()
        if not source:
            raise ExpressionError("an expression cannot be empty", text=text)
        if len(source) > MAX_EXPRESSION_CHARS:
            # Reported without quoting the offender: the message travels to the page, and
            # a refusal that echoes an over-long string back is the amplification the
            # bound exists to stop (12.6.5.2).
            raise ExpressionError(
                f"an expression is at most {MAX_EXPRESSION_CHARS} characters",
                text=source[:MAX_EXPRESSION_CHARS],
            )

        column_match = _IDENTIFIER.match(source)
        if not column_match or column_match.start() != 0:
            raise ExpressionError(
                "an expression must begin with a column name", text=source, position=0
            )
        column = column_match.group()
        cursor = _skip_space(source, column_match.end())

        if cursor == len(source):
            return cls(column=column, text=source)

        operator_match = _OPERATOR.match(source, cursor)
        if not operator_match:
            raise ExpressionError(
                f"expected an operator, one of {' '.join(OPERATORS)}",
                text=source,
                position=cursor,
            )
        operator = operator_match.group()
        cursor = _skip_space(source, operator_match.end())

        operand, cursor = _parse_operand(source, cursor, operator)
        cursor = _skip_space(source, cursor)
        if cursor != len(source):
            raise ExpressionError(
                "unexpected trailing text — an expression holds one operator",
                text=source,
                position=cursor,
            )
        return cls(column=column, operator=operator, operand=operand, text=source)

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> "Expression":
        """Rebuild an expression from `describe` output."""
        operand = data.get("operand")
        return cls(
            column=data["column"],
            operator=data.get("operator"),
            operand=tuple(operand) if isinstance(operand, list) else operand,
            text=data.get("text", ""),
        )

    def describe(self) -> dict[str, Any]:
        """JSON-native data (7.1.7.1) — no numpy, no tuple, no dataclass."""
        described: dict[str, Any] = {"column": self.column}
        if self.operator is not None:
            described["operator"] = self.operator
            described["operand"] = (
                list(self.operand) if isinstance(self.operand, tuple) else self.operand
            )
        return described

    def __str__(self) -> str:
        if self.text:
            return self.text
        if self.operator is None:
            return self.column
        return f"{self.column} {self.operator} {_render_operand(self.operand)}"

    # -- checking --------------------------------------------------------------

    def validate(self, columns: Mapping[str, np.ndarray]) -> None:
        """Check this expression against the corpus it will run on.

        Raises on the first problem *with this expression*; a caller holding several
        collects one error per expression rather than one per chain (7.1.8).
        """
        if self.column not in columns:
            offered = ", ".join(sorted(columns)) or "none"
            raise ExpressionError(
                f"unknown column {self.column!r}; this dataset offers {offered}",
                text=str(self),
                position=0,
            )
        if self.operator is None:
            return

        family = dtype_family(columns[self.column].dtype)
        allowed = _ALLOWED_OPERATORS[family]
        if self.operator not in allowed:
            raise ExpressionError(
                f"{self.operator!r} does not apply to the {family} column"
                f" {self.column!r}; it accepts {' '.join(sorted(allowed))}",
                text=str(self),
            )

        operands = self.operand if self.operator in MEMBERSHIPS else (self.operand,)
        if self.operator in MEMBERSHIPS and not operands:
            raise ExpressionError(
                f"{self.operator!r} needs at least one value to test against",
                text=str(self),
            )
        for value in operands:
            if not _fits(value, family):
                raise ExpressionError(
                    f"{value!r} is not a {family} value, and {self.column!r} is a"
                    f" {family} column",
                    text=str(self),
                )
            # A temporal column wants a *date*, and `_fits` can only see that a string
            # arrived.  The lift that `group_keys` will perform is the only thing that
            # knows whether it parses, so it is performed here too — the same call, not
            # a second implementation of date syntax.  Without this the failure
            # lands in the hot path and reaches the reader as an unaddressed 500,
            # against 12.4.1.2's promise that it is rejected before anything runs.
            if family == TEMPORAL:
                try:
                    _as_comparable(value, columns[self.column].dtype)
                except ValueError:
                    raise ExpressionError(
                        f"{value!r} is not a date {self.column!r} can hold;"
                        " write one the way the column does, as in \"2023-01-05\"",
                        text=str(self),
                    ) from None
        if self.operator in ("/", "%") and self.operand == 0:
            raise ExpressionError(
                f"{self.operator!r} by zero", text=str(self)
            )

    # -- running ---------------------------------------------------------------

    def group_keys(self, columns: Mapping[str, np.ndarray]) -> np.ndarray:
        """The group key this expression assigns to every event.

        `validate` must have passed against the same columns; this is the hot path and
        does not re-check.  Interpretation is a dispatch over a fixed operator set —
        never a host-language evaluation of the reader's text.
        """
        values = columns[self.column]
        if self.operator is None:
            return values
        if self.operator in MEMBERSHIPS:
            member = np.isin(values, _as_comparable(self.operand, values.dtype))
            return member if self.operator == "in" else ~member
        operand = _as_comparable(self.operand, values.dtype)
        if self.operator in COMPARISONS:
            return _COMPARE[self.operator](values, operand)
        if self.operator == "/":
            # Floor, not true division: a group-by key has to be discrete, and
            # `price / 10` means "in tens".
            return values // operand
        return _ARITHMETIC[self.operator](values, operand)


def compile_chain(
    texts: Sequence[str], columns: Mapping[str, np.ndarray] | None = None
) -> tuple[Expression, ...]:
    """Parse and check a whole chain in **one pass**, collecting every failure.

    One pass rather than two phases on purpose.  Parsing every stage first and only then
    checking the survivors against the corpus would report a typo'd operator on stage 2
    while staying silent about a misspelled column on stage 1 — and the reader would fix
    one, resubmit, and meet the other.  A stage that fails to parse cannot also be
    checked against a corpus, but every *other* stage still can, so all of it is reported
    together (7.1.8).

    With no `columns`, only syntax is checked, which is what lets a caller hold a chain
    before a dataset has finished loading.

    The chain is a *set*: order does not reach the layout (12.4.1.3), so nothing here
    preserves an order that would only mislead.  Duplicates are rejected — a repeated
    expression splits nothing a second time and is a typo, not a refinement.
    """
    compiled: list[tuple[int, Expression]] = []
    failures: list[ExpressionError] = []

    for index, text in enumerate(texts):
        try:
            expression = Expression.parse(text)
            if columns is not None:
                expression.validate(columns)
        except ExpressionError as failure:
            failures.append(_at_stage(failure, index))
            continue
        compiled.append((index, expression))

    seen: dict[tuple, int] = {}
    for index, expression in compiled:
        key = (expression.column, expression.operator, expression.operand)
        if key in seen:
            failures.append(
                _at_stage(
                    ExpressionError(
                        f"duplicate of stage {seen[key] + 1}; splitting by the same"
                        " expression twice partitions nothing further",
                        text=str(expression),
                    ),
                    index,
                )
            )
        else:
            seen[key] = index

    if failures:
        raise ExpressionChainError(sorted(failures, key=lambda f: f.stage or 0))
    return tuple(expression for _, expression in compiled)


def parse_chain(texts: Sequence[str]) -> tuple[Expression, ...]:
    """Check a chain's syntax alone, with no corpus to check it against."""
    return compile_chain(texts)


def validate_chain(
    expressions: Sequence[Expression], columns: Mapping[str, np.ndarray]
) -> None:
    """Check an already-parsed chain against a corpus, one error per offending stage."""
    failures = []
    for index, expression in enumerate(expressions):
        try:
            expression.validate(columns)
        except ExpressionError as failure:
            failures.append(_at_stage(failure, index))
    if failures:
        raise ExpressionChainError(failures)


class ExpressionChainError(ExpressionError):
    """Every stage of one chain that failed, reported together rather than one at a time.

    A reader fixing a four-stage chain should learn about all four problems in one round
    trip, which is 7.1.8's rule applied one level down.
    """

    def __init__(self, failures: Sequence[ExpressionError]):
        self.failures = tuple(failures)
        super().__init__("; ".join(failure.rendered() for failure in self.failures))

    def describe(self) -> dict[str, Any]:
        return {"failures": [failure.describe() for failure in self.failures]}


def _at_stage(failure: ExpressionError, index: int) -> ExpressionError:
    """Re-address a failure to the chain position that produced it (7.1.8.1)."""
    return ExpressionError(
        f"stage {index + 1}: {failure.message}",
        text=failure.text,
        position=failure.position,
        stage=index,
    )


# -- the tokenizer ------------------------------------------------------------------


def _skip_space(source: str, cursor: int) -> int:
    while cursor < len(source) and source[cursor].isspace():
        cursor += 1
    return cursor


def _parse_operand(source: str, cursor: int, operator: str) -> tuple[Any, int]:
    if cursor >= len(source):
        raise ExpressionError(
            f"{operator!r} needs a value on its right", text=source, position=len(source)
        )
    if source[cursor] == "[":
        return _parse_list(source, cursor)
    if operator in MEMBERSHIPS:
        raise ExpressionError(
            f"{operator!r} takes a bracketed list, as in `in [1, 2, 3]`",
            text=source,
            position=cursor,
        )
    return _parse_literal(source, cursor)


def _parse_list(source: str, cursor: int) -> tuple[tuple, int]:
    cursor = _skip_space(source, cursor + 1)
    values: list[Any] = []
    while True:
        if cursor >= len(source):
            raise ExpressionError("unclosed `[`", text=source, position=len(source))
        if source[cursor] == "]":
            return tuple(values), cursor + 1
        value, cursor = _parse_literal(source, cursor)
        values.append(value)
        cursor = _skip_space(source, cursor)
        if cursor < len(source) and source[cursor] == ",":
            cursor = _skip_space(source, cursor + 1)
        elif cursor < len(source) and source[cursor] != "]":
            raise ExpressionError(
                "expected `,` or `]` between list values", text=source, position=cursor
            )


def _parse_literal(source: str, cursor: int) -> tuple[Any, int]:
    """A number, or a quoted string. Nothing else is a literal in this language."""
    character = source[cursor]
    if character in "'\"":
        end = source.find(character, cursor + 1)
        if end == -1:
            raise ExpressionError("unclosed quote", text=source, position=cursor)
        return source[cursor + 1 : end], end + 1
    number = _NUMBER.match(source, cursor)
    if number:
        raw = number.group()
        return (float(raw) if "." in raw else int(raw)), number.end()
    raise ExpressionError(
        "expected a number or a quoted string — a bare word is not a value,"
        " and there is no second column reference in this grammar",
        text=source,
        position=cursor,
    )


def _render_operand(operand: Any) -> str:
    if isinstance(operand, tuple):
        return "[" + ", ".join(_render_operand(value) for value in operand) + "]"
    return f'"{operand}"' if isinstance(operand, str) else str(operand)


# -- the type system ----------------------------------------------------------------
#
# The families themselves are the contract's (4.12), not the grammar's: what a column
# holds is a property of the corpus, and this module only decides which operators that
# makes sense of.

_ALLOWED_OPERATORS = {
    NUMERIC: COMPARISONS | MEMBERSHIPS | ARITHMETIC,
    # Ordering text is defined but means nothing as a split, and arithmetic on it means
    # nothing at all.  Equality and membership are the operations that carry intent.
    TEXT: frozenset({"==", "!="}) | MEMBERSHIPS,
    TEMPORAL: COMPARISONS | MEMBERSHIPS,
}


def _fits(value: Any, family: str) -> bool:
    if family == NUMERIC:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    # A date arrives quoted, because an unquoted `2023-01-05` is three numbers and a
    # subtraction.  Both text and temporal columns therefore want a string here.
    return isinstance(value, str)


def _as_comparable(operand: Any, dtype: np.dtype):
    """Lift a parsed literal into something numpy can compare against `dtype`."""
    if isinstance(operand, tuple):
        return np.array([_as_comparable(value, dtype) for value in operand])
    if np.issubdtype(dtype, np.datetime64):
        return np.datetime64(operand)
    return operand


_COMPARE = {
    "==": np.equal,
    "!=": np.not_equal,
    "<": np.less,
    "<=": np.less_equal,
    ">": np.greater,
    ">=": np.greater_equal,
}

_ARITHMETIC = {"+": np.add, "-": np.subtract, "*": np.multiply, "%": np.mod}
