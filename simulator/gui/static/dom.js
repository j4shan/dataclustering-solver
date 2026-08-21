/*
 * Node constructors and number formatting — the page's only two shared utilities.
 *
 * **Text goes in as text** (12.6.5).  Every constructor here sets `textContent` or an
 * attribute it computed itself; none of them accepts markup, and there is no sanitizer to
 * fall back on because 13.3 rules out the library.  A reader who types `<img onerror=…>`
 * into an expression box sees those characters in the report, which is both the correct
 * rendering and the only one that cannot execute them.
 *
 * The formatters assert nothing.  Each one takes a number that came from a metric row and
 * decides how many digits of it to show — 12.6.4's rule is that every figure is traceable
 * to a row, and rounding for display is not the same as computing one.
 */

const SVG_NS = "http://www.w3.org/2000/svg";

/** An element with a class and text. */
export function node(tag, className, text) {
  const created = document.createElement(tag);
  if (className) created.className = className;
  if (text !== undefined) created.textContent = text;
  return created;
}

/** An SVG element with attributes, and text if it takes any.
 *
 * `className` cannot be assigned on an SVG element the way it can on an HTML one, so the
 * class travels in `attrs` like every other attribute.
 */
export function svg(tag, attrs = {}, text) {
  const created = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value !== undefined && value !== null) created.setAttribute(name, String(value));
  }
  if (text !== undefined) created.textContent = text;
  return created;
}

/** A whole number, grouped: `20,000`. */
export function count(value) {
  return Number(value).toLocaleString();
}

/** A short form for an axis tick, where the exact digits are not the point: `1.2M`. */
export function compact(value) {
  return new Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumSignificantDigits: 3,
  }).format(Number(value));
}

/** A ratio in [0, 1] as a percentage: `16.7%`. */
export function percent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

/** A multiple, which is what waste and lift both are: `26.52`. */
export function ratio(value) {
  return Number(value).toFixed(2);
}

/** A byte figure in decimal units, because storage is quoted that way: `194.8 MB`. */
export function bytes(value) {
  const size = Number(value);
  const units = ["B", "kB", "MB", "GB", "TB", "PB"];
  let step = 0;
  let scaled = size;
  while (scaled >= 1000 && step < units.length - 1) {
    scaled /= 1000;
    step += 1;
  }
  return `${scaled.toFixed(step === 0 ? 0 : 1)} ${units[step]}`;
}
