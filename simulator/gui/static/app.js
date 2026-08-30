/*
 * The application shell's behaviour (12.1).
 *
 * Plain modules, no framework and no build step (10.3.5).  What this file does is
 * deliberately small: mount the pane fragments, display the section the nav
 * selected, and attach the figure-zoom widget to whatever those fragments drew.
 * Everything that computes a number lives behind the harness (12.6.4).
 */

import { attachZoom } from "./figure-zoom.js";

/** Fetch a committed fragment and put it in its pane.
 *
 * Some fragments are pre-rendered from Markdown ahead of serving (12.3, 12.5);
 * others are authored HTML. This injects finished HTML rather than parsing Markdown
 * in the browser.  A failure leaves a message naming the file, because a silently
 * empty pane reads as a page that is still loading.
 *
 * **This is the only place the page assigns HTML, and the rule that makes it safe is
 * 12.6.5.**  What it injects is a repository artifact named by an authored
 * `data-mount` attribute — never a path from the URL and never anything a reader
 * typed.  Everything that *did* come from a request — an
 * expression, a block name, a violation message — is written with `textContent` or
 * built as nodes, so no reader-supplied string is ever parsed as markup.
 */
async function mount(pane, url) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${response.status}`);
    pane.innerHTML = await response.text();
    attachZoom(pane);
  } catch (failure) {
    pane.replaceChildren(element("p", "empty", `Could not load ${url} (${failure.message}).`));
  }
}

/** A node with a class and text — the safe constructor everything else in the page uses.
 *
 * Text goes in as text (12.6.5).  A reader who types `<img onerror=…>` into an
 * expression box sees those characters in the report, which is both correct and the
 * only behaviour that cannot execute them.
 */
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/** Display the section the nav selected, and only that one (12.1.1, 12.1.3).
 *
 * The switch is driven by the location hash rather than by a click handler, because the
 * nav is already a list of anchors: letting the browser navigate and reacting to the
 * `hashchange` it fires covers a click, a typed URL, a restored tab and the back button
 * in one path, and leaves the address bar naming what is on screen for free.
 */
function selectSection() {
  const sections = new Map(
    [...document.querySelectorAll(".section")].map((section) => [section.id, section]),
  );
  const links = new Map(
    [...document.querySelectorAll("[data-nav]")].map((a) => [a.dataset.nav, a]),
  );

  const show = (requested) => {
    // An unknown fragment is not an error to report: the page opens on A, which is where
    // a reader who followed a stale link should land anyway.
    const id = sections.has(requested) ? requested : "problem";
    for (const [name, section] of sections) section.hidden = name !== id;
    for (const [name, link] of links) {
      // `aria-current` is the state, and the stylesheet keys off it: one source of
      // truth for "this is the section you are in", not a class beside an attribute.
      link.setAttribute("aria-current", String(name === id));
    }
    // The section a reader just chose is `display: none` at the moment they choose it, so
    // the browser's own fragment navigation has nothing to move to.  Moving focus here is
    // what tells a screen reader the page changed under them (12.6.1).
    sections.get(id).focus({ preventScroll: true });
  };

  window.addEventListener("hashchange", () => show(location.hash.slice(1)));
  show(location.hash.slice(1) || "problem");
}

for (const pane of document.querySelectorAll("[data-mount]")) {
  mount(pane, pane.dataset.mount);
}
selectSection();
