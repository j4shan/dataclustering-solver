"""The strategy parameter schema and the registry's metadata — 7.1.7 to 7.1.9.

These assert the seam's promises, not its contents: that a registration without metadata
stays valid, that what comes out is JSON, that a column parameter takes its choices from
the corpus rather than from source, and that the two shipped baselines still say they are
baselines.
"""

from __future__ import annotations

import json

import pytest

from simulator import strategies
from simulator.strategies import ParamSpec, StrategyEntry, registry


@pytest.fixture
def scratch_registry():
    """Restore the registry afterwards, so a test's registration cannot leak into another.

    The registry is process-global by design — registration is a decorator — so a test
    that registers has to put it back.
    """
    before = dict(registry._REGISTERED_STRATEGIES)
    yield
    registry._REGISTERED_STRATEGIES.clear()
    registry._REGISTERED_STRATEGIES.update(before)


# --- ParamSpec ----------------------------------------------------------------------


def test_a_choice_parameter_must_declare_its_choices():
    with pytest.raises(ValueError):
        ParamSpec(name="mode", label="Mode", kind="choice")


def test_a_column_parameter_must_name_a_known_source():
    with pytest.raises(ValueError):
        ParamSpec(name="by", label="By", kind="column", source="whatever")


def test_an_unknown_kind_is_rejected():
    with pytest.raises(ValueError):
        ParamSpec(name="by", label="By", kind="colour")


def test_describe_omits_absent_constraints_rather_than_emitting_null():
    described = ParamSpec(name="seed", label="Seed", kind="int").describe()
    assert described == {"name": "seed", "label": "Seed", "kind": "int", "required": True}


def test_describe_carries_the_constraints_that_are_present():
    described = ParamSpec(
        name="width", label="Width", kind="float", minimum=0.0, maximum=1.0, default=0.5
    ).describe()
    assert described["minimum"] == 0.0
    assert described["maximum"] == 1.0
    assert described["default"] == 0.5


# --- column resolution, 7.1.7.2 -----------------------------------------------------


def test_a_column_parameter_is_unresolved_until_a_corpus_supplies_its_choices():
    spec = ParamSpec(name="by", label="By", kind="column", source="features")
    assert not spec.resolved
    assert spec.resolve({"features": ["a", "b"]}).resolved


def test_resolution_offers_exactly_the_columns_the_corpus_carries():
    spec = ParamSpec(name="by", label="By", kind="column", source="features")
    assert spec.resolve({"features": ["z", "a"]}).choices == ("z", "a")


def test_resolution_reads_only_the_source_the_parameter_named():
    """7.1.2.2 keeps features and byte columns apart; resolution must not merge them."""
    spec = ParamSpec(name="by", label="By", kind="column", source="features")
    resolved = spec.resolve({"features": ["a"], "size_columns": ["bytes"]})
    assert resolved.choices == ("a",)


def test_a_default_the_corpus_does_not_carry_is_dropped():
    """A default naming an absent column would fail admissibility before it was edited."""
    spec = ParamSpec(
        name="by", label="By", kind="column", source="features", default="absent"
    )
    assert spec.resolve({"features": ["present"]}).default is None


def test_resolution_leaves_every_other_kind_alone():
    spec = ParamSpec(name="seed", label="Seed", kind="int", default=7)
    assert spec.resolve({"features": ["a"]}) == spec


# --- registry metadata, 7.1.9 -------------------------------------------------------


def test_metadata_is_json_serializable_and_needs_no_strategy_imported():
    """7.1.7.1 — a caller renders a form from data, never from the strategy."""
    described = strategies.describe()
    assert json.loads(json.dumps(described)) == described


def test_every_registered_strategy_reports_the_metadata_a_selector_needs():
    for described in strategies.describe():
        assert described["name"] in strategies.available()
        assert described["label"]
        assert described["description"]
        assert described["kind"] in strategies.STRATEGY_KINDS
        assert isinstance(described["params"], list)


def test_the_shipped_strategies_are_registered_as_baselines():
    """7.1.2.3 — the two shipped strategies bracket ordering and read no feature."""
    kinds = {row["name"]: row["kind"] for row in strategies.describe()}
    assert kinds["insertion_order"] == "baseline"
    assert kinds["random_order"] == "baseline"


def test_a_description_carries_no_docstring_markup():
    for described in strategies.describe():
        assert "``" not in described["description"]


def test_get_still_returns_the_callable_the_harness_invokes():
    assert strategies.get("insertion_order") is strategies.entry("insertion_order").call


def test_an_unknown_name_raises_and_names_what_is_registered():
    with pytest.raises(KeyError, match="registered"):
        strategies.entry("no_such_strategy")


class ColumnBearingCorpus:
    """The two column families a schema resolves against, and nothing else.

    `column_choices` reads a dataset by attribute, so a stand-in carrying only what it
    reads is enough — and keeps this test independent of a generated corpus.
    """

    features = {"feature_price_tier": None, "brand_id": None}
    size_columns = {"payload_bytes": None}


def test_describing_against_a_corpus_fills_in_that_corpus_column_names(scratch_registry):
    """7.1.7.2 — the choices come from the loaded dataset, never from the source."""

    @strategies.register(
        "test_group_by",
        params=[ParamSpec(name="by", label="Group by", kind="column", source="features")],
    )
    def group_by(view, **_):
        """A family whose one parameter names a column."""

    described = {row["name"]: row for row in strategies.describe(ColumnBearingCorpus())}
    assert described["test_group_by"]["params"][0]["choices"] == [
        "brand_id",
        "feature_price_tier",
    ]


def test_describing_without_a_corpus_leaves_a_column_parameter_unresolved(scratch_registry):
    """Before a corpus is loaded there is no honest answer, so none is invented."""

    @strategies.register(
        "test_group_by",
        params=[ParamSpec(name="by", label="Group by", kind="column", source="features")],
    )
    def group_by(view, **_):
        """A family whose one parameter names a column."""

    described = {row["name"]: row for row in strategies.describe()}
    assert "choices" not in described["test_group_by"]["params"][0]


def test_column_choices_keeps_the_two_families_apart():
    """7.1.2.2 — a feature parameter must never be offered a byte column."""
    choices = strategies.column_choices(ColumnBearingCorpus())
    assert set(choices) == set(strategies.COLUMN_SOURCES)
    assert not set(choices["features"]) & set(choices["size_columns"])


# --- StrategyEntry ------------------------------------------------------------------


def test_registration_without_metadata_stays_valid_and_takes_no_parameters(scratch_registry):
    """7.1.7 — the schema is additive; declaring nothing is a complete registration."""

    @strategies.register("test_bare_registration")
    def bare(view, **_):
        """A strategy that declares nothing at all."""

    described = strategies.entry("test_bare_registration").describe()
    assert described["params"] == []
    assert described["label"] == "Test Bare Registration"
    assert described["description"] == "A strategy that declares nothing at all."


def test_an_unlabelled_registration_is_never_taken_for_a_baseline(scratch_registry):
    """`baseline` is a claim the registry cannot check, so it is never assumed."""

    @strategies.register("test_unlabelled_kind")
    def unlabelled(view, **_):
        """No kind declared."""

    assert strategies.entry("test_unlabelled_kind").kind == "demonstration"


def test_an_entry_rejects_an_unknown_kind():
    with pytest.raises(ValueError):
        StrategyEntry(name="x", call=None, label="X", description="", kind="prototype")


def test_an_entry_rejects_two_parameters_sharing_a_name():
    duplicate = ParamSpec(name="seed", label="Seed", kind="int")
    with pytest.raises(ValueError):
        StrategyEntry(
            name="x",
            call=None,
            label="X",
            description="",
            kind="demonstration",
            params=(duplicate, duplicate),
        )


def test_the_describe_payload_never_carries_the_callable():
    entry = strategies.entry("insertion_order")
    assert "call" not in entry.describe()
