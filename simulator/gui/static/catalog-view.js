/*
 * Turning a catalog document into what the three views draw (12.4.2.2, 12.4.3.5).
 *
 * **This is the whole of what selecting a strategy does.**  It was a round trip to the
 * server and twenty layouts scored against a 600 000-event corpus; it is now a filter over
 * rows the browser already holds.  Nothing here fetches, nothing here can fail, and
 * nothing here computes a figure — every number it moves was computed offline by 8.11's
 * generator and is passed through untouched (12.4.2.6, 12.6.4).
 *
 * It holds no DOM, which is what lets `tests/js/render-views.mjs` project a document with
 * the *same function the page uses* rather than with a second copy of the rule (10.1.2).
 *
 * The report object it returns is deliberately the **shape the three views already took**
 * — the redesign changed where the numbers come from and changed nothing about how they
 * are drawn, and this function is where that promise is kept.
 */

/** 12.4.2.2 — four, because P2 reserves sixteen candidate rows and P3 draws four series. */
export const MAX_SELECTED = 4;

/** The report P1, P2 and P3 draw, for one selection out of one catalog document.
 *
 * `selected` is the ids of the chosen entries.  Order follows the document rather than
 * the order a reader clicked, so the same four entries always produce the same report and
 * a series keeps its colour across selections.
 */
export function reportFor(catalog, selected) {
  const chosen = new Set(selected);
  const entries = catalog.strategies.filter((entry) => chosen.has(entry.id));

  // **Inside the report, a candidate is named by its label rather than its id.**  The
  // document identifies an entry by id, because an id is what a row is joined on and a
  // label is presentation that may be reworded (12.4.3.5).  P1's column headings and P3's
  // legend are that presentation, and the views take one key for both naming and joining
  // — so the two are reconciled here, once, and every view downstream sees one name.
  // Labels are unique across the catalogue, which is what makes the mapping lossless.
  const labelOf = new Map(catalog.strategies.map((entry) => [entry.id, entry.label]));

  return {
    // Provenance travels from the document rather than from anything the page knows, so a
    // figure is never detached from the corpus that produced it (12.4.3.3).
    dataset_id: catalog.corpus.dataset_id,
    event_count: catalog.corpus.event_count,
    query_count: catalog.corpus.query_count,
    batch_id: catalog.batch_id,
    baseline: catalog.baseline.strategy,
    baseline_capacities: catalog.baseline.capacities,
    // P1 reads `block` and `stages`, and reads only `expression` off a stage — so the
    // split counts ride along here and are drawn by the panel, never by the diagram
    // (13.16).  One array, two readers, no second copy.
    process: entries.map((entry) => ({ block: entry.label, stages: entry.stages })),
    // The baseline's rows carry a null `Block` and are always kept: it is the reference
    // the candidates are read against, not a fifth candidate (12.4.6.5).
    rows: catalog.rows
      .filter((row) => row.Block === null || chosen.has(row.Block))
      .map((row) =>
        row.Block === null ? row : { ...row, Block: labelOf.get(row.Block) },
      ),
  };
}

/** What one entry's row says, for the capacities it was swept across (12.4.2.1).
 *
 * The container count is a property of the layout and therefore of the capacity, so it is
 * read per capacity off the rows rather than stored a second time on the entry.  Either
 * set answers — a container count is the same whichever half of the workload is asked —
 * so the training rows are taken and the choice is stated rather than left to look
 * arbitrary.
 */
export function containersByCapacity(catalog, entry) {
  const counts = new Map();
  for (const row of catalog.rows) {
    if (row.Block === entry.id && row.Set_Name === "training") {
      counts.set(row.target_container_rows, row.container_count);
    }
  }
  return entry.capacities.map((capacity) => ({
    capacity,
    containers: counts.get(capacity) ?? null,
  }));
}

/** Whether one more entry may be selected (12.4.2.2). */
export function canSelect(selected, id) {
  return selected.includes(id) || selected.length < MAX_SELECTED;
}

/** The selection after clicking `id` — added if there is room, removed if already in.
 *
 * Returned as a new array rather than mutated, so a caller can compare before and after
 * to decide whether anything needs redrawing.
 */
export function toggled(selected, id) {
  if (selected.includes(id)) return selected.filter((chosen) => chosen !== id);
  if (selected.length >= MAX_SELECTED) return selected;
  return [...selected, id];
}
