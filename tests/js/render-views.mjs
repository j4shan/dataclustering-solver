/*
 * Render P1, P2 and P3 from a real catalog document and print the trees as JSON.
 *
 * Called as: node render-views.mjs <static-dir> <catalog.json> <id,id,...>
 *
 * The document is projected into a report by `reportFor` — **the page's own function**,
 * imported rather than reimplemented, so what these trees are drawn from is exactly what
 * a reader's selection produces (10.1.2).
 *
 * Nothing here asserts.  The assertions are in `test_report_views.py`, against the trees
 * this prints, so a failure names the requirement rather than a selector.
 */

import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

import { install } from "./fake-dom.mjs";

install();

const [staticDir, payloadPath, selected] = process.argv.slice(2);
const url = (name) => pathToFileURL(`${staticDir}/${name}`).href;

const { processView } = await import(url("view-process.js"));
const { summaryView } = await import(url("view-summary.js"));
const { scatterView } = await import(url("view-scatter.js"));
const { reportFor } = await import(url("catalog-view.js"));

const catalog = JSON.parse(readFileSync(payloadPath, "utf8"));
const report = reportFor(catalog, selected ? selected.split(",") : []);

const p3 = scatterView(report);
const before = p3.toJSON();

// Press the first legend entry, so the highlight can be checked as behaviour rather than
// as a listener that was registered (12.4.6.6).
const [first] = p3.querySelectorAll(".legend-entry");
if (first) first.dispatch("click");

process.stdout.write(
  JSON.stringify({
    // The projection itself, so a test can assert what the views were handed as well as
    // what they drew — and so one node run serves both.
    report,
    p1: processView(report).toJSON(),
    p2: summaryView(report).toJSON(),
    p3: before,
    p3_highlighted: p3.toJSON(),
  }),
);
