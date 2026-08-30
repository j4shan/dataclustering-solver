/*
 * Exercise attachZoom against the fake DOM (12.1.10).
 *
 * Called as: node test_figure_zoom.mjs <static-dir>
 * Prints JSON { ok: true } or exits 1 with a message.
 */

import { pathToFileURL } from "node:url";

import { install } from "./fake-dom.mjs";

install();

const staticDir = process.argv[2];
const { attachZoom, ZOOM_STEPS } = await import(
  pathToFileURL(`${staticDir}/figure-zoom.js`).href
);

function stage() {
  const box = document.createElement("div");
  box.className = "illustration-stage";
  const image = document.createElement("img");
  image.setAttribute("src", "figures/img/section_a_medical_cabinet.png");
  box.append(image);
  return box;
}

function fail(message) {
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

const first = stage();
attachZoom(first);
const widgets = first.querySelectorAll(".zoom-widget");
if (widgets.length !== 1) fail(`expected one widget, got ${widgets.length}`);
if (first.dataset.zoomAttached !== "1") fail("stage was not marked attached");

attachZoom(first);
if (first.querySelectorAll(".zoom-widget").length !== 1) {
  fail("a second attach duplicated the widget");
}

const minus = first.querySelector(".zoom-out");
const plus = first.querySelector(".zoom-in");
const image = first.querySelector("img");
if (!minus || !plus || !image) fail("controls or drawing missing");
if (minus.getAttribute("aria-label") !== "Zoom out") fail("minus is unlabelled");
if (plus.getAttribute("aria-label") !== "Zoom in") fail("plus is unlabelled");
if (image.style.width !== "100%") fail(`default width was ${image.style.width}`);
if (minus.disabled) fail("minus should be enabled at 100%");
if (plus.disabled) fail("plus should be enabled at 100%");

plus.dispatch("click");
if (image.style.width !== "125%") fail(`after + expected 125%, got ${image.style.width}`);

plus.dispatch("click");
plus.dispatch("click");
if (image.style.width !== "200%") fail(`after max + expected 200%, got ${image.style.width}`);
if (!plus.disabled) fail("plus should disable at the top of the ladder");
if (ZOOM_STEPS.at(-1) !== 2) fail("ladder top is not 200%");

minus.dispatch("click");
if (image.style.width !== "150%") fail(`after − expected 150%, got ${image.style.width}`);
if (plus.disabled) fail("plus should enable after stepping down");

const empty = document.createElement("div");
empty.className = "illustration-stage";
attachZoom(empty);
if (empty.querySelector(".zoom-widget")) fail("a stage with no drawing grew a widget");

process.stdout.write(`${JSON.stringify({ ok: true, steps: ZOOM_STEPS })}\n`);
