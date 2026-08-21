"""The strategy factory — the sole authority on admissibility (7.1.8).

The two properties worth most here are that it collects rather than stops, and that every
violation it reports says where it lives.  A form with four blocks of four stages is
unusable if the server answers one question per round trip.
"""

from __future__ import annotations

import pytest

from simulator.core import dataset as dataset_module
from simulator.providers import synthetic
from simulator.providers.synthetic import DatasetConfig
from simulator.strategies import (
    ExpressionChainError,
    FactoryError,
    build,
    build_all,
    build_view,
    entry,
    get,
)
from simulator.strategies.factory import _check, _check_one
from simulator.strategies.schema import ParamSpec, StrategyEntry


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    config = DatasetConfig(
        name="factory-corpus",
        n_events=3_000,
        n_transaction_days=60,
        n_query_days=16,
        half_life_days=5.0,
        seed=31,
    )
    return dataset_module.load(
        synthetic.generate(config, tmp_path_factory.mktemp("factory"))
    )


@pytest.fixture(scope="module")
def features(corpus):
    return corpus.features


def violations_of(callable_, *args, **kwargs) -> list:
    with pytest.raises(FactoryError) as raised:
        callable_(*args, **kwargs)
    return list(raised.value.violations)


# -- building -----------------------------------------------------------------------


def test_it_returns_something_runnable(corpus, features):
    """7.1.8 — a name and a mapping in, a strategy out."""
    built = build("group_by_chain", {"expressions": ["brand_id"]}, features=features)
    layout = built(build_view(corpus, 250))
    assert layout.shape == (corpus.event_count,)


def test_a_strategy_with_no_parameters_builds_from_an_empty_mapping():
    """7.1.7 — declaring nothing is a valid registration, so it must be buildable."""
    built = build("insertion_order", {})
    assert built.params == {}


def test_a_default_is_filled_in_rather_than_left_out():
    built = build("random_order", {})
    assert built.params["seed"] == entry("random_order").params[0].default


def test_the_canonical_chain_is_what_lands_in_params(features):
    """Two orderings of one chain are one configuration, so they are one `Params`.

    The metric row's identity is its configuration (12.4.2.3); if a permutation produced
    a different `Params`, one layout would appear in the table as two.
    """
    forward = build(
        "group_by_chain",
        {"expressions": ["feature_price_tier > 5", "brand_id"]},
        features=features,
    )
    reversed_ = build(
        "group_by_chain",
        {"expressions": ["brand_id", "feature_price_tier > 5"]},
        features=features,
    )
    assert forward.params == reversed_.params
    assert forward.params["expressions"] == ["brand_id", "feature_price_tier > 5"]


def test_params_stay_json_native(features):
    """They travel through CSV in a metric row, so a live object in them is a defect."""
    import json

    built = build("group_by_chain", {"expressions": ["brand_id"]}, features=features)
    assert json.loads(json.dumps(built.params)) == built.params


# -- refusing to build --------------------------------------------------------------


def test_an_unknown_strategy_is_a_violation_not_a_key_error():
    """A caller handling one error type should not also have to catch KeyError."""
    violations = violations_of(build, "no_such_family", {}, block="AS-1")
    assert len(violations) == 1
    assert "unknown strategy" in violations[0].message
    assert violations[0].block == "AS-1"


def test_an_unknown_parameter_names_itself_and_what_was_offered():
    violations = violations_of(build, "group_by_chain", {"expresions": []})
    assert violations[0].parameter == "expresions"
    assert "takes expressions" in violations[0].message


def test_a_missing_required_parameter_is_reported():
    demanding = StrategyEntry(
        name="demanding",
        call=lambda view, width: None,
        label="Demanding",
        description="",
        kind="demonstration",
        params=(ParamSpec(name="width", label="Width", kind="int", required=True),),
    )
    coerced, violations = _check(demanding, {}, None)

    assert coerced == {}
    assert violations[0].parameter == "width"
    assert "required" in violations[0].message


@pytest.mark.parametrize(
    "value,expected",
    [
        ("not a list", "a list of values"),
        (["a"] * 5, "at most 4 entries"),
    ],
)
def test_the_shape_of_a_sequence_parameter_is_checked(value, expected):
    violations = violations_of(build, "group_by_chain", {"expressions": value})
    assert expected in violations[0].message


def test_the_bound_comes_from_the_schema_not_from_the_caller():
    """7.1.7.3 — a caller reading only the schema still learns the limit."""
    spec = entry("group_by_chain").params[0]
    violations = violations_of(
        build, "group_by_chain", {"expressions": ["a"] * (spec.maximum_length + 1)}
    )
    assert f"at most {spec.maximum_length}" in violations[0].message


def test_a_bad_seed_is_rejected_by_type():
    violations = violations_of(build, "random_order", {"seed": "soon"})
    assert violations[0].parameter == "seed"
    assert "not a whole number" in violations[0].message


# -- collecting, and addressing what it collects ------------------------------------


def test_syntax_and_corpus_failures_arrive_together(features):
    """The property a two-phase implementation quietly loses.

    Stage 1 parses but names no column this corpus has; stage 2 does not parse at all.
    Checking syntax for the whole chain first would report only the second, and the
    reader would fix it, resubmit, and meet the first.
    """
    violations = violations_of(
        build,
        "group_by_chain",
        {"expressions": ["brnad_id", "feature_price_tier >> 5"]},
        features=features,
    )
    assert [v.index for v in violations] == [0, 1]
    assert "unknown column" in violations[0].message
    assert "not a value" in violations[1].message


def test_a_violation_is_addressed_by_block_parameter_and_stage(features):
    """7.1.8.1 — the triple 12.4.2.12 renders."""
    violations = violations_of(
        build,
        "group_by_chain",
        {"expressions": ["brand_id", "brnad_id"]},
        features=features,
        block="AS-3",
    )
    assert violations[0].addressed().startswith("AS-3, expressions, stage 2:")
    assert violations[0].describe() == {
        "message": violations[0].message,
        "parameter": "expressions",
        "index": 1,
        "block": "AS-3",
    }


def test_the_stage_is_not_repeated_in_the_message(features):
    """It is carried in `index`; saying it twice renders as "stage 2: stage 2: ..."."""
    violations = violations_of(
        build, "group_by_chain", {"expressions": ["brand_id", "brnad_id"]}, features=features
    )
    assert not violations[0].message.startswith("stage")


def test_building_several_reports_across_all_of_them(features):
    """12.4.2.11 — all-or-nothing, and the reader learns everything in one breath."""
    violations = violations_of(
        build_all,
        [
            {
                "name": "group_by_chain",
                "params": {"expressions": ["brnad_id"]},
                "features": features,
                "block": "AS-1",
            },
            {"name": "group_by_chain", "params": {"nope": 1}, "block": "AS-2"},
            {"name": "missing_family", "block": "AS-3"},
        ],
    )
    assert [v.block for v in violations] == ["AS-1", "AS-2", "AS-3"]


def test_nothing_is_returned_when_any_one_of_them_fails(features):
    """A partial list would be a partial report, which 13.10 refuses."""
    with pytest.raises(FactoryError):
        build_all(
            [
                {"name": "insertion_order", "block": "AS-1"},
                {"name": "group_by_chain", "params": {"expressions": ["oops"]},
                 "features": features, "block": "AS-2"},
            ]
        )


def test_all_of_them_build_when_all_of_them_are_admissible(features):
    built = build_all(
        [
            {"name": "insertion_order", "block": "baseline"},
            {
                "name": "group_by_chain",
                "params": {"expressions": ["brand_id"]},
                "features": features,
                "block": "AS-1",
            },
        ]
    )
    assert [b.block for b in built] == ["baseline", "AS-1"]


def test_a_failure_describes_itself_as_json_native_data(features):
    import json

    with pytest.raises(FactoryError) as raised:
        build("group_by_chain", {"expressions": ["brnad_id"]}, features=features)
    described = raised.value.describe()
    assert json.loads(json.dumps(described)) == described


# -- validating without a corpus ----------------------------------------------------


def test_syntax_can_be_checked_before_a_dataset_is_loaded():
    """A form is checkable while the corpus is still being read."""
    built = build("group_by_chain", {"expressions": ["no_such_column > 1"]})
    assert built.params == {"expressions": ["no_such_column > 1"]}


def test_but_a_column_is_only_checked_when_the_corpus_says_what_it_has(features):
    with pytest.raises(FactoryError, match="unknown column"):
        build("group_by_chain", {"expressions": ["no_such_column > 1"]}, features=features)


def test_the_strategy_still_refuses_at_run_time(corpus):
    """The factory is the authority, not the only guard — 7.1.3 keeps the strategy total."""
    with pytest.raises(ExpressionChainError):
        get("group_by_chain")(build_view(corpus, 250), expressions=["no_such_column"])


def test_an_int_list_parameter_checks_its_entries_and_their_positions():
    """7.1.7.3's other sequence kind, exercised on its own schema."""
    spec = ParamSpec(
        name="capacities",
        label="Capacities",
        kind="int_list",
        maximum_length=4,
        minimum=1,
    )
    value, violations = _check_one(spec, [1000, "many", 0], None)
    assert [v.index for v in violations] == [1, 2]
    assert "not a whole number" in violations[0].message
    assert "below the minimum" in violations[1].message

    _, none = _check_one(spec, [1000, 2000], None)
    assert none == []


def test_an_int_list_rejects_a_repeated_value():
    spec = ParamSpec(
        name="capacities", label="Capacities", kind="int_list", maximum_length=4, minimum=1
    )
    _, violations = _check_one(spec, [1000, 1000], None)
    assert "repeats a value" in violations[0].message


def test_an_unusable_entry_is_reported_rather_than_raised_on():
    """7.1.8 — the factory reports; it never lets untrusted input reach an exception.

    A list is not hashable, so asking whether the entries repeat before knowing they are
    sound raises `TypeError` out of the validator instead of returning a violation.
    """
    spec = ParamSpec(
        name="capacities", label="Capacities", kind="int_list", maximum_length=4, minimum=1
    )
    _, violations = _check_one(spec, [[1], 2], None)
    assert [v.index for v in violations] == [0]
    assert "not a whole number" in violations[0].message
    # And nothing complains about repeats among values that are already wrong.
    assert not any("repeats" in v.message for v in violations)
