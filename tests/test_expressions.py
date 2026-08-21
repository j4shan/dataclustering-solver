"""The group-by expression grammar (12.4.1.2).

This is the only place the project accepts text a reader typed, so the tests that matter
most are the ones asserting what the grammar *cannot* express.  A grammar is closed only
if the things outside it are rejected, and each rejection here is a thing that would be
an arbitrary-code path in a language built on `eval`.
"""

from __future__ import annotations

import numpy as np
import pytest

from simulator.strategies.expressions import (
    Expression,
    ExpressionChainError,
    ExpressionError,
    parse_chain,
    validate_chain,
)


@pytest.fixture
def columns():
    return {
        "price_tier": np.array([1, 5, 9, 12, 5], dtype=np.int64),
        "brand_id": np.array(["a", "b", "c", "a", "b"], dtype=object),
        "sold_on": np.array(
            ["2023-01-01", "2023-06-01", "2024-01-01", "2023-01-01", "2024-06-01"],
            dtype="datetime64[D]",
        ),
    }


# -- what the grammar accepts -------------------------------------------------------


@pytest.mark.parametrize(
    "text,column,operator,operand",
    [
        ("brand_id", "brand_id", None, None),
        ("price_tier > 5", "price_tier", ">", 5),
        ("price_tier>5", "price_tier", ">", 5),
        ("  price_tier   >=   5  ", "price_tier", ">=", 5),
        ("price_tier / 10", "price_tier", "/", 10),
        ("price_tier != -3", "price_tier", "!=", -3),
        ("price_tier < 2.5", "price_tier", "<", 2.5),
        ('brand_id == "a"', "brand_id", "==", "a"),
        ("brand_id == 'a'", "brand_id", "==", "a"),
        ("brand_id in ['a', 'b']", "brand_id", "in", ("a", "b")),
        ("price_tier not in [1, 2, 3]", "price_tier", "not in", (1, 2, 3)),
        ('sold_on >= "2023-06-01"', "sold_on", ">=", "2023-06-01"),
    ],
)
def test_the_grammar_parses_what_it_promises(text, column, operator, operand):
    parsed = Expression.parse(text)
    assert (parsed.column, parsed.operator, parsed.operand) == (column, operator, operand)


def test_an_expression_round_trips_through_json_native_data(columns):
    """12.4.1.2 — parsed to serializable data, so a chain travels in a metric row."""
    original = Expression.parse("price_tier not in [1, 2, 3]")
    described = original.describe()

    assert described == {
        "column": "price_tier",
        "operator": "not in",
        "operand": [1, 2, 3],
    }
    rebuilt = Expression.from_data(described)
    assert rebuilt.column == original.column
    assert rebuilt.operator == original.operator
    assert rebuilt.operand == original.operand
    assert np.array_equal(rebuilt.group_keys(columns), original.group_keys(columns))


# -- what the grammar refuses -------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "__import__('os').system('ls')",
        "price_tier.__class__",
        "price_tier + price_tier",  # no second column reference
        "len(price_tier)",
        "price_tier > (1 + 2)",
        "price_tier > 5 and brand_id == 'a'",  # no conjunction
        "price_tier > 5 > 2",  # one operator only
        "lambda x: x",
        "price_tier > None",
        "price_tier > True",
        "",
        "   ",
        "5 > price_tier",  # the column is always on the left
        "price_tier >",
        "price_tier > ",
        "> 5",
        "price_tier in 1, 2",  # membership takes a bracketed list
        "price_tier in [1, 2",
        "brand_id == 'a",
        "price_tier ** 2",
    ],
)
def test_the_grammar_refuses_everything_outside_it(text):
    with pytest.raises(ExpressionError):
        Expression.parse(text)


def test_a_bare_word_is_never_a_value():
    """The one rule that keeps a second name from resolving to anything."""
    with pytest.raises(ExpressionError, match="bare word is not a value"):
        Expression.parse("brand_id == a")


def test_a_parse_failure_says_where_it_is():
    error = None
    try:
        Expression.parse("price_tier ?? 5")
    except ExpressionError as raised:
        error = raised
    assert error is not None
    assert error.position == len("price_tier ")
    assert "character 11" in error.rendered()


# -- checking against a corpus ------------------------------------------------------


def test_an_unknown_column_is_rejected_and_the_real_ones_are_offered(columns):
    with pytest.raises(ExpressionError, match="unknown column 'brnad_id'") as raised:
        Expression.parse("brnad_id == 'a'").validate(columns)
    assert "brand_id" in raised.value.message


@pytest.mark.parametrize(
    "text,expected",
    [
        ("price_tier > 'a'", "not a numeric value"),
        ("brand_id > 'a'", "does not apply to the text column"),
        ("brand_id + 1", "does not apply to the text column"),
        ("brand_id == 1", "not a text value"),
        ("sold_on + 1", "does not apply to the temporal column"),
        ("price_tier / 0", "'/' by zero"),
        ("price_tier in []", "at least one value"),
        ("brand_id in ['a', 2]", "not a text value"),
        # A temporal column takes a quoted string, so "is it a string" is not the whole
        # question — 12.4.1.2 asks whether the column can *hold* the literal, and the
        # only thing that knows is the lift the run itself would perform.
        ('sold_on > "not-a-date"', "is not a date"),
        ('sold_on >= "2023-13-45"', "is not a date"),
        ('sold_on in ["2023-01-05", "nonsense"]', "is not a date"),
    ],
)
def test_a_value_that_does_not_fit_its_column_is_rejected(columns, text, expected):
    with pytest.raises(ExpressionError, match=expected):
        Expression.parse(text).validate(columns)


@pytest.mark.parametrize("text", ['sold_on > "2023-01-05"', 'sold_on in ["2023-01-05"]'])
def test_a_date_the_column_can_hold_is_admissible(columns, text):
    """The other half of the rule above: a real date is not rejected by it."""
    expression = Expression.parse(text)
    expression.validate(columns)
    assert expression.group_keys(columns).shape == columns["sold_on"].shape


def test_validation_is_the_only_thing_that_reads_the_corpus():
    """Parsing is corpus-free, so a chain can be held before a dataset is loaded."""
    parsed = Expression.parse("no_such_column > 5")
    assert parsed.column == "no_such_column"
    with pytest.raises(ExpressionError):
        parsed.validate({})


# -- group keys ---------------------------------------------------------------------


def test_a_comparison_keys_events_two_ways(columns):
    keys = Expression.parse("price_tier > 5").group_keys(columns)
    assert keys.tolist() == [False, False, True, True, False]


def test_a_bare_column_keys_events_by_its_own_value(columns):
    keys = Expression.parse("brand_id").group_keys(columns)
    assert keys.tolist() == ["a", "b", "c", "a", "b"]


def test_membership_keys_events_two_ways(columns):
    assert Expression.parse("brand_id in ['a', 'c']").group_keys(columns).tolist() == [
        True,
        False,
        True,
        True,
        False,
    ]
    assert Expression.parse("brand_id not in ['a', 'c']").group_keys(columns).tolist() == [
        False,
        True,
        False,
        False,
        True,
    ]


def test_division_buckets_rather_than_dividing(columns):
    """`price / 10` means "group into tens" — a group key has to be discrete."""
    keys = Expression.parse("price_tier / 10").group_keys(columns)
    assert keys.tolist() == [0, 0, 0, 1, 0]
    assert np.issubdtype(keys.dtype, np.integer)


def test_a_date_comparison_reads_a_quoted_literal(columns):
    keys = Expression.parse('sold_on >= "2024-01-01"').group_keys(columns)
    assert keys.tolist() == [False, False, True, False, True]


# -- chains -------------------------------------------------------------------------


def test_a_chain_reports_every_bad_stage_at_once():
    """7.1.8 applied one level down — four problems, one round trip."""
    with pytest.raises(ExpressionChainError) as raised:
        parse_chain(["price_tier > 5", "bad ?? 1", "also bad ??"])
    failures = raised.value.failures
    assert len(failures) == 2
    assert [failure.stage for failure in failures] == [1, 2]
    assert failures[0].message.startswith("stage 2:")


def test_a_chain_reports_every_unknown_column_at_once(columns):
    with pytest.raises(ExpressionChainError) as raised:
        validate_chain(parse_chain(["nope > 1", "price_tier > 5", "nor_this"]), columns)
    assert [failure.stage for failure in raised.value.failures] == [0, 2]


def test_a_repeated_expression_is_rejected():
    """Splitting by the same expression twice partitions nothing further."""
    with pytest.raises(ExpressionChainError, match="duplicate of stage 1"):
        parse_chain(["price_tier > 5", "price_tier > 5"])


def test_a_chain_failure_describes_itself_as_json_native_data():
    with pytest.raises(ExpressionChainError) as raised:
        parse_chain(["price_tier > 5", "?? nope"])
    described = raised.value.describe()
    assert list(described) == ["failures"]
    assert described["failures"][0]["stage"] == 1
    assert "message" in described["failures"][0]


def test_an_empty_chain_is_valid(columns):
    """The zero-length chain is the baseline's degenerate case (12.4.1.5)."""
    assert parse_chain([]) == ()
    validate_chain((), columns)
