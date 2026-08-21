/*
 * P1 — the process view (12.4.4).
 *
 * What each candidate *did* to the corpus, before any score is attached to it.  One
 * column per A.S., all of them dropping from the same root, read top to bottom.  Side by
 * side from one root is what makes two chains comparable at a glance (12.4.4.1).
 *
 * Three things are deliberately absent:
 *
 * **No KPI** (12.4.4.3).  Skipping, waste and cost are P2's and P3's.  A diagram carrying
 * structure and score together invites reading a result off a picture whose geometry
 * means nothing.
 *
 * **Nothing capacity-dependent, and bucketing is not a stage** (12.4.4.4).  A chain has
 * one shape across its whole sweep; drawing the sweep here would quadruple every column
 * to say the same thing four times.  Nothing below reads `target_container_rows`.
 *
 * **No baseline** (12.4.4.6).  Its diagram is a root with no arrows, which would spend a
 * column showing nothing.  The server never sends it in `process`, and nothing here would
 * draw it if it did.
 *
 * Columns are ragged (12.4.4.5): a two-stage chain ends one block higher than a
 * three-stage one and is not padded down to it, because the depth is information.
 */

import { count, node } from "./dom.js";

export function processView(report) {
  const view = node("section", "view view-process");
  view.setAttribute("aria-labelledby", "p1-heading");

  const heading = node("h3", "view-heading", "P1 · How each candidate splits the corpus");
  heading.id = "p1-heading";
  view.append(heading);

  view.append(
    node(
      "p",
      "view-caption",
      "An arrow is one group-by stage, labelled with its expression in the grammar's " +
        "canonical spelling. Stages are shown in the order they are evaluated in, which " +
        "is the order they are sorted into rather than the order they were typed " +
        "\u2014 the chain is a set, so " +
        "every event lands in the same container whichever way round it is written. The " +
        "shape is the same at every container capacity, so no capacity appears here, and " +
        "the baseline is absent because its diagram is a root with no arrows.",
    ),
  );

  if (!report.process.length) {
    view.append(node("p", "empty", "No candidate was configured, so there is nothing to draw."));
    return view;
  }

  const diagram = node("div", "process");

  // The shared root, drawn as a bar the full width of the diagram: every column drops its
  // connector straight from it, so "one corpus, several chains" is the geometry itself
  // rather than a caption claiming it (12.4.4.1).
  const root = node("div", "process-root");
  root.append(node("span", "root-name", "The corpus"));
  root.append(node("span", "root-count", `${count(report.event_count)} records`));
  diagram.append(root);

  const columns = node("div", "process-columns");
  columns.style.setProperty("--column-count", String(report.process.length));
  for (const entry of report.process) columns.append(chainColumn(entry));
  diagram.append(columns);

  view.append(diagram);
  return view;
}

/** One candidate's chain: its name, then a stage per group-by expression. */
function chainColumn(entry) {
  const column = node("div", "process-column");
  column.append(node("div", "process-column-label", entry.block));

  const chain = node("ol", "process-chain");

  // The degenerate chain is a legal block, not an error (12.4.1.5) — it is how the
  // baseline is reproduced from within the family — so it gets a column that says so
  // rather than an empty one that looks like a rendering failure.
  if (!entry.stages.length) {
    chain.append(
      node("li", "process-stage stage-empty", "No stage — the corpus is left whole."),
    );
  }

  for (const stage of entry.stages) chain.append(stageItem(stage));

  column.append(chain);
  return column;
}

function stageItem(stage) {
  const item = node("li", "process-stage");

  const arrow = node("div", "arrow");
  // The line and its head are drawn by the stylesheet and carry no words, so they are
  // hidden from the reading order: the expression beside them is the whole label.
  const line = node("span", "arrow-line");
  line.setAttribute("aria-hidden", "true");
  arrow.append(line);
  arrow.append(node("span", "arrow-label", stage.expression));
  item.append(arrow);

  // The block that the arrow leaves behind carries no number (13.16): a count here is
  // the one figure P1 could be read as a score. It marks that a split happened.
  item.append(node("div", "stage-block"));

  return item;
}
