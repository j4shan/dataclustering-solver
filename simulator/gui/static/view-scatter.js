/*
 * P3 — the paired scatter plots (12.4.6).
 *
 * Two plots side by side, sharing an X domain and a width so a point's horizontal
 * position means the same thing in both (12.4.6.1).  X is total container count on both.
 * Y is activated record count on the left and activated record byte weight on the right.
 *
 * **Both axes are costs, so the reading is a Pareto one and lower-left is better**
 * (12.4.6.2).  The pair exists because the two Y axes disagree exactly when activation
 * concentrates in unusually large or unusually small events — and that disagreement is
 * the finding, not a redundancy.  Sharing the X domain is what makes the disagreement
 * visible as a difference in shape between two plots rather than a difference in scale.
 *
 * **A series is one A.S. across its capacity sweep** (12.4.6.3): one colour, one legend
 * entry, points connected in capacity order.  The connecting line is the granularity–waste
 * trade the sweep traces, and is neither a fit nor a trend.
 *
 * **Every point is direct-labelled with its capacity** (12.4.6.4), so nothing is reachable
 * only by pointing at it.  Highlighting therefore adds emphasis and never information
 * (12.4.6.7) — which is what keeps both plots readable in print, keeps 12.6.2 true, and
 * holds 13.7's hover exception to a narrow one.  The legend is the control: focusable and
 * keyboard-operable, with pointer hover on a legend entry or a mark as its mirror
 * (12.4.6.6), and the mirror runs across both plots at once.
 *
 * Series take the validated report palette (9.4) and are distinguished by marker shape as
 * well as colour (12.4.6.8, 12.6.2).  The baseline is a grey dashed line and not a legend
 * entry (12.4.6.5): it is the reference the candidates are read against, not a fifth
 * candidate.
 *
 * The figures plotted are the **held-out** ones, named in the caption and in each plot's
 * accessible label — 12.4.3.2 makes a number without its set name a defect, and 12.4.6
 * does not choose the set, so it is chosen here and stated.
 */

import { bytes, compact, count, node, svg } from "./dom.js";

/** The drawing box, in user units.  Both plots use it, which is what shares the width.
 *
 * The stylesheet caps the rendered width at this same figure, so one user unit is at most
 * one pixel and the text inside never renders larger than it was drawn.
 */
const GEOMETRY = { width: 320, height: 250, left: 58, right: 12, top: 12, bottom: 44 };

const TICKS = 4;

/** Shape per series, in the order blocks arrive: colour is never the only difference. */
const SHAPES = ["circle", "square", "triangle", "diamond"];

/** The set both plots are drawn from. */
const SET = "validation";

const PLOTS = [
  {
    key: "materialized_records",
    label: "Activated records",
    axis: "Activated record count (held out)",
    format: count,
    tick: compact,
  },
  {
    key: "materialized_bytes",
    label: "Activated bytes",
    axis: "Activated record byte weight (held out)",
    format: bytes,
    tick: bytes,
  },
];

export function scatterView(report) {
  const view = node("section", "view view-scatter");
  view.setAttribute("aria-labelledby", "p3-heading");

  const heading = node("h3", "view-heading", "P3 · What the sweep trades");
  heading.id = "p3-heading";
  view.append(heading);

  view.append(
    node(
      "p",
      "view-caption",
      "Held-out figures. Both axes are costs, so lower-left is better and the two plots share " +
        "an X scale: a point sits at the same horizontal position in each. One line is one " +
        "candidate across its capacity sweep, labelled at every point with the capacity that " +
        "produced it. The grey dashed line is the baseline.",
    ),
  );

  const series = seriesOf(report);
  const baseline = pointsFor(report, (row) => row.Strategy_Name === report.baseline);

  if (!series.length && !baseline.length) {
    view.append(node("p", "empty", "No held-out row came back for this batch."));
    return view;
  }

  const figure = node("div", "p3");
  const xMax = niceMax(
    Math.max(...[...series.flatMap((s) => s.points), ...baseline].map((p) => p.x), 1),
  );

  const plots = node("div", "plot-pair");
  for (const plot of PLOTS) plots.append(plotFor(plot, series, baseline, xMax));
  figure.append(plots);

  if (series.length) figure.append(legend(figure, series));
  view.append(figure);
  return view;
}

/* -- shaping ------------------------------------------------------------------------ */

/** One entry per configured block, in the order the request listed them. */
function seriesOf(report) {
  const names = [];
  for (const row of report.rows) {
    if (row.Block && !names.includes(row.Block)) names.push(row.Block);
  }
  return names.map((name, index) => ({
    name,
    index,
    shape: SHAPES[index % SHAPES.length],
    className: `series-${(index % SHAPES.length) + 1}`,
    points: pointsFor(report, (row) => row.Block === name),
  }));
}

/** Held-out points for whatever the predicate selects, in capacity order (12.4.6.3). */
function pointsFor(report, predicate) {
  return report.rows
    .filter((row) => row.Set_Name === SET && predicate(row))
    .map((row) => ({
      capacity: row.target_container_rows,
      x: row.container_count,
      materialized_records: row.materialized_records,
      materialized_bytes: row.materialized_bytes,
    }))
    .sort((a, b) => a.capacity - b.capacity);
}

/* -- drawing ------------------------------------------------------------------------ */

function plotFor(plot, series, baseline, xMax) {
  const all = [...series.flatMap((s) => s.points), ...baseline];
  const yMax = niceMax(Math.max(...all.map((point) => point[plot.key]), 1));

  const x = (value) =>
    GEOMETRY.left + (value / xMax) * (GEOMETRY.width - GEOMETRY.left - GEOMETRY.right);
  const y = (value) =>
    GEOMETRY.height -
    GEOMETRY.bottom -
    (value / yMax) * (GEOMETRY.height - GEOMETRY.top - GEOMETRY.bottom);

  const canvas = svg("svg", {
    class: "plot",
    viewBox: `0 0 ${GEOMETRY.width} ${GEOMETRY.height}`,
    role: "img",
    "aria-label": `${plot.axis} against total container count. The same figures are in the table above.`,
  });

  canvas.append(axes(plot, x, y, xMax, yMax));

  // The baseline first, so a candidate that lands on top of it stays visible (12.4.6.5).
  if (baseline.length) canvas.append(trace(baseline, plot, x, y, null));
  for (const entry of series) canvas.append(trace(entry.points, plot, x, y, entry));

  const wrapper = node("figure", "plot-figure");
  wrapper.append(canvas);
  wrapper.append(node("figcaption", "plot-caption", plot.label));
  return wrapper;
}

function axes(plot, x, y, xMax, yMax) {
  const group = svg("g", { class: "axes" });

  for (let step = 0; step <= TICKS; step += 1) {
    const value = (xMax / TICKS) * step;
    group.append(
      svg("line", {
        class: "gridline",
        x1: x(value),
        x2: x(value),
        y1: y(0),
        y2: GEOMETRY.top,
      }),
    );
    group.append(
      svg(
        "text",
        { class: "tick", x: x(value), y: y(0) + 14, "text-anchor": "middle" },
        compact(value),
      ),
    );
  }

  for (let step = 0; step <= TICKS; step += 1) {
    const value = (yMax / TICKS) * step;
    group.append(
      svg("line", {
        class: "gridline",
        x1: GEOMETRY.left,
        x2: GEOMETRY.width - GEOMETRY.right,
        y1: y(value),
        y2: y(value),
      }),
    );
    group.append(
      svg(
        "text",
        { class: "tick", x: GEOMETRY.left - 6, y: y(value) + 3, "text-anchor": "end" },
        plot.tick(value),
      ),
    );
  }

  group.append(
    svg(
      "text",
      {
        class: "axis-title",
        x: (GEOMETRY.left + GEOMETRY.width - GEOMETRY.right) / 2,
        y: GEOMETRY.height - 8,
        "text-anchor": "middle",
      },
      "Total containers",
    ),
  );
  group.append(
    svg(
      "text",
      {
        class: "axis-title",
        transform: `translate(12 ${(GEOMETRY.top + GEOMETRY.height - GEOMETRY.bottom) / 2}) rotate(-90)`,
        "text-anchor": "middle",
      },
      plot.axis,
    ),
  );

  return group;
}

/** One connected series, or the baseline when `entry` is null. */
function trace(points, plot, x, y, entry) {
  const group = svg("g", {
    class: entry ? `series ${entry.className}` : "baseline-trace",
    "data-series": entry ? entry.name : undefined,
  });

  group.append(
    svg("polyline", {
      class: entry ? "line" : "baseline-line",
      points: points.map((point) => `${x(point.x)},${y(point[plot.key])}`).join(" "),
    }),
  );

  for (const point of points) {
    const px = x(point.x);
    const py = y(point[plot.key]);
    group.append(
      entry ? marker(entry.shape, px, py) : svg("circle", { class: "baseline-mark", cx: px, cy: py, r: 2.5 }),
    );
    group.append(
      svg(
        "text",
        { class: "point-label", x: px, y: py - 8, "text-anchor": "middle" },
        count(point.capacity),
      ),
    );
  }

  return group;
}

/** A mark whose shape carries the series as reliably as its colour does (12.4.6.8). */
function marker(shape, x, y, size = 4) {
  if (shape === "square") {
    return svg("rect", { class: "mark", x: x - size, y: y - size, width: size * 2, height: size * 2 });
  }
  if (shape === "triangle") {
    return svg("polygon", {
      class: "mark",
      points: `${x},${y - size} ${x + size},${y + size} ${x - size},${y + size}`,
    });
  }
  if (shape === "diamond") {
    return svg("polygon", {
      class: "mark",
      points: `${x},${y - size} ${x + size},${y} ${x},${y + size} ${x - size},${y}`,
    });
  }
  return svg("circle", { class: "mark", cx: x, cy: y, r: size });
}

/* -- the legend, which is the highlight control (12.4.6.6) --------------------------- */

function legend(figure, series) {
  const list = node("div", "legend");
  list.setAttribute("role", "group");
  list.setAttribute("aria-label", "Highlight one candidate across both plots");

  let pinned = null;

  /** Emphasis is applied by dimming everything else, in both plots at once. */
  const apply = (name) => {
    for (const group of figure.querySelectorAll("[data-series]")) {
      group.classList.toggle("dimmed", name !== null && group.dataset.series !== name);
    }
    for (const button of list.querySelectorAll("[data-series]")) {
      button.classList.toggle("dimmed", name !== null && button.dataset.series !== name);
    }
  };

  for (const entry of series) {
    const button = node("button", `legend-entry ${entry.className}`);
    button.type = "button";
    button.dataset.series = entry.name;
    button.setAttribute("aria-pressed", "false");

    const swatch = svg("svg", { class: "legend-swatch", viewBox: "0 0 12 12", "aria-hidden": "true" });
    swatch.append(marker(entry.shape, 6, 6, 4));
    button.append(swatch);
    button.append(node("span", "legend-name", entry.name));

    button.addEventListener("click", () => {
      pinned = pinned === entry.name ? null : entry.name;
      for (const other of list.querySelectorAll("[data-series]")) {
        other.setAttribute("aria-pressed", String(other.dataset.series === pinned));
      }
      apply(pinned);
    });

    // Hover and focus are the same gesture as the button, not a second mechanism with a
    // reach of its own (12.4.6.6): they preview, and release returns to what is pinned.
    button.addEventListener("mouseenter", () => apply(entry.name));
    button.addEventListener("focus", () => apply(entry.name));
    button.addEventListener("mouseleave", () => apply(pinned));
    button.addEventListener("blur", () => apply(pinned));

    list.append(button);
  }

  // A mark mirrors the legend rather than acting on its own (13.7's bounded exception).
  for (const group of figure.querySelectorAll("[data-series]")) {
    group.addEventListener("mouseenter", () => apply(group.dataset.series));
    group.addEventListener("mouseleave", () => apply(pinned));
  }

  return list;
}

/* -- scales -------------------------------------------------------------------------- */

/** The smallest round number at or above `value`, so ticks land on readable figures. */
function niceMax(value) {
  const magnitude = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10]) {
    if (magnitude * step >= value) return magnitude * step;
  }
  return magnitude * 10;
}
