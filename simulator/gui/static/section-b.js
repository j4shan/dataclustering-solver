/*
 * Section B — the strategy catalogue and the report it draws (12.4.2, 12.4.3).
 *
 * **Nothing here starts work.**  This file used to hold a strategy builder: a block bar, a
 * chain repeater, a capacity box, completeness rules, an Evaluate button and the request
 * it fired.  All of it is gone.  What a reader does now is choose which of the catalogued
 * strategies to compare, and choosing redraws three views from rows the browser already
 * holds — no request, no spinner, no failure mode (12.4.2.5).
 *
 * The catalogue itself is computed offline by `bench/catalog.py` (8.11) against a corpus
 * this process never loads.  Every figure on this page is a field of that document; the
 * page computes none of them (12.4.2.6, 12.6.4).
 *
 * State is one plain object, and 13.4 still excludes persisting any of it — no
 * `localStorage`, no cookie, no URL fragment, nothing asked of the server.  A reader
 * returns to a report by selecting the same entries again, against a catalogue that is
 * identical for every reader.
 *
 * **No string from the document is ever parsed as markup** (12.6.5).  Every node below is
 * constructed and every value set with `textContent`.  That the strings now come from a
 * build artifact rather than from a reader's keystrokes does not relax the rule: the page
 * cannot tell the difference, and a boundary that holds only for trusted input is not one.
 *
 * The projection from catalogue to report lives in `catalog-view.js`, which holds no DOM
 * and is exercised directly by the tests.  ES modules, natively — no bundler (13.3).
 */

import {
  MAX_SELECTED,
  containersByCapacity,
  reportFor,
  toggled,
} from "./catalog-view.js";
import { count, node } from "./dom.js";
import { processView } from "./view-process.js";
import { scatterView } from "./view-scatter.js";
import { summaryView } from "./view-summary.js";

/** The three views of the report, in the fixed order a reader needs them (12.4.3.1):
 *  what was built, what it scored, how the scores trade off. */
const VIEWS = [processView, summaryView, scatterView];

const state = {
  catalog: null,
  selected: [],
  error: null,
};

/* -- what is being clustered (12.4.2.3) -------------------------------------------- */

//: The corpus in one paragraph and one table definition, so a reader meets the columns
//: before meeting the strategies that split on them.  Authored here rather than in
//: `index.html` because `render()` replaces everything in the pane.  Every string below
//: describes the shipped synthetic provider and nothing else.
const DATASET_INTRO =
  "Take a look at what is being clustered. Every row is one auto part sale, and the " +
  "columns come in three flavours you can spot by name. There is one id column, " +
  "record_id, which is also the arrival sequence — it counts up in the order the rows " +
  "landed, so position alone tells you how old a row is. Four feature columns describe " +
  "the sale itself: a category, a price tier, a warranty term, and the transaction date " +
  "every query scopes on. Those are the columns the strategies below group on. Then " +
  "there is the blob, which is where the bytes actually are: the payload itself is never " +
  "materialized, only its compressed and decompressed size, drawn so a wiper-blade sale " +
  "stays a few kilobytes while a drivetrain assembly runs into the hundreds. One last " +
  "thing worth knowing: brand_id is a tenant. Forty of them share this one table, a few " +
  "of them large and most of them small, and demand leans hard toward the popular ones — " +
  "which makes it the strongest clusterable signal in here.";

const DATASET_DDL = `CREATE TABLE test.test.auto_parts (
    record_id                       BIGINT,
    brand_id                        STRING,
    feature_category                STRING,
    feature_price_tier              TINYINT,
    feature_warranty_years          TINYINT,
    feature_transaction_date        DATE,
    blob_detail_compressed_bytes    BIGINT,
    blob_detail_decompressed_bytes  BIGINT
);`;

//: 12.4.2.4 — stated where the reader is, not only in the specification.  A list of
//: scored candidates reads as a leaderboard unless it says otherwise, and this is the
//: sentence that says otherwise.
const FIXTURE_NOTE =
  "These are demonstration fixtures, not recommendations. They were chosen to span a " +
  "range of shapes — how many times the corpus is cut, and on what — and they are " +
  "listed from the coarsest split to the finest, which is a property of the chains and " +
  "not a ranking. That one of them scores well here is a fact about this corpus and " +
  "this workload, and this project proposes no assignment strategy.";

function renderDatasetIntro() {
  const intro = node("div", "dataset-intro");
  intro.append(node("p", null, DATASET_INTRO));
  const block = node("pre");
  block.append(node("code", "language-sql", DATASET_DDL));
  intro.append(block);
  return intro;
}

function renderColumnReference() {
  const details = node("details", "columns");
  details.append(node("summary", null, "Feature columns"));

  const list = node("dl", "column-list");
  // From the catalog document's provenance block, which the generator copied out of the
  // corpus manifest (4.12) — so this pane names real columns without a corpus in the
  // process to ask (12.2.3).
  for (const column of state.catalog.corpus.feature_columns) {
    list.append(node("dt", "column-name", column.name));
    const domain =
      column.values !== undefined
        ? column.values.slice(0, 6).join(", ") +
          (column.values.length > 6 ? ` … (${column.cardinality})` : "")
        : `${column.minimum} … ${column.maximum} (${column.cardinality} distinct)`;
    const description = node("dd", "column-domain");
    description.append(
      node("span", "column-family", column.family),
      node("span", null, domain),
    );
    list.append(description);
  }
  details.append(list);
  return details;
}

/* -- the catalogue list (12.4.2.1, 12.4.2.2) --------------------------------------- */

/** One entry: what it does to the corpus, and what that cost in containers. */
function entryCard(entry) {
  const chosen = state.selected.includes(entry.id);
  const full = state.selected.length >= MAX_SELECTED;

  const card = node("div", "entry");
  const control = node("button", "entry-select");
  control.type = "button";
  // Selection is an attribute the stylesheet reads, and it is marked by a check, a
  // border and weight as well as colour (12.6.2).
  control.setAttribute("aria-pressed", String(chosen));
  // Disabled rather than hidden at the ceiling, so the limit is visible before it is
  // reached rather than discovered by a control vanishing (12.4.2.2).
  control.disabled = !chosen && full;
  control.addEventListener("click", () => {
    state.selected = toggled(state.selected, entry.id);
    render();
  });

  const head = node("div", "entry-head");
  head.append(node("span", "entry-mark", chosen ? "✓" : ""));
  head.append(node("span", "entry-label", entry.label));
  control.append(head);

  // The chain, one row per stage, each carrying the splits the corpus stands in after
  // it (8.11.2).  A stage's own expression is drawn in the grammar's canonical spelling
  // (12.4.1.3) — the order shown is the order evaluated, not an order anyone typed.
  const chain = node("ol", "entry-chain");
  if (!entry.stages.length) {
    chain.append(node("li", "entry-stage", "No stage — the corpus is left whole."));
  }
  for (const stage of entry.stages) {
    const row = node("li", "entry-stage");
    row.append(node("code", "stage-expression", stage.expression));
    row.append(node("span", "stage-splits", `${count(stage.splits)} splits`));
    chain.append(row);
  }
  control.append(chain);

  const summary = node("div", "entry-summary");
  summary.append(node("span", "entry-leaves", `${count(entry.leaf_count)} leaves`));
  // Container count depends on capacity, so it is shown per capacity rather than as one
  // number that would have to pick a capacity silently (12.4.2.1).
  const capacities = node("dl", "entry-capacities");
  for (const { capacity, containers } of containersByCapacity(state.catalog, entry)) {
    capacities.append(node("dt", null, count(capacity)));
    capacities.append(
      node("dd", null, containers === null ? "—" : count(containers)),
    );
  }
  summary.append(capacities);
  control.append(summary);

  card.append(control);
  return card;
}

function renderCatalogue() {
  const panel = node("div", "catalogue");

  const heading = node("div", "catalogue-head");
  heading.append(node("h3", null, "Assignment strategies"));
  heading.append(
    node(
      "p",
      "catalogue-hint",
      `Choose up to ${MAX_SELECTED} to compare. ` +
        `${state.selected.length} of ${MAX_SELECTED} selected.`,
    ),
  );
  panel.append(heading);
  panel.append(node("p", "fixture-note", FIXTURE_NOTE));

  const list = node("div", "entry-list");
  for (const entry of state.catalog.strategies) list.append(entryCard(entry));
  panel.append(list);

  if (state.selected.length >= MAX_SELECTED) {
    panel.append(
      node("p", "note", `${MAX_SELECTED} is the limit — deselect one to swap it out.`),
    );
  }
  return panel;
}

/* -- the report (12.4.3) ----------------------------------------------------------- */

/** Which dataset these figures came from (12.4.3.3, 4.10). */
function provenance(report) {
  const line = node("p", "provenance");
  line.append(node("span", "provenance-label", "Corpus"));
  line.append(node("span", "provenance-id", report.dataset_id));
  line.append(node("span", "provenance-figure", `${count(report.event_count)} events`));
  line.append(node("span", "provenance-figure", `${count(report.query_count)} queries`));
  line.append(node("span", "provenance-figure", `batch ${report.batch_id}`));
  return line;
}

function renderReport() {
  const pane = document.getElementById("report");
  pane.replaceChildren();

  if (state.error) {
    const problem = node("div", "problem");
    problem.append(node("h3", null, "The catalogue could not be loaded"));
    problem.append(node("p", null, state.error));
    pane.append(problem);
    return;
  }

  // 12.4.3.8 — empty, and it says which control fills it.
  if (!state.selected.length) {
    pane.append(
      node(
        "p",
        "empty",
        "Nothing selected — choose a strategy from the list to draw its report.",
      ),
    );
    return;
  }

  const report = reportFor(state.catalog, state.selected);
  const container = node("div", "views");
  container.id = "views";
  container.append(provenance(report));
  for (const view of VIEWS) container.append(view(report));
  pane.append(container);
}

function render() {
  const panel = document.getElementById("builder");
  panel.replaceChildren();

  if (state.error) {
    panel.append(node("p", "empty", state.error));
    renderReport();
    return;
  }
  if (!state.catalog) {
    panel.append(node("p", "empty", "Loading the strategy catalogue…"));
    return;
  }

  panel.append(renderDatasetIntro());
  panel.append(renderColumnReference());
  panel.append(renderCatalogue());
  renderReport();
}

/* -- start ------------------------------------------------------------------------- */

/** How many entries are shown before a reader has chosen anything.
 *
 *  Two, so the page arrives with a report on it rather than an instruction — which is
 *  the whole dividend of computing the catalogue ahead of time.  They are the *first*
 *  two in the document's order, which is the coarsest two (8.11.3): a preselection of
 *  the best-scoring entries would be the recommendation 12.4.2.4 denies making.
 */
const OPENING_SELECTION = 2;

async function start() {
  try {
    const response = await fetch("api/catalog");
    if (!response.ok) throw new Error(`the server answered ${response.status}`);
    state.catalog = await response.json();
    state.selected = state.catalog.strategies
      .slice(0, OPENING_SELECTION)
      .map((entry) => entry.id);
  } catch (failure) {
    state.error = `Could not load the strategy catalogue: ${failure.message}`;
  }
  render();
}

start();
