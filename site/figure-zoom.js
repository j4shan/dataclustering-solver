/*
 * Reusable zoom for embedded images and graphs (12.1.10).
 *
 * One helper attaches the same + / − pair to every figure stage it is given.
 * Scale is session-only working memory: nothing is written to storage (12.2.7).
 * Buttons and labels are built as nodes; no string is parsed as markup (12.6.5).
 */

export const ZOOM_STEPS = [0.75, 1, 1.25, 1.5, 2];
const DEFAULT_INDEX = 1;

const STAGE_SELECTORS = [".illustration-stage", ".plot-figure"];

/** Attach + / − controls to every zoomable stage under `root`. Idempotent. */
export function attachZoom(root) {
  if (!root || typeof root.querySelectorAll !== "function") return;
  for (const stage of stagesIn(root)) enhance(stage);
}

function stagesIn(root) {
  const found = [];
  const seen = new Set();
  const push = (stage) => {
    if (!stage || seen.has(stage)) return;
    if (!drawingOf(stage)) return;
    seen.add(stage);
    found.push(stage);
  };
  for (const selector of STAGE_SELECTORS) {
    for (const stage of root.querySelectorAll(selector)) push(stage);
  }
  if (root.matches && STAGE_SELECTORS.some((selector) => root.matches(selector))) {
    push(root);
  }
  for (const figure of root.querySelectorAll(".formulation figure")) {
    if (!figure.querySelector(".illustration-stage")) push(figure);
  }
  return found;
}

function drawingOf(stage) {
  return stage.querySelector("img") || stage.querySelector("svg");
}

function enhance(stage) {
  if (stage.dataset.zoomAttached === "1") return;
  stage.dataset.zoomAttached = "1";
  stage.classList.add("is-zoomable");
  stage.dataset.zoomIndex = String(DEFAULT_INDEX);

  const widget = document.createElement("div");
  widget.className = "zoom-widget";
  widget.setAttribute("role", "group");
  widget.setAttribute("aria-label", "Zoom");

  const minus = button("zoom-out", "Zoom out", "−");
  const plus = button("zoom-in", "Zoom in", "+");
  minus.addEventListener("click", () => step(stage, -1));
  plus.addEventListener("click", () => step(stage, 1));
  widget.append(minus, plus);
  stage.append(widget);
  apply(stage);
}

function button(className, label, text) {
  const control = document.createElement("button");
  control.type = "button";
  control.className = className;
  control.setAttribute("aria-label", label);
  control.textContent = text;
  return control;
}

function step(stage, delta) {
  const next = clamp(Number(stage.dataset.zoomIndex) + delta);
  stage.dataset.zoomIndex = String(next);
  apply(stage);
}

function apply(stage) {
  const index = clamp(Number(stage.dataset.zoomIndex));
  const drawing = drawingOf(stage);
  if (drawing) {
    const scale = ZOOM_STEPS[index];
    drawing.style.width = `${Math.round(scale * 100)}%`;
    drawing.style.maxWidth = "none";
    drawing.style.height = "auto";
  }
  const minus = stage.querySelector(".zoom-out");
  const plus = stage.querySelector(".zoom-in");
  if (minus) minus.disabled = index <= 0;
  if (plus) plus.disabled = index >= ZOOM_STEPS.length - 1;
}

function clamp(index) {
  if (!Number.isFinite(index)) return DEFAULT_INDEX;
  return Math.min(ZOOM_STEPS.length - 1, Math.max(0, index));
}
