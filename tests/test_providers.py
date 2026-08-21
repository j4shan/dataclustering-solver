"""The provider seam.

The harness must be able to score a corpus it did not generate.  These tests are the
only thing standing between that property and a well-meaning edit that reintroduces a
generator's column name into ``core/``.
"""

from __future__ import annotations

import csv
import random

import numpy as np
import pytest

from simulator.core import contract
from simulator.core import dataset as dataset_module
from simulator.core.evaluate import evaluate
from simulator.core.layout import validate_and_compact
from simulator.providers import available, external, synthetic
from simulator.providers.synthetic import DatasetConfig
from simulator.strategies import build_view, get

TINY = DatasetConfig(
    name="seam-corpus",
    n_events=3_000,
    n_transaction_days=60,
    n_query_days=16,
    half_life_days=5.0,
    seed=808,
)


def score(corpus) -> dict:
    view = build_view(corpus, 100)
    container_of_event, _ = validate_and_compact(
        get("insertion_order")(view), corpus.event_count
    )
    return evaluate(corpus, container_of_event, 100)["validation"]


def test_both_providers_are_registered():
    assert available() == ["external", "synthetic"]


def test_external_round_trip_reproduces_every_kpi(tmp_path):
    """Export three CSVs, re-ingest them as a stranger's corpus, score both.

    If these disagree the harness is reading something the contract does not promise.
    """
    generated = synthetic.generate(TINY, tmp_path / "generated")

    export = tmp_path / "export"
    export.mkdir()
    for name in contract.AUTHORED_FILES:
        (export / name).write_bytes((generated / name).read_bytes())

    adopted = external.ingest(out_dir=tmp_path / "adopted", source=export)

    direct = score(dataset_module.load(generated))
    round_tripped = score(dataset_module.load(adopted))
    assert direct == round_tripped


def _foreign_corpus(path):
    """A corpus with keys and column names this project has never emitted."""
    path.mkdir(parents=True, exist_ok=True)
    rng = random.Random(4)
    event_keys = [f"evt-{rng.getrandbits(40):010x}" for _ in range(400)]
    query_keys = [f"q-{i:03d}" for i in range(12)]

    with (path / contract.EVENTS_FILE).open("w", newline="") as handle:
        writer = csv.writer(handle)
        # Unfamiliar feature names, and ONE size pair rather than the synthetic's two.
        writer.writerow(
            ["record_id", "part_family", "list_price_band",
             "blob_payload_compressed_bytes", "blob_payload_decompressed_bytes"]
        )
        for key in event_keys:
            compressed = rng.randint(500, 40_000)
            writer.writerow(
                [key, rng.choice(["clutch", "radiator"]), rng.randint(0, 9),
                 compressed, compressed * 4]
            )

    with (path / contract.QUERIES_FILE).open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["query_id", "query_time", "set_name"])
        for i, key in enumerate(query_keys):
            writer.writerow(
                [key, f"2025-07-{1 + i:02d}",
                 "training" if i < len(query_keys) // 2 else "validation"]
            )

    with (path / contract.SELECTIONS_FILE).open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["record_id", "query_id"])
        for query_key in query_keys:
            for event_key in rng.sample(event_keys, rng.randint(10, 60)):
                writer.writerow([event_key, query_key])
    return path


def test_unfamiliar_columns_become_features_without_a_code_change(tmp_path):
    source = _foreign_corpus(tmp_path / "foreign")
    corpus = dataset_module.load(external.ingest(out_dir=tmp_path / "adopted", source=source))

    assert set(corpus.features) == {"part_family", "list_price_band"}
    assert corpus.compressed_bytes.sum() > 0
    # String keys survive as provenance, hidden from strategies behind the underscore.
    assert corpus.hidden_event_columns["_source_record_key"][0].startswith("evt-")
    assert not any(name.startswith("_") for name in build_view(corpus, 100).features)

    # And the whole pipeline runs on it.
    assert score(corpus)["waste_bytes"] >= 0


def test_size_columns_must_carry_the_blob_prefix(tmp_path):
    """Sizes are the one role the loader must find, so the pattern is enforced.

    An unprefixed byte column is indistinguishable from a feature that happens to be
    named after bytes, and scoring a corpus whose weights were silently read as features
    would produce a plausible wrong number rather than an error.
    """
    source = _foreign_corpus(tmp_path / "foreign")
    rows = list(csv.reader((source / contract.EVENTS_FILE).open()))
    rows[0] = [name.removeprefix(contract.BLOB_PREFIX) for name in rows[0]]
    with (source / contract.EVENTS_FILE).open("w", newline="") as handle:
        csv.writer(handle).writerows(rows)

    with pytest.raises(contract.ContractViolation, match=contract.BLOB_PREFIX):
        contract.validate(source)


def test_a_corpus_missing_size_columns_is_rejected(tmp_path):
    source = _foreign_corpus(tmp_path / "foreign")
    rows = list(csv.reader((source / contract.EVENTS_FILE).open()))
    keep = [i for i, name in enumerate(rows[0]) if not name.endswith("_decompressed_bytes")]
    with (source / contract.EVENTS_FILE).open("w", newline="") as handle:
        csv.writer(handle).writerows([[row[i] for i in keep] for row in rows])

    with pytest.raises(contract.ContractViolation, match="decompressed"):
        contract.validate(source)


def test_duplicate_keys_are_rejected(tmp_path):
    """A repeated identifier corrupts every count while looking like a plausible result."""
    source = _foreign_corpus(tmp_path / "foreign")
    rows = list(csv.reader((source / contract.EVENTS_FILE).open()))
    rows[2][0] = rows[1][0]  # two events claiming one key
    with (source / contract.EVENTS_FILE).open("w", newline="") as handle:
        csv.writer(handle).writerows(rows)

    with pytest.raises(contract.ContractViolation, match="duplicate"):
        external.ingest(out_dir=tmp_path / "adopted", source=source)


def test_a_missing_file_names_itself(tmp_path):
    source = _foreign_corpus(tmp_path / "foreign")
    (source / contract.SELECTIONS_FILE).unlink()
    with pytest.raises(contract.ContractViolation, match=contract.SELECTIONS_FILE):
        contract.validate(source)


def test_core_never_names_a_provider_column():
    """The seam, asserted directly: no generator column name may appear in core/."""
    from pathlib import Path

    core = Path(dataset_module.__file__).parent
    provider_columns = ("feature_price_tier", "feature_warranty_years", "feature_category",
                        "feature_transaction_date", "brand_id", "part_family",
                        "blob_detail_compressed_bytes", "blob_payload_compressed_bytes")
    offenders = [
        f"{source.name}:{column}"
        for source in core.glob("*.py")
        for column in provider_columns
        if column in source.read_text()
    ]
    assert offenders == [], f"core/ names provider-specific columns: {offenders}"


def test_dense_keys_are_assigned_in_table_order(tmp_path):
    source = _foreign_corpus(tmp_path / "foreign")
    corpus = dataset_module.load(external.ingest(out_dir=tmp_path / "adopted", source=source))
    assert np.array_equal(corpus.event_id, np.arange(corpus.event_count))
    assert np.array_equal(corpus.query_id, np.arange(corpus.query_count))


# -- the manifest's feature-column summary (4.12) -----------------------------------


@pytest.fixture(scope="module")
def summarized(tmp_path_factory):
    path = synthetic.generate(TINY, tmp_path_factory.mktemp("summary"))
    return dataset_module.load(path)


def test_the_manifest_summarizes_exactly_the_partitionable_columns(summarized):
    """4.12 — the list a caller composes a group-by against, and nothing else.

    Identity, hidden and blob-size columns are all absent: none of them is something a
    strategy may partition on, so offering one would be offering a mistake.
    """
    named = [column["name"] for column in summarized.feature_summary]
    assert named == list(summarized.features)
    assert contract.RECORD_ID not in named
    assert not any(name.startswith(contract.HIDDEN_PREFIX) for name in named)
    assert not any(contract.is_size(name) for name in named)


def test_the_summary_describes_a_column_as_the_loader_will_read_it(summarized):
    """The date column is written as a string and read back as a date.

    Summarizing what the provider held in memory would call it text and quietly offer a
    reader the wrong operators; summarizing the written CSV calls it what it is.
    """
    families = {c["name"]: c["family"] for c in summarized.feature_summary}
    loaded = {
        name: contract.dtype_family(values.dtype)
        for name, values in summarized.features.items()
    }
    assert families == loaded
    assert contract.TEMPORAL in families.values()


def test_a_small_domain_is_listed_and_a_large_one_is_bounded(summarized):
    """Forty brands are worth showing a reader; a thousand dates are not."""
    for column in summarized.feature_summary:
        if column["cardinality"] <= contract.MAX_ENUMERATED_VALUES:
            assert len(column["values"]) == column["cardinality"]
        else:
            assert "values" not in column
            assert column["minimum"] <= column["maximum"]


def test_the_summary_is_json_native(summarized):
    """It travels to a browser, so a numpy scalar in it would be a defect."""
    import json

    assert json.loads(json.dumps(summarized.feature_summary)) == summarized.feature_summary


def test_a_corpus_written_before_the_field_existed_reports_nothing(summarized):
    """Absence is answered honestly rather than guessed at on load."""
    summarized.manifest.pop("feature_columns")
    try:
        assert summarized.feature_summary == []
    finally:
        summarized.manifest["feature_columns"] = contract.summarize_feature_columns(
            summarized.path
        )


def test_loading_rejects_a_corpus_whose_keys_are_not_the_arrival_sequence(tmp_path):
    """4.13 — the sequence 4.2 declares is checked where a corpus enters, not assumed.

    A strategy is entitled to read an event's position out of its key, so a corpus that
    shuffled the keys would be scored against a layout meaning something other than what
    the strategy asked for — a plausible wrong number rather than an error.
    """
    path = synthetic.generate(TINY, tmp_path / "generated")
    rows = list(csv.reader((path / contract.EVENTS_FILE).open()))
    key = rows[0].index(contract.RECORD_ID)
    rows[3][key], rows[4][key] = rows[4][key], rows[3][key]
    with (path / contract.EVENTS_FILE).open("w", newline="") as handle:
        csv.writer(handle).writerows(rows)

    with pytest.raises(contract.ContractViolation, match="arrival sequence"):
        dataset_module.load(path)


def test_an_adopted_corpus_carries_the_arrival_sequence(tmp_path):
    """4.6 — ingest resolves the order once, so the reader never reconstructs it."""
    corpus = dataset_module.load(
        external.ingest(out_dir=tmp_path / "adopted", source=_foreign_corpus(tmp_path / "foreign"))
    )

    assert np.array_equal(corpus.event_id, np.arange(corpus.event_count))
