"""The catalog generator and the document it emits (8.11).

The document is what Section B is drawn from, and the serving process never checks it —
12.2.5 leaves the server nothing but shaping, and 10.3.1 takes away the libraries it would
need to check anything. So what guards the document is here.

Three kinds of check, and the split is deliberate.

**Structure is anchored, not recomputed.** The split counts below are derivable from the
fixture's own column definitions without running the family (10.1.4): a column of two
values splits a corpus two ways. A test that factorized the columns itself to predict them
would be a second implementation of the split.

**Schema identity is asserted against the real primitive.** 8.10 promises a catalogued row
carries the same schema as a swept one, and the only honest way to check that is to run
`run_one` and compare key sets — which is what happens below, on the same tiny corpus.

**The shipped definition is checked as data.** That every entry builds, that ids are
unique, that the chains differ in shape — these are properties of `DEFINITION` itself.
Its *order* is not among them: granularity is a fact about a chain and a corpus together,
so the ordering check is made against a built document instead.
"""

from __future__ import annotations

import pytest

from simulator.bench import catalog


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    """A small corpus, generated once — the same shape the view tests use."""
    from simulator.core import dataset as dataset_module
    from simulator.providers import synthetic
    from simulator.providers.synthetic import DatasetConfig

    root = tmp_path_factory.mktemp("catalog")
    return dataset_module.load(
        synthetic.generate(
            DatasetConfig(
                name="catalog-corpus",
                n_events=2_000,
                n_transaction_days=60,
                n_query_days=12,
                half_life_days=5.0,
                seed=90,
            ),
            root,
        )
    )


@pytest.fixture(scope="module")
def built(corpus, tmp_path_factory):
    """One catalog document over two entries and two capacities."""
    from simulator.bench import metrics

    definition = (
        catalog.Entry("one", "One stage", ("brand_id",)),
        catalog.Entry("two", "Two stages", ("brand_id", "feature_price_tier > 5")),
    )
    original = metrics.DEFAULT_DIR
    metrics.DEFAULT_DIR = tmp_path_factory.mktemp("catalog-metrics")
    try:
        return catalog.build(corpus, definition=definition, capacities=(500, 1000))
    finally:
        metrics.DEFAULT_DIR = original


# -- the document (8.11.1) ------------------------------------------------------------


def test_the_document_names_the_corpus_every_figure_came_from(built, corpus):
    """8.11.1 and 12.4.3.3 — a figure is never detached from the corpus that produced it."""
    assert built["corpus"]["dataset_id"] == corpus.dataset_id
    assert built["corpus"]["event_count"] == corpus.event_count
    assert built["corpus"]["query_count"] == corpus.query_count


def test_the_document_carries_the_columns_so_the_gui_need_not_load_the_corpus(built):
    """12.2.3 and 12.4.2.3 — the panel lists columns without a corpus in the process."""
    columns = built["corpus"]["feature_columns"]
    assert columns, "the manifest's column summary must travel with the document (4.12)"
    assert {"name", "family"} <= set(columns[0])


def test_every_row_shares_the_batch_that_built_them(built):
    """8.3.1 — one build is one request, and its rows say so."""
    assert {row["Batch_ID"] for row in built["rows"]} == {built["batch_id"]}


def test_a_row_carries_exactly_what_a_swept_row_carries(built, corpus):
    """8.10 — a catalogued row and a swept row are the same schema, not similar ones.

    Checked against the real primitive rather than against a list of field names copied
    into this file, which would go stale the moment a KPI was added.
    """
    from simulator.bench.runner import run_one

    swept = run_one(corpus, "insertion_order", 500)[0]
    catalogued = next(
        row for row in built["rows"] if row["Strategy_Name"] == "insertion_order"
    )
    # The two fields the catalog adds on top of the primitive's own schema.
    assert set(catalogued) - set(swept) == {"Block", "baseline_lift"}
    assert set(swept) - set(catalogued) == set()


def test_the_baseline_is_present_at_every_capacity_and_is_not_an_entry(built):
    """12.4.6.5 — the reference the catalogue is read against, not one of its members."""
    baseline = [r for r in built["rows"] if r["Strategy_Name"] == "insertion_order"]
    assert {row["target_container_rows"] for row in baseline} == {500, 1000}
    assert {row["Block"] for row in baseline} == {None}
    assert "insertion_order" not in {e["id"] for e in built["strategies"]}


def test_every_candidate_row_names_the_entry_that_asked_for_it(built):
    """12.4.3.5 — a row is joined on the entry's id, never on its label."""
    ids = {entry["id"] for entry in built["strategies"]}
    candidates = [r for r in built["rows"] if r["Strategy_Name"] != "insertion_order"]
    assert {row["Block"] for row in candidates} == ids


def test_each_entry_is_swept_across_every_capacity_on_both_sets(built):
    """12.4.3.2 — training and validation are reported as a pair, never one alone."""
    for entry in built["strategies"]:
        rows = [r for r in built["rows"] if r["Block"] == entry["id"]]
        assert {r["target_container_rows"] for r in rows} == {500, 1000}
        assert {"training", "validation"} <= {r["Set_Name"] for r in rows}


def test_baseline_lift_is_taken_at_the_same_capacity(built):
    """12.4.5.4 — never a nearest or interpolated reference."""
    for row in built["rows"]:
        if row["Strategy_Name"] != "insertion_order":
            continue
        # The baseline against itself, at its own capacity, is exactly 1.
        assert row["baseline_lift"] == pytest.approx(1.0)


# -- the structure the panel lists (8.11.2) -------------------------------------------


def test_an_entry_carries_its_chain_its_stages_and_its_leaf_count(built):
    """12.4.2.1 — what the catalogue list is drawn from."""
    entry = next(e for e in built["strategies"] if e["id"] == "two")
    assert entry["label"] == "Two stages"
    assert entry["expressions"] == ["brand_id", "feature_price_tier > 5"]
    assert [stage["expression"] for stage in entry["stages"]] == entry["expressions"]


def test_the_leaf_count_is_the_last_prefixs_split_count(built):
    """8.11.2 — the whole chain is its own last prefix, so the two cannot disagree."""
    for entry in built["strategies"]:
        assert entry["leaf_count"] == entry["stages"][-1]["splits"]


def test_splits_are_cumulative_and_never_shrink_along_the_chain(built):
    """8.11.2 — every stage regroups every split the last one produced.

    An invariant rather than a value: refining a partition cannot merge two groups, so the
    counts are non-decreasing for any chain over any corpus (10.1.4).
    """
    for entry in built["strategies"]:
        counts = [stage["splits"] for stage in entry["stages"]]
        assert counts == sorted(counts)


def test_a_boolean_stage_splits_the_corpus_exactly_two_ways(built):
    """8.11.2 — anchored on the grammar, not on the corpus.

    `feature_price_tier > 5` is a comparison, and a comparison keys events by a boolean,
    so the corpus after `brand_id · price_tier > 5` stands in at most twice the groups it
    stood in after `brand_id` alone. Derivable without running the family (10.1.4).
    """
    entry = next(e for e in built["strategies"] if e["id"] == "two")
    after_brand, after_both = (stage["splits"] for stage in entry["stages"])
    assert after_brand < after_both <= after_brand * 2


def test_the_structure_carries_no_capacity(built):
    """12.4.4.4 — a chain has one shape across its whole sweep."""
    for entry in built["strategies"]:
        for stage in entry["stages"]:
            assert set(stage) == {"expression", "splits"}


# -- the shipped definition (8.11.3) --------------------------------------------------


def test_every_shipped_entry_has_a_unique_id():
    """12.4.3.5 — the id is what a row is joined on, so a collision merges two series."""
    ids = [entry.id for entry in catalog.DEFINITION]
    assert len(ids) == len(set(ids))


def test_the_shipped_catalogue_spans_a_structural_range():
    """8.11.3 — entries differ in shape, not in tuning.

    Chains of one, two and three stages, and no two entries the same chain: a catalogue of
    six variations on one chain would fill the list without widening what it shows.
    """
    chains = [entry.expressions for entry in catalog.DEFINITION]
    assert len(set(chains)) == len(chains)
    assert {len(chain) for chain in chains} >= {1, 2, 3}


def test_the_shipped_catalogue_reaches_every_column_family(corpus):
    """8.11.3 — text, numeric and temporal columns are all represented.

    A catalogue that only ever split on text would leave the reader unable to see that the
    column's *kind* is part of what a layout is trading on.
    """
    families = {column["name"]: column["family"] for column in corpus.feature_summary}
    reached = {
        families[name]
        for entry in catalog.DEFINITION
        for text in entry.expressions
        for name in [text.split()[0]]
        if name in families
    }
    assert {"text", "numeric", "temporal"} <= reached


def test_the_document_is_ordered_by_granularity_and_not_by_score(built):
    """8.11.3 — the order is structural, so the list is not read as a ranking.

    Ordered by leaf count, which is how finely the chain cut *this* corpus. It is not a
    score: a finer split skips more and costs more metadata, so neither end of the order
    is the good end. The check is on the document rather than on `DEFINITION`, because
    granularity is a fact about a chain *and a corpus* — the same chain over dates is
    coarse on a two-month corpus and the finest thing here on a three-year one.
    """
    leaves = [entry["leaf_count"] for entry in built["strategies"]]
    assert leaves == sorted(leaves)


def test_the_order_does_not_follow_the_held_out_waste(built):
    """8.11.3 — and the order is demonstrably *not* the ranking a reader might infer.

    If granularity happened to reproduce the score order, the distinction this project
    draws between the two would be untestable here. On this corpus it does not, which is
    what makes the ordering visibly structural rather than a leaderboard in disguise.
    """
    waste = {
        row["Block"]: row["waste_ratio"]
        for row in built["rows"]
        if row["Block"] and row["Set_Name"] == "validation"
        and row["target_container_rows"] == 500
    }
    by_order = [waste[entry["id"]] for entry in built["strategies"]]
    assert by_order != sorted(by_order) or len(by_order) < 2


def test_every_shipped_entry_builds_against_the_corpus(corpus):
    """7.1.8 — an authoring mistake is caught here rather than at image build."""
    from simulator.strategies import build as build_strategy

    for entry in catalog.DEFINITION:
        build_strategy(
            "group_by_chain",
            {"expressions": list(entry.expressions)},
            features=corpus.features,
            block=entry.id,
        )


def test_a_definition_with_a_bad_stage_scores_nothing_at_all(corpus):
    """8.11 — the build refuses as a whole, so no catalogue ships missing an entry."""
    from simulator.strategies import FactoryError

    definition = (
        catalog.Entry("fine", "Fine", ("brand_id",)),
        catalog.Entry("broken", "Broken", ("no_such_column",)),
    )
    with pytest.raises(FactoryError):
        catalog.build(corpus, definition=definition, capacities=(500,))


def test_a_violation_names_the_entry_that_caused_it(corpus):
    """7.1.8.1 — addressed, not merely described."""
    from simulator.strategies import FactoryError

    definition = (catalog.Entry("broken", "Broken", ("no_such_column",)),)
    with pytest.raises(FactoryError) as refused:
        catalog.build(corpus, definition=definition, capacities=(500,))
    assert any(v.block == "broken" for v in refused.value.violations)
