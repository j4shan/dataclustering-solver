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
  image.setAttribute("src", "figures/img/section_problem_medical_cabinet.png");
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

const viewport = first.querySelector(".zoom-viewport");
const image = first.querySelector("img");
if (!viewport) fail("drawing was not wrapped in a viewport");
if (image.parent !== viewport) fail("drawing is not inside the viewport");
if (widgets[0].parent !== first) fail("widget is not a direct child of the stage");
if (viewport.querySelector(".zoom-widget")) fail("widget was placed inside the scrolling viewport");

attachZoom(first);
if (first.querySelectorAll(".zoom-widget").length !== 1) {
  fail("a second attach duplicated the widget");
}
if (first.querySelectorAll(".zoom-viewport").length !== 1) {
  fail("a second attach duplicated the viewport");
}

const minus = first.querySelector(".zoom-out");
const plus = first.querySelector(".zoom-in");
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

plus.dispatch("click");
if (!first.classList.contains("is-pannable")) fail("zoomed-in stage should be pannable");
viewport.dispatch("pointerdown", { clientX: 40, clientY: 10, target: image });
viewport.dispatch("pointermove", { clientX: 10, clientY: 10 });
if (viewport.scrollLeft !== 30) fail(`expected pan of 30px, got ${viewport.scrollLeft}`);
if (first.scrollLeft !== 0) fail("the stage itself must not scroll");
if (!first.classList.contains("is-panning")) fail("stage should be grabbing while the pointer is down");
viewport.dispatch("pointerup", { clientX: 10, clientY: 10 });
if (first.classList.contains("is-panning")) fail("stage should release the grab on pointerup");

minus.dispatch("click");
minus.dispatch("click");
minus.dispatch("click");
if (first.classList.contains("is-pannable")) fail("fit-width stage should not be pannable");
if (viewport.scrollLeft !== 0) fail("pan should reset at fit-width");

const empty = document.createElement("div");
empty.className = "illustration-stage";
attachZoom(empty);
if (empty.querySelector(".zoom-widget")) fail("a stage with no drawing grew a widget");

process.stdout.write(`${JSON.stringify({ ok: true, steps: ZOOM_STEPS })}\n`);
